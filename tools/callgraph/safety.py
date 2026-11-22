"""Checks that help a developer act safely on a suggested fix. No LLM involved.

* ``blast_radius``: who calls a function, from the call graph.
* ``find_tests`` and ``test_gaps``: which tests mention a function, and which test
  one function has that the other lacks, judged by test *name*.
* ``step_differences``: what differs inside the steps the model called "the same",
  which is what a shared function would have to take as parameters.

These are facts about the code or heuristics worded as such. None of them proves
that a refactor preserves behaviour.
"""

import difflib
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

_TEST_FUNCTION = re.compile(r"^func (Test\w*)\(")
_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|`[^`]*`|[A-Za-z_]\w*|\d+|\S')
_KIND_ORDER = ("string", "type", "receiver", "identifier", "other")


@dataclass(frozen=True)
class Caller:
    id: str
    file: str
    line: int
    resolution: str


@dataclass(frozen=True)
class BlastRadius:
    callers: tuple
    exported: bool
    via_interface: bool


@dataclass(frozen=True)
class Test:
    name: str
    file: str
    line: int


@dataclass(frozen=True)
class Gaps:
    only_first: tuple
    only_second: tuple
    none_first: bool
    none_second: bool


@dataclass(frozen=True)
class Difference:
    kind: str
    a: str
    b: str
    steps: tuple
    count: int


def blast_radius(graph, function_id):
    """Direct callers of a function (recursion excluded) and whether it is exported."""
    node = next((n for n in graph.nodes if n.id == function_id), None)
    callers = sorted(
        (
            Caller(e.caller_id, e.call_file, e.call_line, e.resolution)
            for e in graph.edges
            if e.callee_id == function_id and e.caller_id != function_id
        ),
        key=lambda c: (c.file, c.line, c.id),
    )
    return BlastRadius(
        callers=tuple(callers),
        exported=bool(node and node.name[:1].isupper()),
        via_interface=any(c.resolution == "dynamic" for c in callers),
    )


def subject(node):
    """The name Go tests are named after: the receiver type for a method, else the function."""
    prefix = node.package + "."
    rest = node.id[len(prefix):] if node.id.startswith(prefix) else node.id
    return rest.split(".")[0] if "." in rest else node.name


def find_tests(root, scope_dir, node):
    """Tests under ``scope_dir`` whose body mentions the function (or its receiver type).

    In the function's own directory the bare name counts; elsewhere the name must be
    qualified with the package (``pkg.Thing``). Benchmarks and fuzz targets are not counted.
    """
    scope = Path(root) / scope_dir
    if not scope.is_dir():
        return []
    term = re.escape(subject(node))
    package = re.escape(node.package.rsplit("/", 1)[-1])
    own_directory = posixpath.dirname(node.file)
    found = []
    for path in sorted(scope.rglob("*_test.go")):
        relative = path.relative_to(root).as_posix()
        pattern = rf"\b{term}\b" if posixpath.dirname(relative) == own_directory else rf"\b{package}\.{term}\b"
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for name, line, body in _test_bodies(lines):
            if re.search(pattern, body):
                found.append(Test(name, relative, line))
    return found


def _test_bodies(lines):
    starts = [(i, m.group(1)) for i, text in enumerate(lines) if (m := _TEST_FUNCTION.match(text))]
    for index, (start, name) in enumerate(starts):
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("func ")), len(lines))
        yield name, start + 1, "\n".join(lines[start + 1:end])


def test_gaps(first_tests, second_tests, first_subject, second_subject):
    """Behaviours one function has a test for and the other does not, by test name.

    A name like ``TestOpenAIAnnotatorRedactsAPIKey`` is reduced to ``RedactsAPIKey`` by
    removing ``Test`` and the subject, so parallel names compare equal. This is a
    heuristic: different naming hides a gap or invents one.
    """
    if not first_tests or not second_tests:
        return Gaps((), (), not first_tests, not second_tests)
    first = {_behaviour(t.name, first_subject) for t in first_tests}
    second = {_behaviour(t.name, second_subject) for t in second_tests}
    return Gaps(tuple(sorted(first - second)), tuple(sorted(second - first)), False, False)


def _behaviour(test_name, subject_name):
    rest = test_name[4:] if test_name.startswith("Test") else test_name
    return rest.replace(subject_name, "", 1)


def step_differences(lines_a, lines_b, steps):
    """Token differences inside steps marked the same, grouped and labelled by kind."""
    found = {}
    for step in steps:
        if not step["same"] or step["a"] is None or step["b"] is None:
            continue
        a_tokens = _tokens(lines_a[step["a"][0] - 1:step["a"][1]])
        b_tokens = _tokens(lines_b[step["b"][0] - 1:step["b"][1]])
        for a_text, b_text in _token_pairs(a_tokens, b_tokens):
            key = (_kind(a_text, b_text), a_text, b_text)
            entry = found.setdefault(key, {"steps": [], "count": 0})
            entry["count"] += 1
            if step["name"] not in entry["steps"]:
                entry["steps"].append(step["name"])
    differences = []
    for (kind, a_text, b_text), entry in found.items():
        if kind == "identifier" and entry["count"] >= 2:
            kind = "receiver"  # the same rename in several places is a renamed receiver
        differences.append(Difference(kind, a_text, b_text, tuple(entry["steps"]), entry["count"]))
    return sorted(differences, key=lambda d: (_KIND_ORDER.index(d.kind), d.a, d.b))


def _tokens(lines):
    tokens = []
    for text in lines:
        line = _TOKEN.findall(text)
        for position in range(len(line) - 1):
            if line[position] == "/" == line[position + 1]:  # a comment: drop the rest
                line = line[:position]
                break
        tokens += line + ["\n"]
    return tokens


def _token_pairs(a_tokens, b_tokens):
    matcher = difflib.SequenceMatcher(None, a_tokens, b_tokens, autojunk=False)
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        a_part, b_part = a_tokens[a_start:a_end], b_tokens[b_start:b_end]
        if tag == "replace" and len(a_part) == len(b_part):
            yield from ((x, y) for x, y in zip(a_part, b_part) if x != "\n" and y != "\n")
        else:
            a_text = " ".join(t for t in a_part if t != "\n")
            b_text = " ".join(t for t in b_part if t != "\n")
            if a_text or b_text:
                yield a_text, b_text


def _kind(a_text, b_text):
    if _is_string(a_text) and _is_string(b_text):
        return "string"
    if _is_identifier(a_text) and _is_identifier(b_text):
        return "type" if a_text[0].isupper() and b_text[0].isupper() else (
            "identifier" if a_text[0].islower() and b_text[0].islower() else "other"
        )
    return "other"


def _is_string(text):
    return len(text) >= 2 and text[0] in "\"`" and text[-1] == text[0]


def _is_identifier(text):
    return re.fullmatch(r"[A-Za-z_]\w*", text) is not None
