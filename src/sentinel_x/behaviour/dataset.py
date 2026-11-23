"""Trace-level inputs, provenance and overlap control."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
import os
import random
import tempfile
import urllib.request
import zipfile

ARCHIVE_URL = ("https://raw.githubusercontent.com/verazuo/a-labelled-version-of-the-ADFA-LD-dataset/"
               "68bedf561f7b7abe9954a3ddc22dbf24c0d42372/ADFA-LD.zip")
ARCHIVE_SHA = "58d625470749344843a7f730b0875ce9b8769f6fa48f18dc4a92bd07c342ead5"


@dataclass(frozen=True)
class Trace:
    name: str
    partition: str
    family: str
    tokens: tuple

    @property
    def label(self):
        return int(self.family != "benign")


def digest(tokens):
    return sha256(" ".join(map(str, tokens)).encode("ascii")).hexdigest()


def acquire(path):
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(ARCHIVE_URL, timeout=45) as response:
            content = response.read(3_000_001)
        if sha256(content).hexdigest() != ARCHIVE_SHA:
            raise ValueError("unverified ADFA-LD download")
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            f.write(content)
        os.replace(f.name, path)
    with path.open("rb") as f:
        if sha256(f.read(3_000_001)).hexdigest() != ARCHIVE_SHA:
            raise ValueError("cached ADFA-LD archive has unexpected checksum")
    return path


def adfa(path):
    sections = {"Training_Data_Master": "development", "Validation_Data_Master": "test",
                "Attack_Data_Master": "test"}
    with zipfile.ZipFile(acquire(path)) as z:
        for member in sorted(z.namelist()):
            parts = PurePosixPath(member).parts
            if (len(parts) < 3 or parts[0] != "ADFA-LD" or parts[1] not in sections or
                    not parts[-1].endswith(".txt")):
                continue
            raw = z.read(member).split()
            if not raw or any(not item.isdigit() for item in raw):
                raise ValueError(f"unexpected syscall data in {member}")
            family = parts[2].rsplit("_", 1)[0] if parts[1] == "Attack_Data_Master" else "benign"
            yield Trace(member, sections[parts[1]], family, tuple(map(int, raw)))


def fixture(seed=216):
    rng = random.Random(seed)
    for i in range(270):
        tokens = tuple(t for _ in range(rng.randrange(5, 15))
                       for t in (0, rng.choice((1, 2, 3)), 4))
        family = "benign"
        if i >= 200:
            shuffled = list(tokens)
            rng.shuffle(shuffled)
            tokens = tuple(shuffled)
            family = "permuted_order"
        yield Trace(f"fixture-{i}", "development" if i < 135 else "test", family, tokens)


def partition(records):
    dev, held = {}, defaultdict(list)
    audit = Counter()
    for row in records:
        key = digest(row.tokens)
        audit["input_" + row.partition] += 1
        if row.partition == "development" and row.label == 0:
            dev.setdefault(key, row)
        elif row.partition == "test":
            held[key].append(row)
        else:
            raise ValueError("invalid development record or partition")
    audit["development_duplicates_removed"] = audit["input_development"] - len(dev)
    train, calibration, test = [], [], []
    for i, key in enumerate(sorted(dev)):
        (train if i % 5 else calibration).append(dev[key])
    for key, rows in sorted(held.items()):
        if key in dev:
            audit["heldout_overlap_removed"] += len(rows)
        elif len({r.label for r in rows}) > 1:
            audit["heldout_conflicting_removed"] += len(rows)
        else:
            audit["heldout_duplicates_removed"] += len(rows) - 1
            test.append(min(rows, key=lambda r: r.name))
    return train, calibration, test, dict(audit)
