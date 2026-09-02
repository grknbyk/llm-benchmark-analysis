"""Build the landing page from the reports that exist, so it can never drift
from them.

Run: python pipeline/build_index.py

Reads every reports/*/profile.json and the results.json beside it. A report with
no results.json yet still gets a card, just without the picks.
"""
import json
import sys
from pathlib import Path

BG, INK, MUTED, LINE = "#FBFAF6", "#1A1A1A", "#6A6A6A", "#E3E1D8"

CSS = f"""
*{{box-sizing:border-box}}
body{{background:{BG};color:{INK};margin:0;padding:64px 24px 96px;
     font:16px/1.6 Georgia,'DejaVu Serif',serif}}
main{{max-width:56rem;margin:0 auto}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px}}
.tabs span{{font:11px/1 'DejaVu Sans Mono',monospace;letter-spacing:.08em;padding:7px 10px;
           background:#E9EEE7;color:{INK};font-weight:700}}
.tabs span.off{{background:transparent;color:#8A8A8A;font-weight:400}}
h1{{font-size:2rem;margin:0 0 6px;letter-spacing:-.01em}}
.lede{{color:{MUTED};margin:0 0 8px;max-width:44rem}}
.stamp{{font:11px 'DejaVu Sans Mono',monospace;color:{MUTED};letter-spacing:.08em;margin-bottom:40px}}
.card{{border-top:1px solid {LINE};padding:26px 0}}
.card h2{{font-size:1.25rem;margin:0 0 4px}}
.card h2 a{{color:{INK};text-decoration:none}}
.card h2 a:hover{{text-decoration:underline}}
.stack{{font:12px 'DejaVu Sans Mono',monospace;color:{MUTED};margin:0 0 14px}}
.facts{{display:flex;flex-wrap:wrap;gap:0 26px;font:12px 'DejaVu Sans Mono',monospace;
        color:{MUTED};margin:0 0 16px}}
.facts b{{color:{INK};font-weight:700}}
table{{border-collapse:collapse;width:100%;font:13px/1.45 'DejaVu Sans Mono',monospace}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid {LINE};vertical-align:top}}
th{{font-size:11px;letter-spacing:.06em;color:{MUTED};font-weight:400;text-transform:uppercase}}
td.role{{color:{MUTED}}}
td b{{font-weight:700}}
.tag{{font-size:11px;color:{MUTED}}}
.links{{margin-top:14px;font:12px 'DejaVu Sans Mono',monospace}}
.links a{{color:{INK};margin-right:18px}}
footer{{border-top:1px solid {LINE};margin-top:40px;padding-top:22px;
        font:12px/1.7 'DejaVu Sans Mono',monospace;color:{MUTED}}}
footer b{{color:{INK}}}
"""

SITES = ("artificial-analysis vals-ai deepswe livebench lmarena terminal-bench "
         "arc-prize epoch-ai design-arena benchlm").split()


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pick_rows(res):
    rows = []
    labels = {r["slug"]: r["name"] for r in res["roles"]}
    for slug, p in res["picks"].items():
        best = "no model has every input" if not p["best"] else \
            f'<b>{esc(p["best"]["model"])}</b> <span class="tag">{p["best"]["score"]:g}</span>'
        cheap = '<span class="tag">none qualifies</span>' if not p["cheap"] else \
            f'<b>{esc(p["cheap"]["model"])}</b> <span class="tag">{p["cheap"]["score"]:g}, ' \
            f'{p["cheap"]["times_cheaper"]:g}x cheaper</span>'
        rows.append(f'<tr><td class="role">{esc(labels.get(slug, slug))}</td>'
                    f"<td>{best}</td><td>{cheap}</td></tr>")
    return ("<table><tr><th>role</th><th>best model</th><th>cheap alternative</th></tr>"
            + "".join(rows) + "</table>")


def card(profile_path):
    P = json.loads(profile_path.read_text(encoding="utf-8"))
    here = Path(P.get("out") or profile_path.parent)
    href = (here / P["report"]).with_suffix(".html").as_posix()
    res_path = here / "results.json"

    facts = [f'data <b>{esc(Path(P["data"]).name)}</b>',
             f'sources <b>{len(P["scoring_sources"])}</b>',
             f'roles <b>{len(P["roles"])}</b>']
    body = ""
    if res_path.exists():
        res = json.loads(res_path.read_text(encoding="utf-8"))
        facts.append(f'models <b>{len(res["roles"][0]["scores"])}</b>')
        facts.append(f'metrics <b>{len(res["benchmarks"])}</b>')
        body = pick_rows(res)

    links = [f'<a href="{href}">report</a>',
             f'<a href="{(here / P["report"]).as_posix()}">markdown</a>']
    if res_path.exists():
        links.append(f'<a href="{res_path.as_posix()}">results.json</a>')
    links.append(f'<a href="{(here / "profile.json").as_posix()}">profile.json</a>')

    return (f'<section class="card"><h2><a href="{href}">{esc(P["title"])}</a></h2>'
            f'<p class="stack">{esc(P["stack"])}</p>'
            f'<div class="facts">{"".join(f"<span>{f}</span>" for f in facts)}</div>'
            f'{body}<div class="links">{"".join(links)}</div></section>')


def main():
    profiles = sorted(Path("reports").glob("*/profile.json"), reverse=True)
    if not profiles:
        print("no reports/*/profile.json found; nothing to build")
        return
    loaded = [json.loads(p.read_text(encoding="utf-8")) for p in profiles]
    newest = max(d["data"] for d in loaded)
    # The tab strip names the sites that actually scored the reports on this
    # page. A fixed slice of SITES spotlights one stack's sources forever.
    scoring = list(dict.fromkeys(s for d in loaded for s in d.get("scoring_sources", [])))
    tabs = "".join(f'<span class="{"" if i == 0 else "off"}">{s.upper()}</span>'
                   for i, s in enumerate(["REPORTS"] + scoring))

    html = (
        "<!doctype html><html lang=en><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        "<title>LLM benchmark analysis</title>"
        f"<style>{CSS}</style><main>"
        f'<div class="tabs">{tabs}</div>'
        "<h1>LLM benchmark analysis</h1>"
        '<p class="lede">Model shortlists for a technology stack, built from ten public '
        "leaderboards rather than vendor claims. Each report derives its own weighted role "
        "indexes from the work that stack involves, and every number in it comes out of the "
        "scoring engine.</p>"
        f'<p class="stamp">{len(profiles)} REPORT{"S" if len(profiles) > 1 else ""} '
        f"&middot; NEWEST DATA {Path(newest).name}</p>"
        + "".join(card(p) for p in profiles)
        + "<footer><b>Sources.</b> " + ", ".join(SITES) + ".<br>"
        "<b>Method.</b> A model missing a benchmark is excluded from that index, never imputed, "
        "so an empty cell means the leaderboard has no row for it. Price and latency are "
        "scored relative to the candidate set, not on an absolute scale.<br>"
        "<b>Rebuild.</b> python pipeline/build_index.py</footer></main></html>")

    Path("index.html").write_text(html, encoding="utf-8")
    print(f"wrote index.html for {len(profiles)} report(s)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
