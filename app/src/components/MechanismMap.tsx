import type { Claim, MatchInfo, MechanismAtom } from "../types";

export interface MechanismSelection {
  key: string;
  label: string;
}

interface MechanismNode {
  key: string;
  actor: string;
  action: string;
  lane: string;
  claimIndexes: number[];
  currentUsableCount: number;
  confidence: string;
}

function normalizeActor(actor: string, match: MatchInfo) {
  const lowered = actor.toLowerCase();
  if (lowered.includes("ermes") || lowered.includes("gasparini")) {
    return match.athlete_a;
  }
  if (lowered.includes("morozov") || lowered.includes("artyom")) {
    return match.athlete_b;
  }
  return actor || "Unassigned";
}

function atomKey(atom: MechanismAtom, match: MatchInfo) {
  return [
    normalizeActor(atom.actor, match),
    atom.action || "unknown action",
    atom.lane || "unknown lane",
  ].join("::");
}

function buildMechanismNodes(claims: Claim[], match: MatchInfo) {
  const nodes = new Map<string, MechanismNode>();

  for (const claim of claims) {
    for (const atom of claim.mechanism_atoms) {
      const key = atomKey(atom, match);
      const node = nodes.get(key) ?? {
        key,
        actor: normalizeActor(atom.actor, match),
        action: atom.action || "unknown action",
        lane: atom.lane || "unknown lane",
        claimIndexes: [],
        currentUsableCount: 0,
        confidence: atom.confidence || "unknown",
      };

      if (!node.claimIndexes.includes(claim.evidence_index)) {
        node.claimIndexes.push(claim.evidence_index);
      }
      if (atom.current_form_usable) {
        node.currentUsableCount += 1;
      }
      nodes.set(key, node);
    }
  }

  return [...nodes.values()].sort((a, b) => b.claimIndexes.length - a.claimIndexes.length);
}

function NodeButton({
  node,
  selected,
  onSelect,
}: {
  node: MechanismNode;
  selected: boolean;
  onSelect: (selection: MechanismSelection) => void;
}) {
  return (
    <button
      type="button"
      className={`mechanism-node ${selected ? "selected" : ""}`}
      onClick={() => onSelect({ key: node.key, label: `${node.actor}: ${node.action} (${node.lane})` })}
    >
      <span>{node.actor}</span>
      <strong>{node.action.replaceAll("_", " ")}</strong>
      <em>{node.lane}</em>
      <small>
        {node.claimIndexes.length} claims, {node.currentUsableCount} current
      </small>
    </button>
  );
}

export function MechanismMap({
  claims,
  match,
  selection,
  onSelect,
  onClear,
}: {
  claims: Claim[];
  match: MatchInfo;
  selection: MechanismSelection | null;
  onSelect: (selection: MechanismSelection) => void;
  onClear: () => void;
}) {
  const nodes = buildMechanismNodes(claims, match);
  const ermesNodes = nodes.filter((node) => node.actor === match.athlete_a).slice(0, 8);
  const morozovNodes = nodes.filter((node) => node.actor === match.athlete_b).slice(0, 8);
  const sharedNodes = nodes
    .filter((node) => node.actor !== match.athlete_a && node.actor !== match.athlete_b)
    .slice(0, 6);

  return (
    <section className="panel mechanism-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Mechanism Map</p>
          <h2>Argument paths you can inspect</h2>
        </div>
        {selection ? (
          <button type="button" className="clear-button" onClick={onClear}>
            Clear filter
          </button>
        ) : (
          <p className="muted">Tap a node to filter the evidence library.</p>
        )}
      </div>

      <div className="mechanism-map">
        <div className="mechanism-lane ermes-lane">
          <h3>{match.athlete_a}</h3>
          {ermesNodes.map((node) => (
            <NodeButton key={node.key} node={node} selected={selection?.key === node.key} onSelect={onSelect} />
          ))}
        </div>

        <div className="mechanism-lane middle-lane">
          <h3>Unassigned / contested</h3>
          {sharedNodes.length ? (
            sharedNodes.map((node) => (
              <NodeButton key={node.key} node={node} selected={selection?.key === node.key} onSelect={onSelect} />
            ))
          ) : (
            <p className="muted">No unassigned mechanism atoms in this dataset.</p>
          )}
        </div>

        <div className="mechanism-lane morozov-lane">
          <h3>{match.athlete_b}</h3>
          {morozovNodes.map((node) => (
            <NodeButton key={node.key} node={node} selected={selection?.key === node.key} onSelect={onSelect} />
          ))}
        </div>
      </div>

      {selection ? <p className="selected-note">Filtering claims by {selection.label}</p> : null}
    </section>
  );
}
