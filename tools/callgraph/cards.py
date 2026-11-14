"""Group route analysis findings into readable redundancy cards.

A card is a pair of functions (``first``, ``second``) that each call the same
meeting point (a flagged terminal, or the end of a parallel segment) on separate
routes of the same segment. One function may also call the other, as in
``ingestCandidate`` calling ``Submit`` directly and through ``auditFailure``. One
pair can carry several meeting points, so two functions that repeat the same
pipeline show up once.

Evidence is computed from the graph only, so every statement is checkable:
which functions both call directly, which only one calls, and how similar the
two call sets are. The meeting points themselves are excluded from that
comparison, since both call them by construction.
"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

import networkx as nx

from tools.callgraph import analyze

VERY_SIMILAR = 0.6  # Jaccard similarity of the two call sets; heuristic bands.
PARTLY_SIMILAR = 0.3


@dataclass(frozen=True)
class Evidence:
    shared_callees: tuple
    shared_externals: tuple
    only_first: tuple
    only_second: tuple
    similarity: float
    band: str


@dataclass(frozen=True)
class Card:
    first: str
    second: str
    targets: tuple
    reached_from: tuple
    routes: tuple
    evidence: Evidence


def build_cards(graph, analysis, ignored_packages=()):
    calls = nx.DiGraph()
    calls.add_nodes_from(node.id for node in graph.nodes)
    calls.add_edges_from((e.caller_id, e.callee_id) for e in graph.edges)
    reach = _Reachability(calls)

    pairs = defaultdict(lambda: {"targets": set(), "routes": set()})
    for target, last_hops in _segment_last_hops(analysis, set(calls.nodes)):
        for first, second in combinations(sorted({hop for hop, _ in last_hops}), 2):
            entry = pairs[(first, second)]
            entry["targets"].add(target)
            entry["routes"] |= {route for hop, route in last_hops if hop in (first, second)}

    externals = _externals_by_caller(graph, ignored_packages)
    found = [
        Card(
            first=first,
            second=second,
            targets=tuple(sorted(data["targets"])),
            reached_from=(
                (first, reach.entries_reaching(first, analysis.entries)),
                (second, reach.entries_reaching(second, analysis.entries)),
            ),
            routes=tuple(sorted(data["routes"])),
            evidence=_evidence(calls, externals, first, second, data["targets"]),
        )
        for (first, second), data in pairs.items()
    ]
    return tuple(
        sorted(found, key=lambda c: (-len(c.targets), -c.evidence.similarity, c.first, c.second))
    )


def _segment_last_hops(analysis, node_ids):
    """For each parallel segment, its meeting point and the (last-hop function, route) pairs.

    Routes inside one segment share no interior function, so their last-hop
    functions are independent ways into the meeting point. Functions are paired
    only within a segment, never across segments.
    """
    for finding in analysis.findings:
        segments = [s for s in finding.segments if s.parallel]
        segments += [nested.segment for nested in finding.nested]
        for segment in segments:
            hops = [
                (route[-2], route)
                for route in segment.routes
                if len(route) >= 2 and route[-1] in node_ids and route[-2] in node_ids
            ]
            if hops:
                yield segment.end, hops


class _Reachability:
    def __init__(self, calls):
        self.calls = calls
        self._descendants = {}

    def _below(self, node):
        if node not in self._descendants:
            self._descendants[node] = nx.descendants(self.calls, node)
        return self._descendants[node]

    def reaches(self, source, target):
        return target in self._below(source)

    def entries_reaching(self, function_id, entries):
        return tuple(
            sorted(e for e in entries if e == function_id or self.reaches(e, function_id))
        )


def _externals_by_caller(graph, ignored_packages):
    by_caller = defaultdict(set)
    for call in graph.externals:
        if not analyze.is_ignored(call.external_package, ignored_packages):
            by_caller[call.caller_id].add(call.external_name)
    return by_caller


def _evidence(calls, externals, first, second, targets):
    def callees(function_id):
        return set(calls.successors(function_id)) - {function_id} - set(targets)

    first_callees, second_callees = callees(first), callees(second)
    first_externals, second_externals = externals[first], externals[second]
    first_all = {("callee", c) for c in first_callees} | {("external", e) for e in first_externals}
    second_all = {("callee", c) for c in second_callees} | {("external", e) for e in second_externals}
    union = first_all | second_all
    similarity = len(first_all & second_all) / len(union) if union else 0.0
    return Evidence(
        shared_callees=tuple(sorted(first_callees & second_callees)),
        shared_externals=tuple(sorted(first_externals & second_externals)),
        only_first=tuple(sorted((first_callees - second_callees) | (first_externals - second_externals))),
        only_second=tuple(sorted((second_callees - first_callees) | (second_externals - first_externals))),
        similarity=similarity,
        band=_band(similarity),
    )


def _band(similarity):
    if similarity >= VERY_SIMILAR:
        return "very similar"
    if similarity >= PARTLY_SIMILAR:
        return "partly similar"
    return "little overlap"
