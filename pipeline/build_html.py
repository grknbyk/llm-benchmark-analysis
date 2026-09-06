"""Markdown to HTML for a shortlist report, with hover tooltips on benchmark
jargon and rotated headers on the master table.

Run: uv run --with markdown python pipeline/build_html.py reports/<date>-<slug>/profile.json

A table wider than WIDE_AT columns gets its header row rotated 45 degrees and a
horizontal scroll container. Nothing marks it in the markdown, so the .md stays
readable on GitHub where rotation is not available.
"""
import json
import re
import sys
from pathlib import Path

from strings import strings


def _markdown():
    """Imported on use, not on import: build_blueprint.py wants the stylesheet
    from this module and has no business needing a markdown converter."""
    try:
        import markdown
    except ImportError:
        raise SystemExit("build_html.py needs the markdown package. Either pip install -r "
                         "requirements.txt, or let uv fetch it per run:  "
                         "uv run --with markdown python pipeline/build_html.py <profile>")
    return markdown

WIDE_AT = 8

# Terms that mean the same thing in any report. Everything tied to one
# site or one benchmark belongs in that profile's own `glossary` block,
# which is merged over this at build time.
GLOSSARY = {
    "pass@1": "Share of tasks solved on the first attempt.",
    "frontier": "Price and score frontier: the models nothing else in the candidate set beats on both price and overall index at the same time. Everything off it is beaten on both.",
    "stderr": "Standard error of the mean. A lead under two combined stderr is not significant.",
    "Elo": "Rating from pairwise human votes. Differences under about 20 points are usually not meaningful.",
    "MCP": "Model Context Protocol: the interface a model uses to reach an external tool or data source. An MCP server is code that runs on your machine.",
}

