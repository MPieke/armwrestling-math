"""Render the call graph as Graphviz DOT and a GitHub-friendly Markdown summary."""

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path

from tools.callgraph import analyze, build, cards

TOP_ROWS = 15
DEFAULT_MAX_FINDINGS = 10
DIAGRAM_NODE_CAP = 24
MAX_LISTED_CALLS = 6
COLLAPSE_AFTER = 2  # interior functions kept on a route before it is shortened
LLM_TEXT_LIMIT = 400
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
    judgements=None,
    ignored_packages=(),
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
        found = cards.build_cards(graph, analysis, ignored_packages)
        parts += _cards_section(graph, found, labels, repo_url, max_findings, judgements)
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

    def short(self, node_id):
        """The name without its package path, unless that would be ambiguous."""
        node = self.nodes.get(node_id)
        if node is None:
            return node_id
        prefix = node.package + "."
        rest = node.id[len(prefix):] if node.id.startswith(prefix) else node.id
        clashes = sum(
            1 for other in self.nodes.values()
            if (other.id[len(other.package) + 1:] if other.id.startswith(other.package + ".")
                else other.id) == rest
        )
        return rest if clashes == 1 else self.display(node_id)

    def link(self, node_id):
        node = self.nodes.get(node_id)
        if node is None:
            return self.display(node_id)
        url = source_url(self.repo_url, node.sha, node.file, node.start_line, node.end_line)
        return f"[{_table_text(self.display(node_id))}]({url})"


def _cards_section(graph, found, labels, repo_url, max_cards, judgements):
    names = _Names(graph, labels, repo_url)
    verdicts = {(j["first"], j["second"]): j for j in (judgements or {}).get("judgements", [])}
    out = [
        "### Redundant routes",
        "",
        "Each card is a pair of functions that reach the same code on separate routes, "
        "with the evidence for whether they do the same job. Reusing a shared helper is "
        "normal; the question is whether the two functions are really one.",
        "",
    ]
    out += _judge_status(judgements)
    out += _calibration_banner((judgements or {}).get("calibration"))
    if not found:
        return out + ["No redundant routes found.", ""]
    for rank, card in enumerate(found[:max_cards], start=1):
        out += _card(rank, card, names, verdicts.get((card.first, card.second)), judgements)
    if len(found) > max_cards:
        out += [f"_showing first {max_cards} of {len(found)} cards_", ""]
    return out


def _judge_status(judgements):
    status = (judgements or {}).get("status")
    if status in ("skipped", "unavailable"):
        return [f"LLM judge {status} ({_text(judgements.get('reason', ''))})", ""]
    return []


def _calibration_banner(calibration):
    if not calibration:
        return []
    agree, total = calibration["agree"], calibration["total"]
    line = f"LLM calibration: {agree} of {total} reference cases agree with the human labels."
    if total and agree * 3 < total * 2:
        line += " The LLM verdicts below are unreliable."
    return [line, ""]


def _card(rank, card, names, verdict, judgements):
    first, second = names.display(card.first), names.display(card.second)
    targets = ", ".join(f"`{names.display(t)}`" for t in card.targets)
    reached = dict(card.reached_from)

    def entries_of(function_id):
        return ", ".join(f"`{names.display(e)}`" for e in reached[function_id]) or "no entry point"

    out = [
        f"#### {rank}. `{names.short(card.first)}` and `{names.short(card.second)}`",
        "",
        f"`{first}` and `{second}` each reach {targets} on separate routes "
        "(the routes share no function on the way in).",
        "",
        f"- `{first}` is reached from {entries_of(card.first)}; "
        f"`{second}` is reached from {entries_of(card.second)}.",
    ]
    out += _evidence_lines(card, names, first, second)
    out += ["", "```mermaid", _card_diagram(card, names), "```", ""]
    if verdict is not None:
        out += _verdict_lines(verdict)
    out += _card_details(card, names)
    return out


def _evidence_lines(card, names, first, second):
    evidence = card.evidence
    shared = [f"`{names.display(c)}`" for c in evidence.shared_callees]
    shared += _external_labels(evidence.shared_externals)
    lines = []
    if shared:
        lines.append(f"- Both also call: {', '.join(shared)}.")
    else:
        lines.append("- They share no calls apart from the targets.")
    for name, calls in ((first, evidence.only_first), (second, evidence.only_second)):
        if calls:
            lines.append(f"- Only `{name}` calls: {_limited(_calls_labels(calls, names))}.")
    percent = round(evidence.similarity * 100)
    lines.append(f"- Call overlap: {evidence.band} ({percent}% of their calls in common).")
    return lines


def _calls_labels(calls, names):
    """Repo functions and external functions mixed in one sorted list of labels."""
    labels = []
    externals = []
    for call in calls:
        if call in names.nodes:
            labels.append(f"`{names.display(call)}`")
        else:
            externals.append(call)
    return labels + _external_labels(externals)


def _limited(labels):
    shown = labels[:MAX_LISTED_CALLS]
    extra = len(labels) - len(shown)
    return ", ".join(shown) + (f" and {extra} more" if extra > 0 else "")


def _external_labels(names):
    """External functions as `pkg.Name`; several variants of one name are collapsed."""
    by_final = {}
    for name in names:
        label = name.rsplit("/", 1)[-1]
        by_final.setdefault(label.rsplit(".", 1)[-1], []).append(label)
    out = []
    for final in sorted(by_final):
        labels = sorted(set(by_final[final]))
        out.append(f"`{final}` ({len(labels)} variants)" if len(labels) > 1 else f"`{labels[0]}`")
    return out


