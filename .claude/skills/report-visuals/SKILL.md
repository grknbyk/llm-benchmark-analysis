---
name: report-visuals
description: The presentation rules for a shortlist report in this repo. Covers chart layout and how many charts a section gets, the wide master table with rotated headers and per-site column groups, hover tooltips and the glossary, the landing page cards, and whether a given chart earns its place at all. Use this whenever building or changing the HTML for a report under reports/, adding or removing a chart, editing pipeline/build_html.py or pipeline/build_index.py, or when the user says the report looks wrong, the columns are misaligned, the page is too plain, or asks how a chart should be laid out.
---

# The presentation pass

`report-prose` decides whether a sentence is defensible. This decides whether a
reader can see the answer without reading. Run it after the engine has written
the charts and before the HTML build.

Everything here is enforced by `pipeline/build_html.py` and
`pipeline/build_index.py`. If a rule below is not visible in the output, the
build script is what needs changing, not the markdown.

## Does the chart earn its place

A chart competes with the master table, which already carries every number.
Keep it only when it does something the table cannot:

- **A ranking with gaps you can see.** Bar heights show that first and second
  are level while third is far back. A table makes you subtract.
- **A tradeoff on two axes.** Score against price is the single most
  decision-relevant view in this report, because the whole question is what to
  buy.
- **A shape.** A long tail, a cliff, a cluster.

Cut it when it restates one column of the table in colour, or when it has fewer
than five bars. Three bars are a sentence, not a chart.

## Layout

Two charts per row at most. A row of three is unreadable at report width.

When a section holds an odd number of charts, the first takes a full width row
of its own and the rest pair up. The lead chart is the one a reader should see
first, so put it first in the markdown; `build_html.py` reads the order from
there. An even count pairs all the way down, with no half-empty row.

Every chart ships twice, a PNG for GitHub and an interactive HTML for the site.
The build swaps in the HTML when it exists and falls back to the PNG when it
does not.

## Role sections

A role section is a four row table and three short paragraphs about it. Stacked,
they leave two thirds of the line empty next to the table, so pair them: the
table on the left at its natural width, the reasoning on the right. The heading
and the one line description of the role stay full width above both.

Cap the left column. A long index formula will otherwise take the width the
reasoning needs, and prose in a 350 pixel column is worse than prose under a
table.

Under the table goes a card with the two facts a reader wants at exactly that
moment: the formula that produced the column they are looking at, and the
candidates the role could not score with the input each one lacked. Both come
from `results.json`, so the card cannot disagree with the table above it.

Do not fill the remaining space with anything else. White space under a short
card costs nothing; a chart or a note added to balance a column is filler, and
filler is what a reader learns to skip.

## Two sections on one row

Two short sections that answer the same question belong side by side. The
glance table and the index weights are one example: a reader checks the pick,
then checks what produced it.

Name the pair in `profile.json` under `pair_sections`, because which sections
are short enough is a property of the report and not of the builder. Both keep
their own heading. A merged section with one heading hides what the second
table is.

Only the tables go in the columns. Anything after a table drops below the pair
at full width, because prose in one column stretches the row to its own height
and leaves a hole under the shorter table.

## The interactive charts

No toolbar. Hovering a bar shows that model's metric breakdown with units, which
is the only interaction the report needs. Zoom, pan and export are noise on a
fourteen bar chart, and the toolbar covers the tallest bar.

Bar colour carries no meaning here, so do not explain it. It separates
neighbours and nothing more.

## The master table

Sixteen columns of numbers is only readable with help:

- **Turn the header vertical** past eight columns, not diagonal. A 45 degree
  label starts over a column it does not belong to, which is the misalignment
  complaint in another form. `writing-mode: vertical-rl` plus a 180 degree
  rotation reads bottom to top and stays inside its own column whatever the
  column width is.
- **Cap the header length** and let the overflow truncate. A header band deep
  enough for the longest label pushes the first row of data off the screen. The
  full text is on hover, so nothing is lost.
- **Keep the model column flat and sticky.** It is the row label; a reader
  scrolling right must keep it.
- **Group the columns by source site** with a spanning row above the headers, so
  a reader can see which leaderboard a number came from. A label alone is not
  enough: box the group cell and run a rule down the first column of every
  group, all the way through the body. Without the rule a reader counts columns
  to find where one site stops and the next starts, and gives up.
- **Box the rotated labels too.** A tilted line of text with nothing around it
  reads as floating; a bordered chip belongs to the column under it.
- **Short codes in the header, the full name on hover.** Sixteen full benchmark
  names do not fit across a screen, so the header carries `code_mig` and the
  `title` attribute carries `Code Migration`. The engine writes that long form
  into `results.json` as `columns[].label`, so the HTML never invents it.
- **Units in the header**, `$/1M`, `s`, `%`, `$/task`. A column of bare numbers
  that turn out to be seconds costs more than it gives.
- **Mark missing cells, do not leave them blank.** A blank reads as an
  oversight. `n/a` in a warning colour reads as a finding, and the cell says on
  hover which site publishes no row for that model, or which input the role
  lacked. The value is still never imputed.
- **Offer the zero-fill switch above the table.** An empty cell provokes one
  question, what would the ranking look like if absence counted as zero, and a
  control answers it better than a paragraph. Off is the published ranking. The
  engine computes both variants and writes the second as `roles[].scores_zero`;
  the page swaps precomputed numbers and re-sorts. Nothing is calculated in the
  browser, for the same reason nothing is calculated in prose.

## Tooltips

The HTML puts hover definitions on benchmark jargon from a glossary in
`build_html.py`. Add an entry for any term the report introduces.

Only the first mention of a term is marked. Underlining every one of the
twenty-five mentions of MCP in a section turns a definition into decoration, and
a reader who wants it scrolls up once.

So the printed tooltip count is the number of distinct glossary terms the report
actually uses. Compare it to the previous run: a drop means a term was reworded
out of the text or the alternation regex stopped matching it.

## The landing page

`pipeline/build_index.py` generates `index.html` from every
`reports/*/profile.json` and the `results.json` beside it. Never hand-edit it.

Each report gets a card carrying the stack, the data date, how many models and
metrics were compared, the best and cheap pick per role, and links to the
report, the markdown, `results.json` and `profile.json`. A reader should be able
to decide whether to open the report without opening it.

## Visual language

Warm paper background `#FBFAF6`, ink `#1A1A1A`, serif headings, monospace for
anything a reader might compare digit by digit. The palette and the tab strip
come from the Vals AI and DeepSWE leaderboards, which is deliberate: this report
sits next to those pages in a reader's head.

## Checking it

Look at the result. A rotated header that overlaps its neighbour, a sticky
column that stopped sticking, or a chart that lost its labels are all invisible
in the markdown and obvious in a screenshot.

Use the `chrome-devtools` MCP with your own isolated context. Never any
`mcp__claude-in-chrome__*` tool: that drives the user's own browser and is off
limits unless they ask for it.
