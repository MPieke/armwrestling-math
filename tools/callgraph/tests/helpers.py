"""Shared fixtures for call graph tests.

The expected graph below describes ``codeql/go/test/CallGraph/main.go``. A test
re-reads that source file so these line numbers cannot drift from reality.
"""

import csv
import io
from pathlib import Path

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
