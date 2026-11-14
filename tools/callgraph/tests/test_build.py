import random
import unittest

from tools.callgraph import build
from tools.callgraph.tests import helpers


def build_fixture(nodes_csv=None, edges_csv=None):
    return build.build_graph(
        nodes_csv if nodes_csv is not None else helpers.raw_nodes_csv(),
        edges_csv if edges_csv is not None else helpers.raw_edges_csv(),
        helpers.SHA,
    )


class BuildGraphTest(unittest.TestCase):
    def test_every_node_and_edge_is_stamped_with_language_and_commit(self):
        graph = build_fixture()

        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(len(graph.edges), 5)
        self.assertTrue(all(node.lang == "go" for node in graph.nodes))
        self.assertTrue(all(node.sha == helpers.SHA for node in graph.nodes))
        self.assertTrue(all(edge.sha == helpers.SHA for edge in graph.edges))

    def test_output_is_identical_for_any_input_row_order(self):
        node_rows = [
            [helpers.node_id(n), n, helpers.PACKAGE, helpers.FIXTURE_FILE, s, e]
            for n, s, e in helpers.FIXTURE_FUNCTIONS
        ]
        edge_rows = [
            [helpers.node_id(a), helpers.node_id(b), helpers.FIXTURE_FILE, line]
            for a, b, line in helpers.FIXTURE_CALLS
        ]
        baseline_graph = build_fixture()
        baseline = (build.nodes_to_csv(baseline_graph), build.edges_to_csv(baseline_graph))

        shuffler = random.Random(7)
        for _ in range(5):
            shuffler.shuffle(node_rows)
            shuffler.shuffle(edge_rows)
            graph = build_fixture(
                helpers.raw_nodes_csv(node_rows), helpers.raw_edges_csv(edge_rows)
            )
            self.assertEqual((build.nodes_to_csv(graph), build.edges_to_csv(graph)), baseline)

    def test_duplicate_call_site_rows_collapse_to_one_edge(self):
        row = [helpers.node_id("main"), helpers.node_id("run"), helpers.FIXTURE_FILE, 4]
        graph = build_fixture(edges_csv=helpers.raw_edges_csv([row, row]))

        self.assertEqual(len(graph.edges), 1)

    def test_two_calls_from_one_function_to_same_callee_stay_distinct(self):
        # Same caller and callee on different lines are different call sites.
        rows = [
            [helpers.node_id("run"), helpers.node_id("leaf"), helpers.FIXTURE_FILE, 9],
            [helpers.node_id("run"), helpers.node_id("leaf"), helpers.FIXTURE_FILE, 10],
        ]
        graph = build_fixture(edges_csv=helpers.raw_edges_csv(rows))

        self.assertEqual([edge.call_line for edge in graph.edges], [9, 10])

    def test_written_csv_has_the_documented_columns(self):
        graph = build_fixture()

        self.assertEqual(
            build.nodes_to_csv(graph).splitlines()[0],
            "id,lang,name,package,file,start_line,end_line,sha",
        )
        self.assertEqual(
            build.edges_to_csv(graph).splitlines()[0],
            "caller_id,callee_id,call_file,call_line,sha",
        )


class IncludePrefixTest(unittest.TestCase):
    """The database may contain code outside the scope being analysed."""

    NODES = [
        ["a.in1", "in1", "a", "services/importer/a.go", 1, 10],
        ["a.in2", "in2", "a", "services/importer/b.go", 1, 10],
        ["f.out", "out", "f", "codeql/go/test/main.go", 1, 10],
    ]
    EDGES = [
        ["a.in1", "a.in2", "services/importer/a.go", 3],
        ["f.out", "a.in1", "codeql/go/test/main.go", 4],
        ["a.in2", "f.out", "services/importer/b.go", 5],
    ]

    def build_with(self, prefixes):
        return build.build_graph(
            helpers.raw_nodes_csv(self.NODES),
            helpers.raw_edges_csv(self.EDGES),
            helpers.SHA,
            include_prefixes=prefixes,
        )

    def test_nodes_outside_every_prefix_are_dropped(self):
        graph = self.build_with(["services/importer/"])

        self.assertEqual([node.id for node in graph.nodes], ["a.in1", "a.in2"])

    def test_edges_touching_a_dropped_node_are_dropped_in_either_direction(self):
        graph = self.build_with(["services/importer/"])

        self.assertEqual([(e.caller_id, e.callee_id) for e in graph.edges], [("a.in1", "a.in2")])

    def test_no_prefix_keeps_everything(self):
        graph = self.build_with([])

        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(len(graph.edges), 3)

    def test_prefix_matches_whole_path_segments_only(self):
        # "services/imp" must not select "services/importer/...".
        graph = self.build_with(["services/imp"])

        self.assertEqual(graph.nodes, ())

    def test_edge_to_a_function_that_never_existed_is_still_rejected(self):
        edges = self.EDGES + [["a.in1", "ghost", "services/importer/a.go", 4]]

        with self.assertRaises(build.GraphError):
            build.build_graph(
                helpers.raw_nodes_csv(self.NODES),
                helpers.raw_edges_csv(edges),
                helpers.SHA,
                include_prefixes=["services/importer/"],
            )