CSS = (
    "body{max-width:1400px;margin:40px auto;font:16px/1.55 Georgia,serif;color:#1a1a1a;background:#fbfaf6;"
    "padding:0 24px}h1,h2{font-weight:600}table{border-collapse:collapse;font:13px/1.4 monospace;margin:16px 0}"
    "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}th{background:#e9eee7}"
    "img{max-width:100%;display:block;margin:20px 0;border:1px solid #ddd}"
    "code{font:13px monospace;background:#eee;padding:1px 4px}"
    "abbr{text-decoration:underline dotted #888;cursor:help}"
    ".charts{display:grid;gap:16px;margin:20px 0}.charts.n1{grid-template-columns:1fr}"
    ".charts.n2{grid-template-columns:1fr 1fr}"
    ".charts figure{margin:0;min-width:0;overflow:hidden;border:1px solid #d3cfc0;"
    "border-radius:3px;background:#fdfcf8;padding:8px 6px 4px}"
    ".charts figure img{margin:0;border:none}"
    ".charts figcaption{font:12px monospace;color:#555;margin-top:4px}"
    "@media(max-width:900px){.charts.n2{grid-template-columns:1fr}}"
    ".scroll{overflow-x:auto;margin:20px 0}"
    ".cols{display:grid;grid-template-columns:minmax(0,max-content) minmax(0,1fr);gap:28px;align-items:start;margin:16px 0}"
    ".cols>div:first-child{max-width:540px}.card{overflow-wrap:anywhere}"
    ".cols.even{grid-template-columns:1fr 1fr}.cols.even>div:first-child{max-width:none}"
    ".cols.even h2{margin-top:0}.cols.even table{width:100%}"
    ".cols.even .charts{margin:0}"
    "h2 .wt{font:400 15px/1.4 monospace;color:#8a8478;white-space:nowrap}"
    ".cols table td:first-child{max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:help}"
    ".cols>div>table{margin-top:0}.cols>div>p:first-child{margin-top:0}"
    ".card{border:1px solid #d3cfc0;background:#F5F3EB;padding:10px 12px;margin-top:14px;font:12px monospace;color:#3a3a3a;line-height:1.55}"
    ".card b{display:block;font:11px monospace;color:#6a6a6a;letter-spacing:.04em;text-transform:uppercase;margin-bottom:3px}"
    ".card b~b{margin-top:9px}"
    "table.wide td.na{color:#A8452F;background:#FBEFEA;text-align:center;font-size:11px}"
    ".tablewrap{position:relative}"
    ".tablewrap>.switch{position:absolute;left:0;top:52px;z-index:3;max-width:300px}"
    ".switch{display:inline-flex;align-items:center;gap:9px;font:12px monospace;color:#4a4a4a;"
    "border:1px solid #d3cfc0;background:#F5F3EB;padding:7px 11px;border-radius:3px;cursor:pointer;user-select:none;line-height:1.35}"
    ".switch{flex-direction:column;align-items:flex-start;gap:3px}"
    ".switch b{font:11px monospace;color:#6a6a6a;letter-spacing:.04em;text-transform:uppercase;margin-bottom:2px}"
    ".switch label{display:flex;align-items:center;gap:7px;cursor:pointer}"
    ".switch input{appearance:none;-webkit-appearance:none;flex:none;width:12px;height:12px;"
    "border:1px solid #b0aa99;border-radius:50%;background:#fff;margin:0;cursor:pointer}"
    ".switch input:checked{border-color:#A8452F;background:#A8452F;box-shadow:inset 0 0 0 2px #fff}"
    "table.wide th.sortable{cursor:pointer}"
    "table.wide th[data-dir]{border-color:#A8452F;background:#F7EDE9}"
    "table.wide th[data-dir]>span{color:#A8452F}"
    ".rowcount{font:12px monospace;color:#6a6a6a;margin-top:6px}"
    ".rowcount a{color:#A8452F}"
    "@media(max-width:900px){.tablewrap>.switch{position:static;margin:12px 0;max-width:none}}"
    "@media(max-width:900px){.cols{grid-template-columns:1fr;gap:0}}"
    "table.wide th{height:158px;vertical-align:bottom;padding:6px 3px;text-align:center;"
    "border:1px solid #d3cfc0;background:#F2F0E7;border-radius:2px}"
    "table.wide th>span{display:inline-block;writing-mode:vertical-rl;transform:rotate(180deg);"
    "max-height:142px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:12px monospace}"
    "table.wide th[title]{cursor:help}"
    "table.wide th:first-child{vertical-align:bottom;text-align:left;border:none;background:none;padding:0 0 6px}"
    "table.wide th:first-child>span{writing-mode:horizontal-tb;transform:none;max-height:none;border:none;background:none;padding:0 0 6px}"  # the row label reads flat

    "table.wide td{white-space:nowrap;text-align:right}"
    "table.wide th:first-child,table.wide td:first-child{text-align:left;max-width:190px;min-width:190px;"
    "overflow:hidden;text-overflow:ellipsis}"
    "table.wide td:first-child{cursor:help}"
    "table.wide th:first-child,table.wide td:first-child{position:sticky;left:0;background:#fbfaf6}"
    "table.wide tr.grp th{height:auto;position:static;padding:2px 6px;text-align:center;"
    "font:11px monospace;color:#4a4a4a;letter-spacing:.04em;border:1px solid #c9c5b4;background:#EFEDE3}"
    "table.wide tr.grp th:first-child{border:none;background:none}"
    "table.wide tr.grp a{color:#4a4a4a;text-decoration:underline dotted #9a9484}"
    "table.grouped th.gs,table.grouped tr:not(.grp) td.gs{border-left:2px solid #b8b3a1}"
    "table.grouped th:last-child,table.grouped tr:not(.grp) td:last-child{border-right:2px solid #b8b3a1}"
    ".toc{position:fixed;left:20px;top:40px;width:190px;font:12px/1.5 monospace;max-height:calc(100vh - 80px);overflow:auto}"
    ".toc b{display:block;font:11px monospace;color:#6a6a6a;letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px}"
    ".toc a{display:block;color:#4a4a4a;text-decoration:none;padding:3px 0 3px 9px;border-left:2px solid #e2ded0}"
    ".toc a:hover{color:#1a1a1a;border-left-color:#b8b3a1}"
    ".toc a.on{color:#A8452F;border-left-color:#A8452F}"
    "@media(min-width:1200px){body{margin-left:250px;margin-right:auto}}"
    "@media(max-width:1199px){.toc{display:none}}"
    ".tool{display:block;width:100%;text-align:left;font:inherit;color:inherit;border:1px solid #d3cfc0;background:#F5F3EB;border-radius:3px;padding:10px 12px;margin:8px 0;cursor:pointer;text-decoration:none}"
    ".tool:hover{background:#EFECE1;border-color:#b8b3a1}"
    ".tool .go{float:right;font:11px monospace;color:#8a8478}"
    "details.tool .go::after{content:\" \25be\"}"
    "details.tool[open] .go::after{content:\" \25b4\"}"
    "details.tool{padding:0}"
    "details.tool>summary{list-style:none;padding:10px 12px;cursor:pointer}"
    "details.tool>summary::-webkit-details-marker{display:none}"
    "details.tool[open]>summary{border-bottom:1px solid #ded9c9}"
    ".tool-body{padding:10px 12px 12px;background:#fdfcf8}"
    ".tool-body p{margin:0}.go-link{margin-top:10px !important;font:12px monospace}"
    ".go-link a{color:#A8452F}"
)


