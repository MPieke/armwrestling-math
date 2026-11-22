import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.callgraph import analyze, build, check, cli, plan
from tools.callgraph.tests import helpers
from tools.callgraph.tests.test_plan import EDGES as BEFORE_EDGES
from tools.callgraph.tests.test_plan import good_plan

AFTER_EDGES = [("e1", "Annotate"), ("Annotate", "chat"), ("e2", "Extract"), ("Extract", "chat"),
               ("chat", "t")]
EXTERNALS = [("t", "os.Open")]


def make_session(edges, entries=("e1", "e2"), source_root=None, externals=EXTERNALS, extra_nodes=()):
    graph = helpers.make_graph(edges, entries=list(entries), externals=list(externals),
                               extra_nodes=list(extra_nodes))
    return cli.build_session(graph, analyze.analyze(graph), None, source_root)


class FakeRunner:
    """Records commands and writes the files a real CodeQL run would."""

    def __init__(self, git=None, fail_on=None):
        self.calls = []
        self.git = {
            ("git", "rev-parse", "HEAD"): helpers.SHA + "\n",
            ("git", "ls-files", "--others", "--exclude-standard"): "",
        }
        self.git.update(git or {})
        self.fail_on = fail_on

    def __call__(self, argv, cwd=None):
        argv = list(argv)
        self.calls.append((argv, cwd))
        if self.fail_on and argv[: len(self.fail_on)] == self.fail_on:
            raise check.CheckError(f"{' '.join(argv[:3])} failed")
        if argv[:3] == ["codeql", "bqrs", "decode"]:
            output = Path(next(a for a in argv if a.startswith("--output=")).split("=", 1)[1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text({"nodes": helpers.raw_nodes_csv(), "edges": helpers.raw_edges_csv(),
                               "externals": helpers.raw_externals_csv()}[output.stem])
            return ""
        if argv[0] == "git":
            key = tuple(argv) if tuple(argv) in self.git else tuple(argv[:3])
            if key in self.git:
                return self.git[key]
            if argv[:2] == ["git", "diff"]:
                return self.git.get(("git", "diff"), "")
            return ""
        return ""

    def codeql(self):
        return [argv for argv, _ in self.calls if argv[0] == "codeql"]


class ProduceGraphTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name) / "work"
        self.source = Path(self.directory.name) / "repo"
        self.source.mkdir()

    def produce(self, runner, **options):
        return check.produce_graph(self.source, self.work, runner=runner, **options)

    def test_a_database_is_created_then_each_query_is_run_and_decoded_in_order(self):
        runner = FakeRunner()

        self.produce(runner, scope="codeql/go/test")

        commands = [(a[1], a[2]) if a[1] != "database" else (a[1], a[2]) for a in runner.codeql()]
        self.assertEqual([c[0] for c in commands],
                         ["database", "query", "bqrs", "query", "bqrs", "query", "bqrs"])
        create = runner.codeql()[0]
        self.assertIn("--language=go", create)
        self.assertIn(f"--source-root={self.source}", create)
        self.assertIn("--overwrite", create)

    def test_the_work_directory_exists_when_codeql_creates_the_database_inside_it(self):
        seen = []

        class Watching(FakeRunner):
            def __call__(inner, argv, cwd=None):
                if list(argv)[:3] == ["codeql", "database", "create"]:
                    seen.append(Path(argv[3]).parent.is_dir())
                return super().__call__(argv, cwd)

        self.produce(Watching(), scope="codeql/go/test")

        self.assertEqual(seen, [True])

    def test_queries_run_from_the_codeql_directory_against_the_new_database(self):
        runner = FakeRunner()

        self.produce(runner, scope="codeql/go/test")

        queries = [(a, cwd) for a, cwd in runner.calls if a[:3] == ["codeql", "query", "run"]]
        self.assertEqual([a[-1] for a, _ in queries], ["go/nodes.ql", "go/edges.ql", "go/externals.ql"])
        self.assertTrue(all(cwd == check.CODEQL_DIR for _, cwd in queries))
        self.assertTrue(all(f"--database={self.work / 'db'}" in a for a, _ in queries))

    def test_an_existing_database_is_reused_and_not_recreated(self):
        runner = FakeRunner()

        self.produce(runner, scope="codeql/go/test", database=Path("/some/db"))

        self.assertFalse(any(a[1] == "database" for a in runner.codeql()))
        self.assertTrue(any("--database=/some/db" in a for a in runner.codeql()))

    def test_the_graph_is_stamped_with_the_current_commit_and_written_for_reuse(self):
        runner = FakeRunner()

        graph, graph_dir = self.produce(runner, scope="codeql/go/test")

        self.assertEqual({n.sha for n in graph.nodes}, {helpers.SHA})
        again = build.load_graph((graph_dir / "nodes.csv").read_text(), (graph_dir / "edges.csv").read_text(),
                                 (graph_dir / "externals.csv").read_text())
        self.assertEqual(len(again.nodes), len(graph.nodes))

    def test_only_functions_under_the_scope_are_kept(self):
        graph, _ = self.produce(FakeRunner(), scope="codeql/go/test")

        self.assertEqual(len(graph.nodes), 4)

    def test_a_scope_with_no_functions_is_an_error_naming_the_scope(self):
        with self.assertRaises(check.CheckError) as caught:
            self.produce(FakeRunner(), scope="services/nothing")

        self.assertIn("services/nothing", str(caught.exception))

    def test_a_failing_command_stops_the_run_with_its_message(self):
        with self.assertRaises(check.CheckError):
            self.produce(FakeRunner(fail_on=["codeql", "database"]), scope="codeql/go/test")

    def test_a_missing_codeql_says_to_push_and_let_ci_check(self):
        with self.assertRaises(check.CheckError) as caught:
            check.default_runner(["codeql-not-installed-xyz", "--version"])

        self.assertIn("codeql-not-installed-xyz", str(caught.exception))
        self.assertIn("CI", str(caught.exception))

    def test_a_failing_process_reports_the_end_of_its_error_output(self):
        with self.assertRaises(check.CheckError) as caught:
            check.default_runner([sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])

        self.assertIn("boom", str(caught.exception))


class ChangedFilesTest(unittest.TestCase):
    def test_files_changed_since_the_baseline_commit_and_new_files_are_combined_and_sorted(self):
        runner = FakeRunner(git={("git", "diff"): "b.go\na.go\n",
                                 ("git", "ls-files", "--others", "--exclude-standard"): "new.go\na.go\n"})

        files, known = check.changed_files("/repo", helpers.SHA, runner=runner)

        self.assertEqual((files, known), (["a.go", "b.go", "new.go"], True))
        diff = next(a for a, _ in runner.calls if a[:2] == ["git", "diff"])
        self.assertIn(helpers.SHA, diff)

    def test_an_unknown_baseline_commit_falls_back_to_head_and_says_so(self):
        runner = FakeRunner(git={("git", "diff"): "a.go\n"}, fail_on=["git", "cat-file"])

        files, known = check.changed_files("/repo", helpers.SHA, runner=runner)

        self.assertEqual((files, known), (["a.go"], False))
        diff = next(a for a, _ in runner.calls if a[:2] == ["git", "diff"])
        self.assertIn("HEAD", diff)


class CompareTest(unittest.TestCase):
    # both functions call h1, json.Marshal and io.ReadAll directly and reach t on separate routes
    SHARING = BEFORE_EDGES + [("Annotate", "h1"), ("Extract", "h1")]
    SHARED_EXTERNALS = [("Annotate", "json.Marshal"), ("Extract", "json.Marshal"),
                        ("Annotate", "io.ReadAll"), ("Extract", "io.ReadAll")]

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.baseline = make_session(BEFORE_EDGES)

    def compare(self, fresh=None, document=None, changed=(), known=True):
        return check.compare(document or good_plan(), self.baseline,
                             fresh or make_session(AFTER_EDGES, source_root=str(self.root)),
                             list(changed), known)

    def codes(self, report, level=None):
        return [p.code for p in report.problems if level in (None, p.level)]

    def test_a_fix_that_removes_the_card_with_no_new_cards_is_ok(self):
        report = self.compare()

        self.assertTrue(report.ok, report.problems)
        self.assertTrue(report.data["card_gone"])

    def test_the_card_still_being_there_is_an_error(self):
        report = self.compare(fresh=make_session(BEFORE_EDGES))

        self.assertFalse(report.ok)
        self.assertIn("E_CARD_REMAINS", self.codes(report, "error"))

    def test_a_new_card_between_functions_that_already_existed_is_an_error_naming_the_pair(self):
        edges = AFTER_EDGES + [("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u")]
        fresh = make_session(edges, entries=("e1", "e2", "e3", "e4"),
                             externals=EXTERNALS + [("u", "os.Create")])
        self.baseline = make_session(BEFORE_EDGES, extra_nodes=("c", "d"))

        report = self.compare(fresh=fresh)

        problem = next(p for p in report.problems if p.code == "E_NEW_CARD")
        self.assertIn("c~d", problem.message)
        self.assertFalse(report.ok)

    def test_a_new_card_that_involves_a_new_function_is_a_warning_because_old_duplication_may_have_moved(self):
        edges = AFTER_EDGES + [("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u")]
        fresh = make_session(edges, entries=("e1", "e2", "e3", "e4"),
                             externals=EXTERNALS + [("u", "os.Create")])

        report = self.compare(fresh=fresh)  # c and d did not exist in the baseline

        warning = next(p for p in report.problems if p.code == "W_NEW_CARD_NEW_FUNCTION")
        self.assertIn("c~d", warning.message)
        self.assertIn("moved", warning.message)
        self.assertNotIn("E_NEW_CARD", self.codes(report))
        self.assertTrue(report.ok, report.problems)

    def test_a_card_that_remains_but_shares_fewer_direct_calls_is_a_warning_with_the_numbers(self):
        self.baseline = make_session(self.SHARING, externals=EXTERNALS + self.SHARED_EXTERNALS)
        fresh = make_session(self.SHARING, externals=EXTERNALS)  # json.Marshal and io.ReadAll moved out

        report = self.compare(fresh=fresh)

        warning = next(p for p in report.problems if p.code == "W_CARD_REMAINS")
        self.assertIn("3 to 1", warning.message)
        self.assertNotIn("E_CARD_REMAINS", self.codes(report))
        self.assertTrue(report.ok, report.problems)

    def test_a_card_that_remains_with_as_many_shared_direct_calls_is_still_an_error(self):
        self.baseline = make_session(self.SHARING, externals=EXTERNALS + self.SHARED_EXTERNALS)

        report = self.compare(fresh=make_session(self.SHARING, externals=EXTERNALS + self.SHARED_EXTERNALS))

        self.assertIn("E_CARD_REMAINS", self.codes(report, "error"))

    def test_a_card_that_remains_with_more_shared_direct_calls_is_an_error(self):
        self.baseline = make_session(self.SHARING, externals=EXTERNALS)

        report = self.compare(fresh=make_session(self.SHARING, externals=EXTERNALS + self.SHARED_EXTERNALS))

        self.assertIn("E_CARD_REMAINS", self.codes(report, "error"))

    def test_the_report_carries_the_pair_before_and_after_so_progress_is_visible(self):
        self.baseline = make_session(self.SHARING, externals=EXTERNALS + self.SHARED_EXTERNALS)
        fresh = make_session(self.SHARING, externals=EXTERNALS)

        pair = self.compare(fresh=fresh).data["pair"]

        self.assertEqual((pair["before"]["shared_calls"], pair["after"]["shared_calls"]), (3, 1))

    def test_when_the_card_is_gone_the_pair_after_is_none(self):
        self.assertIsNone(self.compare().data["pair"]["after"])

    def test_a_card_that_already_existed_in_the_baseline_is_not_new(self):
        edges = BEFORE_EDGES + [("e3", "c"), ("c", "u"), ("e4", "d"), ("d", "u")]
        baseline = make_session(edges, entries=("e1", "e2", "e3", "e4"),
                                externals=EXTERNALS + [("u", "os.Create")])
        fresh = make_session(AFTER_EDGES + edges[4:], entries=("e1", "e2", "e3", "e4"),
                             externals=EXTERNALS + [("u", "os.Create")])

        report = check.compare(good_plan(), baseline, fresh, [], True)

        self.assertNotIn("E_NEW_CARD", self.codes(report))
        self.assertTrue(report.ok, report.problems)

    def test_a_function_that_no_longer_exists_is_noted_because_the_card_may_be_gone_for_that_reason(self):
        fresh = make_session([("e1", "Annotate"), ("Annotate", "t")], entries=("e1",))

        report = self.compare(fresh=fresh)

        self.assertIn("N_FUNCTION_GONE", self.codes(report, "note"))

    def test_a_changed_file_under_will_not_touch_is_an_error(self):
        document = good_plan()
        document["will_not_touch"] = ["internal/youtube"]

        report = self.compare(document=document, changed=["internal/youtube/run.go", "Annotate.go"])

        self.assertIn("E_WILL_NOT_TOUCH_CHANGED", self.codes(report, "error"))

    def test_a_changed_file_outside_the_plan_is_a_warning_but_test_files_are_expected(self):
        report = self.compare(changed=["Annotate.go", "shared.go", "other.go", "other_test.go"])

        warning = next(p for p in report.problems if p.code == "W_OUTSIDE_PLAN")
        self.assertIn("other.go", warning.message)
        self.assertNotIn("other_test.go", warning.message)
        self.assertNotIn("Annotate.go", warning.message)
        self.assertTrue(report.ok)

    def test_a_planned_test_that_does_not_exist_is_a_warning(self):
        report = self.compare()

        self.assertIn("W_PLANNED_TEST_MISSING", self.codes(report, "warning"))

    def test_a_planned_test_that_now_exists_is_not_reported(self):
        (self.root / "Extract_test.go").write_text("package p\n\nfunc TestExtractRedacts(t *testing.T) {}\n")

        report = self.compare()

        self.assertNotIn("W_PLANNED_TEST_MISSING", self.codes(report))

    def test_an_unknown_baseline_commit_is_a_warning(self):
        report = self.compare(known=False)

        self.assertIn("W_BASE_UNKNOWN", self.codes(report, "warning"))

    def test_the_report_always_says_behaviour_and_tests_were_not_verified(self):
        note = next(p for p in self.compare().problems if p.code == "N_NOT_VERIFIED")

        self.assertIn("does not run the repository's tests", note.message)

    def test_a_card_that_was_not_in_the_baseline_is_a_warning_and_nothing_to_compare(self):
        document = good_plan()
        document["card"] = "x~y"

        report = self.compare(document=document)

        self.assertIn("W_NOT_IN_BASELINE", self.codes(report, "warning"))


class CheckCommandTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        graph = helpers.make_graph(BEFORE_EDGES, entries=["e1", "e2"], externals=EXTERNALS)
        self.base = self.root / "baseline"
        self.base.mkdir()
        (self.base / "nodes.csv").write_text(build.nodes_to_csv(graph))
        (self.base / "edges.csv").write_text(build.edges_to_csv(graph))
        (self.base / "externals.csv").write_text(build.externals_to_csv(graph))
        (self.root / "none.txt").write_text("")
        self.plan_path = self.root / "plan.json"
        plan.save_plan(self.plan_path, good_plan())

    def run_main(self, edges, *extra):
        fresh = helpers.make_graph(edges, entries=["e1", "e2"], externals=EXTERNALS)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(check, "produce_graph", return_value=(fresh, self.root)), \
                mock.patch.object(check, "changed_files", return_value=(["Annotate.go"], True)):
            code = cli.main(["--graph-dir", str(self.base), "--source-root", str(self.root),
                             "--ignore-file", str(self.root / "none.txt"),
                             "check", "--plan", str(self.plan_path), "--scope", "svc", *extra],
                            out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_a_fixed_card_exits_zero_prints_ok_and_saves_the_result_next_to_the_plan(self):
        code, out, _ = self.run_main(AFTER_EDGES)

        saved = json.loads((self.root / "plan.check.json").read_text())
        self.assertEqual(code, 0)
        self.assertIn("check ok", out)
        self.assertEqual((saved["ok"], saved["plan_digest"]), (True, plan.digest(good_plan())))

    def test_a_card_that_remains_exits_one_and_saves_ok_false(self):
        code, out, _ = self.run_main(BEFORE_EDGES)

        self.assertEqual(code, 1)
        self.assertIn("E_CARD_REMAINS", out)
        self.assertFalse(json.loads((self.root / "plan.check.json").read_text())["ok"])

    def test_json_output_has_the_problems_and_the_data(self):
        code, out, _ = self.run_main(AFTER_EDGES, "--json")

        document = json.loads(out)
        self.assertEqual((code, document["ok"], document["data"]["card_gone"]), (0, True, True))

    def test_a_pipeline_failure_exits_two_with_the_message(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(check, "produce_graph", side_effect=check.CheckError("no codeql, push for CI")):
            code = cli.main(["--graph-dir", str(self.base), "--source-root", str(self.root),
                             "--ignore-file", str(self.root / "none.txt"),
                             "check", "--plan", str(self.plan_path)], out=out, err=err)

        self.assertEqual(code, 2)
        self.assertIn("push for CI", err.getvalue())


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.plan_path = self.root / "plan.json"
        self.approval = plan.approval_path_for(self.plan_path)
        self.check_path = self.root / "plan.check.json"
        self.review = self.root / "plan.review.json"

    def approve_plan(self, document=None):
        plan.save_plan(self.plan_path, document or good_plan())
        self.approval.write_text(json.dumps({"plan_digest": plan.digest(document or good_plan())}))

    def write_check(self, ok=True, document=None):
        self.check_path.write_text(json.dumps({"ok": ok, "plan_digest": plan.digest(document or good_plan())}))

    def review_approve(self):
        return plan.review_approve(self.plan_path, self.approval, self.check_path, self.review)

    def test_review_is_refused_when_the_plan_was_never_approved(self):
        plan.save_plan(self.plan_path, good_plan())
        self.write_check()

        with self.assertRaises(plan.PlanError) as caught:
            self.review_approve()

        self.assertIn("plan was not approved", str(caught.exception))

    def test_review_is_refused_without_a_passing_check_for_this_plan(self):
        self.approve_plan()

        with self.assertRaises(plan.PlanError) as missing:
            self.review_approve()
        self.write_check(ok=False)
        with self.assertRaises(plan.PlanError) as failed:
            self.review_approve()
        self.write_check(document={**good_plan(), "summary": "other"})
        with self.assertRaises(plan.PlanError) as stale:
            self.review_approve()

        self.assertIn("run check", str(missing.exception))
        self.assertIn("did not pass", str(failed.exception))
        self.assertIn("different plan", str(stale.exception))

    def test_review_is_recorded_when_plan_approved_and_check_passed(self):
        self.approve_plan()
        self.write_check()

        self.review_approve()

        self.assertEqual(json.loads(self.review.read_text())["plan_digest"], plan.digest(good_plan()))

    def test_review_does_not_survive_a_later_plan_edit(self):
        self.approve_plan()
        self.write_check()
        self.review_approve()

        plan.save_plan(self.plan_path, {**good_plan(), "summary": "edited"})

        self.assertEqual(plan.review_status(self.plan_path, self.review), "changed since review")

    def test_review_status_before_any_review_is_not_reviewed(self):
        plan.save_plan(self.plan_path, good_plan())

        self.assertEqual(plan.review_status(self.plan_path, self.review), "not reviewed")


if __name__ == "__main__":
    unittest.main()
