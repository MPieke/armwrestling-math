# Model Substitution Experiment v1

Generated: 2026-04-25 17:49 UTC

Goal: determine whether cheaper Gemini media models can replace cached
`gemini-2.5-flash` full-video extraction for audio-first narrative claims.

Config:

- Baseline model: `gemini-2.5-flash` cached artifacts
- Candidate models: `gemini-2.5-flash-lite, gemini-2.0-flash-lite, gemini-2.0-flash, gemini-3.1-flash-lite-preview, gemini-3-flash-preview`
- FPS: `0.01`
- Prompt version: `claim_extraction_v1`
- Schema version: `claims_v1`
- Text evaluator: `gpt-5-nano`
- Candidate Gemini estimated cost: `$0.2565`
- OpenAI evaluator estimated cost: `$0.0230`

## Summary Table

| Source | Candidate model | Gemini cost | OpenAI eval cost | Claim coverage | High-value coverage | Quality | Pass/fail |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-2.5-flash-lite` | $0.0056 | $0.0019 | 100 | 100 | Excellent | pass |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-2.0-flash-lite` | $0.0000 | $0.0011 | 0.0 | 0.0 | F | fail |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-2.0-flash` | $0.0000 | $0.0012 | 0 | 0 | fail | fail |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-3.1-flash-lite-preview` | $0.0021 | $0.0017 | 12.5 | 12.5 | low | fail |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-3-flash-preview` | $0.0026 | $0.0013 | 100.0 | 100.0 | A | pass |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-2.5-flash-lite` | $0.1516 | $0.0015 | 37.5 | 75 | moderate | pass |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-2.0-flash-lite` | $0.0000 | $0.0007 | 0 | 0 | fail | FAIL |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-2.0-flash` | $0.0000 | $0.0007 | 0.0 | 0.0 | poor | fail |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-3.1-flash-lite-preview` | $0.0374 | $0.0023 | 25 | 40 | C- | fail |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-3-flash-preview` | $0.0371 | $0.0017 | 62.5 | 71.43 | medium | pass |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-2.5-flash-lite` | $0.0116 | $0.0023 | 62.5 | 62.5 | B | pass |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-2.0-flash-lite` | $0.0000 | $0.0013 | 0 | 0 | poor | fail |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-2.0-flash` | $0.0000 | $0.0008 | 0 | 0 | fail | fail |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-3.1-flash-lite-preview` | $0.0041 | $0.0026 | 50 | 50 | moderate | fail |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-3-flash-preview` | $0.0044 | $0.0019 | 75.0 | 75.0 | B | pass |

## Per-Source Detail

### Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch

Source: [Victorcali Arm Wrestling](https://www.youtube.com/watch?v=U0kDxaszCu8)

Baseline sample claims:

- [00:00](https://www.youtube.com/watch?v=U0kDxaszCu8&t=0s) Many consider Morozov's victory against Jerry Cadorette a sure thing.
- [00:13](https://www.youtube.com/watch?v=U0kDxaszCu8&t=13s) Direct comparisons between athletes can be misleading.
- [00:17](https://www.youtube.com/watch?v=U0kDxaszCu8&t=17s) Morozov's hook is very powerful.
- [00:21](https://www.youtube.com/watch?v=U0kDxaszCu8&t=21s) If Jerry Cadorette manages to establish his position before Morozov, he can beat him.
- [00:27](https://www.youtube.com/watch?v=U0kDxaszCu8&t=27s) Jerry Cadorette's press is a serious threat if he sets his position, as demonstrated against Genadi Kvikvinia.

#### gemini-2.5-flash-lite

Gemini usage cost: $0.0056

Evaluation: Candidate claims semantically cover all baseline claims (8/8). Coverage percent = 100; high-value coverage = 100. Timestamps are offset for most claims (only one exact match at 01:11), indicating imperfect timestamp alignment but content is preserved. No unsupported or missed high-value claims detected. The cheaper candidate model appears viable to replace the baseline for this dataset.

Candidate sample claims:

- [00:18](https://www.youtube.com/watch?v=U0kDxaszCu8&t=18s) Artyom Morozov's hook is very powerful.
- [00:22](https://www.youtube.com/watch?v=U0kDxaszCu8&t=22s) If Jerry Cadorette manages to establish his position before Morozov, he can beat him.
- [00:28](https://www.youtube.com/watch?v=U0kDxaszCu8&t=28s) Jerry Cadorette successfully pressed back Gennadi Kvikviniya when he tried to go in.
- [00:34](https://www.youtube.com/watch?v=U0kDxaszCu8&t=34s) If Jerry sets his position, his press is a serious threat.
- [00:41](https://www.youtube.com/watch?v=U0kDxaszCu8&t=41s) Many people think Morozov will win for sure.

#### gemini-2.0-flash-lite

Gemini usage cost: $0.0000

Evaluation: The candidate model gemini-2.0-flash-lite produced no candidate_claims to cover any baseline_claims, resulting in 0% claim coverage for both all_claim_coverage_percent and high_value_coverage_percent. It cannot replace the baseline; all baseline claims are unsupported and missed. Timestamp quality is not assessable due to the absence of candidate data.

Candidate sample claims:

- No claims returned.

#### gemini-2.0-flash

Gemini usage cost: $0.0000

Evaluation: Candidate model provided no timestamped claims (empty candidate_claims); 0% coverage of baseline claims and 0% coverage of high-value claims. Cannot replace baseline gemini-2.5-flash. To be viable, provide timestamped claims with high-value coverage across baseline points.

Candidate sample claims:

- No claims returned.

#### gemini-3.1-flash-lite-preview

Gemini usage cost: $0.0021

Evaluation: Only one baseline claim is exactly matched by a candidate claim (01:11). The rest are either different claims, not present in baseline, or context-shifted. Coverage is low (≈12.5%), and several high-value baseline claims remain unsupported, indicating the candidate model cannot reliably replace the baseline at this time.

Candidate sample claims:

- [01:11](https://www.youtube.com/watch?v=U0kDxaszCu8&t=71s) Morozov's hook is super strong.
- [01:14](https://www.youtube.com/watch?v=U0kDxaszCu8&t=74s) The match depends on whether Morozov can go faster than Ermes to establish his position.
- [01:22](https://www.youtube.com/watch?v=U0kDxaszCu8&t=82s) If Ermes establishes his position before Morozov, he can win.
- [01:25](https://www.youtube.com/watch?v=U0kDxaszCu8&t=85s) Ermes successfully pressed Gennadi Kvikvinia back when he tried to go inside.

#### gemini-3-flash-preview

Gemini usage cost: $0.0026

Evaluation: All baseline timestamped claims are covered by candidate claims; high-value items are fully addressed; no unsupported or missed high-value claims; timestamps map to the same thematic points; overall evaluation passes.

Candidate sample claims:

- [00:45](https://www.youtube.com/watch?v=U0kDxaszCu8&t=45s) Fans believe Morozov will win easily based on Jerry's recent performances against Ermes and Levan.
- [01:05](https://www.youtube.com/watch?v=U0kDxaszCu8&t=65s) Direct comparisons between athletes are misleading because power levels vary across different technical points.
- [01:13](https://www.youtube.com/watch?v=U0kDxaszCu8&t=73s) Artyom Morozov's hook is 'super strong.'
- [01:18](https://www.youtube.com/watch?v=U0kDxaszCu8&t=78s) Jerry can win if he gets his position faster than Morozov.
- [01:28](https://www.youtube.com/watch?v=U0kDxaszCu8&t=88s) Jerry's press is a serious threat, citing his match where he pressed back against Genadi Kvikvinia.

### ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM

Source: [East vs West Armwrestling](https://www.youtube.com/watch?v=nvlNtq3T-Hw)

Baseline sample claims:

- [02:22](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=142s) Morozov's arm feels better every day, recovering well, and he feels really good.
- [02:31](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=151s) Morozov trains a lot and uses IVs for recovery, indicating intense preparation.
- [11:14](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=674s) Morozov is confident that it will be a good fight.
- [12:15](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=735s) Morozov prefers to focus on hard work and showing results rather than boasting about winning, reflecting a humble and action-oriented approach.
- [39:21](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=2361s) Robert Smith believes Morozov would be a world champion if not for a past injury.

#### gemini-2.5-flash-lite

Gemini usage cost: $0.1516

Evaluation: Candidate claims align with some baseline recovery/training points (e.g., 02:20/02:51) but largely omit several high-value baseline claims and include extraneous content (nicknames, event updates). Overall partial coverage with one notable high-value claim missed; meets a basic pass threshold.

Candidate sample claims:

- [00:51](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=51s) Artyom Morozov's right arm is strong and improving daily.
- [01:02](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=62s) Morozov received the nickname 'Kurt' from Alizhan.
- [01:10](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=70s) Alizhan gave Morozov cheese, and Morozov got the nickname 'Butter wrist'.
- [01:30](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=90s) Morozov received the 'Kurt' nickname from Alizhan, and Morozov got the 'Butter wrist' nickname.
- [02:20](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=140s) Morozov feels good, is training a lot, and his arm is getting better every day.

#### gemini-2.0-flash-lite

Gemini usage cost: $0.0000

Evaluation: Candidate model produced no candidate_claims. Coverage of baseline claims is 0%; high-value claim coverage 0%; all 8 baseline claims are unsupported/missed; timestamp quality 0 due to absence of candidate timestamps; overall evaluation: FAIL.

Candidate sample claims:

- No claims returned.

#### gemini-2.0-flash

Gemini usage cost: $0.0000

Evaluation: Candidate claims set is empty; baseline claims (8 total, all high-value) are entirely unsupported; coverage 0%; timestamp alignment unverifiable due to absence of candidate data; baseline claims treated as untrusted data.

Candidate sample claims:

- No claims returned.

#### gemini-3.1-flash-lite-preview

Gemini usage cost: $0.0374

Evaluation: Candidate claims only partially align with baseline content (roughly 2 of 8 baseline claims). Several high-value baseline claims (confidence about the fight, past injuries, post-surgery wrist strength, and reserve capacity) are not adequately covered, indicating insufficient coverage to replace the baseline model.

Candidate sample claims:

- [02:18](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=138s) Artyom Morozov reports feeling good and training heavily, with his arm recovering and improving daily.
- [03:22](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=202s) Alizhan Muratov confirms his upcoming title match against Vitaly Laletin is officially set for the next event.
- [07:11](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=431s) Alizhan Muratov considers pulling Levan Saginashvili left-handed to be an 'easy' task.
- [15:02](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=902s) Morozov expected Vitaly Laletin to win his match against Devon Larratt, but was surprised by Devon's performance.
- [17:15](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=1035s) Devon Larratt's performance against Vitaly Laletin was aided by his ability to start first and take bites out of Vitaly's strength.

#### gemini-3-flash-preview

Gemini usage cost: $0.0371

Evaluation: Candidate covers 5 of 8 baseline claims (62.5%), including 5 of 7 high-value claims (71.4%), with generally close timestamps. One claim about peaking is unsupported and three high-value baseline claims (confidence, humble approach, past injury) are missed, but overall the candidate is sufficiently aligned to replace the baseline for practical use.

Candidate sample claims:

- [02:18](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=138s) Morozov's right arm is feeling better every day and is recovering well.
- [02:53](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=173s) Morozov is utilizing IVs and intensive training protocols for this preparation.
- [67:00](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4020s) Post-surgery, Morozov's 'rising' strength on his right hand does not drop or fatigue as it did before.
- [67:40](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4060s) Morozov feels he has more 'reserve' strength now than he had previously.
- [67:55](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4075s) Morozov's current body weight is 140kg.

### Dave Chaffee vs Ermes Gasparini | East vs West 5

Source: [ARMWRESTLING NEWZ](https://www.youtube.com/watch?v=Fg5g-F7TwA4)

Baseline sample claims:

- [00:16](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=16s) Ermes Gasparini gained hand control after a slip, but it was very near to the pad, indicating an initial struggle for central control.
- [00:26](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=26s) After gaining hand control, Ermes immediately brought Dave Chaffee back to the center with a couple of surges.
- [00:42](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=42s) Dave Chaffee's side pressure was too much, causing Ermes Gasparini's elbow to slide off the pad, resulting in an elbow foul.
- [01:07](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=67s) Ermes Gasparini secured hand control, brought Dave Chaffee back to the center, got behind his shoulder, planted his elbow, and pressed him to the pad for a win.
- [02:49](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=169s) Ermes Gasparini, while losing his own wrist, intentionally 'dumped' it and immediately executed a very fast 'flop press'.

#### gemini-2.5-flash-lite

Gemini usage cost: $0.0116

Evaluation: Candidate claims cover 5 of 8 baseline claims (≈62.5%), including major moments such as early hand control, center re-centering, elbow foul, flop press, and behind-shoulder press. Three candidate claims are not supported by the baseline (01:33, 01:55, 03:07). Three baseline high-value moments (01:07, 03:39, 04:09) are missed. Timestamp alignment across matched claims averages ~22 seconds, indicating moderate temporal misalignment but reasonable coverage overall.

Candidate sample claims:

- [00:17](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=17s) Ermes Gasparini gains hand control early in the first round but it's very close to the pad.
- [00:49](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=49s) Ermes Gasparini brings Dave Chaffee back to the center with just a couple of surges.
- [00:50](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=50s) Ermes Gasparini's elbow slides off the back of the pad, resulting in an elbow foul.
- [01:33](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=93s) Both competitors were going two seconds before the go in the referee's grip, indicating a potential setup issue or eagerness.
- [01:55](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=115s) A pin is awarded to Dave Chaffee, but the call is reversed after review.

#### gemini-2.0-flash-lite

Gemini usage cost: $0.0000

Evaluation: Candidate produced no claims; coverage against baseline is 0% with all high-value claims missed. Quality grade is poor; timestamp quality unavailable; overall fail to meet baseline analysis needs.

Candidate sample claims:

- No claims returned.

#### gemini-2.0-flash

Gemini usage cost: $0.0000

Evaluation: Candidate produced no claims, resulting in 0% coverage of baseline claims. All baseline high-value claims are missed. Quality grade is fail; not suitable as a replacement. Baseline claims remain unverified by the candidate.

Candidate sample claims:

- No claims returned.

#### gemini-3.1-flash-lite-preview

Gemini usage cost: $0.0041

Evaluation: 4 of 8 baseline claims (50%) are matched by candidate claims (hand control near the pad, elbow foul under side pressure, flop press effectiveness, motivational framing). Several high-value baseline claims remain unsupported (center surges, detailed win sequence, restart interaction, and top-world status). Timestamp alignment is approximate (roughly within a 10-second window). Overall, the cheaper model does not reliably replace the baseline quality.

Candidate sample claims:

- [00:17](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=17s) Ermes Gasparini consistently gained hand control, even when pushed near the pad.
- [00:44](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=44s) Ermes Gasparini is prone to elbow fouls when under heavy side pressure.
- [01:06](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=66s) Ermes's ability to win is contingent on taking the opponent's wrist.
- [01:33](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=93s) Ermes and Chaffee were both struggling with the referee's grip and setup.
- [02:51](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=171s) Ermes possesses a highly effective flop press as a secondary offensive tool.

#### gemini-3-flash-preview

Gemini usage cost: $0.0044

Evaluation: Approximately 75% of baseline claims are covered by candidate claims (6 of 8). High-value claims coverage is also ~75% (3 of 4). There is 1 unsupported candidate claim (01:35) and 1 missed high-value baseline claim (03:39). Overall alignment is good with minor gaps; the candidate passes evaluation.

Candidate sample claims:

- [00:25](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=25s) Ermes gained hand control very near the pad and successfully brought Dave back to the center.
- [01:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=60s) Ermes gets behind his shoulder to press immediately after regaining center.
- [01:35](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=95s) You cannot beat Ermes Gasparini if you have not taken his wrist.
- [02:50](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=170s) Ermes brought Dave back to center with a single surge despite being less than an inch from being pinned.
- [03:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=180s) Ermes has an incredibly fast flop press transition when his wrist is compromised.

