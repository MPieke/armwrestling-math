import { fcColors, fcType } from "./styles";

export function BrandMasthead() {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 18,
        padding: "10px 0 22px",
        borderBottom: `1px solid ${fcColors.rule}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14, minWidth: 0 }}>
        <img
          src={`${import.meta.env.BASE_URL}logo.png`}
          alt="Armwrestling Math logo"
          style={{
            width: 70,
            height: 44,
            objectFit: "contain",
            flex: "0 0 auto",
          }}
        />
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              ...fcType.display,
              color: fcColors.ink,
              fontSize: 30,
              letterSpacing: "0.02em",
            }}
          >
            Armwrestling Math
          </div>
          <div
            style={{
              ...fcType.mono,
              color: fcColors.contested,
              fontSize: 11,
              letterSpacing: "0.18em",
              marginTop: 4,
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
