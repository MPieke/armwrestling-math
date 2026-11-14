"""Check the call graph analysis against the actual source, independently of CodeQL.

Hard checks (a failure means the graph does not match the source):

* M1 every edge's call line contains the callee's name
* M2 every external call's line contains the external function's name
* M3 every node starts on a ``func`` declaration of that name

Soft checks (reported as notes for a reviewer; text search is heuristic):

* M4 a ``referenced`` entry is mentioned somewhere other than a call
* M5 call-like text for a flagged terminal or its external functions that the
  graph does not explain (possible missed route)
* M6 flagged routes that rely on dynamic-dispatch edges

``dossier_markdown`` lays out every hop of the top findings with the code around
it so a reviewer can compare the analysis with the source line by line.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from tools.callgraph import analyze, build
from tools.callgraph.render import source_url

CENSUS_LIMIT = 20


@dataclass(frozen=True)
class Failure:
    check: str
    location: str
    message: str


@dataclass(frozen=True)
class Note:
    check: str
    subject: str
    message: str


@dataclass
class Report:
    checked: dict = field(default_factory=lambda: {"M1": 0, "M2": 0, "M3": 0})
    hard_failures: list = field(default_factory=list)
    notes: list = field(default_factory=list)


class _Source:
    """Lazy, cached access to source files under a root."""

    def __init__(self, root):
        self.root = Path(root)
        self._cache = {}

    def lines(self, file):
        if file not in self._cache:
            try:
                self._cache[file] = (self.root / file).read_text(errors="replace").splitlines()
            except OSError:
                self._cache[file] = None
        return self._cache[file]

    def line(self, file, number):
        """The text of a 1-based line, or None if the file or line does not exist."""
        lines = self.lines(file)
        if lines is None or not 1 <= number <= len(lines):
            return None
        return lines[number - 1]


def _word(name):
    return rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"


def _short_name(qualified):
    return qualified.rsplit(".", 1)[-1]


def mechanical_checks(graph, source_root, analysis):
    source = _Source(source_root)
    report = Report()
    nodes = {node.id: node for node in graph.nodes}
    _check_edges(graph, nodes, source, report)
    _check_externals(graph, source, report)
    _check_nodes(graph, source, report)
    _check_referenced_entries(graph, source, report)
    _census(graph, analysis, source, report)
    _dynamic_hops(graph, analysis, report)
    return report


def _check_line(report, check, file, number, pattern, what, source):
    report.checked[check] += 1
    text = source.line(file, number)
    location = f"{file}:{number}"
    if source.lines(file) is None:
        report.hard_failures.append(Failure(check, location, f"cannot read {file}"))
    elif text is None:
        report.hard_failures.append(
            Failure(check, location, f"{file} has no line {number} (beyond end of file)")
        )
    elif not re.search(pattern, text):
        report.hard_failures.append(
            Failure(check, location, f"{what} not found on {location}: {text.strip()}")
        )


def _check_edges(graph, nodes, source, report):
    for edge in graph.edges:
        callee = nodes[edge.callee_id]
        _check_line(
            report, "M1", edge.call_file, edge.call_line, _word(callee.name),
            f"call to {callee.name}", source,
        )


def _check_externals(graph, source, report):
    for call in graph.externals:
        short = _short_name(call.external_name)
        _check_line(
            report, "M2", call.call_file, call.call_line, _word(short),
            f"call to {call.external_name}", source,
        )


def _check_nodes(graph, source, report):
    for node in graph.nodes:
        pattern = rf"^\s*func\b.*{_word(node.name)}"
        _check_line(
            report, "M3", node.file, node.start_line, pattern,
            f"declaration of {node.name}", source,
        )


def _scope_files(graph):
    return sorted({node.file for node in graph.nodes})


def _non_call_mentions(graph, source, node):
    """Lines (other than the declaration) that mention the function without calling it."""
    pattern = re.compile(_word(node.name) + r"(?!\s*\()")
    mentions = []
    for file in _scope_files(graph):
        for number, text in enumerate(source.lines(file) or [], start=1):
            if file == node.file and number == node.start_line:
                continue
            if pattern.search(text):
                mentions.append((file, number))
    return mentions


def _check_referenced_entries(graph, source, report):
    for node in graph.nodes:
        if node.root_kind == "referenced" and not _non_call_mentions(graph, source, node):
            report.notes.append(
                Note("M4", node.name,
                     f"{node.id} is classified as referenced but no non-call mention was found")
            )


def _call_hits(graph, source, name):
    """(file, line) pairs where ``name(`` appears, ignoring the function's own declaration."""
    declaration = re.compile(rf"^\s*func\s+(\([^)]*\)\s*)?{re.escape(name)}\s*\(")
    call = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*\(")
    hits = set()
    for file in _scope_files(graph):
        for number, text in enumerate(source.lines(file) or [], start=1):
            if call.search(declaration.sub("(", text)):
                hits.add((file, number))
    return hits


def _census(graph, analysis, source, report):
    nodes = {node.id: node for node in graph.nodes}
    for finding in analysis.findings:
        terminal = nodes[finding.terminal_id]
        explained = {(e.call_file, e.call_line) for e in graph.edges
                     if e.callee_id == finding.terminal_id}
        _report_unexplained(report, graph, source, terminal.name, explained, finding.terminal_id)
        for external in finding.externals:
            explained = {(c.call_file, c.call_line) for c in graph.externals
                         if c.external_name == external}
            _report_unexplained(
                report, graph, source, _short_name(external), explained, external
            )


def _report_unexplained(report, graph, source, name, explained, subject):
    unexplained = sorted(_call_hits(graph, source, name) - explained)
    for file, number in unexplained[:CENSUS_LIMIT]:
        text = source.line(file, number).strip()
        report.notes.append(
            Note("M5", subject,
                 f"call-like text at {file}:{number} is not in the graph: {text}")
        )


def _dynamic_hops(graph, analysis, report):
    resolution = {(e.caller_id, e.callee_id): e.resolution for e in graph.edges}
    for finding in analysis.findings:
        dynamic = {
            (a, b)
            for segment in finding.segments
            for route in segment.routes
            for a, b in zip(route, route[1:])
            if resolution.get((a, b)) == "dynamic"
        }
        if dynamic:
            report.notes.append(
                Note("M6", finding.terminal_id,
                     f"{len(dynamic)} dynamic-dispatch hop(s) on flagged routes")
            )


def dossier_markdown(graph, analysis, source_root, repo_url, top=5, context=2):
    source = _Source(source_root)
    nodes = {node.id: node for node in graph.nodes}
    call_sites = {}
    for edge in graph.edges:
        call_sites.setdefault((edge.caller_id, edge.callee_id), []).append(edge)
    sha = graph.nodes[0].sha if graph.nodes else "unknown"
    out = [
        "# Route verification dossier",
        "",
        f"Commit `{sha[:7]}`. For each finding, compare every hop with the source before "
        "trusting the analysis.",
        "",
    ]
    if not analysis.findings:
        return "\n".join(out + ["No flagged terminals."]) + "\n"
    for rank, finding in enumerate(analysis.findings[:top], start=1):
        out += _finding_section(
            rank, finding, graph, nodes, call_sites, source, repo_url, context
        )
    return "\n".join(out) + "\n"


def _finding_section(rank, finding, graph, nodes, call_sites, source, repo_url, context):
    terminal = nodes[finding.terminal_id]
    out = [
        f"## {rank}. `{terminal.name}` - {finding.score} independent routes",
        "",
        f"`{terminal.id}` ({terminal.file}:{terminal.start_line}); "
        f"{len(finding.entries)} entries, {finding.paths} paths, "
        f"chokepoints: {', '.join(finding.chokepoints) or 'none'}.",
        "",
        "### Terminal external calls",
        "",
    ]
    for call in graph.externals:
        if call.caller_id == finding.terminal_id:
            out += [f"`{call.external_name}` at {call.call_file}:{call.call_line}", ""]
            out += _excerpt(source, call.call_file, call.call_line, context)
    out += ["### Entries", ""]
    for entry_id in finding.entries:
        entry = nodes[entry_id]
        out += [f"`{entry.id}` ({entry.root_kind})", ""]
        for file, number in _non_call_mentions(graph, source, entry):
            out += [f"referenced at {file}:{number}", ""]
            out += _excerpt(source, file, number, context)
    for segment in finding.segments:
        if not segment.parallel:
            continue
        label = f"{segment.start or 'entries'} -> {segment.end}"
        out += [f"### Routes {label} (K={segment.k})", ""]
        for number, route in enumerate(segment.routes, start=1):
            out += [f"**Route {number}**: {' > '.join(route)}", ""]
            for caller, callee in zip(route, route[1:]):
                out += _hop(caller, callee, call_sites, source, repo_url, context)
    return out


def _hop(caller, callee, call_sites, source, repo_url, context):
    edges = call_sites.get((caller, callee))
    if not edges:
        return [f"#### {caller} -> {callee} (collapsed cycle, no single call site)", ""]
    edge = edges[0]
    marker = " [dynamic dispatch]" if edge.resolution == "dynamic" else ""
    extra = f" (+{len(edges) - 1} more call sites)" if len(edges) > 1 else ""
    url = source_url(repo_url, edge.sha, edge.call_file, edge.call_line)
    head = f"#### {caller} -> {callee} at {edge.call_file}:{edge.call_line}{marker}{extra}"
    return [head, "", f"[view on GitHub]({url})", ""] + _excerpt(
        source, edge.call_file, edge.call_line, context
    )


def _excerpt(source, file, number, context):
    lines = source.lines(file)
    if lines is None:
        return [f"(cannot read {file})", ""]
    first, last = max(1, number - context), min(len(lines), number + context)
    body = [
        f"{'>' if current == number else ' '} {current} | {lines[current - 1].replace(chr(9), '    ')}"
        for current in range(first, last + 1)
    ]
    return ["```", *body, "```", ""]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify the call graph analysis against source.")
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--ignore-file", type=Path, default=analyze.DEFAULT_IGNORE_FILE)
    parser.add_argument("--min-entries", type=int, default=2)
    parser.add_argument("--min-gateways", type=int, default=2)
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args(argv)

    externals = args.graph_dir / "externals.csv"
    graph = build.load_graph(
        (args.graph_dir / "nodes.csv").read_text(),
        (args.graph_dir / "edges.csv").read_text(),
        externals.read_text() if externals.exists() else None,
    )
    analysis = analyze.analyze(
        graph,
        ignored_packages=analyze.parse_ignore_file(args.ignore_file.read_text()),
        min_entries=args.min_entries,
        min_gateways=args.min_gateways,
    )
    report = mechanical_checks(graph, args.source_root, analysis)
    (args.graph_dir / "dossier.md").write_text(
        dossier_markdown(graph, analysis, args.source_root, args.repo_url, top=args.top)
    )
    (args.graph_dir / "verification.json").write_text(
        json.dumps(
            {
                "checked": report.checked,
                "hard_failures": [vars(f) for f in report.hard_failures],
                "notes": [vars(n) for n in report.notes],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(
        f"checked {report.checked}; {len(report.hard_failures)} hard failures, "
        f"{len(report.notes)} notes for review"
    )
    for failure in report.hard_failures[:20]:
        print(f"FAIL {failure.check} {failure.location}: {failure.message}")
    return 1 if report.hard_failures else 0


if __name__ == "__main__":
    sys.exit(main())
