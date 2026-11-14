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

## Scope and known gaps

- Test files (`*_test.go`) are excluded. Generated code such as
  `internal/dbgen` is included.
- Calls through interfaces and function values are resolved only as far as
  CodeQL resolves them. Calls into the standard library or dependencies produce
  no edge.
- A call inside a function literal is attributed to the enclosing declared
  function.

## Extending with custom CodeQL queries

`codeql/go/lib/CallGraph.qll` defines the node and edge predicates and the
stable ids. A custom query in the same pack that imports it produces ids and
locations identical to the published graph, so its results can be joined to
`nodes.csv` by `id`.
