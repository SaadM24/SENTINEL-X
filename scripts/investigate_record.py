"""Build a cited evidence report for one anchor. An optional local model can order existing facts."""
import argparse
import json
from pathlib import Path
from sentinel_x.evidence.investigator import EvidenceIndex
from sentinel_x.evidence.provider import local_rerank

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records",type=Path,default=Path("data/fixtures/evidence_records.json"))
    parser.add_argument("--event",required=True,help="Record ID from the supplied JSON list")
    parser.add_argument("--local-model",help="Optional installed Ollama model for constrained ordering")
    args=parser.parse_args()
    report=EvidenceIndex(json.loads(args.records.read_text(encoding="utf-8"))).report(args.event)
    if args.local_model:
        report=local_rerank(report,args.local_model)
    print(json.dumps(report,indent=2,ensure_ascii=True,allow_nan=False))

if __name__=="__main__":
    main()
