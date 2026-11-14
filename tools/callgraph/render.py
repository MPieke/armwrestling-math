"""Render the call graph as Graphviz DOT and a GitHub-friendly Markdown summary."""

import argparse
import re
from collections import Counter
from pathlib import Path

from tools.callgraph import build

DEFAULT_MAX_FUNCTION_EDGES = 300  # Mermaid's default cap is 500 edges.
TOP_ROWS = 15


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


def function_mermaid(graph):
    index = {node.id: f"n{position}" for position, node in enumerate(graph.nodes)}
    counts = Counter((edge.caller_id, edge.callee_id) for edge in graph.edges)
    lines = ["flowchart LR"]
    for node in graph.nodes:
        lines.append(f'  {index[node.id]}["{_mermaid_text(node.name)}"]')
    for (caller, callee), count in sorted(counts.items()):
        label = f"|{count}|" if count > 1 else ""
        lines.append(f"  {index[caller]} -->{label} {index[callee]}")
    return "\n".join(lines) + "\n"


def summary_markdown(graph, repo_url, max_function_edges=DEFAULT_MAX_FUNCTION_EDGES):
    packages = {node.package for node in graph.nodes}
    sha = graph.nodes[0].sha if graph.nodes else "unknown"
    pairs = {(edge.caller_id, edge.callee_id) for edge in graph.edges}
    parts = [
        "## Go call graph",
        "",
        f"**{len(graph.nodes)} functions, {len(graph.edges)} call sites, "
        f"{len(packages)} packages** at `{sha[:7]}`",
        "",
        "### Packages (cross-package call sites)",
        "",
        "```mermaid",
        package_mermaid(graph).rstrip(),
        "```",
        "",
    ]
    if len(pairs) <= max_function_edges:
        parts += ["### Functions", "", "```mermaid", function_mermaid(graph).rstrip(), "```", ""]
    else:
        parts += [
            f"_Note: function-level diagram omitted ({len(pairs)} caller/callee pairs exceeds "
            f"{max_function_edges}); download the `callgraph.svg` artifact._",
            "",
        ]
    parts += _fan_in_table(graph, repo_url)
    return "\n".join(parts) + "\n"


def _fan_in_table(graph, repo_url):
    called = Counter(edge.callee_id for edge in graph.edges)
    by_id = {node.id: node for node in graph.nodes}
    ranked = sorted(called, key=lambda node_id: (-called[node_id], by_id[node_id].name))
    rows = ["### Most called functions", "", "| function | package | call sites |", "| --- | --- | --- |"]
    for node_id in ranked[:TOP_ROWS]:
        node = by_id[node_id]
        url = source_url(repo_url, node.sha, node.file, node.start_line, node.end_line)
        rows.append(f"| [{_table_text(node.name)}]({url}) | {_table_text(node.package)} | {called[node_id]} |")
    return rows + [""]


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
    parser.add_argument("--max-function-edges", type=int, default=DEFAULT_MAX_FUNCTION_EDGES)
    args = parser.parse_args(argv)

    graph = build.load_graph(
        (args.graph_dir / "nodes.csv").read_text(), (args.graph_dir / "edges.csv").read_text()
    )
    (args.graph_dir / "callgraph.dot").write_text(to_dot(graph, args.repo_url))
    (args.graph_dir / "summary.md").write_text(
        summary_markdown(graph, args.repo_url, args.max_function_edges)
    )
    print(f"wrote callgraph.dot and summary.md to {args.graph_dir}")


if __name__ == "__main__":
    main()
