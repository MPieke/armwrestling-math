# Armwrestling Narrative Check

Feasibility spike for an MVP fan/creator tool:

> Before you make your EVW/KOTT picks, see what the community might be missing.

## Current Spike

Question: can we analyze captions from YouTube videos using the official YouTube API?

Short answer: official YouTube Data API search works for discovering relevant videos and filtering
for videos that YouTube marks as captioned. Official caption track listing/downloading is much more
restricted:

- `search.list` can be called with an API key and `videoCaption=closedCaption`.
- `captions.list` requires OAuth scopes.
- `captions.download` requires OAuth and the authenticated user must have permission to edit the
  video, so it is not a general public-transcript API.

That means the official API is useful for source discovery and metadata, but not enough by itself
to extract captions from third-party creator videos unless we have owner authorization.

## Setup

Create `.env`:

```sh
YOUTUBE_API_KEY=...
```

Run a captioned-video search:

```sh
uv run python scripts/youtube_api_probe.py search "Ermes Gasparini Morozov armwrestling" --max-results 10
```

Probe caption tracks for a video only if you have an OAuth bearer token for an account authorized
to access that video's captions:

```sh
uv run python scripts/youtube_api_probe.py captions bWmtNWQM_Ro --oauth-token "$YOUTUBE_OAUTH_TOKEN"
```

Run a bounded Gemini YouTube analysis without storing transcripts:

```sh
uv run python scripts/gemini_video_probe.py \
  "https://www.youtube.com/watch?v=bWmtNWQM_Ro" \
  --start-seconds 0 \
  --end-seconds 90 \
  --output data/gemini_claims_bWmtNWQM_Ro.json
```

## Data Policy

For the MVP, store structured claims only:

- video id, title, channel, URL
- timestamped extracted claim
- speaker/source attribution
- match relevance tags

Do not store full transcripts unless a later legal/product decision explicitly allows it.
