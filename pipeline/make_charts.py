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

from strings import strings

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

# Words a model name loses on its way to a join key. These are one vendor
# generation's effort settings, not identity. They are also ordinary English
# words, so a vendor that puts one inside a real product name gets collapsed
# onto a different model. A profile replaces the list with its own
# `join_strip`, exactly as it replaces `name_strip`.
JOIN_STRIP = ["adaptive reasoning", "default fallback", "max effort", "effort",
              "xhigh", "high", "medium", "low", "max"]
_jstrip = list(JOIN_STRIP)


def key(name, strip=True):
    """Collapse a model string to a join key. Provider prefixes, effort suffixes
    and punctuation differ across sites and carry no identity, so they go.
    Vals writes anthropic/claude-opus-5 where AA writes Claude Opus 5 (max)."""
    s = str(name).rsplit("/", 1)[-1]
    s = re.sub(r"\(.*?\)", " ", s)
    if strip and _jstrip:
        s = re.sub(r"\b(" + "|".join(_jstrip) + r")\b", " ", s, flags=re.I)
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
    # Some sites collapse many boards into one benchmark name and separate them
    # with another column. Without this, "design-arena Elo" means the best of
    # thirty-four boards, text-to-video included.
    for col, want in (spec.get("where") or {}).items():
        if col in d:
            d = d[d[col].astype(str) == str(want)]
    if d.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    col = spec.get("field", "score")
    # A site can publish several configs of one model under one benchmark. All
    # fields have to come off the SAME row, or pass@1, cost, steps and duration
    # end up describing four different runs of the same model. The row is the
    # one that won on the benchmark's headline column, and the collapse is
    # printed, because the honest way to pin a config is a `where` filter.
    pick = spec.get("pick", "score")
    if pick not in d:
        pick = col
    n_rows, n_models = len(d), d[by].nunique() if by in d else d.index.nunique()
    d = d.sort_values(pick, ascending=spec.get("pick_lowest", False)).groupby(by, as_index=True).first()
    if n_rows > n_models:
        print(f"  note: {spec.get('benchmark') or spec.get('metric') or col}: {n_rows} rows over "
              f"{n_models} models. Kept the best row per model by `{pick}`; add a `where` filter "
              "to the metric to pin one config instead.")
    val = pd.to_numeric(d[col], errors="coerce") * spec.get("scale", 1)
    err = pd.to_numeric(d["stderr"], errors="coerce") if spec.get("stderr") and "stderr" in d else pd.Series(dtype=float)
    return val, err


# Substrings a display name loses before it reaches a chart. Vendors word the
# effort setting differently and it eats half the width of the master table
# without adding identity. A profile replaces this with its own `name_strip`,
# because next year's vendors will word it differently again.
# Empty by default. Whatever a vendor pads its display names with is that
# site's wording, so the profile that scores from the site declares it.
NAME_STRIP = []
_strip = [list(x) for x in NAME_STRIP]


def short(m):
    out = str(m)
    for old, new in _strip:
        out = out.replace(old, new)
    return out.strip()


def index_unit(normalize):
    """What an index column's unit really is. Only `candidate_minmax` puts every
    term on the same 0-100 band. Left off, a role carries its metrics' own units
    and can span several hundred, so printing `0-100` on the axis is a lie."""
    return "0-100" if normalize == "candidate_minmax" else ""


def terms(S, weights, transforms, normalize):
    """One weighted part per metric, so every index is built the same way.

    `normalize` decides what a weight means. Without it a weight is a share of
    the metric's raw scale, and a metric spanning 48 points outvotes one
    spanning 10 whatever the profile declared. With it, every term is stretched
    to the same 0-100 band across the candidate set first, and a weight is a
    share of influence.
    """
    parts = []
    for m, wt in weights.items():
        v = S[m]
        t = transforms.get(m)
        if t and t not in ("inverse_log_minmax", "log_minmax", "minmax"):
            sys.exit(f"unknown transform {t!r} on metric {m!r}. Known transforms are "
                     "minmax, log_minmax and inverse_log_minmax. Left unrecognised it "
                     "would be ignored and the raw value added at full magnitude.")
        if t == "inverse_log_minmax":
            v = minmax(v, invert=True, log=True)
        elif t == "log_minmax":
            v = minmax(v, log=True)
        elif t == "minmax" or normalize == "candidate_minmax":
            v = minmax(v)
        parts.append(v * wt)
    return parts


