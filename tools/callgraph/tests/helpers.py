"""Shared fixtures for call graph tests.

The expected graph below describes ``codeql/go/test/CallGraph/main.go``. A test
re-reads that source file so these line numbers cannot drift from reality.
"""

import csv
import io
from pathlib import Path

from tools.callgraph import build

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_FILE = "codeql/go/test/CallGraph/main.go"
PACKAGE = "example.com/fixture"
SHA = "0123456789abcdef0123456789abcdef01234567"
REPO_URL = "https://github.com/MPieke/armwrestling-math"

NODE_COLUMNS = ["id", "name", "package", "file", "start_line", "end_line", "root_kind"]
EDGE_COLUMNS = ["caller_id", "callee_id", "call_file", "call_line", "resolution"]
EXTERNAL_COLUMNS = ["caller_id", "external_name", "external_package", "call_file", "call_line"]

# (name, start_line, end_line)
FIXTURE_FUNCTIONS = [
    ("main", 3, 6),
    ("run", 8, 11),
    ("helper", 13, 15),
    ("leaf", 17, 17),
]

# (caller, callee, call_line)
FIXTURE_CALLS = [
    ("main", "run", 4),
    ("main", "helper", 5),
    ("run", "helper", 9),
    ("run", "leaf", 10),
    ("helper", "leaf", 14),
]


def node_id(name, package=PACKAGE):
    return f"{package}.{name}"


def raw_nodes_csv(rows=None):
    """Rows may omit trailing columns; root_kind defaults to "" (not a root)."""
    rows = rows if rows is not None else [
        [node_id(n), n, PACKAGE, FIXTURE_FILE, s, e] for n, s, e in FIXTURE_FUNCTIONS
    ]
    return _csv(NODE_COLUMNS, [_padded(row, len(NODE_COLUMNS), "") for row in rows])


def raw_edges_csv(rows=None):
    """Rows may omit trailing columns; resolution defaults to "static"."""
    rows = rows if rows is not None else [
        [node_id(a), node_id(b), FIXTURE_FILE, line] for a, b, line in FIXTURE_CALLS
    ]
    return _csv(EDGE_COLUMNS, [_padded(row, len(EDGE_COLUMNS), "static") for row in rows])


def raw_externals_csv(rows=None):
    rows = rows if rows is not None else []
    return _csv(EXTERNAL_COLUMNS, rows)


def _padded(row, width, default):
    return list(row) + [default] * (width - len(row))


def _csv(columns, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


def make_graph(edges, entries=(), dead=(), externals=(), packages=None, extra_nodes=()):
    """Build a synthetic graph. Node ids are plain names; every node has its own file.

    ``entries`` get root_kind "referenced", ``dead`` get "unreferenced", and
    ``externals`` is a list of (caller, "pkg.Name") pairs.
    """
    names = []
    for source, target in edges:
        names += [source, target]
    names += list(entries) + list(dead) + [caller for caller, _ in externals] + list(extra_nodes)
    names = sorted(set(names))
    packages = packages or {}
    nodes = tuple(
        build.Node(
            id=name, lang="go", name=name, package=packages.get(name, "p"),
            file=f"{name}.go", start_line=1, end_line=100,
            root_kind="referenced" if name in entries else "unreferenced" if name in dead else "",
            sha=SHA,
        )
        for name in names
    )
    edge_rows = tuple(
        build.Edge(a, b, f"{a}.go", 5, "static", SHA) for a, b in edges
    )
    external_rows = tuple(
        build.External(caller, name, name.rsplit(".", 1)[0], f"{caller}.go", 7, SHA)
        for caller, name in externals
    )
    return build.Graph(nodes=nodes, edges=edge_rows, externals=external_rows)
