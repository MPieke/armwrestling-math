"""Diagrams for redundancy cards, built by code from validated data.

The LLM never draws anything. It supplies steps (with source line ranges),
issue notes and a proposed fix; ``judge.py`` checks those against the real
source, and this module turns what survived into a small model that
``to_mermaid`` prints.

* ``before``: one chain of steps per function, matched steps linked by a dotted
  "same" edge, numbered issue markers on the steps the model flagged.
* ``apply_fix``: the same diagram after the proposed fix, derived from it: the
  moved steps of both functions become one new shared node.
* ``two_routes``: one function reaching the same code directly and through a
  helper.
"""

from dataclasses import dataclass

MAX_STEPS = 12  # steps drawn per function before the chain is cut

_STYLES = {
    "function": "fill:#dbeafe,stroke:#1d4ed8,color:#000",
    "same": "fill:#ffd6a5,stroke:#b45309,color:#000",
    "differs": "fill:#e5e7eb,stroke:#6b7280,color:#000",
    "helper": "fill:#e5e7eb,stroke:#6b7280,color:#000",
    "target": "fill:#c7f9cc,stroke:#15803d,color:#000",
    "problem": "stroke:#b91c1c,stroke-width:3px",
    "new": "stroke-dasharray: 5 5",
}


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    role: str
    issues: tuple = ()
    dashed: bool = False  # a node that does not exist yet (the shared function after the fix)
    problem: bool = False  # part of the duplicated problem (moved by the fix, or noted by the model)
    detail: str = ""  # second line of the box: the code behind the step


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    style: str = "solid"
    label: str = ""


@dataclass(frozen=True)
class Diagram:
    nodes: tuple
    edges: tuple
    legend: tuple = ()
    note: str = ""
    direction: str = "LR"  # step chains run "TB": a pipeline reads better in two columns


def before(steps, issues, names, moved=(), refs=None):
    """Step chains for both functions, or None when there is too little to draw.

    ``moved`` are the step names the fix would move into a shared function; they and
    any step the model left a note on are marked as part of the problem. ``refs`` maps
    (side, step name) to the code detail shown on a second line of the box.
    """
    if len(steps) < 2:
        return None
    accepted = _accepted_issues(steps, issues)
    nodes = [Node("hA", names["A"], "function"), Node("hB", names["B"], "function")]
    edges, chains, truncated = [], {"A": ["hA"], "B": ["hB"]}, False
    for index, step in enumerate(steps):
        for side, key in (("A", "a"), ("B", "b")):
            if step[key] is None:
                continue
            if len(chains[side]) > MAX_STEPS:
                truncated = True
                continue
            marks = tuple(
                number for number, name, which, _ in accepted
                if name == step["name"] and which in (side, "both")
            )
            label = step["name"] + (f" ({', '.join(map(str, marks))})" if marks else "")
            node_id = f"{key}{index}"
            nodes.append(Node(
                node_id, label, "same" if step["same"] else "differs", marks,
                problem=bool(marks) or step["name"] in moved,
                detail=(refs or {}).get((side, step["name"]), ""),
            ))
            edges.append(Edge(chains[side][-1], node_id))
            chains[side].append(node_id)
        if step["same"] and f"a{index}" in {n.id for n in nodes} and f"b{index}" in {n.id for n in nodes}:
            edges.append(Edge(f"a{index}", f"b{index}", "dotted", "same"))
    legend = tuple((number, note) for number, _, _, note in accepted)
    note = f"showing the first {MAX_STEPS} steps of each function" if truncated else ""
    return Diagram(tuple(nodes), tuple(edges), legend, note, "TB")


def _accepted_issues(steps, issues):
    """[(number, step name, "A"|"B"|"both", note)] for issues on a real step and side."""
    by_name = {step["name"]: step for step in steps}
    accepted = []
    for issue in issues:
        step = by_name.get(issue["step"])
        if step is None:
            continue
        side = issue["function"]
        present = {"A": step["a"] is not None, "B": step["b"] is not None}
        if present["A"] or present["B"] if side == "both" else present.get(side):
            accepted.append((len(accepted) + 1, issue["step"], side, issue["note"]))
    return accepted


