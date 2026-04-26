import type { Claim } from "../types";

function Badge({ children }: { children: string }) {
  return <span className="badge">{children}</span>;
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
          {measurements.map((item) => <Badge key={`measurement-${item}`}>{item}</Badge>)}
          {lifts.map((item) => <Badge key={`lift-${item}`}>{item}</Badge>)}
        </div>
      ) : null}

      {claim.mechanism_atoms.length ? (
        <div className="atom-list">
          {claim.mechanism_atoms.map((atom, index) => (
            <span key={`${atom.mechanism}-${index}`}>
              {atom.subject}: {atom.mechanism} ({atom.lane})
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}
