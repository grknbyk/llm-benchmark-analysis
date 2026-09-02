"""Build two profiles in one process, both orders, and diff the artifacts.

The toolkit is meant to be stack independent, and the way that quietly stops
being true is module level state: a list or a dict that one profile writes and
the next one reads. Those are invisible in a single run and obvious here.

    uv run --with matplotlib --with pandas --with plotly python \\
      pipeline/crosstest.py charts reports/a/profile.json reports/b/profile.json
    uv run --with markdown python \\
      pipeline/crosstest.py html reports/a/profile.json reports/b/profile.json

Each profile is built alone in its own process, then both orders are built in
one shared process. Anything that differs between "alone" and "after the other
one" is residue. `charts` compares results.json and the two tables; `html`
compares the tooltip count and the exact set of terms that got a definition.

Run it against two profiles from genuinely different stacks. Two profiles that
score from the same sites and share a glossary will pass while hiding the bug.
"""
import io, json, re, subprocess, sys, contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

KEYS = {"charts": ["results.json", "master-table.md", "glance-table.md"],
        "html": ["tooltips", "terms"]}


def out_dir(profile):
    P = json.loads(Path(profile).read_text(encoding="utf-8"))
    return Path(P.get("out") or Path(profile).parent), P


def snapshot(profile, stage):
    d, P = out_dir(profile)
    if stage == "charts":
        return {f: (d / f).read_text(encoding="utf-8") if (d / f).exists() else None
                for f in KEYS["charts"]}
    html = d / P["report"].replace(".md", ".html")
    if not html.exists():
        return {"tooltips": None, "terms": None}
    t = html.read_text(encoding="utf-8")
    return {"tooltips": len(re.findall(r"<abbr ", t)),
            "terms": sorted(set(re.findall(r"<abbr [^>]*>(.*?)</abbr>", t)))}


def build(profile, stage):
    mod = __import__("make_charts" if stage == "charts" else "build_html")
    with contextlib.redirect_stdout(io.StringIO()):
        mod.main(str(profile))


def alone(profile, stage):
    """A fresh interpreter, so the baseline carries no state from any sibling."""
    subprocess.run([sys.executable, __file__, "_one", stage, profile], check=True)
    return snapshot(profile, stage)


def main(stage, a, b):
    base = {p: alone(p, stage) for p in (a, b)}
    bad = False
    for first, second in ((a, b), (b, a)):
        build(first, stage)
        build(second, stage)
        now, was = snapshot(second, stage), base[second]
        diff = [k for k in KEYS[stage] if now.get(k) != was.get(k)]
        print(f"\n{Path(first).parent.name} -> {Path(second).parent.name}"
              f"   (does building the first change the second?)")
        for k in KEYS[stage]:
            same = now.get(k) == was.get(k)
            gained = ""
            if k == "terms" and not same:
                gained = f"  gained: {sorted(set(now.get(k) or []) - set(was.get(k) or []))}"
            print(f"  {k:<18} {'same' if same else 'DIFFERENT'}{gained}")
        print(f"  verdict: {'CLEAN' if not diff else 'RESIDUE in ' + str(diff)}")
        bad = bad or bool(diff)
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1] == "_one":
        build(sys.argv[3], sys.argv[2])
    else:
        sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
