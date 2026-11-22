import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.callgraph import analyze, build, cli, plan
from tools.callgraph.tests import helpers
from tools.callgraph.tests.test_render import SOURCE_ANNOTATE, SOURCE_EXTRACT, STEPS, judged

EDGES = [("e1", "Annotate"), ("Annotate", "t"), ("e2", "Extract"), ("Extract", "t")]
TEST_A = ("package p\n\nfunc TestAnnotateParses(t *testing.T) {\n\tAnnotate()\n}\n\n"
          "func TestAnnotateRedacts(t *testing.T) {\n\tAnnotate()\n}\n")
TEST_B = "package p\n\nfunc TestExtractParses(t *testing.T) {\n\tExtract()\n}\n"


def good_plan():
    return {
        "card": "Annotate~Extract",
        "summary": "Share the request pipeline.",
        "shared_name": "chatCompletion",
        "steps": copy.deepcopy(STEPS),
        "moved_steps": ["build request", "send"],
        "differences": [
            {"a": '"annotation label"', "b": '"extraction label"',
             "handled_by": "parameter", "parameter": "label"},
            {"a": "annotator", "b": "extractor", "handled_by": "unified"},
        ],
        "planned_files": ["Annotate.go", "Extract.go", "shared.go"],
        "will_not_touch": [],
        "constraints": ["keep the public interface unchanged"],
        "tests": ["TestExtractRedacts"],
        "uncertainties": [],
    }


