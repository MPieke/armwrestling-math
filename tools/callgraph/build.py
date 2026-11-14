"""Turn raw CodeQL query output into the validated call graph CSVs.

Raw inputs (decoded from the CodeQL queries) carry only what the query knows:

    nodes: id, name, package, file, start_line, end_line
    edges: caller_id, callee_id, call_file, call_line

This module checks the graph invariants, stamps every row with the language and
commit, and writes deterministic ``nodes.csv`` / ``edges.csv``.
"""

import argparse
import csv
import io
from dataclasses import dataclass
from pathlib import Path

RAW_NODE_COLUMNS = ("id", "name", "package", "file", "start_line", "end_line")
RAW_EDGE_COLUMNS = ("caller_id", "callee_id", "call_file", "call_line")
NODE_COLUMNS = ("id", "lang", "name", "package", "file", "start_line", "end_line", "sha")
EDGE_COLUMNS = ("caller_id", "callee_id", "call_file", "call_line", "sha")


class GraphError(ValueError):
    """The input does not describe a consistent call graph."""


@dataclass(frozen=True)
class Node:
    id: str
    lang: str
    name: str
    package: str
    file: str
    start_line: int
    end_line: int
    sha: str


@dataclass(frozen=True)
class Edge:
    caller_id: str
    callee_id: str
    call_file: str
    call_line: int
    sha: str


@dataclass(frozen=True)
class Graph:
    nodes: tuple
    edges: tuple


def build_graph(nodes_csv, edges_csv, sha, lang="go"):
    """Validate raw query output and return a deterministic, stamped graph."""
    nodes = [
        Node(
            id=row["id"],
            lang=lang,
            name=row["name"],
            package=row["package"],
            file=row["file"],
            start_line=_integer(row, "start_line"),
            end_line=_integer(row, "end_line"),
            sha=sha,
        )
        for row in _read_rows(nodes_csv, RAW_NODE_COLUMNS)
    ]
    edges = [
        Edge(
            caller_id=row["caller_id"],
            callee_id=row["callee_id"],
            call_file=row["call_file"],
            call_line=_integer(row, "call_line"),
            sha=sha,
        )
        for row in _read_rows(edges_csv, RAW_EDGE_COLUMNS)
    ]
    return _validated_graph(nodes, edges)


def load_graph(nodes_csv, edges_csv):
    """Read back the final CSVs written by this module and revalidate them."""
    nodes = [
        Node(
            id=row["id"],
            lang=row["lang"],
            name=row["name"],
            package=row["package"],
            file=row["file"],
            start_line=_integer(row, "start_line"),
            end_line=_integer(row, "end_line"),
            sha=row["sha"],
        )
        for row in _read_rows(nodes_csv, NODE_COLUMNS)
    ]
    edges = [
        Edge(
            caller_id=row["caller_id"],
            callee_id=row["callee_id"],
            call_file=row["call_file"],
            call_line=_integer(row, "call_line"),
            sha=row["sha"],
        )
        for row in _read_rows(edges_csv, EDGE_COLUMNS)
    ]
    return _validated_graph(nodes, edges)


def nodes_to_csv(graph):
    return _write_csv(NODE_COLUMNS, (_row(node, NODE_COLUMNS) for node in graph.nodes))


def edges_to_csv(graph):
    return _write_csv(EDGE_COLUMNS, (_row(edge, EDGE_COLUMNS) for edge in graph.edges))


def _validated_graph(nodes, edges):
    nodes_by_id = _index_nodes(nodes)
    unique_edges = sorted(
        set(edges), key=lambda e: (e.caller_id, e.callee_id, e.call_file, e.call_line)
    )
    for edge in unique_edges:
        _check_edge(edge, nodes_by_id)
    return Graph(nodes=tuple(sorted(nodes, key=lambda n: n.id)), edges=tuple(unique_edges))


def _index_nodes(nodes):
    nodes_by_id = {}
    for node in nodes:
        if node.id in nodes_by_id:
            raise GraphError(f"duplicate node id: {node.id}")
        if node.end_line < node.start_line:
            raise GraphError(
                f"{node.id}: end_line {node.end_line} precedes start_line {node.start_line}"
            )
        nodes_by_id[node.id] = node
    return nodes_by_id


def _check_edge(edge, nodes_by_id):
    caller = nodes_by_id.get(edge.caller_id)
    if caller is None:
        raise GraphError(f"edge has unknown caller: {edge.caller_id}")
    if edge.callee_id not in nodes_by_id:
        raise GraphError(f"edge has unknown callee: {edge.callee_id}")
    inside_caller = (
        edge.call_file == caller.file and caller.start_line <= edge.call_line <= caller.end_line
    )
    if not inside_caller:
        raise GraphError(
            f"call site {edge.call_file}:{edge.call_line} is outside caller "
            f"{caller.id} ({caller.file}:{caller.start_line}-{caller.end_line})"
        )


def _read_rows(text, required_columns):
    reader = csv.DictReader(io.StringIO(text))
    missing = [column for column in required_columns if column not in (reader.fieldnames or [])]
    if missing:
        raise GraphError(f"missing column(s): {', '.join(missing)}")
    return list(reader)


def _integer(row, column):
    try:
        return int(row[column])
    except (TypeError, ValueError):
        raise GraphError(f"{column} is not an integer: {row[column]!r}") from None


def _row(record, columns):
    return [getattr(record, column) for column in columns]


def _write_csv(columns, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate raw call graph CSVs and stamp them.")
    parser.add_argument("--nodes", required=True, type=Path, help="raw nodes CSV from CodeQL")
    parser.add_argument("--edges", required=True, type=Path, help="raw edges CSV from CodeQL")
    parser.add_argument("--sha", required=True, help="commit the graph was extracted from")
    parser.add_argument("--lang", default="go")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    graph = build_graph(args.nodes.read_text(), args.edges.read_text(), args.sha, args.lang)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "nodes.csv").write_text(nodes_to_csv(graph))
    (args.out_dir / "edges.csv").write_text(edges_to_csv(graph))
    print(f"wrote {len(graph.nodes)} nodes and {len(graph.edges)} edges to {args.out_dir}")


if __name__ == "__main__":
    main()
