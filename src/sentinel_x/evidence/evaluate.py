"""Evaluate deterministic investigation against the fixed synthetic answer key."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from .investigator import EvidenceIndex, check_citation
from .runstore import publish


def rate(n, d):
    return n / d if d else None


def assess(report, key, index):
    claims = report["observations"]
    true_fields = set()
    c = Counter()
    for obs in claims:
        field = obs["field"]
        correct = field in key["facts"] and key["facts"][field] == obs["value"]
        support = [check_citation(index, obs, ref) and ref == key["id"] for ref in obs["citations"]]
        c.update(claims=1, true_claims=int(correct), citations=len(support),
                 valid_citations=sum(support), unsupported=int(not any(support)))
        if correct and any(support):
            true_fields.add(field)
    expected_ids = set(key["related"])
    got_ids = set(report["related_event_ids"])
    c.update(cases=1, correct_status=int(report["status"] == key["status"]),
             timeline_match=int([e["event_id"] for e in report["timeline"]] == key["timeline"]))
    if key["status"] == "reported":
        c.update(reportable=1, expected_ids=len(expected_ids), recovered_ids=len(got_ids & expected_ids),
                 sufficient=int(true_fields == set(key["facts"]) and got_ids == expected_ids
                                and report["status"] == "reported"))
    return c


def run(dest, records, cases):
    index = EvidenceIndex(records)
    systems = ("session_retrieval", "anchor_only", "citation_stripped")
    counts = {name: Counter() for name in systems}
    output = []
    key_rows = []
    for case in cases:
        for name in systems:
            report = index.report(case["id"], correlate=name != "anchor_only")
            if name == "citation_stripped":
                for observation in report["observations"]:
                    observation["citations"] = []
            c = assess(report, case, index)
            counts[name].update(c)
            review_id = hashlib.sha256(f"{name}/{case['id']}/sx".encode()).hexdigest()[:12]
            output.append(dict(review_id=review_id, query=case["id"], report=report))
            key_rows.append(dict(review_id=review_id, system=name, counts=dict(c)))
    output.sort(key=lambda row: row["review_id"])
    (dest/"cases.jsonl").write_text("".join(json.dumps(row)+"\n" for row in output))
    (dest/"review_key.json").write_text(json.dumps(key_rows,indent=2)+"\n")
    with (dest/"review.csv").open("w",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["review_id","reviewer","citation_precision","evidence_sufficiency","factual_support",
                         "unsupported_claims","correct_abstention","timeline_consistency","completeness","notes"])
        writer.writerows([[item["review_id"]]+[""]*9 for item in output])
    results = {}
    for name,c in counts.items():
        results[name] = dict(counts=dict(c),
            citation_precision=rate(c["valid_citations"],c["citations"]),
            evidence_sufficiency=rate(c["sufficient"],c["reportable"]),
            factual_support=rate(c["true_claims"],c["claims"]),
            unsupported_claim_frequency=rate(c["unsupported"],c["claims"]),
            abstention_correctness=rate(c["correct_status"],c["cases"]),
            timeline_exact_match=rate(c["timeline_match"],c["cases"]),
            related_id_recall=rate(c["recovered_ids"],c["expected_ids"]))
    return dict(dataset="synthetic controlled records v1", evidence_level="author-specified automated key",
                human_reviews_completed=0,systems=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/v04/evidence")
    args=parser.parse_args()
    paths=[Path("data/fixtures/evidence_records.json"),Path("data/fixtures/evidence_key.json")]
    reg=publish(args.output, paths, "E7-investigation", {"split":"all fixed challenge cases"},
                lambda out: run(out, *(json.loads(p.read_text()) for p in paths)))
    print(reg["experiment_id"],reg["status"],args.output)


if __name__=="__main__":
    main()
