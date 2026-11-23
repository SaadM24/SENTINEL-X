"""Independently verify released classifier-input CSVs and distribution manifests."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def audit(folder):
    manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    path = folder / "events.csv"
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != manifest["sha256"]:
            raise ValueError("Released event-table checksum mismatch")
    features = manifest["features"]
    ids, observed_vectors = set(), set()
    categories = {split:Counter() for split in ["train","cal","test"]}
    labels = {split:Counter() for split in categories}
    with path.open(encoding="utf-8",newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["event_id","split","label","attack_category",*features]:
            raise ValueError("Unexpected output schema or feature order")
        for row in reader:
            split = row["split"]
            event = row["event_id"]
            if split not in categories or not event or event in ids:
                raise ValueError("Invalid split or repeated/empty event ID")
            ids.add(event)
            # Decode the actual CSV using floating-point semantics, independently
            # of the preparation code's decimal formatting.
            vals = tuple(float(row[k]) if row[k] else None for k in features)
            if any(x is not None and not math.isfinite(x) for x in vals):
                raise ValueError("Non-finite value in output")
            if vals in observed_vectors:
                raise ValueError("Duplicate model vector survived preparation")
            observed_vectors.add(vals)
            y = int(row["label"])
            cat = row["attack_category"]
            if y not in [0,1] or (cat=="Normal") != (y==0):
                raise ValueError("Inconsistent output label")
            categories[split][cat] += 1
            labels[split][y] += 1
    for split, cat in categories.items():
        claimed = manifest["partitions"][split]
        if dict(cat) != claimed["categories"] or sum(cat.values()) != claimed["selected"]:
            raise ValueError("Output distribution differs from release manifest")
    return {"scope":"Schema, SHA-256, record IDs, category/label mapping, distribution, unique numeric feature vectors across all released partitions",
            "cohort":folder.name, "sha256":manifest["sha256"], "distinct_ids":len(ids),
            "distinct_feature_vectors":len(observed_vectors),"class_counts":labels}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folders",type=Path,nargs="+")
    p.add_argument("--output",type=Path)
    args = p.parse_args()
    out = json.dumps([audit(path) for path in args.folders],indent=2)+"\n"
    if args.output:
        with args.output.open("x",encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)
