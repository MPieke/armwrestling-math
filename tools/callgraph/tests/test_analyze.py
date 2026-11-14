import json
import random
import unittest

from tools.callgraph import analyze, build
from tools.callgraph.tests import helpers


def make_graph(edges, entries=(), dead=(), externals=(), packages=None, extra_nodes=()):
    """Build a synthetic graph. Node ids are plain names; every node has its own file.

    ``entries`` get root_kind "referenced", ``dead`` get "unreferenced", and
    ``externals`` is a list of (caller, "pkg.Name") pairs.
    """
    names = []
    for source, target in edges:
        names += [source, target]
    names += list(entries) + list(dead) + [caller for caller, _ in externals] + list(extra_nodes)
    names = sorted(set(names))
    packages = packages or {}
    nodes = tuple(
        build.Node(
            id=name, lang="go", name=name, package=packages.get(name, "p"),
            file=f"{name}.go", start_line=1, end_line=100,
            root_kind="referenced" if name in entries else "unreferenced" if name in dead else "",
            sha=helpers.SHA,
        )
        for name in names
    )
    edge_rows = tuple(
        build.Edge(a, b, f"{a}.go", 5, "static", helpers.SHA) for a, b in edges
    )
    external_rows = tuple(
        build.External(caller, name, name.rsplit(".", 1)[0], f"{caller}.go", 7, helpers.SHA)
        for caller, name in externals
    )
    return build.Graph(nodes=nodes, edges=edge_rows, externals=external_rows)


def run(edges, entries, **options):
    """Analyse a graph whose terminal is "t" (it calls os.WriteFile)."""
    graph_options = {k: options.pop(k) for k in ("dead", "packages", "extra_nodes") if k in options}
    externals = options.pop("externals", [("t", "os.WriteFile")])
    graph = make_graph(edges, entries=entries, externals=externals, **graph_options)
    return analyze.analyze(graph, **options)


def gateway_summary(segment):
    pairs = [(gateway.function_id, gateway.entries) for gateway in segment.gateways]
    return sorted(pairs, key=lambda pair: (pair[0] is None, pair[0] or ""))


class PathCountTest(unittest.TestCase):
    def paths(self, edges, entries):
        return run(edges, entries).terminals["t"].paths

    def test_a_chain_has_one_path(self):
        self.assertEqual(self.paths([("e", "a"), ("a", "t")], ["e"]), 1)

    def test_a_diamond_has_two_paths(self):
        edges = [("e", "a"), ("a", "b"), ("a", "c"), ("b", "t"), ("c", "t")]

        self.assertEqual(self.paths(edges, ["e"]), 2)

    def test_two_chained_diamonds_have_four_paths(self):
        edges = [
            ("e", "a"), ("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"),
            ("d", "f"), ("d", "g"), ("f", "t"), ("g", "t"),
        ]

        self.assertEqual(self.paths(edges, ["e"]), 4)

    def test_paths_from_several_entries_add_up(self):
        self.assertEqual(self.paths([("h1", "g"), ("h2", "g"), ("g", "t")], ["h1", "h2"]), 2)

    def test_loops_are_ignored_and_the_cycle_is_one_chokepoint(self):
        edges = [("e", "x"), ("x", "y"), ("y", "x"), ("y", "t")]

        report = run(edges, ["e"]).terminals["t"]

        self.assertEqual(report.paths, 1)
        self.assertEqual(report.chokepoints, ("x+y",))


class EntriesAndDeadCodeTest(unittest.TestCase):
    def test_every_documented_entry_kind_counts_as_an_entry(self):
        for kind in ("main", "init", "referenced", "exported-uncalled"):
            graph = make_graph([("e", "t")], externals=[("t", "os.Open")])
            nodes = tuple(
                n if n.id != "e" else build.Node(**{**n.__dict__, "root_kind": kind})
                for n in graph.nodes
            )
            analysis = analyze.analyze(build.Graph(nodes, graph.edges, graph.externals))

            self.assertEqual(analysis.terminals["t"].entries, ("e",), kind)

    def test_unreferenced_functions_are_not_entries_and_are_reported_as_dead(self):
        edges = [("h", "t"), ("u", "t"), ("u", "d")]

        analysis = run(edges, ["h"], dead=["u"])

        self.assertEqual(analysis.terminals["t"].entries, ("h",))
        self.assertEqual(analysis.terminals["t"].paths, 1)
        self.assertEqual(analysis.dead, ("d", "u"))

    def test_functions_no_entry_can_reach_are_dead(self):
        analysis = run([("h", "t")], ["h"], extra_nodes=["orphan"])

        self.assertEqual(analysis.dead, ("orphan",))

    def test_entries_are_listed_sorted(self):
        analysis = run([("h2", "t"), ("h1", "t")], ["h1", "h2"])

        self.assertEqual(analysis.entries, ("h1", "h2"))