def _card_diagram(card, names):
    """Mermaid flowchart of just this card's routes, with gateways and targets highlighted."""
    ids, labels, edges = {}, {}, []

    def node(key, label):
        if key not in ids:
            ids[key] = f"n{len(ids)}"
            labels[ids[key]] = label
        return ids[key]

    entry_ids, shown = set(), 0
    for number, route in enumerate(card.routes):
        steps = _diagram_steps(route, number, names)
        keys = [(key, label) for key, label in steps]
        if len({*ids, *(k for k, _ in keys)}) > DIAGRAM_NODE_CAP:
            break
        shown += 1
        previous = None
        for key, label in keys:
            current = node(key, label)
            if previous is not None and (previous, current) not in edges:
                edges.append((previous, current))
            previous = current
        entry_ids.add(ids[keys[0][0]])
    gateways = {ids[f] for f in (card.first, card.second) if f in ids}
    targets = {ids[t] for t in card.targets if t in ids}
    lines = ["flowchart LR"]
    lines += [f'  {node_id}["{_mermaid_text(label)}"]' for node_id, label in labels.items()]
    lines += [f"  {a} --> {b}" for a, b in edges]
    if shown < len(card.routes):
        lines.append(f'  more["... {len(card.routes) - shown} more routes not drawn"]')
    lines += [
        "  classDef entry fill:#dbeafe,stroke:#1d4ed8,color:#000",
        "  classDef gateway fill:#ffd6a5,stroke:#b45309,color:#000",
        "  classDef target fill:#c7f9cc,stroke:#15803d,color:#000",
    ]
    for role, members in (("entry", entry_ids - gateways - targets), ("gateway", gateways),
                          ("target", targets)):
        if members:
            lines.append(f"  class {','.join(sorted(members))} {role}")
    return "\n".join(lines)


def _diagram_steps(route, number, names):
    """(key, label) per node; a long stretch between the entry and the gateway is collapsed."""
    interior = route[1:-2]
    if len(interior) > COLLAPSE_AFTER:
        head = [(route[0], names.display(route[0]))]
        collapsed = [(("collapsed", route[0], route[-2]), f"... {len(interior)} functions")]
        tail = [(step, names.display(step)) for step in route[-2:]]
        return head + collapsed + tail
    return [(step, names.display(step)) for step in route]


def _card_details(card, names):
    out = ["<details><summary>Details: routes and sources</summary>", ""]
    for route in card.routes:
        out.append("- " + " > ".join(names.display(step) for step in route))
    out += ["", "Sources: " + " | ".join(names.link(f) for f in (card.first, card.second)), "",
            "</details>", ""]
    return out


def _verdict_lines(verdict):
    if verdict.get("status") != "ok":
        reason = _text(verdict.get("reason", "no reason given"))
        return [f"LLM verdict: unavailable ({reason})", ""]
    head = (
        f"**LLM verdict (advisory): {_text(verdict['verdict'])} "
        f"({_text(verdict['confidence'])} confidence)** - {_text(verdict['summary'])}"
    )
    valid, invalid = verdict.get("citations_valid", 0), verdict.get("citations_invalid", 0)
    out = [head, "", "<details><summary>LLM reasoning</summary>", ""]
    if verdict.get("essential_differences"):
        out.append("- Essential differences: " + "; ".join(_text(d) for d in verdict["essential_differences"]))
    if verdict.get("accidental_differences"):
        out.append("- Accidental differences: " + "; ".join(_text(d) for d in verdict["accidental_differences"]))
    if verdict.get("counter_argument"):
        out.append("- Strongest case for keeping them separate: " + _text(verdict["counter_argument"]))
    if verdict.get("suggested_consolidation"):
        out.append("- Suggested consolidation: " + _text(verdict["suggested_consolidation"]))
    if verdict.get("risks"):
        out.append("- Risks: " + "; ".join(_text(r) for r in verdict["risks"]))
    out += [f"- {valid} of {valid + invalid} citations verified against the source.", "",
            "</details>", ""]
    return out


def _text(value):
    """Model output as inert text: HTML-escaped, no link syntax, one line, length-capped."""
    text = html.escape(str(value), quote=False).replace("\n", " ")
    text = text.replace("[", "\\[").replace("]", "\\]")
    return text if len(text) <= LLM_TEXT_LIMIT else text[:LLM_TEXT_LIMIT] + "..."


def load_judgements(path):
    """judgements.json if present, else None. A malformed file is ignored, not fatal."""
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


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
    parser.add_argument("--judgements", type=Path, help="judgements.json from judge.py")
    args = parser.parse_args(argv)

    externals = args.graph_dir / "externals.csv"
    graph = build.load_graph(
        (args.graph_dir / "nodes.csv").read_text(),
        (args.graph_dir / "edges.csv").read_text(),
        externals.read_text() if externals.exists() else None,
    )
    ignored = analyze.parse_ignore_file(args.ignore_file.read_text())
    analysis = analyze.analyze(
        graph,
        ignored_packages=ignored,
        min_entries=args.min_entries,
        min_gateways=args.min_gateways,
    )
    judgements_path = args.judgements or args.graph_dir / "judgements.json"
    (args.graph_dir / "callgraph.dot").write_text(to_dot(graph, args.repo_url))
    (args.graph_dir / "summary.md").write_text(
        summary_markdown(
            graph, args.repo_url, analysis=analysis, max_findings=args.max_findings,
            judgements=load_judgements(judgements_path), ignored_packages=ignored,
        )
    )
    print(f"wrote callgraph.dot and summary.md to {args.graph_dir}")


if __name__ == "__main__":
    main()
