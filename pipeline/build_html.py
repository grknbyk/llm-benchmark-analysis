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

try:
    import markdown
except ImportError:
    raise SystemExit("build_html.py needs the markdown package. Either pip install -r requirements.txt,\nor let uv fetch it per run:\n  uv run --with markdown python pipeline/build_html.py <profile>")

WIDE_AT = 8

GLOSSARY = {
    "TTFT": "Time to first token: seconds from sending the request until the first output token arrives. "
            "For Anthropic and OpenAI models this includes hidden reasoning time.",
    "E2E": "End-to-end response time: median seconds from request to complete answer (Artificial Analysis).",
    "AA-LCR": "Artificial Analysis Long Context Reasoning, 0-1. Proxy for handling large schemas and long packages.",
    "Code Migration": "Vals AI benchmark: reimplement real programs in another language (CLI, COBOL, code quality "
                      "subtasks). Private set, 0-100, published with stderr.",
    "Code Mig.": "Vals AI Code Migration benchmark, 0-100.",
    "CorpFin v2": "Vals AI benchmark: reasoning over long corporate credit agreements. 0-100, with stderr.",
    "Non-halluc": "AA-Omniscience non-hallucination rate, 0-1: share of unknown questions where the model declines "
                  "instead of inventing an answer.",
    "non-hallucination": "AA-Omniscience non-hallucination rate, 0-1: share of unknown questions where the model "
                         "declines instead of inventing an answer.",
    "acc": "AA-Omniscience accuracy, 0-1: share of questions answered correctly. Read together with "
           "non-hallucination: high refusal plus low accuracy means the model abstains rather than knows.",
    "Coding": "Artificial Analysis Coding Index, 0-100.",
    "Agentic": "Artificial Analysis Agentic Index, 0-100: multi-step, tool-using tasks.",
    "$/1M": "Artificial Analysis blended price per 1M tokens at a 3:1 input:output ratio.",
    "$/task": "DeepSWE v1.1 mean USD per completed task, thinking tokens included.",
    "pass@1": "Share of tasks solved on the first attempt.",
    "frontier": "Price and score frontier: the models nothing else in the candidate set beats on both price and overall index at the same time. Everything off it is beaten on both.",
    "stderr": "Standard error of the mean. A lead under two combined stderr is not significant.",
    "DeepSWE": "Datacurve's long-horizon software engineering benchmark: 113 tasks across 91 repositories, every "
               "model run under the mini-swe-agent scaffold.",
    "mini-swe-agent": "The single agent scaffold DeepSWE uses for every model.",
    "IFBench": "Instruction-following benchmark reported by Artificial Analysis, 0-1.",
    "Elo": "Rating from pairwise human votes. Differences under about 20 points are usually not meaningful.",
    "MCP": "Model Context Protocol: the interface a model uses to reach an external tool or data source. "
           "An MCP server is code that runs on your machine.",
    "max effort": "Reasoning effort setting. Higher effort spends more thinking tokens; per-token price stays flat, "
                  "cost per task does not.",
    "xhigh": "Reasoning effort one step below max.",
    "Intelligence Index": "Artificial Analysis composite of knowledge, reasoning, coding and agentic evals, 0-100.",
    "Vals": "Vals AI, independent benchmark publisher (vals.ai).",
    "Artificial Analysis": "Independent model benchmark and pricing tracker (artificialanalysis.ai).",
}

