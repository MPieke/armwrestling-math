// app/src/components/FightCard/EvidenceStrip.tsx
// Compressed top stat strip — promote 1 hero stat, demote others.
import React from "react";
import { fcColors, fcType } from "./styles";
import { FCEyebrow } from "./atoms";
import type { Summary } from "../../types";

interface EvidenceStripProps {
  summary: Summary;
  generatedAt: string;
}

export function EvidenceStrip({ summary, generatedAt }: EvidenceStripProps) {
  const dateStr = new Date(generatedAt).toLocaleDateString("en-GB");
  const histCount = summary.claim_count - summary.current_form_claim_count;

  return (
    <div style={{ marginTop: 16, padding: 28, background: fcColors.bgRaised }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 20,
        }}
      >
        <div>
          <FCEyebrow>WHAT WE CHECKED</FCEyebrow>
          <div style={{ ...fcType.display, fontSize: 26, marginTop: 6 }}>The receipts.</div>
        </div>
        <div style={{ ...fcType.mono, fontSize: 11, color: fcColors.muted, letterSpacing: "0.18em" }}>
          AI-EXTRACTED · {dateStr}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          border: `1px solid ${fcColors.ruleStrong}`,
        }}
      >
        {[
          { v: summary.claim_count, l: "claims", sub: `across ${summary.source_count} channels` },
          { v: summary.mechanism_atom_count, l: "tactical moves", sub: "mapped to mechanics" },
          {
            v: summary.current_form_claim_count,
            l: "from last 90 days",
            sub: `${histCount} historical`,
          },
        ].map((stat, i) => (
          <div
            key={stat.l}
            style={{
              padding: "22px 20px",
              borderLeft: i ? `1px solid ${fcColors.ruleStrong}` : "none",
            }}
          >
            <div style={{ ...fcType.display, fontSize: 64, color: fcColors.ermes, lineHeight: 0.9 }}>
              {stat.v}
            </div>
            <div style={{ ...fcType.display, fontSize: 14, marginTop: 6, color: fcColors.ink }}>
              {stat.l}
            </div>
            <div
              style={{
                ...fcType.mono,
                fontSize: 10,
                letterSpacing: "0.15em",
                color: fcColors.muted,
                marginTop: 4,
                textTransform: "uppercase",
              }}
            >
              {stat.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
