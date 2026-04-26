from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def load_dotenv(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from Gemini API:\n{body}") from exc


def extract_text(response: dict[str, Any]) -> str:
    parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts).strip()


def build_prompt(match_context: str) -> str:
    return f"""
Analyze this public YouTube video for the armwrestling product MVP.

Match context:
{match_context}

Return only JSON. Do not produce a transcript. Do not quote long passages.
Extract up to 8 timestamped claims useful for a narrative-check card.
Prefer tactical, stylistic, form, injury, endurance, setup, hand-control, inside/outside,
and opponent-comparison claims. Ignore generic introductions unless there are no better claims.
If you cannot access or analyze the actual requested video, return usefulness "low", no claims,
and a note explaining the access/problem. Do not invent hypothetical content.

Schema:
{{
  "summary": "one concise sentence",
  "popular_take": "what this video would make a typical fan believe, if any",
  "counter_case": "what this video suggests fans might be missing, if any",
  "claims": [
    {{
      "timestamp": "MM:SS",
      "claim": "specific tactical or narrative claim",
      "speaker_or_source": "person/channel if clear, otherwise unknown",
      "relevance": "why this matters for Ermes vs Morozov right hand",
      "confidence": "low|medium|high"
    }}
  ],
  "key_question": "what decides this match?",
  "usefulness": "low|medium|high",
  "notes": ["limitations or uncertainty"]
}}
""".strip()


def analyze_youtube_url(
    *,
    url: str,
    model: str,
    match_context: str,
    fps: float,
    start_seconds: int | None,
    end_seconds: int | None,
) -> dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY. Add it to .env or export it.")

    video_part: dict[str, Any] = {
        "file_data": {"file_uri": url},
    }
    video_metadata: dict[str, Any] = {"fps": fps}
    if start_seconds is not None:
        video_metadata["start_offset"] = f"{start_seconds}s"
    if end_seconds is not None:
        video_metadata["end_offset"] = f"{end_seconds}s"
    if video_metadata:
        video_part["video_metadata"] = video_metadata

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    video_part,
                    {"text": build_prompt(match_context)},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    api_url = f"{API_BASE}/{model}:generateContent?key={api_key}"
    response = post_json(api_url, payload)
    text = extract_text(response)

    parsed: Any
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"raw_text": text}

    return {
        "request": {
            "url": url,
            "model": model,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "fps": fps,
        },
        "analysis": parsed,
        "usage_metadata": response.get("usageMetadata", {}),
    }


def analyze_youtube(args: argparse.Namespace) -> dict[str, Any]:
    return analyze_youtube_url(
        url=args.url,
        model=args.model,
        match_context=args.match_context,
        fps=args.fps,
        start_seconds=args.start_seconds,
        end_seconds=args.end_seconds,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured armwrestling claims from a YouTube URL with Gemini."
    )
    parser.add_argument("url")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--start-seconds", type=int)
    parser.add_argument("--end-seconds", type=int)
    parser.add_argument(
        "--fps",
        type=float,
        default=0.01,
        help="Low frame sampling reduces video tokens, but does not make YouTube URL input audio-only.",
    )
    parser.add_argument(
        "--match-context",
        default="Upcoming Ermes Gasparini vs Artyom Morozov right-hand match.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    load_dotenv(Path.cwd())
    args = parse_args()
    result = analyze_youtube(args)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
