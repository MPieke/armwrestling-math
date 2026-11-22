import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.callgraph import analyze, build, cli
from tools.callgraph.tests import helpers
from tools.callgraph.tests.test_render import SOURCE_ANNOTATE, SOURCE_EXTRACT, judged

TWO_PAIRS = [
    ("e1", "a"), ("a", "t"), ("e2", "b"), ("b", "t"),
    ("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u"),
]
ENTRIES = ["e1", "e2", "e3", "e4"]
EXTERNALS = [("t", "os.Open"), ("u", "os.Create")]


def session(edges=TWO_PAIRS, entries=ENTRIES, verdicts=(), source_root=None):
    graph = helpers.make_graph(edges, entries=entries, externals=EXTERNALS)
    judgements = {"status": "ok", "judgements": list(verdicts), "calibration": None} if verdicts else None
    return cli.build_session(graph, analyze.analyze(graph), judgements, source_root)


class NumberingTest(unittest.TestCase):
    def test_a_card_the_model_wants_merged_is_numbered_before_an_unjudged_card(self):
        found = session(verdicts=[judged("c", "d", action="merge")])

        pairs = [(entry.number, entry.card.first) for entry in found.entries]

        self.assertEqual(pairs, [(1, "c"), (2, "a")])

    def test_a_card_the_model_says_to_keep_comes_last_and_is_marked_folded(self):
        found = session(verdicts=[judged("a", "b", action="keep", verdict="intentional")])

        self.assertEqual([(e.number, e.card.first, e.folded) for e in found.entries],
                         [(1, "c", False), (2, "a", True)])

    def test_numbers_match_the_order_of_the_run_summary(self):
        from tools.callgraph import render

        verdicts = [judged("c", "d", action="merge"), judged("a", "b", action="keep", verdict="intentional")]
        graph = helpers.make_graph(TWO_PAIRS, entries=ENTRIES, externals=EXTERNALS)
        judgements = {"status": "ok", "judgements": verdicts, "calibration": None}
        text = render.summary_markdown(graph, helpers.REPO_URL, analysis=analyze.analyze(graph),
                                       judgements=judgements)
        headings = [line for line in text.splitlines() if line.startswith("#### ")]

        found = cli.build_session(graph, analyze.analyze(graph), judgements, None)

        self.assertEqual(len(headings), len(found.entries))
        self.assertIn("`c` and `d`", headings[0])
        self.assertEqual(found.entries[0].card.first, "c")


class FindingsTest(unittest.TestCase):
    def test_each_finding_has_a_number_a_ref_a_level_and_the_pair(self):
        document = cli.findings_document(session())

        first = document["cards"][0]
        self.assertEqual(
            (first["number"], first["ref"], first["level"], first["kind"]),
            (1, "a~b", "low", "pair"),
        )
        self.assertEqual(document["total"], 2)

    def test_the_model_action_is_included_only_when_the_card_was_judged(self):
        document = cli.findings_document(session(verdicts=[judged("c", "d", action="merge")]))

        self.assertEqual([c["action"] for c in document["cards"]], ["merge", None])

    def test_the_text_listing_names_each_pair_with_its_level(self):
        text = cli.findings_text(cli.findings_document(session()))

        self.assertIn("1. [low] a and b", text)
        self.assertIn("2. [low] c and d", text)

    def test_the_text_listing_says_so_when_nothing_was_found(self):
        found = session(edges=[("e1", "a")], entries=["e1"], )

        self.assertIn("No redundant routes", cli.findings_text(cli.findings_document(found)))


class RefTest(unittest.TestCase):
    def test_a_card_is_found_by_number_or_by_its_function_pair(self):
        found = session()

        self.assertEqual(cli.find_entry(found, "2").card.first, "c")
        self.assertEqual(cli.find_entry(found, "c~d").number, 2)

    def test_an_unknown_number_or_pair_is_an_error_that_names_what_exists(self):
        found = session()

        for ref in ("9", "x~y", "zero"):
            with self.assertRaises(cli.CliError) as caught:
                cli.find_entry(found, ref)
            self.assertIn("1..2", str(caught.exception))