class TerminalTest(unittest.TestCase):
    def test_only_functions_with_a_non_ignored_external_call_are_terminals(self):
        graph = make_graph(
            [("e", "t"), ("e", "quiet")],
            entries=["e"],
            externals=[("t", "os.Open"), ("quiet", "fmt.Println")],
        )

        analysis = analyze.analyze(graph, ignored_packages=("fmt",))

        self.assertEqual(sorted(analysis.terminals), ["t"])

    def test_suppressed_external_calls_are_counted_by_package(self):
        graph = make_graph(
            [("e", "a")], entries=["e"],
            externals=[("a", "fmt.Println"), ("a", "fmt.Sprintf"), ("a", "os.Open")],
        )

        analysis = analyze.analyze(graph, ignored_packages=("fmt",))

        self.assertEqual(analysis.suppressed, {"fmt": 2})

    def test_ignoring_a_package_also_ignores_its_subpackages_but_not_lookalikes(self):
        graph = make_graph(
            [("e", "a")], entries=["e"],
            externals=[("a", "log/slog.Info"), ("a", "logrus.Info")],
        )

        analysis = analyze.analyze(graph, ignored_packages=("log",))

        self.assertEqual(analysis.suppressed, {"log/slog": 1})
        self.assertEqual(analysis.terminals["a"].externals, ("logrus.Info",))

    def test_terminal_report_lists_its_external_functions(self):
        analysis = run([("e", "t")], ["e"], externals=[("t", "os.Open"), ("t", "os.WriteFile")])

        self.assertEqual(analysis.terminals["t"].externals, ("os.Open", "os.WriteFile"))

    def test_external_usage_counts_distinct_calling_packages(self):
        graph = make_graph(
            [("e", "a"), ("e", "b")], entries=["e"],
            externals=[("a", "os.Open"), ("b", "os.Open"), ("b", "os.Remove")],
            packages={"a": "p/one", "b": "p/two"},
        )

        usage = analyze.analyze(graph).external_usage

        self.assertEqual(
            [(u.name, u.package_count) for u in usage], [("os.Open", 2), ("os.Remove", 1)]
        )

    def test_ignore_file_skips_blank_lines_and_comments(self):
        text = "# noise\nfmt\n\n  errors  \nlog # structured logging\n"

        self.assertEqual(analyze.parse_ignore_file(text), ("fmt", "errors", "log"))


