# Report blueprint

The page, block by block, top to bottom. Move a block here and the builder
follows. Widths are proportions, not pixels; the page is 1400px wide at most.

Boxes marked `[engine]` are pasted from what `make_charts.py` wrote. Boxes
marked `[written]` are prose. Nothing in a `[engine]` box is retyped by hand.

---

## 1. Title

```
+--------------------------------------------------------------------------+
|  # ERP / Oracle APEX model shortlist                             serif h1 |
+--------------------------------------------------------------------------+
```

## 2. Read first

Full width. The opening block and the orientation prose are one section, not
two.

```
+--------------------------------------------------------------------------+
|  ## Read first                                                            |
|                                                                           |
|  Stack: ...            Data: benchmark-data/<date>/            [written]  |
|  Scores from <sites>. The others are provenance, not inputs.              |
|                                                                           |
|  **Three things moved since the <date> run.**                             |
|  para 1   what changed on a leaderboard, with both dates                  |
|  para 2   what changed for one model, with both readings                  |
|  para 3   what changed in the pipeline itself, if anything                |
|                                                                           |
|  the lead, and why it is or is not a lead                                 |
|  the price and score frontier, named model by model                       |
|  what this data cannot measure                                            |
+--------------------------------------------------------------------------+
```

## 3. Picks and weights, one row

Two tables side by side. Trailing prose drops below both at full width, so a
short table never leaves a hole.

```
+---------------------------------+----------------------------------------+
|  ## Best option at a glance     |  ## The four indexes                   |
|                                 |                                        |
|  role | best | cheap  [engine]  |  index | weights            [engine]   |
|  ------------------------       |  ---------------------------           |
|  Overall     ...   ...          |  Overall      0.30 coding + ...        |
|  Role A      ...   ...          |  Role A       0.30 ... + ...           |
|  Role B      ...   ...          |  Role B       ...                      |
|  Role C      ...   ...          |  Role C       ...                      |
+---------------------------------+----------------------------------------+
|  how price and latency are scaled, and against what        [written]      |
|  a model missing an input is excluded, never imputed                      |
+--------------------------------------------------------------------------+
```

## 4. Every model, every metric

The master table. Header vertical, columns grouped by source site, the control
in the table's own empty corner.

```
+--------------------------------------------------------------------------+
|  ## Every model, every metric                                             |
|                                                                           |
|                    +-------------------+--------+--------+-------------+  |
|                    |artificial-analysis| vals-ai|deepswe |    index    |  |
|                    +-------------------+--------+--------+-------------+  |
|                    | v  v  v  v  v  v  |  v  v  |  v  v  | v  v  v  v  |  |
|  (o--) missing=0   | e  e  e  e  e  e  |  e  e  |  e  e  | e  e  e  e  |  |
|                    | r  r  r  r  r  r  |  r  r  |  r  r  | r  r  r  r  |  |
|  model             | t  t  t  t  t  t  |  t  t  |  t  t  | t  t  t  t  |  |
|  ----------------- +-------------------+--------+--------+-------------+  |
|  Model A           | 81.6 58.2 ...     |  54.6  |  n/a   | 63.9 ... 66 |  |
|  Model B           | 75.9 53.0 ...     |  44.6  |  67.5  | 62.7 ... 66 |  |
|  Model C           | ...               |  n/a   |  n/a   | n/a  ...    |  |
|  ...                                                          [engine]    |
+--------------------------------------------------------------------------+
```

- Header labels turn 90 degrees, capped in length, full name on hover.
- A rule runs down the first column of every site group, through the body.
- `n/a` in a warning colour, hover says which site publishes no row.
- The toggle sits above the `model` label, in space the table already wastes.
  On: missing counts as 0, indexes swap to the zero-filled variant, rows
  re-rank. Off: the published ranking.

## 5. Charts

Odd count, so the lead takes a full row and the rest pair up. No toolbar,
hover only.

```
+--------------------------------------------------------------------------+
|  price against the overall index, frontier marked            [engine]     |
|                                                                           |
+--------------------------------+-----------------------------------------+
|  overall index          [engine]|  role A index                 [engine] |
+--------------------------------+-----------------------------------------+
|  role B index           [engine]|  role C index                 [engine] |
+--------------------------------+-----------------------------------------+
```

## 6. One section per role

Repeats for each role. Table left at its natural width, reasoning right, and
under the table a card with the formula and the models the role could not
score.

```
+--------------------------------------------------------------------------+
|  ## <Role name>                                                           |
|  one line: what this job is, in the reader's terms          [written]     |
+---------------------------------+----------------------------------------+
|  model | index | inputs [engine] |  **Pick <model>.** why, with the       |
|  -----------------------------   |  number that decided it, and whether   |
|  ...    ...     ...              |  the lead survives its stderr          |
|  ...    ...     ...              |                                        |
|                                  |  **If the price does not survive       |
|  +----------------------------+  |  review, take <model>.** what it       |
|  | HOW THIS INDEX IS BUILT    |  |  costs in points and what it saves     |
|  | 0.30*a + 0.25*b + ...      |  |                                        |
|  | NOT SCORED         [engine]|  |  which models are absent from this     |
|  | Model X, no <input>        |  |  index and why                         |
|  +----------------------------+  |                                        |
+---------------------------------+----------------------------------------+
```

## 7. Models that moved

Full width prose, one short block per model that is new or that changed
materially since the last run. A vendor's own table is labelled as the
vendor's and stays out of every index.

```
+--------------------------------------------------------------------------+
|  ## Models that moved                                                     |
|  **<Model>** what it did, on which board, with the date     [written]     |
|  **<Model>** ...                                                          |
+--------------------------------------------------------------------------+
```

## 8. Stack tooling

One subsection per technology named in the stack, plus one for agent tooling
in general. Each separates official from community and dates every claim.

```
+--------------------------------------------------------------------------+
|  ## Stack tooling                                                         |
|  how it was researched, and the window                      [written]     |
|                                                                           |
|  ### <Technology A>                                                       |
|  official: what the vendor ships, or plainly that it ships nothing        |
|  community: name, repo, last commit, signal of use                        |
|  what changed in the window, each item with its date                      |
|                                                                           |
|  ### <Technology B>   ...                                                 |
|  ### Agent tooling practice                                               |
|  what shipped / what practitioners changed their minds about /            |
|  security and supply chain                                                |
+--------------------------------------------------------------------------+
```

## 9. Caveats and references

```
+--------------------------------------------------------------------------+
|  ## Caveats                                                               |
|  numbered, one per limitation a reader would otherwise discover late      |
|                                                                           |
|  ## References                                                            |
|  scoring sites, provenance sites, tooling sources, and the line that      |
|  every number is reproducible from results.json                           |
+--------------------------------------------------------------------------+
```

---

## Rules that survive any rearrangement

1. Every number comes from `results.json`, `master-table.md` or
   `glance-table.md`. None is worked out in prose or in the browser.
2. A missing input is never filled in. It is marked, explained, and the model
   is left out of the indexes that need it.
3. Every claim names its source and its date.
4. A chart earns its place by showing what the table cannot.
5. Nothing publishes itself. The pipeline writes files.

## Open questions

- Should a role score a model on partial inputs when the missing weight is
  small, say under 0.10, instead of excluding it?
- Should the overall index stay fixed across stacks, or may a stack reweight it
  and lose comparability?
- How old may a scrape be before the report refuses it?
- What goes in the tooling section when the window returns nothing?