def add_tooltips(md_text, gloss):
    # One pass with a single alternation: replaced text is never rescanned, so a
    # term inside another term's tooltip cannot be wrapped again. Longest first
    # so "Code Migration" wins over "Coding"-style partial hits.
    terms = sorted(gloss, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w\[/-])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w\]/-])")

    # Only the first hit per term. Underlining all 25 mentions of MCP turns a
    # definition into decoration, and a reader who wants it scrolls up once.
    seen = set()

    def wrap(m):
        term = m.group(1)
        if term in seen:
            return term
        seen.add(term)
        return f'<abbr title="{gloss[term].replace(chr(34), "&quot;")}">{term}</abbr>'

    def outside_code(line):
        # a term inside backticks is code, and an <abbr> opened there is
        # printed as literal markup rather than rendered
        return "`".join(part if k % 2 else pattern.sub(wrap, part)
                        for k, part in enumerate(line.split("`")))

    # skip image lines and headings: paths and titles must stay clean
    return "\n".join(line if line.startswith(("![", "#")) else outside_code(line)
                     for line in md_text.split("\n"))


IMG = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


def swap_charts(md_text, here):
    """Replace ![alt](NN.png) with the interactive NN.html when it exists; group
    consecutive charts into a grid of at most two per row."""
    out, group = [], []

    def flush():
        """Two charts per row at most. An odd run gives the first chart a full
        width row of its own and pairs the rest, so the leading chart reads as
        the important one and no row ends with a half-empty gap."""
        if not group:
            return
        lead, rest = ([group[0]], group[1:]) if len(group) % 2 and len(group) > 1 else ([], group)
        if lead:
            out.append('<div class="charts n1">' + lead[0] + "</div>\n")
        if rest:
            out.append(f'<div class="charts n{min(len(rest), 2)}">' + "".join(rest) + "</div>\n")
        group.clear()

    for line in md_text.split("\n"):
        m = IMG.match(line)
        if not m:
            if line.strip():
                flush()
            out.append(line)
            continue
        alt, png = m.groups()
        html = here / png.replace(".png", ".html")
        if html.exists():
            group.append(f'<figure>{html.read_text(encoding="utf-8")}</figure>')
        else:
            group.append(f'<figure><img src="{png}" alt="{alt}"></figure>')
    flush()
    return "\n".join(out)


TABLE = re.compile(r"<table>\s*<thead>.*?</table>", re.S)
TH = re.compile(r"<th(?:\s[^>]*)?>(.*?)</th>", re.S)  # (?:\s...) so <thead> is not a match


