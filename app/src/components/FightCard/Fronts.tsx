// app/src/components/FightCard/Fronts.tsx
import React from "react";
import { fcColors, fcType, leansAccent, type Side } from "./styles";
import { FCEyebrow } from "./atoms";

export interface Front {
  id: string;
  ordinal: string;          // "01", "02"
  label: string;            // "WRIST FRONT"
  question: string;         // "Can Morozov set his hook before Ermes cups the wrist?"
  popular_take: string;     // 1-line crowd assumption
  counter_take: string;     // 1-line evidence-based pushback
  leans: Side;              // ermes | morozov | even
  claim_count: number;
}

interface FrontsProps {
  fronts: Front[];
  /** How many top fronts to show as headline cards. Rest collapsed. */
  headlineCount?: number;
}

export function Fronts({ fronts, headlineCount = 3 }: FrontsProps) {
  const [expanded, setExpanded] = React.useState(false);

  const headline = fronts.slice(0, headlineCount);
  const rest = fronts.slice(headlineCount);

  // Aggregate verdict across ALL fronts (not just headline)
  const totals = fronts.reduce(
    (acc, f) => {
      if (f.leans === "ermes") acc.e += f.claim_count;
      else if (f.leans === "morozov") acc.m += f.claim_count;
      else acc.x += f.claim_count;
      return acc;
    },
    { e: 0, m: 0, x: 0 }
  );
  const total = Math.max(1, totals.e + totals.m + totals.x);
  const ePct = Math.round((totals.e / total) * 100);
  const mPct = Math.round((totals.m / total) * 100);
  const xPct = 100 - ePct - mPct;

  // "Tape leans Ermes on N fronts, Morozov on N, even on N."
  const counts = fronts.reduce(
    (acc, f) => ({ ...acc, [f.leans]: (acc[f.leans] ?? 0) + 1 }),
    {} as Record<Side, number>
  );

  return (
    <div style={{ marginTop: 16, padding: 32, background: fcColors.bg, border: `1px solid ${fcColors.rule}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <FCEyebrow>THE FIGHT IS WON ON {fronts.length} FRONTS</FCEyebrow>
        <div style={{ ...fcType.mono, fontSize: 11, color: fcColors.muted, letterSpacing: "0.18em" }}>
          NO SINGLE QUESTION DECIDES IT
        </div>
      </div>

      <div style={{ ...fcType.display, fontSize: 30, marginTop: 6, color: fcColors.ink, textWrap: "balance", maxWidth: 760 }}>
        Tape leans <span style={{ color: fcColors.ermes }}>Ermes on {counts.ermes ?? 0}</span>,{" "}
        <span style={{ color: fcColors.morozov }}>Morozov on {counts.morozov ?? 0}</span>,{" "}
        <span style={{ color: fcColors.contested }}>even on {counts.even ?? 0}</span>.
      </div>

      {/* Aggregate verdict bar */}
      <div style={{ marginTop: 20 }}>
        <div style={{ display: "flex", height: 18, border: `1px solid ${fcColors.ruleStrong}` }}>
          <div
            style={{
              width: `${ePct}%`,
              background: fcColors.ermes,
              display: "grid",
              placeItems: "center",
              color: fcColors.bg,
              ...fcType.display,
              fontSize: 12,
            }}
          >
            {ePct > 12 ? `ERMES ${ePct}%` : ""}
          </div>
          <div
            style={{
              width: `${xPct}%`,
              background:
                "repeating-linear-gradient(45deg, #2a261f 0 6px, #16140f 6px 12px)",
            }}
          />
          <div
            style={{
              width: `${mPct}%`,
              background: fcColors.morozov,
              display: "grid",
              placeItems: "center",
              color: fcColors.bg,
              ...fcType.display,
              fontSize: 12,
            }}
          >
            {mPct > 12 ? `MOROZOV ${mPct}%` : ""}
          </div>
        </div>
        <div
          style={{
            ...fcType.mono,
            fontSize: 10,
            color: fcColors.muted,
            letterSpacing: "0.15em",
            marginTop: 6,
            textTransform: "uppercase",
          }}
        >
          AGGREGATE OF ALL {fronts.length} FRONTS · WEIGHTED BY CLAIM VOLUME
        </div>
      </div>

      {/* Headline fronts */}
      <div style={{ marginTop: 20 }}>
        {headline.map((f) => (
          <FrontRow key={f.id} f={f} />
        ))}
        <div style={{ borderTop: `1px solid ${fcColors.rule}` }} />
      </div>

      {/* Smaller battles, collapsed by default */}
      {rest.length > 0 && (
        <div style={{ marginTop: 18 }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: "transparent",
              border: `1px solid ${fcColors.ruleStrong}`,
              color: fcColors.ink,
              padding: "10px 16px",
              cursor: "pointer",
              ...fcType.mono,
              fontSize: 11,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              fontWeight: 600,
            }}
          >
            {expanded ? "− Hide smaller battles" : `+ ${rest.length} smaller battles`}
          </button>

          {expanded && (
            <div style={{ marginTop: 14 }}>
              {rest.map((f) => (
                <FrontMini key={f.id} f={f} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FrontRow({ f }: { f: Front }) {
  const accent = leansAccent(f.leans);
  const leansLabel =
    f.leans === "ermes" ? "→ ERMES" : f.leans === "morozov" ? "→ MOROZOV" : "→ TOO CLOSE";

  return (
    <div style={{ borderTop: `1px solid ${fcColors.rule}`, padding: "20px 0" }}>
      <div style={{ display: "grid", gridTemplateColumns: "60px 1fr 130px", gap: 16, alignItems: "start" }}>
        <div style={{ ...fcType.display, fontSize: 38, color: accent, lineHeight: 0.9 }}>
          {f.ordinal}
        </div>
        <div>
          <FCEyebrow color={accent}>
            {f.label} · {f.claim_count} claims
          </FCEyebrow>
          <div
            style={{
              ...fcType.display,
              fontSize: 24,
              marginTop: 6,
              color: fcColors.ink,
              textWrap: "balance",
              lineHeight: 1.05,
            }}
          >
            {f.question}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 14 }}>
            <div style={{ padding: "10px 12px", border: `1px dashed ${fcColors.ruleStrong}` }}>
              <FCEyebrow color={fcColors.muted}>CROWD</FCEyebrow>
              <div style={{ fontFamily: "Georgia, serif", fontSize: 13, color: fcColors.inkDim, marginTop: 6, lineHeight: 1.45 }}>
                "{f.popular_take}"
              </div>
            </div>
            <div style={{ padding: "10px 12px", border: `1px solid ${accent}`, background: "rgba(226,59,33,0.04)" }}>
              <FCEyebrow color={accent}>TAPE</FCEyebrow>
              <div style={{ fontFamily: "Georgia, serif", fontSize: 13, color: "#d6cdb9", marginTop: 6, lineHeight: 1.45 }}>
                "{f.counter_take}"
              </div>
            </div>
          </div>
        </div>
        <div style={{ textAlign: "right", paddingTop: 4 }}>
          <FCEyebrow color={fcColors.muted}>TAPE LEANS</FCEyebrow>
          <div style={{ ...fcType.display, fontSize: 18, color: accent, marginTop: 4, lineHeight: 1 }}>
            {leansLabel}
          </div>
        </div>
      </div>
    </div>
  );
}

function FrontMini({ f }: { f: Front }) {
  const accent = leansAccent(f.leans);
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto auto",
        gap: 14,
        padding: "10px 12px",
        borderBottom: `1px dashed ${fcColors.ruleStrong}`,
        alignItems: "center",
      }}
    >
      <div>
        <div style={{ ...fcType.display, fontSize: 16, color: fcColors.ink }}>{f.label}</div>
        <div
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 12,
            color: fcColors.inkDim,
            marginTop: 2,
            fontStyle: "italic",
          }}
        >
          {f.question}
        </div>
      </div>
      <div style={{ ...fcType.mono, fontSize: 11, color: fcColors.muted, letterSpacing: "0.14em" }}>
        {f.claim_count} claims
      </div>
      <div style={{ ...fcType.mono, fontSize: 11, color: accent, letterSpacing: "0.18em", fontWeight: 700 }}>
        {f.leans === "even" ? "→ EVEN" : f.leans === "ermes" ? "→ ERMES" : "→ MOROZOV"}
      </div>
    </div>
  );
}
