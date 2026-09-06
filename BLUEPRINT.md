# Blueprint

What this system is and why each part is shaped the way it is. `README.md`
says how to run it, `PIPELINE.md` lists the stages in order, and this file says
what must stay true whatever changes.

Revise a section here and the code follows. If a rule below is not visible in
the output, the code is wrong, not the rule.

## 1. The problem

A team has a stack and a budget. They want to know which model to buy for it.
Vendor marketing answers that badly, and a single leaderboard answers it for
one benchmark instead of for their work.

So: read ten public leaderboards, weight the benchmarks that match the jobs the
stack actually involves, and produce a shortlist a reader can check line by
line.

## 2. What must stay true

These are the invariants. Everything else is negotiable.

1. **The engine calculates, nobody else.** Every number in the report comes
   from `results.json`, `master-table.md` or `glance-table.md`. Not from prose,
   not from a browser, not from a subagent's summary. A number typed twice is a
   number that eventually disagrees with itself.
2. **A missing input is missing.** Never imputed, never median-filled, never
   quietly zero. A model lacking an input is excluded from any index that uses
   it, and the report says which model lacks what.
3. **Every claim carries its source and its date.** Latency moves 20% between
   days, so a bare number is not a fact.
4. **A wrong join looks exactly like data.** Cross-source model matching is
   exact first, prefix only when unique, long enough, and not split by a
   version digit. Anything below that is dropped rather than guessed.
5. **Scope stays as wide as the evidence.** "Only the models carrying a price"
   never becomes "all models".
6. **Nothing publishes itself.** The pipeline writes files. Where they go is
   the user's decision.

## 3. Data model

Ten sites, one shape. Every scrape normalises to rows of
`{model, benchmark, metric, score}` in
`benchmark-data/<YYYYMMDD>/<site>/normalized.json`, beside the raw payload and
a `meta.json` recording the extraction method and what changed since the last
scrape.

That single shape is the reason any site can feed any role index. Which sites
actually score is a property of the profile, not of the pipeline.

Scrape data is stack independent. Two stacks on the same day share one data
folder, and the second run skips the scrape entirely.

## 4. The profile is the contract

`reports/<date>-<slug>/profile.json` holds everything stack specific:

- `stack`, `slug`, `data`, `title`
- `scoring_sources`: which sites produce numbers rather than provenance
- `metrics`: each with site, benchmark, metric, and a `unit` when it has one
- `roles`: two to four, each with weights summing to 1.00
- `overall`: stack independent, so reports stay comparable
- `cheap_alternative`: how far behind and how much cheaper still counts
- `gaps`: what the data could not answer
- `pair_sections`: which two report sections share a row

The engine reads only this. Changing a weight means editing the profile and
rerunning, never adjusting a number in the report.

## 5. Roles

A role is a job the stack involves, named after the work: "Batch migration",
"Interactive edit loop". Two to four of them. They are the one decision the
whole report rests on, and the first three that come to mind are always the
same three, which is why the `adhd` skill derives them rather than the model
guessing.

Rules that keep a role honest:

- Weights sum to 1.00. Never renormalise to paper over a missing input.
- Every metric must exist in the catalogue for that scrape day.
- No invented proxy. Code Migration stands in for ERP legacy work because that
  benchmark literally migrates code. When nothing matches, say so and build the
  role from what exists.
- Price and latency enter as inverse log min-max across the candidate set, so
  they are relative to the models compared, not absolute. Adding a model changes
  everyone else's score, and the report says that.

## 6. What the engine produces

`pipeline/make_charts.py` writes, next to the profile:

- `results.json`: every raw value, every role formula, the scores, the picks,
  the price and score frontier, and per role the candidates it could not score
  with the input each one lacked.
- `master-table.md` and `glance-table.md`, ready to paste.
- One chart per index plus the price against score scatter, each as a PNG for
  GitHub and an interactive HTML for the page.

It also writes a zero-filled variant of every index. That is not the published
score; it exists so the report can answer, on demand, what the ranking would
look like if absence counted as zero.

## 7. Report structure

In order:

1. Read first: stack, data path, what moved since the last run, the frontier,
   and what this data cannot measure.
2. The glance table and the index weights, side by side.
3. The master table: every candidate against every metric that has data.
4. One section per role: table on the left, reasoning on the right, and under
   the table a card with the formula and the models the role could not score.
5. A section per newly released model, saying plainly when it has no research
   behind it.
6. Stack tooling from the `last30days` research.
7. Caveats and references.

## 8. Presentation

The rules live in the `report-visuals` skill. The two that decide the rest:

- **A chart earns its place** by showing what the table cannot: a ranking with
  visible gaps, a tradeoff on two axes, a shape. Otherwise the table already
  said it.
- **An empty cell is a finding**, so it is marked and explained rather than
  left blank.

## 9. Branches

`main` is the toolkit and ignores scrapes and reports, so a clone is small.
Each set of reports lives on its own data branch keeping one squashed commit,
because there is no reason to keep every day of scrapes in the object store.

Fix the pipeline on `main`, then cherry-pick. Never force push a data branch
over `main`.

Visibility is a property of the repository, not of a branch.

## 10. Skills

- `refresh-benchmarks`: the pipeline.
- `report-prose`: the editorial pass. Claims, units, scope, gaps.
- `report-visuals`: the presentation pass. Charts, tables, tooltips.
- `adhd`: derives the roles. The user triggers it; the model cannot.
- `last30days`: researches the stack tooling.
- `remove-ai-slop`: the broad prose sweep. The user triggers it.

## 11. Open questions

Written down rather than decided, because guessing here costs more than asking.

- Should a role be allowed to score a model on partial inputs when the missing
  weight is small, say under 0.10, instead of excluding it outright?
- Should the overall index stay fixed across stacks, or should a stack be
  allowed to reweight it and lose comparability?
- How old may a scrape be before the report refuses to use it?
- What belongs in the tooling section when the 30 day window returns nothing?