JS = """<script>
(() => {
  const table = document.querySelector('table.grouped');
  if (!table) return;
  const wrap = table.closest('.tablewrap');
  const body = table.tBodies[0];
  const rows = [...body.rows];
  rows.forEach((r, i) => r.dataset.rank = i);
  const heads = [...table.tHead.rows].pop().cells;
  const LIMIT = 10;

  // published order until the reader asks for something else
  let fill = null, col = null, dir = -1;

  const num = (r, i) => {
    const t = r.cells[i].textContent.trim();
    const v = parseFloat(t);
    return isNaN(v) ? null : v;
  };

  function paint() {
    table.querySelectorAll('td[data-zero]').forEach(td => {
      if (td.dataset.orig === undefined) td.dataset.orig = td.textContent;
      const v = fill === null ? td.dataset.orig : td.dataset[fill];
      td.textContent = v === undefined ? td.dataset.orig : v;
    });
  }

  function order() {
    if (col === null) return [...rows].sort((a, b) => a.dataset.rank - b.dataset.rank);
    if (col === 0) return [...rows].sort((a, b) =>
      dir * a.cells[0].textContent.localeCompare(b.cells[0].textContent));
    return [...rows].sort((a, b) => {
      const x = num(a, col), y = num(b, col);
      if (x === null && y === null) return 0;
      if (x === null) return 1;          // absent sinks, whichever way we sort
      if (y === null) return -1;
      return dir * (y - x);
    });
  }

  function render() {
    paint();
    const o = order();
    o.forEach(r => body.appendChild(r));
    o.forEach((r, i) => r.hidden = i >= LIMIT);
  }

  document.querySelectorAll('input[name=fill]').forEach(r =>
    r.addEventListener('change', () => { fill = r.value === 'exclude' ? null : r.value; render(); }));

  [...heads].forEach((th, i) => {
    th.classList.add('sortable');
    th.addEventListener('click', () => {
      // dir 1 sorts high to low. First click shows the best models, so a
      // column where lower wins starts the other way round.
      const asc = th.dataset.better === 'low';
      dir = (col === i) ? -dir : (i === 0 ? 1 : (asc ? -1 : 1));
      col = i;
      [...heads].forEach(h => h.removeAttribute('data-dir'));
      th.dataset.dir = dir > 0 ? 'desc' : 'asc';
      render();
    });
  });

  const start = [...heads].findIndex(h => h.textContent.trim().toLowerCase() === 'overall');
  if (start > 0) {
    col = start;
    dir = 1;
    heads[start].dataset.dir = 'desc';
  }
  render();
})();
</script>"""


def group_row(columns, sites=None):
    """One header cell per run of columns from the same source, so a reader can
    see at a glance which site a number came from. Columns arrive already sorted
    by site, so consecutive runs are the whole story."""
    cells = ['<th class="grp"></th>']
    site, span = columns[0]["site"], 0
    for c in columns + [{"site": None}]:
        if c["site"] == site:
            span += 1
            continue
        url = (sites or {}).get(site)
        text = f'<a href="{url}" target="_blank" rel="noopener">{site}</a>' if url else site
        cells.append(f'<th class="grp" colspan="{span}">{text}</th>')
        site, span = c["site"], 1
    return '<tr class="grp">' + "".join(cells) + "</tr>"


