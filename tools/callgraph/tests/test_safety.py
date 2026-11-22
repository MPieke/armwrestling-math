import tempfile
import unittest
from pathlib import Path

from tools.callgraph import build, safety
from tools.callgraph.tests import helpers

PKG = "example.com/svc/pkg"


def node(name, package=PKG, file="svc/pkg/a.go", start=1, end=9, receiver=None):
    rest = f"{receiver}.{name}" if receiver else name
    return build.Node(f"{package}.{rest}", "go", name, package, file, start, end, "", helpers.SHA)


def edge(caller, callee, line, resolution="static", file="svc/pkg/a.go"):
    return build.Edge(caller, callee, file, line, resolution, helpers.SHA)


class BlastRadiusTest(unittest.TestCase):
    def graph(self):
        target = node("Annotate", receiver="OpenAIAnnotator")
        caller = node("annotateOne", package="example.com/svc/run", file="svc/run/r.go")
        other = node("helper")
        edges = (
            edge(caller.id, target.id, 12, "dynamic", "svc/run/r.go"),
            edge(other.id, target.id, 4),
            edge(target.id, target.id, 5),  # recursion is not a caller
        )
        return build.Graph((target, caller, other), edges), target

    def test_callers_are_listed_with_their_call_sites_and_how_they_call(self):
        graph, target = self.graph()

        radius = safety.blast_radius(graph, target.id)

        self.assertEqual(
            [(c.id.rsplit(".", 1)[-1], c.file, c.line, c.resolution) for c in radius.callers],
            [("helper", "svc/pkg/a.go", 4, "static"), ("annotateOne", "svc/run/r.go", 12, "dynamic")],
        )

    def test_a_call_through_an_interface_is_flagged_and_recursion_is_ignored(self):
        graph, target = self.graph()

        radius = safety.blast_radius(graph, target.id)

        self.assertTrue(radius.via_interface)
        self.assertEqual(len(radius.callers), 2)

    def test_exported_means_the_name_starts_with_a_capital(self):
        graph, target = self.graph()

        self.assertTrue(safety.blast_radius(graph, target.id).exported)
        self.assertFalse(safety.blast_radius(graph, "example.com/svc/pkg.helper").exported)

    def test_a_function_nobody_calls_has_an_empty_radius(self):
        graph, _ = self.graph()

        radius = safety.blast_radius(graph, "example.com/svc/pkg.helper")

        self.assertEqual((radius.callers, radius.via_interface), ((), False))


class SubjectTest(unittest.TestCase):
    def test_a_method_is_identified_by_its_receiver_type_and_a_function_by_its_name(self):
        self.assertEqual(safety.subject(node("Annotate", receiver="OpenAIAnnotator")), "OpenAIAnnotator")
        self.assertEqual(safety.subject(node("Submit")), "Submit")


class FindTestsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_tests_that_mention_the_receiver_type_are_found_with_their_line(self):
        self.write("svc/pkg/a_test.go", (
            "package pkg\n\n"
            "func TestThingParses(t *testing.T) {\n\tx := Thing{}\n\tx.Do()\n}\n\n"
            "func TestOther(t *testing.T) {\n\thelper()\n}\n"
        ))

        found = safety.find_tests(self.root, "svc", node("Do", receiver="Thing"))

        self.assertEqual([(t.name, t.file, t.line) for t in found], [("TestThingParses", "svc/pkg/a_test.go", 3)])

    def test_a_plain_function_is_found_by_its_own_name(self):
        self.write("svc/pkg/a_test.go", "package pkg\n\nfunc TestRuns(t *testing.T) {\n\tRun()\n}\n")

        found = safety.find_tests(self.root, "svc", node("Run"))

        self.assertEqual([t.name for t in found], ["TestRuns"])

    def test_a_test_in_another_package_counts_only_when_it_qualifies_the_name(self):
        self.write("svc/other/b_test.go", (
            "package other\n\n"
            "func TestQualified(t *testing.T) {\n\tx := pkg.Thing{}\n\t_ = x\n}\n\n"
            "func TestUnqualified(t *testing.T) {\n\tx := Thing{}\n\t_ = x\n}\n"
        ))

        found = safety.find_tests(self.root, "svc", node("Do", receiver="Thing"))

        self.assertEqual([t.name for t in found], ["TestQualified"])

    def test_only_test_files_under_the_scope_directory_are_read(self):
        self.write("svc/pkg/a.go", "package pkg\n\nfunc TestNotATest() { Thing{} }\n")
        self.write("elsewhere/c_test.go", "package x\n\nfunc TestOutside(t *testing.T) { Thing{} }\n")

        found = safety.find_tests(self.root, "svc", node("Do", receiver="Thing"))

        self.assertEqual(found, [])

    def test_a_missing_root_finds_nothing(self):
        self.assertEqual(safety.find_tests(self.root / "nope", "svc", node("Do")), [])

    def test_benchmarks_and_fuzz_targets_are_not_counted_as_tests(self):
        self.write("svc/pkg/a_test.go", (
            "package pkg\n\nfunc BenchmarkThing(b *testing.B) { Thing{} }\n"
            "func FuzzThing(f *testing.F) { Thing{} }\n"
        ))

        self.assertEqual(safety.find_tests(self.root, "svc", node("Do", receiver="Thing")), [])


