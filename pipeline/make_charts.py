"""Stack-generic index engine. Everything stack-specific lives in profile.json.

Run: uv run --with matplotlib --with pandas --with plotly python \
       pipeline/make_charts.py reports/<date>-<slug>/profile.json

Writes one chart per index (PNG + interactive HTML), a master table of every
metric, and results.json holding every raw value, every role formula and the
picks.
The report step reads those; it never recomputes a number.
"""
import json
import re
import sys
from pathlib import Path

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
except ImportError:
    raise SystemExit("make_charts.py needs matplotlib, pandas and plotly. Either pip install -r requirements.txt,\nor let uv fetch them per run:\n  uv run --with matplotlib --with pandas --with plotly python pipeline/make_charts.py <profile>")

BG, INK = "#FBFAF6", "#1A1A1A"
PAL = ["#E8927C", "#3D3D3D", "#5BB381", "#B8BCC4", "#C084E8", "#5B9BF0", "#5A6B8C",
       "#7B8CF0", "#F0923B", "#F0C75B", "#E8DCC8", "#8FD3C7", "#D98CB3", "#9BB0D8"]
MONO = "DejaVu Sans Mono, Menlo, monospace"
SERIF = "Georgia, DejaVu Serif, serif"

mpl.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
                     "font.family": "DejaVu Sans", "axes.edgecolor": INK})


# ---------- joining ----------

def key(name):
    """Collapse a model string to a join key. Provider prefixes, effort suffixes
    and punctuation differ across sites and carry no identity, so they go.
    Vals writes anthropic/claude-opus-5 where AA writes Claude Opus 5 (max)."""
    s = str(name).rsplit("/", 1)[-1]
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(adaptive reasoning|default fallback|max effort|effort|xhigh|high|medium|low|max)\b",
               " ", s, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match(k, pool):
    """Exact first. A prefix match is accepted only when it is unique, long
    enough to be an identity rather than a family, and not separated by a
    version digit, because a wrong join looks exactly like data.

    The version rule is why claude-fable-5 does not answer for Claude Fable 5.1.
    Those are different models with different scores, and the shorter name is a
    prefix of the longer one."""
    if k in pool:
        return k, "exact"
    if len(k) >= 8:
        near = [p for p in pool if p.startswith(k) or k.startswith(p)]
        if len(near) == 1 and len(near[0]) >= 8:
            long_, short = sorted([k, near[0]], key=len, reverse=True)
            if not long_[len(short):][:1].isdigit():
                return near[0], "prefix"
    return None, "-"


# ---------- data ----------

def load(base, site):
    rows = json.load(open(base / site / "normalized.json", encoding="utf-8"))
    df = pd.DataFrame([r for r in rows if isinstance(r, dict)])
    df["key"] = df.model.map(key)
    return df


def series(df, spec, by):
    """One value per model for a metric spec, best score winning when a site
    publishes several configurations. The primary source groups by the full
    model string, because an effort variant is a different product with its own
    price and latency; other sites group by the collapsed join key."""
    d = df
    if spec.get("benchmark"):
        d = d[d.benchmark == spec["benchmark"]]
    if spec.get("metric"):
        d = d[d.metric == spec["metric"]]
    if d.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    col = spec.get("field", "score")
    d = d.sort_values("score", ascending=False).groupby(by, as_index=True).first()
    val = pd.to_numeric(d[col], errors="coerce") * spec.get("scale", 1)
    err = pd.to_numeric(d["stderr"], errors="coerce") if spec.get("stderr") and "stderr" in d else pd.Series(dtype=float)
    return val, err


def short(m):
    """Display label. The effort wording differs per vendor and eats half the
    width of the master table without adding identity."""
    return (str(m).replace("(Adaptive Reasoning, ", "(").replace(", Default Fallback", "")
            .replace(" Effort", "").replace("Artificial Analysis ", "").strip())


