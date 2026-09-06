---
name: refresh-benchmarks
argument-hint: [stack, comma separated, e.g. "Svelte 5, SvelteKit, PostgreSQL, SPA for real estate"]
description: Pick the best LLMs for a given technology stack from ten public leaderboards. Scrapes all ten sites into a dated folder with ten parallel agents, derives weighted role indexes from the stack the user names, researches the skills and MCP servers around that stack with last30days, writes a shortlist report and deploys it as a single squashed commit. Use this whenever the user asks to refresh, re-scrape, re-fetch, update or re-run benchmark data or a shortlist report, says "reloop", "fetch the 10 sites again", "yeni veri cek", "rapor guncelle", asks which model to use for a stack, or asks whether a newly released model has reached the leaderboards. Also use it for one piece of the pipeline, such as scraping without deploying or rebuilding charts after a manual data fix.
---

# Pick models for a stack

The argument is the target stack, for example `Oracle APEX, Oracle DB, JS,
HTML/CSS, ERP` or `Svelte 5, SvelteKit, PostgreSQL, SPA for real estate`. It
decides the roles, the benchmark proxies and the report prose. Everything else
in the pipeline is the same whatever the stack is.

## Confirm before anything runs

This pipeline spawns up to fifteen agents and can take half an hour. Ask first,
every time, argument or no argument. Spawning an agent before the user has
confirmed is the one failure mode that wastes their money instead of yours.

Gather the two facts, then ask in a single question:

```bash
python -c "import glob,json;[print(f, json.load(open(f))['stack']) for f in glob.glob('reports/*/profile.json')]"
ls benchmark-data/
```

**Which profile.** Offer every saved `stack` string as an option, plus "a new
stack" last. A saved profile skips step 0 and turns a 30 minute run into a 10
minute one. When the user passed a stack as the argument, still show it back as
the pre-selected option rather than starting on it: an argument is a proposal,
not a confirmation.

**Which data.** If `benchmark-data/<today>` is missing, say so and give the
newest folder that does exist with its date. Reusing two day old leaderboard
numbers is often the right call and always the user's call. Never fall back to
an older folder silently, and never start a scrape without being asked to.

Only after the answer lands do you spawn anything.

Read `references/sites.md` before spawning scrape agents. It holds the
per-site extraction method and the trap each site sets, which is the
difference between a clean run and four hours of retries.

Three skills are load bearing here and none is a suggestion. `adhd` derives the
roles in step 0. `last30days` researches the stack tooling in step 3.
`report-prose` is the editorial pass in step 4. A run
that skips them produces a generic report that could have been written without
the data.

## Shape of the pipeline

```
step 0  derive the profile          1 min
step 1  scrape ten sites            20-30 min   |  ten agents, parallel
step 3  research stack tooling      5-10 min    |  runs alongside step 1
step 2  build indexes and charts    2 min
step 4  write the report            5 min
step 5  deploy                      1 min
```

Steps 1 and 3 do not depend on the profile, so start them first and derive the
profile while they run. The numbering follows the data, not the clock.

## Layout

```
benchmark-data/<YYYYMMDD>/<site>/{raw,normalized,meta}.json   one folder per scrape day, shared by every stack
reports/<YYYYMMDD>-<slug>/profile.json                        the stack profile, the contract for everything downstream
reports/<YYYYMMDD>-<slug>/<slug>-model-shortlist.md           the report
reports/<YYYYMMDD>-<slug>/results.json                        every raw value, every role formula, the picks
reports/<YYYYMMDD>-<slug>/{master,glance}-table.md            paste-ready tables written by the engine
reports/20260902/                                             the first ERP report, folder name is historical, do not rename
pipeline/catalogue.py                                         prints every metric available in a data folder
pipeline/make_charts.py                                       joins the sources, scores the roles, draws the charts
pipeline/build_html.py                                        markdown to HTML, tooltips, rotated wide headers
pipeline/build_index.py                                       rebuilds index.html from the reports that exist
pipeline/query.py                                             read rows out of a normalized.json
index.html                                                    lists every report
```

