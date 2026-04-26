from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gemini_video_probe import analyze_youtube_url, load_dotenv, post_json
from run_ermes_morozov_prelim import estimate_cost, money, timestamp_url


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "experiments" / "locator_cost_quality_v1"
REPORT_PATH = ROOT / "docs" / "experiments" / "locator_cost_quality_v1.md"

BASELINE_MODEL = "gemini-2.5-flash"
LOCATOR_MODEL = "gemini-2.5-flash-lite"
EXTRACTION_MODEL = "gemini-2.5-flash"
FPS = 0.01
MAX_WORKERS = 2
MAX_RETRIES = 3
MAX_WINDOWS = 4
MAX_WINDOW_SECONDS = 420

MATCH_CONTEXT = """
Upcoming Ermes Gasparini vs Artyom Morozov right-hand match.
We need audio-first evidence for a fan narrative-check MVP: tactical claims, form claims,
injury/recovery claims, confidence claims, and opponent-comparison claims. Do not produce
transcripts. Store only synthesis and timestamp references.
""".strip()

SOURCES = [
    {
        "id": "NsLWax9GwZY",
        "url": "https://www.youtube.com/watch?v=NsLWax9GwZY",
        "title": "Ermes Gasparini - East vs West Podcast",
        "channel": "Engin Terzi Enigma of Rage",
        "type": "long Ermes podcast",
    },
    {
        "id": "nvlNtq3T-Hw",
        "url": "https://www.youtube.com/watch?v=nvlNtq3T-Hw",
        "title": "ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM",
        "channel": "East vs West Armwrestling",
        "type": "recent Morozov livestream",
    },
    {
        "id": "bZUOAv0Kzxs",
        "url": "https://www.youtube.com/watch?v=bZUOAv0Kzxs",
        "title": "ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM",
        "channel": "East vs West Armwrestling",
        "type": "very recent Morozov livestream",
    },
]


def api_key() -> str:
    value = __import__("os").environ.get("GEMINI_API_KEY")
    if not value:
        raise SystemExit("Missing GEMINI_API_KEY. Add it to .env or export it.")
    return value


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def parse_timestamp(value: str) -> int | None:
    parts = value.strip().split(":")
    if not all(part.isdigit() for part in parts):
        return None
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return None


