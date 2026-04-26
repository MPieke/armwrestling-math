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


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "gemini_prelim"
REPORT_PATH = ROOT / "docs" / "ermes_morozov_prelim_analysis.md"

MODEL = "gemini-2.5-flash"
FPS = 0.1
MAX_WORKERS = 2
MAX_RETRIES = 3
MATCH_CONTEXT = """
Upcoming Ermes Gasparini vs Artyom Morozov right-hand match.
We are building a fan + creator narrative-check tool for EVW/KOTT pick'em content.
The target output is not a prediction model. It should surface community narratives,
counter-cases, and timestamped evidence claims that a human can verify.
""".strip()

CANDIDATES = [
    {
        "id": "bWmtNWQM_Ro",
        "url": "https://www.youtube.com/watch?v=bWmtNWQM_Ro",
        "title": "Ermes Gasparini vs Artyom Morozov - East vs West Left Hand Superheavyweight World Title Match",
        "channel": "Engin Terzi Enigma of Rage",
        "why": "Direct head-to-head history, but left hand rather than upcoming right hand.",
    },
    {
        "id": "NsLWax9GwZY",
        "url": "https://www.youtube.com/watch?v=NsLWax9GwZY",
        "title": "Ermes Gasparini - East vs West Podcast",
        "channel": "Engin Terzi Enigma of Rage",
        "why": "Long-form Ermes source before the 2022 East vs West cycle.",
    },
    {
        "id": "28S8Qd02rxI",
        "url": "https://www.youtube.com/watch?v=28S8Qd02rxI",
        "title": "Evgeny Prudnyk - Ermes Gasparini - East vs West Podcast",
        "channel": "Engin Terzi Enigma of Rage",
        "why": "Pre-EVW5 discussion close to Ermes vs Morozov left-hand and Ermes vs Chaffee right-hand.",
    },
    {
        "id": "yGBrHvylMWs",
        "url": "https://www.youtube.com/watch?v=yGBrHvylMWs",
        "title": "Artyom Morozov - East vs West Podcast",
        "channel": "East vs West / Engin Terzi referenced source",
        "why": "Long-form Morozov source referenced by multiple clip videos.",
    },
    {
        "id": "nvlNtq3T-Hw",
        "url": "https://www.youtube.com/watch?v=nvlNtq3T-Hw",
        "title": "ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM",
        "channel": "East vs West Armwrestling",
        "why": "Recent Morozov long-form EVW content.",
    },
    {
        "id": "bZUOAv0Kzxs",
        "url": "https://www.youtube.com/watch?v=bZUOAv0Kzxs",
        "title": "ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM",
        "channel": "East vs West Armwrestling",
        "why": "Very recent Morozov long-form EVW content.",
    },
    {
        "id": "U0kDxaszCu8",
        "url": "https://www.youtube.com/watch?v=U0kDxaszCu8",
        "title": "Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch",
        "channel": "Victorcali Arm Wrestling",
        "why": "Ermes discussing Morozov's style and risks against an elite right-hand opponent.",
    },
    {
        "id": "x5SXZArLVN0",
        "url": "https://www.youtube.com/watch?v=x5SXZArLVN0",
        "title": "Artyom Morozov Predicts Ermes Gasparini vs Levan Saginashvili I Rematch",
        "channel": "Arm wrestling",
        "why": "Morozov giving a view on Ermes against the top right-hand benchmark.",
    },
    {
        "id": "HBfb57rQxTg",
        "url": "https://www.youtube.com/watch?v=HBfb57rQxTg",
        "title": "Levan talks about Alizhan and his supermatch against Ermes",
        "channel": "East vs West / Engin Terzi referenced source",
        "why": "Elite-peer discussion involving Ermes and left-hand title context.",
    },
    {
        "id": "Fg5g-F7TwA4",
        "url": "https://www.youtube.com/watch?v=Fg5g-F7TwA4",
        "title": "Dave Chaffee vs Ermes Gasparini | East vs West 5",
        "channel": "ARMWRESTLING NEWZ",
        "why": "Ermes right-hand result on same card as Morozov/Ermes left-hand.",
    },
]


