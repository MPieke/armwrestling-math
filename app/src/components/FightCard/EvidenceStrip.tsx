// app/src/components/FightCard/EvidenceStrip.tsx
// Compressed top stat strip — promote 1 hero stat, demote others.
import React from "react";
import { fcColors, fcType } from "./styles";
import { FCEyebrow } from "./atoms";
import { ClaimReceipts } from "./ClaimReceipts";
import type { Claim, Summary } from "../../types";

interface EvidenceStripProps {
  summary: Summary;
  generatedAt: string;
  claims: Claim[];
}

type OpenStat = "claims" | "moves" | "current" | null;

export function EvidenceStrip({ summary, generatedAt, claims }: EvidenceStripProps) {
  const [openStat, setOpenStat] = React.useState<OpenStat>(null);
  const dateStr = new Date(generatedAt).toLocaleDateString("en-GB");
  const histCount = summary.claim_count - summary.current_form_claim_count;
  const currentClaims = claims.filter((claim) => claim.current_form_allowed);
  const claimsWithMoves = claims.filter((claim) => claim.mechanism_atoms.length > 0);
  const activeClaims =
    openStat === "current" ? currentClaims : openStat === "moves" ? claimsWithMoves : claims;

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
          { id: "claims" as const, v: summary.claim_count, l: "claims", sub: `across ${summary.source_count} channels` },
          { id: "moves" as const, v: summary.mechanism_atom_count, l: "tactical moves", sub: "mapped to mechanics" },
          {
            id: "current" as const,
            v: summary.current_form_claim_count,
            l: "from last 90 days",
            sub: `${histCount} historical`,
          },
        ].map((stat, i) => (
          <button
            type="button"
            key={stat.l}
            onClick={() => setOpenStat(openStat === stat.id ? null : stat.id)}
            aria-expanded={openStat === stat.id}
            style={{
              padding: "22px 20px",
              borderLeft: i ? `1px solid ${fcColors.ruleStrong}` : "none",
              borderTop: "none",
              borderRight: "none",
              borderBottom: "none",
              background: openStat === stat.id ? fcColors.bg : "transparent",
              color: "inherit",
              cursor: "pointer",
              textAlign: "left",
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
            <div style={{ ...fcType.mono, color: fcColors.ermes, fontSize: 10, letterSpacing: "0.15em", marginTop: 8 }}>
              {openStat === stat.id ? "HIDE DATA" : "VIEW DATA"}
            </div>
          </button>
        ))}
      </div>

      {openStat && (
        <div style={{ marginTop: 16, padding: 14, background: fcColors.bg, border: `1px solid ${fcColors.ruleStrong}` }}>
          <FCEyebrow>
            {openStat === "claims"
              ? `ALL CLAIMS · ${activeClaims.length}`
              : openStat === "moves"
                ? `CLAIMS WITH TACTICAL MOVES · ${activeClaims.length}`
                : `CURRENT-FORM CLAIMS · ${activeClaims.length}`}
          </FCEyebrow>
          <div style={{ marginTop: 12 }}>
            <ClaimReceipts claims={activeClaims} maxHeight={620} />
          </div>
        </div>
      )}
    </div>
  );
}
