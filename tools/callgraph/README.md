# Call graph tools

Extracts a function-level call graph of `services/importer` (Go) with CodeQL,
validates it, and renders it so every node and edge links back to the exact
source lines. Contract: [`docs/contracts/go-callgraph.md`](../../docs/contracts/go-callgraph.md).

## Pipeline

```text
CodeQL database --nodes.ql/edges.ql--> raw CSV --build.py--> nodes.csv, edges.csv
                                                       |--trace.py   file[:line] -> nodes/edges
                                                       '--render.py  callgraph.dot, summary.md
                                                                     (dot -Tsvg -> callgraph.svg)
```

## Schema

`nodes.csv`: `id, lang, name, package, file, start_line, end_line, sha`
`edges.csv`: `caller_id, callee_id, call_file, call_line, sha`

Paths are repo-relative and lines are 1-based. An edge is one call site, so two
calls from `a` to `b` on different lines are two edges. `build.py` rejects
duplicate ids, edges to unknown functions, and call sites outside the caller's
file and line range.

## Run locally

```bash
brew install --cask codeql graphviz        # once
(cd codeql && codeql pack install go && codeql pack install go/test)

# tests
python3 -m unittest discover -v -s tools/callgraph/tests -t .
(cd codeql && codeql test run go/test)

# extract (Go autobuild; source root is the repo root so paths are repo-relative)
codeql database create /tmp/cg/db --language=go --source-root=.
for q in nodes edges; do
  codeql query run --database=/tmp/cg/db --output=/tmp/cg/$q.bqrs codeql/go/$q.ql
  codeql bqrs decode --format=csv --output=/tmp/cg/raw_$q.csv /tmp/cg/$q.bqrs
done

python3 -m tools.callgraph.build --nodes /tmp/cg/raw_nodes.csv --edges /tmp/cg/raw_edges.csv \
  --sha "$(git rev-parse HEAD)" --include-prefix services/importer --out-dir /tmp/cg/out
python3 -m tools.callgraph.render --graph-dir /tmp/cg/out \
  --repo-url https://github.com/MPieke/armwrestling-math
dot -Tsvg /tmp/cg/out/callgraph.dot -o /tmp/cg/out/callgraph.svg
```

On macOS the CodeQL Go extractor does not see compiles started by an explicit
`--command "go build"` (SIP), so rely on the autobuild as above.

## Trace a location

```bash
python3 -m tools.callgraph.trace services/importer/cmd/annotate-claims/main.go:18 \
  --graph-dir /tmp/cg/out
```

## In CI

`.github/workflows/callgraph.yml` runs both test layers, extracts the graph, and
writes everything reviewable to the run's Summary tab, so no download is needed:
package and function Mermaid diagrams, package totals, most called, most calls
out, never-called functions, and collapsible lists of every function and call
site with links to the source line. The `callgraph` artifact additionally holds
the CSVs, `callgraph.dot`, and `callgraph.svg` (open in a browser; clicking a
node or edge opens the GitHub source at that commit). Listings are capped at
2000 rows each to stay under GitHub's 1 MiB summary limit.

## Route analysis

`analyze.py` reads `nodes.csv`, `edges.csv` and `externals.csv` (language-agnostic)
and finds functions reached by several *independent routes*.

- **Entry**: `root_kind` main, init, referenced (used as a value, e.g. a handler),
  or exported-uncalled. Functions called from package-level initializers are
  `init`. `unreferenced` functions and code reachable only from them are dead.
- **Terminal**: a function that calls a non-ignored external function
  (`ignored_externals.txt` is an opt-out noise filter; suppressed counts are
  printed).
- **K**: the number of independent routes (no shared interior function) from the
  entries to the terminal, found with max-flow on a node-split graph. Entries are
  uncuttable; a direct call counts as a route.
- **Gateways**: the minimum cut nearest the terminal, the last functions where the
  routes are still separate, shown with how many entries each serves.
- **Chokepoints and segments**: functions on every route; K is recomputed between
  them, so a funnel followed by a diamond is shown as such. Each entry is also
  analysed alone, which exposes splits below a merge point ("nested").
- Cycles are collapsed first, so loops add no routes.

`python3 -m tools.callgraph.analyze --graph-dir out` writes `findings.csv` and
`findings.json`. Thresholds: `--min-entries`, `--min-gateways` (default 2).

## Verifying the analysis against the source

