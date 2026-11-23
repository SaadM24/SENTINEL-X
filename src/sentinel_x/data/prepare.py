"""Prepare UNSW flow vectors with disk-backed overlap filtering and immutable output."""
import csv
import hashlib
import json
import math
import os
import random
import shutil
import sqlite3
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

VERSION = "unsw-flow-1"
PUBLISHER = "https://research.unsw.edu.au/projects/unsw-nb15-dataset"
MIRROR = "https://raw.githubusercontent.com/huangxyy/bdcc-ids-defense-selection/a490371076ed35c1819815c2371874a8bebeb0b1/data/"
SOURCE = {
    "train": ("afab90b86a0383f249d263e32e21795e33cdfeb906e834f55e7f1ea0fb592dbe", 175341),
    "test": ("e4d5f673a05f2e4b93233dcb57318a15016261fc76d4547767648485703d9930", 82332),
}
# End-of-flow aggregates only. No labels, addresses, ports, ID, TCP bases or
# precomputed multi-flow counters. Fingerprint this exact projection.
FEATURES = "dur spkts dpkts sbytes dbytes rate sload dload sloss dloss sinpkt dinpkt sjit djit tcprtt synack ackdat smean dmean".split()
HEADER = ["event_id", "split", "label", "attack_category", *["f_" + f for f in FEATURES]]
LIMITS = {"train": 6000, "cal": 1500, "test": 3000}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def acquire(directory, source):
    expected, _ = SOURCE[source]
    target = directory / (source + ".csv")
    if not target.exists():
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as f:
            temporary = Path(f.name)
            try:
                with urllib.request.urlopen(MIRROR + target.name, timeout=90) as response:
                    shutil.copyfileobj(response, f, length=1 << 20)
            except BaseException:
                f.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            if digest(temporary) != expected:
                raise ValueError(f"Download checksum mismatch: {source}")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    if digest(target) != expected:
        raise ValueError(f"Cached file differs from pinned mirror bytes: {target}")
    return target


def encode(row):
    vals = [row[k].strip() for k in FEATURES]
    # Empty values are represented consistently, then imputed by training code.
    numbers = [float(v) if v else None for v in vals]
    if any(v is not None and (not math.isfinite(v) or v < 0) for v in numbers):
        raise ValueError("Unexpected nonfinite or negative UNSW flow feature")
    vals = ["" if v is None else format(v or 0., ".17g") for v in numbers]
    packed = ",".join(vals)
    key = hashlib.sha256(packed.encode("ascii")).hexdigest()
    label, category = int(row["label"]), row["attack_cat"].strip()
    if label not in (0, 1) or not category or ((category.lower() == "normal") != (label == 0)):
        raise ValueError("Inconsistent label/category")
    return key, packed, label, category, vals


def ingest(conn, source, path):
    stats = Counter()
    classes, missing = Counter(), Counter()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(["id", "label", "attack_cat", *FEATURES]) <= set(fields):
            raise ValueError("Invalid source schema")
        for row in reader:
            key, packed, label, category, vals = encode(row)
            classes[category] += 1
            missing.update(k for k, v in zip(FEATURES, vals) if not v)
            stats["source_rows"] += 1
            conn.execute("""INSERT INTO vectors VALUES (?, ?, ?, ?, ?, ?, 0, 1)
                ON CONFLICT(source, key) DO UPDATE SET copies=copies+1,
                ambiguous=ambiguous OR excluded.category != category OR excluded.label != label""",
                         (source, key, row["id"], packed, label, category))
    unique, ambiguous = conn.execute("SELECT COUNT(*), SUM(ambiguous) FROM vectors WHERE source=?", (source,)).fetchone()
    return {**stats, "unique_projected_vectors": unique, "additional_projected_duplicates":stats["source_rows"]-unique,
            "ambiguous_vectors": ambiguous or 0, "source_categories": dict(classes),
            "missing_values_by_feature": {k:missing[k] for k in FEATURES},
            "sha256": digest(path), "bytes": path.stat().st_size}


