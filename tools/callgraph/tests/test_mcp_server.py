import asyncio
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tools.callgraph import build, cli, mcp_server, plan
from tools.callgraph.tests import helpers
from tools.callgraph.tests.test_plan import EDGES, TEST_A, TEST_B, good_plan
from tools.callgraph.tests.test_render import SOURCE_ANNOTATE, SOURCE_EXTRACT, judged

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_EXAMPLE = REPO_ROOT / "tools" / "callgraph" / "claude-settings.example.json"
AUTOMATIC = {"findings", "card", "plan_init", "plan_lint", "plan_diagram", "plan_tests", "plan_status", "check"}
GATED = {"plan_approve", "plan_review"}


class Workspace(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "Annotate.go").write_text(SOURCE_ANNOTATE)
        (self.root / "Extract.go").write_text(SOURCE_EXTRACT)
        (self.root / "Annotate_test.go").write_text(TEST_A)
        (self.root / "Extract_test.go").write_text(TEST_B)
        (self.root / "none.txt").write_text("")
        graph = helpers.make_graph(EDGES, entries=["e1", "e2"], externals=[("t", "os.Open")])
        self.graph_dir = self.root / "graph"
        self.graph_dir.mkdir()
        (self.graph_dir / "nodes.csv").write_text(build.nodes_to_csv(graph))
        (self.graph_dir / "edges.csv").write_text(build.edges_to_csv(graph))
        (self.graph_dir / "externals.csv").write_text(build.externals_to_csv(graph))
        (self.graph_dir / "judgements.json").write_text(json.dumps(
            {"status": "ok", "judgements": [judged("Annotate", "Extract")], "calibration": None}))
        self.plan_path = self.root / "plan.json"
        self.context = mcp_server.Context(
            graph_dir=self.graph_dir, source_root=self.root, ignore_file=self.root / "none.txt",
            plan=self.plan_path,
        )

    def cli_output(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        cli.main(["--graph-dir", str(self.graph_dir), "--source-root", str(self.root),
                  "--ignore-file", str(self.root / "none.txt"), *argv], out=out, err=err)
        return out.getvalue()


class RegistryTest(unittest.TestCase):
    def test_the_tools_are_the_automatic_ones_plus_the_two_checkpoints(self):
        self.assertEqual({t.name for t in mcp_server.TOOLS}, AUTOMATIC | GATED)

    def test_only_the_two_checkpoint_tools_are_gated(self):
        self.assertEqual({t.name for t in mcp_server.TOOLS if t.gated}, GATED)

    def test_a_gated_tool_says_in_its_description_that_it_needs_the_developer(self):
        for tool in mcp_server.TOOLS:
            starts = tool.description.startswith("REQUIRES THE DEVELOPER'S APPROVAL")
            self.assertEqual(starts, tool.gated, tool.name)

    def test_every_tool_has_a_description(self):
        self.assertTrue(all(len(t.description) > 20 for t in mcp_server.TOOLS))

    def test_the_example_settings_allow_the_automatic_tools_and_never_the_gated_ones(self):
        settings = json.loads(SETTINGS_EXAMPLE.read_text())["permissions"]

        self.assertEqual(set(settings["allow"]), {f"mcp__callgraph__{n}" for n in AUTOMATIC})
        self.assertEqual(set(settings["ask"]), {f"mcp__callgraph__{n}" for n in GATED})


class RunToolTest(Workspace):
    def test_findings_is_exactly_what_the_cli_prints(self):
        self.assertEqual(mcp_server.run_tool("findings", {}, self.context), self.cli_output("findings"))

    def test_card_is_exactly_what_the_cli_prints(self):
        self.assertEqual(mcp_server.run_tool("card", {"ref": "1"}, self.context), self.cli_output("card", "1"))

    def test_a_missing_required_argument_is_named(self):
        self.assertIn("ref", mcp_server.run_tool("card", {}, self.context))

    def test_an_unknown_tool_is_reported(self):
        self.assertIn("unknown tool", mcp_server.run_tool("rm_rf", {}, self.context))

    def test_a_cli_error_comes_back_as_text_with_the_exit_code(self):
        text = mcp_server.run_tool("card", {"ref": "99"}, self.context)

        self.assertIn("no card", text)
        self.assertIn("exit code 2", text)

    def test_plan_tools_work_on_the_configured_plan_path_from_draft_to_approval(self):
        init = mcp_server.run_tool("plan_init", {"ref": "1"}, self.context)
        draft = mcp_server.run_tool("plan_lint", {}, self.context)
        plan.save_plan(self.plan_path, good_plan())
        clean = mcp_server.run_tool("plan_lint", {}, self.context)
        approved = mcp_server.run_tool("plan_approve", {}, self.context)
        status = mcp_server.run_tool("plan_status", {}, self.context)

        self.assertIn("wrote", init)
        self.assertIn("E_DIFF_UNHANDLED", draft)
        self.assertIn("exit code 1", draft)
        self.assertIn("plan ok", clean)
        self.assertIn("approved plan", approved)
        self.assertIn("approval: approved", status)

    def test_init_refuses_to_overwrite_unless_forced(self):
        mcp_server.run_tool("plan_init", {"ref": "1"}, self.context)

        again = mcp_server.run_tool("plan_init", {"ref": "1"}, self.context)
        forced = mcp_server.run_tool("plan_init", {"ref": "1", "force": True}, self.context)

        self.assertIn("already exists", again)
        self.assertIn("wrote", forced)

    def test_diagram_and_tests_tools_return_what_the_cli_returns(self):
        plan.save_plan(self.plan_path, good_plan())

        self.assertIn("```mermaid", mcp_server.run_tool("plan_diagram", {}, self.context))
        self.assertIn("TestPinnedText_Annotate", mcp_server.run_tool("plan_tests", {}, self.context))


@unittest.skipUnless(importlib.util.find_spec("mcp"), "the mcp SDK is not installed (requirements-mcp.txt)")
class HandshakeTest(Workspace):
    def run_async(self, coroutine):
        return asyncio.run(asyncio.wait_for(coroutine, timeout=60))

    async def session_call(self, name=None, arguments=None):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "tools.callgraph.mcp_server", "--graph-dir", str(self.graph_dir),
                  "--source-root", str(self.root), "--ignore-file", str(self.root / "none.txt"),
                  "--plan", str(self.plan_path)],
            cwd=REPO_ROOT,
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                result = await session.call_tool(name, arguments or {}) if name else None
                return listed, result

    def test_the_server_lists_every_tool_and_marks_the_gated_ones_not_read_only(self):
        listed, _ = self.run_async(self.session_call())

        by_name = {tool.name: tool for tool in listed.tools}
        self.assertEqual(set(by_name), AUTOMATIC | GATED)
        for name in GATED:
            self.assertFalse(by_name[name].annotations.read_only_hint, name)
        self.assertTrue(by_name["findings"].annotations.read_only_hint)

    def test_calling_findings_over_stdio_returns_the_cli_text(self):
        _, result = self.run_async(self.session_call("findings"))

        text = "".join(block.text for block in result.content)
        self.assertEqual(text, self.cli_output("findings"))


if __name__ == "__main__":
    unittest.main()