def apply_fix(diagram, fix, steps, refs=None):
    """The diagram after the fix: moved steps of both functions merge into one shared node.

    Steps that stay keep their colour; the shared node takes the colour of the
    duplicates it merges and is dashed because it is new. Nothing is marked as a problem.
    """
    known = {step["name"] for step in steps}
    moved = [name for name in fix["moved_steps"] if name in known]
    if diagram is None or not moved:
        return None
    shared = Node("shared", fix["shared_name"] or "shared function", "same", dashed=True)
    names = {n.id: n.label for n in diagram.nodes if n.role == "function"}
    nodes = [Node("hA", names["hA"], "function"), Node("hB", names["hB"], "function")]
    edges, used_shared = [], False
    for side, key in (("A", "a"), ("B", "b")):
        previous, inserted, count = f"h{side}", False, 0
        for index, step in enumerate(steps):
            if step[key] is None:
                continue
            if step["name"] in moved:
                if not inserted:
                    edges.append(Edge(previous, "shared"))
                    previous, inserted, used_shared = "shared", True, True
                continue
            if count >= MAX_STEPS:
                break
            node_id = f"{key}{index}"
            nodes.append(Node(
                node_id, step["name"], "same" if step["same"] else "differs",
                detail=(refs or {}).get((side, step["name"]), ""),
            ))
            edges.append(Edge(previous, node_id))
            previous, count = node_id, count + 1
    if used_shared:
        nodes.append(shared)
    return Diagram(tuple(nodes), tuple(dict.fromkeys(edges)), (), "", "TB")


def two_routes(owner, helper, targets):
    nodes = [Node("owner", owner, "function"), Node("helper", helper, "helper")]
    edges = [Edge("owner", "helper")]
    for index, target in enumerate(targets):
        nodes.append(Node(f"target{index}", target, "target"))
        edges.append(Edge("helper", f"target{index}"))
        edges.append(Edge("owner", f"target{index}", label="directly"))
    return Diagram(tuple(nodes), tuple(edges))


def to_mermaid(diagram):
    ids = {node.id: f"n{position}" for position, node in enumerate(diagram.nodes)}
    lines = [f"flowchart {diagram.direction}"]
    lines += [f'  {ids[node.id]}["{_box_text(node)}"]' for node in diagram.nodes]
    for edge in diagram.edges:
        source, target = ids[edge.source], ids[edge.target]
        if edge.style == "dotted":
            lines.append(f"  {source} -. {edge.label} .- {target}" if edge.label else f"  {source} -.- {target}")
        elif edge.label:
            lines.append(f"  {source} -->|{_escape(edge.label)}| {target}")
        else:
            lines.append(f"  {source} --> {target}")
    roles = {node.role for node in diagram.nodes}
    if any(node.problem for node in diagram.nodes):
        roles.add("problem")
    if any(node.dashed for node in diagram.nodes):
        roles.add("new")
    lines += [f"  classDef {role} {_STYLES[role]}" for role in _STYLES if role in roles]
    for role in _STYLES:
        if role == "problem":
            members = [ids[n.id] for n in diagram.nodes if n.problem]
        elif role == "new":
            members = [ids[n.id] for n in diagram.nodes if n.dashed]
        else:
            members = [ids[n.id] for n in diagram.nodes if n.role == role]
        if members:
            lines.append(f"  class {','.join(members)} {role}")
    return "\n".join(lines)


def _box_text(node):
    text = _escape(node.label)
    return f"{text}<br/>{_escape(node.detail)}" if node.detail else text


def _escape(text):
    return text.replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;")


__all__ = ["Diagram", "Edge", "MAX_STEPS", "Node", "apply_fix", "before", "to_mermaid", "two_routes"]
