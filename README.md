# LLM benchmark analysis

Scraped leaderboard data from 10 benchmark sites and a shortlist report for
ERP and Oracle APEX development.

- Report: [reports/20260902/erp-oracle-apex-model-shortlist.md](reports/20260902/erp-oracle-apex-model-shortlist.md)
  (interactive HTML version alongside it)
- Data: `benchmark-data/<YYYYMMDD>/<site>/` with `raw.json`, `normalized.json`, `meta.json` (20260902, 20260903 and 20260904; the report reads 20260904)
- Rebuild charts and HTML: `make_charts.py` then `build_html.py` in the report folder
