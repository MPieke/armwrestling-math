"""Render the call graph as Graphviz DOT and a GitHub-friendly Markdown summary."""

import argparse
import re
from collections import Counter
from pathlib import Path

from tools.callgraph import analyze, build

TOP_ROWS = 15
DEFAULT_MAX_FINDINGS = 10
DEFAULT_MAX_LISTED_ROWS = 2000  # keeps the summary far below GitHub's 1 MiB limit.


def source_url(repo_url, sha, file, start_line, end_line=None):
    anchor = f"#L{start_line}" if end_line is None else f"#L{start_line}-L{end_line}"
    return f"{repo_url}/blob/{sha}/{file}{anchor}"


def to_dot(graph, repo_url):
    """DOT text where every node and edge links to its source lines at the commit."""
    lines = ["digraph callgraph {", "  rankdir=LR;", '  node [shape=box, fontsize=10];']
    for node in graph.nodes:
        url = source_url(repo_url, node.sha, node.file, node.start_line, node.end_line)
        lines.append(
            f'  "{_dot(node.id)}" [label="{_dot(node.name)}\\n{_dot(node.package)}", '
            f'URL="{url}", tooltip="{_dot(node.file)}:{node.start_line}-{node.end_line}"];'
        )
    for edge in graph.edges:
        url = source_url(repo_url, edge.sha, edge.call_file, edge.call_line)
        lines.append(
            f'  "{_dot(edge.caller_id)}" -> "{_dot(edge.callee_id)}" '
            f'[URL="{url}", tooltip="{_dot(edge.call_file)}:{edge.call_line}"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def package_mermaid(graph):
    """Packages as nodes; edges labelled with the number of cross-package call sites."""
    package_of = {node.id: node.package for node in graph.nodes}
    counts = Counter(
        (package_of[edge.caller_id], package_of[edge.callee_id])
        for edge in graph.edges
        if package_of[edge.caller_id] != package_of[edge.callee_id]
    )
    lines = ["flowchart LR"]
    packages = sorted({node.package for node in graph.nodes})
    labels = _package_labels(packages)
    for package in packages:
        lines.append(f'  {_mermaid_id(package)}["{_mermaid_text(labels[package])}"]')
    for (source, target), count in sorted(counts.items()):
        lines.append(f"  {_mermaid_id(source)} -->|{count}| {_mermaid_id(target)}")
    return "\n".join(lines) + "\n"


def summary_markdown(
    graph,
    repo_url,
    analysis=None,
    max_findings=DEFAULT_MAX_FINDINGS,
    max_listed_rows=DEFAULT_MAX_LISTED_ROWS,
):
    packages = sorted({node.package for node in graph.nodes})
    labels = _package_labels(packages)
    sha = graph.nodes[0].sha if graph.nodes else "unknown"
    parts = [
        "## Go call graph",
        "",
        f"**{len(graph.nodes)} functions, {len(graph.edges)} call sites, "
        f"{len(packages)} packages** at `{sha[:7]}`",
        "",
    ]
    if analysis is not None:
        parts += _findings_section(graph, analysis, labels, repo_url, max_findings)
        parts += _dead_section(graph, analysis, labels, repo_url, max_listed_rows)
    parts += [
        "### Packages (cross-package call sites)",
        "",
        "```mermaid",
        package_mermaid(graph).rstrip(),
        "```",
        "",
    ]
    parts += _package_totals_table(graph, labels)
    if analysis is not None:
        parts += _external_section(analysis)
    called = Counter(edge.callee_id for edge in graph.edges)
    calling = Counter(edge.caller_id for edge in graph.edges)
    parts += _ranked_table("Most called functions", called, graph, repo_url)
    parts += _ranked_table("Most calls out", calling, graph, repo_url)
    parts += _never_called_table(graph, called, repo_url, max_listed_rows)
    parts += _functions_listing(graph, labels, repo_url, max_listed_rows)
    parts += _call_sites_listing(graph, labels, repo_url, max_listed_rows)
    return "\n".join(parts) + "\n"


class _Names:
    """Readable function names ("internal/pkg.Type.Method") and source links."""

    def __init__(self, graph, labels, repo_url):
        self.nodes = {node.id: node for node in graph.nodes}
        self.labels = labels
        self.repo_url = repo_url

    def display(self, node_id):
        node = self.nodes.get(node_id)
        if node is None:  # a collapsed cycle ("a+b") or similar label
            return node_id
        prefix = node.package + "."
        rest = node.id[len(prefix):] if node.id.startswith(prefix) else node.id
        return f"{self.labels[node.package]}.{rest}"

    def link(self, node_id):
        node = self.nodes.get(node_id)
        if node is None:
            return self.display(node_id)
        url = source_url(self.repo_url, node.sha, node.file, node.start_line, node.end_line)
        return f"[{_table_text(self.display(node_id))}]({url})"


def _plural(count, singular, plural):
    return f"{count} {singular if count == 1 else plural}"


def _findings_section(graph, analysis, labels, repo_url, max_findings):
    names = _Names(graph, labels, repo_url)
    out = [
        "### Redundant routes",
        "",
        "A terminal is a function that calls outside the code (database, network, files). "
        "*Independent routes* share no function between an entry point and the terminal; "
        "the gateways are the last functions where those routes are still separate, "
        "so they are the merge candidates. Reuse of a shared helper is normal: judge "
        "whether the gateways do the same job.",
        "",
    ]
    findings = analysis.findings
    if not findings:
        return out + ["No redundant routes found.", ""]
    shown = {}
    for rank, finding in enumerate(findings[:max_findings], start=1):
        out += _finding(rank, finding, names, shown)
    if len(findings) > max_findings:
        out += [f"_showing first {max_findings} of {len(findings)} flagged terminals; "
                "findings.json has the full list_", ""]
    return out


def _finding(rank, finding, names, shown):
    node = names.nodes[finding.terminal_id]
    head = (
        f"#### {rank}. `{_table_text(node.name)}` in `{names.labels[node.package]}` - "
        f"{finding.score} independent routes"
    )
    chokepoints = ", ".join(names.link(c) for c in finding.chokepoints) or "none"
    out = [
        head,
        "",
        f"{names.link(finding.terminal_id)} - {_plural(len(finding.entries), 'entry', 'entries')}, "
        f"{finding.paths} paths, chokepoints: {chokepoints}. "
        f"Calls: {', '.join(f'`{e}`' for e in finding.externals)}.",
        "",
    ]
    for segment in finding.segments:
        if segment.parallel:
            out += _segment_block(segment, names, "Routes")
    for nested in finding.nested:
        key = (nested.entry, nested.segment.start, nested.segment.end)
        label = f"Nested under `{names.display(nested.entry)}`"
        if key in shown:
            out += [f"**{label}**: same nested routes as #{shown[key]} "
                    f"({names.display(nested.segment.end)}).", ""]
            continue
        shown[key] = rank
        out += _segment_block(nested.segment, names, label)
    return out


def _segment_block(segment, names, title):
    start = names.display(segment.start) if segment.start else "entries"
    out = [f"**{title}** ({start} to {names.display(segment.end)}, {segment.k} independent):", ""]
    for gateway in segment.gateways:
        who = names.link(gateway.function_id) if gateway.function_id else "direct call"
        out.append(f"- gateway {who} - serves {_plural(gateway.entries, 'entry', 'entries')}")
    out.append("")
    for number, route in enumerate(segment.routes, start=1):
        chain = " > ".join(names.display(step) for step in route)
        out.append(f"{number}. {chain}")
    return out + [""]


def _dead_section(graph, analysis, labels, repo_url, max_rows):
    names = _Names(graph, labels, repo_url)
    out = [f"### Dead-code candidates ({len(analysis.dead)})", ""]
    if not analysis.dead:
        return out + ["None: every function is reachable from an entry point.", ""]
    out += [f"- {names.link(node_id)}" for node_id in analysis.dead[:max_rows]]
    return out + _truncation_note(len(analysis.dead), max_rows) + [""]


def _external_section(analysis):
    out = ["### Most used external functions", "",
           "| function | calling packages | calling functions |", "| --- | --- | --- |"]
    for usage in analysis.external_usage[:TOP_ROWS]:
        out.append(f"| {_table_text(usage.name)} | {usage.package_count} | {len(usage.callers)} |")
    suppressed = ", ".join(f"{pkg} ({count})" for pkg, count in analysis.suppressed.items())
    out += ["", f"Ignored external calls (noise filter): {suppressed or 'none'}.", ""]
    return out


def _package_totals_table(graph, labels):
    package_of = {node.id: node.package for node in graph.nodes}
    functions = Counter(node.package for node in graph.nodes)
    calls_out = Counter()
    calls_in = Counter()
    for edge in graph.edges:
        caller_package = package_of[edge.caller_id]
        callee_package = package_of[edge.callee_id]
        if caller_package != callee_package:
            calls_out[caller_package] += 1
            calls_in[callee_package] += 1
    rows = [
        "### Package totals",
        "",
        "| package | functions | calls out | calls in |",
        "| --- | --- | --- | --- |",
    ]
    for package in sorted(functions):
        rows.append(
            f"| {_table_text(labels[package])} | {functions[package]} | "
            f"{calls_out[package]} | {calls_in[package]} |"
        )
    return rows + [""]


def _function_link(node, repo_url):
    url = source_url(repo_url, node.sha, node.file, node.start_line, node.end_line)
    return f"[{_table_text(node.name)}]({url})"


def _ranked_table(title, counts, graph, repo_url):
    by_id = {node.id: node for node in graph.nodes}
    ranked = sorted(counts, key=lambda node_id: (-counts[node_id], by_id[node_id].name))
    rows = [f"### {title}", "", "| function | package | call sites |", "| --- | --- | --- |"]
    for node_id in ranked[:TOP_ROWS]:
        node = by_id[node_id]
        rows.append(
            f"| {_function_link(node, repo_url)} | {_table_text(node.package)} | {counts[node_id]} |"
        )
    return rows + [""]


def _never_called_table(graph, called, repo_url, max_rows):
    uncalled = [node for node in graph.nodes if node.id not in called]
    rows = [
        "### Never called (entry points or unused)",
        "",
        "| function | package |",
        "| --- | --- |",
    ]
    for node in uncalled[:max_rows]:
        rows.append(f"| {_function_link(node, repo_url)} | {_table_text(node.package)} |")
    return rows + _truncation_note(len(uncalled), max_rows) + [""]


def _functions_listing(graph, labels, repo_url, max_rows):
    rows = [
        f"<details><summary>All functions ({len(graph.nodes)})</summary>",
        "",
        "| function | package | lines |",
        "| --- | --- | --- |",
    ]
    for node in graph.nodes[:max_rows]:
        rows.append(
            f"| {_function_link(node, repo_url)} | {_table_text(labels[node.package])} | "
            f"{node.start_line}-{node.end_line} |"
        )
    return rows + _truncation_note(len(graph.nodes), max_rows) + ["", "</details>", ""]


def _call_sites_listing(graph, labels, repo_url, max_rows):
    by_id = {node.id: node for node in graph.nodes}

    def qualified(node):
        return _table_text(f"{labels[node.package]}.{node.name}")

    rows = [
        f"<details><summary>All call sites ({len(graph.edges)})</summary>",
        "",
        "| caller | callee | call site |",
        "| --- | --- | --- |",
    ]
    for edge in graph.edges[:max_rows]:
        url = source_url(repo_url, edge.sha, edge.call_file, edge.call_line)
        rows.append(
            f"| {qualified(by_id[edge.caller_id])} | {qualified(by_id[edge.callee_id])} | "
            f"[{_table_text(edge.call_file)}:{edge.call_line}]({url}) |"
        )
    return rows + _truncation_note(len(graph.edges), max_rows) + ["", "</details>", ""]


def _truncation_note(total, max_rows):
    if total <= max_rows:
        return []
    return ["", f"_showing first {max_rows} of {total}; the artifact has the full list_"]


def _package_labels(packages):
    """Short labels: the import path minus the leading directories all packages share."""
    split = {package: package.split("/") for package in packages}
    shared = _shared_leading_segments([parts[:-1] for parts in split.values()])
    return {package: "/".join(parts[shared:]) for package, parts in split.items()}


def _shared_leading_segments(directory_lists):
    shared = 0
    for segments in zip(*directory_lists):
        if len(set(segments)) != 1:
            break
        shared += 1
    return shared


def _dot(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _mermaid_id(text):
    return re.sub(r"\W", "_", text)


def _mermaid_text(text):
    return text.replace('"', "#quot;")


def _table_text(text):
    return text.replace("|", "\\|")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render call graph CSVs to DOT and Markdown.")
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument("--repo-url", required=True, help="e.g. https://github.com/owner/repo")
    parser.add_argument("--ignore-file", type=Path, default=analyze.DEFAULT_IGNORE_FILE)
    parser.add_argument("--min-entries", type=int, default=2)
    parser.add_argument("--min-gateways", type=int, default=2)
    parser.add_argument("--max-findings", type=int, default=DEFAULT_MAX_FINDINGS)
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
    (args.graph_dir / "callgraph.dot").write_text(to_dot(graph, args.repo_url))
    (args.graph_dir / "summary.md").write_text(
        summary_markdown(graph, args.repo_url, analysis=analysis, max_findings=args.max_findings)
    )
    print(f"wrote callgraph.dot and summary.md to {args.graph_dir}")


if __name__ == "__main__":
    main()