def safe_filename(video_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", video_id)


def timestamp_url(video_url: str, timestamp: str) -> str:
    parts = timestamp.split(":")
    if len(parts) == 2:
        seconds = int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
        return video_url
    return f"{video_url}&t={seconds}s"


def money(amount: float) -> str:
    return f"${amount:.4f}"


def estimate_cost(usage: dict[str, Any]) -> float:
    details = usage.get("promptTokensDetails", [])
    video_tokens = sum(d.get("tokenCount", 0) for d in details if d.get("modality") == "VIDEO")
    audio_tokens = sum(d.get("tokenCount", 0) for d in details if d.get("modality") == "AUDIO")
    text_tokens = sum(d.get("tokenCount", 0) for d in details if d.get("modality") == "TEXT")
    output_tokens = usage.get("candidatesTokenCount", 0)
    return (
        ((video_tokens + text_tokens) / 1_000_000 * 0.30)
        + (audio_tokens / 1_000_000 * 1.00)
        + (output_tokens / 1_000_000 * 2.50)
    )


def render_report(results: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    total_cost = sum(estimate_cost(item.get("usage_metadata", {})) for item in results)
    total_tokens = sum(item.get("usage_metadata", {}).get("totalTokenCount", 0) for item in results)
    lines = [
        "# Ermes Gasparini vs Artyom Morozov Preliminary Video Analysis",
        "",
        f"Generated: {generated}",
        "",
        "Scope: preliminary Gemini pass over 10 candidate public YouTube videos. This report stores",
        "structured synthesis and timestamp references only, not transcripts.",
        "",
        "Model/settings:",
        "",
        f"- Model: `{MODEL}`",
        f"- Video frame sampling: `{FPS}` FPS",
        "- Input: public YouTube URLs",
        f"- Total Gemini tokens reported: `{total_tokens}`",
        f"- Rough paid-tier cost estimate: `{money(total_cost)}`",
        "",
        "## Cross-Video Read",
        "",
        "- Popular take: Morozov's size, hand, and inside/hook threat are the obvious danger points.",
        "- Counter-case: the strongest Ermes evidence is right-hand-specific, especially his ability to manage elite heavyweights with back pressure, pronation, and containment rather than only raw side pressure.",
        "- Key uncertainty: direct Ermes-vs-Morozov evidence is left-hand; the upcoming right-hand match should not be inferred directly from that result.",
        "- MVP usefulness: the source set is good enough for narrative-check cards, but several videos are weak/indirect and should be replaced with verified recent right-hand analysis if available.",
        "",
        "## Per-Video Evidence",
        "",
    ]

    for item in results:
        meta = item["candidate"]
        analysis = item.get("analysis", {})
        usage = item.get("usage_metadata", {})
        lines.extend(
            [
                f"### {meta['title']}",
                "",
                f"Source: [{meta['channel']}]({meta['url']})",
                "",
                f"Why selected: {meta['why']}",
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
                "Claims:",
                "",
            ]
        )
        claims = analysis.get("claims", [])
        if not claims:
            lines.extend(["- No timestamped claims returned.", ""])
        for claim in claims:
            timestamp = claim.get("timestamp", "")
            link = timestamp_url(meta["url"], timestamp) if timestamp else meta["url"]
            lines.append(
                "- "
                f"[{timestamp}]({link}) "
                f"{claim.get('claim', 'No claim text.')} "
                f"Source: {claim.get('speaker_or_source', 'unknown')}. "
                f"Relevance: {claim.get('relevance', 'not stated')}. "
                f"Confidence: `{claim.get('confidence', 'unknown')}`."
            )
        notes = analysis.get("notes", [])
        if notes:
            lines.extend(["", "Notes:"])
            for note in notes:
                lines.append(f"- {note}")
        lines.extend(
            [
                "",
                "Usage:",
                "",
                f"- Tokens: `{usage.get('totalTokenCount', 0)}`",
                f"- Estimated cost: `{money(estimate_cost(usage))}`",
                "",
            ]
        )
    return "\n".join(lines)


def analyze_candidate(candidate: dict[str, str]) -> dict[str, Any]:
    output_path = OUTPUT_DIR / f"{safe_filename(candidate['id'])}.json"
    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        analysis = existing.get("analysis", {})
        if analysis.get("summary") != "Gemini analysis failed.":
            print(f"Skipping existing success {candidate['id']}", file=sys.stderr)
            return existing

    print(f"Analyzing {candidate['id']} {candidate['url']}", file=sys.stderr)
    last_error = ""
    result = {}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = analyze_youtube_url(
                url=candidate["url"],
                model=MODEL,
                match_context=MATCH_CONTEXT,
                fps=FPS,
                start_seconds=None,
                end_seconds=None,
            )
            break
        except SystemExit as exc:
            last_error = str(exc)
            if "HTTP 429" not in last_error or attempt == MAX_RETRIES:
                break
            sleep_seconds = 20 * attempt
            print(
                f"Rate limited {candidate['id']} attempt {attempt}; sleeping {sleep_seconds}s",
                file=sys.stderr,
            )
            time.sleep(sleep_seconds)
    if not result:
        result = {
            "request": {"url": candidate["url"], "model": MODEL, "fps": FPS},
            "analysis": {
                "summary": "Gemini analysis failed.",
                "claims": [],
                "notes": [last_error],
                "usefulness": "low",
            },
            "usage_metadata": {},
        }
    result["candidate"] = candidate
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"Finished {candidate['id']}", file=sys.stderr)
    return result


def main() -> None:
    load_dotenv(ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_by_id = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_candidate = {
            executor.submit(analyze_candidate, candidate): candidate for candidate in CANDIDATES
        }
        for future in as_completed(future_to_candidate):
            candidate = future_to_candidate[future]
            try:
                results_by_id[candidate["id"]] = future.result()
            except Exception as exc:  # noqa: BLE001
                results_by_id[candidate["id"]] = {
                    "request": {"url": candidate["url"], "model": MODEL, "fps": FPS},
                    "analysis": {
                        "summary": "Unexpected runner failure.",
                        "claims": [],
                        "notes": [repr(exc)],
                        "usefulness": "low",
                    },
                    "usage_metadata": {},
                    "candidate": candidate,
                }

    results = [results_by_id[candidate["id"]] for candidate in CANDIDATES]

    REPORT_PATH.write_text(render_report(results) + "\n", encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
