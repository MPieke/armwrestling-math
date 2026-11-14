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

## Extending with custom CodeQL queries

`codeql/go/lib/CallGraph.qll` defines the node and edge predicates and the
stable ids. A custom query in the same pack that imports it produces ids and
locations identical to the published graph, so its results can be joined to
`nodes.csv` by `id`.
