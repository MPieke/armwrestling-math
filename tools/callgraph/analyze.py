"""Find terminals reached by many independent routes in the call graph.

Definitions (see docs/contracts/go-route-analysis.md):

* An *entry* is a function entered from outside the graph (``root_kind`` main,
  init, referenced, or exported-uncalled). Functions only reachable from
  ``unreferenced`` code are dead and excluded.
* A *terminal* is a function that makes a call to a non-ignored external
  function.
* ``K`` is the maximum number of routes from the entries to a terminal that
  share no interior function (= the minimum vertex cut, found by max-flow on a
  node-split graph). Entries are uncuttable; a direct entry-to-terminal call is
  one route.
* A *chokepoint* is an interior function on every route (a dominator). Between
  consecutive chokepoints K is computed again, so a funnel followed by a diamond
  is reported as such.
* *Gateways* are the minimum cut nearest the terminal: the last functions where
  independent routes are still separate.

Cycles are collapsed first, so loops never add routes.
"""

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from tools.callgraph import build

ENTRY_KINDS = ("main", "init", "referenced", "exported-uncalled")
VIRTUAL_SOURCE = "<entries>"
DEFAULT_IGNORE_FILE = Path(__file__).with_name("ignored_externals.txt")


@dataclass(frozen=True)
class Gateway:
    """A function where independent routes are last separate; None means a direct call."""

    function_id: object
    entries: int


@dataclass(frozen=True)
class Segment:
    """Independent routes between two boundaries (start None = the entries)."""

    start: object
    end: str
    k: int
    gateways: tuple
    routes: tuple
    parallel: bool


@dataclass(frozen=True)
class TerminalReport:
    terminal_id: str
    entries: tuple
    paths: int
    chokepoints: tuple
    k: int
    segments: tuple
    flagged: bool
    externals: tuple

    @property
    def score(self):
        return max((s.k for s in self.segments if s.parallel), default=self.k)


@dataclass(frozen=True)
class ExternalUsage:
    name: str
    package: str
    package_count: int
    callers: tuple


@dataclass(frozen=True)
class Analysis:
    entries: tuple
    dead: tuple
    suppressed: dict
    terminals: dict
    findings: tuple
    external_usage: tuple


def parse_ignore_file(text):
    packages = []
    for line in text.splitlines():
        package = line.split("#", 1)[0].strip()
        if package:
            packages.append(package)
    return tuple(packages)


def analyze(graph, ignored_packages=(), min_entries=2, min_gateways=2):
    nodes = {node.id: node for node in graph.nodes}
    entry_ids = sorted(node.id for node in graph.nodes if node.root_kind in ENTRY_KINDS)
    calls = nx.DiGraph()
    calls.add_nodes_from(sorted(nodes))
    calls.add_edges_from(sorted({(e.caller_id, e.callee_id) for e in graph.edges}))
    alive = set(entry_ids)
    for entry in entry_ids:
        alive |= nx.descendants(calls, entry)
    dead = tuple(sorted(set(nodes) - alive))

    externals_by_caller, suppressed = _split_externals(graph, alive, ignored_packages)
    dag, label_of = _condense(calls.subgraph(alive))
    entry_labels = {label_of[e] for e in entry_ids}
    context = _Context(dag, entry_labels, label_of, entry_ids, min_entries, min_gateways)

    terminals = {}
    for terminal_id in sorted(externals_by_caller):
        names = tuple(sorted({call.external_name for call in externals_by_caller[terminal_id]}))
        terminals[terminal_id] = context.report(terminal_id, names)
    findings = tuple(
        sorted(
            (report for report in terminals.values() if report.flagged),
            key=lambda r: (-r.score, -r.paths, r.terminal_id),
        )
    )
    usage = _external_usage(graph, nodes, ignored_packages)
    return Analysis(tuple(entry_ids), dead, suppressed, terminals, findings, usage)


def _is_ignored(package, ignored_packages):
    return any(package == ig or package.startswith(ig + "/") for ig in ignored_packages)


def _split_externals(graph, alive, ignored_packages):
    kept = defaultdict(list)
    suppressed = Counter()
    for call in graph.externals:
        if _is_ignored(call.external_package, ignored_packages):
            suppressed[call.external_package] += 1
        elif call.caller_id in alive:
            kept[call.caller_id].append(call)
    return kept, dict(sorted(suppressed.items()))


def _external_usage(graph, nodes, ignored_packages):
    callers = defaultdict(set)
    packages = {}
    for call in graph.externals:
        if _is_ignored(call.external_package, ignored_packages):
            continue
        callers[call.external_name].add(call.caller_id)
        packages[call.external_name] = call.external_package
    usage = [
        ExternalUsage(
            name=name,
            package=packages[name],
            package_count=len({nodes[c].package for c in ids}),
            callers=tuple(sorted(ids)),
        )
        for name, ids in callers.items()
    ]
    return tuple(sorted(usage, key=lambda u: (-u.package_count, u.name)))