def mark_cells(block, columns, roles=None, medians=None, T=None):
    """Tag the first cell of each site run so the CSS can draw one rule down the
    whole table, and give every empty cell a reason. A colspan label alone
    leaves a reader counting columns, and a blank cell alone reads as an
    oversight rather than as the finding it is.

    Index cells also carry the zero-filled score from `results.json`, which is
    what the switch above the table swaps in. The number is precomputed by the
    engine; nothing here works one out."""
    T = T or strings({})
    starts, site = set(), None
    for i, c in enumerate(columns, start=1):   # 0 is the model column
        if c["site"] != site:
            starts.add(i)
            site = c["site"]

    by_slug = {r["slug"]: r for r in (roles or [])}
    med = medians or {}
    gaps = {sl: {g["model"]: g["missing"] for g in r.get("not_scored", [])}
            for sl, r in by_slug.items()}

    def cell(i, c, model):
        """i is the data column index, c the raw `<td>...` fragment."""
        col = columns[i]
        empty = re.fullmatch(r"<td[^>]*>\s*</td>\s*", c) is not None
        attrs = ' class="gs"' if i + 1 in starts else ""
        if col["site"] == "index":
            role = by_slug.get(col["name"], {})
            zero = (role.get("scores_zero") or {}).get(model)
            mid = (role.get("scores_median") or {}).get(model)
            zattr = (f' data-zero="{zero:.2f}"' if isinstance(zero, (int, float)) else "") + \
                    (f' data-median="{mid:.2f}"' if isinstance(mid, (int, float)) else "")
            if empty:
                miss = " or ".join(gaps.get(col["name"], {}).get(model, [])) or T["an input"]
                title = T["not scored"].format(model=model, label=col["label"], missing=miss)
                return f'<td class="na"{zattr} title="{title}">{T["n/a"]}</td>'
            return re.sub(r"^<td", f"<td{attrs}{zattr}", c, count=1)
        if empty:
            title = T["no row"].format(label=col["label"], site=col["site"], model=model)
            mid = med.get(col["name"])
            mattr = f' data-median="{mid:g}"' if isinstance(mid, (int, float)) else ""
            return (f'<td class="na{" gs" if i + 1 in starts else ""}" data-zero="0"{mattr}'
                    f' title="{title}">{T["n/a"]}</td>')
        return re.sub(r"^<td", f"<td{attrs}", c, count=1) if attrs else c

    def row(m):
        cells = re.split(r"(?=<t[dh])", m.group(0))
        if "<th" in m.group(0):        # header rows only need the group rule
            return "".join(c if i - 1 not in starts else
                           re.sub(r"^<(t[dh])", r'<\1 class="gs"', c, count=1)
                           for i, c in enumerate(cells))
        model = re.sub(r"<[^>]+>", "", cells[1]).strip() if len(cells) > 1 else ""
        # the column is clipped to keep the metrics readable, so the full name
        # has to live somewhere a reader can reach
        name_cell = re.sub(r"^<td", f'<td title="{model.replace(chr(34), chr(39))}"',
                           cells[1], count=1) if model else cells[1]
        out = [cells[0]] + [name_cell] + [cell(i, c, model)
                                         for i, c in enumerate(cells[2:])]
        return "".join(out)

    return re.sub(r"<tr>.*?</tr>", row, block, flags=re.S)


def modes(T):
    """The question an empty cell provokes, offered as a control rather than a
    paragraph. Nothing is preselected, so the table opens on the published
    scores and a fill is always something the reader chose."""
    opts = [("exclude", T["exclude"]), ("zero", T["fill 0"]), ("median", T["fill median"])]
    radios = "".join(
        f'<label><input type="radio" name="fill" value="{v}"><span>{t}</span></label>'
        for v, t in opts)
    return f'<div class="switch"><b>{T["missing benchmark"]}</b>{radios}</div>'


def rotate_wide(html, columns=None, roles=None, medians=None, sites=None, T=None):
    """A table past WIDE_AT columns is unreadable with flat headers, so rotate
    them. The header text moves into a span because a rotated th collapses the
    row height otherwise."""
    T = T or strings({})

    def fix(m):
        block = m.group(0)
        head = block.split("</thead>")[0]
        ths = TH.findall(head)
        if len(ths) <= WIDE_AT:
            return block
        aligned = bool(columns) and len(columns) == len(ths) - 1
        new = block.replace("<table>", '<table class="wide grouped">' if aligned
                            else '<table class="wide">', 1)

        # the header keeps the short code; the full benchmark name goes on hover,
        # because sixteen full names do not fit across one screen
        seq = iter(range(len(ths)))

        def head_cell(t):
            i = next(seq)
            inner = t.group(1).strip()
            # a header cell can already carry an <abbr>, whose own title
            # attribute would end this one early
            plain = re.sub(r"<[^>]+>", "", inner).strip()
            col = columns[i - 1] if aligned and i else {}
            lines = [col.get("label") or plain]
            if col.get("site"):
                lines.append(T["computed in this report"] if col["site"] == "index"
                             else col["site"])
            # the last line is for a reader who has never seen the
            # benchmark: the code and the official name both assume too much
            if col.get("plain"):
                lines.append(col["plain"])
            full = "\n".join(lines)
            title = "" if i == 0 else f' title="{full.replace(chr(34), chr(39))}"'
            better = f' data-better="{col.get("better", "high")}"' if col else ""
            return f"<th{title}{better}><span>{inner}</span></th>"

        head_new = TH.sub(head_cell, new.split("</thead>")[0])
        # only when the column count lines up, so a second wide table in the
        # report cannot pick up the master table's grouping by accident
        if aligned:
            head_new = head_new.replace("<thead>", "<thead>\n" + group_row(columns, sites), 1)
        new = head_new + "</thead>" + new.split("</thead>", 1)[1]
        if aligned:
            new = mark_cells(new, columns, roles, medians, T)
            return f'<div class="tablewrap">{modes(T)}<div class="scroll">{new}</div></div>'
        return f'<div class="scroll">{new}</div>'
    return TABLE.sub(fix, html)