def format_timestamp(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def locator_prompt() -> str:
    return f"""
Find only the most relevant audio sections in this YouTube video for the MVP.

Match context:
{MATCH_CONTEXT}

Return only JSON. Do not produce a transcript. Do not quote long passages.
Identify up to {MAX_WINDOWS} windows likely to contain high-signal spoken claims.
Prefer windows that mention Ermes, Morozov, right hand, current shape, recovery, injury,
training, tactical style, hook, toproll, press, setup, hand control, endurance, or elite
opponent comparisons.

Each window should be no longer than {MAX_WINDOW_SECONDS} seconds. If a topic runs longer,
choose the densest subsection.

Schema:
{{
  "windows": [
    {{
      "start": "MM:SS or HH:MM:SS",
      "end": "MM:SS or HH:MM:SS",
      "relevance": 0.0,
      "reason": "why this section is worth final extraction",
      "expected_claim_types": ["form|tactic|injury|confidence|opponent_comparison|other"]
    }}
  ],
  "notes": ["limitations or uncertainty"]
}}
""".strip()


def call_locator(source: dict[str, str]) -> dict[str, Any]:
    video_part = {
        "file_data": {"file_uri": source["url"]},
        "video_metadata": {"fps": FPS},
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    video_part,
                    {"text": locator_prompt()},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{LOCATOR_MODEL}:generateContent?key={api_key()}"
    )
    response = post_json(url, payload)
    text = "\n".join(
        part.get("text", "")
        for part in response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    )
    try:
        analysis = json.loads(text)
    except json.JSONDecodeError:
        analysis = {"windows": [], "notes": [text]}
    return {
        "source": source,
        "request": {"url": source["url"], "model": LOCATOR_MODEL, "fps": FPS},
        "locator": analysis,
        "usage_metadata": response.get("usageMetadata", {}),
    }


def with_retry(label: str, func: Any) -> dict[str, Any]:
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func()
        except SystemExit as exc:
            last_error = str(exc)
            if "HTTP 429" not in last_error and "HTTP 503" not in last_error:
                break
            if attempt == MAX_RETRIES:
                break
            sleep_seconds = 20 * attempt
            print(f"Retryable Gemini error for {label}; sleeping {sleep_seconds}s", file=sys.stderr)
            time.sleep(sleep_seconds)
    return {
        "analysis": {
            "summary": "Gemini analysis failed.",
            "claims": [],
            "notes": [last_error],
            "usefulness": "low",
        },
        "usage_metadata": {},
    }


def baseline_path(source: dict[str, str]) -> Path:
    return ROOT / "data" / "gemini_prelim" / f"{safe_filename(source['id'])}.json"


def load_or_run_baseline(source: dict[str, str]) -> dict[str, Any]:
    path = baseline_path(source)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing["source"] = source
        return existing
    return with_retry(
        f"baseline {source['id']}",
        lambda: analyze_youtube_url(
            url=source["url"],
            model=BASELINE_MODEL,
            match_context=MATCH_CONTEXT,
            fps=FPS,
            start_seconds=None,
            end_seconds=None,
        ),
    )


def normalize_windows(locator: dict[str, Any]) -> list[dict[str, Any]]:
    windows = locator.get("locator", {}).get("windows", [])
    normalized = []
    for window in windows[:MAX_WINDOWS]:
        start = parse_timestamp(str(window.get("start", "")))
        end = parse_timestamp(str(window.get("end", "")))
        if start is None or end is None or end <= start:
            continue
        if end - start > MAX_WINDOW_SECONDS:
            end = start + MAX_WINDOW_SECONDS
        normalized.append({**window, "start_seconds": start, "end_seconds": end})
    return normalized


def extract_window(source: dict[str, str], window: dict[str, Any], index: int) -> dict[str, Any]:
    result = with_retry(
        f"extract {source['id']} window {index}",
        lambda: analyze_youtube_url(
            url=source["url"],
            model=EXTRACTION_MODEL,
            match_context=(
                f"{MATCH_CONTEXT}\n\nAnalyze only this located high-signal window: "
                f"{format_timestamp(window['start_seconds'])}-"
                f"{format_timestamp(window['end_seconds'])}. Locator reason: {window.get('reason', '')}"
            ),
            fps=FPS,
            start_seconds=window["start_seconds"],
            end_seconds=window["end_seconds"],
        ),
    )
    result["window"] = window
    return result


def run_source(source: dict[str, str]) -> dict[str, Any]:
    output_path = OUTPUT_DIR / f"{safe_filename(source['id'])}.json"
    if output_path.exists():
        return json.loads(output_path.read_text(encoding="utf-8"))

    print(f"Running locator experiment for {source['id']}", file=sys.stderr)
    baseline = load_or_run_baseline(source)
    baseline["source"] = source
    locator = with_retry(f"locator {source['id']}", lambda: call_locator(source))
    windows = normalize_windows(locator)
    extractions = [extract_window(source, window, index) for index, window in enumerate(windows, 1)]
    result = {
        "source": source,
        "baseline": baseline,
        "locator": locator,
        "windows": windows,
        "extractions": extractions,
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def claim_count(result: dict[str, Any]) -> int:
    claims = result.get("analysis", {}).get("claims", [])
    return len(claims) if isinstance(claims, list) else 0


def combined_window_claim_count(item: dict[str, Any]) -> int:
    return sum(claim_count(extraction) for extraction in item.get("extractions", []))


def item_cost(item: dict[str, Any]) -> float:
    locator_cost = estimate_cost(item.get("locator", {}).get("usage_metadata", {}))
    extraction_cost = sum(
        estimate_cost(extraction.get("usage_metadata", {}))
        for extraction in item.get("extractions", [])
    )
    return locator_cost + extraction_cost


def item_tokens(item: dict[str, Any]) -> int:
    locator_tokens = item.get("locator", {}).get("usage_metadata", {}).get("totalTokenCount", 0)
    extraction_tokens = sum(
        extraction.get("usage_metadata", {}).get("totalTokenCount", 0)
        for extraction in item.get("extractions", [])
    )
    return locator_tokens + extraction_tokens


def usage_string(usage: dict[str, Any]) -> str:
    return f"`{usage.get('totalTokenCount', 0)}` tokens, {money(estimate_cost(usage))}"


def render_claims(source: dict[str, str], result: dict[str, Any]) -> list[str]:
    claims = result.get("analysis", {}).get("claims", [])
    if not claims:
        return ["- No claims returned."]
    lines = []
    for claim in claims[:4]:
        timestamp = claim.get("timestamp", "")
        link = timestamp_url(source["url"], timestamp) if timestamp else source["url"]
        lines.append(f"- [{timestamp}]({link}) {claim.get('claim', 'No claim text.')}")
    return lines


def render_report(results: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Locator Cost / Quality Experiment v1",
        "",
        f"Generated: {generated}",
        "",
        "Goal: separate signal audio tokens from noise audio tokens by locating relevant windows",
        "before final extraction.",
        "",
        "Design:",
        "",
        f"- Baseline: full-video `{BASELINE_MODEL}` extraction at `fps={FPS}`",
        f"- Locator: full-video `{LOCATOR_MODEL}` pass returning up to `{MAX_WINDOWS}` windows",
        f"- Final extraction: `{EXTRACTION_MODEL}` only on located windows",
        "- Human review target: compare recovered claim quality against full-video baseline",
        "",
        "Important caveat: this still pays for one full-video locator pass. The experiment tests",
        "whether a cheap locator plus window extraction is cheaper and good enough versus full final",
        "extraction. True 10x savings likely require metadata/chapters/manual timestamps before any",
        "full-video audio pass.",
        "",
        "## Summary Table",
        "",
        "| Source | Baseline claims | Baseline cost | Windows | Window claims | Locator+window cost | Cost delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        source = item["source"]
        baseline = item["baseline"]
        baseline_cost = estimate_cost(baseline.get("usage_metadata", {}))
        located_cost = item_cost(item)
        delta = located_cost - baseline_cost
        lines.append(
            "| "
            f"[{source['title']}]({source['url']}) | "
            f"{claim_count(baseline.get('analysis', {}))} | "
            f"{money(baseline_cost)} | "
            f"{len(item.get('windows', []))} | "
            f"{combined_window_claim_count(item)} | "
            f"{money(located_cost)} | "
            f"{money(delta)} |"
        )

    lines.extend(["", "## Per-Source Detail", ""])
    for item in results:
        source = item["source"]
        baseline = item["baseline"]
        locator = item["locator"]
        lines.extend(
            [
                f"### {source['title']}",
                "",
                f"Source: [{source['channel']}]({source['url']})",
                "",
                f"Type: {source['type']}",
                "",
                f"Baseline usage: {usage_string(baseline.get('usage_metadata', {}))}",
                "",
                f"Locator usage: {usage_string(locator.get('usage_metadata', {}))}",
                "",
                f"Locator+window usage: `{item_tokens(item)}` tokens, {money(item_cost(item))}",
                "",
                "Baseline sample claims:",
                "",
                *render_claims(source, baseline),
                "",
                "Located windows:",
                "",
            ]
        )
        if not item.get("windows"):
            lines.append("- No windows returned.")
        for index, window in enumerate(item.get("windows", []), 1):
            start = format_timestamp(window["start_seconds"])
            end = format_timestamp(window["end_seconds"])
            lines.append(
                f"- Window {index}: `{start}-{end}`, relevance `{window.get('relevance')}`. "
                f"Reason: {window.get('reason', 'not stated')}"
            )
        lines.extend(["", "Window extraction sample claims:", ""])
        for index, extraction in enumerate(item.get("extractions", []), 1):
            window = extraction["window"]
            lines.append(
                f"Window {index} `{format_timestamp(window['start_seconds'])}-"
                f"{format_timestamp(window['end_seconds'])}`:"
            )
            lines.extend(render_claims(source, extraction))
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    load_dotenv(ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {executor.submit(run_source, source): source for source in SOURCES}
        for future in as_completed(future_to_source):
            results.append(future.result())

    results_by_id = {item["source"]["id"]: item for item in results}
    ordered = [results_by_id[source["id"]] for source in SOURCES]
    REPORT_PATH.write_text(render_report(ordered) + "\n", encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
