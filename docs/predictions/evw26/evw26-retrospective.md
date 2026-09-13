# EVW26 LLM Forecasting Experiment: Retrospective

Status: open-ended record, written 2026-09-13. This document records what was
done, what was observed, and what was discussed afterward. It deliberately does
not commit to an approach; it exists to inform later decisions.

Related files in this directory:

- `evw26-prompt.md` - the final forecasting prompt
- `evw26-dataset.md` - the dataset export supplied to the dataset-enabled runs
- `evw26-chatgpt-analysis.md` - the post-event analysis written by ChatGPT,
  reproduced verbatim

---

## 1. Why the experiment happened

East vs West 26 was held on 12 September 2026 in Jiaxing, China. The in-repo
prediction pipeline was not in a position to produce credible forecasts in time.

A rerun of the existing Tier A rating models on the full local dataset (57
matches from EVW 22-25, 90 athletes, rolling-origin protocol, two folds)
showed why:

| Model | Log-loss | Accuracy |
|---|---|---|
| Elo | 0.70 | 43.1% |
| Glicko2 | 0.77 | 43.1% |
| Bradley-Terry | 0.72 | 43.1% |

All three sit at the random baseline (log-loss ln 2 = 0.693). 46 of the 58
test-row predictions (79%) were cold starts: the athletes had no shared history
in the training window, so every model output p = 0.5. On the 12 rows where a
rating signal existed, accuracy was 16.7% - six matches, too few to mean much,
but no evidence of useful signal either.

The decision was therefore to use frontier LLMs through their consumer UIs
(ChatGPT and Claude), with live web search, as the forecasters for this event,
and to treat the exercise as a genuinely prospective test: the matches had not
happened, so there was no risk of the models having memorised results.

---

## 2. Experiment design

### Goals

1. Get the most informed prediction possible for each match.
2. Surface the factors the models consider decisive and how those factors
   interact, as raw material for later feature engineering.
3. Supply our own accumulated data without letting the models anchor on it.

### Prompt design principles

- **Neutrality.** The prompt names no armwrestling concepts. Listing factors
  (styles, leverage, and so on) would seed the vocabulary and contaminate the
  feature-discovery output, which was one of the main things being collected.
- **Two phases.** Phase 1: research and commit to forecasts independently.
  Phase 2: read the supplied dataset and state, per match, whether and why it
  changes the Phase 1 view. This makes anchoring visible rather than hidden.
- **Search effort.** Iterate heavily, pursue niche and non-English sources, and
  exhaust a useful source (continue through pagination) rather than stopping at
  the first page.
- **No result lookup.** The models were told not to look up EVW26 results and
  to report it if they encountered one.
- **Outputs.** Winner (primary), probability, round score (secondary), and
  free-form reasoning that was explicitly allowed to differ in structure from
  match to match.

### Dataset export

`evw26-dataset.md` contains everything in the canonical tables at the time:
57 match results from EVW 22-25 and 323 commentary claims covering 38 of those
matches, 229 of them carrying model-assigned labels (claim type, temporality,
certainty, concept tags, subject athlete). It states its provenance and
weaknesses plainly: commentator speech rather than measurement, LLM-extracted
and LLM-labelled without human verification, and one promotion over six months.

Two deliberate omissions:

- No concept-frequency summary. A ranked list of the most common tags at the
  top of the file would read as "these are the factors that matter".
- No data from The Armwrestling Archives. Its owner was emailed for permission
  to use the results and had not replied.

Coverage of the EVW26 card itself was thin: 13 of the 29 athletes on the card
appeared in the dataset, each with one or two matches.

### Card sourcing

The card was assembled from secondary sources, which disagreed on match 7.
The first prompt version used Babaiev vs Shterengas; the correct matchup was
Babaiev vs Bubenko, and the prompt was corrected before the final runs. Name
spellings and nationalities also varied between sources.

---

## 3. Pilot run and prompt revision