`python3 -m tools.callgraph.verify --graph-dir out --source-root . --repo-url ...`
re-reads the source independently of CodeQL. Hard checks (exit 1): M1 every call
line contains the callee, M2 every external call line contains the function, M3
every node starts on its `func` declaration. Notes for a reviewer: M4 referenced
entries are mentioned somewhere other than a call, M5 call-like text near flagged
terminals that the graph does not explain, M6 dynamic-dispatch hops on flagged
routes. `dossier.md` lays out every hop of the top findings with the code around
it; results of the review done on `services/importer` are in
`docs/contracts/go-route-analysis.md`.

Install the one dependency with `pip install -r tools/callgraph/requirements.txt`.

## Redundancy cards and the LLM judge

Every section of the run summary is a collapsible block with a one-line description;
only Redundant routes is open by default. It shows one card per redundancy. A card reads
top to bottom:

1. **Problem**: one sentence naming both functions (the model's headline; a
   deterministic sentence when there is no judgement).
2. **Advisory verdict**: one line, for example "extract the shared part (overlap,
   high confidence)".
3. **Diagram 1**: each function's steps as a chain, matched steps linked and coloured
   (orange = the same step in both functions, grey = differs), a red outline on every
   step the fix would move (plus any the model noted), the model's numbered notes with
   a legend, and a colour key. Each box also shows the calls in that step's source
   lines and the line range. Drawn by code.
4. **Fix** and **diagram 2**: the proposed change, and the same diagram after it, with
   the moved steps of both functions merged into one new dashed orange node, with the
   same colours and nothing red. Derived by code.
5. **Maybe intentional because**: the strongest reason the code may be deliberate and
   what would make it matter.
6. **Before you change this** (cards with a fix): two lines computed by code from the graph
   and the source, not by the model. Blast radius: who calls each function and whether
   through an interface. Tests: how many tests mention each function and which test one
   has that the other lacks, judged by test name (only when the names are parallel).
7. Dropdowns: safety check details (what differs inside the steps called the same, which a
   shared function must take as parameters; callers; tests found, all linked), evidence
   (calls both make, overlap), routes and entry points, and the model's details
   (explanation, differences, risks, citations, the step table with source links).

Cards the model says to leave as is fold into "Looked at, probably fine". A function
that reaches the same code two ways (`ingestCandidate` calls `Submit` directly and
through `auditFailure`) gets its own card type and a different question: deliberate
or accidental. Pairs are `cards.py` (last-hop callers within one parallel segment).

`judge.py` asks an LLM (default `gpt-6-luna`, override with `LLM_JUDGE_MODEL`). The
model supplies data, never drawings: `headline`, `action` (merge / extract_shared /
keep), `verdict`, ordered `steps` with line ranges, `issues` on those steps, a `fix`
with the step names that move, and `maybe_intentional`. Code checks all of it:

- step ranges must lie inside the function and may not overlap; issue notes must sit
  on a step and side that exist; fix step names must exist; what does not hold is
  dropped and counted (shown under "LLM details");
- every claim needs a citation (function, line, quote) checked against the source; no
  verifiable citation downgrades the verdict to `unsure`;
- failures (no `OPENAI_API_KEY`, API error, bad answer) are shown in the summary and
  never fail the build; the step is skipped for pull requests from forks;
- answers are cached by a hash of what the model saw (`actions/cache` in CI);
- `judge_golden.json` holds human reference labels; the summary shows how many the
  model agrees with and warns below two thirds.

`python3 -m tools.callgraph.judge --graph-dir out --source-root . --repo-url ... --dry-run`
writes `judge_inputs.md` (the exact prompts) without calling anything. The source of
the compared functions is sent to the API; check that before using it on private code.

## Fixing findings with a coding agent

CI finds the cards and never proposes fixes. Fixing is a conversation, so it happens on the
developer's machine with a coding agent (Claude Code, Cursor, ...). The tools in this section
give the agent deterministic facts, pictures, test skeletons and a re-check, so it does not rely
on memory for them. No tool calls an LLM; the model's suggestion from CI is shown as advisory.

