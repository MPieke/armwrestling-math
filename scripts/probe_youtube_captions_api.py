from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from gemini_video_probe import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "youtube_captions_api_probe.json"
API_BASE = "https://www.googleapis.com/youtube/v3"


def get_json(path: str, params: dict[str, str], headers: dict[str, str] | None = None) -> dict[str, Any]:
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "body": body,
        }


def get_bytes(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            return {
                "ok": True,
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "byte_count": len(body),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "body": body,
        }


def main() -> None:
    load_dotenv(ROOT)
    video_id = "U0kDxaszCu8"
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("Missing YOUTUBE_API_KEY.")

    captions_list = get_json(
        "captions",
        {
            "part": "id,snippet",
            "videoId": video_id,
            "key": api_key,
        },
    )
    result = {
        "video_id": video_id,
        "api_key_captions_list": captions_list,
    }

    english_tracks = [
        item
        for item in captions_list.get("items", [])
        if item.get("snippet", {}).get("language") == "en"
    ]
    result["api_key_download_attempts"] = []
    for track in english_tracks:
        caption_id = track["id"]
        download_url = (
            f"{API_BASE}/captions/{urllib.parse.quote(caption_id)}?"
            f"{urllib.parse.urlencode({'tfmt': 'vtt', 'key': api_key})}"
        )
        result["api_key_download_attempts"].append(
            {
                "caption_id": caption_id,
                "track_kind": track.get("snippet", {}).get("trackKind"),
                "language": track.get("snippet", {}).get("language"),
                "download_result": get_bytes(download_url),
            }
        )

    token = os.environ.get("YOUTUBE_OAUTH_TOKEN")
    if token:
        result["oauth_captions_list"] = get_json(
            "captions",
            {
                "part": "id,snippet",
                "videoId": video_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        result["oauth_download_attempts"] = []
        for track in english_tracks:
            caption_id = track["id"]
            download_url = (
                f"{API_BASE}/captions/{urllib.parse.quote(caption_id)}?"
                f"{urllib.parse.urlencode({'tfmt': 'vtt'})}"
            )
            result["oauth_download_attempts"].append(
                {
                    "caption_id": caption_id,
                    "track_kind": track.get("snippet", {}).get("trackKind"),
                    "language": track.get("snippet", {}).get("language"),
                    "download_result": get_bytes(
                        download_url,
                        headers={"Authorization": f"Bearer {token}"},
                    ),
                }
            )
    else:
        result["oauth_captions_list"] = {
            "ok": False,
            "skipped": "Missing YOUTUBE_OAUTH_TOKEN.",
        }

    OUTPUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(OUTPUT_PATH)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
