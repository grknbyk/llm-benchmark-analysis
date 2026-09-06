# Per-site scrape notes

Each site's own `meta.json` in the most recent `benchmark-data/<date>/<site>/`
is the authoritative method, because it records what actually worked that day.
This file is the accumulated memory of the traps behind those methods, so an
agent knows what to watch for before it starts.

Read the entry for your site. Ignore the rest.

## artificial-analysis

`https://artificialanalysis.ai`

Data lives in React Server Component flight chunks. `window.__next_f` is
emptied after hydration, so read the `self.__next_f.push(...)` `<script>` tags
out of the DOM (around 53 of them) and eval them with a stubbed `push()` to
capture the chunks. Then balanced-bracket-extract the `"models":[...]` array
and parse it in the page.

Two traps:

- The payload contains **two** `"models":[` arrays. The first is a slim picker
  list with name, slug and effort only. The second carries every benchmark and
  metric. Confirm you took the second by checking for `intelligenceIndex` and
  `gpqa` keys nearby.
- The missing-value sentinel changed from the literal string `"$undefined"` to
  plain JSON `null` on 2026-09-04. Treat both as absent.

Fields come and go between days: `cweBench` appeared all-null on 09-03 and had
vanished by 09-04, while eight per-task cost and time metrics appeared on
09-04. Record additions in `meta.json` rather than trimming to yesterday's shape.

Nested breakdown objects (`gdpvalBreakdown`, `omniscienceBreakdown`,
per-eval token counts) stay unflattened. Note that in `meta.json`.

This is the usual primary source, because it is the only site publishing price
and latency next to quality. Its coding index, agentic index, AA-LCR,
Omniscience accuracy and non-hallucination rate, blended 3:1 price, end-to-end
time and time to first token carry most role indexes. Which of them a given
profile actually uses is the profile's business, not this file's.

## vals-ai

`https://www.vals.ai/benchmarks`, about 43 benchmark slugs.

The page renders several `<astro-island>` elements that each carry a
`benchmarkView` key. Only the one holding `benchmarkView.default` has `stderr`
and the subtask breakdowns; a summary-card island parses cleanly and silently
drops them. Diff against the previous schema to confirm `stderr` survived.

`vals.ai` sends permissive CORS headers, so absolute-URL `fetch()` succeeds
even when another agent has stolen the page pointer. That makes this site the
least race-prone of the ten.

`rsi_index` has no data island, which once made it look frozen. It is not: it
updated on 2026-09-04 with new scores and 8 models per task instead of 3. Scrape
it every run and check the UPDATED stamp on the page rather than carrying the
previous day forward.

Slugs get renamed rather than added: `reverse_eng` now 302-redirects to
`srebench`. Some benchmarks drop off the `/benchmarks` nav while their pages
still resolve, so fetch known slugs directly rather than trusting the nav.

Vals supplies Code Migration and CorpFin v2, the two ERP proxies. Code
Migration is the whole basis of the batch index, so a run that loses `stderr`
here is a failed run.

## deepswe

`https://deepswe.datacurve.ai/`

Four JSON artifacts, fetched same-origin from the page:
`v1.1/leaderboard-live.json`, `v1/leaderboard-live.json`, `v1/leaderboard.json`,
`v1.1/v1-delta.json`. A fifth, `v1.1/tasks.json`, holds per-task metadata and
was found later; check for new artifacts each run.

The artifacts carry a `generated_at` stamp. When it has not moved, the payload
is byte-identical to the previous day and the honest report is "unchanged",
not a fabricated diff.

Keep every field per record: `pass@1`, `pass@4`, `cost_usd`,
`mean_output_tokens`, `mean_agent_steps`, `ci_half_pct`, `n_tasks_attempted`,
`n_runs`, `reasoning_effort`, `config`, `rank`. Cost per task and agent steps
are report columns; steps are what makes an efficient model visible.

Seven models carry a client-side cost adjustment from an earlier run. Carry it
forward while their underlying rows are unchanged, and note it.

The site has a data view the artifact probe does not reach, because it is a
page route rather than a file:

```
https://deepswe.datacurve.ai/data/v1.1?hm_stat=avg_duration_seconds&pivot=true
```

`hm_stat` selects which per-run statistic the page pivots. Read it each run and
list the values it offers, because that list is the site's own statement of
which numbers it considers publishable. Two things follow from it:

- The artifact carries both `mean_` and `median_` variants of duration, steps,
  cost and tokens. The page publishes the mean. A report that shows the median
  and calls it the site's figure disagrees with the site.
- A statistic that appears in `hm_stat` and not in the artifact is a gap. Probe
  for it before assuming the artifact is complete.

## livebench

`https://livebench.ai/`

CSV and JSON artifacts for the table, categories and cost. A release selector
offers `2024-06-24 · v1` and `2026-06-25 · latest`; check whether a newer
release string exists rather than assuming.

Capture every category column: overall, reasoning, coding, agentic coding,
mathematics, data analysis, language, instruction following, plus cost, org and
open-weights flags. Include finetunes.

The finetune flag has no CSS class, but it can be derived structurally by
toggling the finetune switch and diffing the two model sets. Do that rather than
matching against the previous scrape's finetune names, which was the old
fallback. The CSVs also carry more model ids than the leaderboard renders, two
on 2026-09-06; keep the extras in `raw.json` only and say so.

The 23-column per-subtask CSV stays verbatim in `raw.json` and is not expanded
into `normalized.json`.

## lmarena

`https://arena.ai/leaderboard/...`, 124 leaderboards across 12 arenas.

