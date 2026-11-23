"""Compare frozen triage policies on stored held-out model predictions."""
import argparse
import csv
import json
from collections import Counter
from decimal import Decimal
from math import isfinite
from pathlib import Path
from .investigator import EvidenceIndex, check_citation
from .runstore import publish


POLICIES = (("raw_all","raw_probability",0),("cal_all","probability",0),
            ("cal_70","probability",0.70),("cal_85","probability",0.85),("cal_95","probability",0.95))


def run(out, predictions):
    counts = {policy:Counter() for policy, _, _ in POLICIES}
    sources = set()
    models = set()
    seen = set()
    cases = cited = claims = 0
    with predictions.open(newline="") as data, (out/"decisions.csv").open("w",newline="") as decisions, (
            out/"reports.jsonl").open("w") as reports:
        reader = csv.DictReader(data)
        writer = csv.writer(decisions)
        writer.writerow(["event_id","policy","decision","escalated","error","y_true"])
        for row in reader:
            event_id = row["event_id"]
            if not event_id or event_id in seen:
                raise ValueError("Duplicate or empty held-out event ID")
            seen.add(event_id)
            sources.add(row["dataset"])
            models.add(row["model"])
            if len(sources) > 1 or len(models) > 1:
                raise ValueError("One run must use one dataset and one model")
            label = int(row["y_true"])
            if label not in (0,1):
                raise ValueError("Expected binary outcome")
            scores = {field:float(row[field]) for field in ("raw_probability","probability")}
            if not all(isfinite(p) and 0 <= p <= 1 for p in scores.values()):
                raise ValueError("Invalid probability")
            for policy, field, threshold in POLICIES:
                p = scores[field]
                predicted = int(p >= 0.5)
                # Compare against both class boundaries, avoiding cancellation around a tie.
                boundary = Decimal(str(threshold))
                score = Decimal(row[field])
                escalated = (Decimal(1)-boundary) < score < boundary
                error = predicted != label
                counts[policy].update(n=1, escalated=int(escalated), escalated_errors=int(escalated and error),
                                      automatic_errors=int(not escalated and error), errors=int(error))
                writer.writerow([event_id,policy,predicted,int(escalated),int(error),label])
                if policy == "cal_85" and escalated:
                    # Deliberate projection: annotation and attack family never enter the index.
                    index = EvidenceIndex([{"event_id":event_id,"model":row["model"],"probability":p}])
                    report = index.report(event_id)
                    for obs in report["observations"]:
                        claims += 1
                        cited += int(any(check_citation(index,obs,ref) for ref in obs["citations"]))
                    reports.write(json.dumps(report)+"\n")
                    cases += 1
    if not seen:
        raise ValueError("Empty held-out prediction table")
    result = {}
    for policy,c in counts.items():
        n_auto=c["n"]-c["escalated"]
        result[policy] = dict(c, coverage=n_auto/c["n"],
                              automatic_risk=c["automatic_errors"]/n_auto if n_auto else None,
                              unnecessary_escalations=c["escalated"]-c["escalated_errors"])
    return dict(dataset=next(iter(sources)),model=next(iter(models)),policies=result,
                fixed_threshold_report_ablation={"cases":cases,"claims":claims,
                "verifiable_claims_with_citations":cited,"verifiable_claims_after_stripping_citations":0},
                limitations="Score and model metadata only. Reviewer time, reviewer accuracy and root cause unmeasured.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--predictions", required=True,type=Path)
    p.add_argument("--output", required=True)
    args=p.parse_args()
    reg=publish(args.output,[args.predictions],"E8-integrated-triage",
                {"policies":list(map(list,POLICIES)),"split":"upstream held-out predictions"},
                lambda out: run(out,args.predictions))
    print(reg["experiment_id"],reg["status"],args.output)


if __name__=="__main__":
    main()
