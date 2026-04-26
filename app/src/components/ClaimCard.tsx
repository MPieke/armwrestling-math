import type { Claim } from "../types";

function Badge({ children }: { children: string }) {
  return <span className="badge">{children}</span>;
}

function formatDimensionValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  if (!value || typeof value !== "object") {
    return String(value);
  }

  const record = value as Record<string, unknown>;
  const metric = record.metric ? String(record.metric) : "dimension";
  const amount = [record.value, record.unit].filter(Boolean).join(" ");
  const context = record.setup_or_context ? ` (${record.setup_or_context})` : "";
  return amount ? `${metric}: ${amount}${context}` : metric;
}

export function ClaimCard({ claim }: { claim: Claim }) {
  const mechanics = claim.dimensions?.mechanics ?? [];
  const measurements = claim.dimensions?.measurements ?? [];
  const lifts = claim.dimensions?.lifts ?? [];

  return (
    <article className="claim-card">
      <div className="claim-meta">
        <Badge>{`Claim ${claim.evidence_index}`}</Badge>
        <Badge>{claim.source_recency.replace("_", " ")}</Badge>
        {claim.current_form_allowed ? <Badge>current form usable</Badge> : <Badge>style/history only</Badge>}
      </div>

      <p className="claim-text">{claim.claim}</p>
      <p className="claim-relevance">{claim.relevance}</p>

      <div className="claim-source">
        <a href={claim.source_url} target="_blank" rel="noreferrer">
          {claim.channel} at {claim.timestamp}
        </a>
        <span>{claim.video_title}</span>
      </div>

      {[...mechanics, ...measurements, ...lifts].length ? (
        <div className="chip-row">
          {mechanics.map((item) => <Badge key={`mechanic-${item}`}>{item}</Badge>)}
          {measurements.map((item, index) => (
            <Badge key={`measurement-${index}-${formatDimensionValue(item)}`}>{formatDimensionValue(item)}</Badge>
          ))}
          {lifts.map((item, index) => (
            <Badge key={`lift-${index}-${formatDimensionValue(item)}`}>{formatDimensionValue(item)}</Badge>
          ))}
        </div>
      ) : null}

      {claim.mechanism_atoms.length ? (
        <div className="atom-list">
          {claim.mechanism_atoms.map((atom, index) => (
            <span key={`${atom.action}-${index}`}>
              {atom.actor || "Unknown actor"}: {atom.action || "unknown action"} ({atom.lane || "unknown lane"})
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}
