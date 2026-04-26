// app/src/components/FightCard/Storylines.tsx
import React from "react";
import { fcColors, fcType, leansAccent, type Side } from "./styles";
import { FCDivider } from "./atoms";
import type { Theme, Claim } from "../../types";

interface StorylinesProps {
  themes: Theme[];
  claims: Claim[];
}

/**
 * Maps a Theme to a "leans" side. Replace this with a real signal from
 * synthesis (e.g. theme.leans: "ermes" | "morozov" | "even") once available.
 */
function deriveLeans(theme: Theme): Side {
  const text = `${theme.label} ${theme.match_relevance}`.toLowerCase();
  if (text.includes("ermes")) return "ermes";
  if (text.includes("morozov")) return "morozov";
  return "even";
}

export function Storylines({ themes, claims }: StorylinesProps) {
  const [openThemeId, setOpenThemeId] = React.useState<string | null>(themes[0]?.theme_id ?? null);
  const claimsByIndex = React.useMemo(
    () => new Map(claims.map((claim) => [claim.evidence_index, claim])),
    [claims],
  );

  return (
    <div style={{ marginTop: 16 }}>
      <FCDivider label={`${themes.length} STORYLINES THAT MATTER`} />
      <div>
        {themes.map((s, i) => {
          const leans = deriveLeans(s);
          const accent = leansAccent(leans);
          const claimCount = s.evidence_refs.length;
          const open = openThemeId === s.theme_id;
          const evidenceClaims = s.evidence_refs
            .map((ref) => claimsByIndex.get(ref.evidence_index))
            .filter((claim): claim is Claim => Boolean(claim))
            .slice(0, 8);

          return (
            <div
              key={s.theme_id}
              style={{
                borderTop: `1px solid ${fcColors.rule}`,
                borderBottom: i === themes.length - 1 ? `1px solid ${fcColors.rule}` : "none",
                padding: "22px 0",
              }}
            >
              <button
                type="button"
                onClick={() => setOpenThemeId(open ? null : s.theme_id)}
                aria-expanded={open}
                style={{
                  display: "grid",
                  gridTemplateColumns: "70px 1fr 130px",
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  padding: 0,
                  textAlign: "left",
                  alignItems: "center",
                }}
              >
                <div style={{ ...fcType.display, fontSize: 56, color: accent, paddingLeft: 4 }}>
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div>
                  <div style={{ ...fcType.display, fontSize: 22, color: fcColors.ink }}>
                    {s.label}
                  </div>
                  <div
                    style={{
                      ...fcType.mono,
                      fontSize: 11,
                      color: fcColors.muted,
                      letterSpacing: "0.12em",
                      textTransform: "uppercase",
                      marginTop: 4,
                    }}
                  >
                    {s.match_relevance.split(".")[0]}
                  </div>
                  <div
                    style={{
                      fontFamily: "Georgia, serif",
                      fontSize: 13,
                      color: fcColors.inkDim,
                      marginTop: 8,
                      lineHeight: 1.5,
                    }}
                  >
                    {s.why_this_theme_emerged}
                  </div>
                </div>
                <div style={{ textAlign: "right", paddingRight: 4 }}>
                  <div style={{ ...fcType.mono, fontSize: 10, color: fcColors.muted, letterSpacing: "0.18em" }}>
                    LEANS
                  </div>
                  <div style={{ ...fcType.display, fontSize: 18, color: accent, marginTop: 2 }}>
                    {leans === "even" ? "EVEN" : leans === "ermes" ? "ERMES" : "MOROZOV"}
                  </div>
                  <div style={{ ...fcType.mono, fontSize: 10, color: fcColors.muted, marginTop: 4 }}>
                    {claimCount} claims · {s.confidence ?? "—"}
                  </div>
                  <div style={{ ...fcType.mono, fontSize: 10, color: accent, marginTop: 8, letterSpacing: "0.16em" }}>
                    {open ? "HIDE RECEIPTS" : "VIEW RECEIPTS"}
                  </div>
                </div>
              </button>

              {open && (
                <div
                  style={{
                    marginTop: 18,
                    marginLeft: 70,
                    padding: "14px 16px",
                    background: fcColors.bgRaised,
                    border: `1px solid ${fcColors.ruleStrong}`,
                  }}
                >
                  <div style={{ ...fcType.mono, fontSize: 10, color: accent, letterSpacing: "0.18em" }}>
                    SOURCE RECEIPTS · CLICK TIMESTAMP FOR ORIGINAL
                  </div>
                  <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
                    {evidenceClaims.map((claim) => (
                      <div
                        key={claim.evidence_index}
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
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
