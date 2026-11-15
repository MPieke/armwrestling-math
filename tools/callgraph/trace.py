"""Map a source location back to call graph nodes and their edges."""

import argparse
from dataclasses import dataclass
from pathlib import Path

from tools.callgraph import build


@dataclass(frozen=True)
class TraceResult:
    nodes: tuple
    incoming: tuple
    outgoing: tuple


def parse_location(text):
    """Split ``path`` or ``path:line`` into ``(path, line_or_None)``."""
    path, separator, line = text.rpartition(":")
    if not separator:
        return text, None
    if not line.isdigit():
        raise ValueError(f"line must be a number in {text!r}")
    return path, int(line)


def trace_location(graph, file, line=None):
    """Functions in ``file`` covering ``line`` (all of them if no line), plus their edges."""
    nodes = tuple(
        node
        for node in graph.nodes
        if node.file == file and (line is None or node.start_line <= line <= node.end_line)
    )
    node_ids = {node.id for node in nodes}
    incoming = tuple(edge for edge in graph.edges if edge.callee_id in node_ids)
    outgoing = tuple(edge for edge in graph.edges if edge.caller_id in node_ids)
    return TraceResult(nodes=nodes, incoming=incoming, outgoing=outgoing)


def format_result(result):
    if not result.nodes:
        return "no call graph node covers that location"
    lines = []
    for node in result.nodes:
        lines.append(f"{node.id}  ({node.file}:{node.start_line}-{node.end_line})")
    for edge in result.incoming:
        lines.append(f"  called by {edge.caller_id} at {edge.call_file}:{edge.call_line}")
    for edge in result.outgoing:
        lines.append(f"  calls {edge.callee_id} at {edge.call_file}:{edge.call_line}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Trace a source location in the call graph.")
    parser.add_argument("location", help="path or path:line, repo-relative")
    parser.add_argument("--graph-dir", type=Path, default=Path("callgraph-out"))
    args = parser.parse_args(argv)

    graph = build.load_graph(
        (args.graph_dir / "nodes.csv").read_text(), (args.graph_dir / "edges.csv").read_text()
    )
    file, line = parse_location(args.location)
    print(format_result(trace_location(graph, file, line)))


if __name__ == "__main__":
    main()
