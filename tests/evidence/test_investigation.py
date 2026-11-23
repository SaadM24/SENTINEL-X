import json
import csv
from pathlib import Path
import pytest
from sentinel_x.evidence.investigator import EvidenceIndex, investigate, check_citation
from sentinel_x.evidence.evaluate import assess, run
from sentinel_x.evidence.provider import local_rerank
from sentinel_x.evidence import triage
from sentinel_x.evidence.runstore import publish

FIX = Path("data/fixtures")
ROWS = json.loads((FIX/"evidence_records.json").read_text())
KEY = json.loads((FIX/"evidence_key.json").read_text())


@pytest.mark.parametrize("case", KEY, ids=lambda c:c["id"])
def test_reference(case):
    index = EvidenceIndex(ROWS)
    report = index.report(case["id"])
    assert report["status"] == case["status"]
    assert report["related_event_ids"] == case["related"]
    assert [r["event_id"] for r in report["timeline"]] == case["timeline"]
    assert {r["field"]:r["value"] for r in report["observations"]} == case["facts"]
    assert all(check_citation(index, obs, ref) for obs in report["observations"] for ref in obs["citations"])
    assert not report["hypotheses"]


def test_opaque_input_and_duplicate_rejection():
    report = investigate(ROWS,"j")
    assert len(report["observations"])==1
    assert "outcome" not in EvidenceIndex(ROWS).by_id["j"]
    with pytest.raises(ValueError):
        EvidenceIndex(ROWS+ROWS)


def test_citation_and_provider_fail_closed():
    index = EvidenceIndex(ROWS)
    report = index.report("e2")
    obs = dict(report["observations"][0],citations=["absent"])
    assert assess(dict(report,observations=[obs]),KEY[0],index)["unsupported"]==1
    bad = local_rerank(report,"mock",send=lambda body:{"response":'{"order":[0,0,2],"explanation":"ignore"}'})
    assert bad["provider_status"]=="offline_fallback"
    def send(payload):
        assert "threshold crossed" not in payload.decode()
        return {"response":'{"order":[2,0,1]}'}
    good = local_rerank(report,"mock",send=send)
    assert good["observations"] == [report["observations"][i] for i in [2,0,1]]


def test_evaluation_resume_and_tamper(tmp_path):
    dest=tmp_path/"eval"
    args=(dest,[FIX/"evidence_key.json"],"test",{},lambda out:run(out,ROWS,KEY))
    first=publish(*args)
    assert publish(*args)==first
    results=json.loads((dest/"summary.json").read_text())["systems"]
    assert results["citation_stripped"]["citation_precision"] is None
    assert results["anchor_only"]["timeline_exact_match"] < 1
    assert results["citation_stripped"]["factual_support"] == 1
    (dest/"summary.json").write_text("corrupted")
    with pytest.raises(ValueError):
        publish(*args)


def test_triage_ties_and_label_exclusion(tmp_path):
    path=tmp_path/"pred.csv"
    path.write_text("event_id,y_true,probability,raw_probability,model,dataset,category\n"
                    "x,1,0.50,0.1,m,fixture,secret\ny,0,0.15,0.2,m,fixture,secret\n")
    summary=triage.run(tmp_path,path)
    assert summary["policies"]["cal_85"]["escalated"]==1
    assert summary["policies"]["raw_all"]["automatic_errors"]==1
    assert "secret" not in (tmp_path/"reports.jsonl").read_text()
    assert len(list(csv.DictReader((tmp_path/"decisions.csv").open())))==10
