# YouTube Official API Feasibility

## Finding

The official YouTube Data API can support source discovery for the MVP, but it cannot generally
provide public captions for arbitrary third-party videos.

Useful official API calls:

- `search.list`: find videos by query, channel, recency, and `videoCaption=closedCaption`.
- `videos.list`: enrich selected videos with statistics, duration, live status, and metadata.
- `captions.list`: list caption tracks, but only with OAuth authorization.
- `captions.download`: download a caption track, but only when the authenticated user has permission
  to edit the video.

## Product Implication

For public creator analysis, the official API path should be:

1. Use `search.list` with `videoCaption=closedCaption` to shortlist videos likely to have captions.
2. Store video metadata and analysis outputs, not transcript text.
3. For caption extraction, use one of these compliant paths:
   - videos uploaded by participating creators who grant OAuth access
   - creator-submitted transcript/caption files
   - manual timestamped claim extraction
   - a later legal review of non-official transcript sources

## MVP Fit

The first MVP can still work if we constrain it:

- 2-3 vetted videos per match
- manual or creator-authorized caption extraction
- structured claims with timestamps only
- no full transcript storage

This keeps the pipeline compatible with the intended product output: narrative check, counter-case,
evidence claims, and shareable match cards.

## Gemini Route

Gemini can analyze public YouTube URLs directly. This avoids scraping YouTube transcript endpoints,
but it is not strictly "audio only" for YouTube URL input. Cost can be reduced by:

- clipping to the relevant interval with `videoMetadata.start_offset` / `end_offset`
- lowering frame sampling with `videoMetadata.fps`
- using `gemini-2.5-flash-lite` for first-pass claim extraction
- asking for structured claims only, not transcripts

If we have a legally obtained audio file, then an audio-only Gemini request is possible through the
Files API or inline audio. That is the cleaner cost-saving path, but it requires creator permission,
licensed media, or another lawful source of the audio.

## Gemini Cost Baseline

Measured on 2026-04-25 with `gemini-2.5-flash-lite`, a public YouTube URL, a 90-second clip, and
`fps=0.1`:

- text prompt: 197 tokens
- video: 2,367 tokens
- audio: 2,880 tokens
- output: 566 tokens
- total: 6,010 tokens

At listed paid-tier prices for `gemini-2.5-flash-lite`:

- text/image/video input: $0.10 per 1M tokens
- audio input: $0.30 per 1M tokens
- output: $0.40 per 1M tokens

That test costs roughly `$0.00135` for 90 seconds, or about `$0.054` per hour if the same token
rate scales linearly. Actual cost varies with clip length, model, frame rate, output length, and
future pricing changes.

For lawful audio-only files, Gemini audio tokenization is documented at 32 tokens per second. On
`gemini-2.5-flash-lite`, one hour of audio input is about 115,200 tokens, or roughly `$0.035`
before output tokens. This is cheaper than YouTube URL video analysis, but only available when we
have a lawful audio file to upload.
