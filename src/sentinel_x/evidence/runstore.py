"""Publish complete result bundles atomically; never mix inputs or source versions."""
import hashlib
import json
import platform
import tempfile
import shutil
import time
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def publish(destination, inputs, name, config, execute):
    dest = Path(destination)
    source_dir = Path(__file__).resolve().parent
    source = {p.name: sha(p) for p in sorted(source_dir.glob("*.py"))}
    code = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    fingerprints = {str(path): sha(path) for path in inputs}
    if dest.is_dir():
        reg = json.loads((dest / "registry.json").read_text())
        if (reg["inputs"] != fingerprints or reg["code_version"] != code
                or reg["configuration"] != config):
            raise ValueError("Existing run differs; choose a new output directory.")
        if any(sha(dest / path) != digest for path, digest in reg["artifacts"].items()):
            raise ValueError("Existing result failed integrity check.")
        return reg
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="." + dest.name + "-", dir=dest.parent))
    start = time.perf_counter()
    try:
        results = execute(tmp)
        (tmp / "summary.json").write_text(json.dumps(results, indent=2, allow_nan=False)+"\n")
        reg = dict(experiment_id=name, code_version=code, inputs=fingerprints,
                   configuration=config, environment=platform.platform(), python=platform.python_version(),
                   dependencies="Python standard library", seed=None, status="executed",
                   results="summary.json", runtime_seconds=time.perf_counter()-start,
                   artifacts={p.name: sha(p) for p in sorted(tmp.iterdir())})
        (tmp / "registry.json").write_text(json.dumps(reg, indent=2)+"\n")
        tmp.rename(dest)
        return reg
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
