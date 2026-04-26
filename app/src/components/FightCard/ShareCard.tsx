// app/src/components/FightCard/ShareCard.tsx
// 1:1 pull-quote card. Pass any claim; user can right-click → save image.
import React from "react";
import { fcColors, fcType } from "./styles";
import type { Claim } from "../../types";

interface ShareCardProps {
  claim: Claim;
  matchTitle: string; // "ERMES vs MOROZOV · JUNE 2026"
  index?: number;     // shown as "EVIDENCE #N"
}

export function ShareCard({ claim, matchTitle, index }: ShareCardProps) {
  return (
    <div
      style={{
        background: fcColors.ermes,
        color: fcColors.bg,
        padding: 32,
        position: "relative",
        aspectRatio: "1 / 1",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        <div style={{ ...fcType.mono, fontSize: 11, letterSpacing: "0.2em" }}>
          EVW · KOTT NARRATIVE CHECK
        </div>
        {typeof index === "number" && (
          <div style={{ ...fcType.display, fontSize: 14, marginTop: 4 }}>
            EVIDENCE #{index + 1}
          </div>
        )}
      </div>

      <div style={{ ...fcType.display, fontSize: 38, lineHeight: 0.95, textWrap: "balance" }}>
        "{claim.claim}"
      </div>

      <div>
        <div style={{ ...fcType.mono, fontSize: 11, letterSpacing: "0.15em" }}>
          {(claim.speaker_or_source || claim.channel).toUpperCase()} ·{" "}
          {claim.video_title.toUpperCase().slice(0, 48)}
          {claim.video_title.length > 48 ? "…" : ""} · {claim.timestamp}
        </div>
        <div style={{ height: 1, background: fcColors.bg, margin: "10px 0", opacity: 0.3 }} />
        <div style={{ ...fcType.display, fontSize: 16 }}>{matchTitle}</div>
      </div>
    </div>
  );
}