class TestGapTest(unittest.TestCase):
    def tests(self, *names):
        return [safety.Test(name, "svc/x_test.go", 1) for name in names]

    def gaps(self, a, b):
        return safety.test_gaps(self.tests(*a), self.tests(*b), "OpenAIAnnotator", "OpenAIClaimExtractor")

    def test_a_behaviour_tested_for_one_function_but_not_the_other_is_a_gap(self):
        result = self.gaps(
            ["TestOpenAIAnnotatorParsesStructuredResponse", "TestOpenAIAnnotatorRedactsAPIKeyOnTransportFailure"],
            ["TestOpenAIClaimExtractorParsesStructuredResponse"],
        )

        self.assertEqual(result.only_first, ("RedactsAPIKeyOnTransportFailure",))
        self.assertEqual(result.only_second, ())

    def test_matching_behaviours_are_not_gaps(self):
        result = self.gaps(["TestOpenAIAnnotatorParses"], ["TestOpenAIClaimExtractorParses"])

        self.assertEqual((result.only_first, result.only_second), ((), ()))

    def test_a_function_with_no_tests_is_reported_instead_of_listing_every_gap(self):
        result = self.gaps(["TestOpenAIAnnotatorParses", "TestOpenAIAnnotatorRedacts"], [])

        self.assertEqual((result.none_first, result.none_second), (False, True))
        self.assertEqual(result.only_first, ())

    def test_neither_function_having_tests_is_reported(self):
        result = self.gaps([], [])

        self.assertEqual((result.none_first, result.none_second), (True, True))

    def test_a_test_name_without_the_subject_keeps_its_whole_name(self):
        result = self.gaps(["TestEndToEnd"], ["TestOpenAIClaimExtractorParses"])

        self.assertEqual(result.only_first, ("EndToEnd",))
        self.assertEqual(result.only_second, ("Parses",))


class StepDifferenceTest(unittest.TestCase):
    def steps(self, a, b, same=True, name="step"):
        return [{"name": name, "a": a, "b": b, "same": same}]

    def diff(self, lines_a, lines_b, steps):
        return safety.step_differences(lines_a, lines_b, steps)

    def test_a_different_result_type_is_reported_as_a_type_difference(self):
        a = ["\treturn ClaimAnnotation{}, nil, nil, err"]
        b = ["\treturn StructuredExtraction{}, nil, nil, err"]

        found = self.diff(a, b, self.steps([1, 1], [1, 1]))

        self.assertEqual([(d.kind, d.a, d.b) for d in found], [("type", "ClaimAnnotation", "StructuredExtraction")])

    def test_a_different_string_is_reported_with_both_full_strings(self):
        a = ['\treturn fmt.Errorf("OpenAI annotation HTTP %d: %s", code, body)']
        b = ['\treturn fmt.Errorf("OpenAI extraction HTTP %d: %s", code, body)']

        found = self.diff(a, b, self.steps([1, 1], [1, 1]))

        self.assertEqual(
            [(d.kind, d.a, d.b) for d in found],
            [("string", '"OpenAI annotation HTTP %d: %s"', '"OpenAI extraction HTTP %d: %s"')],
        )

    def test_a_renamed_receiver_used_in_several_places_is_one_grouped_difference(self):
        a = ["\tkey := annotator.APIKey", "\turl := annotator.BaseURL"]
        b = ["\tkey := extractor.APIKey", "\turl := extractor.BaseURL"]

        found = self.diff(a, b, self.steps([1, 2], [1, 2]))

        self.assertEqual([(d.kind, d.a, d.b, d.count) for d in found], [("receiver", "annotator", "extractor", 2)])

    def test_identical_steps_have_no_differences(self):
        lines = ["\tx := call(a, b)", "\treturn x"]

        self.assertEqual(self.diff(lines, lines, self.steps([1, 2], [1, 2])), [])

    def test_steps_not_marked_the_same_or_missing_a_side_are_ignored(self):
        a, b = ["\tx := one()"], ["\tx := two()"]

        self.assertEqual(self.diff(a, b, self.steps([1, 1], [1, 1], same=False)), [])
        self.assertEqual(self.diff(a, b, self.steps([1, 1], None)), [])

    def test_extra_tokens_on_one_side_are_reported_as_other_with_both_texts(self):
        a = ["\tx := call(a)"]
        b = ["\tx := call(a, extra)"]

        found = self.diff(a, b, self.steps([1, 1], [1, 1]))

        self.assertEqual([d.kind for d in found], ["other"])

    def test_a_difference_made_only_of_punctuation_is_not_reported(self):
        # B's range happens to include the closing brace of the function; A's does not.
        a = ["\treturn output, nil"]
        b = ["\treturn output, nil", "}"]

        self.assertEqual(self.diff(a, b, self.steps([1, 1], [1, 2])), [])

    def test_each_difference_names_the_steps_it_appears_in(self):
        a = ["\tx := annotator.A", "\ty := annotator.B"]
        b = ["\tx := extractor.A", "\ty := extractor.B"]
        steps = [
            {"name": "first", "a": [1, 1], "b": [1, 1], "same": True},
            {"name": "second", "a": [2, 2], "b": [2, 2], "same": True},
        ]

        found = self.diff(a, b, steps)

        self.assertEqual(found[0].steps, ("first", "second"))


if __name__ == "__main__":
    unittest.main()
