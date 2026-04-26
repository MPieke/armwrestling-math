import { fcColors, fcType } from "./styles";

export function BrandMasthead() {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 22,
        padding: "8px 0 28px",
        borderBottom: `1px solid ${fcColors.rule}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 18, minWidth: 0 }}>
        <img
          src={`${import.meta.env.BASE_URL}logo.png`}
          alt="Armwrestling Math logo"
          style={{
            width: "clamp(128px, 18vw, 210px)",
            height: "auto",
            objectFit: "contain",
            flex: "0 0 auto",
          }}
        />
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              ...fcType.display,
              color: fcColors.ink,
              fontSize: "clamp(34px, 5vw, 58px)",
              letterSpacing: "0.02em",
            }}
          >
            Armwrestling Math
          </div>
          <div
            style={{
              ...fcType.mono,
              color: fcColors.contested,
              fontSize: "clamp(10px, 1.4vw, 13px)",
              letterSpacing: "0.18em",
              marginTop: 7,
              textTransform: "uppercase",
            }}
          >
            What you might be missing
          </div>
        </div>
      </div>

      <div
        style={{
          ...fcType.mono,
          color: fcColors.muted,
          fontSize: 10,
          letterSpacing: "0.18em",
          textAlign: "right",
          textTransform: "uppercase",
        }}
      >
        Evidence-first
        <br />
        pick&apos;em
      </div>
    </header>
  );
}
