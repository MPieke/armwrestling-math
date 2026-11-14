---
linear_issue: TBD
status: proposed
---

# Contract go-route-analysis: Redundant-Route Analysis With Self-Verification

> No Linear ticket exists yet, so this file and its branch/commits carry no
> `MPI-NN` code (see `docs/repository-guidance.md`). Rename once one exists.
> Builds on `docs/contracts/go-callgraph.md` (PR #16, unmerged).

## Context
The user works on a messy, AI-generated codebase with many redundant paths
between front end and back end. Goal (1): find where many independent routes
reach the same operation, so they can be consolidated. Goal (2): once simplified,
keep it simple (a ratchet on the same metrics). PR #16 already extracts and
publishes the call graph; this plan adds the analysis that turns it into ranked,
source-linked findings, plus a self-verification step that checks the analysis
against the real source so we do not trust a graph blindly.

The function-level diagram leaves the run summary (devs cannot use it); the full
graph stays in the artifact and is queryable. Prior art check: dominators, min
vertex cut and disjoint paths are standard (igraph, graph-tool, networkx); no tool
found that reports them per terminal on a call graph for refactoring. Usefulness
is unproven until run on real messy code.

## Definitions (the contract's core)
- **Entry point**: a node in the graph with no callers, classified by CodeQL into
  `root_kind` (new `nodes.csv` column):
  `main` | `init` | `referenced` (function used as a value: handler/callback
  registration, not called directly) | `exported-uncalled` (exported, no
  references: public API or framework callback such as ServeHTTP) |
  `unreferenced` (unexported, never referenced: dead-code candidate).
  Entries = first four kinds. `unreferenced` nodes and anything reachable only from
  them are excluded from path math and counted as dead candidates.
- **Terminal**: a repo function with at least one call to a non-ignored external
  function (new `externals.csv`). Opt-out list `tools/callgraph/ignored_externals.txt`
  (fmt, errors, strings, strconv, sort, slices, maps, math, context, time, log,
  sync, ...); the summary prints what was suppressed. No sink allow-list.
- **Graph for analysis**: caller/callee pairs (call-site multiplicity kept as weight),
  restricted to scope; cycles collapsed to one node (strongly connected components),
  giving a DAG ("ignore loops"). A collapsed cycle is displayed as "cycle of N functions".
- **paths(T)**: exact count of entry-to-T paths on the DAG: one pass in topological
  order, count(T)=1, count(v)=sum of successors' counts, total = sum over entries.
  Context only; never the flag condition (it counts overlapping routes).
- **entries(T)**: entries that reach T (reverse reachability from T).
- **Chokepoint of T**: an interior function (not an entry, not T) on every route
  from every entry to T = a dominator of T from a virtual source joined to all
  entries. Found with a dominator tree.
- **K (independent routes)**: max number of routes entry-to-T sharing no interior
  function, = size of the minimum vertex cut (Menger). Entries are uncuttable;
  a direct entry-to-T call counts as one route. Computed by node-split max-flow
  (exact; greedy search can undercount).
- **Gateways when K >= 2**: the minimum vertex cut *nearest T* (run min-cut on the
  reversed split graph with T as source). The cut is not unique, so K drives
  flagging/ranking; named gateways are a representative, shown with **group
  sizes** ("A serves 3 entries, B serves 2, 1 direct").
- **Hierarchical K** (diamond case): once chokepoints c1..ck exist, K is also
  computed per segment (entries->c1, c1->c2, ..., ck->T). A funnel into c1 is
  good design and not flagged. Flag: (a) no chokepoint and K >= 2, or (b) any
  later segment with K_seg >= 2 (parallel implementations between a chokepoint
  and T). Report reads "all routes pass X, then split into 2 routes to T".
- **Flag rule**: entries(T) >= 2 and (a) or (b); thresholds are CLI flags
  (`--min-entries`, `--min-gateways`, default 2/2). Rank: K, then paths(T).
- **Edge `resolution`** (new `edges.csv` column): `static` (call target resolves
  to the declaration) or `dynamic` (interface dispatch via getACallee). Routes
  using dynamic edges are marked in findings.
- Secondary table: per external function, distinct repo packages calling it.

Known limits (documented in README and summary): reflection, function values in
maps/struct fields, goroutine/channel hand-offs, DI containers, generated code,
over-approximation from interface dispatch. K is a strong signal, not proof.

## 1. Current state (after PR #16)
```
services/importer --CodeQL--> nodes.ql, edges.ql --> raw CSV --build.py-->
  nodes.csv, edges.csv --render.py--> callgraph.dot/svg + summary.md
  summary: package diagram, package totals, function diagram, most called/calls
  out/never called, collapsible lists.  External calls are dropped. No route analysis.
```

## 2. Target state (+ = new)
```
CodeQL: nodes.ql(+root_kind) edges.ql(+resolution) +externals.ql  (lib/CallGraph.qll
        gains isReferencedAsValue, isExported, resolution predicate)
   -> raw CSV -> build.py (validates +root_kind, +externals.csv, +resolution)
   -> nodes.csv edges.csv externals.csv
   -> +analyze.py (networkx: SCC condense, paths DP, dominators, node-split max-flow,
        hierarchical K, nearest-T cut) -> findings.csv, findings.json
   -> +verify.py  mechanical checks (hard + soft) + dossier.md (source excerpts)
   -> render.py: summary = package diagram, totals, "Redundant routes" (top N with
        K, group sizes, routes with source links), dead candidates, suppressed
        externals; function diagram moves to artifact only
   -> artifacts: CSVs, findings.*, dossier.md, callgraph.svg
```
Sequence (analysis for one terminal T):
```
 load graph -> drop unreferenced -> condense SCCs -> ancestors(T) -> entries(T)
 -> paths DP -> dominator tree from virtual S -> chokepoints [c1..ck]
 -> per segment: node-split max-flow (entries/segment-start uncuttable)
 -> K_seg, flow decomposition -> routes -> nearest-T cut -> gateways + groups
 -> flag? -> findings.json (routes carry file:line per hop, resolution)
```

## 3. Commits (test-first; each red commit shows failure, green must not weaken it)
Branch `feat/go-route-analysis` from `feat/go-callgraph`; PR base `feat/go-callgraph`
(retarget to main after #16 merges). Commit format `<type>(callgraph): ...`
(no Linear code yet). Co-Authored-By trailer on all.
1. `docs`: contract file.
2. `test`: build schema (root_kind enum, externals.csv referencing known callers,
   edge resolution enum, malformed rows fail loudly) - red.
3. `feat`: build.py/schema extension.
4. `test`: CodeQL tests on new fixture `codeql/go/test/Routes/` with planted truth:
   handler registered via HandleFunc (referenced), main, unreferenced func,
   exported-uncalled method, interface dispatch (dynamic edge), closure call,
   function stored in a map (documented blind spot, expected absent), funnel,
   diamond, independent chains, external calls (pgx-like stub / net/http). - red
5. `feat`: CodeQL root_kind, externals.ql, resolution. Existing `Nodes.expected` /
   `Edges.expected` gain columns (schema extension, not weakened assertions); said
   in commit message.
6. `test`: analysis unit tests on synthetic graphs with hand-computed expected
   values: path counts (chain 1, diamond 2, ladder), cycle collapse, dead
   exclusion, funnel K=1 with chokepoint, independent chains K=n, direct entry
   calls count, entries uncuttable (single entry, two internal routes -> K=2),
   funnel-then-diamond segments, nearest-T cut choice, group sizes, thresholds,
   ignore-list suppression reported, deterministic output - red.
7. `feat`: `tools/callgraph/analyze.py` (+ pinned `tools/callgraph/requirements.txt`
   with networkx; thin adapter Graph -> DiGraph; CSVs remain the contract).
8. `test`: verify.py mechanical checks and dossier content - red.
9. `feat`: `tools/callgraph/verify.py`.
10. `test`: summary renders findings (K, groups, links, dead candidates, suppressed
    externals), function diagram absent from summary - red.
11. `feat`: render.py findings section; function diagram to artifact only.
12. `ci`: workflow installs requirements, runs analyze + verify (hard checks fail
    the build), uploads findings and dossier, lists discovered tests verbosely.
13. `docs`: README; record self-verification results in the contract.

Reuse: `tools/callgraph/build.py` (`Graph`, `load_graph`, `_validated_graph`),
`render.py` (`source_url`, `_package_labels`, `summary_markdown` helpers),
`codeql/go/lib/CallGraph.qll` (`GraphFunction`, `callEdge`, `isGraphFile`),
`tools/callgraph/tests/helpers.py`, `.github/workflows/callgraph.yml`.

## 4. Verification plan
Automated: `python3 -m unittest discover -v -s tools/callgraph/tests -t .`;
`(cd codeql && codeql test run go/test)`; `ruff check tools`; CI run on the PR
(`gh run watch`), artifacts downloaded and inspected.

### Self-verification: does the analysis match the real source? (new, required)
Two layers; results are recorded, not assumed.

**Layer A: mechanical, independent of CodeQL (`verify.py`, runs in CI).**
Hard invariants (fail the build): (M1) every edge's call line contains the callee's
name; (M2) every external call line contains the external function's name;
(M3) every node start line is a `func` declaration of that name.
Soft cross-checks (reported as "unexplained", reviewed in Layer B):
(M4) `referenced` entries: the name appears outside its declaration without a
direct call (grep); (M5) call-site census: for each flagged terminal and each
external function used, grep the source for call sites and diff against the graph
(missing = possible false negative; extra = possible false positive);
(M6) count of edges marked `dynamic` per flagged route.

**Layer B: source review (done by Claude during implementation, on demand later).**
`verify.py` writes `dossier.md` for the top 5 findings: terminal, its external
calls, each entry with its registration site, and every hop of every route as
`caller -> callee at file:line` with +-2 lines of code. Claude then opens the actual
source (not just the dossier) and checks, per finding:
1. Hop truth: does each call site really call that function (not commented out,
   not a different overload/receiver, not an unreachable branch)?
2. Entry truth: is each entry really invoked (find the registration, or confirm it
   is exported API/callback), or is it dead code mislabeled?
3. Terminal truth: does the boundary function really perform the external call?
4. Completeness: use M5 and manual grep to look for routes the graph missed
   (reflection, function values in maps/struct fields, goroutines/channels, DI,
   method values, init-time registration). Each miss is a false negative.
5. Gateway/K truth: for at least 2 findings, recompute K by hand from the source
   and compare; confirm every claimed chokepoint truly lies on all routes by
   searching for other callers of T that bypass it.
6. Dynamic edges: for each, list real implementers and say whether the route exists.
Each finding gets a verdict (confirmed / false positive + cause / missed route +
cause). Verdicts, tallies, and the failure taxonomy are appended to the contract.

**Exit criteria**: M1-M3 100%; at least 90% of reviewed hops confirmed; no
mislabeled entry or terminal left unfixed or undocumented; every discovered failure
class either gets a regression test (new fixture case) and a fix, or is added to
the documented limits. If the bar is not met, adjust the analysis and re-run;
do not declare done.

Truth sources: planted fixture (`codeql/go/test/Routes/`) has known expected
answers; the real `services/importer` has none, so Layer B is the only check there
(its findings may be few because that code is clean). The real test is the user's
messy codebase (stack still unknown; blocks extraction and the front/back join,
not this analysis step).

## 5. Next step (non-binding): are multiple routes a good idea?
Static structure cannot decide. Evidence to add later, strongest first: do routes
end differently (compare constant arguments to the terminal call: SQL text, table,
URL); same input/output types and similar step sequences; callee-set overlap and
clone similarity between routes; git change coupling; differential/runtime
behavior (same fixture through both routes, traces for unused routes); reviewed
annotations for intentional multiplicity (excluded from the phase 2 ratchet);
LLM triage over route source as a hint, never a gate. Phase 2 ratchet: per-terminal
K (and dead-candidate count) must not rise versus main.

## Open decisions (defaults chosen; change on request)
- Flag thresholds default entries>=2, K>=2.
- networkx as a pinned CI dependency instead of hand-written flow/dominator code.
- Findings capped at top 10 in the summary; full list in artifacts.
