# Experiment Methodology

Goal: reduce media-analysis cost while preserving or improving the quality of timestamped
armwrestling narrative claims.

## Baseline

Current baseline:

- Provider/model: `gemini-2.5-flash`
- Input: public YouTube URL
- Sampling: `fps=0.01`
- Prompt: current claim extraction prompt in `scripts/gemini_video_probe.py`
- Output: structured JSON claims, no transcript storage
- Baseline artifacts: `data/gemini_prelim/*.json`

The baseline is treated as the temporary quality reference until a human-reviewed gold set exists.

## Iteration Loop

1. Freeze the baseline and evaluation set.
2. Change exactly one variable per experiment where possible.
3. Cache every provider call by deterministic configuration.
4. Run the candidate on the fixed evaluation set.
5. Compare candidate output to baseline with cheap text-side evaluation.
6. Record cost, claim coverage, quality, failures, and next decision.
7. Promote only variants that pass the quality and cost gates.

## Evaluation Set

Start with a small mixed set:

- short commentary clip
- long livestream/podcast
- commentary-heavy match recap

Expand to 6-10 videos once a candidate variant looks promising.

## Cache Policy

Cache keys must include:

- provider
- model
- video id or source id
- start/end seconds
- fps
- prompt version
- schema version
- generation config

If the cache key matches, do not call the provider again.

## Cost Policy

Use Gemini only for media-derived work:

- public YouTube URL audio/video analysis
- media locator, only when metadata/timestamps are insufficient
- final extraction from selected media windows

Use OpenAI `gpt-5-nano` for text-side work:

- source scoring
- claim comparison
- coverage grading
- report synthesis
- dedupe
- prompt/debug analysis

Track estimated cost for every provider and every experiment.

## Quality Gates

A candidate passes only if it satisfies:

- at least 90% high-value baseline claim coverage
- at least 70% all baseline claim coverage
- at least 30-50% cost reduction, depending on experiment goal
- no major fabricated or unsupported claims
- timestamps remain human-checkable
- output remains useful for narrative-check cards

## Failure Taxonomy

- Missed late claims: improve source/window distribution or avoid locator.
- Generic claims: tighten prompt toward tactics/form/injury/confidence/opponent comparison.
- Intro/context over-selection: penalize introductory material.
- Bad timestamps: add validation or widen windows.
- Unsupported claims: strengthen no-invention rule and cite requirement.
- Cost too high: reduce media calls, batch windows, downgrade model, or use text-only stages.
- Quota hit: stop using that model for the day or switch to a clearly labeled alternate.

## Quota Rule

If a provider/model hits quota:

- stop using that exact model for the current experiment run
- do not retry-loop wastefully
- use cached results if available
- try an alternate model only if the model switch is part of the experiment or is clearly labeled
- otherwise stop media experiments and continue text-only evaluation

Fallback order for Gemini media experiments:

1. cached `gemini-2.5-flash` baseline
2. `gemini-2.5-flash-lite`
3. `gemini-2.5-flash-lite-preview-09-2025`
4. `gemini-2.0-flash`, if available and compatible
5. stop media calls; continue OpenAI/text-only work

## Current Next Experiment

Model substitution v1:

- Baseline: cached `gemini-2.5-flash`
- Candidates:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash-lite-preview-09-2025`, if available
  - `gemini-2.0-flash`, if available
- Evaluation set: three representative videos
- Scorer: OpenAI `gpt-5-nano`
- Goal: determine whether a cheaper Gemini model can replace Flash for full-video extraction.
