"""Every string the pipeline writes into a report, in one place.

A report is written in the language the user asked for, so the prose is the
model's job and these are not. They are the labels the engine and the HTML
build emit on their own: table headers, the fill control, an empty cell, a
chart annotation.

`profile.json` carries the overrides:

    "language": "tr",
    "strings": {"model": "model", "best model": "en iyi model", ...}

Anything absent falls back to English, so a half translated profile still
builds. Keys are the English string itself, which keeps a diff readable and
means an untranslated key is visible in the output rather than hidden behind
a code like `tbl.hdr.model`.
"""

DEFAULTS = {
    # glance and master table headers
    "model": "model",
    "index": "index",
    "weights": "weights",
    "best model": "best model",
    "cheap alternative": "cheap alternative",
    # picks
    "no model has every input": "no model has every input",
    "none qualifies": "none qualifies",
    "behind": "behind",
    "cheaper": "cheaper",
    # charts
    "models": "models",
    "models with a price": "models with a price",
    "on the frontier": "on the frontier",
    "bubble size": "bubble size",
    "log scale": "log scale",
    # index columns
    "computed in this report": "computed in this report",
    "weighted score": "Weighted score, 0 to 100, higher is better",
    # the fill control and the empty cells it explains
    "missing benchmark": "missing benchmark",
    "exclude": "exclude",
    "fill 0": "fill 0",
    "fill median": "fill median",
    "n/a": "n/a",
    "not scored": "{model} is not scored on {label}: no {missing}. "
                  "A missing benchmark is never filled in, so the model is left out.",
    "no row": "{label}: {site} publishes no row for {model}. "
              "Nothing is assumed in its place.",
    "an input": "an input",
}


def strings(profile):
    """Merge the profile's overrides over the English defaults."""
    return {**DEFAULTS, **(profile.get("strings") or {})}