class Fixture(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def sources(self, tests=True):
        (self.root / "Annotate.go").write_text(SOURCE_ANNOTATE)
        (self.root / "Extract.go").write_text(SOURCE_EXTRACT)
        if tests:
            (self.root / "Annotate_test.go").write_text(TEST_A)
            (self.root / "Extract_test.go").write_text(TEST_B)

    def session(self, source=True, verdict=True):
        if source:
            self.sources()
        graph = helpers.make_graph(EDGES, entries=["e1", "e2"], externals=[("t", "os.Open")])
        judgements = {"status": "ok", "judgements": [judged("Annotate", "Extract")], "calibration": None}
        return cli.build_session(graph, analyze.analyze(graph), judgements if verdict else None,
                                 str(self.root) if source else None)

    def codes(self, result, level=None):
        return [p.code for p in result.problems if level in (None, p.level)]


class LoadSaveTest(Fixture):
    def test_a_saved_plan_loads_back_unchanged(self):
        path = self.root / ".callgraph" / "plan.json"

        plan.save_plan(path, good_plan())

        self.assertEqual(plan.load_plan(path), good_plan())

    def test_a_missing_plan_says_how_to_create_one(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.load_plan(self.root / "nope.json")

        self.assertIn("plan init", str(caught.exception))

    def test_malformed_json_is_a_plan_error_not_a_traceback(self):
        path = self.root / "plan.json"
        path.write_text("{not json")

        with self.assertRaises(plan.PlanError):
            plan.load_plan(path)

    def test_the_digest_does_not_depend_on_key_order(self):
        reordered = dict(reversed(list(good_plan().items())))

        self.assertEqual(plan.digest(good_plan()), plan.digest(reordered))
        self.assertNotEqual(plan.digest(good_plan()), plan.digest({**good_plan(), "summary": "other"}))


class TemplateTest(Fixture):
    def test_a_draft_takes_steps_and_fix_from_the_model_and_lists_differences_to_decide(self):
        draft = plan.template(self.session(), "1")

        self.assertEqual(draft["card"], "Annotate~Extract")
        self.assertEqual(draft["moved_steps"], ["build request", "send"])
        self.assertEqual(draft["shared_name"], "chatCompletion")
        self.assertEqual({(d["a"], d["b"]) for d in draft["differences"]},
                         {('"annotation label"', '"extraction label"'), ("annotator", "extractor")})
        self.assertTrue(all(d["handled_by"] is None for d in draft["differences"]))
        self.assertEqual(draft["planned_files"], ["Annotate.go", "Extract.go"])

    def test_a_draft_without_a_judgement_has_no_steps_for_the_agent_to_fill_in(self):
        draft = plan.template(self.session(verdict=False), "1")

        self.assertEqual((draft["steps"], draft["moved_steps"], draft["differences"]), ([], [], []))

    def test_a_draft_for_an_unknown_card_is_an_error(self):
        with self.assertRaises(cli.CliError):
            plan.template(self.session(), "9")

    def test_a_fresh_draft_fails_lint_until_the_differences_are_decided(self):
        found = self.session()

        result = plan.lint(plan.template(found, "1"), found)

        self.assertIn("E_DIFF_UNHANDLED", self.codes(result, "error"))


class LintTest(Fixture):
    def test_a_complete_plan_has_no_errors(self):
        result = plan.lint(good_plan(), self.session())

        self.assertTrue(result.ok, result.problems)

    def test_a_difference_the_plan_does_not_mention_is_an_error_naming_it(self):
        bad = good_plan()
        bad["differences"] = bad["differences"][1:]  # drops the label string

        result = plan.lint(bad, self.session())

        self.assertFalse(result.ok)
        problem = next(p for p in result.problems if p.code == "E_DIFF_UNHANDLED")
        self.assertIn('"annotation label"', problem.message)

    def test_a_difference_with_no_decision_counts_as_not_handled(self):
        bad = good_plan()
        bad["differences"][0]["handled_by"] = None

        self.assertIn("E_DIFF_UNHANDLED", self.codes(plan.lint(bad, self.session()), "error"))

    def test_an_unknown_handler_or_a_parameter_without_a_name_is_an_error(self):
        unknown = good_plan()
        unknown["differences"][0]["handled_by"] = "ignore"
        nameless = good_plan()
        del nameless["differences"][0]["parameter"]

        self.assertIn("E_DIFF_HANDLER", self.codes(plan.lint(unknown, self.session())))
        self.assertIn("E_DIFF_HANDLER", self.codes(plan.lint(nameless, self.session())))

    def test_stays_is_a_valid_decision_for_a_difference(self):
        stays = good_plan()
        stays["differences"][0] = {"a": '"annotation label"', "b": '"extraction label"', "handled_by": "stays"}

        self.assertTrue(plan.lint(stays, self.session()).ok)

    def test_only_differences_inside_moved_steps_must_be_handled(self):
        only_send = good_plan()
        only_send["moved_steps"] = ["send"]  # the label string is in "build request", which stays
        only_send["differences"] = only_send["differences"][1:]

        result = plan.lint(only_send, self.session())

        self.assertTrue(result.ok, result.problems)

    def test_a_listed_difference_that_does_not_exist_is_a_warning_not_an_error(self):
        stale = good_plan()
        stale["differences"].append({"a": "x", "b": "y", "handled_by": "stays"})

        result = plan.lint(stale, self.session())

        self.assertTrue(result.ok)
        self.assertIn("W_DIFF_STALE", self.codes(result, "warning"))

    def test_a_step_range_outside_the_function_is_an_error(self):
        bad = good_plan()
        bad["steps"][1]["a"] = [6, 500]  # make_graph functions end at line 100

        self.assertIn("E_RANGE", self.codes(plan.lint(bad, self.session()), "error"))

    def test_a_reversed_range_is_an_error(self):
        bad = good_plan()
        bad["steps"][1]["b"] = [9, 5]

        self.assertIn("E_RANGE", self.codes(plan.lint(bad, self.session()), "error"))

    def test_overlapping_steps_in_one_function_are_an_error(self):
        bad = good_plan()
        bad["steps"][2]["a"] = [9, 15]  # overlaps "build request" 6-10

        self.assertIn("E_RANGE", self.codes(plan.lint(bad, self.session()), "error"))

    def test_a_duplicate_step_name_is_an_error(self):
        bad = good_plan()
        bad["steps"][2]["name"] = "build request"

        self.assertIn("E_DUP_STEP", self.codes(plan.lint(bad, self.session()), "error"))

    def test_a_moved_step_must_exist_and_exist_in_both_functions(self):
        unknown = good_plan()
        unknown["moved_steps"] = ["build request", "teleport"]
        one_sided = good_plan()
        one_sided["steps"][2]["b"] = None  # "send" now only in Annotate

        self.assertIn("E_MOVED_UNKNOWN", self.codes(plan.lint(unknown, self.session())))
        self.assertIn("E_MOVED_ONE_SIDED", self.codes(plan.lint(one_sided, self.session())))

    def test_a_plan_that_moves_nothing_is_an_error(self):
        bad = good_plan()
        bad["moved_steps"] = []

        self.assertIn("E_NO_MOVED", self.codes(plan.lint(bad, self.session()), "error"))

    def test_a_planned_file_under_a_will_not_touch_path_is_an_error(self):
        bad = good_plan()
        bad["will_not_touch"] = ["Extract.go"]

        result = plan.lint(bad, self.session())

        self.assertIn("E_WILL_NOT_TOUCH", self.codes(result, "error"))

    def test_will_not_touch_may_name_a_function_and_means_its_file(self):
        bad = good_plan()
        bad["will_not_touch"] = ["e1"]
        bad["planned_files"].append("e1.go")

        self.assertIn("E_WILL_NOT_TOUCH", self.codes(plan.lint(bad, self.session()), "error"))

    def test_a_directory_in_will_not_touch_covers_the_files_below_it(self):
        bad = good_plan()
        bad["will_not_touch"] = ["internal/youtube"]
        bad["planned_files"].append("internal/youtube/run.go")

        self.assertIn("E_WILL_NOT_TOUCH", self.codes(plan.lint(bad, self.session())))

    def test_without_source_differences_cannot_be_checked_and_that_is_a_warning(self):
        result = plan.lint(good_plan(), self.session(source=False))

        self.assertTrue(result.ok)
        self.assertIn("W_NO_SOURCE", self.codes(result, "warning"))

    def test_a_test_gap_with_no_test_planned_is_a_warning(self):
        bad = good_plan()
        bad["tests"] = []

        result = plan.lint(bad, self.session())

        self.assertIn("W_TESTS", self.codes(result, "warning"))
        self.assertTrue(result.ok)

    def test_constraints_are_reported_as_not_machine_checked(self):
        result = plan.lint(good_plan(), self.session())

        note = next(p for p in result.problems if p.code == "N_CONSTRAINTS")
        self.assertEqual(note.level, "note")
        self.assertIn("keep the public interface unchanged", note.message)

    def test_a_missing_or_mistyped_field_is_a_schema_error_and_stops_the_other_checks(self):
        broken = good_plan()
        del broken["moved_steps"]
        broken["steps"] = "many"

        result = plan.lint(broken, self.session())

        self.assertEqual(set(self.codes(result)), {"E_SCHEMA"})

    def test_an_unknown_card_is_an_error(self):
        bad = good_plan()
        bad["card"] = "x~y"

        self.assertIn("E_CARD", self.codes(plan.lint(bad, self.session()), "error"))


class ApprovalTest(Fixture):
    def paths(self):
        return self.root / "plan.json", self.root / "approval.json"

    def test_a_plan_with_lint_errors_cannot_be_approved(self):
        plan_path, approval_path = self.paths()
        bad = good_plan()
        bad["moved_steps"] = []
        plan.save_plan(plan_path, bad)

        with self.assertRaises(plan.PlanError) as caught:
            plan.approve(plan_path, approval_path, self.session())

        self.assertIn("E_NO_MOVED", str(caught.exception))
        self.assertFalse(approval_path.exists())

    def test_approval_records_the_digest_and_status_is_approved(self):
        plan_path, approval_path = self.paths()
        plan.save_plan(plan_path, good_plan())

        plan.approve(plan_path, approval_path, self.session())

        self.assertEqual(json.loads(approval_path.read_text())["plan_digest"], plan.digest(good_plan()))
        self.assertEqual(plan.approval_status(plan_path, approval_path), "approved")

    def test_changing_the_plan_after_approval_revokes_it(self):
        plan_path, approval_path = self.paths()
        plan.save_plan(plan_path, good_plan())
        plan.approve(plan_path, approval_path, self.session())

        plan.save_plan(plan_path, {**good_plan(), "summary": "different"})

        self.assertEqual(plan.approval_status(plan_path, approval_path), "changed since approval")

    def test_a_plan_never_approved_has_status_not_approved(self):
        plan_path, approval_path = self.paths()
        plan.save_plan(plan_path, good_plan())

        self.assertEqual(plan.approval_status(plan_path, approval_path), "not approved")


class PlanCommandTest(Fixture):
    def graph_dir(self):
        self.sources()
        graph = helpers.make_graph(EDGES, entries=["e1", "e2"], externals=[("t", "os.Open")])
        base = self.root / "graph"
        base.mkdir()
        (base / "nodes.csv").write_text(build.nodes_to_csv(graph))
        (base / "edges.csv").write_text(build.edges_to_csv(graph))
        (base / "judgements.json").write_text(json.dumps(
            {"status": "ok", "judgements": [judged("Annotate", "Extract")], "calibration": None}))
        return base

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(list(argv), out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def common(self):
        return ["--graph-dir", str(self.graph_dir()), "--source-root", str(self.root),
                "--ignore-file", str(self.root / "none.txt")]

    def test_init_writes_a_draft_and_will_not_overwrite_without_force(self):
        target = self.root / "p" / "plan.json"
        (self.root / "none.txt").write_text("")
        common = self.common()

        first = self.run_main(*common, "plan", "--plan", str(target), "init", "1")
        second = self.run_main(*common, "plan", "--plan", str(target), "init", "1")
        forced = self.run_main(*common, "plan", "--plan", str(target), "init", "1", "--force")

        self.assertEqual((first[0], second[0], forced[0]), (0, 2, 0))
        self.assertIn("already exists", second[2])
        self.assertEqual(json.loads(target.read_text())["card"], "Annotate~Extract")

    def test_lint_exits_one_with_the_codes_when_the_plan_has_errors_and_zero_when_clean(self):
        (self.root / "none.txt").write_text("")
        target = self.root / "plan.json"
        common = self.common()
        plan.save_plan(target, {**good_plan(), "moved_steps": []})

        bad = self.run_main(*common, "plan", "--plan", str(target), "lint")
        plan.save_plan(target, good_plan())
        good = self.run_main(*common, "plan", "--plan", str(target), "lint")

        self.assertEqual((bad[0], good[0]), (1, 0))
        self.assertIn("E_NO_MOVED", bad[1])

    def test_approve_then_status_reports_approved(self):
        (self.root / "none.txt").write_text("")
        target = self.root / "plan.json"
        common = self.common()
        plan.save_plan(target, good_plan())

        approved = self.run_main(*common, "plan", "--plan", str(target), "approve")
        status = self.run_main(*common, "plan", "--plan", str(target), "status")

        self.assertEqual(approved[0], 0)
        self.assertIn("approved", status[1])


if __name__ == "__main__":
    unittest.main()
