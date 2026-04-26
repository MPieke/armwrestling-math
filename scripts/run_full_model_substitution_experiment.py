from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai_text import DEFAULT_MODEL
from run_model_substitution_experiment import (
    FPS,
    MATCH_CONTEXT,
    OUTPUT_DIR as SMALL_OUTPUT_DIR,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    baseline_path,
    cache_path,
    claim_lines,
    evaluate_candidate,
    load_baseline,
    run_candidate,
)
from run_ermes_morozov_prelim import CANDIDATES, estimate_cost, money
from gemini_video_probe import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "experiments" / "model_substitution_full_v1"
REPORT_PATH = ROOT / "docs" / "experiments" / "model_substitution_full_v1.md"

FULL_CANDIDATE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
]


def copy_or_run_candidate(source: dict[str, str], model: str) -> dict[str, Any]:
    local_path = OUTPUT_DIR / cache_path(source, model).name
    if local_path.exists():
        return json.loads(local_path.read_text(encoding="utf-8"))

    previous_path = SMALL_OUTPUT_DIR / cache_path(source, model).name
    if previous_path.exists():
        result = json.loads(previous_path.read_text(encoding="utf-8"))
    else:
        # Reuse the original runner logic, then copy into this experiment namespace.
        old_parent = cache_path(source, model).parent
        old_parent.mkdir(parents=True, exist_ok=True)
        result = run_candidate(source, model)

    result["source"] = source
    local_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def evaluate_full_candidate(
    source: dict[str, str], baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    model = candidate.get("request", {}).get("model", "unknown")
    local_path = OUTPUT_DIR / f"{source['id']}__{model}__openai_eval.json"
    if local_path.exists():
        return json.loads(local_path.read_text(encoding="utf-8"))

    previous_path = SMALL_OUTPUT_DIR / f"{source['id']}__{model}__openai_eval.json"
    if previous_path.exists():
        result = json.loads(previous_path.read_text(encoding="utf-8"))
    else:
        result = evaluate_candidate(source, baseline, candidate)
    local_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def normalize_source(candidate: dict[str, Any]) -> dict[str, str]:
    return {
        "id": candidate["id"],
        "url": candidate["url"],
        "title": candidate["title"],
        "channel": candidate["channel"],
        "type": candidate.get("why", "candidate video"),
    }


def render_report(
    sources: list[dict[str, str]],
    baselines: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    candidate_by_key = {
        (item["source"]["id"], item.get("request", {}).get("model")): item for item in candidates
    }
    eval_by_key = {
        (item["source"]["id"], item["candidate_model"]): item for item in evaluations
    }
    total_gemini_cost = sum(estimate_cost(item.get("usage_metadata", {})) for item in candidates)
    total_openai_cost = sum(item.get("estimated_cost", 0.0) for item in evaluations)

    lines = [
        "# Full Model Substitution Experiment v1",
        "",
        f"Generated: {generated}",
        "",
        "Goal: evaluate the two viable cheaper Gemini models against the full 10-video baseline set.",
        "",
        "Config:",
        "",
        f"- Candidate models: `{', '.join(FULL_CANDIDATE_MODELS)}`",
        f"- FPS: `{FPS}`",
        f"- Prompt version: `{PROMPT_VERSION}`",
        f"- Schema version: `{SCHEMA_VERSION}`",
        f"- Text evaluator: `{DEFAULT_MODEL}`",
        f"- Match context: `{MATCH_CONTEXT[:120]}...`",
        f"- Candidate Gemini estimated cost: `{money(total_gemini_cost)}`",
        f"- OpenAI evaluator estimated cost: `{money(total_openai_cost)}`",
        "",
        "## Summary Table",
        "",
        "| Source | Model | Gemini cost | Coverage | High-value coverage | Quality | Pass/fail |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]

    for source in sources:
        for model in FULL_CANDIDATE_MODELS:
            candidate = candidate_by_key[(source["id"], model)]
            evaluation = eval_by_key[(source["id"], model)]
            analysis = evaluation.get("analysis", {})
            lines.append(
                "| "
                f"[{source['title']}]({source['url']}) | "
                f"`{model}` | "
                f"{money(estimate_cost(candidate.get('usage_metadata', {})))} | "
                f"{analysis.get('all_claim_coverage_percent', 'n/a')} | "
                f"{analysis.get('high_value_coverage_percent', 'n/a')} | "
                f"{analysis.get('quality_grade', 'n/a')} | "
                f"{analysis.get('pass_fail', 'n/a')} |"
            )

    lines.extend(["", "## Recommendation", ""])
    lines.append(
        "Use this report to select the default media model for the MVP. Promote a model only if it "
        "passes most high-signal videos and does not introduce unsupported claims. For videos where "
        "the cheaper model fails, fall back to cached/full `gemini-2.5-flash` analysis."
    )
    lines.extend(["", "## Per-Source Notes", ""])
    for source in sources:
        baseline = baselines[source["id"]]
        lines.extend(
            [
                f"### {source['title']}",
                "",
                "Baseline sample claims:",
                "",
                *claim_lines(source, baseline),
                "",
            ]
        )
        for model in FULL_CANDIDATE_MODELS:
            candidate = candidate_by_key[(source["id"], model)]
            evaluation = eval_by_key[(source["id"], model)]
            lines.extend(
                [
                    f"#### {model}",
                    "",
                    f"Gemini cost: {money(estimate_cost(candidate.get('usage_metadata', {})))}",
                    "",
                    f"Evaluation: {evaluation.get('analysis', {}).get('concise_rationale', 'Not available.')}",
                    "",
                    "Candidate sample claims:",
                    "",
                    *claim_lines(source, candidate),
                    "",
                ]
            )
    return "\n".join(lines)


def main() -> None:
    load_dotenv(ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    sources = [normalize_source(candidate) for candidate in CANDIDATES if baseline_path(candidate).exists()]
    baselines = {source["id"]: load_baseline(source) for source in sources}

    candidates = []
    evaluations = []
    for source in sources:
        for model in FULL_CANDIDATE_MODELS:
            candidate = copy_or_run_candidate(source, model)
            candidates.append(candidate)
            evaluations.append(evaluate_full_candidate(source, baselines[source["id"]], candidate))

    REPORT_PATH.write_text(
        render_report(sources, baselines, candidates, evaluations) + "\n",
        encoding="utf-8",
    )
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
