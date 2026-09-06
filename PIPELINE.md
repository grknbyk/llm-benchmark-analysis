# Pipeline

One run, five stages. Stages 1 and 2 start together; nothing else overlaps.

1. **Confirm.** Which stack profile, and which scrape day. Nothing spawns before
   this answer.
2. **Gather.** Ten agents, one per leaderboard, into
   `benchmark-data/<YYYYMMDD>/<site>/`. In parallel, research agents run
   `last30days` over the stack for skills, MCP servers and what moved in the
   window.
3. **Roles.** `pipeline/catalogue.py` prints every metric the fresh data
   carries. The roles and their weights go into `profile.json`. Two to four
   roles, weights summing to 1.00, no metric that the catalogue does not list.
4. **Calculate.** `pipeline/make_charts.py` joins the sources, scores every
   role, and writes `results.json`, `master-table.md`, `glance-table.md` and one
   chart per role. Every number in the report comes from here.
5. **Report and deploy.** Paste the two tables, write one section per role, run
   `report-prose`, build the HTML, rebuild `index.html`, push one squashed
   commit to the data branch.

## Worked example

```bash
# 1. confirm: ERP profile, scrape day 20260906

# 2. gather: ten scrape agents write benchmark-data/20260906/

# 3. roles: read what the data has, then write the profile
python pipeline/catalogue.py benchmark-data/20260906 --min-models 10

# 4. calculate
uv run --with matplotlib --with pandas --with plotly python \
  pipeline/make_charts.py reports/20260906-erp-oracle-apex/profile.json

# 5. report and deploy
uv run --with markdown python pipeline/build_html.py reports/20260906-erp-oracle-apex/profile.json
python pipeline/build_index.py
git add -A && git commit -q --amend -m "<the data branch's fixed message>" \
  && git push --force-with-lease origin <data-branch>
```

## Two skills only you can start

`adhd` and `remove-ai-slop` carry `disable-model-invocation`, so the model
cannot call them. Copying them into `.claude/skills/` does not help either:
personal skills in `~/.claude/skills/` shadow project skills of the same name.

They are checkpoints, not steps. The run stops and hands you the prompt:

- Stage 3, type `/adhd` to derive the roles. The result goes into
  `profile.json` and the engine reads only that.
- Stage 5, type `/remove-ai-slop` for the broad prose sweep, after
  `report-prose` has done the repo-specific pass.

A section may never claim either skill's authorship without your turn in the
transcript behind it.
