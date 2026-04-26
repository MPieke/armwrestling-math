from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_PUBLIC = ROOT / "app" / "public"
OUTPUT_PATH = APP_PUBLIC / "match_dossier.json"

EVIDENCE_INPUTS = [
    ROOT / "data" / "app" / "ermes_morozov_evidence_v1.json",
    ROOT / "data" / "app" / "ermes_morozov_expanded_evidence_v1.json",
]
DIMENSIONS_PATH = ROOT / "data" / "app" / "ermes_morozov_evidence_dimensions.json"
ATOMS_PATH = ROOT / "data" / "app" / "ermes_morozov_mechanism_atoms.json"
CLUSTERS_PATH = ROOT / "data" / "app" / "ermes_morozov_data_driven_clusters.json"


def load_claims() -> list[dict[str, Any]]:
    seen = set()
    claims = []
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


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def build_sources(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        video_id = claim.get("video_id", "")
        source = by_id.setdefault(
            video_id,
            {
                "video_id": video_id,
                "title": claim.get("video_title", ""),
                "channel": claim.get("channel", ""),
                "claim_count": 0,
                "source_recency": claim.get("source_recency", "unknown"),
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            },
        )
        source["claim_count"] += 1
    return sorted(by_id.values(), key=lambda item: item["claim_count"], reverse=True)


def build_summary(
    claims: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    clusters: dict[str, Any],
) -> dict[str, Any]:
    recency = Counter(claim.get("source_recency", "unknown") for claim in claims)
    return {
        "claim_count": len(claims),
        "source_count": len({claim.get("video_id") for claim in claims}),
        "current_form_claim_count": sum(bool(claim.get("current_form_allowed")) for claim in claims),
        "recency_distribution": dict(recency),
        "dimension_count": len(dimensions),
        "mechanics_dimension_count": sum(bool(item.get("mechanics")) for item in dimensions),
        "measurement_dimension_count": sum(bool(item.get("measurements")) for item in dimensions),
        "lift_dimension_count": sum(bool(item.get("lifts")) for item in dimensions),
        "mechanism_atom_count": len(atoms),
        "theme_count": len(clusters.get("themes", [])),
    }


def attach_claim_indexes(
    claims: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    dimensions_by_claim = {item["evidence_index"]: item for item in dimensions}
    atoms_by_claim: dict[int, list[dict[str, Any]]] = {}
    for atom in atoms:
        atoms_by_claim.setdefault(atom["evidence_index"], []).append(atom)

    enriched = []
    for claim in claims:
        evidence_index = claim["evidence_index"]
        enriched.append(
            {
                **claim,
                "dimensions": dimensions_by_claim.get(evidence_index),
                "mechanism_atoms": atoms_by_claim.get(evidence_index, []),
            }
        )
    return enriched


def build_bundle() -> dict[str, Any]:
    claims = load_claims()
    dimensions_payload = load_json(DIMENSIONS_PATH, {"dimensions": []})
    atoms_payload = load_json(ATOMS_PATH, {"atoms": [], "conflicts": []})
    clusters = load_json(CLUSTERS_PATH, {"themes": [], "cross_theme_tensions": [], "source_gaps": []})
    dimensions = dimensions_payload.get("dimensions", [])
    atoms = atoms_payload.get("atoms", [])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "match": {
            "athlete_a": "Ermes Gasparini",
            "athlete_b": "Artyom Morozov",
            "arm": "right",
            "event_context": "June 2026 right-hand match",
            "product_positioning": (
                "Before you make your EVW/KOTT picks, see the evidence, mechanics, "
                "and unresolved questions behind the matchup."
            ),
        },
        "summary": build_summary(claims, dimensions, atoms, clusters),
        "sources": build_sources(claims),
        "themes": clusters.get("themes", []),
        "cross_theme_tensions": clusters.get("cross_theme_tensions", []),
        "source_gaps": clusters.get("source_gaps", []),
        "mechanism_conflicts": atoms_payload.get("conflicts", []),
        "claims": attach_claim_indexes(claims, dimensions, atoms),
    }


def main() -> None:
    APP_PUBLIC.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle()
    OUTPUT_PATH.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
