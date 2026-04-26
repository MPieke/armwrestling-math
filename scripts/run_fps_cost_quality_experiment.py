from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gemini_video_probe import analyze_youtube_url, load_dotenv
from run_ermes_morozov_prelim import estimate_cost, money, timestamp_url


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "experiments" / "fps_cost_quality_v1"
REPORT_PATH = ROOT / "docs" / "experiments" / "fps_cost_quality_v1.md"

MODEL = "gemini-2.5-flash"
FPS_VALUES = [0.1, 0.01]
MAX_WORKERS = 2
MAX_RETRIES = 3
MATCH_CONTEXT = """
Upcoming Ermes Gasparini vs Artyom Morozov right-hand match.
This experiment tests whether very low visual frame sampling preserves audio-first analysis quality
while reducing cost. Focus on spoken tactical claims, narrative claims, and timestamp references.
Ignore purely visual observations unless they are clearly supported by commentary.
""".strip()

SOURCES = [
    {
        "id": "U0kDxaszCu8",
        "url": "https://www.youtube.com/watch?v=U0kDxaszCu8",
        "title": "Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch",
        "channel": "Victorcali Arm Wrestling",
        "type": "short commentary clip",
        "why": "Audio-first Morozov tactical commentary from Ermes.",
    },
    {
        "id": "nvlNtq3T-Hw",
        "url": "https://www.youtube.com/watch?v=nvlNtq3T-Hw",
        "title": "ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM",
        "channel": "East vs West Armwrestling",
        "type": "long livestream/podcast",
        "why": "Recent Morozov self-assessment and preparation discussion.",
    },
    {
        "id": "Fg5g-F7TwA4",
        "url": "https://www.youtube.com/watch?v=Fg5g-F7TwA4",
        "title": "Dave Chaffee vs Ermes Gasparini | East vs West 5",
        "channel": "ARMWRESTLING NEWZ",
        "type": "commentary-heavy match recap",
        "why": "Right-hand Ermes evidence with tactical commentary.",
    },
]


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def run_with_retry(source: dict[str, str], fps: float) -> dict[str, Any]:
    output_path = OUTPUT_DIR / f"{safe_filename(source['id'])}_fps_{str(fps).replace('.', '_')}.json"
    if output_path.exists():
        return json.loads(output_path.read_text(encoding="utf-8"))

    last_error = ""
    result: dict[str, Any] = {}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Analyzing {source['id']} at fps={fps}", file=sys.stderr)
            result = analyze_youtube_url(
                url=source["url"],
                model=MODEL,
                match_context=MATCH_CONTEXT,
                fps=fps,
                start_seconds=None,
                end_seconds=None,
            )
            break
        except SystemExit as exc:
            last_error = str(exc)
            if "HTTP 429" not in last_error and "HTTP 503" not in last_error:
                break
            if attempt == MAX_RETRIES:
                break
            sleep_seconds = 20 * attempt
            print(
                f"Retryable Gemini error for {source['id']} fps={fps}; sleeping {sleep_seconds}s",
                file=sys.stderr,
            )
            time.sleep(sleep_seconds)

    if not result:
        result = {
            "request": {"url": source["url"], "model": MODEL, "fps": fps},
            "analysis": {
                "summary": "Gemini analysis failed.",
                "claims": [],
                "notes": [last_error],
                "usefulness": "low",
            },
            "usage_metadata": {},
        }
    result["source"] = source
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def claim_count(result: dict[str, Any]) -> int:
    claims = result.get("analysis", {}).get("claims", [])
    return len(claims) if isinstance(claims, list) else 0


def usage_line(result: dict[str, Any]) -> str:
    usage = result.get("usage_metadata", {})
    details = usage.get("promptTokensDetails", [])
    video_tokens = sum(d.get("tokenCount", 0) for d in details if d.get("modality") == "VIDEO")
    audio_tokens = sum(d.get("tokenCount", 0) for d in details if d.get("modality") == "AUDIO")
    return (
        f"`{usage.get('totalTokenCount', 0)}` total, "
        f"`{audio_tokens}` audio, `{video_tokens}` video, {money(estimate_cost(usage))}"
    )


