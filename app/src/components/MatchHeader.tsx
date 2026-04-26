import type { MatchInfo } from "../types";

export function MatchHeader({ match, generatedAt }: { match: MatchInfo; generatedAt: string }) {
  return (
    <header className="hero">
      <div>
        <p className="eyebrow">EVW/KOTT Narrative Check</p>
        <h1>
          {match.athlete_a} <span>vs</span> {match.athlete_b}
        </h1>
        <p className="hero-copy">{match.product_positioning}</p>
      </div>
      <div className="hero-card">
        <p>{match.event_context}</p>
        <strong>{match.arm.toUpperCase()} hand</strong>
        <span>Dataset generated {new Date(generatedAt).toLocaleString()}</span>
      </div>
    </header>
  );
}
