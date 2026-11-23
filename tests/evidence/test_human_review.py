import csv
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("review",Path("scripts/score_evidence_reviews.py"))
review=importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def sheet(path,who,values):
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["review_id","reviewer",*review.FIELDS])
        writer.writeheader()
        for key,value in values:
            writer.writerow(dict(review_id=key,reviewer=who,**{field:value for field in review.FIELDS}))


def test_scorer_and_adjudication(tmp_path):
    key=tmp_path/"k.json"
    key.write_text('[{"review_id":"x","system":"test"},{"review_id":"y","system":"test"}]')
    a,b,c=[tmp_path/name for name in ["a","b","c"]]
    sheet(a,"A",[("x","yes"),("y","no")])
    sheet(b,"B",[("x","yes"),("y","yes")])
    first=review.score(key,a,b)
    assert first["agreement"]["factual_support"]["observed_agreement"]==0.5
    assert first["all_resolved"] is False
    sheet(c,"C",[("x","yes"),("y","unclear")])
    assert review.score(key,a,b,c)["all_resolved"]
    with pytest.raises(ValueError):
        review.score(key,a,a)
    sheet(c,"C",[("x","no"),("y","unclear")])
    with pytest.raises(ValueError):
        review.score(key,a,b,c)


def test_blinded_packet_hides_outcomes_and_checks_identity(tmp_path):
    p_spec=importlib.util.spec_from_file_location("packet",Path("scripts/build_evidence_packet.py"))
    pmod=importlib.util.module_from_spec(p_spec)
    p_spec.loader.exec_module(pmod)
    preds=tmp_path/"pred.csv"
    events=tmp_path/"events.csv"
    preds.write_text("event_id,y_true,probability,model,dataset,category\n"
                     "e1,1,0.9,same,d,attack\ne2,0,0.8,same,d,Normal\n")
    events.write_text("event_id,label,split,f_dur,attack_category\ne1,1,test,1,attack\ne2,0,test,2,Normal\n")
    summary=pmod.packet(tmp_path,preds,events)
    control=summary["negative_control"]
    assert control["model"]["wrong_record_field_matches"]==2
    assert control["model"]["wrong_record_identity_and_field_matches"]==0
    assert control["probability"]["wrong_record_field_matches"]==0
    import json
    blind=[json.loads(line) for line in (tmp_path/"blinded_cases.jsonl").read_text().splitlines()]
    assert all(set(row["measurements"])=={"f_dur"} for row in blind)
    assert all("y_true" not in row["evidence"] for row in blind)
