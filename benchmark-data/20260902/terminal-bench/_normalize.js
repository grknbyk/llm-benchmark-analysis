const fs = require("fs");
const dir = "C:/Users/gurkan/Desktop/llm-benchmark-analysis/benchmark-data/terminal-bench";

const raw = JSON.parse(fs.readFileSync(dir + "/raw.json", "utf8"));

function label(v) {
  if (v === null || v === undefined) return undefined;
  if (typeof v === "string") return v || undefined;
  if (typeof v === "object" && typeof v.label === "string") return v.label;
  return undefined;
}

function put(rec, key, value) {
  if (value === undefined || value === null || value === "") return;
  rec[key] = value;
}

const records = [];

for (const req of raw.requests) {
  const board = req.response.leaderboard;
  for (const row of req.response.rows) {
    const md = row.metadata || {};
    const mx = row.metrics || {};
    const rec = {};

    put(rec, "model", label(md.model_display) || (md.model_names || [])[0]);
    put(rec, "provider", label(md.model_org) || (md.model_providers || [])[0]);
    put(rec, "agent", label(md.agent_display) || md.agent_name);
    put(rec, "agent_org", label(md.agent_org));
    put(rec, "agent_version", md.agent_version === "unknown" ? undefined : md.agent_version);
    put(rec, "reasoning_effort", md.reasoning_effort);
    put(rec, "benchmark", board.title);
    put(rec, "benchmark_version", req.version);
    rec.metric = "accuracy";
    put(rec, "score", mx.accuracy);
    put(rec, "score_ci95_half_width", mx.accuracy_ci95_half_width);
    put(rec, "rank", row.rank);
    put(rec, "cost_usd", mx.total_cost_usd);
    put(rec, "total_tokens", mx.total_tokens);
    put(rec, "n_trials", row.n_trials || mx.n_trials || undefined);
    put(rec, "date", md.release_date || md.date);
    put(rec, "verified", md.verified);
    rec.source_url = req.source_url;

    records.push(rec);
  }
}

fs.writeFileSync(dir + "/normalized.json", JSON.stringify(records, null, 2) + "\n");

const meta = {
  source_url: "https://www.tbench.ai/",
  scraped_at: new Date().toISOString(),
  benchmarks_captured: raw.requests.map(r => ({
    version: r.version,
    title: r.response.leaderboard.title,
    package: r.request_body.package,
    leaderboard_name: r.request_body.name,
    rows: r.response.rows.length,
    source_url: r.source_url
  })),
  row_count: records.length,
  extraction_method:
    "chrome-devtools MCP: observed the POST XHR to the Supabase edge function " +
    "https://ofhuhcpkvzjlejydnvyd.supabase.co/functions/v1/leaderboard-read on https://www.tbench.ai/, " +
    "enumerated the four version options in the page's Benchmark combobox by clicking each one while " +
    "recording the outgoing request bodies, then re-issued each POST from the page context (same origin, " +
    "no auth required) and saved the JSON responses verbatim as raw.json. normalized.json is derived from " +
    "raw.json by a local Node script (_normalize.js).",
  notes: [
    "No CSV/JSON static asset exists; all leaderboard data comes from the leaderboard-read edge function. Payloads were saved verbatim, not DOM-scraped.",
    "The site's Benchmark selector offers exactly four versions: 4.0, 3.0, 2.1, 2.0. Terminal-Bench 1.0 is listed on /benchmarks as a released dataset but has no leaderboard: /leaderboard/terminal-bench/1.0 redirects to the unversioned home page and the edge function returns not_found for every 1.0 name/package combination tried.",
    "Terminal-Bench Challenges and Terminal-Bench Science are separate datasets listed on /benchmarks; neither appears in the leaderboard selector on tbench.ai (Science has its own site) and neither was captured.",
    "Agent/harness is a first-class field (metadata.agent_display) and is kept separate from the model name. reasoning_effort is also kept separate.",
    "Metric is the leaderboard 'accuracy' field, displayed on the site as RESOLUTION RATE, in percent (0-100). score_ci95_half_width is the +/- 95% CI half width in percentage points.",
    "context_window is not published by this site, so the field is omitted from every record.",
    "cost_usd / total_tokens are the total across all trials for that run, as published. Terminal-Bench 2.0 rows publish accuracy only, so cost, tokens and trial counts are omitted for them; n_trials is reported as 0 there and was treated as not-provided rather than a real zero.",
    "Verified via the browser only; no curl fallback was needed. The 4.0 payload re-fetched from the page (15123 bytes) matches the byte length of the response the browser itself made on page load (reqid 39).",
    "Rank values come from the source payload and contain ties (e.g. two rank-9 rows in 4.0)."
  ]
};

fs.writeFileSync(dir + "/meta.json", JSON.stringify(meta, null, 2) + "\n");

const missing = records.filter(r => !r.model || !r.agent || r.score === undefined);
console.log("records:", records.length, "missingCore:", missing.length);
console.log("perVersion:", meta.benchmarks_captured.map(b => b.version + "=" + b.rows).join(" "));
console.log("sample:", JSON.stringify(records[0]));
console.log("sample2:", JSON.stringify(records[records.length - 1]));
