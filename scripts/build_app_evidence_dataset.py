from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evidence_recency import current_form_allowed, evidence_roles, source_age_days, source_recency_bucket
from run_ermes_morozov_prelim import CANDIDATES, estimate_cost, timestamp_url
from run_full_model_substitution_experiment import FULL_CANDIDATE_MODELS, OUTPUT_DIR as FULL_OUTPUT_DIR
from run_model_substitution_experiment import baseline_path, safe_filename


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "app" / "ermes_morozov_evidence_v1.json"
REPORT_PATH = ROOT / "docs" / "app" / "ermes_morozov_evidence_v1.md"
YOUTUBE_METADATA_PATH = ROOT / "data" / "youtube_caption_metadata.json"


def load_video_metadata() -> dict[str, dict[str, Any]]:
    if not YOUTUBE_METADATA_PATH.exists():
        return {}
    rows = json.loads(YOUTUBE_METADATA_PATH.read_text(encoding="utf-8"))
    return {row["id"]: row for row in rows}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_result_path(video_id: str, model: str) -> Path:
    return FULL_OUTPUT_DIR / f"{safe_filename(video_id)}__{safe_filename(model)}.json"


def candidate_eval_path(video_id: str, model: str) -> Path:
    return FULL_OUTPUT_DIR / f"{video_id}__{model}__openai_eval.json"


def pass_value(value: Any) -> bool:
    return str(value).strip().lower() == "pass"


def select_best_result(video: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    for model in FULL_CANDIDATE_MODELS:
        result_path = candidate_result_path(video["id"], model)
        eval_path = candidate_eval_path(video["id"], model)
        if not result_path.exists() or not eval_path.exists():
            continue
        evaluation = load_json(eval_path)
        if pass_value(evaluation.get("analysis", {}).get("pass_fail")):
            return model, load_json(result_path), evaluation
    baseline = load_json(baseline_path(video))
    return "gemini-2.5-flash-baseline", baseline, None


def normalize_claim(video: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(claim.get("timestamp", ""))
    published_at = video.get("published_at")
    return {
        "claim": claim.get("claim", ""),
        "timestamp": timestamp,
        "source_url": timestamp_url(video["url"], timestamp) if timestamp else video["url"],
        "speaker_or_source": claim.get("speaker_or_source", "unknown"),
        "relevance": claim.get("relevance", ""),
        "confidence": claim.get("confidence", "unknown"),
        "source_published_at": published_at,
        "source_age_days": source_age_days(published_at),
        "source_recency": source_recency_bucket(published_at),
        "current_form_allowed": current_form_allowed(published_at),
        "allowed_evidence_roles": evidence_roles(published_at),
    }


def extract_claims(result: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = result.get("analysis", {})
    if isinstance(analysis, list):
        return analysis
    if isinstance(analysis, dict):
        claims = analysis.get("claims", [])
        return claims if isinstance(claims, list) else []
    return []


def build_dataset() -> dict[str, Any]:
    metadata_by_id = load_video_metadata()
    videos = []
    all_claims = []
    for video in CANDIDATES:
        video = {**video, **metadata_by_id.get(video["id"], {})}
        if not baseline_path(video).exists():
            continue
        selected_model, result, evaluation = select_best_result(video)
        claims = [normalize_claim(video, claim) for claim in extract_claims(result)]
        usage = result.get("usage_metadata", {})
        video_entry = {
            "id": video["id"],
            "title": video["title"],
            "channel": video["channel"],
            "url": video["url"],
            "published_at": video.get("published_at"),
            "source_age_days": source_age_days(video.get("published_at")),
            "source_recency": source_recency_bucket(video.get("published_at")),
            "selected_model": selected_model,
            "model_selection_reason": "cheaper_candidate_passed" if evaluation else "baseline_fallback",
            "estimated_media_cost_usd": estimate_cost(usage),
            "evaluation": evaluation.get("analysis", {}) if evaluation else None,
            "summary": result.get("analysis", {}).get("summary", "")
            if isinstance(result.get("analysis", {}), dict)
            else "",
            "popular_take": result.get("analysis", {}).get("popular_take", "")
            if isinstance(result.get("analysis", {}), dict)
            else "",
            "counter_case": result.get("analysis", {}).get("counter_case", "")
            if isinstance(result.get("analysis", {}), dict)
            else "",
            "key_question": result.get("analysis", {}).get("key_question", "")
            if isinstance(result.get("analysis", {}), dict)
            else "",
            "claims": claims,
        }
        videos.append(video_entry)
        for claim in claims:
            all_claims.append(
                {
                    **claim,
                    "video_id": video["id"],
                    "video_title": video["title"],
                    "channel": video["channel"],
                    "selected_model": selected_model,
                }
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "match": {
            "athlete_a": "Ermes Gasparini",
            "athlete_b": "Artyom Morozov",
            "arm": "right",
            "context": "preliminary narrative-check MVP evidence set",
        },
        "policy": {
            "stores_transcripts": False,
            "stores_structured_claims_only": True,
            "public_youtube_media_path": "Gemini URL analysis",
            "current_form_window_days": 180,
            "recency_rule": (
                "Sources older than the current-form window may support durable style or "
                "historical matchup context, but not current readiness/form."
            ),
        },
        "videos": videos,
        "claims": all_claims,
    }


def render_report(dataset: dict[str, Any]) -> str:
    lines = [
        "# Ermes vs Morozov App Evidence Dataset v1",
        "",
        f"Generated: {dataset['generated_at']}",
        "",
        "Purpose: app-ready structured evidence for the EVW/KOTT narrative-check MVP.",
        "This artifact stores claims and references only, not transcripts.",
        "",
        "## Dataset Summary",
        "",
        f"- Videos: `{len(dataset['videos'])}`",
        f"- Claims: `{len(dataset['claims'])}`",
        "- Selection rule: use cheaper passing candidate model when available, otherwise baseline Flash.",
        "",
        "## Source Coverage",
        "",
        "| Source | Selected model | Claims | Media cost | Recency |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for video in dataset["videos"]:
        lines.append(
            "| "
            f"[{video['title']}]({video['url']}) | "
            f"`{video['selected_model']}` | "
            f"{len(video['claims'])} | "
            f"${video['estimated_media_cost_usd']:.4f} | "
            f"`{video.get('source_recency')}` |"
        )

    lines.extend(["", "## Claim Samples", ""])
    for claim in dataset["claims"][:30]:
        lines.append(
            "- "
            f"[{claim['timestamp']}]({claim['source_url']}) "
            f"{claim['claim']} "
            f"Source: {claim['channel']}. Recency: `{claim.get('source_recency')}`."
        )
    return "\n".join(lines)


def main() -> None:
    dataset = build_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n")
    REPORT_PATH.write_text(render_report(dataset) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
