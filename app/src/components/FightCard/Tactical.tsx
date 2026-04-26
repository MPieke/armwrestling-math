// app/src/components/FightCard/Tactical.tsx
import React from "react";
import { fcColors, fcType } from "./styles";
import { FCEyebrow } from "./atoms";
import { ClaimReceipts } from "./ClaimReceipts";
import type { Claim } from "../../types";

interface TacticalProps {
  claims: Claim[];
  athleteA: string; // "Ermes Gasparini"
  athleteB: string; // "Artyom Morozov"
}

interface MoveRow {
  key: string;
  move: string;
  lane: string;
  count: number;
  claimIndexes: number[];
}

function moveKey(actor: string, action: string): string {
  return `${actor}::${action}`;
}

/**
 * Aggregates mechanism atoms into per-side move counts.
 * Splits actors into A / B / shared.
 */
function aggregateMoves(claims: Claim[], a: string, b: string) {
  const buckets: Record<"a" | "b" | "shared", Map<string, MoveRow>> = {
    a: new Map(),
    b: new Map(),
    shared: new Map(),
  };

  for (const c of claims) {
    for (const atom of c.mechanism_atoms ?? []) {
      const actorLower = (atom.actor || "").toLowerCase();
      let bucket: "a" | "b" | "shared" = "shared";
      if (actorLower.includes(a.split(" ")[0].toLowerCase())) bucket = "a";
      else if (actorLower.includes(b.split(" ")[0].toLowerCase())) bucket = "b";

      const key = moveKey(atom.actor, atom.action);
      const existing = buckets[bucket].get(key);
      if (existing) {
        existing.count += 1;
        if (!existing.claimIndexes.includes(c.evidence_index)) existing.claimIndexes.push(c.evidence_index);
      }
      else
        buckets[bucket].set(key, {
          key: `${bucket}::${key}`,
          move: atom.action || "unspecified",
          lane: atom.lane || "unknown",
          count: 1,
          claimIndexes: [c.evidence_index],
        });
    }
  }

  const sortRows = (m: Map<string, MoveRow>) =>
    Array.from(m.values()).sort((x, y) => y.count - x.count);

  return {
    a: sortRows(buckets.a),
    b: sortRows(buckets.b),
    shared: sortRows(buckets.shared),
  };
}

export function Tactical({ claims, athleteA, athleteB }: TacticalProps) {
  const [openMoveKey, setOpenMoveKey] = React.useState<string | null>(null);
  const claimsByIndex = React.useMemo(
    () => new Map(claims.map((claim) => [claim.evidence_index, claim])),
    [claims],
  );
  const moves = React.useMemo(
    () => aggregateMoves(claims, athleteA, athleteB),
    [claims, athleteA, athleteB]
  );

  return (
    <div style={{ marginTop: 16, padding: 28, background: fcColors.bg, border: `1px solid ${fcColors.rule}` }}>
      <FCEyebrow>HOW EACH ATHLETE WINS</FCEyebrow>
      <div style={{ ...fcType.display, fontSize: 26, marginTop: 6, marginBottom: 20 }}>
        The toolkit.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", border: `1px solid ${fcColors.ruleStrong}` }}>
        {[
          { color: fcColors.ermes, name: athleteA.toUpperCase(), moves: moves.a },
          { color: fcColors.morozov, name: athleteB.toUpperCase(), moves: moves.b },
        ].map((col, i) => (
          <div key={col.name} style={{ padding: 20, borderLeft: i ? `1px solid ${fcColors.ruleStrong}` : "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div style={{ width: 12, height: 12, background: col.color }} />
              <div style={{ ...fcType.display, fontSize: 18 }}>{col.name}</div>
            </div>
            {col.moves.length === 0 && (
              <div style={{ color: fcColors.muted, fontSize: 12, fontFamily: "Georgia, serif", fontStyle: "italic" }}>
                No tactical moves attributed yet.
              </div>
            )}
            {col.moves.map((mv) => {
              const open = openMoveKey === mv.key;
              const receipts = mv.claimIndexes
                .map((index) => claimsByIndex.get(index))
                .filter((claim): claim is Claim => Boolean(claim));

              return (
              <div key={`${col.name}-${mv.move}`}>
                <button
                  type="button"
                  onClick={() => setOpenMoveKey(open ? null : mv.key)}
                  aria-expanded={open}
                key={`${col.name}-${mv.move}`}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  padding: "10px 0",
                  borderBottom: `1px dashed ${fcColors.rule}`,
                  textAlign: "left",
                }}
              >
                <div>
                  <div style={{ ...fcType.display, fontSize: 16, color: fcColors.ink }}>
                    {mv.move}
                  </div>
                  <div
                    style={{
                      ...fcType.mono,
                      fontSize: 10,
                      color: fcColors.muted,
                      letterSpacing: "0.15em",
                      textTransform: "uppercase",
                    }}
                  >
                    {mv.lane}
                  </div>
                </div>
                <div style={{ ...fcType.display, fontSize: 18, color: col.color }}>
                  {open ? "VIEWING" : `×${mv.count}`}
                </div>
                </button>
                {open && (
                  <div style={{ padding: "8px 0 16px" }}>
                    <ClaimReceipts claims={receipts} accent={col.color} maxHeight={360} />
                  </div>
                )}
              </div>
            )})}
          </div>
        ))}
      </div>

      {moves.shared.length > 0 && (
        <div style={{ marginTop: 14, padding: 12, background: fcColors.bgRaised, border: `1px solid ${fcColors.ruleStrong}` }}>
          <FCEyebrow color={fcColors.muted}>
            CONTESTED GROUND · {moves.shared.length} moves
          </FCEyebrow>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {moves.shared.map((mv) => {
              const open = openMoveKey === mv.key;
              const receipts = mv.claimIndexes
                .map((index) => claimsByIndex.get(index))
                .filter((claim): claim is Claim => Boolean(claim));

              return (
              <div key={mv.key}>
              <button
                type="button"
                onClick={() => setOpenMoveKey(open ? null : mv.key)}
                aria-expanded={open}
                style={{
                  ...fcType.mono,
                  fontSize: 11,
                  padding: "6px 10px",
                  background: fcColors.bg,
                  border: `1px solid ${fcColors.ruleStrong}`,
                  color: open ? fcColors.contested : fcColors.inkDim,
                  cursor: "pointer",
                }}
              >
                {mv.move.toUpperCase()}
              </button>
              {open && (
                <div style={{ flexBasis: "100%", marginTop: 8 }}>
                  <ClaimReceipts claims={receipts} accent={fcColors.contested} maxHeight={360} />
                </div>
              )}
              </div>
            )})}
          </div>
        </div>
      )}
    </div>
  );
}