def _condense(subgraph):
    """Collapse strongly connected components; a component is labelled "a+b+c"."""
    label_of = {}
    for members in nx.strongly_connected_components(subgraph):
        label = "+".join(sorted(members))
        for member in members:
            label_of[member] = label
    dag = nx.DiGraph()
    dag.add_nodes_from(sorted(set(label_of.values())))
    dag.add_edges_from(
        sorted(
            {(label_of[a], label_of[b]) for a, b in subgraph.edges if label_of[a] != label_of[b]}
        )
    )
    return dag, label_of


class _Context:
    def __init__(self, dag, entry_labels, label_of, entry_ids, min_entries, min_gateways):
        self.dag = dag
        self.entry_labels = entry_labels
        self.label_of = label_of
        self.entry_ids = entry_ids
        self.min_entries = min_entries
        self.min_gateways = min_gateways

    def report(self, terminal_id, externals):
        target = self.label_of[terminal_id]
        upstream = nx.ancestors(self.dag, target) | {target}
        sub = self.dag.subgraph(upstream)
        entries = tuple(e for e in self.entry_ids if self.label_of[e] in upstream)
        chokepoints = self._chokepoints(sub, target)
        boundaries = [None, *chokepoints, target]
        segments = []
        for index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
            segments.append(self._segment(sub, start, end, index, bool(chokepoints)))
        k = segments[0].k if not chokepoints else self._segment(sub, None, target, 0, False).k
        flagged = len(entries) >= self.min_entries and any(s.parallel for s in segments)
        return TerminalReport(
            terminal_id=terminal_id,
            entries=entries,
            paths=self._paths(sub, target),
            chokepoints=tuple(chokepoints),
            k=k,
            segments=tuple(segments),
            flagged=flagged,
            externals=externals,
        )

    def _paths(self, sub, target):
        count = {}
        for node in reversed(list(nx.topological_sort(sub))):
            if node == target:
                count[node] = 1
            else:
                count[node] = sum(count[succ] for succ in sub.successors(node))
        return sum(count[label] for label in self.entry_labels if label in count)

    def _chokepoints(self, sub, target):
        rooted = nx.DiGraph(sub)
        sources = sorted(label for label in self.entry_labels if label in sub and label != target)
        rooted.add_edges_from((VIRTUAL_SOURCE, label) for label in sources)
        if not sources:
            return []
        dominators = nx.immediate_dominators(rooted, VIRTUAL_SOURCE)
        chain, node = [], dominators[target]
        while node != VIRTUAL_SOURCE:
            if node not in self.entry_labels:
                chain.append(node)
            node = dominators[node]
        return chain[::-1]

    def _segment(self, sub, start, end, index, has_chokepoints):
        network, source, sink = self._network(sub, start, end)
        if source is None:
            return Segment(start, end, 0, (), (), False)
        value, flow = nx.maximum_flow(network, source, sink)
        routes = _decompose(flow, source, sink)
        gateways = self._gateways(network, flow, sink)
        parallel = value >= self.min_gateways and (index >= 1 or not has_chokepoints)
        return Segment(start, end, value, gateways, tuple(routes), parallel)

    def _network(self, sub, start, end):
        """Node-split flow network for routes from ``start`` (None = entries) to ``end``."""
        inside = nx.ancestors(sub, end) | {end}
        if start is not None:
            inside &= nx.descendants(sub, start) | {start}
        entries = sorted(label for label in self.entry_labels if label in inside and label != end)
        if start is None and not entries:
            return None, None, None
        uncuttable = set(entries) | {end} | ({start} if start is not None else set())
        network = nx.DiGraph()
        for node in sorted(inside):
            if node == end or node == start:
                continue
            network.add_edge((node, "in"), (node, "out"), **_capacity(node in uncuttable))
        for tail, head in sorted(sub.subgraph(inside).edges):
            if head == start:
                continue
            both_fixed = tail in uncuttable and head in uncuttable
            network.add_edge((tail, "out"), (head, "in"), **({"capacity": 1} if both_fixed else {}))
        if start is None:
            for entry in entries:
                network.add_edge(VIRTUAL_SOURCE, (entry, "in"))
            return network, VIRTUAL_SOURCE, (end, "in")
        return network, (start, "out"), (end, "in")

    def _gateways(self, network, flow, sink):
        """The saturated cut nearest the sink: edges leaving the set that cannot reach it."""
        can_reach_sink = _can_reach_in_residual(network, flow, sink)
        gateways = []
        for tail, head, data in network.edges(data=True):
            if tail in can_reach_sink or head not in can_reach_sink:
                continue
            if flow[tail][head] < data.get("capacity", float("inf")):
                continue
            if tail[1] == "in" and head[1] == "out" and tail[0] == head[0]:
                gateways.append(Gateway(tail[0], self._entries_reaching(tail[0])))
            else:
                gateways.append(Gateway(None, self._entries_reaching(tail[0])))
        return tuple(sorted(gateways, key=lambda g: (g.function_id is None, g.function_id or "")))

    def _entries_reaching(self, label):
        upstream = nx.ancestors(self.dag, label) | {label}
        return sum(1 for entry in self.entry_ids if self.label_of[entry] in upstream)


