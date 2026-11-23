"""Compute agreement and adjudicated per-condition rates for the v0.4 review."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

FIELDS = ("citation_precision", "evidence_sufficiency", "factual_support", "unsupported_claims",
          "correct_abstention", "timeline_consistency", "completeness")
VALUES = {"yes", "no", "unclear", "na"}


def read(path, expected):
    judgments = {}
    reviewers = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            unit = row["review_id"]
            if unit not in expected or unit in judgments:
                raise ValueError(f"{path}: unexpected or duplicate unit {unit!r}")
            judgments[unit] = {f:row[f].strip().lower() for f in FIELDS}
            if any(v not in VALUES for v in judgments[unit].values()):
                raise ValueError(f"{path}: missing or invalid rating on {unit}")
            reviewers.add(row["reviewer"].strip())
    if len(reviewers) != 1 or "" in reviewers or set(judgments) != set(expected):
        raise ValueError(f"{path}: expected one named reviewer and all required units")
    return judgments,reviewers.pop()


def agreement(pairs):
    a = Counter(x for x,y in pairs)
    b = Counter(y for x,y in pairs)
    total = len(pairs)
    exact = sum(x == y for x,y in pairs) / total
    chance = sum(a[v]*b[v] for v in VALUES) / total**2
    return {"n":total, "observed_agreement":exact, "nominal_kappa":None if chance==1 else (exact-chance)/(1-chance)}


def score(keyfile, a_path, b_path, adjudicated_path=None):
    key = {r["review_id"]:r["system"] for r in json.loads(keyfile.read_text())}
    a, who_a = read(a_path,key)
    b, who_b = read(b_path,key)
    if who_a.casefold()==who_b.casefold():
        raise ValueError("Distinct reviewer identifiers required")
    resolution = {}
    if adjudicated_path:
        resolution, name = read(adjudicated_path,key)
        if name.casefold() in {who_a.casefold(),who_b.casefold()}:
            raise ValueError("Use a separate adjudicator identifier")
    disagree = []
    by_system = defaultdict(lambda:defaultdict(Counter))
    for unit, system in key.items():
        for field in FIELDS:
            left,right = a[unit][field], b[unit][field]
            if left != right:
                disagree.append({"review_id":unit,"field":field,"A":left,"B":right})
                value = resolution[unit][field] if resolution else "unresolved"
            else:
                value = left
                if resolution and resolution[unit][field] != value:
                    raise ValueError(f"Adjudication changed an agreed rating: {unit}, {field}")
            by_system[system][field][value] += 1
    output = {"reviewers":[who_a,who_b],"units":len(key),"agreement":{},"disagreements":disagree,
              "by_system":{},"all_resolved":not disagree or bool(resolution)}
    for field in FIELDS:
        output["agreement"][field]=agreement([(a[u][field],b[u][field]) for u in key])
    for system,fields in by_system.items():
        output["by_system"][system]={}
        for field,counts in fields.items():
            denominator=counts["yes"]+counts["no"]
            output["by_system"][system][field] = {"counts":dict(counts),"binary_denominator":denominator,
                "yes_rate_among_decisive":counts["yes"]/denominator if denominator else None}
    return output


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewer_a",type=Path)
    parser.add_argument("reviewer_b",type=Path)
    parser.add_argument("--key",type=Path,default=Path("results/v04/evidence/review_key.json"))
    parser.add_argument("--adjudication",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    report=score(args.key,args.reviewer_a,args.reviewer_b,args.adjudication)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,allow_nan=False)
        f.write("\n")
