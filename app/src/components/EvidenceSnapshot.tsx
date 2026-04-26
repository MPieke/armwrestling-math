import type { Source, Summary } from "../types";

const snapshotLabels: Array<[keyof Summary, string]> = [
  ["claim_count", "Total claims"],
  ["source_count", "Video sources"],
  ["current_form_claim_count", "Recent form"],
  ["mechanism_atom_count", "Tactical moves"],
  ["theme_count", "Key storylines"],
  ["measurement_dimension_count", "Measurements"],
];

export function EvidenceSnapshot({ summary, sources }: { summary: Summary; sources: Source[] }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">What We Found</p>
          <h2>The evidence behind the takes</h2>
        </div>
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