The ten sites: `artificial-analysis`, `vals-ai`, `deepswe`, `livebench`,
`lmarena`, `terminal-bench`, `arc-prize`, `epoch-ai`, `design-arena`,
`benchlm`.

All ten normalize to the same long shape, one row per
`{model, benchmark, metric, score}`. That is why any site can feed a role
index. Which ones actually do is a property of the profile, not of the
pipeline. The ERP profile scores from Artificial Analysis, Vals and DeepSWE and
treats the other seven as provenance. A frontend profile will want design-arena
Elo and the LMArena webdev boards as scoring sources instead.

## Step 0: derive the profile

Ask the data what exists before deciding anything:

```bash
uv run --with pandas python pipeline/catalogue.py benchmark-data/<today>
```

It prints every `site | benchmark | metric` triple with the number of models
carrying it. A metric covering three models cannot rank ten, so coverage is the
first filter.

Then write `reports/<today>-<slug>/profile.json`:

```json
{
  "stack": "Svelte 5, SvelteKit, PostgreSQL, SPA for real estate",
  "slug": "svelte-spa",
  "data": "benchmark-data/20260906",
  "title": "Svelte / SvelteKit model shortlist",
  "scoring_sources": ["artificial-analysis", "design-arena", "lmarena"],
  "metrics": {
    "coding": {"site": "artificial-analysis", "benchmark": "Artificial Analysis Coding Index", "metric": "score"},
    "price": {"site": "artificial-analysis", "metric": "blended_price_per_1m_usd_3to1", "unit": "$/1M"},
    "webdev": {"site": "lmarena", "benchmark": "webdev-overall-raw", "metric": "arena_score", "scale": 1}
  },
  "roles": [
    {"name": "Component authoring", "weights": {"coding": 0.40, "webdev": 0.30, "nh": 0.30}}
  ],
  "cheap_alternative": {"max_points_behind": 5.0, "min_price_ratio": 3.0}
}
```

Do not pick the roles off the top of your head. Run the `adhd` skill on the
question "what distinct jobs does this stack actually involve, and what would
each one need from a model", then converge its output into two to four roles.
Roles are the one decision the whole report rests on, and the first three that
come to mind are always the same three. This step is not optional.

Rules that keep a derived profile honest:

- Two to four roles, named after the work the user described. "Component
  authoring" and "Schema and migration" tell a reader what the column means.
  "Role B" does not.
- Weights inside a role sum to 1.00. Never renormalise a weight to paper over a
  missing input.
- Every metric in `metrics` must appear in the catalogue output. If a role wants
  something the data does not have, drop that term, redistribute across the rest
  and record the gap in `profile.json` under `gaps`.
- Give every metric with a real unit a `unit` field, such as `$/1M`, `$/task`,
  `s` or `%`. It reaches the table headers and the chart tooltips. A column of
  bare numbers that turn out to be seconds is worse than no column.
- No invented proxy. Code Migration stands in for ERP legacy work because the
  benchmark literally migrates code. When nothing on any of the ten sites
  matches the stack's core task, say so and build the role from coding and
  agentic alone.
- `overall` is added automatically and stays stack independent, so reports stay
  comparable: 0.30 coding + 0.25 agentic + 0.15 long context + 0.15
  non-hallucination + 0.15 accuracy.

Show the derived roles to the user in five lines while the agents run. A wrong
weight caught at minute two costs nothing. Caught after the report is written,
it costs a rebuild.

## Step 1: scrape

Only run this when the confirmation gate said to. The data is stack independent,
so a populated folder for the chosen date means this step is already done.

Otherwise create the folder and spawn ten agents in ONE message so they run in
parallel, `subagent_type: "general-purpose"`, one site each. Do not pass a
`model`: the agents inherit the session model, which is what the user wants
unless they name one. Never Fable for scrape or search work.

Every agent prompt needs these parts, because leaving one out is what produces
a folder that looks fine and is quietly wrong:

