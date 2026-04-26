import { useState } from "react";

export function PickemPanel({ athleteA, athleteB }: { athleteA: string; athleteB: string }) {
  const [winner, setWinner] = useState<string>(athleteA);
  const [confidence, setConfidence] = useState(60);

  return (
    <section className="panel pickem-panel">
      <p className="eyebrow">Pick'em Mock</p>
      <h2>Make a pick before reading</h2>
      <div className="pick-buttons">
        {[athleteA, athleteB].map((athlete) => (
          <button
            type="button"
            className={winner === athlete ? "active" : ""}
            onClick={() => setWinner(athlete)}
            key={athlete}
          >
            {athlete}
          </button>
        ))}
      </div>
      <label className="confidence-slider">
        <span>Confidence: {confidence}%</span>
        <input
          type="range"
          min="50"
          max="100"
          value={confidence}
          onChange={(event) => setConfidence(Number(event.target.value))}
        />
      </label>
      <p className="muted">Local-only placeholder. Community percentages come after we add submission storage.</p>
    </section>
  );
}