A pilot run was made with the first prompt version. The dataset was not
actually attached, so the model completed Phase 1 and correctly declined to
invent Phase 2.

### Pilot Phase 1 forecasts

| # | Match | Pick | Prob | Score | Actual winner |
|---|---|---|---|---|---|
| 1 | Larratt - Matyushenko | Larratt | 67% | 3-1 | Larratt |
| 2 | Stoica - Zirakashvili | Stoica | 56% | 4-3 | Stoica (4-3) |
| 3 | Brzenk - Zhao | Brzenk | 57% | 3-2 | Zhao (3-0) |
| 4 | Bornman - Larsson | Bornman | 72% | 3-1 | Bornman (3-0) |
| 5 | Makarov - Cherkasov | Makarov | 59% | 4-3 | Cherkasov (4-3) |
| 6 | Bajčiová - Volkova | Bajčiová | 83% | 4-1 | Bajčiová |
| 7 | Babaiev - Shterengas* | Shterengas | 57% | 3-2 | n/a (actual: Babaiev def. Bubenko 3-0) |
| 8 | Reisek - Orazkhan | Reisek | 60% | 4-3 | Reisek (4-1) |
| 9 | Meranto - Low | Meranto | 72% | 3-1 | Meranto (3-1) |
| 10 | Mercieca - Tanapat | Tanapat | 57% | 3-2 | Mercieca (3-0) |
| 11 | Lovei - Nicholas | Lovei | 65% | 3-1 | Lovei |
| 12 | Liepins - Rui | Liepins | 76% | 3-1 | Liepins |
| 13 | Zhuo - Jolly | Zhuo | 64% | 3-1 | Zhuo |
| 14 | Mask - Arkona | Mask | 55% | 3-2 | Mask (3-0) |

\* Forecast against the stale matchup. Scores shown for actual results are
those reported in the post-event analysis; omitted where not reported.

On the 13 matches with the correct matchup, the pilot picked 10 winners. That
is higher than any of the four final runs (7-9 of 14; see section 4). The pilot
used an earlier, less demanding prompt and a single run, so this is one data
point, not a comparison. It is recorded because it is consistent with an
observation that recurs below: detailed mechanistic reasoning did not obviously
improve winner selection.

### What the pilot output lacked

The pilot's reasoning was careful and well researched, but almost every factor
it used could be derived from a results table: records, head-to-heads,
rankings, transitive comparisons, format length. For feature discovery it
yielded almost nothing new. Specifically absent:

- anthropometrics (hand size, forearm length, reach)
- physical mechanism ("needs the first inch" without saying why)
- round-level dynamics (fatigue, adaptation between rounds, strap restarts)
- start-phase detail (grip, elbow placement, fouls)
- left/right asymmetry as a general property
- falsifiable decision boundaries ("X wins if Y happens")

Likely causes: the dataset (which is mostly technical commentary) was missing;
the word "factors" was ambiguous between evidence and causes; and web search
naturally favours results pages over technique material.

### Revisions made for the final runs

- Name every factor used, including low-confidence ones, rather than the most
  presentable few.
- Describe how factors interact (which dominate when, which cancel, which are
  conditional, in what order they come into play), not a flat list.
- Describe the physical mechanism: what happens between the competitors, in
  what sequence, and why.
- Add two outputs: what would flip the result, and what the model would want
  to know but could not find.
- Attribution: inline source URLs per claim, an `<INTERNAL KNOWLEDGE>` tag for
  prior knowledge not retrieved in-session, and explicit marking of inference.
- Look beyond results tables for technique breakdowns, coaching content,
  interviews and physical attributes.
- Output length explicitly unbounded.
- Attach the dataset before sending the prompt.

All revisions kept the neutrality property: they specify the shape of the
explanation, not its content.

---

## 4. Final runs

Four runs, one prompt: ChatGPT without the dataset, ChatGPT with it, Claude
without it, Claude with it. The raw forecast files are not yet in this
directory; the figures below come from the post-event analysis.

### Headline numbers

