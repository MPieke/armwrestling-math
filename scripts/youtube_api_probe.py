from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://www.googleapis.com/youtube/v3"


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


def get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from YouTube API:\n{body}") from exc


def build_url(path: str, params: dict[str, str | int]) -> str:
    return f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"


def search_videos(args: argparse.Namespace) -> None:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("Missing YOUTUBE_API_KEY. Add it to .env or export it.")

    params: dict[str, str | int] = {
        "part": "snippet",
        "type": "video",
        "q": args.query,
        "maxResults": args.max_results,
        "videoCaption": "closedCaption" if args.captioned_only else "any",
        "key": api_key,
    }
    if args.order:
        params["order"] = args.order

    payload = get_json(build_url("search", params))
    results = []
    for item in payload.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not video_id:
            continue
        results.append(
            {
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title"),
                "channel": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "description": snippet.get("description"),
            }
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))


def list_captions(args: argparse.Namespace) -> None:
    token = args.oauth_token or os.environ.get("YOUTUBE_OAUTH_TOKEN")
    if not token:
        raise SystemExit(
            "Missing OAuth token. Official captions.list requires YouTube OAuth scopes, "
            "not just an API key."
        )

    params = {
        "part": "id,snippet",
        "videoId": args.video_id,
    }
    headers = {"Authorization": f"Bearer {token}"}
    payload = get_json(build_url("captions", params), headers=headers)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe official YouTube Data API video/caption access.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search YouTube videos with official search.list.")
    search.add_argument("query")
    search.add_argument("--max-results", type=int, default=10)
    search.add_argument("--order", choices=["date", "relevance", "viewCount"], default="relevance")
    search.add_argument(
        "--include-uncaptioned",
        action="store_false",
        dest="captioned_only",
        help="Do not apply videoCaption=closedCaption.",
    )
    search.set_defaults(func=search_videos, captioned_only=True)

    captions = subparsers.add_parser(
        "captions",
        help="List caption tracks. Requires OAuth and sufficient permission on the video.",
    )
    captions.add_argument("video_id")
    captions.add_argument("--oauth-token")
    captions.set_defaults(func=list_captions)

    return parser.parse_args()


def main() -> None:
    load_dotenv(Path.cwd())
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
