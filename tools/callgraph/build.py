"""Turn raw CodeQL query output into the validated call graph CSVs.

Raw inputs (decoded from the CodeQL queries) carry only what the query knows:

    nodes:     id, name, package, file, start_line, end_line, root_kind
    edges:     caller_id, callee_id, call_file, call_line, resolution
    externals: caller_id, external_name, external_package, call_file, call_line

This module checks the graph invariants, stamps every row with the language and
commit, and writes deterministic ``nodes.csv``, ``edges.csv`` and
``externals.csv``.
"""

import argparse
import csv
import io
from dataclasses import dataclass
from pathlib import Path

RAW_NODE_COLUMNS = ("id", "name", "package", "file", "start_line", "end_line", "root_kind")
RAW_EDGE_COLUMNS = ("caller_id", "callee_id", "call_file", "call_line", "resolution")
RAW_EXTERNAL_COLUMNS = ("caller_id", "external_name", "external_package", "call_file", "call_line")
NODE_COLUMNS = (
    "id", "lang", "name", "package", "file", "start_line", "end_line", "root_kind", "sha"
)
EDGE_COLUMNS = ("caller_id", "callee_id", "call_file", "call_line", "resolution", "sha")
EXTERNAL_COLUMNS = RAW_EXTERNAL_COLUMNS + ("sha",)

# "" means the function is not a root (it is only ever called from other functions).
ROOT_KINDS = ("", "main", "init", "referenced", "exported-uncalled", "unreferenced")
RESOLUTIONS = ("static", "dynamic")


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
    root_kind: str
    sha: str


@dataclass(frozen=True)
class Edge:
    caller_id: str
    callee_id: str
    call_file: str
    call_line: int
    resolution: str
    sha: str


@dataclass(frozen=True)
class External:
    """A call from a graph function to a function outside the extracted source."""

    caller_id: str
    external_name: str
    external_package: str
    call_file: str
    call_line: int
    sha: str


@dataclass(frozen=True)
class Graph:
    nodes: tuple
    edges: tuple
    externals: tuple = ()


def build_graph(nodes_csv, edges_csv, sha, lang="go", include_prefixes=(), externals_csv=None):
    """Validate raw query output and return a deterministic, stamped graph.

    ``include_prefixes`` limits the graph to functions whose file is at or below
    one of the given repo-relative paths. The whole input is validated first, so
    an edge to a function that never existed is still an error; edges and
    external calls with a caller or callee outside the scope are then dropped.
    """
    nodes = [
        _node(row, lang=lang, sha=sha) for row in _read_rows(nodes_csv, RAW_NODE_COLUMNS)
    ]
    edges = [_edge(row, sha=sha) for row in _read_rows(edges_csv, RAW_EDGE_COLUMNS)]
    externals = [
        _external(row, sha=sha)
        for row in _read_rows(externals_csv, RAW_EXTERNAL_COLUMNS)
    ] if externals_csv is not None else []
    return _restricted_to(_validated_graph(nodes, edges, externals), include_prefixes)


def load_graph(nodes_csv, edges_csv, externals_csv=None):
    """Read back the final CSVs written by this module and revalidate them."""
    nodes = [
        _node(row, lang=row["lang"], sha=row["sha"]) for row in _read_rows(nodes_csv, NODE_COLUMNS)
    ]
    edges = [_edge(row, sha=row["sha"]) for row in _read_rows(edges_csv, EDGE_COLUMNS)]
    externals = [
        _external(row, sha=row["sha"])
        for row in _read_rows(externals_csv, EXTERNAL_COLUMNS)
    ] if externals_csv is not None else []
    return _validated_graph(nodes, edges, externals)


def _node(row, lang, sha):
    return Node(
        id=row["id"],
        lang=lang,
        name=row["name"],
        package=row["package"],
        file=row["file"],
        start_line=_integer(row, "start_line"),
        end_line=_integer(row, "end_line"),
        root_kind=_choice(row, "root_kind", ROOT_KINDS),
        sha=sha,
    )


def _edge(row, sha):
    return Edge(
        caller_id=row["caller_id"],
        callee_id=row["callee_id"],
        call_file=row["call_file"],
        call_line=_integer(row, "call_line"),
        resolution=_choice(row, "resolution", RESOLUTIONS),
        sha=sha,
    )


