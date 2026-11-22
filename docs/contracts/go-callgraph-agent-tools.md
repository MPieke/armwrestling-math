---
linear_issue: TBD
status: proposed
---

# Contract go-callgraph-agent-tools: fix findings locally with a coding agent

> No Linear ticket exists yet, so no `MPI-NN` code (see `docs/repository-guidance.md`).
> Builds on `docs/contracts/go-route-story.md` and `go-route-safety.md` (PR #19).

## Context
CI already finds redundancy cards and renders them. Fixing them is conversational and
judgement-heavy, so it happens locally: the dev talks to a coding agent. A deterministic tool
(CLI plus a thin MCP wrapper, no LLM) gives the agent the facts, diagrams, test skeletons and a
"did the finding go away" check. The dev approves at two points only: the proposed plan (before
code changes) and the finished work (before pushing). CI stays as it is, re-analyses the pushed
code on its own, and does **not** gate on findings. Each card gets a display-only confidence level.

Not in scope: any CI gate or exit code, `decisions.yml`, `baseline.json`, committed suppressions,
CI-side fixing or PR bots, the gold set, a "try the fix" job, changes to the LLM prompt.

## 1. Current state
```
CI                                             DEV MACHINE
 CodeQL -> csv -> build.py (graph)              the coding agent edits by hand; nothing
 analyze.py -> findings.json (terminals)         deterministic helps with facts per card,
 cards.py (rebuilt each run, never written)      diagrams from a plan, test skeletons,
 judge.py (LLM, advisory) -> judgements.json     or "is it fixed?"
 render.py + safety.py + diagrams.py -> Summary
 verify.py (graph vs source). No exit code on findings.
```

## 2. Target state
```
 DEV MACHINE                                                   GITHUB
 +-------------------------------------------------+          +--------------------------+
 | DEV <-- chat, steer, approve --> CODING AGENT   |          | CI (as today)            |
 |                                    |    ^       |          |  + confidence level on   |
 |                             edits  |    | MCP/CLI|          |    each card (display)   |
 |                                    v    |        |  git push|  no gate                 |
 | CODEBASE (working tree) <--- callgraph tools    |--------->|  re-analyses all code    |
 |  + .callgraph/ (gitignored)   tools/callgraph/  |          +--------------------------+
 |      plan.json, snapshot.json cli.py, plan.py,  |
 |                               mcp_server.py     |
 +-------------------------------------------------+
 AUTOMATIC (agent runs; dev may too)      APPROVAL-GATED (dev must say yes)
   findings   cards + level                 plan approve    checkpoint 1
   card N     facts for one card            review approve  checkpoint 2
   plan lint  checks the plan
   diagram    before/after mermaid
   tests      Go test skeletons
   check      re-analyse locally
```
Approval is enforced by configuration: the gated tools are left out of the agent's allow-list so
the harness asks the dev. The tool never claims a human approved.

Sequence for one card:
```
dev           agent                      tools                        codebase
 |-- fix 1 --->|-- findings / card 1 ---->| facts                          |
 |             |<-------------------------|                                |
 |             |-- reads code ------------------------------------------->|
 |             |-- plan.json; plan lint; diagram                           |
 |<- proposal -|  (diagrams, parameters, tests, will-not-touch)            |
 |-- feedback->|-- revises plan (loop)                                     |
 |-- approve ->|-- plan approve (prompts dev)                              |
 |             |-- edits, tests skeleton, go test ------------------------>|
 |             |-- check: card gone? diff in planned files? -------------->|
 |<- evidence -|-- review approve (prompts dev)                            |
 |-- push -----------------------------------------> CI re-analyses        |
```

## 3. Design
- **Confidence level** (display only): `high` overlap >= 0.6, `medium` >= 0.3, `low` below, from the
  existing `cards.Evidence.band`. It compares which calls are made, not the code: a weak,
  uncalibrated signal. *Correction to the approved plan:* the level lives on the card's
  `Evidence`, not in `findings.json` (that file is per terminal; cards are rebuilt on each run).
- **Plan** (`.callgraph/plan.json`, local, gitignored): card, steps with line ranges, moved steps,
  shared name, parameters, constraints, will-not-touch, tests, uncertainties. Same step/fix shape
  as the judge, so its validators are reused.
- **`plan lint`**: judge validators plus: every difference inside a moved "same" step is covered by
  a parameter or marked "stays"; moved steps exist; will-not-touch vs planned files.
- **`check`**: re-runs CodeQL, build, analyze, cards on the working tree; reports target card
  gone, new cards versus the session snapshot, changed files versus the plan. Needs `codeql`;
  otherwise says to push and let CI check. `findings` uses a local run, or `--from-ci` fetches the
  branch's latest artifact.
- **MCP** is last and thin, official `mcp` SDK in `requirements-mcp.txt`; core stays networkx-only.

## 4. Commits (test-first; each test commit red and recorded)
1. docs: this contract.
2. test / feat: confidence level on `Evidence` and in the card header.
3. test / feat: `cli.py` with `findings` and `card N --json`.
4. test / feat: `plan.py` (schema, load/save, lint).
5. test / feat: `diagram` command.
6. test / feat: `tests` skeleton generator.
7. test / feat: `check` with an injectable pipeline runner.
8. test / feat: MCP wrapper.
9. ci + docs: CLI smoke step, README section, example `.claude/settings.json`, results here.

## 5. Verification plan
- `python -m unittest discover -v -s tools/callgraph/tests -t .`; `ruff check tools`; CI green.
- Importer artifact: `findings` lists the same 6 cards as the Summary with levels high / medium /
  low; `card 1 --json` equals the Summary's safety block; `plan lint` rejects a card-1 plan that
  omits `annotator -> extractor` and a range outside the function, accepts the corrected plan.
- Scratch copy of armwrestling-math (not committed): apply the Annotate/Extract fix using the
  tools, `go test` passes (DB tests reported as not run), `check` shows card 1 gone, no new cards.
- MCP: `claude mcp add`, call each tool once; gated tools must prompt.
- No tool output may claim behaviour preservation.

## 6. Defaults and risks
Gate off. Local analysis needs CodeQL (macOS autobuild only). Card numbers can shift as code
changes, so the CLI also accepts a function pair. Tests needing external services may be skipped
locally and `check` lists what was not verified.
