"""A fix plan for one redundancy card: the agreement between the developer and the coding agent.

The agent writes ``.callgraph/plan.json``; the developer steers it in conversation. This module
holds only deterministic checks: the plan must be well formed, its step ranges must lie inside
the real functions, and every difference inside a step it moves into a shared function must be
accounted for (a parameter, a unified value, or "stays"). It cannot say whether the plan is a
good idea, and it cannot prove a refactor preserves behaviour.

``approve`` records a digest of the plan. Whether a human really approved is enforced by how the
command is permitted in the agent's harness, not by this file.
"""

import copy
import hashlib
import json
import posixpath
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.callgraph import cli, render, safety
from tools.callgraph import diagrams as drawing

DEFAULT_PLAN = Path(".callgraph/plan.json")
HANDLERS = ("parameter", "unified", "stays")
_LIST_OF_TEXT = ("moved_steps", "planned_files", "will_not_touch", "constraints", "tests", "uncertainties")
_TEXT = ("card", "summary", "shared_name")


class PlanError(Exception):
    """A problem with the plan file or an approval request; printed without a traceback."""


@dataclass(frozen=True)
class Problem:
    level: str  # "error", "warning" or "note"
    code: str
    message: str


@dataclass(frozen=True)
class LintResult:
    problems: tuple
    differences: tuple = ()

    @property
    def ok(self):
        return not any(p.level == "error" for p in self.problems)


def approval_path_for(plan_path):
    plan_path = Path(plan_path)
    return plan_path.with_name(plan_path.stem + ".approval.json")


def check_path_for(plan_path):
    plan_path = Path(plan_path)
    return plan_path.with_name(plan_path.stem + ".check.json")


def review_path_for(plan_path):
    plan_path = Path(plan_path)
    return plan_path.with_name(plan_path.stem + ".review.json")


def path_under(path, entry):
    """True when ``path`` is ``entry`` or lies below it (``entry`` may be a directory)."""
    path, entry = posixpath.normpath(path), posixpath.normpath(entry)
    return path == entry or path.startswith(entry.rstrip("/") + "/")


def load_plan(path):
    path = Path(path)
    try:
        text = path.read_text()
    except OSError as error:
        raise PlanError(f"no plan at {path}; create one with: plan init CARD") from error
    try:
        document = json.loads(text)
    except ValueError as error:
        raise PlanError(f"{path} is not valid JSON ({error})") from error
    if not isinstance(document, dict):
        raise PlanError(f"{path} must contain a JSON object")
    return document