CSS = (
    "body{max-width:1400px;margin:40px auto;font:16px/1.55 Georgia,serif;color:#1a1a1a;background:#fbfaf6;"
    "padding:0 24px}h1,h2{font-weight:600}table{border-collapse:collapse;font:13px/1.4 monospace;margin:16px 0}"
    "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}th{background:#e9eee7}"
    "img{max-width:100%;display:block;margin:20px 0;border:1px solid #ddd}"
    "code{font:13px monospace;background:#eee;padding:1px 4px}"
    "abbr{text-decoration:underline dotted #888;cursor:help}"
    ".charts{display:grid;gap:16px;margin:20px 0}.charts.n1{grid-template-columns:1fr}"
    ".charts.n2{grid-template-columns:1fr 1fr}.charts figure{margin:0;min-width:0}"
    ".charts figcaption{font:12px monospace;color:#555;margin-top:4px}"
    "@media(max-width:900px){.charts.n2{grid-template-columns:1fr}}"
    ".scroll{overflow-x:auto;margin:20px 0}"
    ".cols{display:grid;grid-template-columns:minmax(0,max-content) minmax(0,1fr);gap:28px;align-items:start;margin:16px 0}"
    ".cols>div:first-child{max-width:540px}.card{overflow-wrap:anywhere}"
    ".cols>div>table{margin-top:0}.cols>div>p:first-child{margin-top:0}"
    ".card{border:1px solid #d3cfc0;background:#F5F3EB;padding:10px 12px;margin-top:14px;font:12px monospace;color:#3a3a3a;line-height:1.55}"
    ".card b{display:block;font:11px monospace;color:#6a6a6a;letter-spacing:.04em;text-transform:uppercase;margin-bottom:3px}"
    ".card b~b{margin-top:9px}"
    "@media(max-width:900px){.cols{grid-template-columns:1fr;gap:0}}"
    "table.wide th{background:none;border:none;height:96px;vertical-align:bottom;padding:0;"
    "position:relative}"
    "table.wide th>span{position:absolute;bottom:6px;left:50%;transform-origin:left bottom;"
    "transform:rotate(-45deg);white-space:nowrap;font:12px monospace;"
    "border:1px solid #d3cfc0;background:#F2F0E7;padding:2px 7px;border-radius:2px}"
    "table.wide th[title]{cursor:help}"
    "table.wide th:first-child>span{position:static;transform:none;border:none;background:none;padding:0}"  # the row label reads flat

    "table.wide td{white-space:nowrap;text-align:right}table.wide td:first-child{text-align:left}"
    "table.wide th:first-child,table.wide td:first-child{position:sticky;left:0;background:#fbfaf6}"
    "table.wide tr.grp th{height:auto;position:static;padding:2px 6px;text-align:center;"
    "font:11px monospace;color:#4a4a4a;letter-spacing:.04em;border:1px solid #c9c5b4;background:#EFEDE3}"
    "table.wide tr.grp th:first-child{border:none;background:none}"
    "table.grouped th.gs,table.grouped tr:not(.grp) td.gs{border-left:2px solid #b8b3a1}"
    "table.grouped th:last-child,table.grouped tr:not(.grp) td:last-child{border-right:2px solid #b8b3a1}"
)


