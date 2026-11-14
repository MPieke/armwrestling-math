import tempfile
import unittest
from pathlib import Path

from tools.callgraph import analyze, build, verify
from tools.callgraph.tests import helpers

SOURCE = """package main

func handler() { serviceA() }

func handler2() { serviceB() }

func serviceA() { store() }

func serviceB() { store() }

func store() { _ = os.Open("x") }

func main() {
	http.HandleFunc("/a", handler)
	http.HandleFunc("/b", handler2)
}
"""
FILE = "a.go"
REPO_URL = "https://github.com/o/r"


def node(name, start, end, kind=""):
    return build.Node(name, "go", name, "p", FILE, start, end, kind, helpers.SHA)


def edge(caller, callee, line, resolution="static"):
    return build.Edge(caller, callee, FILE, line, resolution, helpers.SHA)


def external(caller, name, line):
    return build.External(caller, name, name.rsplit(".", 1)[0], FILE, line, helpers.SHA)


def make_graph(**overrides):
    nodes = overrides.get("nodes") or (
        node("handler", 3, 3, "referenced"),
        node("handler2", 5, 5, "referenced"),
        node("main", 13, 16, "main"),
        node("serviceA", 7, 7),
        node("serviceB", 9, 9),
        node("store", 11, 11),
    )
    edges = overrides.get("edges") or (
        edge("handler", "serviceA", 3),
        edge("handler2", "serviceB", 5),
        edge("serviceA", "store", 7),
        edge("serviceB", "store", 9),
    )
    externals = overrides.get("externals") or (
        external("main", "net/http.HandleFunc", 14),
        external("main", "net/http.HandleFunc", 15),
        external("store", "os.Open", 11),
    )
    return build.Graph(tuple(nodes), tuple(edges), tuple(externals))


class VerifyTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / FILE).write_text(SOURCE)

    def check(self, graph, source=None):
        if source is not None:
            (self.root / FILE).write_text(source)
        return verify.mechanical_checks(graph, self.root, analyze.analyze(graph))


class HardChecksTest(VerifyTestCase):
    def test_a_graph_that_matches_the_source_has_no_failures_and_counts_every_check(self):
        report = self.check(make_graph())

        self.assertEqual(report.hard_failures, [])
        self.assertEqual(report.checked, {"M1": 4, "M2": 3, "M3": 6})

    def test_edge_whose_call_line_lacks_the_callee_name_fails_m1(self):
        graph = make_graph(edges=(edge("handler", "serviceB", 3),))  # line 3 calls serviceA

        report = self.check(graph)

        self.assertEqual([(f.check, f.location) for f in report.hard_failures], [("M1", "a.go:3")])

    def test_external_call_whose_line_lacks_the_function_name_fails_m2(self):
        graph = make_graph(externals=(external("store", "os.Remove", 11),))

        report = self.check(graph)

        self.assertEqual([(f.check, f.location) for f in report.hard_failures], [("M2", "a.go:11")])

    def test_node_not_starting_on_its_declaration_fails_m3(self):
        graph = make_graph(
            nodes=(node("handler", 1, 3), node("serviceA", 7, 7), node("store", 11, 11)),
            edges=(), externals=(),
        )

        report = self.check(graph)

        self.assertEqual([(f.check, f.location) for f in report.hard_failures], [("M3", "a.go:1")])

    def test_missing_source_file_is_a_failure_not_a_crash(self):
        graph = make_graph()
        (self.root / FILE).unlink()

        report = self.check(graph)

        self.assertTrue(report.hard_failures)
        self.assertTrue(all("a.go" in f.message for f in report.hard_failures))

    def test_line_beyond_the_end_of_the_file_fails_instead_of_crashing(self):
        graph = make_graph(edges=(edge("handler", "serviceA", 400),))

        report = self.check(graph)

        self.assertIn("M1", [f.check for f in report.hard_failures])


class SoftChecksTest(VerifyTestCase):
    def notes(self, report, check):
        return [n for n in report.notes if n.check == check]

    def test_referenced_entry_with_a_non_call_mention_is_not_noted(self):
        report = self.check(make_graph())

        self.assertEqual(self.notes(report, "M4"), [])

    def test_referenced_entry_never_mentioned_outside_its_declaration_is_noted(self):
        source = SOURCE.replace("http.HandleFunc(\"/a\", handler)", "")

        report = self.check(make_graph(), source)

        self.assertEqual([n.subject for n in self.notes(report, "M4")], ["handler"])

    def test_call_text_the_graph_does_not_explain_is_listed_by_census(self):
        # Line 3 of this source also calls store(), which the graph does not know about.
        source = SOURCE.replace("func handler() { serviceA() }", "func handler() { serviceA(); store() }")

        report = self.check(make_graph(), source)

        census = self.notes(report, "M5")
        self.assertEqual([(n.subject, "a.go:3" in n.message) for n in census], [("store", True)])

    def test_complete_graph_has_no_census_notes(self):
        report = self.check(make_graph())

        self.assertEqual(self.notes(report, "M5"), [])

    def test_dynamic_edges_on_flagged_routes_are_counted(self):
        edges = (
            edge("handler", "serviceA", 3, "dynamic"),
            edge("handler2", "serviceB", 5),
            edge("serviceA", "store", 7),
            edge("serviceB", "store", 9),
        )

        report = self.check(make_graph(edges=edges))

        self.assertEqual([n.subject for n in self.notes(report, "M6")], ["store"])
        self.assertIn("1", self.notes(report, "M6")[0].message)


class DossierTest(VerifyTestCase):
    def dossier(self, **options):
        graph = make_graph()
        return verify.dossier_markdown(
            graph, analyze.analyze(graph), self.root, REPO_URL, **options
        )

    def test_every_hop_of_every_route_appears_with_location_and_code(self):
        text = self.dossier()

        self.assertIn("handler -> serviceA", text)
        self.assertIn("handler2 -> serviceB", text)
        self.assertIn("serviceA -> store", text)
        self.assertIn("serviceB -> store", text)
        self.assertIn("> 3 | func handler() { serviceA() }", text)

    def test_hops_link_to_the_exact_line_at_the_commit(self):
        text = self.dossier()

        self.assertIn(f"{REPO_URL}/blob/{helpers.SHA}/a.go#L3", text)

    def test_terminal_external_calls_and_entry_registrations_are_shown(self):
        text = self.dossier()

        self.assertIn("os.Open", text)
        self.assertIn("> 11 | func store() { _ = os.Open(\"x\") }", text)
        self.assertIn("a.go:14", text)  # where handler is registered
        self.assertIn('http.HandleFunc("/a", handler)', text)

    def test_dynamic_hops_are_marked(self):
        edges = (
            edge("handler", "serviceA", 3, "dynamic"),
            edge("handler2", "serviceB", 5),
            edge("serviceA", "store", 7),
            edge("serviceB", "store", 9),
        )
        graph = make_graph(edges=edges)

        text = verify.dossier_markdown(graph, analyze.analyze(graph), self.root, REPO_URL)

        self.assertIn("[dynamic dispatch]", text)

    def test_only_the_top_findings_are_included(self):
        text = self.dossier(top=0)

        self.assertNotIn("handler -> serviceA", text)

    def test_no_findings_says_so(self):
        graph = make_graph(edges=(edge("handler", "serviceA", 3),), externals=())

        text = verify.dossier_markdown(graph, analyze.analyze(graph), self.root, REPO_URL)

        self.assertIn("No flagged terminals", text)


if __name__ == "__main__":
    unittest.main()