class BuildRejectsInvalidGraphsTest(unittest.TestCase):
    def assert_rejected(self, message_part, nodes_csv=None, edges_csv=None):
        with self.assertRaises(build.GraphError) as context:
            build_fixture(nodes_csv, edges_csv)
        self.assertIn(message_part, str(context.exception))

    def test_duplicate_node_id_is_rejected(self):
        row = [helpers.node_id("leaf"), "leaf", helpers.PACKAGE, helpers.FIXTURE_FILE, 17, 17]
        self.assert_rejected("duplicate node id", nodes_csv=helpers.raw_nodes_csv([row, row]))

    def test_edge_to_unknown_function_is_rejected(self):
        rows = [[helpers.node_id("main"), "example.com/fixture.ghost", helpers.FIXTURE_FILE, 4]]
        self.assert_rejected("unknown callee", edges_csv=helpers.raw_edges_csv(rows))

    def test_edge_from_unknown_function_is_rejected(self):
        rows = [["example.com/fixture.ghost", helpers.node_id("run"), helpers.FIXTURE_FILE, 4]]
        self.assert_rejected("unknown caller", edges_csv=helpers.raw_edges_csv(rows))

    def test_call_site_outside_the_callers_line_range_is_rejected(self):
        # main spans lines 3-6, so a call at line 9 cannot belong to it.
        rows = [[helpers.node_id("main"), helpers.node_id("run"), helpers.FIXTURE_FILE, 9]]
        self.assert_rejected("outside caller", edges_csv=helpers.raw_edges_csv(rows))

    def test_call_site_in_a_different_file_than_the_caller_is_rejected(self):
        rows = [[helpers.node_id("main"), helpers.node_id("run"), "other.go", 4]]
        self.assert_rejected("outside caller", edges_csv=helpers.raw_edges_csv(rows))

    def test_node_whose_end_line_precedes_start_line_is_rejected(self):
        row = [helpers.node_id("leaf"), "leaf", helpers.PACKAGE, helpers.FIXTURE_FILE, 17, 16]
        self.assert_rejected(
            "end_line",
            nodes_csv=helpers.raw_nodes_csv([row]),
            edges_csv=helpers.raw_edges_csv([]),
        )

    def test_non_integer_line_number_is_rejected(self):
        row = [helpers.node_id("leaf"), "leaf", helpers.PACKAGE, helpers.FIXTURE_FILE, "x", 17]
        self.assert_rejected(
            "start_line",
            nodes_csv=helpers.raw_nodes_csv([row]),
            edges_csv=helpers.raw_edges_csv([]),
        )

    def test_missing_required_column_is_rejected(self):
        self.assert_rejected("missing column", nodes_csv="id,name\nx,y\n")


class FixtureMatchesSourceTest(unittest.TestCase):
    """Traceability must hold against real source, not only against itself."""

    @classmethod
    def setUpClass(cls):
        path = helpers.REPO_ROOT / helpers.FIXTURE_FILE
        cls.lines = path.read_text().splitlines()

    def line(self, number):
        return self.lines[number - 1]

    def test_each_function_starts_on_its_declaration_line(self):
        for name, start, _end in helpers.FIXTURE_FUNCTIONS:
            self.assertTrue(
                self.line(start).startswith(f"func {name}("),
                f"{name}: line {start} is {self.line(start)!r}",
            )

    def test_each_function_ends_on_its_closing_brace(self):
        for name, _start, end in helpers.FIXTURE_FUNCTIONS:
            self.assertTrue(self.line(end).endswith("}"), f"{name}: line {end}")

    def test_each_call_site_line_contains_the_call(self):
        for caller, callee, line in helpers.FIXTURE_CALLS:
            self.assertIn(f"{callee}()", self.line(line), f"{caller} -> {callee}")


if __name__ == "__main__":
    unittest.main()