def _capacity(fixed):
    return {} if fixed else {"capacity": 1}


def _can_reach_in_residual(network, flow, sink):
    reached, frontier = {sink}, [sink]
    while frontier:
        node = frontier.pop()
        for tail in network.predecessors(node):
            capacity = network[tail][node].get("capacity", float("inf"))
            if tail not in reached and capacity - flow[tail][node] > 0:
                reached.add(tail)
                frontier.append(tail)
        for head in network.successors(node):
            if head not in reached and flow[node][head] > 0:
                reached.add(head)
                frontier.append(head)
    return reached


def _decompose(flow, source, sink):
    """Split a flow into unit routes, returned as label tuples."""
    remaining = {u: {v: f for v, f in targets.items() if f > 0} for u, targets in flow.items()}
    routes = []
    while any(remaining.get(source, {}).values()):
        node, path = source, [source]
        while node != sink:
            following = sorted(v for v, f in remaining[node].items() if f > 0)
            nxt = following[0]
            remaining[node][nxt] -= 1
            path.append(nxt)
            node = nxt
        labels = []
        for step in path:
            if step == VIRTUAL_SOURCE:
                continue
            if not labels or labels[-1] != step[0]:
                labels.append(step[0])
        routes.append(tuple(labels))
    return sorted(routes)


def findings_to_csv(analysis):
    rows = ["terminal_id,entries,paths,k,chokepoints,flagged"]
    ordered = sorted(
        analysis.terminals.values(),
        key=lambda r: (not r.flagged, -r.score if r.flagged else 0, -r.paths, r.terminal_id),
    )
    for report in ordered:
        rows.append(
            f"{report.terminal_id},{len(report.entries)},{report.paths},{report.k},"
            f"{';'.join(report.chokepoints)},{str(report.flagged).lower()}"
        )
    return "\n".join(rows) + "\n"


def findings_to_json(analysis):
    def segment(s):
        return {
            "start": s.start,
            "end": s.end,
            "k": s.k,
            "parallel": s.parallel,
            "gateways": [{"function_id": g.function_id, "entries": g.entries} for g in s.gateways],
            "routes": [list(route) for route in s.routes],
        }

    document = {
        "entries": list(analysis.entries),
        "dead": list(analysis.dead),
        "suppressed": analysis.suppressed,
        "terminals_total": len(analysis.terminals),
        "findings": [
            {
                "terminal_id": r.terminal_id,
                "entries": list(r.entries),
                "paths": r.paths,
                "k": r.k,
                "score": r.score,
                "chokepoints": list(r.chokepoints),
                "externals": list(r.externals),
                "segments": [segment(s) for s in r.segments],
            }
            for r in analysis.findings
        ],
        "external_usage": [
            {"name": u.name, "package": u.package, "packages": u.package_count,
             "callers": list(u.callers)}
            for u in analysis.external_usage
        ],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find terminals reached by many independent routes.")
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument("--ignore-file", type=Path, default=DEFAULT_IGNORE_FILE)
    parser.add_argument("--min-entries", type=int, default=2)
    parser.add_argument("--min-gateways", type=int, default=2)
    args = parser.parse_args(argv)

    externals = args.graph_dir / "externals.csv"
    graph = build.load_graph(
        (args.graph_dir / "nodes.csv").read_text(),
        (args.graph_dir / "edges.csv").read_text(),
        externals.read_text() if externals.exists() else None,
    )
    analysis = analyze(
        graph,
        ignored_packages=parse_ignore_file(args.ignore_file.read_text()),
        min_entries=args.min_entries,
        min_gateways=args.min_gateways,
    )
    (args.graph_dir / "findings.csv").write_text(findings_to_csv(analysis))
    (args.graph_dir / "findings.json").write_text(findings_to_json(analysis))
    print(
        f"{len(analysis.terminals)} terminals, {len(analysis.findings)} flagged, "
        f"{len(analysis.dead)} dead candidates -> {args.graph_dir}"
    )


if __name__ == "__main__":
    main()
