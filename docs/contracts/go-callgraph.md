---
linear_issue: TBD
status: proposed
---

# Contract go-callgraph: Go Call Graph With Source Traceability In CI

> No Linear ticket exists yet, so this file and its branch/commits do not carry
> an `MPI-NN` code, which `docs/repository-guidance.md` normally requires.
> Rename the file, heading, and `linear_issue` once the ticket exists.

## Scope

Extract a whole-codebase call graph for the Go module in
`services/importer/` using CodeQL, publish it from CI, and make every node and
edge traceable to an exact source location. Path counting and any other
analysis of the graph are out of scope; this change only produces and renders
the graph.

In scope: `services/importer/**` (read-only input), new files under
`codeql/`, `tools/callgraph/`, `.github/workflows/callgraph.yml`, and this
contract. No existing file is modified. Python and TypeScript extraction are
deferred; the `lang` column keeps the schema ready for them.

## Data model

Node (one per function or method declared in the repo, `nodes.csv`):
`id, lang, name, package, file, start_line, end_line, sha`

Edge (one per call site, `edges.csv`):
`caller_id, callee_id, call_file, call_line, sha`

- `file`/`call_file` are repo-relative paths; lines are 1-based.
- Only callees declared inside the extracted source root are nodes; calls to
  the standard library or dependencies produce no edge.
- A call inside a function literal is attributed to the enclosing declared
  function.
- Invariants checked by `build.py`: node ids unique; every edge endpoint is a
  node; `start_line <= end_line`; `call_file == caller.file` and
  `caller.start_line <= call_line <= caller.end_line`.

## 1. Current-State Architecture

```text
C4 container
  services/importer (Go)  --->  generic-ingestion-ci.yml (lint, test)

  No structural or call-graph analysis exists; nothing can be traced.
```

## 2. Target-State Architecture

```text
C4 component (+ = new)

 services/importer (Go)
        |
 +codeql/go/lib/CallGraph.qll    shared node/edge/id/location definitions
 +codeql/go/nodes.ql edges.ql    thin queries over the library
        |  codeql query run -> .bqrs -> bqrs decode --format=csv
        v
 +tools/callgraph/build.py   validate + stamp sha  -> nodes.csv, edges.csv
        |                \
        |                 +tools/callgraph/trace.py   file[:line] -> nodes/edges
        v
 +tools/callgraph/render.py  -> callgraph.dot -> callgraph.svg (Graphviz,
        |                       clickable GitHub blob URLs at the commit SHA)
        |                    -> summary.md (Mermaid package graph + tables)
        v
 +.github/workflows/callgraph.yml
     artifacts: nodes.csv, edges.csv, callgraph.svg
     run page:  summary.md via $GITHUB_STEP_SUMMARY
```

```text
Sequence (CI run)

 push/PR/dispatch
   -> checkout
   -> setup-go
   -> install CodeQL CLI
   -> unittest discover (tools/callgraph) and codeql test run (codeql/go)
   -> codeql database create (go, source-root services/importer)
   -> codeql query run nodes.ql, edges.ql  -> bqrs decode -> raw csv
   -> build.py -> render.py (dot, svg, summary.md)
   -> upload-artifact; append summary.md to $GITHUB_STEP_SUMMARY
```

Extension: future custom queries import `CallGraph.qll` from the same pack so
ids and locations match the graph exactly. Path counting later runs in Python
on the SCC-condensed DAG, not in QL.

## 3. Commit Breakdown

1. `docs(callgraph): add go call graph contract` - this file.
2. `test(callgraph): add call graph fixture and failing tests` - a Go fixture
   with known edges/lines under `codeql/go/test/CallGraph/`, and `unittest`
   tests under `tools/callgraph/tests/` for build, trace, and render. Expected
   failure: the modules do not exist (`ModuleNotFoundError`).
3. `feat(callgraph): add build, trace, and render tools` - makes commit 2's
   tests pass without changing assertions.
4. `test(callgraph): add CodeQL query tests` - `codeql test run` test over the
   fixture. Expected failure: the queries do not exist.
5. `feat(callgraph): add CodeQL go call graph queries` - `qlpack.yml`,
   `CallGraph.qll`, `nodes.ql`, `edges.ql`; commit 4's test passes.
6. `ci(callgraph): add call graph workflow` - runs both test layers verbosely,
   the real extraction, uploads artifacts, writes the run summary.
7. `docs(callgraph): document usage and schema` - README for `tools/callgraph`.

Each commit is reviewable alone: tests precede the code that satisfies them,
and the workflow lands only after both test layers pass locally.

## 4. Verification Plan

- Unit: `python3 -m unittest discover -v -s tools/callgraph/tests -t .`
- Query: `codeql test run codeql/go/test`
- Real extraction (local):
  `codeql database create /tmp/cg-db --language=go --source-root=services/importer`,
  `codeql query run --database=/tmp/cg-db --output=/tmp/nodes.bqrs codeql/go/nodes.ql`,
  `codeql bqrs decode --format=csv /tmp/nodes.bqrs`, same for `edges.ql`, then
  `python3 -m tools.callgraph.build ...`.
- Traceability spot check on real data: sample 5 edges and confirm
  `call_file:call_line` contains the call to the callee; sample 5 nodes and
  confirm `start_line` is the `func` declaration; run
  `python3 -m tools.callgraph.trace <file>:<line>` and confirm the result.
- CI: open the PR, then `gh run watch`; confirm the run page shows the Mermaid
  package graph and counts, and that the artifacts contain non-empty CSVs and
  an SVG whose nodes link to the right GitHub lines.

Known gaps to report, not hide: calls through interfaces and function values
are resolved only as far as CodeQL resolves them; generated code (for example
`internal/dbgen`) is included unless excluded.
