from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "discovery" / "ermes_morozov_youtube_candidates.json"
OUTPUT_PATH = ROOT / "data" / "discovery" / "ermes_morozov_filtered_candidates.json"
REPORT_PATH = ROOT / "docs" / "discovery" / "ermes_morozov_filtered_candidates.md"

GEMINI_25_FLASH_PER_HOUR = 0.147
GEMINI_3_FLASH_PREVIEW_PER_HOUR = 0.0303
HYBRID_PER_HOUR = 0.1285
OPENAI_EVAL_PER_VIDEO_LOW = 0.0015
OPENAI_EVAL_PER_VIDEO_HIGH = 0.0030


def duration_seconds(value: str | None) -> int:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def classify(row: dict[str, Any]) -> dict[str, Any]:
    title = row.get("title", "").lower()
    description = row.get("description", "").lower()
    combined = f"{title} {description}"
    seconds = duration_seconds(row.get("duration"))
    exclude = False
    category = "review"
    reasons = []

    if seconds <= 45 and any(term in combined for term in ["stage walk", "walkout", "edit", "short"]):
        exclude = True
        category = "exclude_low_signal_short"
        reasons.append("very short stage-walk/edit/short-style video")

    if "cancelled" in combined or "canceled" in combined:
        exclude = True
        category = "exclude_cancellation_context"
        reasons.append("cancellation/replacement news, not current June 2026 analysis")

    if "ermes" in combined and "morozov" in combined:
        category = "direct_or_near_direct"
        reasons.append("mentions both target athletes")
    elif "devon larratt vs ermes" in combined and "morozov" not in combined:
        category = "style_evidence"
        reasons.append("Ermes style context, not direct Morozov matchup")

    if any(term in combined for term in ["prediction", "predict", "analysis", "breakdown"]):
        reasons.append("analysis/prediction language")
    if any(term in combined for term in ["right hand", "right arm"]):
        reasons.append("right-hand/right-arm signal")
    if seconds >= 600:
        reasons.append("long-form or match-length source")
    if not reasons:
        reasons.append("ambiguous; keep for review")

    return {
        **row,
        "duration_seconds": seconds,
        "filter_category": category,
        "exclude_high_confidence": exclude,
        "filter_reasons": reasons,
    }


def media_cost(rows: list[dict[str, Any]], per_hour: float) -> float:
    hours = sum(row["duration_seconds"] for row in rows) / 3600
    return hours * per_hour


def render_report(rows: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    kept = [row for row in rows if not row["exclude_high_confidence"]]
    excluded = [row for row in rows if row["exclude_high_confidence"]]
    total_hours = sum(row["duration_seconds"] for row in rows) / 3600
    kept_hours = sum(row["duration_seconds"] for row in kept) / 3600

    lines = [
        "# Ermes vs Morozov Conservative Source Filter",
        "",
        f"Generated: {generated}",
        "",
        "Policy: only exclude videos when there is high confidence they are not useful for the",
        "June 2026 Ermes vs Morozov right-hand narrative check. Ambiguous videos stay in review.",
        "",
        "## Counts",
        "",
        f"- Input videos: `{len(rows)}`",
        f"- Kept/review videos: `{len(kept)}`",
        f"- High-confidence excluded videos: `{len(excluded)}`",
        f"- Input duration hours: `{total_hours:.2f}`",
        f"- Kept duration hours: `{kept_hours:.2f}`",
        "",
        "## Cost Estimates",
        "",
        "| Scope | Hours | Gemini 3 preview | Gemini 2.5 Flash | Hybrid estimate | + OpenAI eval low/high |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, subset in [
        ("Top 20 discovered", rows[:20]),
        ("Top 40 discovered", rows[:40]),
        ("All discovered", rows),
        ("Kept after conservative filter", kept),
    ]:
        hours = sum(row["duration_seconds"] for row in subset) / 3600
        openai_low = len(subset) * OPENAI_EVAL_PER_VIDEO_LOW
        openai_high = len(subset) * OPENAI_EVAL_PER_VIDEO_HIGH
        lines.append(
            "| "
            f"{label} | "
            f"{hours:.2f} | "
            f"${media_cost(subset, GEMINI_3_FLASH_PREVIEW_PER_HOUR):.2f} | "
            f"${media_cost(subset, GEMINI_25_FLASH_PER_HOUR):.2f} | "
            f"${media_cost(subset, HYBRID_PER_HOUR):.2f} | "
            f"${openai_low:.2f}-${openai_high:.2f} |"
        )

    lines.extend(["", "## Kept / Review Candidates", ""])
    lines.extend(["| Score | Video | Channel | Category | Duration | Reasons |", "| ---: | --- | --- | --- | --- | --- |"])
    for row in kept[:60]:
        lines.append(
            "| "
            f"{row.get('score', 0)} | "
            f"[{row['title']}]({row['url']}) | "
            f"{row['channel']} | "
            f"`{row['filter_category']}` | "
            f"`{row.get('duration')}` | "
            f"{'; '.join(row['filter_reasons'][:4])} |"
        )

    lines.extend(["", "## High-Confidence Exclusions", ""])
    if not excluded:
        lines.append("- None.")
    else:
        lines.extend(["| Video | Channel | Duration | Reason |", "| --- | --- | --- | --- |"])
        for row in excluded:
            lines.append(
                "| "
                f"[{row['title']}]({row['url']}) | "
                f"{row['channel']} | "
                f"`{row.get('duration')}` | "
                f"{'; '.join(row['filter_reasons'])} |"
            )
    return "\n".join(lines)


def main() -> None:
    rows = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    filtered = [classify(row) for row in rows]
    OUTPUT_PATH.write_text(json.dumps(filtered, indent=2, ensure_ascii=False) + "\n")
    REPORT_PATH.write_text(render_report(filtered) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
