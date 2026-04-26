from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from gemini_video_probe import load_dotenv


API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-5-nano"

# Standard GPT-5 nano text rates from OpenAI pricing, USD per 1M tokens.
OPENAI_INPUT_PER_1M = 0.05
OPENAI_OUTPUT_PER_1M = 0.40


def openai_api_key() -> str:
    value = os.environ.get("OPENAI_API_KEY")
    if not value:
        raise SystemExit("Missing OPENAI_API_KEY. Add it to .env or export it.")
    return value


def estimate_openai_cost(usage: dict[str, Any]) -> float:
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    return (input_tokens / 1_000_000 * OPENAI_INPUT_PER_1M) + (
        output_tokens / 1_000_000 * OPENAI_OUTPUT_PER_1M
    )


def call_openai_json(
    *,
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    if temperature is not None:
        payload["temperature"] = temperature
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {openai_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from OpenAI API:\n{body}") from exc

    content = raw.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"raw_text": content}
    return {
        "model": model,
        "analysis": parsed,
        "usage": raw.get("usage", {}),
        "estimated_cost": estimate_openai_cost(raw.get("usage", {})),
    }


def load_project_env(root: Path) -> None:
    load_dotenv(root)
