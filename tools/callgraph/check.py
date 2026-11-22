"""Re-run the call graph analysis on the working tree and compare it with the baseline.

``check`` answers one question for a fix plan: did the redundancy card go away without new
ones appearing, and did the changes stay inside what the plan said? It runs the same CodeQL
queries as CI, so a clean local check predicts a clean CI run. It does not run the
repository's tests and cannot show that behaviour is preserved; the report says so.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from tools.callgraph import analyze, build, cli, plan

CODEQL_DIR = Path(__file__).resolve().parents[2] / "codeql"
QUERIES = ("nodes", "edges", "externals")
MAX_LISTED_FILES = 10
_TEST_FUNCTION = re.compile(r"^func (Test\w*)\(", re.MULTILINE)

Problem = plan.Problem


class CheckError(Exception):
    """The check could not run (no CodeQL, a failing command); printed without a traceback."""


@dataclass(frozen=True)
class Report:
    problems: tuple
    data: dict

    @property
    def ok(self):
        return not any(p.level == "error" for p in self.problems)


def default_runner(argv, cwd=None):
    argv = [str(a) for a in argv]
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise CheckError(f"{argv[0]} is not installed here; push and let CI check instead") from error
    if done.returncode != 0:
        tail = (done.stderr or done.stdout).strip()[-400:]
        raise CheckError(f"{' '.join(argv[:3])} failed (exit {done.returncode}): {tail}")
    return done.stdout


def produce_graph(source_root, work_dir, scope="", database=None, runner=None, codeql_dir=None):
    """Extract and stamp the call graph for the working tree, like the CI steps do."""
    runner = runner or default_runner
    codeql_dir = codeql_dir or CODEQL_DIR
    source_root, work_dir = Path(source_root), Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)  # codeql will not create the parent of the database
    sha = runner(["git", "rev-parse", "HEAD"], cwd=source_root).strip()
    if database is None:
        database = work_dir / "db"
        runner(["codeql", "database", "create", database, "--language=go",
                f"--source-root={source_root}", "--overwrite"])
    raw = work_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for query in QUERIES:
        runner(["codeql", "query", "run", f"--database={database}", f"--output={raw / (query + '.bqrs')}",
                f"go/{query}.ql"], cwd=codeql_dir)
        runner(["codeql", "bqrs", "decode", "--format=csv", f"--output={raw / (query + '.csv')}",
                raw / (query + ".bqrs")])
    try:
        graph = build.build_graph(
            (raw / "nodes.csv").read_text(), (raw / "edges.csv").read_text(), sha,
            include_prefixes=(scope,) if scope else (),
            externals_csv=(raw / "externals.csv").read_text(),
        )
    except build.GraphError as error:
        raise CheckError(f"the query output is not a valid graph: {error}") from error
    if not graph.nodes:
        raise CheckError(f"no functions found under {scope!r}; check --scope")
    graph_dir = work_dir / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "nodes.csv").write_text(build.nodes_to_csv(graph))
    (graph_dir / "edges.csv").write_text(build.edges_to_csv(graph))
    (graph_dir / "externals.csv").write_text(build.externals_to_csv(graph))
    return graph, graph_dir


def changed_files(source_root, base_sha, runner=None):
    """(files, base_known): tracked files changed since the baseline commit, plus new files."""
    runner = runner or default_runner
    try:
        runner(["git", "cat-file", "-e", f"{base_sha}^{{commit}}"], cwd=source_root)
        base, known = base_sha, True
    except CheckError:
        base, known = "HEAD", False
    changed = runner(["git", "diff", "--name-only", base], cwd=source_root).splitlines()
    new = runner(["git", "ls-files", "--others", "--exclude-standard"], cwd=source_root).splitlines()
    return sorted({f for f in changed + new if f}), known


def run(document, baseline, source_root, work_dir, scope="", database=None, ignored=(), runner=None):
    graph, _ = produce_graph(source_root, work_dir, scope, database, runner)
    fresh = cli.build_session(graph, analyze.analyze(graph, ignored_packages=ignored), None, source_root, ignored)
    base_sha = baseline.graph.nodes[0].sha if baseline.graph.nodes else "HEAD"
    files, known = changed_files(source_root, base_sha, runner)
    return compare(document, baseline, fresh, files, known)


def compare(document, baseline, fresh, changed, base_known=True):
    ref = document["card"]
    before = {e.ref: e for e in baseline.entries}
    after = {e.ref: e for e in fresh.entries}
    problems = []
    gone = ref not in after
    if ref not in before:
        problems.append(Problem("warning", "W_NOT_IN_BASELINE",
                                f"card {ref} is not among the baseline cards, so there is nothing to compare"))
    elif not gone:
        problems.append(Problem("error", "E_CARD_REMAINS", f"card {ref} is still reported after the change"))
    missing = [f for f in ref.split("~") if f not in fresh.names.nodes]
    if missing:
        problems.append(Problem(
            "note", "N_FUNCTION_GONE",
            f"{', '.join(missing)} no longer exists, which may be why the card is gone; "
            "that counts as a fix only if merging them was the plan",
        ))
    for new_ref in sorted(set(after) - set(before)):
        level = after[new_ref].card.evidence.level if after[new_ref].card.kind == "pair" else "two routes"
        problems.append(Problem("error", "E_NEW_CARD", f"the change introduces a new card {new_ref} ({level})"))
    problems += _change_problems(document, baseline, fresh, changed)
    problems += _test_problems(document, fresh)
    if not base_known:
        problems.append(Problem(
            "warning", "W_BASE_UNKNOWN",
            "the baseline commit is not in this checkout, so changes were measured against HEAD; "
            "fetch it to see everything this branch changed",
        ))
    problems.append(Problem(
        "note", "N_NOT_VERIFIED",
        "this check does not run the repository's tests and cannot show that behaviour is preserved; "
        "run the tests, including any that need external services",
    ))
    data = {
        "card": ref, "card_gone": gone, "new_cards": sorted(set(after) - set(before)),
        "changed_files": list(changed), "baseline_total": len(before), "fresh_total": len(after),
    }
    return Report(tuple(problems), data)


def _change_problems(document, baseline, fresh, changed):
    nodes = {**baseline.names.nodes, **fresh.names.nodes}
    forbidden = [nodes[e].file if e in nodes else e for e in document["will_not_touch"]]
    problems, outside = [], []
    for path in changed:
        hit = next((f for f in forbidden if plan.path_under(path, f)), None)
        if hit is not None:
            problems.append(Problem("error", "E_WILL_NOT_TOUCH_CHANGED",
                                    f"{path} changed but the plan said not to touch {hit}"))
        elif not path.endswith("_test.go") and not any(plan.path_under(path, p) for p in document["planned_files"]):
            outside.append(path)
    if outside:
        shown = ", ".join(outside[:MAX_LISTED_FILES])
        more = f" and {len(outside) - MAX_LISTED_FILES} more" if len(outside) > MAX_LISTED_FILES else ""
        problems.append(Problem("warning", "W_OUTSIDE_PLAN", f"changed but not in planned_files: {shown}{more}"))
    return problems


def _test_problems(document, fresh):
    files = fresh.names.files
    if files is None or not document["tests"]:
        return []
    scope = Path(files.root) / fresh.names.scope_dir
    defined = set()
    for path in scope.rglob("*_test.go") if scope.is_dir() else []:
        try:
            defined |= set(_TEST_FUNCTION.findall(path.read_text(errors="replace")))
        except OSError:
            continue
    missing = [name for name in document["tests"] if name not in defined]
    if not missing:
        return []
    return [Problem("warning", "W_PLANNED_TEST_MISSING", f"planned tests not found: {', '.join(missing)}")]


def report_text(report):
    errors = sum(p.level == "error" for p in report.problems)
    warnings = sum(p.level == "warning" for p in report.problems)
    head = "check ok" if report.ok else f"check failed ({errors} errors)"
    lines = [f"{head}; card gone: {'yes' if report.data['card_gone'] else 'no'}, "
             f"cards {report.data['baseline_total']} -> {report.data['fresh_total']}, "
             f"{warnings} warnings"]
    lines += [f"{p.level} {p.code}: {p.message}" for p in report.problems]
    return "\n".join(lines) + "\n"