def pair_sections(html, pairs):
    """Put the second named section beside the first and take it out of its old
    place. Only the tables sit in the columns; anything after a table drops
    below the pair at full width."""
    chunks = re.findall(r"<h2>.*?(?=<h2>|$)", html, flags=re.S)
    if not chunks:
        return html
    head = html[:html.index(chunks[0])]
    named = {re.search(r"<h2>(.*?)</h2>", c).group(1): c for c in chunks}
    order = list(chunks)
    for a_, b_ in pairs or []:
        if a_ not in named or b_ not in named:
            continue
        heads, tails = [], []
        for chunk in (named[a_], named[b_]):
            end = chunk.find("</table>")
            cut = end + len("</table>") if end >= 0 else len(chunk)
            heads.append(chunk[:cut])
            tails.append(chunk[cut:])
        merged = (f'<div class="cols even"><div>{heads[0]}</div><div>{heads[1]}</div></div>'
                  + "".join(tails))
        order[order.index(named[a_])] = merged
        order.remove(named[b_])
    return head + "".join(order)


TOOL_P = re.compile(r"<p>(<strong>\[[^\]]+\].*?)</p>", re.S)
URL = re.compile(r"<code>((?:https?://)?[a-z0-9][a-z0-9.-]*\.[a-z]{2,}[^<\s]*)</code>")


def tool_cards(body):
    """Any paragraph opening with a [TAG] is a tooling entry, whatever the
    report's language calls that section."""
    def card(m):
        chunk = m.group(1)
        u = URL.search(chunk)
        href = ""
        if u:
            href = u.group(1)
            if not href.startswith("http"):
                href = "https://" + href

        def short_seg(x):
            # a provenance or a date is short; a sentence is detail
            return "<code>" not in x and len(re.sub(r"<[^>]+>", "", x)) <= 46

        # the visible line is the name, the provenance and the date. Everything
        # past them is detail worth a click, not worth a paragraph.
        segs = re.split(r"\s*(?:&middot;|\u00b7)\s*", chunk)
        head = " &middot; ".join([segs[0]] + [x for x in segs[1:3] if short_seg(x)]).strip()
        rest = [x for x in segs[1:] if "&middot; " + x not in head and x != segs[0]]
        tail = re.sub(r"<[^>]+>", "", " ".join(rest)).strip()
        if href and not tail:
            return (f'<a class="tool" href="{href}" target="_blank" rel="noopener">'
                    f'<span class="go">open &rarr;</span>{head}</a>')
        link = (f'<p class="go-link"><a href="{href}" target="_blank" rel="noopener">'
                f'{u.group(1)}</a></p>' if href else "")
        # the open panel carries what the summary left out, not the whole entry
        body_ = " &middot; ".join(rest) or chunk
        return (f'<details class="tool"><summary><span class="go">details</span>{head}'
                f'</summary><div class="tool-body"><p>{body_}</p>{link}</div></details>')

    return TOOL_P.sub(card, body)


NAME_JS = """<script>
document.querySelectorAll('.cols table td:first-child').forEach(td =>
  td.title = td.textContent.trim());
</script>"""

def contents(body):
    """Anchor every section and list them down the left margin.

    The link text is the heading up to its first bracket: a role heading
    carries its formula, and the formula does not fit a 190px column.
    """
    seen = {}

    def anchor(m):
        text = re.sub(r"<[^>]+>", "", m.group(1))
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "section"
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        items.append((slug, text.split("(")[0].strip()))
        return f'<h2 id="{slug}">{m.group(1)}</h2>'

    items = []
    body = re.sub(r"<h2>(.*?)</h2>", anchor, body, flags=re.S)
    if len(items) < 3:
        return body, ""
    links = "".join(f'<a href="#{sl}">{t}</a>' for sl, t in items)
    return body, f'<nav class="toc"><b>sections</b>{links}</nav>'