class IndependentRoutesTest(unittest.TestCase):
    def test_a_funnel_through_one_function_is_not_flagged(self):
        report = run([("h1", "g"), ("h2", "g"), ("g", "t")], ["h1", "h2"]).terminals["t"]

        self.assertEqual(report.chokepoints, ("g",))
        self.assertEqual(report.k, 1)
        self.assertFalse(report.flagged)
        # The entries merge at g: two direct routes, which is what a funnel looks like.
        self.assertEqual(report.segments[0].k, 2)

    def test_independent_chains_are_flagged_with_k_equal_to_their_number(self):
        edges = [("e1", "s1"), ("s1", "t"), ("e2", "s2"), ("s2", "t")]

        report = run(edges, ["e1", "e2"]).terminals["t"]

        self.assertEqual(report.chokepoints, ())
        self.assertEqual(report.k, 2)
        self.assertTrue(report.flagged)
        self.assertEqual(gateway_summary(report.segments[0]), [("s1", 1), ("s2", 1)])

    def test_gateways_are_the_cut_nearest_the_terminal(self):
        edges = [("e1", "a1"), ("a1", "a2"), ("a2", "t"), ("e2", "b1"), ("b1", "b2"), ("b2", "t")]

        report = run(edges, ["e1", "e2"]).terminals["t"]

        self.assertEqual(gateway_summary(report.segments[0]), [("a2", 1), ("b2", 1)])

    def test_mixed_groups_report_how_many_entries_each_gateway_serves(self):
        edges = [
            ("e1", "A"), ("e2", "A"), ("e3", "A"), ("A", "t"),
            ("e4", "B"), ("e5", "B"), ("B", "t"),
            ("e6", "t"),
        ]

        report = run(edges, ["e1", "e2", "e3", "e4", "e5", "e6"]).terminals["t"]

        self.assertEqual(report.k, 3)
        self.assertEqual(gateway_summary(report.segments[0]), [("A", 3), ("B", 2), (None, 1)])

    def test_entries_calling_the_terminal_directly_are_independent_routes(self):
        report = run([("e1", "t"), ("e2", "t")], ["e1", "e2"]).terminals["t"]

        self.assertEqual(report.k, 2)
        self.assertEqual(gateway_summary(report.segments[0]), [(None, 1), (None, 1)])
        self.assertTrue(report.flagged)

    def test_one_entry_with_two_internal_routes_has_k_two_but_needs_min_entries_one(self):
        edges = [("e", "a"), ("e", "b"), ("a", "t"), ("b", "t")]

        default = run(edges, ["e"]).terminals["t"]
        relaxed = run(edges, ["e"], min_entries=1).terminals["t"]

        self.assertEqual(default.k, 2)
        self.assertFalse(default.flagged)
        self.assertTrue(relaxed.flagged)

    def test_a_funnel_followed_by_a_diamond_is_flagged_on_the_later_segment(self):
        edges = [("e1", "x"), ("e2", "x"), ("x", "a"), ("x", "b"), ("a", "t"), ("b", "t")]

        report = run(edges, ["e1", "e2"]).terminals["t"]

        self.assertEqual(report.chokepoints, ("x",))
        self.assertEqual(report.k, 1)
        self.assertTrue(report.flagged)
        first, second = report.segments
        self.assertEqual((first.start, first.end, first.k), (None, "x", 2))
        self.assertEqual((second.start, second.end, second.k), ("x", "t", 2))
        self.assertEqual(gateway_summary(second), [("a", 2), ("b", 2)])

    def test_the_gateway_threshold_is_configurable(self):
        edges = [("e1", "s1"), ("s1", "t"), ("e2", "s2"), ("s2", "t")]

        report = run(edges, ["e1", "e2"], min_gateways=3).terminals["t"]

        self.assertFalse(report.flagged)

    def test_findings_are_ranked_by_independent_routes_then_paths(self):
        edges = [
            ("e1", "a1"), ("a1", "t3"), ("e2", "a2"), ("a2", "t3"), ("e3", "t3"),
            ("e1", "b1"), ("b1", "t2"), ("e2", "b2"), ("b2", "t2"),
        ]
        graph = make_graph(
            edges, entries=["e1", "e2", "e3"], externals=[("t2", "os.Open"), ("t3", "os.Open")]
        )

        findings = analyze.analyze(graph).findings

        self.assertEqual([f.terminal_id for f in findings], ["t3", "t2"])

    def test_every_reported_route_is_a_real_path_and_routes_share_no_interior_function(self):
        cases = [
            ([("e1", "s1"), ("s1", "t"), ("e2", "s2"), ("s2", "t")], ["e1", "e2"]),
            ([("e1", "x"), ("e2", "x"), ("x", "a"), ("x", "b"), ("a", "t"), ("b", "t")], ["e1", "e2"]),
            ([("e1", "A"), ("e2", "A"), ("A", "t"), ("e3", "B"), ("B", "t"), ("e4", "t")],
             ["e1", "e2", "e3", "e4"]),
        ]
        for edges, entries in cases:
            analysis = run(edges, entries)
            edge_set = set(edges)
            for report in analysis.findings:
                for segment in report.segments:
                    interiors = []
                    for route in segment.routes:
                        self.assertEqual(route[-1], segment.end)
                        self.assertTrue(segment.start is None and route[0] in entries
                                        or route[0] == segment.start)
                        for a, b in zip(route, route[1:]):
                            self.assertIn((a, b), edge_set)
                        interiors.append(set(route[1:-1]))
                    for i, left in enumerate(interiors):
                        for right in interiors[i + 1:]:
                            self.assertFalse(left & right)
                    self.assertEqual(len(segment.routes), segment.k)

    def test_results_do_not_depend_on_input_order(self):
        edges = [
            ("e1", "x"), ("e2", "x"), ("x", "a"), ("x", "b"), ("a", "t"), ("b", "t"),
            ("e3", "s3"), ("s3", "t"),
        ]
        baseline = analyze.findings_to_json(run(edges, ["e1", "e2", "e3"]))

        shuffler = random.Random(11)
        for _ in range(5):
            shuffled = list(edges)
            shuffler.shuffle(shuffled)
            self.assertEqual(analyze.findings_to_json(run(shuffled, ["e3", "e2", "e1"])), baseline)


