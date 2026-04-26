// app/src/components/FightCard/styles.ts
// Shared style tokens for the Fight Card direction.

export const fcColors = {
  bg: "#0d0d0e",
  bgRaised: "#16140f",
  rule: "#1f1d1a",
  ruleStrong: "#2a261f",
  ink: "#f3ece0",
  inkDim: "#a89e8e",
  muted: "#7a7064",
  ermes: "#e23b21",
  morozov: "#5db1ff",
  contested: "#d39a2b",
} as const;

export const fcType = {
  display: {
    fontFamily: "'Barlow Condensed', 'Oswald', 'Helvetica Neue', sans-serif",
    fontWeight: 800,
    letterSpacing: "-0.01em",
    textTransform: "uppercase" as const,
    lineHeight: 0.88,
  },
  mono: {
    fontFamily: "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace",
  },
  serif: {
    fontFamily: "Georgia, 'Source Serif Pro', serif",
  },
};

export const fcShell: React.CSSProperties = {
  width: "100%",
  minHeight: "100vh",
  background: fcColors.bg,
  color: fcColors.ink,
  fontFamily: "'Barlow Condensed', 'Oswald', 'Helvetica Neue', sans-serif",
  padding: "24px",
  boxSizing: "border-box",
};

export type Side = "ermes" | "morozov" | "even";

export function leansAccent(leans: Side): string {
  if (leans === "ermes") return fcColors.ermes;
  if (leans === "morozov") return fcColors.morozov;
  return fcColors.contested;
}
