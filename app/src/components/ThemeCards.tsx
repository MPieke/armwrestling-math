import type { Claim, SourceGap, Theme } from "../types";

export function ThemeCards({
  themes,
  claims,
  gaps,
}: {
  themes: Theme[];
  claims: Claim[];
  gaps: SourceGap[];
}) {
  const claimLookup = new Map(claims.map((claim) => [claim.evidence_index, claim]));

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Key Storylines</p>
          <h2>What the sources are saying</h2>
        </div>
      </div>

      <div className="theme-grid">
        {themes.map((theme) => {
          const currentRefs = theme.evidence_refs
            .map((ref) => claimLookup.get(ref.evidence_index))
            .filter((claim): claim is Claim => Boolean(claim))
            .slice(0, 3);

          return (
            <article className="theme-card" key={theme.theme_id}>
              <div className="theme-topline">
                <h3>{theme.label}</h3>
                <span>{theme.confidence ?? "unknown"}</span>
              </div>
              <p>{theme.match_relevance}</p>
              {theme.challenged_assumption ? (
                <div className="counter-note">
                  <strong>What people might be wrong about</strong>
                  <span>{theme.challenged_assumption}</span>
                </div>
              ) : null}
              <div className="reference-stack">
                {currentRefs.map((claim) => (
                  <a href={claim.source_url} target="_blank" rel="noreferrer" key={claim.evidence_index}>
                    {claim.channel} at {claim.timestamp}
                  </a>
                ))}
              </div>
            </article>
          );
        })}
      </div>

      {gaps.length ? (
        <div className="gap-box">
          <strong>What we don't have yet</strong>
          <ul className="compact-list">
            {gaps.slice(0, 3).map((gap) => (
              <li key={gap.gap}>{gap.gap}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
