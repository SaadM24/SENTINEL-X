"""Cache the byte-pinned academic NetFlow v2 mirrors for the external-corpus study."""
import argparse
import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

ARCHIVES = {
    "nf-unsw-nb15-v2": "c686c1eb7057e42d3ffff3797277804687b9780b3becb7185cb9c66811cdbf1c",
    "nf-cse-cic-ids2018-v2": "ac38f3a072882f0d06395ad4ca1a6d84d2844411fdb497cd9ddd2b06ac1b9719",
}
BASE = "https://www.kaggle.com/api/v1/datasets/download/asdibnufvsd/"


def check(path, expected):
    with path.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != expected:
            raise ValueError(f"Checksum mismatch: {path.name}. See docs/protocols/DATASET_AUDIT.md.")


def fetch(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for slug, expected in ARCHIVES.items():
        target = directory / (slug + ".zip")
        if target.exists():
            check(target, expected)
            continue
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            local = Path(tmp) / target.name
            with urllib.request.urlopen(BASE + slug, timeout=180) as source, local.open("wb") as f:
                shutil.copyfileobj(source, f, length=1 << 20)
            check(local, expected)
            os.replace(local, target)
        print(target)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, default=Path("data/raw/nf-v2"))
    fetch(p.parse_args().directory)
