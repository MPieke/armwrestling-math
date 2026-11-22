"""An MCP server that gives a coding agent the callgraph commands as tools.

It is a thin wrapper: every tool runs the same code as the matching ``cli`` command and returns
its text, so the CLI and the tools cannot drift apart. No LLM is called here.

Two tools record the developer's decisions (``plan_approve`` and ``plan_review``). The server
cannot know whether a human really agreed; that is enforced by the agent's harness. Leave those
two out of the allow-list so the developer is asked each time (see claude-settings.example.json).

    python -m tools.callgraph.mcp_server --graph-dir DIR --source-root . --scope services/importer
"""

import argparse
import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

from tools.callgraph import analyze, cli, plan

GATED_PREFIX = "REQUIRES THE DEVELOPER'S APPROVAL: do not call this unless the developer has said yes in this conversation. "

INSTRUCTIONS = (
    "Deterministic facts about redundancy cards in a Go codebase (no LLM). Typical order: "
    "findings, card N, then write a plan (plan_init, edit .callgraph/plan.json), plan_lint, "
    "plan_diagram, show the developer, and only after they agree plan_approve. Then implement, "
    "run plan_tests and the repository's tests, check, and only after the developer reviews the "
    "result plan_review. Differences in moved steps must each be decided in the plan."
)


@dataclass(frozen=True)
class Context:
    graph_dir: Path
    source_root: Path = Path(".")
    ignore_file: Path = analyze.DEFAULT_IGNORE_FILE
    plan: Path = plan.DEFAULT_PLAN
    scope: str = ""
    judgements: Path = None
    database: Path = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    arguments: tuple  # names of required text arguments
    argv: object  # (arguments, context) -> the cli arguments after the shared options
    gated: bool = False
    read_only: bool = False


def _plan(context, *rest):
    return ["plan", "--plan", str(context.plan), *rest]


TOOLS = (
    Tool("findings", "List the redundancy cards (number, level, pair, the model's action if any).",
         (), lambda a, c: ["findings"], read_only=True),
    Tool("card", "Facts for one card: callers, tests found by name, test gaps, differences inside the "
                 "steps the model called the same, evidence, and the model's advisory suggestion. "
                 "ref is the card number or first~second.",
         ("ref",), lambda a, c: ["card", a["ref"]], read_only=True),
    Tool("plan_init", "Write a draft fix plan for a card (steps and fix from the model when judged, every "
                      "difference left undecided). Set force to replace an existing plan.",
         ("ref",), lambda a, c: _plan(c, "init", a["ref"], *(["--force"] if a.get("force") else []))),
    Tool("plan_lint", "Check the plan against the code: schema, step ranges, moved steps, a decision for "
                      "every difference in a moved step, planned files versus will_not_touch, tests.",
         (), lambda a, c: _plan(c, "lint"), read_only=True),
    Tool("plan_diagram", "Mermaid pictures of the two functions' steps before and after the planned move.",
         (), lambda a, c: _plan(c, "diagram"), read_only=True),
    Tool("plan_tests", "Skipped Go test skeletons that pin today's text differences, plus stubs for the "
                       "tests the plan promises.",
         (), lambda a, c: _plan(c, "tests"), read_only=True),
    Tool("plan_status", "Whether the plan is approved and unchanged since, and whether the work was reviewed.",
         (), lambda a, c: _plan(c, "status"), read_only=True),
    Tool("check", "Re-run the analysis on the working tree and compare with the baseline: is the card gone, "
                  "any new cards, did the changes stay inside the plan. Does not run the repository's tests.",
         (), lambda a, c: ["check", "--plan", str(c.plan), "--scope", c.scope,
                           *(["--database", str(c.database)] if c.database else [])]),
    Tool("plan_approve", GATED_PREFIX + "Record that the developer approved the plan (checkpoint 1). "
                         "Refused while the plan has lint errors.",
         (), lambda a, c: _plan(c, "approve"), gated=True),
    Tool("plan_review", GATED_PREFIX + "Record that the developer reviewed the finished work (checkpoint 2). "
                        "Refused unless the plan is approved and the last check passed for this plan.",
         (), lambda a, c: _plan(c, "review"), gated=True),
)
_BY_NAME = {tool.name: tool for tool in TOOLS}


def run_tool(name, arguments, context):
    """Run one tool and return its text: the CLI output, errors, and a non-zero exit code."""
    tool = _BY_NAME.get(name)
    if tool is None:
        return f"unknown tool {name!r}; available: {', '.join(_BY_NAME)}\n"
    arguments = dict(arguments or {})
    for required in tool.arguments:
        if not str(arguments.get(required, "")).strip():
            return f"missing argument {required!r} for {name}\n"
        arguments[required] = str(arguments[required])
    shared = ["--graph-dir", str(context.graph_dir), "--source-root", str(context.source_root),
              "--ignore-file", str(context.ignore_file)]
    if context.judgements:
        shared += ["--judgements", str(context.judgements)]
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            code = cli.main(shared + tool.argv(arguments, context), out=out, err=err)
    except SystemExit as stop:  # argparse rejected the arguments
        code = stop.code if isinstance(stop.code, int) else 2
    text = out.getvalue() + err.getvalue()
    return text + (f"exit code {code}\n" if code else "")


def build_server(context):
    from mcp.server.mcpserver import MCPServer  # imported late: the SDK is optional
    from mcp.types import ToolAnnotations

    server = MCPServer("callgraph", instructions=INSTRUCTIONS)

    def findings() -> str:
        return run_tool("findings", {}, context)

    def card(ref: str) -> str:
        return run_tool("card", {"ref": ref}, context)

    def plan_init(ref: str, force: bool = False) -> str:
        return run_tool("plan_init", {"ref": ref, "force": force}, context)

    def plan_lint() -> str:
        return run_tool("plan_lint", {}, context)

    def plan_diagram() -> str:
        return run_tool("plan_diagram", {}, context)

    def plan_tests() -> str:
        return run_tool("plan_tests", {}, context)

    def plan_status() -> str:
        return run_tool("plan_status", {}, context)

    def check() -> str:
        return run_tool("check", {}, context)

    def plan_approve() -> str:
        return run_tool("plan_approve", {}, context)

    def plan_review() -> str:
        return run_tool("plan_review", {}, context)

    functions = {f.__name__: f for f in (findings, card, plan_init, plan_lint, plan_diagram, plan_tests,
                                         plan_status, check, plan_approve, plan_review)}
    for tool in TOOLS:
        annotations = ToolAnnotations(read_only_hint=tool.read_only, destructive_hint=False)
        server.tool(name=tool.name, description=tool.description, annotations=annotations)(functions[tool.name])
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--graph-dir", required=True, type=Path, help="baseline graph (e.g. the CI artifact)")
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--ignore-file", type=Path, default=analyze.DEFAULT_IGNORE_FILE)
    parser.add_argument("--plan", type=Path, default=plan.DEFAULT_PLAN)
    parser.add_argument("--scope", default="", help="repo path the graph covers, e.g. services/importer")
    parser.add_argument("--judgements", type=Path)
    parser.add_argument("--database", type=Path, help="reuse an existing CodeQL database for check")
    args = parser.parse_args(argv)
    context = Context(args.graph_dir, args.source_root, args.ignore_file, args.plan, args.scope,
                      args.judgements, args.database)
    build_server(context).run("stdio")


if __name__ == "__main__":
    main()
