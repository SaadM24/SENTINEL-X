"""Create a stratified, blinded packet of actual test records for human inspection."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

from sentinel_x.evidence.investigator import EvidenceIndex, check_citation
from sentinel_x.evidence.runstore import publish


def stable_id(value):
    return hashlib.sha256(("SENTINEL-X review " + value).encode()).hexdigest()


def packet(out, predictions, events):
    groups = defaultdict(list)
    with predictions.open(newline="") as f:
        for row in csv.DictReader(f):
            truth=int(row["y_true"])
            pred=int(float(row["probability"])>=0.5)
            group=("T" if pred==truth else "F") + ("P" if pred else "N")
            groups[group].append(row)
    sample=[]
    for group,rows in sorted(groups.items()):
        sample.extend((group,item) for item in sorted(rows,key=lambda r:stable_id(r["event_id"]))[:5])
    selected={r["event_id"]:r for _,r in sample}
    raw={}
    with events.open(newline="") as f:
        for row in csv.DictReader(f):
            eid=row["event_id"]
            if row["split"]=="test" and eid in selected:
                if eid in raw or int(row["label"]) != int(selected[eid]["y_true"]):
                    raise ValueError("Ambiguous event or inconsistent evaluation label")
                raw[eid]={k:v for k,v in row.items() if k.startswith("f_")}
    if set(raw)!=set(selected) or len(raw)<2:
        raise ValueError("Need at least two fully matched held-out events")
    sample.sort(key=lambda pair:stable_id(pair[1]["event_id"]))
    records=[{"event_id":row["event_id"],"model":row["model"],"probability":float(row["probability"])}
             for _,row in sample]
    index=EvidenceIndex(records)
    control=defaultdict(lambda:{"claims":0,"right_record_field_matches":0,
                                 "wrong_record_field_matches":0,"wrong_record_identity_and_field_matches":0})
    key=[]
    with (out/"blinded_cases.jsonl").open("w",encoding="utf-8") as stream, (
            out/"review.csv").open("w",newline="") as sheet:
        writer=csv.writer(sheet)
        writer.writerow(["unit","reviewer","record_fields_correct","policy_reason_correct",
                         "insufficient_for_attack_attribution","notes"])
        for i,(group,row) in enumerate(sample):
            eid=row["event_id"]
            unit=stable_id(eid)[:12]
            report=index.report(eid)
            p=float(row["probability"])
            pred=int(p>=0.5)
            review=0.15<p<0.85
            for obs in report["observations"]:
                c=control[obs["field"]]
                wrong=sample[(i+1)%len(sample)][1]["event_id"]
                c["claims"]+=1
                c["right_record_field_matches"]+=int(check_citation(index,obs,eid))
                c["wrong_record_field_matches"]+=int(check_citation(index,obs,wrong))
                c["wrong_record_identity_and_field_matches"]+=int(wrong==eid and check_citation(index,obs,wrong))
            item=dict(unit=unit,query=eid,measurements=raw[eid],evidence=records[i],
                      report=report,policy={"positive_at_or_above":0.5,"escalate_below_confidence":0.85,
                                          "predicted_label":pred,"escalated":review})
            stream.write(json.dumps(item)+"\n")
            writer.writerow([unit,"","","","",""])
            key.append(dict(unit=unit,event_id=eid,ground_truth=row["y_true"],category=row["category"],stratum=group))
    (out/"coordinator_key.json").write_text(json.dumps(key,indent=2)+"\n")
    return dict(dataset=sample[0][1]["dataset"],cases=len(sample),source_counts={g:len(r) for g,r in groups.items()},
                reviewed_by_humans=0,negative_control=dict(control),
                interpretation="Exploratory case-control sample; unsuitable for population risk estimates.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions",type=Path,default=Path("results/v02/research/predictions.csv"))
    parser.add_argument("--events",type=Path,default=Path("data/processed/research/events.csv"))
    parser.add_argument("--output",default="results/v10/research/evidence_packet")
    args=parser.parse_args()
    publish(args.output,[args.predictions,args.events,Path("scripts/build_evidence_packet.py")],
            "E8-exploratory-reviewed-flow-packet",{"split":"held-out test","per_stratum":5,"human_reviews":0},
            lambda out:packet(out,args.predictions,args.events))