def add_tooltips(md_text):
    # One pass with a single alternation: replaced text is never rescanned, so a
    # term inside another term's tooltip cannot be wrapped again. Longest first
    # so "Code Migration" wins over "Coding"-style partial hits.
    terms = sorted(GLOSSARY, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w\[/-])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w\]/-])")

    # Only the first hit per term. Underlining all 25 mentions of MCP turns a
    # definition into decoration, and a reader who wants it scrolls up once.
    seen = set()

    def wrap(m):
        term = m.group(1)
        if term in seen:
            return term
        seen.add(term)
        return f'<abbr title="{GLOSSARY[term].replace(chr(34), "&quot;")}">{term}</abbr>'

    # skip image lines and headings: paths and titles must stay clean
    return "\n".join(line if line.startswith(("![", "#")) else pattern.sub(wrap, line)
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
            group.append(f'<figure>{html.read_text(encoding="utf-8")}'
                         f'<figcaption>{alt} (interactive: hover for the breakdown)</figcaption></figure>')
        else:
            group.append(f'<figure><img src="{png}" alt="{alt}"><figcaption>{alt}</figcaption></figure>')
    flush()
    return "\n".join(out)


TABLE = re.compile(r"<table>\s*<thead>.*?</table>", re.S)
TH = re.compile(r"<th(?:\s[^>]*)?>(.*?)</th>", re.S)  # (?:\s...) so <thead> is not a match


def group_row(columns):
    """One header cell per run of columns from the same source, so a reader can
    see at a glance which site a number came from. Columns arrive already sorted
    by site, so consecutive runs are the whole story."""
    cells = ['<th class="grp"></th>']
    site, span = columns[0]["site"], 0
    for c in columns + [{"site": None}]:
        if c["site"] == site:
            span += 1
            continue
        cells.append(f'<th class="grp" colspan="{span}">{site}</th>')
        site, span = c["site"], 1
    return '<tr class="grp">' + "".join(cells) + "</tr>"


def mark_groups(block, columns):
    """Tag the first cell of each site run so the CSS can draw one rule down the
    whole table. A colspan label alone leaves a reader counting columns to work
    out where artificial-analysis stops and vals-ai starts."""
    starts, site = set(), None
    for i, c in enumerate(columns, start=1):   # 0 is the model column
        if c["site"] != site:
            starts.add(i)
            site = c["site"]

    def row(m):
        cells = re.split(r"(?=<t[dh])", m.group(0))
        out = [c if i - 1 not in starts else re.sub(r"^<(t[dh])", r'<\1 class="gs"', c, count=1)
               for i, c in enumerate(cells)]
        return "".join(out)

    return re.sub(r"<tr>.*?</tr>", row, block, flags=re.S)


def rotate_wide(html, columns=None):
    """A table past WIDE_AT columns is unreadable with flat headers, so rotate
    them. The header text moves into a span because a rotated th collapses the
    row height otherwise."""
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
            label = columns[i - 1].get("label") if aligned and i else None
            title = f' title="{label}"' if label and label != t.group(1).strip() else ""
            return f"<th{title}><span>{t.group(1).strip()}</span></th>"

        head_new = TH.sub(head_cell, new.split("</thead>")[0])
        # only when the column count lines up, so a second wide table in the
        # report cannot pick up the master table's grouping by accident
        if aligned:
            head_new = head_new.replace("<thead>", "<thead>\n" + group_row(columns), 1)
        new = head_new + "</thead>" + new.split("</thead>", 1)[1]
        if aligned:
            new = mark_groups(new, columns)
        return f'<div class="scroll">{new}</div>'
    return TABLE.sub(fix, html)


def role_card(role):
    """Formula first, because it explains the column the reader just looked at.
    Then the candidates the role could not score, named with the input each one
    lacked. An empty cell is a fact, and this is where it gets said."""
    out = [f'<b>How this index is built</b>{role["formula"]}']
    gaps = role.get("not_scored") or []
    if gaps:
        out.append("<b>Not scored</b>" + "<br>".join(
            f'{g["model"]}, no {" or ".join(g["missing"])}' for g in gaps))
    return '<div class="card">' + "".join(out) + "</div>"


def side_by_side(html, roles=None):
    """A role section is a small table and three short paragraphs about it. Read
    down the page they are two thirds white space, so pair them: the table on
    the left at its natural width, the reasoning filling the rest.

    Only plain tables qualify. The master table is `<table class="wide">` inside
    a scroll container and has to keep the full width it already needs."""
    def fix(m):
        chunk = m.group(0)
        t = re.search(r"<table>.*?</table>", chunk, re.S)
        if not t:
            return chunk
        rest = chunk[t.end():]
        if "<p>" not in rest:            # nothing to put beside it
            return chunk
        name = re.search(r"<h2>(.*?)</h2>", chunk)
        role = next((r for r in (roles or []) if r["name"] == (name.group(1) if name else None)), None)
        left = t.group(0) + (role_card(role) if role else "")
        return (chunk[:t.start()] + '<div class="cols"><div>' + left
                + "</div><div>" + rest + "</div></div>")

    return re.sub(r"<h2>.*?(?=<h2>|$)", fix, html, flags=re.S)


def main(profile_path):
    P = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    here = Path(P.get("out") or Path(profile_path).parent)
    src = here / P["report"]
    dst = src.with_suffix(".html")
    GLOSSARY.update(P.get("glossary", {}))

    results = here / "results.json"
    data = json.loads(results.read_text(encoding="utf-8")) if results.exists() else {}
    columns, roles = data.get("columns"), data.get("roles")

    md_text = swap_charts(add_tooltips(src.read_text(encoding="utf-8")), here)
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "md_in_html"])
    body = side_by_side(rotate_wide(body, columns), roles)
    dst.write_text(f'<!doctype html><meta charset=utf-8><title>{P["title"]}</title>'
                   f"<style>{CSS}</style>{body}", encoding="utf-8")
    print("wrote", dst.name, "tooltips:", body.count("<abbr"), "wide tables:", body.count('class="wide'))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit("usage: build_html.py reports/<date>-<slug>/profile.json\nrun it through uv so markdown comes with it:\n  uv run --with markdown python pipeline/build_html.py <profile>")
    main(sys.argv[1])