def render_claims(result: dict[str, Any]) -> list[str]:
    source = result["source"]
    claims = result.get("analysis", {}).get("claims", [])
    if not claims:
        return ["- No claims returned."]
    lines = []
    for claim in claims[:5]:
        timestamp = claim.get("timestamp", "")
        link = timestamp_url(source["url"], timestamp) if timestamp else source["url"]
        lines.append(
            "- "
            f"[{timestamp}]({link}) {claim.get('claim', 'No claim text.')} "
            f"Confidence: `{claim.get('confidence', 'unknown')}`."
        )
    return lines


def render_report(results: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    by_key = {(item["source"]["id"], item["request"]["fps"]): item for item in results}
    lines = [
        "# FPS Cost / Quality Experiment v1",
        "",
        f"Generated: {generated}",
        "",
        "Goal: test whether `fps=0.01` preserves audio-first analysis quality while reducing",
        "Gemini video-token cost for the armwrestling narrative-check MVP.",
        "",
        "Design:",
        "",
        f"- Model: `{MODEL}`",
        "- Sources: one short commentary clip, one long livestream/podcast, one commentary-heavy match recap",
        "- Conditions: `fps=0.1` baseline vs `fps=0.01` reduced visual sampling",
        "- Human review target: compare claim usefulness, timestamp plausibility, and missed tactical detail",
        "",
        "## Summary Table",
        "",
        "| Source | Type | FPS | Claims | Usefulness | Usage / estimated cost |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for source in SOURCES:
        for fps in FPS_VALUES:
            result = by_key[(source["id"], fps)]
            analysis = result.get("analysis", {})
            lines.append(
                "| "
                f"[{source['title']}]({source['url']}) | "
                f"{source['type']} | "
                f"{fps} | "
                f"{claim_count(result)} | "
                f"{analysis.get('usefulness', 'unknown')} | "
                f"{usage_line(result)} |"
            )

    lines.extend(
        [
            "",
            "## Preliminary Read",
            "",
            "- If `fps=0.01` returns comparable spoken claims and timestamps, make it the MVP default.",
            "- Use higher FPS only for match-footage segments where visual mechanics matter.",
            "- Prefer podcasts/livestreams/commentary because their value is in audio claims, not frame detail.",
            "",
            "## Per-Source Comparison",
            "",
        ]
    )
    for source in SOURCES:
        lines.extend(
            [
                f"### {source['title']}",
                "",
                f"Source: [{source['channel']}]({source['url']})",
                "",
                f"Why selected: {source['why']}",
                "",
            ]
        )
        for fps in FPS_VALUES:
            result = by_key[(source["id"], fps)]
            analysis = result.get("analysis", {})
            lines.extend(
                [
                    f"#### FPS {fps}",
                    "",
                    f"Summary: {analysis.get('summary', 'No summary returned.')}",
                    "",
                    f"Popular take: {analysis.get('popular_take', 'Not identified.')}",
                    "",
                    f"Counter-case: {analysis.get('counter_case', 'Not identified.')}",
                    "",
                    f"Key question: {analysis.get('key_question', 'Not identified.')}",
                    "",
                    f"Usefulness: `{analysis.get('usefulness', 'unknown')}`",
                    "",
                    f"Usage: {usage_line(result)}",
                    "",
                    "Claims:",
                    "",
                    *render_claims(result),
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> None:
    load_dotenv(ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    jobs = [(source, fps) for source in SOURCES for fps in FPS_VALUES]
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_job = {
            executor.submit(run_with_retry, source, fps): (source, fps) for source, fps in jobs
        }
        for future in as_completed(future_to_job):
            results.append(future.result())

    REPORT_PATH.write_text(render_report(results) + "\n", encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
