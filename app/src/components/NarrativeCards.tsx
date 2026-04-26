import type { Narrative } from "../types";

export function NarrativeCards({ narrative }: { narrative: Narrative }) {
  return (
    <section className="narrative-section">
      <h2 className="key-question">{narrative.key_question}</h2>
      <div className="narrative-grid">
        <article className="narrative-card popular">
          <p className="narrative-label">Most people think...</p>
          <h3>{narrative.popular_take.headline}</h3>
          <p>{narrative.popular_take.detail}</p>
        </article>
        <article className="narrative-card counter">
          <p className="narrative-label">But what about...</p>
          <h3>{narrative.counter_case.headline}</h3>
          <p>{narrative.counter_case.detail}</p>
        </article>
      </div>
    </section>
  );
}
