"""Execute independent stages, retaining the status and console log for each attempt."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}\Z")


@contextmanager
def exclusive_run(directory):
    """A kernel lock is automatically released if the orchestrator is interrupted."""
    with (directory / "workflow.lock").open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise SystemExit(f"Another workflow is active in {directory}") from error
        yield


def stages(mode, name, seed, full, resume, device, sequence, test):
    input_mode = "research-full" if full else mode
    data = f"data/processed/{input_mode}/events.csv"
    stages = [
        ("environment", [], ["scripts/check_environment.py"] + (["--require-tests"] if test else [])),
        ("data", ["environment"], ["scripts/download_datasets.py", "--mode", mode] + (["--full"] if full else [])),
        ("detection", ["data"], ["-m", "sentinel_x.detection", "--input", data,
                                 "--run", name, "--mode", mode, "--seed", str(seed), "--device", device]
                                 + (["--resume"] if resume else [])),
        ("replay", ["detection"], ["scripts/audit_detection.py", "--input", data,
                                   "--results", f"results/v02/{name}"]),
        ("overlap", ["detection"], ["scripts/audit_transformed_overlap.py", "--input", data,
                                    "--results", f"results/v02/{name}"]),
        ("sequences", ["environment"], ["-m", "sentinel_x.behaviour", "--dataset", sequence,
                                        "--out", f"results/v03/{name}"]),
        ("evidence", ["environment"], ["-m", "sentinel_x.evidence.evaluate",
                                       "--output", f"results/v04/{name}"]),
        ("triage", ["detection", "evidence"], ["-m", "sentinel_x.evidence.triage",
            "--predictions", f"results/v02/{name}/predictions.csv", "--output", f"results/v10/{name}/triage"]),
        ("export", ["detection"], ["scripts/export_research_results.py", "--run", name]),
        ("verify", ["detection", "export"], ["scripts/verify_results.py", "--run", name]),
    ]
    if mode == "research" and sequence == "adfa":
        stages.append(("fusion", ["sequences"], ["-m", "sentinel_x.fusion",
                      "--out", f"results/v03_fusion/{name}", "--archive", "data/raw/ADFA-LD.zip"]))
    if mode == "research":
        stages.append(("review_packet", ["triage"], ["scripts/build_evidence_packet.py",
                      "--predictions", f"results/v02/{name}/predictions.csv", "--events", data,
                      "--output", f"results/v10/{name}/evidence_packet"]))
    if test:
        stages.insert(1, ("tests", ["environment"], ["-m", "pytest", "-q"]))
    return stages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "research"], default="smoke")
    parser.add_argument("--run", help="New experiment identifier, must start with local-.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--full", action="store_true", help="Use all eligible official UNSW rows.")
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument("--sequence", choices=["fixture", "adfa"])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--tests", action="store_true", help="Run all repository tests in addition to experiments.")
    parser.add_argument("--list", action="store_true", help="Print the exact commands without running.")
    args = parser.parse_args()
    if args.full and args.mode != "research":
        parser.error("--full needs --mode research")
    name = args.run or ("local-" + args.mode + ("-full" if args.full else ""))
    if not SAFE_NAME.fullmatch(name) or not name.startswith("local-"):
        parser.error("use a simple local- prefixed name with ASCII letters, digits, - or _")
    sequence = args.sequence or ("fixture" if args.mode == "smoke" else "adfa")
    jobs = stages(args.mode, name, args.seed, args.full, args.resume, args.device, sequence, args.tests)
    if args.list:
        for step, _, command in jobs:
            print(step, subprocess.list2cmdline([sys.executable, *command]))
        return 0
    run_dir = ROOT / "results" / "workflow" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    with exclusive_run(run_dir):
        return execute_jobs(args, parser, run_dir, name, sequence, jobs)


def execute_jobs(args, parser, run_dir, name, sequence, jobs):
    settings = dict(run=name, mode=args.mode, seed=args.seed, full=args.full, device=args.device,
                    sequence=sequence)
    specification = run_dir / "configuration.json"
    if specification.exists():
        if json.loads(specification.read_text()) != settings:
            parser.error(f"configuration mismatch with {specification}; choose a new --run")
        if not args.resume:
            parser.error("existing run: add --resume or choose another --run")
    else:
        with specification.open("x", encoding="utf8") as handle:
            json.dump(settings, handle, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = run_dir / stamp
    attempt.mkdir()
    state = {}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    for step, prerequisites, command in jobs:
        failed = [p for p in prerequisites if state[p]["status"] != "passed"]
        entry = {"command": command, "blocked_by": failed, "status": "blocked" if failed else "running"}
        state[step] = entry
        print(f"[{step}] {entry['status']}", flush=True)
        (attempt / "status.json").write_text(json.dumps(state, indent=2), encoding="utf8")
        if failed:
            continue
        start = time.monotonic()
        log = attempt / (step + ".log")
        with log.open("w", encoding="utf8") as stream:
            completed = subprocess.run([sys.executable, "-u", *command], cwd=ROOT,
                                       env=env, stdout=stream, stderr=subprocess.STDOUT)
        entry.update(status="passed" if completed.returncode == 0 else "failed",
                     returncode=completed.returncode, seconds=round(time.monotonic()-start, 3),
                     log=str(log.relative_to(ROOT)))
        print(f"  {entry['status']} ({entry['seconds']}s) {log.relative_to(ROOT)}", flush=True)
        (attempt / "status.json").write_text(json.dumps(state, indent=2), encoding="utf8")
    return int(any(item["status"] != "passed" for item in state.values()))


if __name__ == "__main__":
    sys.exit(main())
