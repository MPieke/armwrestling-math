// app/src/App.tsx — drop-in replacement using the Fight Card components.
import { useMemo } from "react";
import {
  FightCardHero,
  BrandMasthead,
  Pickem,
  Fronts,
  EvidenceStrip,
  Tactical,
  ShareCard,
  fcShell,
  type Front,
} from "./components/FightCard";
import { useDossier } from "./data/useDossier";
import type { Dossier } from "./types";

export default function App() {
  const dossierState = useDossier();

  if (dossierState.status === "loading") {
    return <main style={fcShell}>Loading dossier…</main>;
  }
  if (dossierState.status === "error") {
    return <main style={fcShell}>Could not load dossier: {dossierState.error}</main>;
  }

  return <FightCardApp dossier={dossierState.dossier} />;
}

function FightCardApp({ dossier }: { dossier: Dossier }) {
  // The synthesis output should ultimately include `dossier.fronts`.
  // Until the schema lands, derive a stub from themes so the UI renders.
  // (See scripts/synthesize_match_fronts_stub.py for the real shape.)
  const fronts: Front[] = useMemo(() => {
    const anyDossier = dossier as unknown as { fronts?: Front[] };
    if (anyDossier.fronts && anyDossier.fronts.length > 0) return anyDossier.fronts;

    return dossier.themes.map((t, i) => {
      const text = t.label.toLowerCase();
      const leans: Front["leans"] = text.includes("ermes")
        ? "ermes"
        : text.includes("morozov")
        ? "morozov"
        : "even";
      return {
        id: t.theme_id,
        ordinal: String(i + 1).padStart(2, "0"),
        label: t.label.toUpperCase().slice(0, 32),
        question: t.match_relevance.split(".")[0] + "?",
        popular_take: t.challenged_assumption ?? t.why_this_theme_emerged.split(".")[0],
        counter_take: t.current_form_read ?? t.historical_style_read ?? "Evidence pending.",
        leans,
        claim_count: t.evidence_refs.length,
        evidence_indexes: t.evidence_refs.map((ref) => ref.evidence_index),
      };
    });
  }, [dossier]);

  const matchId = `${dossier.match.athlete_a}-${dossier.match.athlete_b}-${dossier.match.arm}`;
  const matchTitle = `${dossier.match.athlete_a.split(" ").pop()?.toUpperCase()} vs ${dossier.match.athlete_b
    .split(" ")
    .pop()
    ?.toUpperCase()} · ${dossier.match.event_context.toUpperCase()}`;

  // Pick the "most quotable" claim for the share card — for now, first claim
  // tagged as current_form. Replace with an explicit `hero_claim_index` from
  // synthesis once available.
  const heroClaim =
    dossier.claims.find((c) => c.source_recency === "current_window") ?? dossier.claims[0];
  const heroIdx = heroClaim ? dossier.claims.indexOf(heroClaim) : 0;

  return (
    <main className="fight-card-shell" style={fcShell}>
      <BrandMasthead />

      <FightCardHero match={dossier.match} generatedAt={dossier.generated_at} />

      <Pickem
        athleteA={dossier.match.athlete_a}
        athleteB={dossier.match.athlete_b}
        matchId={matchId}
      />

      <Fronts fronts={fronts} claims={dossier.claims} headlineCount={fronts.length} />

      <EvidenceStrip summary={dossier.summary} generatedAt={dossier.generated_at} claims={dossier.claims} />

      <Tactical
        claims={dossier.claims}
        athleteA={dossier.match.athlete_a}
        athleteB={dossier.match.athlete_b}
      />

      {heroClaim && <ShareCard claim={heroClaim} matchTitle={matchTitle} index={heroIdx} />}
    </main>
  );
}