class CardFactsTest(unittest.TestCase):
    EDGES = [("e1", "Annotate"), ("Annotate", "t"), ("e2", "Extract"), ("Extract", "t")]

    def document(self, source=True, verdicts=None):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            if source:
                (base / "Annotate.go").write_text(SOURCE_ANNOTATE)
                (base / "Extract.go").write_text(SOURCE_EXTRACT)
                (base / "Annotate_test.go").write_text(
                    "package p\n\nfunc TestAnnotateParses(t *testing.T) {\n\tAnnotate()\n}\n\n"
                    "func TestAnnotateRedacts(t *testing.T) {\n\tAnnotate()\n}\n")
                (base / "Extract_test.go").write_text(
                    "package p\n\nfunc TestExtractParses(t *testing.T) {\n\tExtract()\n}\n")
            found = session(
                self.EDGES, ["e1", "e2"],
                verdicts=[judged("Annotate", "Extract")] if verdicts is None else verdicts,
                source_root=str(base) if source else None,
            )
            return cli.card_document(found, "1")

    def test_the_card_names_both_functions_with_their_files(self):
        document = self.document()

        self.assertEqual([f["id"] for f in document["functions"]], ["Annotate", "Extract"])
        self.assertEqual(document["functions"][0]["file"], "Annotate.go")

    def test_callers_come_from_the_graph_with_the_call_site(self):
        document = self.document()

        callers = document["blast_radius"]["Annotate"]["callers"]
        self.assertEqual([c["id"] for c in callers], ["e1"])
        self.assertEqual(callers[0]["resolution"], "static")

    def test_tests_are_found_by_mention_and_gaps_by_name(self):
        document = self.document()

        self.assertEqual([t["name"] for t in document["tests"]["Annotate"]],
                         ["TestAnnotateParses", "TestAnnotateRedacts"])
        self.assertEqual(document["test_gaps"]["only_first"], ["Redacts"])

    def test_differences_inside_the_steps_called_the_same_are_listed(self):
        document = self.document()

        kinds = {(d["kind"], d["a"], d["b"]) for d in document["differences"]}
        self.assertIn(("string", '"annotation label"', '"extraction label"'), kinds)

    def test_the_model_suggestion_is_marked_advisory(self):
        document = self.document()

        self.assertEqual(document["model_suggestion"]["action"], "extract_shared")
        self.assertTrue(document["model_suggestion"]["advisory"])

    def test_without_a_judgement_there_is_no_suggestion_and_no_differences(self):
        document = self.document(verdicts=[])

        self.assertIsNone(document["model_suggestion"])
        self.assertIsNone(document["differences"])
        self.assertIn("steps", document["differences_note"])

    def test_without_source_access_tests_and_differences_are_not_checked(self):
        document = self.document(source=False)

        self.assertIsNone(document["tests"])
        self.assertIsNone(document["differences"])
        self.assertIn("source", document["differences_note"])

    def test_the_card_text_shows_level_callers_and_tests(self):
        text = cli.card_text(self.document())

        # the two functions call nothing but the shared target, so their overlap is 0%
        self.assertIn("Level: low (call overlap 0%", text)
        self.assertIn("Annotate is called from e1", text)
        self.assertIn("no counterpart by name for: Redacts", text)


class ReadableNamesTest(unittest.TestCase):
    PKG = "example.com/svc/pkg"

    def document(self):
        a, b = f"{self.PKG}.OpenAIAnnotator.Annotate", f"{self.PKG}.OpenAIExtractor.Extract"
        send = f"{self.PKG}.Send"
        edges = [("e1", a), (a, send), ("e2", b), (b, send)]
        graph = helpers.make_graph(edges, entries=["e1", "e2"], externals=[(send, "os.Open")],
                                   packages={a: self.PKG, b: self.PKG, send: self.PKG})
        found = cli.build_session(graph, analyze.analyze(graph), None, None)
        return cli.card_document(found, "1")

    def test_the_text_uses_short_names_without_the_package_path(self):
        text = cli.card_text(self.document())

        self.assertIn("OpenAIAnnotator.Annotate and OpenAIExtractor.Extract", text)
        self.assertIn("Reach: Send", text)
        self.assertNotIn("example.com/svc/pkg", text)

    def test_the_json_keeps_full_ids_and_adds_a_short_name_for_each_function_and_caller(self):
        document = self.document()

        self.assertTrue(document["functions"][0]["id"].startswith(self.PKG))
        self.assertEqual(document["functions"][0]["short"], "OpenAIAnnotator.Annotate")
        caller = document["blast_radius"][document["functions"][0]["id"]]["callers"][0]
        self.assertEqual((caller["id"], caller["name"]), ("e1", "e1"))

    def test_the_findings_text_also_uses_short_names(self):
        a, b = f"{self.PKG}.A", f"{self.PKG}.B"
        edges = [("e1", a), (a, "t"), ("e2", b), (b, "t")]
        graph = helpers.make_graph(edges, entries=["e1", "e2"], externals=[("t", "os.Open")],
                                   packages={a: self.PKG, b: self.PKG})
        found = cli.build_session(graph, analyze.analyze(graph), None, None)

        text = cli.findings_text(cli.findings_document(found))

        self.assertIn("1. [low] A and B", text)


class MainTest(unittest.TestCase):
    def graph_dir(self, directory):
        base = Path(directory)
        graph = build.build_graph(helpers.raw_nodes_csv(), helpers.raw_edges_csv(), helpers.SHA)
        (base / "nodes.csv").write_text(build.nodes_to_csv(graph))
        (base / "edges.csv").write_text(build.edges_to_csv(graph))
        return base

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(list(argv), out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_findings_json_is_valid_json_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            code, out, _ = self.run_main("--graph-dir", str(self.graph_dir(directory)), "findings", "--json")

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["cards"], [])

    def test_an_unknown_card_exits_two_with_a_message_on_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            code, out, err = self.run_main("--graph-dir", str(self.graph_dir(directory)), "card", "1")

        self.assertEqual((code, out), (2, ""))
        self.assertIn("no card", err)

    def test_a_missing_graph_directory_exits_two_and_says_what_to_do(self):
        code, _, err = self.run_main("--graph-dir", "/nonexistent-graph-dir", "findings")

        self.assertEqual(code, 2)
        self.assertIn("nodes.csv", err)

    def test_a_malformed_judgements_file_is_ignored_not_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            base = self.graph_dir(directory)
            (base / "judgements.json").write_text("{not json")
            code, _, _ = self.run_main("--graph-dir", str(base), "findings")

        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