def minmax(s, invert=False, log=False):
    v = np.log10(s) if log else s
    out = (v - v.min()) / (v.max() - v.min()) * 100
    return 100 - out if invert else out


# ---------- charts ----------

def dotgrid(ax):
    ax.set_axisbelow(True)
    ax.yaxis.set_minor_locator(mpl.ticker.AutoMinorLocator(4))
    ax.grid(True, which="both", axis="y", linestyle=(0, (1, 5)), color="#B5B5B5", linewidth=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(which="minor", length=0)


def figure(title, subtitle, active, tabs_, stamp):
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    fig.subplots_adjust(top=0.78, bottom=0.26, left=0.07, right=0.97)
    fig.text(0.04, 0.955, title, fontsize=19, family="serif", color=INK)
    fig.text(0.04, 0.845, subtitle, fontsize=10.5, color="#555")
    x = 0.04
    for it in tabs_:
        on = it == active
        fig.text(x, 0.905, ("- " if on else "  ") + it, fontsize=9, family="monospace",
                 color=INK if on else "#8A8A8A", fontweight="bold" if on else "normal",
                 bbox=dict(boxstyle="square,pad=0.45", fc="#E9EEE7" if on else BG, ec="none"))
        x += 0.045 + 0.0118 * len(it)
    fig.text(0.96, 0.905, stamp, fontsize=8.5, family="monospace", ha="right", color=INK, fontweight="bold")
    dotgrid(ax)
    return fig, ax


def bars(ax, labels, values):
    xs = range(len(values))
    ax.bar(xs, values, color=[PAL[i % len(PAL)] for i in xs], edgecolor=INK, linewidth=1.1)
    for i, v in zip(xs, values):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9, family="monospace")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)


