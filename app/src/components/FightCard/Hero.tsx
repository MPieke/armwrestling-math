// app/src/components/FightCard/Hero.tsx
import React from "react";
import { fcColors, fcType } from "./styles";
import { FCEyebrow } from "./atoms";
import type { MatchInfo } from "../../types";

interface HeroProps {
  match: MatchInfo;
  // Optional tape-of-the-tape rows. If absent, we render only the marquee.
  tape?: Array<{ label: string; left: string | number; right: string | number }>;
  generatedAt?: string;
}

export function FightCardHero({ match, tape, generatedAt }: HeroProps) {
  // Naively split the names — the synthesis output should give first/last cleanly.
  const [aFirst, ...aRest] = match.athlete_a.split(" ");
  const [bFirst, ...bRest] = match.athlete_b.split(" ");
  const aLast = aRest.join(" ");
  const bLast = bRest.join(" ");

  return (
    <div
      style={{
        background: fcColors.bg,
        border: `1px solid ${fcColors.rule}`,
        padding: "32px 28px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 28,
        }}
      >
        <FCEyebrow>EVW · KOTT · NARRATIVE CHECK</FCEyebrow>
        <div
          style={{
            ...fcType.mono,
            fontSize: 11,
            color: fcColors.muted,
            letterSpacing: "0.15em",
            textTransform: "uppercase",
          }}
        >
          {match.event_context} · {match.arm}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          gap: 16,
          alignItems: "center",
        }}
      >
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              ...fcType.mono,
              color: fcColors.muted,
              fontSize: 11,
              letterSpacing: "0.2em",
              marginBottom: 6,
            }}
          >
            RED CORNER
          </div>
          <div style={{ ...fcType.display, fontSize: 76, color: fcColors.ink }}>{aFirst}</div>
          <div
            style={{ ...fcType.display, fontSize: 76, color: fcColors.ermes, marginTop: -6 }}
          >
            {aLast}
          </div>
        </div>

        <div
          style={{
            ...fcType.display,
            fontSize: 90,
            color: "#3a3733",
            textAlign: "center",
            padding: "0 4px",
          }}
        >
          VS
        </div>

        <div style={{ textAlign: "left" }}>
          <div
            style={{
              ...fcType.mono,
              color: fcColors.muted,
              fontSize: 11,
              letterSpacing: "0.2em",
              marginBottom: 6,
            }}
          >
            BLUE CORNER
          </div>
          <div style={{ ...fcType.display, fontSize: 76, color: fcColors.ink }}>{bFirst}</div>
          <div
            style={{ ...fcType.display, fontSize: 76, color: fcColors.morozov, marginTop: -6 }}
          >
            {bLast}
          </div>
        </div>
      </div>

      {tape && tape.length > 0 && (
        <div style={{ marginTop: 32, border: `1px solid ${fcColors.rule}`, padding: "18px 0" }}>
          {tape.map((row, i) => (
            <div
              key={row.label}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 120px 1fr",
                padding: "10px 24px",
                borderTop: i ? `1px dashed ${fcColors.rule}` : "none",
              }}
            >
              <div style={{ ...fcType.display, fontSize: 22, textAlign: "right" }}>
                {row.left}
              </div>
              <div
                style={{
                  ...fcType.mono,
                  fontSize: 11,
                  color: fcColors.muted,
                  textAlign: "center",
                  alignSelf: "center",
                  letterSpacing: "0.2em",
                  textTransform: "uppercase",
                }}
              >
                {row.label}
              </div>
              <div style={{ ...fcType.display, fontSize: 22, textAlign: "left" }}>
                {row.right}
              </div>
            </div>
          ))}
        </div>
      )}

      {generatedAt && (
        <div
          style={{
            ...fcType.mono,
            fontSize: 10,
            color: fcColors.muted,
            letterSpacing: "0.18em",
            marginTop: 14,
            textAlign: "right",
          }}
        >
          DOSSIER · {new Date(generatedAt).toLocaleDateString()}
        </div>
      )}
    </div>
  );
}
