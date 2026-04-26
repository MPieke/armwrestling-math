from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gemini_video_probe import load_dotenv
from run_ermes_morozov_prelim import CANDIDATES


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "youtube_caption_metadata.json"
REPORT_PATH = ROOT / "docs" / "youtube_caption_metadata.md"
API_BASE = "https://www.googleapis.com/youtube/v3"


def api_key() -> str:
    value = os.environ.get("YOUTUBE_API_KEY")
    if not value:
        raise SystemExit("Missing YOUTUBE_API_KEY. Add it to .env or export it.")
    return value


def get_json(path: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from YouTube API:\n{body}") from exc


def fetch_video_metadata(video_ids: list[str]) -> list[dict[str, Any]]:
    payload = get_json(
        "videos",
        {
            "part": "snippet,contentDetails,status",
            "id": ",".join(video_ids),
            "key": api_key(),
        },
    )
    by_id = {item["id"]: item for item in payload.get("items", [])}
    results = []
    for candidate in CANDIDATES:
        item = by_id.get(candidate["id"])
        if not item:
            results.append(
                {
                    "id": candidate["id"],
                    "url": candidate["url"],
                    "title": candidate["title"],
                    "channel": candidate["channel"],
                    "found": False,
                    "caption": None,
                }
            )
            continue
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        status = item.get("status", {})
        results.append(
            {
                "id": candidate["id"],
                "url": candidate["url"],
                "title": snippet.get("title", candidate["title"]),
                "channel": snippet.get("channelTitle", candidate["channel"]),
                "published_at": snippet.get("publishedAt"),
                "description": snippet.get("description", ""),
                "duration": content.get("duration"),
                "caption": content.get("caption"),
                "licensed_content": content.get("licensedContent"),
                "privacy_status": status.get("privacyStatus"),
                "license": status.get("license"),
                "embeddable": status.get("embeddable"),
                "found": True,
            }
        )
    return results


def render_report(results: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    captioned = [item for item in results if item.get("caption") == "true"]
    lines = [
        "# YouTube Caption Metadata",
        "",
        f"Generated: {generated}",
        "",
        "Official YouTube Data API metadata check for the 10 Ermes/Morozov candidate videos.",
        "This checks the `contentDetails.caption` flag only. It does not download captions or",
        "transcripts.",
        "",
        "Important: official caption download for arbitrary public videos is still OAuth/edit",
        "permission gated. A `caption=true` flag means YouTube metadata says captions exist, not",
        "that this app may download the transcript through the official API.",
        "",
        f"- Videos checked: `{len(results)}`",
        f"- Caption flag true: `{len(captioned)}`",
        "",
        "## Results",
        "",
        "| Video | Channel | Caption flag | License | Duration |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            "| "
            f"[{item['title']}]({item['url']}) | "
            f"{item.get('channel', '')} | "
            f"`{item.get('caption')}` | "
            f"`{item.get('license')}` | "
            f"`{item.get('duration')}` |"
        )
    lines.extend(["", "## Caption-Flagged Videos", ""])
    if not captioned:
        lines.append("- None.")
    for item in captioned:
        lines.append(f"- [{item['title']}]({item['url']}) by {item.get('channel', '')}")
    return "\n".join(lines)


def main() -> None:
    load_dotenv(ROOT)
    results = fetch_video_metadata([candidate["id"] for candidate in CANDIDATES])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    REPORT_PATH.write_text(render_report(results) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
