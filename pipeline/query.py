"""Read rows out of a normalized.json without jq, so the pipeline needs nothing
but Python on any machine.

  python pipeline/query.py benchmark-data/20260904/artificial-analysis/normalized.json --model "Grok 4.6"
  python pipeline/query.py benchmark-data/20260904/vals-ai/normalized.json --benchmark "Code Migration" --limit 20

Filters are case-insensitive substring matches and combine with AND. Every
filter is optional; with none, you get the first rows as they are stored.
"""
import argparse
import json
import sys
from pathlib import Path

FIELDS = ("model", "benchmark", "metric", "score", "stderr", "cost_usd", "rank")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--model", default="")
    ap.add_argument("--benchmark", default="")
    ap.add_argument("--metric", default="")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", action="store_true", help="print matching rows as JSON")
    a = ap.parse_args()

    rows = [r for r in json.loads(Path(a.path).read_text(encoding="utf-8")) if isinstance(r, dict)]
    for field, want in (("model", a.model), ("benchmark", a.benchmark), ("metric", a.metric)):
        if want:
            rows = [r for r in rows if want.lower() in str(r.get(field, "")).lower()]

    if a.json:
        print(json.dumps(rows[:a.limit], indent=2, ensure_ascii=False))
    else:
        for r in rows[:a.limit]:
            print("  ".join(f"{f}={r[f]}" for f in FIELDS if r.get(f) is not None))
    print(f"\n{len(rows)} rows matched, showing {min(len(rows), a.limit)}.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
