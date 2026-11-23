"""Acquire and prepare the checksummed benchmark or generate a local smoke fixture."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sentinel_x.data.prepare import prepare

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "research"], default="research")
    parser.add_argument("--full", action="store_true", help="Keep every eligible vector instead of bounded sample")
    args = parser.parse_args()
    print(prepare(ROOT, args.mode, args.full))
