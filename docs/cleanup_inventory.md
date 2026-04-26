# Cleanup Inventory

This project is moving toward a legal, recency-aware, data-driven evidence pipeline:

1. Discover public YouTube metadata through the official YouTube API.
2. Conservatively filter candidate videos using metadata only.
3. Analyze public YouTube URLs with Gemini, storing structured claims and references only.
4. Add deterministic recency metadata to each claim.
5. Use data-driven clustering over claims; do not predefine narrative categories.

## Current Pipeline

These files are part of the active path.

- `scripts/gemini_video_probe.py`: Gemini public YouTube URL analysis utility.
- `scripts/openai_text.py`: cheap text-model JSON helper for evaluation/clustering.
- `scripts/youtube_api_probe.py`: official YouTube metadata/search utility.
- `scripts/discover_youtube_sources.py`: source discovery from official YouTube metadata.
- `scripts/filter_discovered_sources.py`: conservative metadata-only filtering.
- `scripts/run_expanded_top40_analysis.py`: current cached source-analysis builder.
- `scripts/evidence_recency.py`: deterministic recency rules.
- `scripts/build_app_evidence_dataset.py`: legacy 10-video evidence builder, still used as seed evidence until replaced.
- `scripts/data_driven_cluster_models.py`: Pydantic models for emergent clustering.
- `scripts/cluster_evidence_data_driven.py`: active data-driven clustering entrypoint.

## Deprecated

These files should not be used for the MVP path.

- `scripts/synthesize_match_narrative.py`: deprecated because it asks for fixed narrative fields too early. Keep only as a reference until data-driven clustering replaces it fully.
- `scripts/synthesis_models.py`: deprecated companion schema for `synthesize_match_narrative.py`.
- `data/app/ermes_morozov_match_synthesis_v1.json`: deprecated fixed-synthesis artifact.
- `docs/app/ermes_morozov_match_synthesis_v1.md`: deprecated fixed-synthesis report.
- `data/app/ermes_morozov_match_synthesis_v1_openai_raw.json`: deprecated raw response.
- `data/app/ermes_morozov_match_synthesis_v2_openai_raw.json`: deprecated raw response.

## Archived Experiments

These are not active product code, but they document decisions and should stay until the methodology stabilizes.

- `scripts/run_fps_cost_quality_experiment.py`: showed lower FPS reduces video cost but audio dominates.
- `scripts/run_locator_cost_quality_experiment.py`: showed the locator/window approach missed too much evidence.
- `scripts/run_locator_text_evaluation.py`: text evaluator for locator failure analysis.
- `scripts/run_model_substitution_experiment.py`: model-cost substitution experiments.
- `scripts/run_full_model_substitution_experiment.py`: full candidate model substitution run.
- `scripts/list_gemini_models.py`: model availability probe.
- `docs/experiments/*.md`: experiment records.

## Legal/Feasibility Probes

These are not product code, but should remain as policy evidence.

- `scripts/check_youtube_caption_metadata.py`: verifies caption metadata only, no downloads.
- `scripts/probe_youtube_captions_api.py`: confirms official caption download is OAuth/permission gated.
- `docs/youtube_caption_metadata.md`: metadata results.
- `docs/youtube_official_api_feasibility.md`: API feasibility notes.

## Removed

- `scripts/audit_evidence_coverage.py`: removed because it used predefined evidence categories, which conflicts with the data-driven clustering direction.
- `docs/app/ermes_morozov_evidence_coverage_audit.md`: removed generated report from the predefined-category audit.
