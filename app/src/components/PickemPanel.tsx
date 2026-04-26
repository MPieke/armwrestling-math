import { useState } from "react";

export function PickemPanel({ athleteA, athleteB }: { athleteA: string; athleteB: string }) {
  const [winner, setWinner] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(65);
  const picked = winner !== null;

  return (
    <section className="panel pickem-hero">
      <p className="eyebrow">Before you read the evidence</p>
      <h2>Who you got?</h2>
      <div className="pick-row">
        {[athleteA, athleteB].map((athlete) => (
          <button
            type="button"
            className={`pick-btn ${winner === athlete ? "active" : ""}`}
            onClick={() => setWinner(athlete)}
            key={athlete}
          >
            {athlete}
          </button>
        ))}
      </div>
      {picked ? (
        <div className="confidence-row">
          <label className="confidence-slider">
            <span>How sure? {confidence}%</span>
            <input
              type="range"
              min="50"
              max="100"
              value={confidence}
              onChange={(event) => setConfidence(Number(event.target.value))}
            />
          </label>
          <p className="pick-confirm">
            You picked <strong>{winner}</strong> at {confidence}%. Now see if the evidence agrees.
          </p>
        </div>
      ) : (
        <p className="muted">Commit to a pick, then scroll down to see what you might be missing.</p>
      )}
    </section>
  );
}