TOC_JS = """<script>
(() => {
  const links = [...document.querySelectorAll('.toc a')];
  if (!links.length) return;
  const heads = links.map(a => document.getElementById(a.hash.slice(1)));
  const mark = () => {
    // the section a reader is in is the last one whose heading is above the
    // middle of the screen
    let k = 0;
    heads.forEach((h, i) => { if (h.getBoundingClientRect().top < innerHeight / 2) k = i; });
    links.forEach((a, i) => a.classList.toggle('on', i === k));
  };
  addEventListener('scroll', mark, {passive: true});
  mark();
})();
</script>"""


def side_by_side(html, roles=None, skip=()):
    """Two columns wherever a section has two things that read side by side.

    A role section is a chart and a four row table: chart left, table right,
    the reasoning below both at full width. A section with a table and prose
    puts the table left and the prose right.

    The master table is excluded: it is `<table class="wide">` in a scroll
    container and needs every pixel it has.
    """
    def fix(m):
        chunk = m.group(0)
        name = re.search(r"<h2>(.*?)</h2>", chunk)
        if (name.group(1) if name else None) in skip:
            return chunk
        t = re.search(r"<table>.*?</table>", chunk, re.S)
        if not t:
            return chunk
        c = re.search(r'<div class="charts[^"]*">.*?</figure>\s*</div>', chunk, re.S)
        if c and c.end() <= t.start():
            # chart left, table right, and the pick under the table in the same
            # column: it is about that table, not about the section
            head = chunk[:c.start()]
            tail = chunk[t.end():]
            return (head + '<div class="cols even"><div>' + c.group(0) + "</div><div>"
                    + t.group(0) + tail + "</div></div>")
        rest = chunk[t.end():]
        if "<p>" not in rest:
            return chunk
        return (chunk[:t.start()] + '<div class="cols"><div>' + t.group(0)
                + "</div><div>" + rest + "</div></div>")

    return re.sub(r"<h2>.*?(?=<h2>|$)", fix, html, flags=re.S)


def main(profile_path):
    P = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    here = Path(P.get("out") or Path(profile_path).parent)
    src = here / P["report"]
    dst = src.with_suffix(".html")

    results = here / "results.json"
    data = json.loads(results.read_text(encoding="utf-8")) if results.exists() else {}
    columns, roles = data.get("columns"), data.get("roles")

    # merged per call, never into the module dict: two profiles built in one
    # process would otherwise hand each other their benchmark definitions.
    gloss = {**GLOSSARY, **(P.get("glossary") or {})}
    md_text = swap_charts(add_tooltips(src.read_text(encoding="utf-8"), gloss), here)
    body = _markdown().markdown(md_text, extensions=["tables", "fenced_code", "md_in_html"])
    pairs = P.get("pair_sections") or []
    T = strings(P)
    body = side_by_side(rotate_wide(body, columns, roles, data.get("medians"), data.get("sites"), T), roles,
                        skip={n for pair in pairs for n in pair} | set(P.get("full_width", [])))
    body = pair_sections(body, pairs)
    body = re.sub(r"<h2>([^<(]+?) (\([^<]*\))</h2>",
                  r'<h2>\1 <span class="wt">\2</span></h2>', body)
    body = tool_cards(body)
    body, nav = contents(body)
    script = ((JS if 'name="fill"' in body else "") + (TOC_JS if nav else "")
              + (NAME_JS if '<div class="cols' in body else ""))
    dst.write_text(f'<!doctype html><html lang="{P.get("language", "en")}">'
                   f'<meta charset=utf-8><title>{P["title"]}</title>'
                   f"<style>{CSS}</style>{nav}{body}{script}", encoding="utf-8")
    print("wrote", dst.name, "tooltips:", body.count("<abbr"), "wide tables:", body.count('class="wide'))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit("usage: build_html.py reports/<date>-<slug>/profile.json\nrun it through uv so markdown comes with it:\n  uv run --with markdown python pipeline/build_html.py <profile>")
    main(sys.argv[1])
