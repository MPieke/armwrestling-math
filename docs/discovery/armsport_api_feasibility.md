# ArmSport Data Source Feasibility Spike

Resolves the gating unknown for a results adapter: does `armsport.app`
expose competition/match data as unauthenticated JSON, or would ingestion
require HTML scraping.

## Verdict

**Yes — unauthenticated, complete, and richer than needed.** Not a
conventional REST API (`api.armsport.app` is a separate Laravel app behind
session/CSRF cookies, likely an admin backend — not the public data source).
The actual source is `armsport.app`'s own Nuxt 3 SSR payload endpoint,
public on every competition page.

## Access Pattern

```text
GET https://armsport.app/competitions/<slug>/_payload.json
```

Slugs are discoverable from `https://armsport.app/sitemap.xml` (not
paginated/rate-limited in 5 rapid sequential requests, ~0.22-0.27s each).
Confirmed working across three different competitions (2.3 KB to 373 KB),
including both single-event supermatch cards (East vs West) and large
multi-category bracket tournaments (World Championship 2014).

The response is **not plain JSON** — it's Nuxt's `devalue`-style flat array
with integer index references instead of nested objects (the same format
`useNuxtApp().payload` deserializes client-side). A ~25-line recursive
resolver reconstructs it fully; verified working, resolver code below.

## Data Shape (`arm_fights`, resolved)

Per match, already present:

```text
hand                     "right" / "left"
category.label           weight class, e.g. "Up to 85 kg"
athlete1 / athlete2      {id, name, first_name, last_name, photo_url}
state                    "finished" / "scheduled"
winner_athlete_id        overall winner
rounds                   [{round_number, winner_athlete_id, status}, ...]
                          -- finer-grained than a final score; score is
                          derived by counting rounds each athlete won
videos                   [{youtube_url, youtube_video_id, title}]
                          -- direct link to match footage, when available
```

Verified example (East vs West 25, 15/15 matches `finished`):

```text
KRASOVSKIS VLADISLAVS vs Artem Popov, hand=right, category=Up to 85 kg,
score=3-0 (derived from rounds), winner=KRASOVSKIS VLADISLAVS
video: https://www.youtube.com/watch?v=0mmm0qQa0SA
```

This maps cleanly onto MPI-19's `ResultSubmission`: `hand` → `arm`,
`state` → `status` (`finished`→`completed`; a `scheduled` fight is
directly usable too), derived score/winner → `CompetitorResultInput`.

## Bonus: solves evidence discovery too

`videos[].youtube_url` is a direct, source-confirmed link to match footage
for fights ArmSport has indexed — for ArmSport-sourced matches, this can
skip MPI-16's fixed-query YouTube search entirely and go straight to a known
video ID via `--video-id`, which is both cheaper and more reliable than
search-based discovery.

## Caveats

- **No named public API contract.** This is an SSR framework's internal
  payload mechanism, not a documented endpoint — it works today by
  observation, not by guarantee. Could change on ArmSport's next deploy with
  no notice. An adapter should fail loudly (not silently degrade) if the
  payload shape changes, and the resolver should be a small, isolated,
  well-tested unit for exactly that reason.
- **No published Terms of Service** (`/terms` renders "Coming Soon"; robots.txt
  disallows only `/login`/`/register`). No explicit permission or
  prohibition either way — worth reading again before high-volume automated
  use, and being a good citizen (reasonable rate, identify a contact if
  asked) rather than treating silence as unlimited license.
- `arm_fights` on a competition page appears to return the full list
  unpaginated (15 for EVW25, presumably more for large brackets) — worth
  confirming there's no silent truncation on a very large event before
  relying on completeness at scale.

## Resolver (verified working)

```python
def resolve(arr, ref, memo):
    if ref in memo:
        return memo[ref]
    val = arr[ref]
    if isinstance(val, dict):
        out = {}
        memo[ref] = out
        for k, v in val.items():
            out[k] = resolve(arr, v, memo) if isinstance(v, int) else v
        return out
    if isinstance(val, list):
        if len(val) == 2 and isinstance(val[0], str) and val[0][:1].isupper():
            tag, inner = val
            resolved = resolve(arr, inner, memo) if isinstance(inner, int) else inner
            memo[ref] = resolved
            return resolved
        out = []
        memo[ref] = out
        for v in val:
            out.append(resolve(arr, v, memo) if isinstance(v, int) else v)
        return out
    memo[ref] = val
    return val

# root = resolve(json.load(open("payload.json")), 0, {})
# root["data"]["competition-<slug>-en"]["data"]["arm_fights"]
```

## Recommendation

Order of attack for the actual adapter (unblocked now):

1. Fetch `sitemap.xml` for competition slugs.
2. Fetch `_payload.json` per slug, resolve, extract `arm_fights`.
3. Map each fight to `ResultSubmission` (MPI-19): derive score/result from
   `rounds`, `hand` → `arm`, competition `date_start`/`name`/`slug` → the
   `EventInput`.
4. For `finished` fights with a `videos[]` entry, pass the video ID directly
   to the existing YouTube evidence pipeline instead of searching.

No new unknowns block starting that adapter ticket.
