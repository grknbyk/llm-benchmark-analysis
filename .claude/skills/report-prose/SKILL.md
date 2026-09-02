---
name: report-prose
description: The editorial pass for a model shortlist report in this repo. Checks that every number names its source and date, that absent data is stated rather than smoothed, that ranks and scopes are exact, that units are attached, and that the prose reads like a person wrote it. Use this after writing or editing any report under reports/, whenever the user says "rapor dilini temizle", "raporu düzelt", "clean the report", asks whether a claim in the report is defensible, or before deploying. Also use it on README.md and on the skill files, since they carry the same voice.
---

# The editorial pass

A shortlist report tells someone which model to spend money on. That only works
if a reader can check every claim in it. Most of the rules below exist because a
sentence once slipped through that a reader could not check, or could check and
find wrong.

Run this on the report before the HTML build, and again on any prose you add
afterwards.

For the general prose sweep across all the usual machine-writing tells, ask the
user to run `/remove-ai-slop`. That skill is theirs to trigger, not yours. This
one covers what is specific to this repo.

## Claims

**Every number names where it came from and when.** Artificial Analysis
re-measures latency daily and figures move 20% or more between days, so a bare
"31 seconds" is not a fact, it is a fact from a date.

Wrong: The model responds in 31 seconds.
Right: End-to-end 31 s in the 20260904 scrape, up from 18 s the day before.

**Absent is a value.** A model with no row for a benchmark is missing it, not
scoring zero and not "roughly comparable". Say which model lacks which input and
which index it therefore misses.

Wrong: Astra leads on every index.
Right: Astra leads the batch index. It has no latency row, so it does not enter
the interactive one.

**Scope stays exactly as wide as the evidence.** "Only the models carrying a
price" never becomes "all models". "First on overall, fourth on batch" never
becomes "top five across the board".

**A lead inside two combined standard errors is noise.** Vals publishes stderr.
When the gap is smaller, write that the two are level, then say which you would
pick and why, on grounds other than the score.

**A vendor's own table is not a leaderboard result.** It goes in that model's
section, labelled as the vendor's number, and stays out of every index.

**Read what a benchmark measures before naming it a proxy.** The Vals benchmark
called "APEX Agents" is Mercor's banking and law agent test, not Oracle APEX.
Names lie.

## Numbers on the page

**Units are attached, always.** `$/1M`, `$/task`, `s`, `%`. A column of bare
numbers that turn out to be seconds costs a reader more than the column gave.

**Scores keep the precision the engine produced**, no rounding a 62.68 to "about
63" in prose while the table says 62.68.

**Price and latency are relative to the candidate set.** They are inverse log
min-max scored, so adding a model changes everyone else's interactive score. If
you compare two runs, say that.

**Never do arithmetic in prose.** Every figure comes from `master-table.md`,
`glance-table.md` or `results.json`. If a number you want is not in them, change
the profile and rerun the engine.

## Voice

**One benchmark, one name.** Do not rotate between "Code Migration", "the
migration benchmark" and "Vals code mig" in the same section. Repetition is
correct here; a reader is matching your words against a table.

**No em dashes or en dashes.** Use a comma, a period, or restructure.

**No sentence that would survive being moved into a report about a different
stack.** "This model represents a significant step forward" says nothing. Cut it
or replace it with the measurement that made you write it.

**No closing solicitation**, no "hope this helps", no "let me know". The report
ends on its last finding.

**Bold carries the claim, not the decoration.** Bold the pick and the number a
reader needs. Do not bold every metric name in a paragraph.

**Say the awkward thing.** When the top pick costs 20 dollars per million tokens
and the cheap alternative is 4 points behind at a twelfth the price, that
sentence is the most useful one in the section. Write it plainly.

## The pass

Read the report once for each of these, in order. Batching them means missing
things.

1. **Numbers.** Every figure traceable to `results.json` or the day's scrape.
   Units present. Nothing computed in prose.
2. **Gaps.** Every empty cell in the master table explained somewhere, at least
   once.
3. **Scope and rank.** Each superlative checked against the table it claims.
4. **Voice.** Em dashes, portable filler sentences, synonym rotation, closing
   solicitations.
5. **Structure.** Glance table, master table, one section per role, new model
   sections, tooling section, caveats, references.

Report what you changed as a short list, not as a rewritten copy of the report.

## Applying edits

Use a throwaway script at `reports/<...>/_deslopN.py` with exact-string
`replace` and an assert on the match count. Bash heredocs break on the
apostrophes in the report text, and blind `sed` silently edits nothing when a
line has moved. Files matching `reports/**/_*` are gitignored.

Rebuild the HTML afterwards, since the tooltip count is a cheap check that you
did not break a term the glossary matches:

```bash
uv run --with markdown python pipeline/build_html.py reports/<date>-<slug>/profile.json
```