| Command (MCP tool) | What it does | Who runs it |
| --- | --- | --- |
| `findings` | list cards with a confidence level | agent, automatic |
| `card REF` | callers, tests by name, test gaps, differences inside the steps called the same | agent, automatic |
| `plan init REF` (`plan_init`) | draft `.callgraph/plan.json`, every difference left undecided | agent, automatic |
| `plan lint` | check the plan against the code | agent, automatic |
| `plan diagram` | before and after pictures from the plan | agent, automatic |
| `plan tests` | skipped Go test skeletons pinning today's text, stubs for planned tests | agent, automatic |
| `check` | re-run CodeQL on the working tree and compare with the baseline | agent, automatic |
| `plan approve` (`plan_approve`) | **checkpoint 1**: the developer agrees to the plan | **developer** |
| `plan review` (`plan_review`) | **checkpoint 2**: the developer reviewed the finished work | **developer** |

The developer can run any of them too: `python -m tools.callgraph.cli --graph-dir DIR card 1`.

**Set up**

```sh
gh run download RUN_ID -n callgraph -D .callgraph/baseline          # the CI artifact is the baseline
pip install -r tools/callgraph/requirements.txt -r tools/callgraph/requirements-mcp.txt
claude mcp add callgraph -- python -m tools.callgraph.mcp_server \
  --graph-dir .callgraph/baseline --source-root . --scope services/importer
```

Copy `claude-settings.example.json` into `.claude/settings.json`. It allows the eight automatic
tools and makes the harness ask before `plan_approve` and `plan_review`. That is the only thing
that enforces the checkpoints: the tools record a decision, they cannot know a human made it.

**The conversation**

1. The agent calls `findings` and `card N` and reads the code.
2. It writes the plan (`plan init`, then edits `.callgraph/plan.json`), runs `plan lint` and
   `plan diagram`, and shows the developer the pictures, what moves, what stays, which tests.
3. The developer steers in words ("keep the public interface", "use the existing helper"); the
   agent updates the plan and lints again. Only when the developer agrees: `plan approve`.
4. The agent implements, fills in `plan tests` skeletons, runs the repository's tests and `check`.
5. The developer reviews the diff and the evidence; `plan review`. Then push: CI re-analyses
   everything from the code alone and needs no record of any of this.

**The plan** (`.callgraph/plan.json`, local, git-ignored): the card, the steps with line ranges,
which steps move into a shared function and its name, a decision for every difference inside a
moved step (`parameter` with a name, `unified`, or `stays`), planned files, `will_not_touch`,
constraints, tests, uncertainties. `plan lint` fails on: a bad or overlapping step range, a moved
step missing from one function, an undecided difference, a planned file under `will_not_touch`.
Constraints written in words are listed but not machine-checked. Approval stores a digest, so any
later edit to the plan revokes it.

**What `check` tells you**: whether the card is gone, how many direct calls the pair still shares
(before -> after), whether new cards appeared, whether changed files stayed inside the plan and
out of `will_not_touch`, whether the planned tests exist. It needs `codeql` on the machine (about
20 s on the importer); without it, push and let CI check.

For a fix that extracts a shared helper the card normally **stays**: both functions now reach the
helper by separate routes, which is what the analysis looks for. So a remaining card is an error
only if the pair's shared direct calls did not go down; if they did it is a warning with the
numbers. A new card that involves a function created by the change is also a warning (an old
duplicate may have moved with the code); a new card between two existing functions is an error.

**What none of this proves**: that behaviour is preserved. Tests are matched by name, the level is
call overlap only (high >= 0.6, medium >= 0.3, low below; not calibrated), and tests that need
external services may be skipped locally. `check` says so every time. CI does not fail on
findings.

## Scope and known gaps

- Test files (`*_test.go`) are excluded. Generated code such as
  `internal/dbgen` is included.
- Calls through interfaces and function values are resolved only as far as
  CodeQL resolves them. Calls into the standard library or dependencies produce
  no edge.
- A call inside a function literal is attributed to the enclosing declared
  function.
- A shared helper reached by two callers is flagged like a duplicate; whether the
  gateways do the same job needs a human (or the next-step evidence signals).
- Unused exported methods count as entries (`exported-uncalled`).
- Routes through an interface with several implementers may exist only for some
  runtime configurations (marked `[dynamic dispatch]` in the dossier).
- Reflection and function values stored in maps or struct fields are not followed.
- The LLM verdict label is coarse and sometimes contradicts the model's own advice;
  read its reasoning and citations, not only the label. A caller and its callee can
  appear as a pair (`ingestCandidate` and `auditFailure`).

## Extending with custom CodeQL queries

`codeql/go/lib/CallGraph.qll` defines the node and edge predicates and the
stable ids. A custom query in the same pack that imports it produces ids and
locations identical to the published graph, so its results can be joined to
`nodes.csv` by `id`.
