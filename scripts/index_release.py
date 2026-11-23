"""Index the integrated source tree and released empirical artifacts for packaging."""
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT=Path(__file__).resolve().parents[1]

def accepted(p):
    rel=p.relative_to(ROOT)
    return (p.is_file() and not any(s in {".git",".venv","__pycache__",".pytest_cache","outputs","build","dist"}
            or s.endswith(".egg-info") for s in rel.parts)
            and rel.parts[:2]!=("data","raw") and p.suffix not in {".pyc",".lock",".sqlite3"}
            and p.name not in {".env",".DS_Store"}
            and rel.as_posix()!="releases/archive_sha256.json")

def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def put(name,obj):
    p=ROOT/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n",encoding="utf8")

def main():
    files=sorted(p for p in ROOT.rglob("*") if accepted(p))
    code=hashlib.sha256()
    for path in files:
        if path.relative_to(ROOT).parts[0] in {"src","scripts","configs","requirements"} or path.name=="pyproject.toml":
            code.update((path.relative_to(ROOT).as_posix()+":"+sha(path)+"\n").encode())
    version=code.hexdigest()
    def read(rel):
        return json.loads((ROOT/rel).read_text())
    entries=[]
    for folder in sorted((ROOT/"results/v02").glob("*/registry.json")):
        reg=json.loads(folder.read_text())
        base=folder.parent.relative_to(ROOT)
        spec=read(base/"spec.json")
        entries.append(dict(id="flow-"+reg["experiment_id"],code_version=spec["source_sha256"],
            dataset=spec["dataset"],dataset_sha256=spec["dataset_sha256"],splits=reg["split_counts"],
            seed=spec["seed"],model_configuration=spec["config"],dependencies=spec["dependencies"],
            environment=reg["environment"],status="executed",results=str(base/"comparison.csv"),
            seconds_by_model={r["model"]:r["seconds"] for r in reg["runs"]},
            warnings={r["model"]:r["warnings"] for r in reg["runs"] if r["warnings"]},
            registry=folder.relative_to(ROOT).as_posix()))
    suites=[("sequence","ADFA-LD","results/v03/summary.json","results/v03/manifest.json","docs/protocols/SEQUENCE_PROTOCOL.md"),
            ("sequence-fixture","synthetic-order","results/v03_fixture/summary.json","results/v03_fixture/manifest.json","docs/protocols/SEQUENCE_PROTOCOL.md"),
            ("fusion","ADFA-LD","results/v03_fusion/summary.json","results/v03_fusion/manifest.json","docs/protocols/FUSION_PROTOCOL.md"),
            ("retrieval","synthetic-evidence-v1","results/v04/evidence/summary.json","results/v04/evidence/registry.json","docs/protocols/EVIDENCE_AND_TRIAGE.md"),
            ("dashboard","stored benchmark and fixtures","results/v05/browser-check.json","results/v05/manifest.json","docs/architecture/DASHBOARD.md")]
    for p in (ROOT/"results/v10").glob("*/triage/registry.json"):
        rel=p.relative_to(ROOT)
        suites.append(("triage-"+p.parents[1].name,p.parents[1].name,str(rel.parent/"summary.json"),str(rel),"docs/protocols/EVIDENCE_AND_TRIAGE.md"))
    for p in (ROOT/"results/external").glob("*/metrics.json"):
        rel=p.relative_to(ROOT).as_posix()
        suites.append(("shift-"+p.parent.name,p.parent.name,rel,rel,"docs/protocols/EXPERIMENTAL_PROTOCOL.md"))
    for name,dataset,result,config,protocol in suites:
        entries.append(dict(id=name,dataset=dataset,status="executed",results=result,
                            producer_metadata=config,protocol=protocol,code_version=version))
    put("experiments/registry.json",dict(release="1.0",source_sha256=version,experiments=entries,
        system_environment="results/v10/workflow_qa/environment.json",
        limitations="reports/SCIENTIFIC_LIMITATIONS.md",runtime_python=platform.python_version(),
        unexecuted=["native Windows execution","CUDA training","live local LLM","independent analyst review"]))
    releases={
      "v01":["src/sentinel_x/detection","src/sentinel_x/data","configs","data/processed","results/v01","scripts/download_datasets","docs/protocols/DATASET_AUDIT"],
      "v02":["src/sentinel_x/detection","results/v02","configs","scripts/audit_detection","scripts/audit_transformed","docs/protocols/DETECTION","reports/DETECTION"],
      "v03":["src/sentinel_x/behaviour","src/sentinel_x/fusion","results/v03","reports/sequence","docs/protocols/SEQUENCE","docs/protocols/FUSION","scripts/verify_sequence"],
      "v04":["scripts/investigate_record","src/sentinel_x/evidence","results/v04","data/fixtures","scripts/score_evidence","docs/evaluation/INDEPENDENT","docs/protocols/EVIDENCE"],
      "v05":["src/sentinel_x/dashboard","results/v05","docs/architecture/DASHBOARD","scripts/check_dashboard","tests/integration/test_dashboard"],
      "v10":["results/v10","results/external","results/workflow","reports","scripts","docs","experiments","tests","README","setup_windows","launch_dashboard","run_research","run_smoke","resume_research",".github","requirements","pyproject"]}
    for release,prefixes in releases.items():
        paths=[p for p in ROOT.rglob("*") if accepted(p) and any(p.relative_to(ROOT).as_posix().startswith(s) for s in prefixes)]
        put("releases/"+release+".json",dict(stage=release,integrated_source_sha256=version,
               files={p.relative_to(ROOT).as_posix():sha(p) for p in paths}))
    put("releases/index.json",dict(logical_releases=list(releases),completion_matrix="reports/COMPLETION_MATRIX.md",
                                    source_sha256=version))
    put("releases/archive_sha256.json",{p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob("*") if accepted(p)})

if __name__=="__main__":
    main()
