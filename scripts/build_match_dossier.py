from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_INPUTS = [
    ROOT / "data" / "app" / "ermes_morozov_evidence_v1.json",
    ROOT / "data" / "app" / "ermes_morozov_expanded_evidence_v1.json",
]
CLUSTERS_PATH = ROOT / "data" / "app" / "ermes_morozov_data_driven_clusters.json"
DIMENSIONS_PATH = ROOT / "data" / "app" / "ermes_morozov_evidence_dimensions.json"
OUTPUT_PATH = ROOT / "docs" / "app" / "ermes_morozov_match_dossier.md"


def load_claims() -> list[dict[str, Any]]:
    claims = []
    seen = set()
    for path in EVIDENCE_INPUTS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for raw_claim in payload["claims"]:
            key = (
                raw_claim.get("video_id"),
                raw_claim.get("timestamp"),
                raw_claim.get("claim"),
            )
            if key in seen:
                continue
            seen.add(key)
            claims.append({"evidence_index": len(claims), **raw_claim})
    return claims


def load_clusters() -> dict[str, Any]:
    return json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))


def load_dimensions() -> dict[int, dict[str, Any]]:
    if not DIMENSIONS_PATH.exists():
        return {}
    payload = json.loads(DIMENSIONS_PATH.read_text(encoding="utf-8"))
    return {item["evidence_index"]: item for item in payload.get("dimensions", [])}


def render_claim_summary(claim: dict[str, Any]) -> str:
    return (
        f"[{claim.get('timestamp', '')}]({claim.get('source_url')}) "
        f"{claim.get('claim')} Source: {claim.get('channel')}. "
        f"Recency: `{claim.get('source_recency', 'unknown')}`."
    )


def render_dossier(
    claims: list[dict[str, Any]],
    clusters: dict[str, Any],
    dimensions: dict[int, dict[str, Any]],
) -> str:
    claim_lookup = {claim["evidence_index"]: claim for claim in claims}
    recency_counts = Counter(claim.get("source_recency", "unknown") for claim in claims)
    current_count = sum(bool(claim.get("current_form_allowed")) for claim in claims)
    dimension_values = list(dimensions.values())
    mechanics_count = sum(bool(item.get("mechanics")) for item in dimension_values)
    measurement_count = sum(bool(item.get("measurements")) for item in dimension_values)
    lift_count = sum(bool(item.get("lifts")) for item in dimension_values)
    lines = [
        "# Ermes Gasparini vs Artyom Morozov Evidence Dossier",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "Purpose: keep the evidence visible first, then provide light synthesis on top.",
        "This dossier stores structured claims and references only. It does not store",
        "transcripts, captions, audio, or video.",
        "",
        "## Evidence Snapshot",
        "",
        f"- Claims: `{len(claims)}`",
        f"- Sources: `{len({claim.get('video_id') for claim in claims})}`",
        f"- Recency distribution: `{dict(recency_counts)}`",
        f"- Current-form-allowed claims: `{current_count}`",
        f"- Claims with mechanics dimensions: `{mechanics_count}`",
        f"- Claims with measurement dimensions: `{measurement_count}`",
        f"- Claims with lift dimensions: `{lift_count}`",
        "",
        "Interpretation rule: historical claims can support durable style, options, and",
        "similar-opponent reasoning. They should not be read as current form.",
        "",
        "## Light Synthesis: Emergent Themes",
        "",
    ]
    for theme in clusters["themes"]:
        lines.extend(
            [
                f"### {theme['label']}",
                "",
                f"Why this emerged: {theme.get('why_this_theme_emerged', '')}",
                "",
                f"Match relevance: {theme.get('match_relevance', '')}",
                "",
            ]
        )
        current_read = theme.get("current_form_read", "")
        historical_read = theme.get("historical_style_read", "")
        if current_read:
            lines.extend([f"Current-form read: {current_read}", ""])
        if historical_read:
            lines.extend([f"Historical/style read: {historical_read}", ""])
        challenged = theme.get("challenged_assumption", "")
        if challenged:
            lines.extend([f"Challenged assumption: {challenged}", ""])
        lines.append("Evidence:")
        for ref in theme.get("evidence_refs", [])[:10]:
            claim = claim_lookup.get(ref["evidence_index"])
            if not claim:
                continue
            lines.append(
                f"- Claim `{ref['evidence_index']}`: {render_claim_summary(claim)} "
                f"Role: {ref.get('role_in_theme', '')}"
            )
        lines.append("")

    lines.extend(["## Cross-Theme Tensions", ""])
    for item in clusters.get("cross_theme_tensions", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Source Gaps", ""])
    for gap in clusters.get("source_gaps", []):
        lines.append(
            f"- {gap.get('gap')} Why it matters: {gap.get('why_it_matters')} "
            f"Search: `{gap.get('suggested_source_query')}`"
        )

    lines.extend(["", "## Full Evidence Library", ""])
    for claim in claims:
        dimension = dimensions.get(claim["evidence_index"], {})
        lines.append(f"### Claim {claim['evidence_index']}")
        lines.extend(
            [
                "",
                render_claim_summary(claim),
                "",
                f"Video: {claim.get('video_title')}",
                "",
                f"Speaker/source: {claim.get('speaker_or_source', 'unknown')}",
                "",
                f"Published: `{claim.get('source_published_at')}`",
                "",
                f"Current-form allowed: `{claim.get('current_form_allowed')}`",
                "",
                f"Allowed evidence roles: `{claim.get('allowed_evidence_roles', [])}`",
                "",
                f"Relevance note: {claim.get('relevance', '')}",
                "",
            ]
        )
        if dimension:
            lines.extend(
                [
                    "Dimensions:",
                    "",
                    f"- Evidence kind: `{dimension.get('evidence_kind')}`",
                    f"- Temporal scope: `{dimension.get('temporal_scope')}`",
                    f"- Noise risk: `{dimension.get('noise_risk')}`",
                    f"- Mechanics: `{dimension.get('mechanics', [])}`",
                    f"- Measurements: `{dimension.get('measurements', [])}`",
                    f"- Lifts: `{dimension.get('lifts', [])}`",
                    f"- Verification needed: `{dimension.get('verification_needed', [])}`",
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> None:
    claims = load_claims()
    clusters = load_clusters()
    dimensions = load_dimensions()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_dossier(claims, clusters, dimensions) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
