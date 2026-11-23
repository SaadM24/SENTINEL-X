import csv
import json
import sqlite3

import pytest

from sentinel_x.data.prepare import FEATURES, SOURCE, acquire, digest, encode, ingest, prepare


def source_row(identifier, value="1", category="Normal"):
    return dict(id=str(identifier), attack_cat=category, label=str(int(category != "Normal")),
                **dict.fromkeys(FEATURES, value))


def test_output_features_ignore_ground_truth_and_identifier():
    assert encode(source_row(2))[:2] == encode(source_row(89, "1.0", "Exploits"))[:2]
    assert encode(source_row(1, "0"))[0] == encode(source_row(1, "-0"))[0]
    with pytest.raises(ValueError):
        encode(source_row(2, "nan"))
    with pytest.raises(ValueError):
        encode(dict(source_row(3), label="1"))


def test_corrupt_cache_stops(tmp_path):
    (tmp_path/"train.csv").write_text("bad")
    with pytest.raises(ValueError, match="pinned"):
        acquire(tmp_path, "train")


def test_synthetic_is_reproducible_and_cached(tmp_path):
    result = prepare(tmp_path, "smoke")
    manifest = json.loads((result/"manifest.json").read_text())
    assert manifest["synthetic_fixture"]
    with (result/"events.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len({r["event_id"] for r in rows}) == 560
    independent = prepare(tmp_path/"other", "smoke")
    assert digest(independent/"events.csv") == manifest["sha256"]
    assert prepare(tmp_path, "smoke") == result
    (result/"events.csv").write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        prepare(tmp_path, "smoke")


def test_real_preparation_removes_ambiguous_and_overlap(tmp_path, monkeypatch):
    from sentinel_x.data import prepare as module
    raw = tmp_path / "data/raw/unsw"
    raw.mkdir(parents=True)
    rows_by_source = {
        "train":[source_row(1,"1"), source_row(2,"1.0","Exploits"), source_row(3,"2"), source_row(4,"2.0")],
        "test":[source_row(1,"1"),source_row(2,"2"),source_row(3,"3","Exploits")]}
    for source, rows in rows_by_source.items():
        path = raw / (source+".csv")
        with path.open("w",newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        monkeypatch.setitem(SOURCE,source,(digest(path),len(rows)))
    dest = prepare(tmp_path,"research",full=True)
    with (dest/"events.csv").open() as f:
        output = list(csv.DictReader(f))
    assert set(r["event_id"] for r in output) == {"unsw-train-3","unsw-test-3"}
    manifest = json.loads((dest/"manifest.json").read_text())
    assert manifest["cross_source_projected_overlap"] == 2
    assert manifest["audit"]["train"]["ambiguous_vectors"] == 1