- The site name, the previous day's folder as reference, the new folder as target.
- Read the previous `meta.json` in full for the method, and the first ~40 lines
  of the previous `normalized.json` for the record schema. Never read a whole
  `raw.json` or `normalized.json`; several are over 10 MB.
- Go deeper than last time: every benchmark, every metric, any field that was
  absent before and has values now, any benchmark added since. Add new fields
  rather than trimming to yesterday's shape, and list them in `meta.json`.
- Browser rules, verbatim below.
- Write all three files, `scraped_at` from the real clock in ISO UTC, plus a
  `changes_vs_<previous date>` note naming models added or removed and any
  schema drift.
- Verify and report: record counts old versus new, and the specific rows for the
  models the user is asking about. Absent means say absent. Never fabricate.
- Do not touch previous date folders, `reports/`, or another site's folder.

### Browser rules for every agent

Copy these into each prompt. They exist because ten agents share one browser and
one global "selected page" pointer.

- Never use any `mcp__claude-in-chrome__*` tool. That drives the user's own
  browser and is off limits unless the user asks for it directly.
- Use `chrome-devtools` MCP only. Call `list_pages` first, then open your own
  page with `new_page` using an isolated context named
  `<site>-rescrape-<YYYYMMDD>`.
- Before every `evaluate_script`, call `select_page` on your own id and check
  `location.href` inside the script. Issue `select_page` and `evaluate_script` as
  two tool calls in the same turn; split across turns, another agent wins the
  pointer in between.
- Compare the hostname exactly, never with `includes`. A guard written as
  `hostname.includes('arena.ai')` also passes on `www.designarena.ai`, which is
  how one site's data ends up in another site's folder.
- The href guard must `throw`, not return an error object. A guard that returns
  `{error: "wrong_page"}` gets written to the output file as if it were data, and
  the "Output saved" confirmation from `evaluate_script` will not warn you. Check
  the file size on disk after every save.
- Fetch JSON with the page's own `fetch()` inside `evaluate_script` and save
  through its `filePath` option. Node or curl from Bash is usually blocked, but it
  works for some hosts and is an accepted fallback where the previous `meta.json`
  records it.
- Close only pages you opened, and close them when the scrape finishes.

Expect roughly 20 to 60 wasted retries per agent from pointer contention. That is
normal and not a failure. If a site fails outright after several honest attempts,
report it and leave that folder absent rather than writing partial data.

Relay each agent's result to the user as it lands, one or two lines: record
counts, whether the models of interest appeared, and anything that changed shape.

## Step 3: research the tooling around the stack

Spawn these in the same message as the scrape agents. One agent per technology
named in the argument, plus one for agent tooling in general. Each one runs the
`last30days` skill on its own subject, which is also not optional: a plain web
search returns the same three blog posts every time, and the point of this
section is what moved recently. Each agent reports back:

- The official MCP server, if the vendor ships one, with its repository.
- Community skills and MCP servers people are actually using, with the date of
  the last commit.
- What changed in the last 30 days: a new release, a deprecation, a practice
  that flipped.

Two things keep this section trustworthy. Separate official from community and
say which is which, because a community server wearing a familiar name is the
oldest supply chain trick there is. And do not tell the user to install anything:
an MCP server is code that runs on their machine. Report what exists, how
maintained it looks, and let them decide.

If a technology returns nothing solid, write that it returned nothing. An empty
window is a finding.

## Step 2: build the indexes

The scoring sources share no key, so models are joined by normalized name. Print
the join table before scoring anything:

```
AA model                  -> vals            deepswe          join
Grok 4.6 (xhigh)          -> grok_4_6        grok-4.6         exact
Muse Spark 1.3 (xhigh)    -> -               -                AA only
```

A match below the confidence threshold is dropped, not guessed. A model that
matched only one source keeps that source's numbers and is excluded from any role
needing the others. Wrong joins are the worst failure this pipeline has, because
they look like data.

