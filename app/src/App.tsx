import { useMemo, useState } from "react";
import { ClaimCard } from "./components/ClaimCard";
import { EvidenceSnapshot } from "./components/EvidenceSnapshot";
import { MatchHeader } from "./components/MatchHeader";
import { PickemPanel } from "./components/PickemPanel";
import { ThemeCards } from "./components/ThemeCards";
import { useDossier } from "./data/useDossier";
import type { Claim, Recency } from "./types";

const RECENCY_OPTIONS: Array<{ value: "all" | Recency; label: string }> = [
  { value: "all", label: "All evidence" },
  { value: "current_window", label: "Current form only" },
  { value: "recent_context", label: "Recent context" },
  { value: "historical_context", label: "Historical style" },
];

function claimMatchesQuery(claim: Claim, query: string) {
  if (!query.trim()) {
    return true;
  }
  const haystack = [
    claim.claim,
    claim.relevance,
    claim.channel,
    claim.video_title,
    claim.speaker_or_source,
    claim.dimensions?.mechanics.join(" "),
    claim.dimensions?.measurements.join(" "),
    claim.dimensions?.lifts.join(" "),
    claim.mechanism_atoms.map((atom) => `${atom.subject} ${atom.mechanism} ${atom.lane}`).join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return haystack.includes(query.toLowerCase());
}

function EvidenceLibrary({ claims }: { claims: Claim[] }) {
  const [query, setQuery] = useState("");
  const [recency, setRecency] = useState<"all" | Recency>("all");
  const [mechanicsOnly, setMechanicsOnly] = useState(false);

  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      if (recency !== "all" && claim.source_recency !== recency) {
        return false;
      }
      if (mechanicsOnly && !claim.mechanism_atoms.length && !claim.dimensions?.mechanics.length) {
        return false;
      }
      return claimMatchesQuery(claim, query);
    });
  }, [claims, mechanicsOnly, query, recency]);

  return (
    <section className="panel evidence-library">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Evidence Library</p>
          <h2>Every claim stays inspectable</h2>
        </div>
        <p className="muted">{filteredClaims.length} of {claims.length} claims visible</p>
      </div>

      <div className="filters">
        <label className="search-field">
          <span>Search claims, mechanics, channels</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Try hook, wrist, back pressure, measurements..."
          />
        </label>

        <label>
          <span>Evidence age</span>
          <select value={recency} onChange={(event) => setRecency(event.target.value as "all" | Recency)}>
            {RECENCY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={mechanicsOnly}
            onChange={(event) => setMechanicsOnly(event.target.checked)}
          />
          <span>Mechanics only</span>
        </label>
      </div>

      <div className="claim-list">
        {filteredClaims.slice(0, 60).map((claim) => (
          <ClaimCard key={claim.evidence_index} claim={claim} />
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const dossierState = useDossier();

  if (dossierState.status === "loading") {
    return <main className="loading-shell">Loading dossier...</main>;
  }

  if (dossierState.status === "error") {
    return <main className="loading-shell">Could not load dossier: {dossierState.error}</main>;
  }

  const { dossier } = dossierState;

  return (
    <main>
      <MatchHeader match={dossier.match} generatedAt={dossier.generated_at} />
      <div className="page-grid">
        <div className="main-column">
          <EvidenceSnapshot summary={dossier.summary} sources={dossier.sources} />
          <ThemeCards themes={dossier.themes} claims={dossier.claims} gaps={dossier.source_gaps} />
          <EvidenceLibrary claims={dossier.claims} />
        </div>
        <aside className="side-column">
          <PickemPanel athleteA={dossier.match.athlete_a} athleteB={dossier.match.athlete_b} />
          <section className="panel">
            <p className="eyebrow">Tensions</p>
            <h2>What still conflicts</h2>
            {dossier.cross_theme_tensions.length ? (
              <ul className="compact-list">
                {dossier.cross_theme_tensions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No cross-theme tensions in this dossier yet.</p>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}