class NestedRoutesTest(unittest.TestCase):
    """K counts independent routes globally; a split under one entry's merge point must still show."""

    MERGE_THEN_SPLIT = [
        ("e1", "run"), ("run", "resolve"), ("run", "submit"), ("resolve", "t"), ("submit", "t"),
        ("e2", "annotate"), ("annotate", "t"),
    ]

    def test_a_split_below_a_merge_point_is_reported_for_that_entry(self):
        report = run(self.MERGE_THEN_SPLIT, ["e1", "e2"]).terminals["t"]

        self.assertEqual(report.k, 2)  # global K is unchanged: gateways are annotate and run
        self.assertEqual([n.entry for n in report.nested], ["e1"])
        segment = report.nested[0].segment
        self.assertEqual((segment.start, segment.end, segment.k), ("run", "t", 2))
        self.assertEqual(gateway_summary(segment), [("resolve", 1), ("submit", 1)])

    def test_entries_with_a_single_route_have_no_nested_findings(self):
        edges = [("e1", "s1"), ("s1", "t"), ("e2", "s2"), ("s2", "t")]

        report = run(edges, ["e1", "e2"]).terminals["t"]

        self.assertEqual(report.nested, ())

    def test_a_terminal_with_one_entry_has_no_nested_findings_at_the_default_threshold(self):
        edges = [("e", "a"), ("e", "b"), ("a", "t"), ("b", "t")]

        report = run(edges, ["e"]).terminals["t"]

        self.assertEqual(report.nested, ())

    def test_a_split_before_a_shared_chokepoint_flags_the_terminal_through_nesting(self):
        # Globally everything funnels through c, so the global rule alone would not flag t.
        edges = [("e1", "a"), ("e1", "b"), ("a", "c"), ("b", "c"), ("e2", "c"), ("c", "t")]

        report = run(edges, ["e1", "e2"]).terminals["t"]

        self.assertEqual(report.chokepoints, ("c",))
        self.assertTrue(report.flagged)
        self.assertEqual([n.entry for n in report.nested], ["e1"])
        segment = report.nested[0].segment
        self.assertEqual((segment.start, segment.end, segment.k), (None, "c", 2))

    def test_nested_routes_count_towards_ranking(self):
        edges = self.MERGE_THEN_SPLIT + [
            ("e1", "o"), ("o", "u"), ("e2", "p"), ("p", "u"),
        ]
        graph = make_graph(
            edges, entries=["e1", "e2"], externals=[("t", "os.Open"), ("u", "os.Open")]
        )

        findings = analyze.analyze(graph).findings

        self.assertEqual([f.terminal_id for f in findings], ["t", "u"])
        self.assertEqual(findings[0].score, 2)

    def test_nested_routes_are_real_disjoint_paths_from_the_entry(self):
        report = run(self.MERGE_THEN_SPLIT, ["e1", "e2"]).terminals["t"]

        edge_set = set(self.MERGE_THEN_SPLIT)
        segment = report.nested[0].segment
        for route in segment.routes:
            self.assertEqual((route[0], route[-1]), ("run", "t"))
            for a, b in zip(route, route[1:]):
                self.assertIn((a, b), edge_set)
        self.assertEqual(len(segment.routes), 2)
        self.assertFalse(set(segment.routes[0][1:-1]) & set(segment.routes[1][1:-1]))

    def test_nested_findings_are_in_the_json_output(self):
        document = json.loads(analyze.findings_to_json(run(self.MERGE_THEN_SPLIT, ["e1", "e2"])))

        nested = document["findings"][0]["nested"]
        self.assertEqual([n["entry"] for n in nested], ["e1"])
        self.assertEqual(nested[0]["segment"]["k"], 2)


class FindingsOutputTest(unittest.TestCase):
    def analysis(self):
        edges = [("e1", "s1"), ("s1", "t"), ("e2", "s2"), ("s2", "t")]
        return run(edges, ["e1", "e2"])

    def test_csv_has_one_row_per_terminal_with_the_documented_columns(self):
        rows = analyze.findings_to_csv(self.analysis()).splitlines()

        self.assertEqual(rows[0], "terminal_id,entries,paths,k,chokepoints,flagged")
        self.assertEqual(rows[1], "t,2,2,2,,true")

    def test_json_carries_routes_with_every_hop(self):
        document = json.loads(analyze.findings_to_json(self.analysis()))

        segment = document["findings"][0]["segments"][0]
        self.assertEqual(sorted(tuple(route) for route in segment["routes"]),
                         [("e1", "s1", "t"), ("e2", "s2", "t")])
        self.assertEqual(document["dead"], [])


if __name__ == "__main__":
    unittest.main()