| Forecaster | Winners correct |
|---|---|
| ChatGPT, no dataset | 8/14 |
| ChatGPT, with dataset | 9/14 |
| Claude, no dataset | 9/14 |
| Claude, with dataset | 7/14 |
| Market favourite (odds recorded by one run) | 11/14 |

### Results

| # | Match | Winner | Score |
|---|---|---|---|
| 1 | Larratt - Matyushenko | Larratt | |
| 2 | Stoica - Zirakashvili | Stoica | 4-3 |
| 3 | Brzenk - Zhao | Zhao | 3-0 |
| 4 | Bornman - Larsson | Bornman | 3-0 |
| 5 | Makarov - Cherkasov | Cherkasov | 4-3 |
| 6 | Bajčiová - Volkova | Bajčiová | |
| 7 | Babaiev - Bubenko | Babaiev | 3-0 |
| 8 | Reisek - Orazkhan | Reisek | 4-1 |
| 9 | Meranto - Low | Meranto | 3-1 |
| 10 | Mercieca - Tanapat | Mercieca | 3-0 |
| 11 | Lovei - Nicholas | Lovei | |
| 12 | Liepins - Rui | Liepins | |
| 13 | Zhuo - Jolly | Zhuo | |
| 14 | Mask - Arkona | Mask | 3-0 |

### Design problems

These limit what the dataset versus no-dataset comparison can show:

- One no-dataset run independently found dataset-related material while
  researching.
- One dataset run hit a tool limit and read all match results but only part of
  the commentary.
- The repository is public, and `evw26-dataset.md` was pushed to a branch
  before the event. A heavily searching no-dataset run could in principle have
  found it.
- The four runs share model families and web sources, so they are not four
  independent forecasters.

The dataset effect (+1 for ChatGPT, -2 for Claude) is not distinguishable from
noise.

---

## 5. Pitfalls and holes in reasoning

Each is illustrated by one or two matches. With 14 outcomes, every item here is
a hypothesis.

### Treating a technique as a strength advantage (Babaiev - Bubenko)

All four runs picked Bubenko; Babaiev won 3-0. The dataset-enabled reasoning
combined Bubenko's observed toproll, wrist flexion and back pressure against
Bittinger with Babaiev's recent use of an unnatural outside lane into a
coherent thesis. The flaw: a technique label says which *direction* of force an
athlete applies, not *how much*. Succeeding with a movement against one
opponent does not establish enough magnitude to repeat it against another.

### Corroboration counted as new evidence (Makarov - Cherkasov)

All four picked Makarov; Cherkasov won 4-3. One run said the dataset added
nothing beyond a 4-0 result it had already found, then raised its probability
from 79% to 80% anyway because the sources agreed. Agreement between sources
increases confidence that a *fact is recorded correctly*; it should not
increase the *predictive weight* of that fact. Relatedly, recent activity was
weighted over an older but demonstrated elite ceiling.

### Regional results without calibration (Mercieca - Tanapat, Brzenk - Zhao, and others)

All four picked Tanapat; Mercieca won 3-0. One run flipped from Mercieca 54% to
Tanapat 55% after finding he was the current Southeast Asian 85 kg champion.
Nobody had a way to convert a regional title into East vs West level, so the
models did it implicitly. The same problem affected Zhao, Rui, Zhuo, Jolly and
Nicholas.

### More information mistaken for more strength (Brzenk - Zhao)

Three of four picked Brzenk; Zhao won 3-0. The athlete with the larger public
record was easier to reason about, which is not the same as being stronger.
Missing data should widen uncertainty rather than tilt the pick toward the
better-documented athlete.

### Transitive comparisons

"A beat B and B beat C" was among the most-used and weakest tools. Styles make
armwrestling results non-transitive.

### Using age and mass on their own

Babaiev's age was repeatedly treated as a liability, and Arkona's roughly 12 kg
advantage as decisive. Both lost the argument 3-0. Such attributes appear to
matter only through a mechanism: age through the specific ability the athlete's
style relies on, mass through whether it can be connected to the table
position.

