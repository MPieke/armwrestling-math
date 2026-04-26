// app/src/components/FightCard/atoms.tsx
// Tiny presentational primitives reused across the Fight Card.

import React from "react";
import { fcColors, fcType } from "./styles";

export function FCEyebrow({
  children,
  color = fcColors.ermes,
}: {
  children: React.ReactNode;
  color?: string;
}) {
  return (
    <div
      style={{
        ...fcType.mono,
        color,
        fontSize: 11,
        letterSpacing: "0.2em",
        textTransform: "uppercase",
        fontWeight: 600,
      }}
    >
      {children}
    </div>
  );
}

export function FCDivider({ thick = 1, label }: { thick?: number; label?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "20px 0" }}>
      <div style={{ height: thick, background: fcColors.ermes, flex: 1 }} />
      {label && (
        <div
          style={{
            ...fcType.mono,
            fontSize: 10,
            letterSpacing: "0.25em",
            color: fcColors.muted,
            textTransform: "uppercase",
          }}
        >
          {label}
        </div>
      )}
      <div style={{ height: thick, background: fcColors.ermes, flex: 1 }} />
    </div>
  );
}
