"""Markdown -> HTML for the shortlist, with hover tooltips on benchmark jargon.
Run: uv run --with markdown python reports/20260902/build_html.py
"""
import re
from pathlib import Path

import markdown

HERE = Path(__file__).parent
SRC = HERE / "erp-oracle-apex-model-shortlist.md"
DST = HERE / "erp-oracle-apex-model-shortlist.html"

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
    "stderr": "Standard error of the mean. A lead under two combined stderr is not significant.",
    "DeepSWE": "Datacurve's long-horizon software engineering benchmark: 113 tasks across 91 repositories, every "
               "model run under the mini-swe-agent scaffold.",
    "mini-swe-agent": "The single agent scaffold DeepSWE uses for every model.",
    "IFBench": "Instruction-following benchmark reported by Artificial Analysis, 0-1.",
    "Batch idx": "Batch role index, see Four indexes.",
    "Interactive idx": "Interactive role index, see Four indexes.",
    "Quality idx": "Quality role index: 0.40 Coding + 0.30 Agentic + 0.30 non-hallucination, see Four indexes.",
    "max effort": "Reasoning effort setting. Higher effort spends more thinking tokens; per-token price stays flat, "
                  "cost per task does not.",
    "xhigh": "Reasoning effort one step below max.",
    "MRCR": "Multi-round co-reference: long-context retrieval test, 0-100. Meta reports it for Muse Spark 1.3.",
    "Contributor tier": "Meta Model API price tier where prompts and outputs are used to train Meta models.",
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


def swap_charts(md_text):
    """Replace ![alt](NN.png) with the interactive NN.html when it exists; group
    consecutive charts into a grid of at most two per row."""
    out, group = [], []

    def flush():
        if not group:
            return
        n = min(len(group), 2)
        out.append(f'<div class="charts n{n}">' + "".join(group) + "</div>\n")
        group.clear()

    for line in md_text.split("\n"):
        m = IMG.match(line)
        if not m:
            if line.strip():
                flush()
            out.append(line)
            continue
        alt, png = m.groups()
        html = HERE / png.replace(".png", ".html")
        if html.exists():
            group.append(f'<figure>{html.read_text(encoding="utf-8")}'
                         f'<figcaption>{alt} (interactive: hover, zoom, click legend)</figcaption></figure>')
        else:
            group.append(f'<figure><img src="{png}" alt="{alt}"><figcaption>{alt}</figcaption></figure>')
    flush()
    return "\n".join(out)


CSS += (".charts{display:grid;gap:16px;margin:20px 0}.charts.n1{grid-template-columns:1fr}"
        ".charts.n2{grid-template-columns:1fr 1fr}.charts figure{margin:0;min-width:0}"
        ".charts figcaption{font:12px monospace;color:#555;margin-top:4px}"
        "@media(max-width:900px){.charts.n2{grid-template-columns:1fr}}")

md_text = swap_charts(add_tooltips(SRC.read_text(encoding="utf-8")))
body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "md_in_html"])
DST.write_text(f'<!doctype html><meta charset=utf-8><title>ERP / APEX model shortlist</title>'
               f"<style>{CSS}</style>{body}", encoding="utf-8")
print("wrote", DST.name, "tooltips:", body.count("<abbr"))