### Confidence tracking the story, not the evidence

Pooled, confidence carried weak signal (50-59%: 11/26 correct; 60-69%: 15/20;
70%+: 7/10). But several of the worst misses (Makarov at 78-80%, Bubenko at
70%) were the ones with the richest explanations. Detailed narrative appeared
to raise confidence without adding evidence.

### Correlated consensus

Unanimous picks went 4/7; 3-1 majorities went 4/5. Agreement among runs drawing
on the same sources can mean they all made the same inference from the same
misleading evidence.

### Reading predictability off the final score

Mask - Arkona was a genuine 2-2 split and ended 3-0. Rounds are not independent
draws: whoever wins the decisive first exchange tends to win it again, so a
lopsided score does not show the match was predictable beforehand.

---

## 6. Candidate mechanisms and signals

These are the patterns that seemed to work, or seemed to explain outcomes, with
the conditions under which they appeared to hold and to break. They come from
the analysis and from our discussion afterward, and are all untested.

| Signal | Seemed to work when | Plausible reason | Seemed to break when |
|---|---|---|---|
| Current level (recent, same-arm, opponent-adjusted results) | Broad sample against varied, comparable opposition (Bornman, Meranto, Bajčiová, Lovei) | Averages over many matchups, so style noise cancels | Opponents from disconnected competitive pools (Tanapat, Zhao); old but real elite ceiling (Cherkasov) |
| Direct head-to-head | Same arm, weight, format, recent | It is the actual matchup | Different format, or development since (Reisek - Orazkhan) |
| Technique / style | Paired with a measure of magnitude | Tells the direction of force | Used as a strength advantage in itself (Bubenko) |
| Physical capacity per movement | Not observed in this experiment; the most-cited missing variable | Supplies the magnitude that technique lacks | - |
| Age, mass, anthropometrics | Only through the mechanism they affect | Age acts through the abilities a style depends on; mass through connection to the table | Used on their own (Babaiev, Arkona) |
| Format (Bo5/Bo7, tournament vs supermatch) | Combined with adaptation and endurance | A long format tests repeating a position after the opponent adapts | Results from different formats pooled together |
| Injury | By movement and severity, weighed against the athlete's technique | Damage matters when it hits the force the athlete relies on | Recorded as yes/no |
| Evidence quality and missingness | Always | Should govern uncertainty, not direction | Absent: better-documented athlete favoured; duplicated sources treated as independent |
| Market odds | As a prior | Aggregates many bettors' information | Not tested as more than a reference; would be a problem if copied blindly |

### A recurring structural picture

Across the better explanations, a match looked like this:

1. The first critical position is decided by each athlete's direction of force
   (technique) against the other's, scaled by magnitude (capacity), under the
   specific setup.
2. That position tends to recur round after round, modified by endurance,
   adaptation, injury and format.
3. Rating-based level estimates compress all of this, and appear to work when
   matchup-specific information is weak and fail when a style mismatch
   dominates.

### Missing variables named by the forecasts

Hand dimensions; rise, cup, pronation and back pressure strength; side
pressure; reaction latency; elbow range of motion; current bodyweight and weight
cuts; preferred start path; fatigue across repeated maximal efforts; referee
grip; strap rules; pad geometry; travel.

---

## 7. How much can be taken from this

### The initial critique

The first reaction to the analysis was that it repeats the error it diagnoses:
its author had the outcomes, so each lesson is a story fitted afterward.
Bubenko losing at 60-70% is a 30-40% event, and one outcome cannot separate a
reasoning error from ordinary variance. The analysis also counted correct
winners instead of scoring the probabilities it had asked for (log-loss or
Brier), its calibration bins are within noise at these counts, and the dataset
effect is not identifiable.

### The counter-position

Outcomes are necessary for reasoning about which approaches worked, and bias
from knowing them is the price of learning anything. The appropriate use is to
treat the lessons as hypotheses that shape what to collect and how to structure
prediction, and to test them on future events, not to discard them.

