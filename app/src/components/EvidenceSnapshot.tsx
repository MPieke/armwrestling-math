import type { Source, Summary } from "../types";

const snapshotLabels: Array<[keyof Summary, string]> = [
  ["claim_count", "Claims"],
  ["source_count", "Sources"],
  ["current_form_claim_count", "Current-form claims"],
  ["mechanism_atom_count", "Mechanism atoms"],
  ["theme_count", "Emergent themes"],
  ["measurement_dimension_count", "Measurements"],
];

export function EvidenceSnapshot({ summary, sources }: { summary: Summary; sources: Source[] }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Evidence Snapshot</p>
          <h2>Structured claims, not transcripts</h2>
        </div>
        <p className="muted">Historical sources are style evidence, not current form.</p>
      </div>

      <div className="stat-grid">
        {snapshotLabels.map(([key, label]) => (
          <div className="stat" key={key}>
            <span>{label}</span>
            <strong>{summary[key] as number}</strong>
          </div>
        ))}
      </div>

      <div className="source-strip">
        {sources.slice(0, 6).map((source) => (
          <a href={source.url} target="_blank" rel="noreferrer" className="source-pill" key={source.video_id}>
            <span>{source.channel}</span>
            <strong>{source.claim_count}</strong>
          </a>
        ))}
      </div>
    </section>
  );
}
