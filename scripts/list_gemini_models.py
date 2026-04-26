from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from gemini_video_probe import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "gemini_models.json"


def main() -> None:
    load_dotenv(ROOT)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY. Add it to .env or export it.")

    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from Gemini API:\n{body}") from exc

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    for model in payload.get("models", []):
        name = model.get("name", "")
        methods = ", ".join(model.get("supportedGenerationMethods", []))
        print(f"{name} [{methods}]")


if __name__ == "__main__":
    main()
