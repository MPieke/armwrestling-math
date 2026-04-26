// app/src/components/FightCard/Pickem.tsx
import React, { useEffect, useState } from "react";
import { fcColors, fcType } from "./styles";
import { FCEyebrow } from "./atoms";

interface PickemProps {
  athleteA: string;
  athleteB: string;
  matchId: string; // used for localStorage key
  /** Optional pre-fight crowd sentiment, 0–100 each, must sum to 100 */
  crowd?: { aPct: number; bPct: number; sample: string };
}

interface PickState {
  pick: "a" | "b" | null;
  conf: number;
}

export function Pickem({ athleteA, athleteB, matchId, crowd }: PickemProps) {
  const storageKey = `narrative-check:pick:${matchId}`;
  const [state, setState] = useState<PickState>({ pick: null, conf: 50 });

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) setState(JSON.parse(raw) as PickState);
    } catch {
      /* ignore */
    }
  }, [storageKey]);

  function update(next: PickState) {
    setState(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }

  const accent = state.pick === "a" ? fcColors.ermes : state.pick === "b" ? fcColors.morozov : fcColors.muted;

  return (
    <div style={{ background: fcColors.bgRaised, padding: 28, marginTop: 16 }}>
      <FCEyebrow>WHO YOU GOT?</FCEyebrow>
      <div style={{ ...fcType.display, fontSize: 30, marginTop: 6, marginBottom: 18 }}>
        Lock your pick before you read the evidence.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", border: `1px solid ${fcColors.ruleStrong}` }}>
        {[
          { id: "a" as const, name: athleteA, color: fcColors.ermes, label: "RED CORNER" },
          { id: "b" as const, name: athleteB, color: fcColors.morozov, label: "BLUE CORNER" },
        ].map((side) => {
          const active = state.pick === side.id;
          return (
            <button
              key={side.id}
              onClick={() => update({ ...state, pick: side.id })}
              style={{
                background: active ? side.color : "transparent",
                color: active ? fcColors.bg : fcColors.ink,
                border: "none",
                padding: "20px 18px",
                cursor: "pointer",
                textAlign: "left",
                ...fcType.display,
                fontSize: 24,
                transition: "background 0.15s",
              }}
            >
              <div
                style={{
                  ...fcType.mono,
                  fontSize: 11,
                  letterSpacing: "0.2em",
                  color: active ? fcColors.bg : fcColors.muted,
                  marginBottom: 6,
                }}
              >
                {side.label}
              </div>
              {side.name}
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <FCEyebrow color={fcColors.muted}>CONFIDENCE</FCEyebrow>
          <div style={{ ...fcType.display, fontSize: 16 }}>{state.conf}%</div>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={state.conf}
          onChange={(e) => update({ ...state, conf: Number(e.target.value) })}
          style={{ width: "100%", accentColor: accent }}
        />
      </div>

      {crowd && (
        <div style={{ marginTop: 22 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <FCEyebrow color={fcColors.muted}>CROWD VOTE · {crowd.sample}</FCEyebrow>
            <div style={{ ...fcType.mono, fontSize: 11, color: fcColors.muted }}>
              {crowd.aPct}% / {crowd.bPct}%
            </div>
          </div>
          <div style={{ height: 14, display: "flex", border: `1px solid ${fcColors.ruleStrong}` }}>
            <div style={{ width: `${crowd.aPct}%`, background: fcColors.ermes }} />
            <div style={{ width: `${crowd.bPct}%`, background: fcColors.morozov }} />
          </div>
        </div>
      )}
    </div>
  );
}
