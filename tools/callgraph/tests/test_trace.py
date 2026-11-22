import unittest

from tools.callgraph import build, trace
from tools.callgraph.tests import helpers


class TraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = build.build_graph(helpers.raw_nodes_csv(), helpers.raw_edges_csv(), helpers.SHA)

    def names(self, nodes):
        return sorted(node.name for node in nodes)

    def test_line_inside_a_function_resolves_to_that_function(self):
        result = trace.trace_location(self.graph, helpers.FIXTURE_FILE, 10)

        self.assertEqual(self.names(result.nodes), ["run"])

    def test_result_lists_callers_and_callees_of_the_function(self):
        result = trace.trace_location(self.graph, helpers.FIXTURE_FILE, 14)  # inside helper

        self.assertEqual(self.names(result.nodes), ["helper"])
        self.assertEqual(sorted(edge.caller_id for edge in result.incoming),
                         [helpers.node_id("main"), helpers.node_id("run")])
        self.assertEqual([edge.callee_id for edge in result.outgoing], [helpers.node_id("leaf")])

    def test_function_boundaries_are_inclusive(self):
        for name, start, end in helpers.FIXTURE_FUNCTIONS:
            for line in (start, end):
                result = trace.trace_location(self.graph, helpers.FIXTURE_FILE, line)
                self.assertEqual(self.names(result.nodes), [name], f"{name} line {line}")

    def test_line_between_functions_matches_nothing(self):
        result = trace.trace_location(self.graph, helpers.FIXTURE_FILE, 7)

        self.assertEqual(result.nodes, ())
        self.assertEqual(result.incoming, ())
        self.assertEqual(result.outgoing, ())

    def test_file_without_a_line_returns_every_function_in_it(self):
        result = trace.trace_location(self.graph, helpers.FIXTURE_FILE)

        self.assertEqual(self.names(result.nodes), ["helper", "leaf", "main", "run"])

    def test_unknown_file_matches_nothing(self):
        result = trace.trace_location(self.graph, "nope.go", 4)

        self.assertEqual(result.nodes, ())


class ParseLocationTest(unittest.TestCase):
    def test_file_and_line_are_split(self):
        self.assertEqual(trace.parse_location("a/b.go:12"), ("a/b.go", 12))

    def test_file_alone_has_no_line(self):
        self.assertEqual(trace.parse_location("a/b.go"), ("a/b.go", None))

    def test_non_numeric_line_is_rejected(self):
        with self.assertRaises(ValueError):
            trace.parse_location("a/b.go:twelve")


if __name__ == "__main__":
    unittest.main()
