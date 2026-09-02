import json
import datetime

BASE = r"C:/Users/gurkan/Desktop/llm-benchmark-analysis/benchmark-data/20260915/benchlm"

with open(BASE + "/raw.json", encoding="utf-8") as f:
    raw = json.load(f)

records = []


def parse_release_label(label):
    if not label:
        return None
    try:
        return datetime.datetime.strptime(label, "%b %d, %Y").date().isoformat()
    except ValueError:
        return None


models_detail = raw["modelsDetail"]

# --- per-benchmark leaderboard rows ---
benchmark_leaderboard_rows = 0
for slug in sorted(raw["benchmarks"].keys()):
    bm = raw["benchmarks"][slug]
    b = bm["benchmark"]
    benchmark_name = f"{b['name']} — {b['fullName']}"
    metric = b.get("format") or b.get("metric") or "Score"
    source_url = f"https://benchlm.ai/benchmarks/{b['pageSlug']}"
    leaderboard = bm.get("leaderboard") or []
    for i, entry in enumerate(leaderboard):
        score = entry.get("score")
        if score is None:
            continue
        rec = {
            "model": entry.get("model"),
        }
        provider = entry.get("creator")
        if provider is not None:
            rec["provider"] = provider
        rec["benchmark"] = benchmark_name
        rec["metric"] = metric
        rec["score"] = score
        rec["rank"] = i + 1

        model_slug = entry.get("slug")
        detail = models_detail.get(model_slug) if model_slug else None
        cost_usd = None
        context_window = entry.get("contextWindow")
        date = None
        if detail:
            pricing = detail.get("pricing") or {}
            cost_usd = pricing.get("blendedPrice")
            context_window = pricing.get("contextWindow") or context_window
            date = parse_release_label((detail.get("model") or {}).get("releaseLabel"))
        if cost_usd is not None:
            rec["cost_usd"] = cost_usd
        if context_window is not None:
            rec["context_window"] = context_window
        if date is not None:
            rec["date"] = date
        rec["source_url"] = source_url
        records.append(rec)
        benchmark_leaderboard_rows += 1

# --- Overall / Category / Elo rows from homepage leaderboard ---
index_page = raw["pages"]["index"]
homepage = index_page["homepageData"]
leaderboard = homepage["leaderboard"]
rows = leaderboard["rows"]
category_labels = leaderboard["categoryLabels"]
category_keys = list(category_labels.keys())

# Overall: sort rows with non-null displayScore (col 26, the ranking-eligible
# set) by full-precision score (col 27) descending, matching the
# 20260906 convention.
overall_candidates = [r for r in rows if r[26] is not None]
overall_candidates.sort(key=lambda r: r[27], reverse=True)

overall_rows_scored = 0
for rank, r in enumerate(overall_candidates, start=1):
    rec = {
        "model": r[1],
    }
    if r[3] is not None:
        rec["provider"] = r[3]
    rec["benchmark"] = "Overall (bench-align-v5 composite index)"
    rec["metric"] = "Composite index score 0-100"
    rec["score"] = r[26]
    rec["rank"] = rank
    if r[12] is not None:
        rec["cost_usd"] = r[12]
    if r[8] is not None:
        rec["context_window"] = r[8]
    if r[17] is not None:
        rec["date"] = r[17]
    if r[10] is not None:
        rec["input_price_usd_per_mtok"] = r[10]
    if r[11] is not None:
        rec["output_price_usd_per_mtok"] = r[11]
    if r[13] is not None:
        rec["tokens_per_second"] = r[13]
    if r[14] is not None:
        rec["latency_ttft_s"] = r[14]
    rec["source_url"] = f"https://benchlm.ai/models/{r[2]}"
    records.append(rec)
    overall_rows_scored += 1

# Category indexes
category_row_count = 0
for cat_idx, cat_key in enumerate(category_keys):
    cat_label = category_labels[cat_key]
    cat_candidates = [r for r in rows if r[30] is not None and r[30][cat_idx] is not None]
    cat_candidates.sort(key=lambda r: r[30][cat_idx], reverse=True)
    for rank, r in enumerate(cat_candidates, start=1):
        rec = {
            "model": r[1],
        }
        if r[3] is not None:
            rec["provider"] = r[3]
        rec["benchmark"] = f"Category index: {cat_label}"
        rec["metric"] = "Category index score 0-100"
        rec["score"] = r[30][cat_idx]
        rec["rank"] = rank
        if r[12] is not None:
            rec["cost_usd"] = r[12]
        if r[8] is not None:
            rec["context_window"] = r[8]
        if r[17] is not None:
            rec["date"] = r[17]
        rec["source_url"] = f"https://benchlm.ai/{cat_key}"
        records.append(rec)
        category_row_count += 1

# Elo
elo_candidates = [r for r in rows if r[15] is not None]
elo_candidates.sort(key=lambda r: r[15], reverse=True)
elo_rows = 0
for rank, r in enumerate(elo_candidates, start=1):
    rec = {
        "model": r[1],
    }
    if r[3] is not None:
        rec["provider"] = r[3]
    rec["benchmark"] = "Elo (leaderboard Elo column)"
    rec["metric"] = "Elo rating"
    rec["score"] = r[15]
    rec["rank"] = rank
    if r[12] is not None:
        rec["cost_usd"] = r[12]
    if r[8] is not None:
        rec["context_window"] = r[8]
    if r[17] is not None:
        rec["date"] = r[17]
    rec["source_url"] = "https://benchlm.ai/"
    records.append(rec)
    elo_rows += 1

with open(BASE + "/normalized.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False)

print(json.dumps({
    "total_records": len(records),
    "benchmark_leaderboard_rows": benchmark_leaderboard_rows,
    "overall_leaderboard_rows_scored": overall_rows_scored,
    "overall_leaderboard_rows_total": len(rows),
    "category_index_rows": category_row_count,
    "elo_rows": elo_rows,
}, indent=2))
