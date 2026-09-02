"""Print every metric available in a scrape folder, so step 0 picks role inputs
from what the data actually has rather than from memory.

Run: python pipeline/catalogue.py benchmark-data/20260904 [--min-models 5]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def clip(s, n):
    return s if len(s) <= n else s[:n - 1] + "…"


def rows(path):
    with open(path, encoding="utf-8") as fh:
        for r in json.load(fh):
            if isinstance(r, dict):
                yield r


def main(folder, min_models):
    base = Path(folder)
    counts = defaultdict(set)
    for site in sorted(p.name for p in base.iterdir() if (p / "normalized.json").is_file()):
        for r in rows(base / site / "normalized.json"):
            key = (site, r.get("benchmark") or "-", r.get("metric") or "-")
            counts[key].add(r.get("model"))

    kept = [(k, len(v)) for k, v in counts.items() if len(v) >= min_models]
    kept.sort(key=lambda kv: (kv[0][0], -kv[1], kv[0][1]))
    site_now = None
    for (site, bench, metric), n in kept:
        if site != site_now:
            print(f"\n=== {site} ===")
            site_now = site
        print(f"{clip(bench, 58):<58}  {clip(metric, 26):<26}  {n:>4} models")
    print(f"\n{len(kept)} metrics with >= {min_models} models, "
          f"{len(counts) - len(kept)} below the floor and hidden.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console is cp1254
    args = sys.argv[1:]
    floor = 5
    if "--min-models" in args:
        i = args.index("--min-models")
        floor = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        sys.exit("usage: catalogue.py benchmark-data/<YYYYMMDD> [--min-models N]\nprints every site | benchmark | metric the scrape folder carries, with model counts.")
    main(args[0], floor)