def plotly_bars(labels, values, hover, title, subtitle, ytitle):
    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=[PAL[k % len(PAL)] for k in range(len(values))], line=dict(color=INK, width=1.1)),
        text=[f"{v:.1f}" for v in values], textposition="inside", insidetextanchor="end",
        textfont=dict(family=MONO, size=11), customdata=hover,
        hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:12px;color:#555'>{subtitle}</span>",
                   font=dict(family=SERIF, size=20, color=INK), x=0.01, xanchor="left"),
        paper_bgcolor=BG, plot_bgcolor=BG, height=520, margin=dict(l=50, r=20, t=90, b=40),
        font=dict(family=MONO, size=11, color=INK),
        hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="white"))
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=10), showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    fig.update_yaxes(title=ytitle, showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    return fig


def frontier(d, score, price):
    """Models that nothing else beats on both price and score at once. Walking
    up the price axis and keeping the running best score gives exactly that
    set, which is the shortlist a buyer can defend."""
    keep, best = [], -np.inf
    for m, r in d.sort_values(price).iterrows():
        if r[score] > best:
            best = r[score]
            keep.append(m)
    return keep


def plotly_scatter(d, price, unit, on, title, subtitle):
    import plotly.graph_objects as go
    fig = go.Figure()
    for name, idx, colour, size in (("frontier", on, PAL[0], 15), ("rest", [m for m in d.index if m not in on], "#B8BCC4", 11)):
        s = d.loc[idx]
        fig.add_trace(go.Scatter(
            x=s[price], y=s["overall"], mode="markers+text", name=name,
            text=[short(m) for m in s.index], textposition="top center",
            textfont=dict(family=MONO, size=9, color="#555"),
            marker=dict(size=size, color=colour, line=dict(color=INK, width=1.1)),
            hovertemplate="%{customdata}<br>" + f"price %{{x}}{unit}<br>overall %{{y:.2f}}<extra></extra>",
            customdata=list(s.index)))
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:12px;color:#555'>{subtitle}</span>",
                   font=dict(family=SERIF, size=20, color=INK), x=0.01, xanchor="left"),
        paper_bgcolor=BG, plot_bgcolor=BG, height=560, margin=dict(l=60, r=20, t=90, b=50),
        font=dict(family=MONO, size=11, color=INK), showlegend=False,
        hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="white"))
    fig.update_xaxes(type="log", title=f"blended price ({unit}), log scale",
                     showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    fig.update_yaxes(title="overall index (0-100)", showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    return fig


# ---------- main ----------

def main(profile_path):
    P = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    base = Path(P["data"])
    out = Path(P.get("out") or Path(profile_path).parent)
    out.mkdir(parents=True, exist_ok=True)
    stamp = P.get("stamp", P["slug"].upper())

    frames = {s: load(base, s) for s in P["scoring_sources"]}
    primary = P["scoring_sources"][0]
    names = frames[primary].drop_duplicates("model").set_index("model").key  # model string -> join key

    # join table, printed before any score is computed
    print(f"{'model':<44} " + " ".join(f"{s[:14]:<16}" for s in P['scoring_sources'][1:]) + "join")
    joins = {}
    for m, k in names.items():
        cells, kinds = [], []
        for s in P["scoring_sources"][1:]:
            hit, kind = match(k, set(frames[s].key))
            joins[(m, s)] = hit
            cells.append(f"{(hit or '-')[:14]:<16}")
            kinds.append(kind)
        print(f"{str(m)[:43]:<44} " + " ".join(cells) + ("exact" if set(kinds) == {"exact"} else "/".join(kinds)))

    # wide frame, one column per declared metric
    cols, errs = {}, {}
    for name, spec in P["metrics"].items():
        site = spec["site"]
        val, err = series(frames[site], spec, "model" if site == primary else "key")
        if site != primary:
            err = pd.Series({m: err.get(joins.get((m, site))) for m in names.index}, dtype=float)
            val = pd.Series({m: val.get(joins.get((m, site))) for m in names.index}, dtype=float)
        cols[name] = val
        if not err.dropna().empty:
            errs[name + "_se"] = err
    S = pd.DataFrame({**cols, **errs}).reindex(names.index)

    # candidates: the deepest slice that still has a price and the overall inputs
    ow = P["overall"]
    S["overall"] = sum(S[m] * w for m, w in ow.items())
    S = S.dropna(subset=["overall"])
    if "price" in S:
        S = S[S.price.notna()]
    S = S.sort_values("overall", ascending=False)
    cand = P.get("candidates", {})
    if cand.get("one_variant_per_model", True):
        # Effort variants of one model would otherwise fill the table with the
        # same product four times. Keep the variant that scores best overall.
        S = S[~names.reindex(S.index).duplicated()]
    S = S.head(cand.get("top_n", 14))
    S.index = [short(m) for m in S.index]

    # role indexes
    tabs_ = ["OVERALL"] + [r["slug"].upper() for r in P["roles"]]
    for role in P["roles"]:
        w, tr = role["weights"], role.get("transforms", {})
        parts = []
        for m, wt in w.items():
            v = S[m]
            if tr.get(m) == "inverse_log_minmax":
                v = minmax(v, invert=True, log=True)
            parts.append(v * wt)
        S[role["slug"]] = sum(parts)

    # grouped by source site so the HTML can span a header over each run,
    # then the role columns, then overall
    metric_cols = sorted([m for m in P["metrics"] if S[m].notna().any()],
                         key=lambda m: P["scoring_sources"].index(P["metrics"][m]["site"]))
    role_cols = [r["slug"] for r in P["roles"]] + ["overall"]
    order = metric_cols + role_cols
    columns = [{"name": m, "site": P["metrics"][m]["site"], "unit": P["metrics"][m].get("unit", "")}
               for m in metric_cols] + [{"name": c, "site": "index", "unit": "0-100"} for c in role_cols]
    master = S[order].sort_values("overall", ascending=False).round(2)
    print("\n" + master.to_string())
    head = ["model"] + [c["name"] + (f' ({c["unit"]})' if c["unit"] else "") for c in columns]
    md = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for m, row in master.iterrows():
        md.append(f"| {m} | " + " | ".join("" if pd.isna(v) else f"{v:g}" for v in row) + " |")
    (out / "master-table.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # picks: best and cheap alternative per index
    ca = P.get("cheap_alternative", {"max_points_behind": 5.0, "min_price_ratio": 3.0})
    picks = {}
    for slug in ["overall"] + [r["slug"] for r in P["roles"]]:
        d = S[slug].dropna().sort_values(ascending=False)
        if d.empty:
            picks[slug] = {"best": None, "cheap": None}
            continue
        lead = d.index[0]
        cheap = None
        if "price" in S:
            lp = S.price.get(lead)
            for m in d.index[1:]:
                mp = S.price.get(m)
                if pd.notna(lp) and pd.notna(mp) and mp > 0 and \
                        d[lead] - d[m] <= ca["max_points_behind"] and lp / mp >= ca["min_price_ratio"]:
                    cheap = {"model": m, "score": round(float(d[m]), 2), "price": float(mp),
                             "points_behind": round(float(d[lead] - d[m]), 2),
                             "times_cheaper": round(float(lp / mp), 1)}
                    break
        picks[slug] = {"best": {"model": lead, "score": round(float(d[lead]), 2),
                                "price": None if "price" not in S or pd.isna(S.price.get(lead)) else float(S.price[lead])},
                       "cheap": cheap}
    # one machine-readable artifact: raw benchmark values, the formula behind
    # every role, the resulting scores and the picks. Whoever reads the report
    # can re-derive any number from this file without touching the scrapes.
    def fmt(w, tr):
        return " + ".join(f"{wt:g}*{m}" + (f" [{tr[m]}]" if m in tr else "") for m, wt in w.items())

    def vals(col):
        return {m: None if pd.isna(v) else round(float(v), 4) for m, v in S[col].items()}

    # the models nothing else beats on both price and score, recorded here so
    # the report can name the frontier without anyone working it out by hand.
    pm = P.get("price_metric", "price")
    pareto = S[["overall", pm]].dropna() if pm in S.columns and "overall" in S else pd.DataFrame()
    on = frontier(pareto, "overall", pm) if len(pareto) >= 5 else []

    results = {
        "stack": P["stack"], "data": P["data"], "generated_from": str(profile_path),
        "join": {m: {s: joins.get((m, s)) for s in P["scoring_sources"][1:]} for m in S.index},
        "columns": columns,
        "benchmarks": {name: {"source": f"{sp['site']} / {sp.get('benchmark', '-')} / {sp.get('metric') or sp.get('field')}",
                              "unit": sp.get("unit", ""), "scale": sp.get("scale", 1), "values": vals(name)}
                       for name, sp in P["metrics"].items() if name in S},
        "roles": [{"name": "Overall", "slug": "overall", "formula": fmt(ow, {}),
                   "weights": ow, "scores": vals("overall")}]
                 + [{"name": r["name"], "slug": r["slug"], "formula": fmt(r["weights"], r.get("transforms", {})),
                     "weights": r["weights"], "transforms": r.get("transforms", {}),
                     "scores": vals(r["slug"])} for r in P["roles"]],
        "picks": picks,
        "frontier": [{"model": m, "price": round(float(pareto.loc[m, pm]), 4),
                      "overall": round(float(pareto.loc[m, "overall"]), 2)} for m in on],
    }
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # glance table, ready to paste. The report step copies these cells rather
    # than recomputing them, because a number typed twice is a number that
    # eventually disagrees with itself.
    label = {"overall": "Overall", **{r["slug"]: r["name"] for r in P["roles"]}}
    g = ["| role | best model | cheap alternative |", "|---|---|---|"]
    for slug, p in picks.items():
        best = "no model has every input" if not p["best"] else \
            f'{p["best"]["model"]} ({p["best"]["score"]:g})'
        cheap = "none qualifies" if not p["cheap"] else \
            f'{p["cheap"]["model"]} ({p["cheap"]["score"]:g}, {p["cheap"]["points_behind"]:g} behind, ' \
            f'{p["cheap"]["times_cheaper"]:g}x cheaper)'
        g.append(f"| {label[slug]} | {best} | {cheap} |")
    (out / "glance-table.md").write_text("\n".join(g) + "\n", encoding="utf-8")

    # price against score. The master table carries both columns already; only
    # this view shows which models nothing else beats on both at once, which is
    # the question the whole report exists to answer.
    if on:
        d, unit_p = pareto, P["metrics"][pm].get("unit", "")
        sub = f"{len(d)} models with a price, {len(on)} of them on the frontier"
        fig, ax = figure("Price against the overall index", sub, "PARETO", tabs_, stamp)
        ax.set_xscale("log")
        rest = [m for m in d.index if m not in on]
        ax.scatter(d.loc[rest, pm], d.loc[rest, "overall"], s=70, color="#B8BCC4",
                   edgecolor=INK, linewidth=1.1, zorder=3)
        ax.scatter(d.loc[on, pm], d.loc[on, "overall"], s=130, color=PAL[0],
                   edgecolor=INK, linewidth=1.1, zorder=4)
        ax.step(d.loc[on, pm], d.loc[on, "overall"], where="post", color=PAL[0],
                linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
        for m, r in d.iterrows():
            ax.annotate(short(m), (r[pm], r["overall"]), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=8, color="#555")
        ax.set_xlabel(f"blended price ({unit_p}), log scale")
        ax.set_ylabel("overall index (0-100)")
        ax.grid(True, which="both", axis="x", linestyle=(0, (1, 5)), color="#B5B5B5", linewidth=0.7)
        fig.savefig(out / "00_price_vs_overall.png", dpi=170)
        plt.close(fig)
        plotly_scatter(d, pm, unit_p, on, "Price against the overall index", sub).write_html(
            out / "00_price_vs_overall.html", include_plotlyjs="cdn", full_html=False,
            config={"responsive": True, "displayModeBar": False})
        print("\nfrontier: " + ", ".join(f"{m} ({d.loc[m, pm]:g}{unit_p}, {d.loc[m, 'overall']:.2f})" for m in on))

    # one chart per index
    charts = [("overall", "Overall weighted index", ow, {})] + \
             [(r["slug"], r["name"], r["weights"], r.get("transforms", {})) for r in P["roles"]]
    for n, (slug, title, w, tr) in enumerate(charts, start=1):
        d = S[slug].dropna().sort_values(ascending=False)
        if d.empty:
            print(f"skipped {slug}: no model has every input")
            continue
        sub = " + ".join(f"{wt:.2f} {m}" for m, wt in w.items())
        fig, ax = figure(title, sub, slug.upper(), tabs_, stamp)
        bars(ax, d.index.tolist(), d.tolist())
        ax.set_ylabel(f"{slug} index (0-100)")
        fig.savefig(out / f"{n:02d}_index_{slug}.png", dpi=170)
        plt.close(fig)
        unit = {m: P["metrics"][m].get("unit", "") for m in w}
        hover = [" | ".join(f"{m} {S.loc[i, m]:.1f}{unit[m]}" for m in w) + f"<br><b>{slug} {v:.1f}</b>"
                 for i, v in d.items()]
        plotly_bars(d.index.tolist(), d.tolist(), hover, title, sub, f"{slug} index (0-100)").write_html(
            out / f"{n:02d}_index_{slug}.html", include_plotlyjs="cdn", full_html=False,
            config={"responsive": True, "displayModeBar": False})

    print(f"\nwrote {len(charts)} indexes, master-table.md, glance-table.md and results.json to {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit("usage: make_charts.py reports/<date>-<slug>/profile.json\nrun it through uv so the plotting dependencies come with it:\n  uv run --with matplotlib --with pandas --with plotly python pipeline/make_charts.py <profile>")
    main(sys.argv[1])
