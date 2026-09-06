"""Write BLUEPRINT.html: the report layout as a wireframe you can annotate.

Run: python pipeline/build_blueprint.py

Every block is an empty box with a one word label and room to write in. Notes
survive a reload, and the export button copies them as markdown.

It imports the stylesheet the report itself uses, so the columns, the chart
grids and the table corner sit where they sit in a real report. A drawing
drifts from the code; this cannot.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_html import CSS  # noqa: E402

EXTRA = (
    ".bp{max-width:1400px;margin:0 auto 120px}"
    ".bp h2{margin:38px 0 4px}"
    ".bp .why{font:13px/1.5 Georgia,serif;color:#555;margin:0 0 12px;max-width:900px}"
    ".ph{border:1px dashed #b8b3a1;background:#F5F3EB;border-radius:2px;"
    "padding:8px 10px;min-height:52px;display:flex;flex-direction:column;gap:6px}"
    ".ph.chart{min-height:200px}.ph.wide{min-height:240px}"
    ".ph.text{min-height:78px}.ph.tall{min-height:150px}"
    ".lbl{font:11px monospace;color:#8a8478;letter-spacing:.06em;text-transform:uppercase}"
    ".note{flex:1;font:13px/1.5 monospace;color:#1a1a1a;outline:none;min-height:20px;"
    "white-space:pre-wrap}"
    ".note:empty::before{content:attr(data-hint);color:#bdb7a8}"
    ".note:focus{background:#fff;box-shadow:inset 0 0 0 1px #d3cfc0}"
    ".ph:has(.note:not(:empty)){border-style:solid;border-color:#A8452F;background:#FBF6F2}"
    ".corner{position:absolute;left:0;top:52px;z-index:3;width:190px}"
    ".rule{border:none;border-top:1px solid #ddd8c8;margin:44px 0 0}"
    "#bar{position:fixed;right:24px;bottom:24px;z-index:9;display:flex;gap:8px;"
    "align-items:center;background:#F5F3EB;border:1px solid #d3cfc0;border-radius:3px;"
    "padding:8px 12px;font:12px monospace;box-shadow:0 2px 10px rgba(0,0,0,.12)}"
    "#bar button{font:12px monospace;cursor:pointer;border:1px solid #b0aa99;"
    "background:#fff;border-radius:2px;padding:5px 10px;color:#1a1a1a}"
    "#bar button:hover{background:#efece3}"
    "#count{color:#6a6a6a}"
)

JS = """<script>
(() => {
  const notes = [...document.querySelectorAll('.note')];
  const count = document.getElementById('count');
  const KEY = 'blueprint-notes';
  const saved = JSON.parse(localStorage.getItem(KEY) || '{}');

  notes.forEach(n => { if (saved[n.dataset.id]) n.textContent = saved[n.dataset.id]; });

  const filled = () => notes.filter(n => n.textContent.trim());
  const tally = () => count.textContent = `${filled().length} note(s)`;

  const save = () => {
    const o = {};
    notes.forEach(n => { const v = n.textContent.trim(); if (v) o[n.dataset.id] = v; });
    localStorage.setItem(KEY, JSON.stringify(o));
    tally();
  };
  notes.forEach(n => n.addEventListener('input', save));

  const markdown = () => {
    let out = ['# Blueprint notes', ''];
    document.querySelectorAll('section[data-section]').forEach(s => {
      const mine = [...s.querySelectorAll('.note')].filter(n => n.textContent.trim());
      if (!mine.length) return;
      out.push(`## ${s.dataset.section}`, '');
      mine.forEach(n => out.push(`- **${n.dataset.label}**: ${n.textContent.trim()}`));
      out.push('');
    });
    return out.join('\\n');
  };

  document.getElementById('copy').onclick = async () => {
    const md = markdown();
    if (!filled().length) { count.textContent = 'nothing to copy'; return; }
    try { await navigator.clipboard.writeText(md); count.textContent = 'copied'; }
    catch (e) {
      const t = document.createElement('textarea');
      t.value = md; document.body.appendChild(t); t.select();
      document.execCommand('copy'); t.remove(); count.textContent = 'copied';
    }
    setTimeout(tally, 1500);
  };

  document.getElementById('clear').onclick = () => {
    if (!confirm('Clear every note?')) return;
    notes.forEach(n => n.textContent = '');
    localStorage.removeItem(KEY);
    tally();
  };

  tally();
})();
</script>"""

_seq = [0]


def ph(label, cls=""):
    _seq[0] += 1
    return (f'<div class="ph {cls}"><span class="lbl">{label}</span>'
            f'<div class="note" contenteditable="plaintext-only" spellcheck="false" '
            f'data-id="b{_seq[0]}" data-label="{label}" data-hint="note"></div></div>')


def sections():
    return [
        ("Read first",
         "Three blocks. The pick and the frontier are one thought, not two: the "
         "frontier is the evidence behind the pick, so it reads as one block "
         "that names the models and their prices.",
         ph("stack and data") + ph("the pick, with the frontier behind it")
         + ph("limits")),

        ("Indexes and picks",
         "One table, pasted from glance-table.md: index, weights, best model, "
         "cheap alternative. The weights that define an index and the pick that "
         "came out of it belong in the same row.",
         ph("table", "tall") + ph("paragraph")),

        ("Every model, every metric",
         "The master table, pasted from master-table.md. Vertical headers, "
         "columns grouped by source site and linked to it, n/a marked, ten rows "
         "shown, every column sorts. The fill control sits in the corner the "
         "table already wastes.",
         '<div class="tablewrap" style="min-height:300px">'
         + ph("control", "corner tall")
         + '<div style="margin-left:210px">'
         + ph("site groups") + ph("table", "wide") + ph("row count")
         + "</div></div>"),

        ("Lead chart",
         "An odd chart count puts the lead on a full width row and pairs the "
         "rest. Price against the overall index earns that place: it answers "
         "what to buy rather than what scores best.",
         '<div class="charts n1">' + ph("lead chart", "chart") + "</div>"
         + '<div class="charts n2">' + ph("chart", "chart") + ph("chart", "chart") + "</div>"),

        ("&lt;Role name&gt; (0.30 a + 0.25 b + ...)",
         "The formula is in the heading, so the section starts with the chart. "
         "Bar chart left. Table right, and the pick sits under that table in the "
         "same column, two or three lines. Repeats for each role.",
         '<div class="cols even"><div>' + ph("bar chart", "chart")
         + "</div><div>" + ph("table", "tall")
         + ph("pick, and the cheaper option", "text") + "</div></div>"),

        ("Cost, turns and time against a benchmark",
         "Built straight from the scrape, not from an index: cost against a "
         "benchmark, turns against it, time against it. The benchmark is the "
         "general one where a site has it, otherwise the one carrying the "
         "highest weight in the profile. No such pair in the data means the "
         "section does not appear at all. One chart takes a full row; two share "
         "a row.",
         '<div class="charts n2">' + ph("cost / benchmark", "chart")
         + ph("turns / benchmark", "chart") + "</div>"
         + '<div class="charts n1">' + ph("time / benchmark", "chart") + "</div>"),

        ("Stack tooling",
         "No subsection per technology. One block per tool, tagged by what it "
         "is and carrying its link, so the whole section is a short list rather "
         "than four essays.",
         ph("[MCP] name &middot; link &middot; official or community &middot; last commit")
         + ph("[SKILL] name &middot; link &middot; official or community &middot; last commit")
         + ph("[BEST PRACTICE] what changed in the window &middot; link &middot; date")),

        ("Caveats and references",
         "Caveats are numbered, one per limitation a reader would otherwise "
         "discover late. References name the scoring sites, the provenance sites "
         "and the tooling sources.",
         ph("caveats") + ph("references")),
    ]


RULES = [
    "Every number comes from results.json, master-table.md or glance-table.md. "
    "None is worked out in prose or in the browser.",
    "A missing input is never filled in silently. It is marked, explained, and "
    "the model is left out of the indexes that need it.",
    "Every claim names its source and its date.",
    "A chart earns its place by showing what the table cannot.",
    "Nothing publishes itself. The pipeline writes files.",
]


def main():
    body = ['<div class="bp"><h1>Report blueprint</h1>',
            '<p class="why">The page section by section, at the proportions the '
            'stylesheet actually produces. Write in any box; notes survive a '
            'reload and the export button copies them as markdown.</p>']
    for i, (title, why, wire) in enumerate(sections(), start=1):
        body.append(f'<section data-section="{i}. {title}"><hr class="rule">'
                    f'<h2>{i}. {title}</h2><p class="why">{why}</p>{wire}</section>')
    body.append('<hr class="rule"><h2>Rules that survive any rearrangement</h2><ol>'
                + "".join(f"<li>{r}</li>" for r in RULES) + "</ol></div>")
    body.append('<div id="bar"><span id="count"></span>'
                '<button id="copy">copy notes</button>'
                '<button id="clear">clear</button></div>')

    out = Path(__file__).parent.parent / "BLUEPRINT.html"
    out.write_text("<!doctype html><meta charset=utf-8><title>Report blueprint</title>"
                   f"<style>{CSS}{EXTRA}</style>" + "".join(body) + JS, encoding="utf-8")
    print("wrote", out.name, "boxes:", _seq[0])


if __name__ == "__main__":
    main()