Which candidates enter: models carrying a price in the primary source, taken in
score order, deep enough to reach the cheap end of the market. A model with no
price cannot enter a price-weighted role.

Then run:

```bash
uv run --with matplotlib --with pandas --with plotly python pipeline/make_charts.py reports/<today>-<slug>/profile.json
```

It prints the join table and the full index table, then writes three artifacts
next to the profile:

- `results.json`, holding every raw benchmark value, the formula behind every
  role, the resulting scores and the picks. Anyone can re-derive a number from
  it without touching the scrapes.
- `master-table.md` and `glance-table.md`, ready to paste into the report.

**Every calculation belongs to the script.** Set the weights in
`profile.json`, then read what comes out. Do not add, average, rank or convert
a number by hand, not even to sanity-check one, because a number typed twice
is a number that eventually disagrees with itself. If a figure looks wrong,
fix the profile or the engine and run it again.

A model missing an input is excluded from that role, never imputed. That is why
some models have no batch score, and the report says so plainly instead of hiding
the gap.

**Cheap alternative rule.** For each role, the cheap column holds the
highest-scoring model that is within `max_points_behind` of the leader and at
least `min_price_ratio` times cheaper. Defaults are 5 points and 3x. When nothing
qualifies, the cell says so. No fixed dollar threshold, because a threshold set
today is wrong next month.

## Step 4: write the report

`BLUEPRINT.md` holds the page section by section. Follow it. What is below is
the short form plus the rules a writer gets wrong.

Sections in order, and the layout each one uses:

```
# <title>

## Read first                     full width, four blocks, nothing longer
   stack and data                 one sentence
   **the pick**                   two sentences, and why the leader may not be one
   **the frontier**               model, price, score, each named
   **what this cannot measure**   one sentence

## Indexes and picks              glance-table.md verbatim, one merged table
   index | weights | best model | cheap alternative
   one short paragraph: what is relative, what is left out

## Every model, every metric      master-table.md verbatim, full width
   sorts by any column, fills a gap three ways, shows ten rows

## <lead chart>                   full width, then the index chart beside it

## <Role name>                    chart left, table right, prose below both
   `0.30 a + 0.25 b + ...`        the formula, one line of monospace
   **Pick <model>.**              why, with the number that decided it
   **Cheaper: <model>**           what it costs in points, what it saves

## <cross-metric charts>          odd count: lead full width, rest paired
   what a task costs, how many turns, how long

## What changed since <date>      three bold-led blocks, each with both readings

## Stack tooling                  one subsection per technology, from step 3

## Caveats                        numbered

## References                     scoring sites, provenance, tooling sources
```

Rules that hold whatever the stack is:

- **Both tables come out of the engine.** Paste `glance-table.md` and
  `master-table.md`; never retype a cell. They stay plain markdown in the `.md`
  because that is what GitHub renders, and `build_html.py` adds the vertical
  headers, the site groups, the sorting and the fill control in the HTML.
- **Charts go two per row at most.** An odd count puts the lead chart on a full
  width row and pairs the rest. `build_html.py` reads that from the order the
  images appear, so put the chart that matters first.
- **A role section holds its own chart.** Put the image before the table and the
  builder makes the two columns.
- **Compression is the point.** Every block is a bold lead and two or three
  sentences. A reader who stops after the first screen should already know what
  to buy.
- **The opening is not a changelog.** What moved since the last run goes near
  the end, with both readings and both dates.

Verify before you write. Every number has to come from the new scrape:

```bash
python pipeline/query.py benchmark-data/<today>/artificial-analysis/normalized.json --model "Grok 4.6"
python pipeline/query.py benchmark-data/<today>/vals-ai/normalized.json --benchmark "Code Migration" --limit 20
```

Filters are case-insensitive substrings and combine with AND. Use this rather
than jq: it needs nothing beyond Python, it skips the stray non-object entries
some normalized files carry, and it does not care which shell you are in.

Then run `report-prose` for the editorial pass and `report-visuals` for the
presentation pass. Ask the user to run `/remove-ai-slop` for the broader prose
sweep, since that skill only they can trigger.