def _external(row, sha):
    return External(
        caller_id=row["caller_id"],
        external_name=row["external_name"],
        external_package=row["external_package"],
        call_file=row["call_file"],
        call_line=_integer(row, "call_line"),
        sha=sha,
    )


def _restricted_to(graph, include_prefixes):
    if not include_prefixes:
        return graph
    prefixes = [prefix.rstrip("/") for prefix in include_prefixes]
    nodes = tuple(node for node in graph.nodes if _is_under(node.file, prefixes))
    kept_ids = {node.id for node in nodes}
    edges = tuple(
        edge for edge in graph.edges if edge.caller_id in kept_ids and edge.callee_id in kept_ids
    )
    externals = tuple(call for call in graph.externals if call.caller_id in kept_ids)
    return Graph(nodes=nodes, edges=edges, externals=externals)


def _is_under(file, prefixes):
    return any(file == prefix or file.startswith(prefix + "/") for prefix in prefixes)


def nodes_to_csv(graph):
    return _write_csv(NODE_COLUMNS, (_row(node, NODE_COLUMNS) for node in graph.nodes))


def edges_to_csv(graph):
    return _write_csv(EDGE_COLUMNS, (_row(edge, EDGE_COLUMNS) for edge in graph.edges))


def externals_to_csv(graph):
    return _write_csv(EXTERNAL_COLUMNS, (_row(call, EXTERNAL_COLUMNS) for call in graph.externals))


def _validated_graph(nodes, edges, externals):
    nodes_by_id = _index_nodes(nodes)
    unique_edges = sorted(
        set(edges), key=lambda e: (e.caller_id, e.callee_id, e.call_file, e.call_line)
    )
    for edge in unique_edges:
        _check_edge(edge, nodes_by_id)
    unique_externals = sorted(
        set(externals),
        key=lambda x: (x.caller_id, x.external_package, x.external_name, x.call_file, x.call_line),
    )
    for call in unique_externals:
        _check_call_site(call.caller_id, call.call_file, call.call_line, nodes_by_id)
    return Graph(
        nodes=tuple(sorted(nodes, key=lambda n: n.id)),
        edges=tuple(unique_edges),
        externals=tuple(unique_externals),
    )


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
    _check_call_site(edge.caller_id, edge.call_file, edge.call_line, nodes_by_id)
    if edge.callee_id not in nodes_by_id:
        raise GraphError(f"edge has unknown callee: {edge.callee_id}")


def _check_call_site(caller_id, call_file, call_line, nodes_by_id):
    caller = nodes_by_id.get(caller_id)
    if caller is None:
        raise GraphError(f"call has unknown caller: {caller_id}")
    inside_caller = (
        call_file == caller.file and caller.start_line <= call_line <= caller.end_line
    )
    if not inside_caller:
        raise GraphError(
            f"call site {call_file}:{call_line} is outside caller "
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


def _choice(row, column, allowed):
    value = row[column]
    if value not in allowed:
        raise GraphError(f"{column} must be one of {list(allowed)}, got {value!r}")
    return value


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
    parser.add_argument("--externals", type=Path, help="raw external calls CSV from CodeQL")
    parser.add_argument("--sha", required=True, help="commit the graph was extracted from")
    parser.add_argument("--lang", default="go")
    parser.add_argument(
        "--include-prefix",
        action="append",
        default=[],
        help="keep only functions under this repo-relative path (repeatable)",
    )
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    graph = build_graph(
        args.nodes.read_text(),
        args.edges.read_text(),
        args.sha,
        args.lang,
        include_prefixes=args.include_prefix,
        externals_csv=args.externals.read_text() if args.externals else None,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "nodes.csv").write_text(nodes_to_csv(graph))
    (args.out_dir / "edges.csv").write_text(edges_to_csv(graph))
    (args.out_dir / "externals.csv").write_text(externals_to_csv(graph))
    print(
        f"wrote {len(graph.nodes)} nodes, {len(graph.edges)} edges and "
        f"{len(graph.externals)} external calls to {args.out_dir}"
    )


if __name__ == "__main__":
    main()