def save_plan(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n")


def digest(document):
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def template(session, ref):
    """A starting plan: the model's steps and fix when there is a judgement, else empty."""
    entry = _pair_entry(session, ref)
    card = entry.card
    draft = {
        "card": entry.ref,
        "summary": "",
        "shared_name": "",
        "steps": [],
        "moved_steps": [],
        "differences": [],
        "planned_files": sorted({session.names.nodes[f].file for f in (card.first, card.second)}),
        "will_not_touch": [],
        "constraints": [],
        "tests": [],
        "uncertainties": [],
    }
    verdict = entry.verdict
    if verdict is not None and verdict.get("status") == "ok":
        draft["steps"] = copy.deepcopy(verdict["steps"])
        draft["moved_steps"] = list(verdict["fix"]["moved_steps"])
        draft["shared_name"] = verdict["fix"]["shared_name"]
        draft["summary"] = verdict["fix"]["summary"]
        found = _moved_differences(session, card, draft["steps"], draft["moved_steps"])
        draft["differences"] = [{"a": d.a, "b": d.b, "handled_by": None} for d in found or []]
    return draft


def lint(document, session):
    problems = _schema_problems(document)
    if problems:
        return LintResult(tuple(problems))
    try:
        entry = _pair_entry(session, document["card"])
    except cli.CliError as error:
        return LintResult((Problem("error", "E_CARD", str(error)),))
    card = entry.card
    problems += _step_problems(document, session, card)
    problems += _moved_problems(document)
    differences, found = [], None
    if not problems:
        found = _moved_differences(session, card, document["steps"], document["moved_steps"])
        diff_problems, differences = _difference_problems(document, found)
        problems += diff_problems
    problems += _touch_problems(document, session)
    problems += _test_problems(document, session, entry)
    if document["constraints"]:
        problems.append(Problem(
            "note", "N_CONSTRAINTS",
            "constraints are not machine-checked, only will_not_touch is: "
            + "; ".join(document["constraints"]),
        ))
    return LintResult(tuple(problems), tuple(differences))


_STRUCTURAL = ("E_SCHEMA", "E_CARD", "E_DUP_STEP", "E_RANGE")


def diagrams(document, session):
    """Mermaid source for the plan: the two functions' steps before, and after the move.

    Built by the same code as the run summary's pictures. Problems that make the steps
    meaningless (schema, card, ranges, duplicate names) block drawing; undecided
    differences do not.
    """
    _require_structure(document, session, "drawing")
    card = _pair_entry(session, document["card"]).card
    steps = document["steps"]
    refs = render._step_refs(card, session.names, steps)
    before = drawing.before(steps, [], render._names_pair(card, session.names),
                             moved=document["moved_steps"], refs=refs)
    if before is None:
        raise PlanError("a diagram needs at least two steps")
    fix = {"moved_steps": document["moved_steps"], "shared_name": document["shared_name"]}
    after = drawing.apply_fix(before, fix, steps, refs=refs)
    return {
        "before": drawing.to_mermaid(before),
        "after": drawing.to_mermaid(after) if after is not None else None,
    }


def _require_structure(document, session, action):
    blocking = [p for p in lint(document, session).problems if p.code in _STRUCTURAL]
    if blocking:
        raise PlanError(f"fix these before {action}: " + "; ".join(f"{p.code}: {p.message}" for p in blocking))


def go_test_skeleton(document, session):
    """Skipped Go tests that pin today's text differences, plus stubs for the tests the plan promises.

    Every case calls ``t.Skip`` until the agent fills it in, so a skeleton can never pass by
    itself. Differences the compiler checks (types, receivers, identifiers) are only listed.
    """
    _require_structure(document, session, "generating tests")
    files = session.names.files
    if files is None:
        raise PlanError("a skeleton needs source access (--source-root) to find the text to pin")
    entry = _pair_entry(session, document["card"])
    card = entry.card
    found = _moved_differences(session, card, document["steps"], document["moved_steps"])
    if found is None:
        raise PlanError("the source files could not be read, so there is nothing to pin")
    decided = {(i["a"], i["b"]): i for i in document["differences"]}
    nodes = [session.names.nodes[card.first], session.names.nodes[card.second]]
    existing = {t.name for node in nodes for t in safety.find_tests(files.root, session.names.scope_dir, node)}
    stubs = {0: [], 1: []}
    for name in document["tests"]:
        if name in existing:
            continue
        stubs[_stub_owner(name, nodes)].append(name)
    moved = [step for step in document["steps"] if step["name"] in document["moved_steps"]]
    out = [
        f"// Characterization skeleton for card {entry.number} "
        f"({session.names.short(card.first)} and {session.names.short(card.second)}).",
        "// Generated by `plan tests`. Every case is skipped until you fill it in: reach the line",
        "// shown and assert today's text. Run them before the refactor (they must pass), then again after.",
        "",
    ]
    unpinned = [d for d in found if d.kind != "string"]
    if unpinned:
        out.append("// not pinned (the compiler checks these or they do not change behaviour):")
        out += [
            f"//   {d.a or '(nothing)'} -> {d.b or '(nothing)'} ({d.kind}, {d.count} places; "
            f"{_handling(decided.get((d.a, d.b)))})"
            for d in unpinned
        ]
        out.append("")
    for index, node in enumerate(nodes):
        out += _skeleton_section(node, "ab"[index], moved, found, decided, files, stubs[index])
    return "\n".join(out).rstrip("\n") + "\n"


def _stub_owner(test_name, nodes):
    for index in (1, 0):
        if safety.subject(nodes[index]) in test_name:
            return index
    return 0


def _handling(item):
    handled = item.get("handled_by") if item else None
    if handled is None:
        return "undecided"
    return f"parameter {item['parameter']}" if handled == "parameter" and item.get("parameter") else handled


def _skeleton_section(node, side, moved, found, decided, files, stubs):
    lines = files.lines(node.file) or []
    directory = posixpath.dirname(node.file)
    name = posixpath.splitext(posixpath.basename(node.file))[0] + "_characterization_test.go"
    rows = []
    for difference in found:
        if difference.kind != "string":
            continue
        text = difference.a if side == "a" else difference.b
        rows.append((_handling(decided.get((difference.a, difference.b))), _line_of(text, lines, moved, side), text))
    out = [f"// file: {posixpath.join(directory, name)}", f"package {node.package.rsplit('/', 1)[-1]}", "",
           'import "testing"', ""]
    if rows:
        out += [
            f"func TestPinnedText_{node.name}(t *testing.T) {{",
            '\tt.Skip("TODO: fill in the cases below, then delete this line")',
            "\tcases := []struct {",
            "\t\tname string // how the plan handles this difference",
            "\t\tline int    // where the text is today",
            "\t\twant string // today's text, which must survive the refactor",
            "\t}{",
        ]
        out += [f"\t\t{{name: {json.dumps(label)}, line: {line}, want: {text}}}," for label, line, text in rows]
        out += [
            "\t}",
            "\tfor _, tc := range cases {",
            "\t\tt.Run(tc.name, func(t *testing.T) {",
            f"\t\t\t// TODO: call {node.name} so it reaches the line above, then assert tc.want is kept",
            "\t\t\t_ = tc",
            "\t\t})",
            "\t}",
            "}",
            "",
        ]
    for stub in stubs:
        out += [f"func {stub}(t *testing.T) {{", '\tt.Skip("TODO: planned in the fix plan, write this test")', "}", ""]
    return out


def _line_of(text, lines, moved, side):
    for step in moved:
        span = step[side]
        if span is None:
            continue
        for number in range(span[0], min(span[1], len(lines)) + 1):
            if text in lines[number - 1]:
                return number
    return 0


def approve(plan_path, approval_path, session):
    document = load_plan(plan_path)
    result = lint(document, session)
    if not result.ok:
        errors = "; ".join(f"{p.code}: {p.message}" for p in result.problems if p.level == "error")
        raise PlanError(f"cannot approve a plan with errors: {errors}")
    approval = {
        "card": document["card"],
        "plan_digest": digest(document),
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    approval_path = Path(approval_path)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(approval, indent=2) + "\n")
    return approval


def review_approve(plan_path, approval_path, check_path, review_path):
    """Checkpoint 2: record that the finished work was reviewed. Needs an approved plan and a
    passing ``check`` made for exactly this plan."""
    document = load_plan(plan_path)
    if approval_status(plan_path, approval_path) != "approved":
        raise PlanError("the plan was not approved (or changed since): run plan approve first")
    try:
        result = json.loads(Path(check_path).read_text())
    except (OSError, ValueError) as error:
        raise PlanError("there is no check result; run check first") from error
    if result.get("plan_digest") != digest(document):
        raise PlanError("the last check was made for a different plan; run check again")
    if not result.get("ok"):
        raise PlanError("the last check did not pass; fix the errors and run check again")
    review = {
        "card": document["card"],
        "plan_digest": digest(document),
        "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    Path(review_path).write_text(json.dumps(review, indent=2) + "\n")
    return review


def review_status(plan_path, review_path):
    try:
        review = json.loads(Path(review_path).read_text())
    except (OSError, ValueError):
        return "not reviewed"
    return "reviewed" if review.get("plan_digest") == digest(load_plan(plan_path)) else "changed since review"


def approval_status(plan_path, approval_path):
    try:
        approval = json.loads(Path(approval_path).read_text())
    except (OSError, ValueError):
        return "not approved"
    return "approved" if approval.get("plan_digest") == digest(load_plan(plan_path)) else "changed since approval"


def _pair_entry(session, ref):
    entry = cli.find_entry(session, ref)
    if entry.card.kind != "pair":
        raise cli.CliError(f"card {ref!r} is a two-routes card; plans support pair cards")
    return entry


def _schema_problems(document):
    problems = []

    def bad(message):
        problems.append(Problem("error", "E_SCHEMA", message))

    for field in _TEXT:
        if not isinstance(document.get(field), str):
            bad(f"{field} must be text")
    for field in _LIST_OF_TEXT:
        value = document.get(field)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            bad(f"{field} must be a list of text")
    steps = document.get("steps")
    if not isinstance(steps, list):
        bad("steps must be a list")
    else:
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or not isinstance(step.get("name"), str) or not step["name"].strip():
                bad(f"steps[{index}] needs a name")
                continue
            for side in ("a", "b"):
                if not _range_shape(step.get(side)):
                    bad(f"steps[{index}].{side} must be null or [start, end] line numbers")
            if not isinstance(step.get("same"), bool):
                bad(f"steps[{index}].same must be true or false")
    differences = document.get("differences")
    if not isinstance(differences, list):
        bad("differences must be a list")
    else:
        for index, item in enumerate(differences):
            if not isinstance(item, dict) or not isinstance(item.get("a"), str) or not isinstance(item.get("b"), str):
                bad(f"differences[{index}] needs text a and b")
    return problems


def _range_shape(value):
    return value is None or (
        isinstance(value, list) and len(value) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in value)
    )


def _step_problems(document, session, card):
    problems, seen = [], set()
    taken = {"a": [], "b": []}
    nodes = {"a": session.names.nodes[card.first], "b": session.names.nodes[card.second]}
    for step in document["steps"]:
        if step["name"] in seen:
            problems.append(Problem("error", "E_DUP_STEP", f"step name {step['name']!r} is used twice"))
        seen.add(step["name"])
        for side in ("a", "b"):
            span = step[side]
            if span is None:
                continue
            start, end = span
            node = nodes[side]
            if not (node.start_line <= start <= end <= node.end_line):
                problems.append(Problem(
                    "error", "E_RANGE",
                    f"step {step['name']!r} lines {start}-{end} are not inside "
                    f"{node.name} (lines {node.start_line}-{node.end_line})",
                ))
            elif any(not (end < s or start > e) for s, e in taken[side]):
                problems.append(Problem(
                    "error", "E_RANGE", f"step {step['name']!r} lines {start}-{end} overlap another step"))
            else:
                taken[side].append((start, end))
    return problems


def _moved_problems(document):
    problems = []
    by_name = {step["name"]: step for step in document["steps"]}
    if not document["moved_steps"]:
        problems.append(Problem("error", "E_NO_MOVED", "the plan moves no steps into a shared function"))
    for name in document["moved_steps"]:
        step = by_name.get(name)
        if step is None:
            problems.append(Problem("error", "E_MOVED_UNKNOWN", f"moved step {name!r} is not in steps"))
        elif step["a"] is None or step["b"] is None:
            problems.append(Problem(
                "error", "E_MOVED_ONE_SIDED", f"moved step {name!r} exists in only one of the two functions"))
    return problems


def _moved_differences(session, card, steps, moved):
    """Differences inside the moved steps (treated as the same), or None without source."""
    files = session.names.files
    if files is None:
        return None
    nodes = [session.names.nodes[card.first], session.names.nodes[card.second]]
    lines = [files.lines(node.file) for node in nodes]
    if any(line is None for line in lines):
        return None
    chosen = [
        {**step, "same": True} for step in steps
        if step["name"] in moved and step.get("a") is not None and step.get("b") is not None
    ]
    return safety.step_differences(lines[0], lines[1], chosen)


def _difference_problems(document, found):
    if found is None:
        return [Problem("warning", "W_NO_SOURCE",
                        "no source access, so the differences inside the moved steps were not checked")], []
    problems, listed = [], {}
    for item in document["differences"]:
        listed.setdefault((item["a"], item["b"]), item)
    shown = []
    for difference in found:
        item = listed.pop((difference.a, difference.b), None)
        handled = item.get("handled_by") if item else None
        label = f"{difference.a or '(nothing)'} -> {difference.b or '(nothing)'}"
        if handled is None:
            problems.append(Problem(
                "error", "E_DIFF_UNHANDLED",
                f"difference {label} ({difference.kind}, {difference.count} places) is not accounted for: "
                "say how the shared function handles it (parameter, unified or stays)",
            ))
        elif handled not in HANDLERS:
            problems.append(Problem(
                "error", "E_DIFF_HANDLER", f"difference {label}: handled_by must be one of {', '.join(HANDLERS)}"))
        elif handled == "parameter" and not str(item.get("parameter") or "").strip():
            problems.append(Problem("error", "E_DIFF_HANDLER", f"difference {label}: name the parameter"))
        shown.append({"kind": difference.kind, "a": difference.a, "b": difference.b,
                      "count": difference.count, "handled_by": handled})
    for a, b in listed:
        problems.append(Problem(
            "warning", "W_DIFF_STALE", f"the plan lists a difference {a} -> {b} that is not in the moved steps"))
    return problems, shown


def _touch_problems(document, session):
    nodes = session.names.nodes
    forbidden = [
        posixpath.normpath(nodes[entry].file if entry in nodes else entry)
        for entry in document["will_not_touch"]
    ]
    problems = []
    for planned in document["planned_files"]:
        path = posixpath.normpath(planned)
        for entry in forbidden:
            if path_under(path, entry):
                problems.append(Problem(
                    "error", "E_WILL_NOT_TOUCH", f"planned file {planned} is under will_not_touch entry {entry}"))
    return problems


def _test_problems(document, session, entry):
    if session.names.files is None or document["tests"]:
        return []
    facts = cli.card_document(session, str(entry.number))
    gaps = facts["test_gaps"]
    if gaps is None:
        return []
    if gaps["none_first"] or gaps["none_second"]:
        return [Problem("warning", "W_TESTS", "a function has no tests found by name and the plan adds none")]
    missing = gaps["only_first"] + gaps["only_second"]
    if missing:
        return [Problem("warning", "W_TESTS", f"no counterpart by name for: {', '.join(missing)}; the plan adds no tests")]
    return []
