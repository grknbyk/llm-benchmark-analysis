# LLM benchmark analysis

Pick the best models for a technology stack, using ten public leaderboards
instead of vendor marketing. You name a stack, the pipeline scrapes the
leaderboards, derives weighted role indexes for the jobs that stack involves,
researches the skills and MCP servers around it, and writes a shortlist report
with charts.

`main` is the toolkit. Your scrapes and reports live on your own data branch.

## What you need

- **Python 3.11 or newer.** `pip install -r requirements.txt`, or nothing at all
  if you use [uv](https://docs.astral.sh/uv/), which fetches the dependencies per
  run.
- **Claude Code**, with three skills from this repo: `refresh-benchmarks` is
  the pipeline, `report-prose` is the editorial pass, `report-visuals` is the
  presentation pass. They load from `.claude/skills/` on clone, nothing to
  install.
- **The `chrome-devtools` MCP server**, for the scrape step. Ten agents drive it
  in parallel in isolated browser contexts.

Nothing else is machine specific. There are no absolute paths, no jq, no shell
assumptions beyond what Python gives you.

## Recommended, not bundled

Two outside skills make the report better. Neither ships in this repo, both are
public, and the pipeline runs without either. Install them yourself if you want
what they add:

- **[`adhd`](https://github.com/UditAkhourii/adhd)** derives the indexes in
  step 0: the role, the metrics that feed it, and the weight on each. It runs
  five isolated branches, then three blind judges, so the weights come out of a
  process rather than out of the first three ideas anyone has.
  **Without it:** the driver model judges directly. Same output shape, one
  point of view instead of eight, and the first three roles that come to mind
  are always the same three.
- **[`last30days`](https://github.com/mvanhorn/last30days-skill)** researches
  the stack tooling in step 3, over a fixed 30 day window, across sources a web
  search does not reach.
  **Without it:** the model falls back to whatever search it has. The section
  still gets written; expect the same three blog posts every run, and dates
  that are harder to trust.

`remove-ai-slop` is the one prose skill this repo asks *you* to run, not the
model: `/remove-ai-slop` on the finished report. It is yours to trigger, which
is why the pipeline never calls it.

## Example run

```
$ git clone https://github.com/grknbyk/llm-benchmark-analysis && cd llm-benchmark-analysis
$ claude
> /refresh-benchmarks Svelte 5, SvelteKit, PostgreSQL, SPA for real estate
```

What happens, in order:

1. **Ten scrape agents and five research agents start at once.** The scrapers
   fill `benchmark-data/<today>/<site>/`. The researchers run `last30days` on
   Svelte 5, SvelteKit, PostgreSQL, SPA tooling and agent tooling in general.
   Roughly 25 minutes, most of it waiting.
2. **While they run, the roles get derived.** `pipeline/catalogue.py` lists every
   metric the fresh data actually carries. The `adhd` skill proposes candidate
   roles for the stack, and the converged two to four land in
   `reports/<today>-svelte-spa/profile.json`. You see them as five lines and can
   correct a weight before anything is computed.
3. **The engine scores everything.**

   ```bash
   uv run --with matplotlib --with pandas --with plotly python \
     pipeline/make_charts.py reports/20260906-svelte-spa/profile.json
   ```

   It prints the cross-source join table, writes `results.json` with every raw
   value and every role formula, and writes `master-table.md` and
   `glance-table.md` ready to paste. One chart per role plus a price against
   score scatter with the frontier marked, each as a PNG and an interactive
   HTML.
4. **The report gets written** from those artifacts, never from arithmetic done
   by hand, then converted:

   ```bash
   uv run --with markdown python pipeline/build_html.py reports/20260906-svelte-spa/profile.json
   ```
5. **Deploy.** `python pipeline/build_index.py` refreshes the landing page from
   the reports that exist, then one squashed commit goes to your data branch.

Running a second stack the same day skips step 1 entirely, because the
leaderboard data does not depend on the stack. That run takes about five
minutes.

## Layout

```
pipeline/catalogue.py     every site | benchmark | metric available in a scrape folder
pipeline/make_charts.py   joins the sources, scores the roles, draws the charts
pipeline/build_html.py    markdown to HTML, hover tooltips, rotated wide headers
pipeline/query.py         read rows out of a normalized.json without jq
pipeline/build_index.py   rebuilds index.html from the reports that exist
.claude/skills/refresh-benchmarks/   the pipeline itself, as a Claude Code skill
.claude/skills/report-prose/         the editorial pass: claims, units, scope
.claude/skills/report-visuals/       the presentation pass: charts, wide tables, tooltips
```

On a data branch you also get:

```
benchmark-data/<YYYYMMDD>/<site>/{raw,normalized,meta}.json   one folder per scrape day
reports/<YYYYMMDD>-<slug>/profile.json                        the stack profile
reports/<YYYYMMDD>-<slug>/results.json                        raw values, role formulas, picks
reports/<YYYYMMDD>-<slug>/<slug>-model-shortlist.{md,html}    the report
```

## The profile is the contract

Everything stack-specific lives in `profile.json`: which sites score, which
metric feeds which role, and the weights. The engine does every calculation
from it. Nothing is computed by hand, so the report and `results.json` can never
disagree.

```json
{
  "stack": "Svelte 5, SvelteKit, PostgreSQL, SPA for real estate",
  "metrics": {
    "coding": {"site": "artificial-analysis", "benchmark": "Artificial Analysis Coding Index", "metric": "score"}
  },
  "roles": [
    {"name": "Component authoring", "slug": "components",
     "weights": {"coding": 0.40, "webdev": 0.30, "nh": 0.30}}
  ],
  "cheap_alternative": {"max_points_behind": 5.0, "min_price_ratio": 3.0}
}
```

A model missing an input is excluded from that role. It is never imputed, and
the report says which model is missing what.

## The ten sites

`artificial-analysis`, `vals-ai`, `deepswe`, `livebench`, `lmarena`,
`terminal-bench`, `arc-prize`, `epoch-ai`, `design-arena`, `benchlm`.

All ten normalize to the same long shape, one row per
`{model, benchmark, metric, score}`, so any of them can feed a role index. Which
ones do is the profile's decision. `.claude/skills/refresh-benchmarks/references/sites.md`
holds the extraction method and the specific trap each site sets.

## Branches

`main` holds the toolkit and ignores `benchmark-data/` and `reports/`, so a
clone is small and a pipeline run never pushes scrapes here. Each set of
reports lives on its own data branch, which tracks those folders.

That means a fresh clone has nowhere to keep its output yet. Make the data
branch before the first run:

```bash
git checkout -b mystack
printf '!benchmark-data/\n!reports/\n!index.html\n' >> .gitignore
git add .gitignore && git commit -m "track scrapes and reports on this branch"
```

The data branch keeps one squashed commit, so a run ends with
`git commit --amend` and a force push rather than a growing history. Scrapes
are large and there is no reason to keep every day of them in the object store.

Reports are read from disk. Open
`reports/<date>-<slug>/<slug>-model-shortlist.html` in a browser, or open
`index.html` at the root, which lists every report that exists. Nothing in this
pipeline publishes to the web, and there is no GitHub Pages step; if you want
one, that is your decision to make in the repository settings.

Fix the pipeline on `main`, then cherry-pick onto the data branch. Never force
push a data branch over `main`.

Visibility is a property of the repository, not of a branch. A public repo
publishes every branch, including the scrapes on the data branch. If that
matters, keep the data in a separate private repo.
