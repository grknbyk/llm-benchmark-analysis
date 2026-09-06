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
    "table.wide th{background:none;border:none;height:96px;vertical-align:bottom;padding:0;"
    "position:relative}"
    "table.wide th>span{position:absolute;bottom:6px;left:50%;transform-origin:left bottom;"
    "transform:rotate(-45deg);white-space:nowrap;font:12px monospace}"
    "table.wide th:first-child>span{position:static;transform:none}"  # the row label reads flat

    "table.wide td{white-space:nowrap;text-align:right}table.wide td:first-child{text-align:left}"
    "table.wide th:first-child,table.wide td:first-child{position:sticky;left:0;background:#fbfaf6}"
    "table.wide tr.grp th{height:auto;position:static;padding:0 6px 3px;text-align:center;"
    "font:11px monospace;color:#6a6a6a;border-bottom:1px solid #c9c5b4;letter-spacing:.04em}"
    "table.wide tr.grp th:first-child{border-bottom:none}"
)


def add_tooltips(md_text):
    # One pass with a single alternation: replaced text is never rescanned, so a
    # term inside another term's tooltip cannot be wrapped again. Longest first
    # so "Code Migration" wins over "Coding"-style partial hits.
    terms = sorted(GLOSSARY, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w\[/-])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w\]/-])")

    def wrap(m):
        term = m.group(1)
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
        new = block.replace("<table>", '<table class="wide">', 1)
        head_new = TH.sub(lambda t: f"<th><span>{t.group(1).strip()}</span></th>",
                          new.split("</thead>")[0])
        # only when the column count lines up, so a second wide table in the
        # report cannot pick up the master table's grouping by accident
        if columns and len(columns) == len(ths) - 1:
            head_new = head_new.replace("<thead>", "<thead>\n" + group_row(columns), 1)
        new = head_new + "</thead>" + new.split("</thead>", 1)[1]
        return f'<div class="scroll">{new}</div>'
    return TABLE.sub(fix, html)


def main(profile_path):
    P = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    here = Path(P.get("out") or Path(profile_path).parent)
    src = here / P["report"]
    dst = src.with_suffix(".html")
    GLOSSARY.update(P.get("glossary", {}))

    results = here / "results.json"
    columns = json.loads(results.read_text(encoding="utf-8")).get("columns") if results.exists() else None

    md_text = swap_charts(add_tooltips(src.read_text(encoding="utf-8")), here)
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "md_in_html"])
    body = rotate_wide(body, columns)
    dst.write_text(f'<!doctype html><meta charset=utf-8><title>{P["title"]}</title>'
                   f"<style>{CSS}</style>{body}", encoding="utf-8")
    print("wrote", dst.name, "tooltips:", body.count("<abbr"), "wide tables:", body.count('class="wide"'))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit("usage: build_html.py reports/<date>-<slug>/profile.json\nrun it through uv so markdown comes with it:\n  uv run --with markdown python pipeline/build_html.py <profile>")
    main(sys.argv[1])