Apply edits with a throwaway Python script at `reports/<...>/_rewriteN.py` using
exact-string `replace` with an assert on the match count. Bash heredocs break on
the apostrophes in the report text, and blind `sed` silently edits nothing when a
line has moved. Files matching `reports/**/_*` are gitignored.

Verify before you write. Every number has to come from the new scrape:

```bash
python pipeline/query.py benchmark-data/<today>/artificial-analysis/normalized.json --model "Grok 4.6"
python pipeline/query.py benchmark-data/<today>/vals-ai/normalized.json --benchmark "Code Migration" --limit 20
```

Filters are case-insensitive substrings and combine with AND. Use this rather
than jq: it needs nothing beyond Python, it skips the stray non-object entries
some normalized files carry, and it does not care which shell you are in.

Then run the `report-prose` skill on it. That is the editorial pass for this
repo: every number traceable to `results.json`, every empty cell explained, every
rank exact, units attached, no portable filler. Ask the user to run
`/remove-ai-slop` as well when they want the broader prose sweep, since that
skill only they can trigger.

Build the HTML:

```bash
uv run --with markdown python pipeline/build_html.py reports/<today>-<slug>/profile.json
```

Add a glossary entry for any new term you introduce, since the HTML puts hover
definitions on jargon. It prints the tooltip count; a drop means the alternation
regex stopped matching something.

The interactive charts carry no toolbar. Hovering a bar shows that model's
metric breakdown, which is the only interaction the report needs.

## Step 5: deploy

Two branches, and the difference matters. `main` carries the toolkit only:
`pipeline/`, the skill, the README. It ignores `benchmark-data/` and `reports/`
so a clone stays small and a run never pushes someone's scrapes to it. Your
scrapes and reports live on a data branch, `erp` by default, whose `.gitignore`
tracks them.

Check where you are before committing:

```bash
git branch --show-current
```

On the data branch, the repo keeps exactly one commit. Amend and force-push:

```bash
git add -A
git commit -q --amend -m "260902 llm analysis"
git push --force-with-lease origin erp
```

The message is fixed, even though the content is newer than that date. Rebuild
the landing page rather than editing it:

```bash
python pipeline/build_index.py
```

It reads every `reports/*/profile.json` and the `results.json` beside it, so a
new report appears with its picks the moment it exists. It is a local file. This
pipeline does not publish anywhere: no GitHub Pages step, no Actions workflow,
and neither gets added back without the user asking for it.

Hand back the file path when the run finishes, not a URL.

A change to `pipeline/` or to this skill belongs on `main` as its own commit.
Cherry-pick it onto the data branch rather than force-pushing the data branch
over `main`.

Never check the deployment over the network. Report what you changed, say plainly
that the live page is unverified, and let the user open it.

## Partial runs

The user often wants one piece:

- "scrape only" stops after step 1.
- "rebuild the charts" is step 2 alone, useful after a manual data fix or a
  weight correction. It does not re-scrape.
- "deploy" is step 5 alone.
- "has model X reached the leaderboards" is step 1 for the sites that would carry
  it, plus an answer, with no report changes unless asked.
- A second stack on the same day reuses today's data folder and runs steps 0, 3,
  2, 4 and 5.

## Honesty rules that keep a report worth reading

These took several rounds of correction to settle:

- A vendor's own benchmark table is not a leaderboard result. Put it in the
  model's section, label it as the vendor's number, keep it out of every index.
- State ranks exactly. "First on overall, fourth on batch" beats "top five of all
  four" when the second is no longer true.
- Artificial Analysis re-measures latency daily and the numbers move by 20% or
  more between days. Every latency figure is that day's reading, and a big move
  deserves a sentence, not a silent update.
- A lead inside two combined standard errors is noise. Say so.
- Benchmark names lie. The Vals benchmark called "APEX Agents" is Mercor's
  banking and law agent test, not Oracle APEX. Read what a benchmark measures
  before making it a proxy for anything.
