"""Retrieve a bounded public NetFlow v3 mirror sample with deterministic block offsets."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
from pathlib import Path
import random
import time
import urllib.parse
import urllib.request

DATASET = "keys-i/netFlow"
REVISION = "59b97b2fa47e2ce45488812289c83adefe877355"
CORPORA = {"NF-UNSW-NB15-v3": 2365424, "NF-CSE-CIC-IDS2018-v3": 20115529}
FEATURES = ["IN_BYTES", "OUT_BYTES", "IN_PKTS", "OUT_PKTS", "FLOW_DURATION_MILLISECONDS",
            "LONGEST_FLOW_PKT", "SHORTEST_FLOW_PKT", "RETRANSMITTED_IN_PKTS",
            "RETRANSMITTED_OUT_PKTS", "TCP_WIN_MAX_IN", "TCP_WIN_MAX_OUT"]

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)

def retrieve(out):
    current = get("https://huggingface.co/api/datasets/" + DATASET)["sha"]
    if current != REVISION:
        raise ValueError("Mirror revision changed; inspect provenance before collecting new results")
    out.mkdir(parents=True, exist_ok=True)
    for corpus, size in CORPORA.items():
        rng = random.Random(2026)
        offsets = [rng.randrange(i*size//32, (i+1)*size//32-100) for i in range(32)]
        def fetch(offset):
            path = out / f"{corpus}-{offset}.json"
            if path.exists():
                return json.loads(path.read_text())
            query = urllib.parse.urlencode(dict(dataset=DATASET, config=corpus, split="full", offset=offset, length=100))
            rows = get("https://datasets-server.huggingface.co/rows?" + query)["rows"]
            if [r["row_idx"] for r in rows] != list(range(offset, offset+100)):
                raise ValueError("Unexpected source row IDs")
            records = [{**{k: r["row"][k] for k in FEATURES+["Label"]}, "source_row": r["row_idx"]} for r in rows]
            tmp = path.with_suffix(".part")
            tmp.write_text(json.dumps(records))
            tmp.replace(path)
            return records
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            blocks = list(pool.map(fetch, offsets))
        path = out / (corpus + ".csv")
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FEATURES+["Label", "source_row"])
            writer.writeheader()
            for block in blocks:
                writer.writerows(block)
        print(corpus, hashlib.sha256(path.read_bytes()).hexdigest(), flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/raw/nf_pilot"))
    retrieve(parser.parse_args().out)
