"""Vals-AI / DeepSWE styled charts for the ERP-APEX shortlist.
Run: uv run --with matplotlib --with pandas python reports/20260902/make_charts.py
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

B = Path("benchmark-data/20260904")
OUT = Path("reports/20260902")
BG = "#FBFAF6"
INK = "#1A1A1A"
PAL = ["#E8927C", "#3D3D3D", "#5BB381", "#B8BCC4", "#C084E8", "#5B9BF0", "#5A6B8C",
       "#7B8CF0", "#F0923B", "#F0C75B", "#E8DCC8", "#8FD3C7", "#D98CB3", "#9BB0D8"]
TABS = ("INTELLIGENCE", "COST", "TIME", "TURNS")
STAMP = "ERP / APEX INDEX  •  SEP 04, 2026"

mpl.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
                     "font.family": "DejaVu Sans", "axes.edgecolor": INK})


def load(name):
    return pd.DataFrame(json.load(open(B / name / "normalized.json", encoding="utf-8")))


def short(m):
    return (m.replace("(Adaptive Reasoning, ", "(").replace(", Default Fallback", "")
             .replace(" Effort", "").replace("Artificial Analysis ", ""))


def luminance(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def dotgrid(ax):
    ax.set_axisbelow(True)
    ax.yaxis.set_minor_locator(mpl.ticker.AutoMinorLocator(4))
    ax.grid(True, which="both", axis="y", linestyle=(0, (1, 5)), color="#B5B5B5", linewidth=0.7)
    ax.grid(True, which="major", axis="x", linestyle=(0, (1, 5)), color="#B5B5B5", linewidth=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(which="minor", length=0)


def tabs(fig, active, right=STAMP, items=TABS):
    x = 0.04
    for it in items:
        on = it == active
        fig.text(x, 0.905, ("▮ " if on else "↔ ") + it, fontsize=9, family="monospace",
                 color=INK if on else "#8A8A8A", fontweight="bold" if on else "normal",
                 bbox=dict(boxstyle="square,pad=0.45", fc="#E9EEE7" if on else BG, ec="none"))
        x += 0.045 + 0.0118 * len(it)
    fig.text(0.96, 0.905, right, fontsize=8.5, family="monospace", ha="right", color=INK, fontweight="bold")


def vals_bars(ax, labels, values, fmt, err=None, colors=None):
    x = np.arange(len(values))
    cols = colors or [PAL[i % len(PAL)] for i in x]
    ax.bar(x, values, width=0.92, color=cols, edgecolor=INK, linewidth=1.1,
           yerr=err, ecolor=INK, capsize=3)
    top = max(values)
    for i, v in enumerate(values):
        ax.text(i, v - top * 0.025, fmt(v), ha="center", va="top", fontsize=8.5, family="monospace",
                fontweight="bold", color="white" if luminance(cols[i]) < 0.5 else INK)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8, family="monospace")
    ax.set_xlim(-0.5, len(values) - 0.5)
    dotgrid(ax)


def figure(title, subtitle, active, items=TABS):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.subplots_adjust(top=0.82, bottom=0.22, left=0.06, right=0.98)
    fig.text(0.04, 0.965, title, fontsize=18, family="serif", color=INK)
    fig.text(0.04, 0.935, subtitle, fontsize=9.5, color="#555555")
    tabs(fig, active, items=items)
    return fig, ax


# ---------- data ----------
aa = load("artificial-analysis")
aa = aa[aa["is_estimated"] != True]  # noqa: E712  (NaN counts as measured)


def aa_col(bench=None, metric=None):
    d = aa[aa.benchmark == bench] if bench else aa[aa.metric == metric]
    return d.groupby("model").score.first()


P = pd.DataFrame({
    "coding": aa_col("Artificial Analysis Coding Index"),
    "agentic": aa_col("Artificial Analysis Agentic Index"),
    "lcr": aa_col("AA-LCR"),
    "nh": aa_col("AA-Omniscience Non-Hallucination Rate"),
    "acc": aa_col("AA-Omniscience Accuracy"),
    "tb": aa_col("Terminal-Bench 2.1"),
    "ifb": aa_col("IFBench"),
    "price": aa_col(metric="blended_price_per_1m_usd_3to1"),
    "e2e": aa_col(metric="end_to_end_response_time_median_seconds"),
    "ttft": aa_col(metric="time_to_first_token_median_seconds"),
})
W = {"coding": 0.30, "agentic": 0.25, "lcr": 0.15, "nh": 0.15, "acc": 0.15}
idx = P.dropna(subset=list(W)).copy()
idx["index"] = (idx.coding * W["coding"] + idx.agentic * W["agentic"]
                + idx.lcr * 100 * W["lcr"] + idx.nh * 100 * W["nh"] + idx.acc * 100 * W["acc"])
top = idx.sort_values("index", ascending=False).head(14)

ds = load("deepswe")
ds = ds[ds.metric == "pass@1"]
best = ds.sort_values("score").groupby("model").tail(1)  # best config per model
va = load("vals-ai")

# ---------- 1. intelligence ----------
fig, ax = figure("ERP / APEX weighted intelligence index",
                 "0.30 Coding + 0.25 Agentic + 0.15 long-context + 0.15 non-hallucination + 0.15 accuracy "
                 "(Artificial Analysis, measured only, max-effort configs)", "INTELLIGENCE")
vals_bars(ax, [short(m) for m in top.index], top["index"].tolist(), lambda v: f"{v:.1f}")
ax.set_ylabel("weighted index (0-100)")
fig.savefig(OUT / "01_intelligence_weighted.png", dpi=170)
plt.close(fig)

# ---------- 2. cost ----------
best60 = best[best.score > 60]  # cost and turns only for models that clear 60 pass@1
c = best60.sort_values("cost_usd")
fig, ax = figure("Cost per completed task", "DeepSWE v1.1 mean USD per task, best-scoring config per model with "
                 "pass@1 > 60, mini-swe-agent scaffold (log scale)", "COST")
vals_bars(ax, [f"{m} [{e}]" for m, e in zip(c.model, c.reasoning_effort.fillna(""))],
          c.cost_usd.tolist(), lambda v: f"${v:.2f}")
ax.set_yscale("log")
ax.set_ylabel("USD per task (log)")
fig.savefig(OUT / "02_cost_per_task.png", dpi=170)
plt.close(fig)

# ---------- 3. time ----------
t = P.loc[top.index, "e2e"].dropna().sort_values()
fig, ax = figure("End-to-end response time", "Artificial Analysis median seconds per response, "
                 "same 14 models as the intelligence chart", "TIME")
vals_bars(ax, [short(m) for m in t.index], t.tolist(), lambda v: f"{v:.0f}s")
ax.set_ylabel("seconds (median)")
fig.savefig(OUT / "03_time_end_to_end.png", dpi=170)
plt.close(fig)

# ---------- 4. turns ----------
s = best60.sort_values("mean_agent_steps")
fig, ax = figure("Agent turns per task", "DeepSWE v1.1 mean agent steps, best-scoring config per model with pass@1 > 60",
                 "TURNS")
vals_bars(ax, [f"{m} [{e}]" for m, e in zip(s.model, s.reasoning_effort.fillna(""))],
          s.mean_agent_steps.tolist(), lambda v: f"{v:.0f}")
ax.set_ylabel("mean agent steps")
fig.savefig(OUT / "04_turns_agent_steps.png", dpi=170)
plt.close(fig)

# ---------- 5. pareto (DeepSWE style) ----------
order = {e: k for k, e in enumerate(["low", "medium", "high", "xhigh", "max"])}
CALLOUT = {"claude-opus-5", "claude-fable-5", "gpt-5.6-luna", "glm-5.3-flash", "gemini-3.8-flash"}
fig, ax = plt.subplots(figsize=(14, 7.5))
fig.subplots_adjust(top=0.86, bottom=0.1, left=0.06, right=0.80)
fig.text(0.04, 0.95, "DeepSWE score vs cost per task", fontsize=18, family="serif", color=INK)
fig.text(0.04, 0.915, "pass@1 across effort levels (low → max), one line per model, configs above 60% only."
         "Up and right is better.", fontsize=9.5, color="#555555")
ds60 = ds[ds.score > 60]  # every plotted point clears 60, not just the model's best config
MODELS60 = ds60.groupby("model").score.max().sort_values(ascending=False).index.tolist()  # legend in score order
for i, m in enumerate(MODELS60):
    d = ds60[ds60.model == m]
    d = d.assign(o=d.reasoning_effort.map(order)).sort_values("o")
    col = PAL[i % len(PAL)]
    tip = d.iloc[-1]
    strong = True
    ax.plot(d.cost_usd, d.score, "-", color=col, lw=1.6 if strong else 0.9, alpha=0.9 if strong else 0.35,
            label=f"{m}  [{tip.reasoning_effort}] {tip.score:.0f}%" if strong else None)
    ax.scatter(d.cost_usd, d.score, s=30 if strong else 14, color=col, edgecolor="white", lw=0.8,
               alpha=1 if strong else 0.5, zorder=3)
    if m in CALLOUT:
        ax.annotate(f"{m} [{tip.reasoning_effort}]", (tip.cost_usd, tip.score), xytext=(8, 10),
                    textcoords="offset points", fontsize=8, family="monospace", color=col, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=col, lw=0.6, alpha=0.6))
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=7.5,
          prop={"family": "monospace", "size": 7.5}, title="pass@1 > 60 configs", title_fontsize=8)
ax.set_xscale("log")
ax.invert_xaxis()
ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"${v:g}"))
ax.set_xlabel("avg cost per task (USD, log; cheaper →)")
ax.set_ylabel("DeepSWE v1.1 pass@1 (%)")
ax.text(0.98, 0.97, "most efficient ↗", transform=ax.transAxes, ha="right", va="top",
        family="monospace", fontsize=9, color="#5B9BF0")
dotgrid(ax)
fig.savefig(OUT / "05_pareto_score_vs_cost.png", dpi=170)
plt.close(fig)

# ---------- 6. per-benchmark grid ----------
def vals_top(bench, n=8):
    d = va[va.benchmark == bench].sort_values("score", ascending=False).head(n)
    return d.model.str.split("/").str[-1].tolist(), d.score.tolist(), d.stderr.tolist()


def aa_top(col, n=8, min_coding=None):
    d = P if min_coding is None else P[P.coding >= min_coding]
    d = d[col].dropna().sort_values(ascending=False).head(n)
    return [short(m) for m in d.index], d.tolist(), None


panels = [("Code Migration (Vals, ±stderr)", *vals_top("Code Migration"), "{:.1f}"),
          ("CorpFin v2 (Vals, ±stderr)", *vals_top("CorpFin v2"), "{:.1f}"),
          ("Coding Index (AA)", *aa_top("coding"), "{:.1f}"),
          ("Agentic Index (AA)", *aa_top("agentic"), "{:.1f}"),
          ("AA-LCR long context", *aa_top("lcr"), "{:.3f}"),
          ("Non-hallucination rate (AA, Coding ≥ 70)", *aa_top("nh", min_coding=70), "{:.3f}"),
          ("Terminal-Bench 2.1 (AA)", *aa_top("tb"), "{:.3f}"),
          ("IFBench (AA)", *aa_top("ifb"), "{:.3f}")]
fig, axes = plt.subplots(2, 4, figsize=(20, 10.5))
fig.subplots_adjust(top=0.86, bottom=0.2, left=0.04, right=0.99, wspace=0.18, hspace=0.75)
fig.text(0.02, 0.96, "Each benchmark separately, top 8", fontsize=18, family="serif", color=INK)
fig.text(0.02, 0.93, "Vals benchmarks show stderr whiskers. Artificial Analysis publishes no error bars.",
         fontsize=9.5, color="#555555")
fig.text(0.98, 0.96, STAMP, fontsize=8.5, family="monospace", ha="right", color=INK, fontweight="bold")
for ax, (title, labels, vals, err, fmt) in zip(axes.flat, panels):
    vals_bars(ax, labels, vals, lambda v, f=fmt: f.format(v), err=err)
    ax.set_title(title, fontsize=10.5, family="serif", loc="left", color=INK)
    ax.tick_params(axis="x", labelsize=7)
fig.savefig(OUT / "06_benchmarks_grid.png", dpi=150)
plt.close(fig)

# ---------- 7/8. role-weighted indexes ----------
# Cross-source join for the handful of models in the shortlist. Regex on the
# source-native id; anything that does not match is excluded from that index
# (missing-score rule), never imputed.
ALIAS = {  # AA model string -> (vals regex, deepswe model)
    "Claude Opus 5 (Adaptive Reasoning, Max Effort)": (r"claude-opus-5$", "claude-opus-5"),
    "Claude Fable 5.1 (Adaptive Reasoning, Max Effort, Default Fallback)": (r"claude-fable-5$", "claude-fable-5"),
    "GPT-5.6 Sol (max)": (r"gpt-5\.6-sol", "gpt-5.6-sol"),
    "GPT-5.6 Terra (max)": (r"gpt-5\.6-terra", "gpt-5.6-terra"),
    "GPT-5.6 Luna (max)": (r"gpt-5\.6-luna", "gpt-5.6-luna"),
    "Kimi K3 (max)": (r"kimi-k3", "kimi-k3"),
    "Grok 4.6 (xhigh)": (r"grok-4\.6", "grok-4.6"),
    "Gemini 3.8 Flash (high)": (r"gemini-3[-.]8-flash", "gemini-3.8-flash"),
    "GLM-5.3-Flash": (r"glm-5\.3-flash", "glm-5.3-flash"),
    "GLM-5.3 (max)": (r"glm-5\.3$", "glm-5.3"),
    "Qwen3.8-Flash-Next": (r"qwen3\.8-flash", None),
    "Claude Opus 4.8 (Adaptive Reasoning, Max Effort)": (r"claude-opus-4-8", "claude-opus-4.8"),
    "Muse Spark 1.2 (xhigh)": (r"muse_spark_1_2", "muse-spark-1.2"),
    "Muse Spark 1.3 (xhigh)": (r"muse_spark_1_3", "muse-spark-1.3"),
    "GPT-6 Astra (max)": (r"gpt-6-astra", "gpt-6-astra"),  # AA only; Vals and DeepSWE have no 1.3 yet
}


def vals_score(bench, rx):
    d = va[(va.benchmark == bench) & va.model.str.contains(rx, regex=True)]
    return (d.score.iloc[0], d.stderr.iloc[0]) if len(d) else (np.nan, np.nan)


rows = []
for m, (rx, dsm) in ALIAS.items():
    if m not in P.index:
        continue
    r = P.loc[m].to_dict()
    r["model"] = short(m)
    r["code_mig"], r["code_mig_se"] = vals_score("Code Migration", rx)
    r["corpfin"], r["corpfin_se"] = vals_score("CorpFin v2", rx)
    b = best[best.model == dsm]
    r["task_cost"] = b.cost_usd.iloc[0] if len(b) else np.nan
    r["pass1"] = b.score.iloc[0] if len(b) else np.nan
    r["ds_effort"] = b.reasoning_effort.iloc[0] if len(b) else ""
    rows.append(r)
S = pd.DataFrame(rows).set_index("model")


def minmax(s, invert=False, log=False):
    v = np.log10(s) if log else s
    out = (v - v.min()) / (v.max() - v.min()) * 100
    return 100 - out if invert else out


S["overall"] = (S.coding * 0.30 + S.agentic * 0.25 + S.lcr * 100 * 0.15 + S.nh * 100 * 0.15 + S.acc * 100 * 0.15)
S["batch"] = (S.code_mig * 0.30 + S.coding * 0.25 + S.agentic * 0.20 + S.lcr * 100 * 0.15 + S.nh * 100 * 0.10)
S["interactive"] = (S.coding * 0.30 + S.agentic * 0.20 + S.nh * 100 * 0.20
                    + minmax(S.e2e, invert=True, log=True) * 0.15 + minmax(S.price, invert=True, log=True) * 0.15)
S["quality"] = S.coding * 0.40 + S.agentic * 0.30 + S.nh * 100 * 0.30

ROLE_TABS = ("OVERALL", "BATCH", "INTERACTIVE", "QUALITY")
b = S.dropna(subset=["batch"]).sort_values("batch", ascending=False)
fig, ax = figure("Batch role index: migration and package rewrite",
                 "0.30 Code Migration (Vals) + 0.25 Coding + 0.20 Agentic + 0.15 long-context + 0.10 non-hallucination. "
                 "Models without a Code Migration score are excluded.", "BATCH", items=ROLE_TABS)
vals_bars(ax, b.index.tolist(), b.batch.tolist(), lambda v: f"{v:.1f}")
ax.set_ylabel("batch index (0-100)")
fig.savefig(OUT / "07_index_batch.png", dpi=170)
plt.close(fig)

i = S.dropna(subset=["interactive"]).sort_values("interactive", ascending=False)
fig, ax = figure("Interactive role index: page-edit loop",
                 "0.30 Coding + 0.20 Agentic + 0.20 non-hallucination + 0.15 speed (inverse log end-to-end) "
                 "+ 0.15 price (inverse log $/1M)", "INTERACTIVE", items=ROLE_TABS)
vals_bars(ax, i.index.tolist(), i.interactive.tolist(), lambda v: f"{v:.1f}")
ax.set_ylabel("interactive index (0-100)")
fig.savefig(OUT / "08_index_interactive.png", dpi=170)
plt.close(fig)

q = S.dropna(subset=["quality"]).sort_values("quality", ascending=False)
fig, ax = figure("Quality role index: model quality only",
                 "0.40 Coding + 0.30 Agentic + 0.30 non-hallucination", "QUALITY", items=ROLE_TABS)
vals_bars(ax, q.index.tolist(), q.quality.tolist(), lambda v: f"{v:.1f}")
ax.set_ylabel("quality index (0-100)")
fig.savefig(OUT / "09_index_quality.png", dpi=170)
plt.close(fig)

# summary table for the report (stdout)
cols = ["overall", "batch", "interactive", "quality", "coding", "agentic", "code_mig", "corpfin", "nh", "acc", "e2e", "price", "task_cost", "pass1"]
print(S[cols].sort_values("overall", ascending=False).round(2).to_string())

# ---------- interactive (Plotly) twins of every chart, same data ----------
import plotly.graph_objects as go  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

MONO = "DejaVu Sans Mono, Menlo, monospace"
SERIF = "Georgia, DejaVu Serif, serif"


def playout(fig, title, subtitle, height=520):
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:12px;color:#555'>{subtitle}</span>",
                   font=dict(family=SERIF, size=20, color=INK), x=0.01, xanchor="left"),
        paper_bgcolor=BG, plot_bgcolor=BG, height=height, margin=dict(l=50, r=20, t=90, b=40),
        font=dict(family=MONO, size=11, color=INK), hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="white"),
        legend=dict(font=dict(family=MONO, size=10)),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#c8c8c8", griddash="dot", zeroline=False, linecolor=INK)
    fig.update_yaxes(showgrid=True, gridcolor="#c8c8c8", griddash="dot", zeroline=False, linecolor=INK)
    return fig


def pbars(labels, values, hover, fmt, title, subtitle, ytitle, err=None, logy=False):
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker=dict(color=[PAL[k % len(PAL)] for k in range(len(values))],
                                        line=dict(color=INK, width=1.1)),
        text=[fmt(v) for v in values], textposition="inside", insidetextanchor="end",
        textfont=dict(family=MONO, size=11), customdata=hover,
        hovertemplate="%{x}<br>%{customdata}<extra></extra>",
        error_y=dict(type="data", array=err, color=INK, thickness=1.2, width=3) if err is not None else None,
    ))
    playout(fig, title, subtitle)
    fig.update_yaxes(title=ytitle, type="log" if logy else "linear")
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=10))
    return fig


def save(fig, name):
    fig.write_html(OUT / f"{name}.html", include_plotlyjs="cdn", full_html=False,
                   config={"responsive": True, "displaylogo": False})


def idx_hover(df, col_weights):
    return [" | ".join(f"{c} {getattr(r, c) * (100 if c in ('lcr', 'nh', 'acc') else 1):.1f}" for c in col_weights)
            + f"<br><b>index {getattr(r, 'index' if 'index' in df.columns else 'score'):.1f}</b>" for r in df.itertuples()]


# 01 overall
save(pbars([short(m) for m in top.index], top["index"].tolist(),
           [f"coding {r.coding:.1f} | agentic {r.agentic:.1f} | lcr {r.lcr:.2f} | non-halluc {r.nh:.2f} | acc {r.acc:.2f}"
            f"<br><b>overall {r.index:.1f}</b>" for r in top.itertuples()],
           lambda v: f"{v:.1f}", "Overall weighted index",
           "0.30 Coding + 0.25 Agentic + 0.15 long-context + 0.15 non-hallucination + 0.15 accuracy",
           "weighted index (0-100)"), "01_intelligence_weighted")
# 02 cost
save(pbars([f"{m} [{e}]" for m, e in zip(c.model, c.reasoning_effort.fillna(""))], c.cost_usd.tolist(),
           [f"pass@1 {r.score:.1f} ±{r.ci_half_pct:.1f} | steps {r.mean_agent_steps:.0f} | out tok {r.mean_output_tokens/1000:.0f}k"
            f"<br><b>${r.cost_usd:.2f} per task</b>" for r in c.itertuples()],
           lambda v: f"${v:.2f}", "Cost per completed task",
           "DeepSWE v1.1 mean USD per task, best-scoring config with pass@1 > 60, log scale",
           "USD per task (log)", logy=True), "02_cost_per_task")
# 03 time
save(pbars([short(m) for m in t.index], t.tolist(),
           [f"TTFT {P.loc[m, 'ttft']:.1f}s<br><b>{v:.0f}s end to end</b>" for m, v in t.items()],
           lambda v: f"{v:.0f}s", "End-to-end response time", "Artificial Analysis median seconds per response",
           "seconds (median)"), "03_time_end_to_end")
# 04 turns
save(pbars([f"{m} [{e}]" for m, e in zip(s.model, s.reasoning_effort.fillna(""))], s.mean_agent_steps.tolist(),
           [f"pass@1 {r.score:.1f} | ${r.cost_usd:.2f}/task<br><b>{r.mean_agent_steps:.0f} steps</b>" for r in s.itertuples()],
           lambda v: f"{v:.0f}", "Agent turns per task",
           "DeepSWE v1.1 mean agent steps, best-scoring config with pass@1 > 60",
           "mean agent steps"), "04_turns_agent_steps")
# 05 pareto
fig = go.Figure()
for k, m in enumerate(MODELS60):
    d = ds60[ds60.model == m].assign(o=lambda x: x.reasoning_effort.map(order)).sort_values("o")
    fig.add_trace(go.Scatter(
        x=d.cost_usd, y=d.score, mode="lines+markers", name=f"{m} {d.score.max():.0f}%",
        line=dict(color=PAL[k % len(PAL)], width=2), marker=dict(size=8, line=dict(color="white", width=1)),
        customdata=np.stack([d.reasoning_effort.fillna(""), d.ci_half_pct, d.mean_agent_steps, d.mean_output_tokens / 1000], axis=1),
        hovertemplate=f"<b>{m}</b> [%{{customdata[0]}}]<br>pass@1 %{{y:.1f}} ±%{{customdata[1]:.1f}}"
                      "<br>$%{x:.2f} per task<br>%{customdata[2]:.0f} steps | %{customdata[3]:.0f}k out tokens<extra></extra>"))
playout(fig, "DeepSWE score vs cost per task",
        "pass@1 across effort levels (low → max), one line per model, configs above 60% only.Up and right is better.",
        height=600)
fig.update_xaxes(type="log", autorange="reversed", title="avg cost per task (USD, log; cheaper →)", tickprefix="$")
fig.update_yaxes(title="DeepSWE v1.1 pass@1 (%)")
fig.add_annotation(x=0.99, y=0.98, xref="paper", yref="paper", text="most efficient ↗", showarrow=False,
                   font=dict(color="#5B9BF0", family=MONO))
save(fig, "05_pareto_score_vs_cost")
# 06 grid, 4 rows x 2 cols so the page never shows more than two charts side by side
fig = make_subplots(rows=4, cols=2, subplot_titles=[p[0] for p in panels], vertical_spacing=0.09, horizontal_spacing=0.06)
for k, (title, labels, vals, err, fmt) in enumerate(panels):
    fig.add_trace(go.Bar(
        x=labels, y=vals, marker=dict(color=[PAL[j % len(PAL)] for j in range(len(vals))], line=dict(color=INK, width=1)),
        text=[fmt.format(v) for v in vals], textposition="inside", insidetextanchor="end", textfont=dict(size=10),
        error_y=dict(type="data", array=err, color=INK) if err else None,
        hovertemplate="%{x}<br><b>%{y}</b>" + (" ±%{error_y.array:.2f}" if err else "") + "<extra></extra>",
        showlegend=False), row=k // 2 + 1, col=k % 2 + 1)
playout(fig, "Each benchmark separately, top 8", "Vals panels carry stderr whiskers; Artificial Analysis publishes no error bars",
        height=1500)
fig.update_xaxes(tickangle=-35, tickfont=dict(size=9))
save(fig, "06_benchmarks_grid")
# 07/08 role indexes
save(pbars(b.index.tolist(), b.batch.tolist(),
           [f"code mig {r.code_mig:.1f} | coding {r.coding:.1f} | agentic {r.agentic:.1f} | lcr {r.lcr:.2f} | non-halluc {r.nh:.2f}"
            f"<br><b>batch {r.batch:.1f}</b>" for r in b.itertuples()],
           lambda v: f"{v:.1f}", "Batch role index: migration and package rewrite",
           "0.30 Code Migration + 0.25 Coding + 0.20 Agentic + 0.15 long-context + 0.10 non-hallucination",
           "batch index (0-100)"), "07_index_batch")
save(pbars(i.index.tolist(), i.interactive.tolist(),
           [f"coding {r.coding:.1f} | agentic {r.agentic:.1f} | non-halluc {r.nh:.2f} | e2e {r.e2e:.0f}s | ${r.price:g}/1M"
            f"<br><b>interactive {r.interactive:.1f}</b>" for r in i.itertuples()],
           lambda v: f"{v:.1f}", "Interactive role index: page-edit loop",
           "0.30 Coding + 0.20 Agentic + 0.20 non-hallucination + 0.15 speed + 0.15 price",
           "interactive index (0-100)"), "08_index_interactive")
save(pbars(q.index.tolist(), q.quality.tolist(),
           [f"coding {r.coding:.1f} | agentic {r.agentic:.1f} | non-halluc {r.nh:.2f}"
            f"<br><b>quality {r.quality:.1f}</b>" for r in q.itertuples()],
           lambda v: f"{v:.1f}", "Quality role index: model quality only",
           "0.40 Coding + 0.30 Agentic + 0.30 non-hallucination",
           "quality index (0-100)"), "09_index_quality")

print("wrote", sorted(p.name for p in OUT.glob("0*.png")), "+", len(list(OUT.glob("0*.html"))), "interactive html")
