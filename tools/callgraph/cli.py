"""Facts about redundancy cards for a coding agent or a developer. No LLM is called here.

    python -m tools.callgraph.cli --graph-dir DIR findings [--json]
    python -m tools.callgraph.cli --graph-dir DIR card REF [--json]

``REF`` is a card number (as in the run summary) or ``first~second`` (two function ids).
Everything printed is computed from the graph and the source; the model's suggestion, when a
``judgements.json`` exists, is included and labelled advisory.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from tools.callgraph import analyze, build, cards, render, safety


class CliError(Exception):
    """A problem the user can fix; printed without a traceback."""


@dataclass(frozen=True)
class Entry:
    number: int
    card: object
    verdict: object
    folded: bool

    @property
    def ref(self):
        return f"{self.card.first}~{self.card.second}"


@dataclass(frozen=True)
class Session:
    graph: object
    analysis: object
    entries: tuple
    source_root: object
    names: object


def load_session(graph_dir, source_root=".", ignore_file=analyze.DEFAULT_IGNORE_FILE, judgements_path=None):
    graph_dir = Path(graph_dir)
    try:
        nodes = (graph_dir / "nodes.csv").read_text()
        edges = (graph_dir / "edges.csv").read_text()
    except OSError as error:
        raise CliError(
            f"cannot read nodes.csv and edges.csv in {graph_dir} ({error.strerror}); "
            "download the CI artifact or run the CodeQL queries first"
        ) from error
    externals = graph_dir / "externals.csv"
    graph = build.load_graph(nodes, edges, externals.read_text() if externals.exists() else None)
    ignored = analyze.parse_ignore_file(Path(ignore_file).read_text())
    analysis = analyze.analyze(graph, ignored_packages=ignored)
    judgements = render.load_judgements(judgements_path or graph_dir / "judgements.json")
    return build_session(graph, analysis, judgements, source_root, ignored)


def build_session(graph, analysis, judgements, source_root=None, ignored=()):
    found = cards.build_cards(graph, analysis, ignored)
    verdicts = {(j["first"], j["second"]): j for j in (judgements or {}).get("judgements", [])}
    surface, folded = render.ranked_cards(found, verdicts)
    entries = tuple(
        Entry(number, card, verdict, is_folded)
        for number, (card, verdict, is_folded) in enumerate(
            [(c, v, False) for c, v in surface] + [(c, v, True) for c, v in folded], start=1
        )
    )
    names = render._Names(graph, render._package_labels(sorted({n.package for n in graph.nodes})), "")
    names.files = render._Files(source_root) if source_root else None
    return Session(graph, analysis, entries, source_root, names)


def find_entry(session, ref):
    if ref.isdigit() and 1 <= int(ref) <= len(session.entries):
        return session.entries[int(ref) - 1]
    for entry in session.entries:
        if entry.ref == ref:
            return entry
    available = f"1..{len(session.entries)}" if session.entries else "none"
    raise CliError(f"no card {ref!r}; cards available: {available}")


def findings_document(session):
    return {
        "commit": session.graph.nodes[0].sha if session.graph.nodes else None,
        "total": len(session.entries),
        "cards": [
            {
                "number": e.number,
                "ref": e.ref,
                "kind": e.card.kind,
                "first": e.card.first,
                "second": e.card.second,
                "first_short": session.names.short(e.card.first),
                "second_short": session.names.short(e.card.second),
                "level": e.card.evidence.level if e.card.kind == "pair" else None,
                "similarity": round(e.card.evidence.similarity, 2),
                "targets": list(e.card.targets),
                "folded": e.folded,
                "action": e.verdict["action"] if render._is_judged(e.verdict) else None,
            }
            for e in session.entries
        ],
    }


def findings_text(document):
    if not document["cards"]:
        return "No redundant routes found.\n"
    lines = []
    for card in document["cards"]:
        level = card["level"] or "two routes"
        action = f" ({card['action']})" if card["action"] else ""
        lines.append(f"{card['number']}. [{level}] {card['first_short']} and {card['second_short']}{action}")
    return "\n".join(lines) + "\n"


def card_document(session, ref):
    entry = find_entry(session, ref)
    card, names = entry.card, session.names
    ids = (card.first, card.second) if card.kind == "pair" else (card.owner, card.helper)
    radius = {i: safety.blast_radius(session.graph, i) for i in ids}
    files = names.files
    tests = gaps = differences = None
    note = "no source access, so steps could not be compared"
    if files is not None:
        tests = {i: safety.find_tests(files.root, names.scope_dir, names.nodes[i]) for i in ids}
        if card.kind == "pair":
            gaps = safety.test_gaps(tests[ids[0]], tests[ids[1]],
                                    safety.subject(names.nodes[ids[0]]), safety.subject(names.nodes[ids[1]]))
    verdict = entry.verdict if render._is_judged(entry.verdict) else None
    if files is not None:
        note = "no steps yet: the plan supplies them, or a model judgement does"
        if verdict is not None and card.kind == "pair":
            lines = [files.lines(names.nodes[i].file) for i in ids]
            if all(line is not None for line in lines):
                differences = safety.step_differences(lines[0], lines[1], verdict["steps"])
                note = ""
    evidence = card.evidence
    return {
        "number": entry.number,
        "ref": entry.ref,
        "kind": card.kind,
        "level": evidence.level if card.kind == "pair" else None,
        "folded": entry.folded,
        "functions": [_function(names, i) for i in ids],
        "targets": list(card.targets),
        "targets_short": [names.short(t) for t in card.targets],
        "reached_from": list(card.reached_from),
        "evidence": {
            "similarity": round(evidence.similarity, 2),
            "band": evidence.band,
            "shared_callees": list(evidence.shared_callees),
            "shared_externals": list(evidence.shared_externals),
            "only_first": list(evidence.only_first),
            "only_second": list(evidence.only_second),
        },
        "blast_radius": {i: _radius(radius[i], names) for i in ids},
        "tests": None if tests is None else {i: [_test(t) for t in tests[i]] for i in ids},
        "test_gaps": None if gaps is None else {
            "only_first": list(gaps.only_first), "only_second": list(gaps.only_second),
            "none_first": gaps.none_first, "none_second": gaps.none_second,
            "comparable": gaps.comparable,
        },
        "differences": None if differences is None else [
            {"kind": d.kind, "a": d.a, "b": d.b, "steps": list(d.steps), "count": d.count}
            for d in differences
        ],
        "differences_note": note,
        "model_suggestion": None if verdict is None else {
            "advisory": True,
            "verdict": verdict["verdict"],
            "action": verdict["action"],
            "headline": verdict["headline"],
            "fix": verdict["fix"],
            "steps": verdict["steps"],
        },
    }


def card_text(document):
    label = {f["id"]: f["short"] for f in document["functions"]}
    first, second = (f["short"] for f in document["functions"])
    lines = [f"Card {document['number']}: {first} and {second}"]
    if document["level"]:
        percent = round(document["evidence"]["similarity"] * 100)
        lines.append(f"Level: {document['level']} (call overlap {percent}%; display only)")
    lines.append(f"Reach: {', '.join(document['targets_short'])}")
    lines += ["", "Callers:"]
    for function, radius in document["blast_radius"].items():
        callers = ", ".join(c["name"] for c in radius["callers"]) or "none in the graph"
        via = " (through an interface)" if radius["via_interface"] else ""
        lines.append(f"- {label[function]} is called from {callers}{via}")
    lines += ["", "Tests:"]
    if document["tests"] is None:
        lines.append("- not checked (no source access)")
    else:
        for function, found in document["tests"].items():
            lines.append(f"- {label[function]}: {', '.join(t['name'] for t in found) or 'none found'}")
        gaps = document["test_gaps"]
        if gaps:
            for side, name in (("only_first", second), ("only_second", first)):
                if gaps[side]:
                    lines.append(f"- {name} has no counterpart by name for: {', '.join(gaps[side])}")
    lines += ["", "Differences inside the steps called the same:"]
    if document["differences"] is None:
        lines.append(f"- not computed: {document['differences_note']}")
    for d in document["differences"] or []:
        lines.append(f"- [{d['kind']}] {d['a'] or '(nothing)'} -> {d['b'] or '(nothing)'}"
                     + (f" ({d['count']} places)" if d["count"] > 1 else ""))
    suggestion = document["model_suggestion"]
    if suggestion:
        lines += ["", f"Model suggestion (advisory): {suggestion['action']} - {suggestion['fix']['summary']}"]
    return "\n".join(lines) + "\n"


def _function(names, function_id):
    node = names.nodes[function_id]
    return {"id": function_id, "short": names.short(function_id),
            "display": names.display(function_id), "file": node.file,
            "start_line": node.start_line, "end_line": node.end_line}


def _radius(radius, names):
    return {
        "callers": [{"id": c.id, "name": names.short(c.id), "file": c.file, "line": c.line,
                     "resolution": c.resolution} for c in radius.callers],
        "exported": radius.exported,
        "via_interface": radius.via_interface,
    }


def _test(test):
    return {"name": test.name, "file": test.file, "line": test.line}


def main(argv=None, out=None, err=None):
    out, err = out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--graph-dir", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--ignore-file", type=Path, default=analyze.DEFAULT_IGNORE_FILE)
    parser.add_argument("--judgements", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    findings_parser = commands.add_parser("findings", help="list the redundancy cards")
    card_parser = commands.add_parser("card", help="facts for one card")
    card_parser.add_argument("ref", help="card number or first~second")
    for sub in (findings_parser, card_parser):
        sub.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)
    try:
        found = load_session(args.graph_dir, args.source_root, args.ignore_file, args.judgements)
        if args.command == "findings":
            document = findings_document(found)
            text = findings_text(document)
        else:
            document = card_document(found, args.ref)
            text = card_text(document)
    except (CliError, build.GraphError) as error:
        print(f"error: {error}", file=err)
        return 2
    out.write(json.dumps(document, indent=2) + "\n" if args.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