def influence(S, weights, transforms, normalize):
    """What share of the spread each term actually drives. A profile declaring
    0.40 on a term that drives 17% is not lying, it is unaware."""
    out = {}
    for m, wt in weights.items():
        v = S[m].dropna()
        if v.empty:
            out[m] = 0.0
            continue
        wide = m in transforms or normalize == "candidate_minmax"
        out[m] = wt * (100.0 if wide else float(v.max() - v.min()))
    tot = sum(out.values()) or 1.0
    return {m: 100 * v / tot for m, v in out.items()}


def minmax(s, invert=False, log=False):
    if log:
        bad = s <= 0
        if bad.any():
            print(f"  note: {int(bad.sum())} candidate(s) carry a value of 0 or less on a "
                  "log scaled term. log10 of those is undefined, so they are left out of "
                  "that term rather than dragging the whole column to NaN.")
        s = s.where(s > 0)
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


def plotly_bars(labels, values, hover, ytitle):
    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=[PAL[k % len(PAL)] for k in range(len(values))], line=dict(color=INK, width=1.1)),
        text=[f"{v:.1f}" for v in values], textposition="inside", insidetextanchor="end",
        textfont=dict(family=MONO, size=11), customdata=hover,
        hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG, height=460, margin=dict(l=50, r=20, t=20, b=10),
        font=dict(family=MONO, size=11, color=INK),
        hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="white"))
    # rotated model names need room, and plotly measures them better than a
    # guessed bottom margin does
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=10), automargin=True,
                     showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    fig.update_yaxes(title=ytitle, showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    return fig


def human(v, unit):
    """One value, formatted for a person. Seconds become h/m/s, because nobody
    reads 3972.86 s as "just over an hour"."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    u = unit.strip()
    if u == "s":
        t = int(round(float(v)))
        h, r = divmod(t, 3600)
        m, sec = divmod(r, 60)
        if h:
            return f"{h}h {m}m {sec}s"
        return f"{m}m {sec}s" if m else f"{sec}s"
    return f"{v:.2f}" + (f" {u}" if u else "")


def label_spots(xs, ys, labels, log_x):
    if len(xs) == 0:
        return []
    """One text position per point, chosen so labels do not land on each other.

    Plotly has no collision handling for scatter text, so this does the two
    things a person would do by hand: lean a label inward at the edge of the
    plot, and drop it under the marker when the label above is already taken.
    """
    x = np.asarray(xs, float)
    # A free model prices at 0 and log10 of that is -inf, which would drag every
    # other label's position to NaN. It is off the log axis anyway, so it keeps
    # the default placement rather than poisoning the rest.
    v = np.log10(np.where(x > 0, x, np.nan)) if log_x else x
    y = np.asarray(ys, float)
    sx = np.nan_to_num((v - np.nanmin(v)) / ((np.nanmax(v) - np.nanmin(v)) or 1), nan=0.5)
    sy = np.nan_to_num((y - np.nanmin(y)) / ((np.nanmax(y) - np.nanmin(y)) or 1), nan=0.5)
    out, taken = [], []
    for i, text in enumerate(labels):
        if not text:
            out.append("top center")
            continue
        side = "right" if sx[i] < .12 else "left" if sx[i] > .88 else "center"
        # the width of a label is roughly its length, and a label is only a
        # problem when the other one sits at the same height
        near = [t for t in taken
                if abs(sx[i] - t[0]) < .015 * max(len(text), 8) and abs(sy[i] - t[1]) < .06]
        vert = "bottom" if any(t[2] == "top" for t in near) else "top"
        taken.append((sx[i], sy[i], vert))
        out.append(f"{vert} {side}")
    return out


def bubbles(v, lo=10, hi=26):
    """Marker areas scaled between two readable diameters. A raw metric mapped
    straight onto radius makes a 3x difference look like 9x."""
    a, b = float(np.nanmin(v)), float(np.nanmax(v))
    if not np.isfinite(a) or b == a:
        return np.full(len(v), (lo + hi) / 2)
    return lo + (np.asarray(v, dtype=float) - a) / (b - a) * (hi - lo)


def plotly_xy(d, x, y, ux, uy, log_x, size=None, us="", note="", names=None, log_label="log scale"):
    """One scatter, three readings: the axes, the bubble size, and the line
    through the models nothing beats on both axes at once."""
    import plotly.graph_objects as go
    front = frontier(d, y, x)
    f = d.loc[front].sort_values(x)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=f[x], y=f[y], mode="lines", line=dict(color=PAL[0], width=1.4, dash="dot"),
        hoverinfo="skip"))
    nx_, ny_ = (names or {}).get(x, x), (names or {}).get(y, y)
    zname = (names or {}).get(size, size) if size else ""
    rows = list(zip(d.index,
                    [human(v, ux) for v in d[x]],
                    [human(v, uy) for v in d[y]],
                    [human(v, us) for v in (d[size] if size else d[x])]))
    marks = bubbles(d[size]) if size else np.full(len(d), 15.0)
    tags = [short(m) if m in front else "" for m in d.index]
    where = label_spots(d[x], d[y], tags, log_x)
    on = [m in front for m in d.index]
    extra = f"<br>{zname} %{{customdata[3]}}" if size else ""
    fig.add_trace(go.Scatter(
        x=d[x], y=d[y], mode="markers+text",
        text=tags,
        textposition=where, textfont=dict(family=MONO, size=9, color="#555"),
        cliponaxis=False,
        marker=dict(size=marks, sizemode="diameter",
                    color=[PAL[0] if o else "#B8BCC4" for o in on],
                    line=dict(color=INK, width=1.1)),
        customdata=rows,
        hovertemplate=f"%{{customdata[0]}}<br>{nx_} %{{customdata[1]}}"
                      f"<br>{ny_} %{{customdata[2]}}{extra}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG, height=460, margin=dict(l=64, r=64, t=26, b=50),
        font=dict(family=MONO, size=11, color=INK), showlegend=False,
        hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="white"))
    if note:
        fig.add_annotation(text=note, xref="paper", yref="paper", x=0, y=1.02,
                           showarrow=False, xanchor="left", yanchor="bottom",
                           font=dict(family=MONO, size=10, color="#6a6a6a"))
    nx, ny = nx_, ny_
    ux, uy = ux.strip(), uy.strip()
    fig.update_xaxes(type="log" if log_x else "linear",
                     title=f"{nx} ({ux}), {log_label}" if log_x and ux else (f"{nx} ({ux})" if ux else nx),
                     showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    if log_x:
        # A log axis labels its minor ticks with the mantissa alone, so 0.2 and 2
        # both read "2". Spell the values out instead.
        lo, hi = float(d[x].min()), float(d[x].max())
        t = [v * 10 ** k for k in range(-4, 5) for v in (1, 2, 5) if lo * 0.9 <= v * 10 ** k <= hi * 1.1]
        fig.update_xaxes(tickmode="array", tickvals=t, ticktext=[f"{v:g}" for v in t])
    fig.update_yaxes(title=f"{ny} ({uy})" if uy else ny, showgrid=True,
                     gridcolor="#c8c8c8", griddash="dot")
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


def plotly_price_tabs(S, price, unit, indexes, log_label="log scale", note_of=None,
                      breakdown=None, price_label="price", iunit=""):
    """Price against a chosen index, one tab per index.

    Each tab is two traces, the frontier line and the markers, so switching a
    tab is a visibility flip rather than a redraw. The frontier is recomputed
    per index: the models nothing beats on both price and that index.
    """
    import plotly.graph_objects as go
    fig = go.Figure()
    spans, notes = [], []
    for slug, name in list(indexes):
        d = S[[price, slug]].dropna()
        if d.empty:
            indexes = [i for i in indexes if i[0] != slug]
            print(f"  skipped tab {slug}: no model has both a price and a score")
            continue
        front = frontier(d, slug, price)
        f = d.loc[front].sort_values(price)
        tags = [short(m) if m in front else "" for m in d.index]
        fig.add_trace(go.Scatter(x=f[price], y=f[slug], mode="lines", hoverinfo="skip",
                                 line=dict(color=PAL[0], width=1.4, dash="dot")))
        fig.add_trace(go.Scatter(
            x=d[price], y=d[slug], mode="markers+text",
            text=tags,
            textposition=label_spots(d[price], d[slug], tags, True),
            textfont=dict(family=MONO, size=9, color="#555"),
            cliponaxis=False,
            marker=dict(size=15, color=[PAL[0] if m in front else "#B8BCC4" for m in d.index],
                        line=dict(color=INK, width=1.1)),
            customdata=list(zip(d.index, [human(v, unit) for v in d[price]],
                               [(breakdown or {}).get(slug, {}).get(m, "") for m in d.index])),
            hovertemplate=f"%{{customdata[0]}}<br>{price_label} %{{customdata[1]}}"
                          f"<br><b>{name} %{{y:.2f}}</b>"
                          f"<br>%{{customdata[2]}}<extra></extra>"))
        spans.append((len(d), len(front)))
        notes.append(note_of(len(d), len(front)) if note_of else "")

    n = len(indexes)
    buttons = []
    for k, (slug, name) in enumerate(indexes):
        vis = [False] * (2 * n)
        vis[2 * k] = vis[2 * k + 1] = True
        buttons.append(dict(label=name, method="update",
                            args=[{"visible": vis},
                                  {"yaxis.title.text": name + (f" ({iunit})" if iunit else ""),
                                   "annotations": [dict(text=notes[k], xref="paper", yref="paper",
                                                        x=0, y=1.02, showarrow=False,
                                                        xanchor="left", yanchor="bottom",
                                                        font=dict(family=MONO, size=10, color="#6a6a6a"))]}]))
    for k in range(2, 2 * n):
        fig.data[k].visible = False

    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG, height=520,
        margin=dict(l=64, r=64, t=74, b=50),
        font=dict(family=MONO, size=11, color=INK), showlegend=False,
        hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="white"),
        annotations=[dict(text=notes[0], xref="paper", yref="paper", x=0, y=1.02,
                          showarrow=False, xanchor="left", yanchor="bottom",
                          font=dict(family=MONO, size=10, color="#6a6a6a"))],
        updatemenus=[dict(type="buttons", direction="right", showactive=True,
                          x=0, xanchor="left", y=1.20, yanchor="top",
                          pad=dict(l=0, t=0), bgcolor=BG, bordercolor="#d3cfc0",
                          font=dict(family=MONO, size=11, color=INK), buttons=buttons)])
    lo, hi = float(S[price].min()), float(S[price].max())
    t = [v * 10 ** k for k in range(-4, 5) for v in (1, 2, 5) if lo * 0.9 <= v * 10 ** k <= hi * 1.1]
    fig.update_xaxes(type="log", title=f"{price_label} ({unit}), {log_label}",
                     tickmode="array", tickvals=t, ticktext=[f"{v:g}" for v in t],
                     showgrid=True, gridcolor="#c8c8c8", griddash="dot")
    fig.update_yaxes(title=indexes[0][1] + (f" ({iunit})" if iunit else ""), showgrid=True,
                     gridcolor="#c8c8c8", griddash="dot")
    return fig


# ---------- main ----------

def main(profile_path):
    P = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    base = Path(P["data"])
    out = Path(P.get("out") or Path(profile_path).parent)
    out.mkdir(parents=True, exist_ok=True)
    stamp = P.get("stamp", P["slug"].upper())
    T = strings(P)
    _strip[:] = [list(x) for x in P.get("name_strip", NAME_STRIP)]
    _jstrip[:] = list(P.get("join_strip", JOIN_STRIP))

    frames = {s: load(base, s) for s in P["scoring_sources"]}
    # A strip that leaves no version digit behind usually ate part of the
    # product name rather than an effort setting. "Qwen Max" becoming "qwen"
    # then joins onto plain Qwen and looks exactly like data.
    for s_, f_ in frames.items():
        for m_ in f_["model"].drop_duplicates():
            k_ = key(m_)
            if k_ != key(m_, strip=False) and not any(c.isdigit() for c in k_):
                print(f"  warning: {s_} '{m_}' collapses to join key '{k_}' with no version "
                      "left. Set `join_strip` in the profile if that word is part of the name.")
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
    pmetric = P.get("price_metric", "price")
    norm = P.get("normalize")
    ow = P.get("overall") or {}
    if not ow:
        sys.exit("profile has no `overall` block. It is a weights dict like the roles, "
                 "for example {\"coding\": 0.30, \"agentic\": 0.25, \"lcr\": 0.15, "
                 "\"nh\": 0.15, \"acc\": 0.15}. Nothing adds it for you.")
    absent = [m for m in ow if m not in S]
    if absent:
        sys.exit(f"`overall` names metrics the profile does not declare: {absent}")
    oparts = terms(S, ow, {}, norm)
    S["overall"] = sum(oparts)
    S["overall_zero"] = sum(p_.fillna(0) for p_ in oparts)
    # Which models are candidates at all. Gating on `overall` lets the overall
    # inputs decide the population of every report, so a profile scoring from a
    # site that publishes none of them has to name its own gate.
    gate = P.get("gate", "overall")
    if gate:
        S = S.dropna(subset=[gate])
    if pmetric in S:
        S = S[S[pmetric].notna()]
    S = S.sort_values("overall", ascending=False)
    cand = P.get("candidates", {})
    if cand.get("one_variant_per_model", True):
        # Effort variants of one model would otherwise fill the table with the
        # same product four times. Keep the variant that scores best overall.
        S = S[~names.reindex(S.index).duplicated()]
    if cand.get("top_n"):
        S = S.head(cand["top_n"])
    S.index = [short(m) for m in S.index]

    # Coverage over the candidate set, which is the only coverage deciding
    # whether a column prints. A benchmark can cover 450 models on its own site
    # and two of the fourteen here.
    print("\ncoverage over the candidates")
    thin = []
    for m_ in P["metrics"]:
        if m_ not in S:
            continue
        n_ = int(S[m_].notna().sum())
        flag = "  THIN" if n_ < 0.7 * len(S) else ""
        print(f"  {m_:<12} {n_:>3}/{len(S)}{flag}")
        if flag:
            thin.append(m_)
    weighted = {m_ for r_ in P["roles"] for m_ in r_["weights"]} | set(ow)
    for m_ in sorted(set(thin) & weighted):
        print(f"  warning: {m_} is weighted in an index and covers "
              f"{int(S[m_].notna().sum())} of {len(S)} candidates")

    # The other reading of an empty cell: not "this model would have scored
    # nothing" but "this model would have been ordinary". Published scores use
    # neither.
    metric_names = [m for m in P["metrics"] if m in S]
    med = S[metric_names].median()
    M = S.copy()
    M[metric_names] = S[metric_names].fillna(med)
    S["overall_median"] = sum(terms(M, ow, {}, norm))

    # role indexes
    tabs_ = ["OVERALL"] + [r["slug"].upper() for r in P["roles"]]
    print("\nwhat each weight actually drives"
          + ("" if norm else "   (no `normalize` set: a weight is a share of raw scale)"))
    for slug_, w_, tr_ in [("overall", ow, {})] + \
            [(r_["slug"], r_["weights"], r_.get("transforms", {})) for r_ in P["roles"]]:
        sh = influence(S, w_, tr_, norm)
        print(f"  {slug_:<12} " + "  ".join(
            f"{m_} {w_[m_]:g}->{sh[m_]:.0f}%" for m_ in sorted(w_, key=lambda x: -sh[x])))

    for role in P["roles"]:
        w, tr = role["weights"], role.get("transforms", {})
        parts = terms(S, w, tr, norm)
        S[role["slug"]] = sum(parts)
        # The same index with a missing term contributing nothing. It is not the
        # published score: a model is excluded from a role it lacks an input for.
        # It exists so the report can show what the ranking would look like if
        # absence were read as zero, which is the question a reader asks the
        # moment they see an empty cell.
        S[role["slug"] + "_zero"] = sum(p.fillna(0) for p in parts)
        S[role["slug"] + "_median"] = sum(terms(M, w, tr, norm))

    # grouped by source site so the HTML can span a header over each run,
    # then the role columns, then overall
    metric_cols = sorted([m for m in P["metrics"]
                          if S[m].notna().any() and P["metrics"][m].get("in_table", True)],
                         key=lambda m: P["scoring_sources"].index(P["metrics"][m]["site"]))
    role_cols = [r["slug"] for r in P["roles"]] + ["overall"]
    order = metric_cols + role_cols
    role_label = {r["slug"]: r["name"] for r in P["roles"]} | {"overall": T["Overall weighted index"]}
    iu = index_unit(norm)

    def direction(m):
        """An explicit `better` in the profile wins outright. Otherwise a price
        is lower-is-better whether or not a role happens to transform it, and a
        transform is the last hint left."""
        d = P["metrics"][m].get("better")
        if d:
            return d
        if m == pmetric or any(r.get("transforms", {}).get(m) == "inverse_log_minmax"
                               for r in P["roles"]):
            return "low"
        return "high"

    low = {m for m in metric_cols if direction(m) == "low"}
    def calc(w, tr):
        return " + ".join(f"{wt:g}*{m}" + (f" [{tr[m]}]" if m in tr else "")
                          for m, wt in w.items())

    sums = {"overall": calc(ow, {}),
            **{r["slug"]: calc(r["weights"], r.get("transforms", {})) for r in P["roles"]}}

    columns = [{"name": m, "site": P["metrics"][m]["site"], "unit": P["metrics"][m].get("unit", ""),
                "better": "low" if m in low else "high",
                "plain": P["metrics"][m].get("plain", ""),
                "label": P["metrics"][m].get("label") or P["metrics"][m].get("benchmark") or P["metrics"][m].get("metric")
                         or P["metrics"][m].get("field", m)}
               for m in metric_cols] + \
              [{"name": c, "site": "index", "unit": iu, "better": "high",
                "plain": f'{T["weighted score" if iu else "weighted score raw"]}: {sums[c]}',
                "label": role_label[c]} for c in role_cols]
    master = S[order].sort_values("overall", ascending=False).round(2)
    print("\n" + master.to_string())
    head = [T["model"]] + [c["name"] + (f' ({c["unit"]})' if c["unit"] else "") for c in columns]
    md = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for m, row in master.iterrows():
        md.append(f"| {m} | " + " | ".join("" if pd.isna(v) else f"{v:g}" for v in row) + " |")
    (out / "master-table.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # picks: best and cheap alternative per index
    ca = P.get("cheap_alternative", {"max_points_behind": 5.0, "min_price_ratio": 3.0})
    # Those points are in each index's own units. Without `candidate_minmax` an
    # index is not on a 0-100 band, so the same constant is a wide tolerance in
    # one profile and inside rounding error in the next. Print both.
    spans = [(s_, float(S[s_].max() - S[s_].min())) for s_ in ["overall"] + [r["slug"] for r in P["roles"]]
             if S[s_].notna().any()]
    print(f'\ncheap alternative: within {ca["max_points_behind"]:g} points of the leader and '
          f'{ca["min_price_ratio"]:g}x cheaper. Index spans across the candidates: '
          + ", ".join(f"{s_} {v:.1f}" for s_, v in spans))
    picks = {}
    for slug in ["overall"] + [r["slug"] for r in P["roles"]]:
        d = S[slug].dropna().sort_values(ascending=False)
        if d.empty:
            picks[slug] = {"best": None, "cheap": None}
            continue
        lead = d.index[0]
        cheap = None
        if pmetric in S:
            lp = S[pmetric].get(lead)
            for m in d.index[1:]:
                mp = S[pmetric].get(m)
                if pd.notna(lp) and pd.notna(mp) and mp > 0 and \
                        d[lead] - d[m] <= ca["max_points_behind"] and lp / mp >= ca["min_price_ratio"]:
                    cheap = {"model": m, "score": round(float(d[m]), 2), "price": float(mp),
                             "points_behind": round(float(d[lead] - d[m]), 2),
                             "times_cheaper": round(float(lp / mp), 1)}
                    break
        picks[slug] = {"best": {"model": lead, "score": round(float(d[lead]), 2),
                                "price": None if pmetric not in S or pd.isna(S[pmetric].get(lead))
                                else float(S[pmetric][lead])},
                       "cheap": cheap}
    # one machine-readable artifact: raw benchmark values, the formula behind
    # every role, the resulting scores and the picks. Whoever reads the report
    # can re-derive any number from this file without touching the scrapes.
    def fmt(w, tr):
        return "`" + " + ".join(f"{wt:g}*{m}" + (f" [{tr[m]}]" if m in tr else "") for m, wt in w.items()) + "`"

    def origin(site):
        d = frames.get(site)
        u = d.source_url.dropna() if d is not None and "source_url" in d else pd.Series(dtype=str)
        m = re.match(r"(https?://[^/]+)", str(u.iloc[0])) if not u.empty else None
        return m.group(1) if m else None

    def vals(col):
        return {m: None if pd.isna(v) else round(float(v), 4) for m, v in S[col].items()}

    # the models nothing else beats on both price and score, recorded here so
    # the report can name the frontier without anyone working it out by hand.
    pm = P.get("price_metric", "price")
    pareto = S[["overall", pm]].dropna() if pm in S.columns and "overall" in S else pd.DataFrame()
    on = frontier(pareto, "overall", pm) if len(pareto) >= 5 else []

    def missing(slug, weights):
        """Candidates the role could not score, and the input each one lacked.
        A reader seeing an empty cell should not have to work out which of five
        weighted terms was the one that went absent."""
        return [{"model": m, "missing": [w for w in weights if pd.isna(S.loc[m, w])]}
                for m in S.index[S[slug].isna()]]

    results = {
        "stack": P["stack"], "data": P["data"], "generated_from": str(profile_path),
        "join": {m: {s: joins.get((m, s)) for s in P["scoring_sources"][1:]} for m in S.index},
        "columns": columns,
        "benchmarks": {name: {"source": f"{sp['site']} / {sp.get('benchmark', '-')} / {sp.get('metric') or sp.get('field')}",
                              "unit": sp.get("unit", ""), "scale": sp.get("scale", 1), "values": vals(name)}
                       for name, sp in P["metrics"].items() if name in S},
        "roles": [{"name": "Overall", "slug": "overall", "formula": fmt(ow, {}),
                   "weights": ow, "scores": vals("overall"), "not_scored": missing("overall", ow),
                   "scores_zero": vals("overall_zero"), "scores_median": vals("overall_median")}]
                 + [{"name": r["name"], "slug": r["slug"], "formula": fmt(r["weights"], r.get("transforms", {})),
                     "weights": r["weights"], "transforms": r.get("transforms", {}),
                     "scores": vals(r["slug"]), "not_scored": missing(r["slug"], r["weights"]),
                     "scores_zero": vals(r["slug"] + "_zero"),
                     "scores_median": vals(r["slug"] + "_median")}
                    for r in P["roles"]],
        "picks": picks,
        "sites": {s_: u for s_ in P["scoring_sources"] for u in [origin(s_)] if u},
        "medians": {m: round(float(v), 4) for m, v in med.items() if pd.notna(v)},
        "frontier": [{"model": m, "price": round(float(pareto.loc[m, pm]), 4),
                      "overall": round(float(pareto.loc[m, "overall"]), 2)} for m in on],
    }
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # glance table, ready to paste. The report step copies these cells rather
    # than recomputing them, because a number typed twice is a number that
    # eventually disagrees with itself.
    label = {"overall": "Overall", **{r["slug"]: r["name"] for r in P["roles"]}}
    formula = {"overall": fmt(ow, {}),
               **{r["slug"]: fmt(r["weights"], r.get("transforms", {})) for r in P["roles"]}}
    g = [f'| {T["index"]} | {T["weights"]} | {T["best model"]} | {T["cheap alternative"]} |',
         "|---|---|---|---|"]
    for slug, p in picks.items():
        best = T["no model has every input"] if not p["best"] else \
            f'{p["best"]["model"]} ({p["best"]["score"]:g})'
        cheap = T["none qualifies"] if not p["cheap"] else \
            f'{p["cheap"]["model"]} ({p["cheap"]["score"]:g}, ' \
            f'{p["cheap"]["points_behind"]:g} {T["behind"]}, ' \
            f'{p["cheap"]["times_cheaper"]:g}x {T["cheaper"]})'
        g.append(f"| {label[slug]} | {formula[slug]} | {best} | {cheap} |")
    (out / "glance-table.md").write_text("\n".join(g) + "\n", encoding="utf-8")

    # the same breakdown the bar charts show, so a reader can check an index
    # value against its terms wherever they meet it
    unit_of = {m: P["metrics"][m].get("unit", "") for m in P["metrics"]}
    breakdown = {}
    for slug_, w_, tr_ in [("overall", ow, {})] + \
            [(r["slug"], r["weights"], r.get("transforms", {})) for r in P["roles"]]:
        breakdown[slug_] = {
            m_: " &middot; ".join(
                f"{wt_:g}&times;{k_} {human(S.loc[m_, k_], unit_of.get(k_, ''))}"
                + (" [rel]" if k_ in tr_ else "")
                for k_, wt_ in w_.items())
            for m_ in S.index}

    # price against score. The master table carries both columns already; only
    # this view shows which models nothing else beats on both at once, which is
    # the question the whole report exists to answer.
    if on:
        d, unit_p = pareto, P["metrics"][pm].get("unit", "")
        sub = f'{len(d)} {T["models with a price"]}, {len(on)} {T["on the frontier"]}'
        plabel = P["metrics"][pm].get("label") or pm
        fig, ax = figure(f'{plabel} {T["against the overall index"]}', sub, "PARETO", tabs_, stamp)
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
        ax.set_xlabel(f"{P['metrics'][pm].get('label') or pm} ({unit_p}), log scale")
        ax.set_ylabel(f'{T["Overall"]} {T["index scale"]}' + (f" ({iu})" if iu else ""))
        ax.grid(True, which="both", axis="x", linestyle=(0, (1, 5)), color="#B5B5B5", linewidth=0.7)
        fig.savefig(out / f"00_{pm}_vs_overall.png", dpi=170)
        plt.close(fig)
        plotly_price_tabs(
            S[[pm] + ["overall"] + [r["slug"] for r in P["roles"]]].dropna(subset=[pm]),
            pm, unit_p,
            [("overall", T["Overall"])] + [(r["slug"], r["name"]) for r in P["roles"]],
            T["log scale"],
            lambda a, b: f'{a} {T["models with a price"]}  ·  {b} {T["on the frontier"]}',
            breakdown,
            plabel, iu,
        ).write_html(
            out / f"00_{pm}_vs_overall.html", include_plotlyjs="cdn", full_html=False,
            config={"responsive": True, "displayModeBar": False})
        print("\nfrontier: " + ", ".join(f"{m} ({d.loc[m, pm]:g}{unit_p}, {d.loc[m, 'overall']:.2f})" for m in on))

    # one chart per index
    charts = [("overall", T["Overall weighted index"], ow, {})] + \
             [(r["slug"], r["name"], r["weights"], r.get("transforms", {})) for r in P["roles"]]
    for n, (slug, title, w, tr) in enumerate(charts, start=1):
        d = S[slug].dropna().sort_values(ascending=False)
        if d.empty:
            print(f"skipped {slug}: no model has every input")
            continue
        sub = " + ".join(f"{wt:.2f} {m}" for m, wt in w.items())
        fig, ax = figure(title, sub, slug.upper(), tabs_, stamp)
        bars(ax, d.index.tolist(), d.tolist())
        ax.set_ylabel(f'{slug} {T["index scale"]}' + (f" ({iu})" if iu else ""))
        fig.savefig(out / f"{n:02d}_index_{slug}.png", dpi=170)
        plt.close(fig)
        unit = {m: P["metrics"][m].get("unit", "") for m in w}
        hover = [" | ".join(f"{m} {human(S.loc[i, m], unit[m])}" for m in w)
                 + f"<br><b>{slug} {v:.2f}</b>" for i, v in d.items()]
        plotly_bars(d.index.tolist(), d.tolist(), hover,
                    f'{slug} {T["index scale"]}' + (f" ({iu})" if iu else "")).write_html(
            out / f"{n:02d}_index_{slug}.html", include_plotlyjs="cdn", full_html=False,
            config={"responsive": True, "displayModeBar": False})

    for n, sc in enumerate(P.get("scatters", []), start=len(charts) + 1):
        x, y, z = sc["x"], sc["y"], sc.get("size")
        cols = [c for c in (x, y, z) if c]
        d = S[cols].dropna()
        if len(d) < 4:
            print(f"skipped scatter {x} vs {y}: {len(d)} models have all of {cols}")
            continue
        ux = P["metrics"][x].get("unit", "")
        uy = P["metrics"][y].get("unit", "")
        uz = P["metrics"][z].get("unit", "") if z else ""
        names = {k: sc.get(k + "_label", k) for k in (x, y, z) if k}
        zname = names.get(z, z) if z else ""
        note = f'{len(d)} {T["models"]}  ·  {P["metrics"][x]["site"]}'
        if z:
            note += f'  ·  {T["bubble size"]}: {zname}' + (f" ({uz.strip()})" if uz else "")
        fig, ax = figure(sc["title"], note, "CROSS", tabs_, stamp)
        if sc.get("log_x"):
            ax.set_xscale("log")
        front = frontier(d, y, x)
        f = d.loc[front].sort_values(x)
        ax.plot(f[x], f[y], color=PAL[0], linewidth=1.2, linestyle=(0, (2, 3)), zorder=2)
        area = (bubbles(d[z]) if z else np.full(len(d), 15.0)) ** 2
        ax.scatter(d[x], d[y], s=area, zorder=3, linewidth=1.1, edgecolor=INK,
                   color=[PAL[0] if m in front else "#B8BCC4" for m in d.index])
        for m, r in d.iterrows():
            ax.annotate(short(m), (r[x], r[y]), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=8, color="#555")
        ax.set_xlabel(f"{names[x]} ({ux.strip()})" if ux.strip() else names[x])
        ax.set_ylabel(f"{names[y]} ({uy.strip()})" if uy.strip() else names[y])
        ax.grid(True, which="both", axis="x", linestyle=(0, (1, 5)), color="#B5B5B5", linewidth=0.7)
        fig.savefig(out / f"{n:02d}_{x}_vs_{y}.png", dpi=170)
        plt.close(fig)
        plotly_xy(d, x, y, ux, uy, bool(sc.get("log_x")), z, uz, note, names,
                  T["log scale"]).write_html(
            out / f"{n:02d}_{x}_vs_{y}.html", include_plotlyjs="cdn", full_html=False,
            config={"responsive": True, "displayModeBar": False})

    print(f"\nwrote {len(charts)} indexes, master-table.md, glance-table.md and results.json to {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit("usage: make_charts.py reports/<date>-<slug>/profile.json\nrun it through uv so the plotting dependencies come with it:\n  uv run --with matplotlib --with pandas --with plotly python pipeline/make_charts.py <profile>")
    main(sys.argv[1])
