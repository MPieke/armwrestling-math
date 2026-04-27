import { fcColors, fcType } from "./styles";
import type { Claim } from "../../types";

interface ClaimReceiptsProps {
  claims: Claim[];
  accent?: string;
  emptyLabel?: string;
  maxHeight?: number;
}

export function ClaimReceipts({
  claims,
  accent = fcColors.ermes,
  emptyLabel = "No source receipts available.",
  maxHeight = 520,
}: ClaimReceiptsProps) {
  if (!claims.length) {
    return (
      <div style={{ color: fcColors.muted, fontFamily: "Georgia, serif", fontSize: 13, fontStyle: "italic" }}>
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className="claim-receipt-list" style={{ display: "grid", gap: 12, maxHeight, overflowY: "auto", paddingRight: 4 }}>
      {claims.map((claim) => (
        <div
          key={claim.evidence_index}
          className="claim-receipt-row"
          style={{
            display: "grid",
            gridTemplateColumns: "92px 1fr",
            gap: 12,
            paddingTop: 12,
            borderTop: `1px dashed ${fcColors.ruleStrong}`,
          }}
        >
          <a
            href={claim.source_url}
            target="_blank"
            rel="noreferrer"
            style={{
              ...fcType.display,
              color: accent,
              fontSize: 18,
              textDecoration: "none",
            }}
          >
            {claim.timestamp || "SOURCE"}
          </a>
          <div>
            <div style={{ fontFamily: "Georgia, serif", color: fcColors.ink, fontSize: 14, lineHeight: 1.45 }}>
              {claim.claim}
            </div>
            <div
              style={{
                ...fcType.mono,
                color: fcColors.muted,
                fontSize: 10,
                letterSpacing: "0.12em",
                marginTop: 6,
                textTransform: "uppercase",
              }}
            >
              Claim #{claim.evidence_index} · {claim.channel} · {claim.source_recency.replaceAll("_", " ")}
            </div>
            {claim.relevance && (
              <div style={{ color: fcColors.inkDim, fontSize: 12, lineHeight: 1.45, marginTop: 6 }}>
                {claim.relevance}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