The `fetch(url, {headers: {RSC: "1"}})` trick that worked on 2026-09-02 returns
404 for every route since 09-03. The method that works now: fetch the plain
server-rendered HTML per route, pull the `self.__next_f.push([...])` flight
chunks out of it with a bracket-depth-aware scan, unescape with `new Function`,
then brace-match the `"leaderboard":{` or `"snapshot":{` object.

Two URL shapes do not follow the pattern: `image-to-code` lives at
`/leaderboard/code/image-to-webdev` with no `/overall` suffix, and
`video-to-video` at `/leaderboard/video-edit`.

The agent arena uses a different shape, `rows` / `avgScore` / `rankSpread`
instead of `entries[]` / `rating`. Normalize it with metric `agent_score` and
benchmark slugs `arena-agent-<category>`.

Documents streamed through Suspense sometimes come back truncated. Retry until
the end marker is present rather than parsing what arrived.

Scores drift daily because it is a live Elo board. Drift is not an error.

Compare the hostname exactly. A guard written as
`hostname.includes('arena.ai')` also passes on `www.designarena.ai`, so two
agents that swap the page pointer can write one site's data into the other's
folder without the guard firing.

Scope trap: asking only for text, code and vision yields 90 of the 124
leaderboards. Ask for every arena.

The file uses two naming conventions at once. The text and webdev boards key on
slugs, `claude-opus-5-max`. The agent boards key on display names, `Claude Opus
5 (High)`. Both collapse to the same join key, so a de-duplicating join keeps
one of them and silently drops every board the other one carried.

That is why LMArena cannot be `scoring_sources[0]`. The first source defines the
candidate universe, and here it would define it with 694 model strings including
text-to-video and image-edit entries, then keep the alias with no webdev row.
Use it as a second or third source, joined by name, and check the join table.

## terminal-bench

`https://www.tbench.ai/`

Data comes from a Supabase edge function, `leaderboard-read`, called with POST
bodies of the form `{package, name}`. Four versions exist: 4.0, 3.0, 2.1, 2.0.
The exact bodies are recorded in the previous `meta.json`.

There is no `<select>` version picker in the DOM. Speculative POSTs for 5-0-0,
4-1-0, 3-1-0 and `terminal-bench-2-2/main` all return 404, which is how you
confirm the version list rather than guessing.

Version 4.0 is much harder than 2.1. A model at 89 on 2.1 can sit at 19 on 4.0,
so never compare across versions without naming which one.

## arc-prize

`https://arcprize.org/leaderboard`

The verified leaderboard comes from JSON endpoints: datasets, providers,
models, evaluations, and leaderboard v1, v2 and v3. The community leaderboard
has no API and is reconstructed by regex-extracting and bracket-matching the
Next.js RSC payload in `self.__next_f`.

Costs arrive as either `cost_usd` or `cost_usd_total` depending on the
leaderboard; keep both names.

Rank shifts here are usually an artefact of new higher-scoring rows displacing
old ones, not real movement. Check score deltas before reporting a change.

The site has had display bugs of its own, such as a model name serialized as
the boolean `true`. Report the fix rather than silently absorbing it.

No model in this report's shortlist has ever appeared here. It is provenance,
not a source of numbers.

## epoch-ai

`https://epoch.ai/benchmarks`

Roughly 70 endpoints: four core files plus 66 external per-benchmark CSVs.
This is the slowest site of the ten.

The benchmark-to-metric-column mapping is not published. It was reverse
engineered from the previous `normalized.json` by collecting unique
benchmark and metric pairs, then applied to freshly fetched CSVs behind a
schema-drift guard. Keep the guard; when it fires, the mapping needs redoing.

Model identity lives in different columns per CSV. Without `Name` and `Agent`
fallbacks, benchmarks such as GSM8K, OS World, BoolQ and MMLU undercount by up
to 65%. Row counts that drop sharply against the previous day mean the fallback
broke, not that the site changed.

Orphan tasks appear in `benchmarks.csv` with no public benchmark card, for
example `FrontierMath-Erdos`. Include them and note the pattern.

## design-arena

`https://www.designarena.ai/leaderboard`

About 33 category endpoints, plus `/api/registry` for the model list with
pricing and provider, plus an `llm-scores` endpoint.

A model can sit in the registry with no leaderboard rows at all, which is what
"announced but not yet voted on" looks like. Report the registry entry and the
absence separately.

Seven categories have been persistently empty (music, sts, worldmodel,
agon_dataviz, agentic_3d, fullstack_gamedev, agon_html). Sweep them anyway and
confirm.

Elo, votes, wins and losses drift daily from ordinary voting. Expect most rows
to change slightly.

Node `fetch` from Bash works against this host and is the recorded fallback for
the bulk sweep when page contention is bad. Cross-check one endpoint through
the browser to prove the payloads match.

## benchlm

`https://benchlm.ai/`

A Next.js static site. Data comes from `/_next/data/<buildId>/...` for the
index, models, benchmarks, pricing and speed pages, plus every individual
benchmark page and model page. Roughly 410 of each.

The `buildId` changes between days and must be rediscovered every run.

Payload shapes move: model detail data migrated into `pageProps.pageData`, and
the homepage leaderboard from a bare array into `leaderboard.rows`. Unwrap both
to keep `raw.json`'s shape stable across days.

The `/models` listing page undercounts the true catalogue. Harvest slugs from
`/sitemap.xml` and its `sitemap-0..17.xml` children instead.

Fetching 800-plus pages as one concurrency-pooled `fetch()` inside a single
`evaluate_script` is far more reliable than many small batches, because each
round trip is another chance to lose the page pointer.

This site mirrors other benchmarks rather than running its own, so treat it as
corroboration and prefer the original source when they disagree.
