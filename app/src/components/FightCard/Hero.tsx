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
        overflow: "hidden",
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

      <div className="hero-fighter-grid">
        <FighterCorner
          corner="RED CORNER"
          firstName={aFirst}
          lastName={aLast}
          accent={fcColors.ermes}
          imageSrc={`${import.meta.env.BASE_URL}athletes/ermes.png`}
          imageSide="left"
        />

        <div
          className="hero-vs"
          style={{
            ...fcType.display,
            color: "#3a3733",
            textAlign: "center",
          }}
        >
          VS
        </div>

        <FighterCorner
          corner="BLUE CORNER"
          firstName={bFirst}
          lastName={bLast}
          accent={fcColors.morozov}
          imageSrc={`${import.meta.env.BASE_URL}athletes/morozov.png`}
          imageSide="right"
        />
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

function FighterCorner({
  corner,
  firstName,
  lastName,
  accent,
  imageSrc,
  imageSide,
}: {
  corner: string;
  firstName: string;
  lastName: string;
  accent: string;
  imageSrc: string;
  imageSide: "left" | "right";
}) {
  const photo = (
    <div
      className="fighter-photo"
      style={{
        border: `1px solid ${accent}`,
        background: `linear-gradient(145deg, ${accent}33, transparent 58%), ${fcColors.bgRaised}`,
      }}
    >
      <img
        src={imageSrc}
        alt={`${firstName} ${lastName}`}
        onError={(event) => {
          event.currentTarget.style.display = "none";
        }}
      />
      <div className="fighter-photo-fallback" style={{ color: accent }}>
        {firstName[0]}
        {lastName[0]}
      </div>
    </div>
  );

  const name = (
    <div className="fighter-name">
      <div
        style={{
          ...fcType.mono,
          color: fcColors.muted,
          fontSize: 11,
          letterSpacing: "0.2em",
          marginBottom: 8,
        }}
      >
        {corner}
      </div>
      <div className="fighter-first" style={{ ...fcType.display, color: fcColors.ink }}>
        {firstName}
      </div>
      <div className="fighter-last" style={{ ...fcType.display, color: accent }}>
        {lastName}
      </div>
    </div>
  );

  return (
    <div className={`fighter-card fighter-card-${imageSide}`}>
      {imageSide === "left" ? (
        <>
          {photo}
          {name}
        </>
      ) : (
        <>
          {name}
          {photo}
        </>
      )}
    </div>
  );
}