def write_unsw(work, raw, full):
    database = work / "audit.sqlite"
    conn = sqlite3.connect(database)
    conn.execute("""CREATE TABLE vectors(source TEXT,key TEXT,id TEXT,packed TEXT,label INTEGER,
                 category TEXT,ambiguous INTEGER,copies INTEGER,PRIMARY KEY(source,key)) WITHOUT ROWID""")
    try:
        stats = {}
        for source in SOURCE:
            path = acquire(raw, source)
            stats[source] = ingest(conn, source, path)
            if stats[source]["source_rows"] != SOURCE[source][1]:
                raise ValueError(f"Wrong record count: {source}")
        conn.commit()
        overlaps = conn.execute("""SELECT count(*) FROM vectors t JOIN vectors r ON r.key=t.key
            WHERE t.source='test' AND r.source='train'""").fetchone()[0]
        # Two disjoint hash prefixes: first byte sets cal/train; remainder samples.
        queries = {
            "train": "source='train' AND substr(key,1,2)>='33'",
            "cal": "source='train' AND substr(key,1,2)<'33'",
            "test": "source='test' AND NOT EXISTS (SELECT 1 FROM vectors r WHERE r.source='train' AND r.key=t.key)",
        }
        counts = {}
        with (work / "events.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            for split, where in queries.items():
                eligible = " FROM vectors t WHERE ambiguous=0 AND " + where
                available = conn.execute("SELECT COUNT(*)" + eligible).fetchone()[0]
                rows = conn.execute("SELECT source,id,packed,label,category" + eligible +
                                    " ORDER BY substr(key,3),key LIMIT ?", (-1 if full else LIMITS[split],))
                cats = Counter()
                for source, raw_id, packed, label, cat in rows:
                    writer.writerow([f"unsw-{source}-{raw_id}", split, label, cat, *packed.split(",")])
                    cats[cat] += 1
                counts[split] = {"eligible":available, "selected":sum(cats.values()), "categories":dict(cats)}
        return {"dataset":"UNSW-NB15", "version":VERSION, "provenance":PUBLISHER, "mirror":MIRROR,
                "synthetic_fixture":False, "audit":stats, "cross_source_projected_overlap":overlaps, "partitions":counts,
                "sampling":"SHA-256 feature vector grouping, first byte < 51 gives calibration; remaining bytes rank eligible observations. Training source takes priority. Ambiguous categories within source excluded.",
                "mode":"full" if full else "bounded"}
    finally:
        conn.close()
        database.unlink(missing_ok=True)


def write_smoke(work):
    rng = random.Random(119)
    counts = {}
    with (work / "events.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for split, n in [("train",320),("cal",100),("test",140)]:
            cats = Counter()
            for i in range(n):
                y = int(rng.random() < .37)
                c = "fixture-anomaly" if y else "Normal"
                cats[c] += 1
                features = [round(rng.lognormvariate(y*.70 if j<4 else 0, 1.), 8) for j in range(len(FEATURES))]
                writer.writerow([f"fixture-{split}-{i}", split, y, c, *features])
            counts[split] = {"eligible":n,"selected":n,"categories":dict(cats)}
    return {"dataset":"synthetic smoke fixture", "version":"fixture-1", "synthetic_fixture":True,
            "provenance":"Seed 119 independent lognormal columns, artificial binary labels; no security inference.",
            "partitions":counts,"mode":"smoke"}


def prepare(root, mode, full=False):
    if mode not in ("smoke","research") or (mode == "smoke" and full):
        raise ValueError("Unsupported preparation mode")
    base = Path(root) / "data"
    target = base / "processed" / (mode + ("-full" if full else ""))
    if target.exists():
        m = json.loads((target / "manifest.json").read_text())
        if m["sha256"] != digest(target / "events.csv"):
            raise ValueError("Prepared CSV checksum mismatch. Move damaged directory before rebuilding.")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="prepare-",dir=target.parent))
    try:
        manifest = write_smoke(work) if mode == "smoke" else write_unsw(work,base / "raw/unsw",full)
        manifest.update(features=HEADER[4:], sha256=digest(work/"events.csv"))
        (work / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
        work.rename(target)
    finally:
        if work.exists():
            shutil.rmtree(work)
    return target