For this purpose, data availability was set aside: assume any attribute could
be collected, and ask what the experiment says about which features matter,
when, and why.

### What seemed to survive that framing

- The experiment is more informative about the *structure* of the problem
  (conditional features, first critical position, evidence quality) than about
  the *weight* of any single feature. Weights need many more outcomes.
- The models were fairly good at surfacing relevant factors and poor at
  weighting and calibrating them.
- Features that matter are mostly conditional, and conditional effects need
  far more data to estimate than there currently is.
- The duplicated-evidence problem is not specific to LLMs. Any pipeline that
  ingests several videos or articles about the same match produces correlated
  claims that could be mistaken for independent evidence.

---

## 8. From one question to two tracks

### The dilemma

Two ways to learn from forecasts were identified, and they lead to different
choices of model, data and prediction target:

- **Correlational / predictive.** Find the smallest set of features correlated
  with correct predictions, whether or not they are causal and even if they
  omit important parts of how matches unfold. Suits simpler models, simpler
  features and simpler targets (a winner probability, perhaps a score).
- **Mechanistic.** Model why a match goes the way it does. Needs causal
  variables, richer targets (how the match unfolds, round by round) and models
  capable of reasoning.

Simpler models imply simpler features and predictions. Reasoned outcomes imply
more capable models.

### Positions taken in the discussion

An initial suggestion was to make calibrated prediction the primary goal and
use mechanism only as a source of candidate features for a statistical model,
because the market outperformed mechanistic LLM reasoning here and LLM
confidence was poorly calibrated.

The response:

- This is a hobby project and the goal is not fixed; both matter.
- The original motivation was that there are reasons athlete B beats athlete A
  despite A being favoured, and those reasons are buried in a haystack of
  data. Finding those needles is a core goal.
- It is independently interesting whether statistical approaches work despite
  all the underlying mechanisms.
- LLMs should not be dismissed as mechanistic predictors. The way data and
  reasoning templates are given to them can be improved, and their progress
  can be tracked over time by forecasting matches that have not yet happened.
  Models themselves also keep improving (the bitter lesson).

### Where it landed

Two tracks, neither committed to over the other, expected to inform each other:

- **Statistical:** does a simpler, correlational approach predict well?
- **Mechanistic:** can reasoning about how matches work (by LLMs or otherwise)
  find the needles and predict well?

If their methodologies diverge, they can be pursued as separate pieces of work
at different times.

### Considerations raised, not resolved

- A "needle" can be framed as a disagreement with a baseline (market or
  rating) that turns out right. Performance on those disagreements may say
  more about the mechanistic track's value than its average accuracy.
- LLM forecasts can only be evaluated on future matches, because of the risk
  that models memorised historical results. At roughly 14 matches per event,
  real differences will take many events to show.
- Tracking LLM improvement over time needs the model version, prompt version,
  data snapshot and tools recorded for each run, or improvements from better
  models cannot be separated from improvements to our own inputs.
- Forecasts must be fixed before the event and kept out of reach of the
  forecasters, which a public repository does not guarantee.
- Should either track predict only the winner, or also the score, or also how
  the match unfolds?
- Should an LLM forecaster see a baseline probability? It might improve
  calibration and might also suppress exactly the disagreements that
  constitute needles.
- Round-level data (who won each round and how) is a candidate shared input:
  a target for score modelling and a way to check mechanistic claims.

---

## 9. Open questions

- Which of the section 5 pitfalls recur on future events, and which were
  one-offs?
- Do the conditional signals in section 6 hold up with more outcomes?
- Does the supplied dataset help or hurt an LLM forecaster once the runs are
  cleanly separated?
- Does the market remain the strongest single forecaster?
- Is there a class of match (disconnected competitive pools, strong style
  mismatches) where mechanistic reasoning outperforms level-based prediction?
- What is the right prediction target for each track?
