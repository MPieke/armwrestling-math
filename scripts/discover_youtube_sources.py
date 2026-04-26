from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from gemini_video_probe import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SEEDS_PATH = ROOT / "data" / "source_seeds.yaml"
OUTPUT_PATH = ROOT / "data" / "discovery" / "ermes_morozov_youtube_candidates.json"
REPORT_PATH = ROOT / "docs" / "discovery" / "ermes_morozov_youtube_candidates.md"
API_BASE = "https://www.googleapis.com/youtube/v3"

QUERIES = [
    "Ermes Morozov right hand",
    "Ermes Gasparini Artyom Morozov",
    "Ermes vs Morozov prediction",
    "Ermes Morozov East vs West",
    "Artyom Morozov Ermes Gasparini analysis",
    "Ermes Gasparini Morozov Performance Enhancing Pancakes",
    "Ermes Morozov Voice of Armwrestling",
    "Ermes Morozov Grip Kings",
    "Ermes Morozov Armwrestling Newz",
    "Ermes Morozov Filip Larsson Henry Nehring",
    "Ermes Morozov Armwrestling Academia",
    "Ermes Morozov Armwrestling Theory",
    "Ermes Morozov biomechanics",
    "Ermes Morozov gym lifts",
    "Ermes Gasparini measurements forearm weight",
    "Artyom Morozov measurements forearm weight",
    "Ermes Gasparini pronation back pressure lift",
    "Artyom Morozov pronation back pressure lift",
    "Ermes Gasparini armwrestling theory",
    "Artyom Morozov armwrestling theory",
    "armwrestling biomechanics pronation cupping rising back pressure",
]


def api_key() -> str:
    value = os.environ.get("YOUTUBE_API_KEY")
    if not value:
        raise SystemExit("Missing YOUTUBE_API_KEY. Add it to .env or export it.")
    return value


def get_json(path: str, params: dict[str, str | int]) -> dict[str, Any]:
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from YouTube API:\n{body}") from exc


def load_seeds() -> dict[str, Any]:
    return yaml.safe_load(SEEDS_PATH.read_text(encoding="utf-8"))


def search_query(query: str) -> list[dict[str, Any]]:
    payload = get_json(
        "search",
        {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 12,
            "order": "relevance",
            "key": api_key(),
        },
    )
    rows = []
    for item in payload.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})
        rows.append(
            {
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
                "matched_queries": [query],
            }
        )
    return rows


def enrich_videos(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in rows}
    ids = list(by_id)
    for start in range(0, len(ids), 50):
        chunk = ids[start : start + 50]
        payload = get_json(
            "videos",
            {
                "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(chunk),
                "key": api_key(),
            },
        )
        for item in payload.get("items", []):
            row = by_id[item["id"]]
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            stats = item.get("statistics", {})
            status = item.get("status", {})
            row.update(
                {
                    "title": snippet.get("title", row["title"]),
                    "channel": snippet.get("channelTitle", row["channel"]),
                    "published_at": snippet.get("publishedAt", row["published_at"]),
                    "description": snippet.get("description", row["description"]),
                    "duration": content.get("duration"),
                    "caption": content.get("caption"),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
                    "license": status.get("license"),
                }
            )
    return list(by_id.values())


def score_video(row: dict[str, Any], seeds: dict[str, Any]) -> dict[str, Any]:
    title = row.get("title", "").lower()
    description = row.get("description", "").lower()
    channel = row.get("channel", "").lower()
    score = 0
    reasons = []

    for trusted in seeds.get("trusted_channels", []):
        if trusted["name"].lower() in channel:
            score += int(trusted["priority"]) * 3
            reasons.append(f"trusted channel: {trusted['name']}")

    combined = f"{title} {description}"
    for term in seeds.get("positive_title_terms", []):
        if term in combined:
            score += 2
            reasons.append(f"matched term: {term}")

    if "ermes" in combined and "morozov" in combined:
        score += 10
        reasons.append("mentions both Ermes and Morozov")
    elif "ermes" in combined or "morozov" in combined:
        score += 3
        reasons.append("mentions one target athlete")

    for term in seeds.get("negative_title_terms", []):
        if term in combined:
            score -= 4
            reasons.append(f"negative term: {term}")

    if row.get("caption") == "true":
        score += 1
        reasons.append("caption flag true")

    if row.get("view_count", 0) > 10_000:
        score += 1
        reasons.append("10k+ views")

    return {**row, "score": score, "score_reasons": reasons}


def discover() -> list[dict[str, Any]]:
    load_dotenv(ROOT)
    seeds = load_seeds()
    by_id: dict[str, dict[str, Any]] = {}
    for query in QUERIES:
        for row in search_query(query):
            existing = by_id.get(row["id"])
            if existing:
                existing["matched_queries"].extend(row["matched_queries"])
            else:
                by_id[row["id"]] = row
    enriched = enrich_videos(list(by_id.values()))
    scored = [score_video(row, seeds) for row in enriched]
    return sorted(scored, key=lambda row: (row["score"], row.get("view_count", 0)), reverse=True)


def render_report(rows: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Ermes vs Morozov YouTube Source Discovery",
        "",
        f"Generated: {generated}",
        "",
        "Official YouTube Data API metadata discovery. This artifact stores metadata only, not",
        "transcripts, captions, audio, or video.",
        "",
        f"- Queries: `{len(QUERIES)}`",
        f"- Unique videos found: `{len(rows)}`",
        "",
        "## Top Candidates",
        "",
        "| Score | Video | Channel | Caption | Duration | Views | Why |",
        "| ---: | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in rows[:40]:
        why = "; ".join(row.get("score_reasons", [])[:5])
        lines.append(
            "| "
            f"{row['score']} | "
            f"[{row['title']}]({row['url']}) | "
            f"{row['channel']} | "
            f"`{row.get('caption')}` | "
            f"`{row.get('duration')}` | "
            f"{row.get('view_count', 0)} | "
            f"{why} |"
        )
    return "\n".join(lines)


def main() -> None:
    rows = discover()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    REPORT_PATH.write_text(render_report(rows) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
