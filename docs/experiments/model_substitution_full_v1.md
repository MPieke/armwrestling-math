# Full Model Substitution Experiment v1

Generated: 2026-04-25 18:39 UTC

Goal: evaluate the two viable cheaper Gemini models against the full 10-video baseline set.

Config:

- Candidate models: `gemini-3-flash-preview, gemini-2.5-flash-lite`
- FPS: `0.01`
- Prompt version: `claim_extraction_v1`
- Schema version: `claims_v1`
- Text evaluator: `gpt-5-nano`
- Match context: `Upcoming Ermes Gasparini vs Artyom Morozov right-hand match.
We are building a fan + creator narrative-check tool for EV...`
- Candidate Gemini estimated cost: `$1.5179`
- OpenAI evaluator estimated cost: `$0.0353`

## Summary Table

| Source | Model | Gemini cost | Coverage | High-value coverage | Quality | Pass/fail |
| --- | --- | ---: | ---: | ---: | --- | --- |
| [Ermes Gasparini vs Artyom Morozov - East vs West Left Hand Superheavyweight World Title Match](https://www.youtube.com/watch?v=bWmtNWQM_Ro) | `gemini-3-flash-preview` | $0.0111 | 50 | 50 | mixed | fail |
| [Ermes Gasparini vs Artyom Morozov - East vs West Left Hand Superheavyweight World Title Match](https://www.youtube.com/watch?v=bWmtNWQM_Ro) | `gemini-2.5-flash-lite` | $0.0394 | 0 | 0 | poor | fail |
| [Ermes Gasparini - East vs West Podcast](https://www.youtube.com/watch?v=NsLWax9GwZY) | `gemini-3-flash-preview` | $0.0419 | 50 | 50 | medium | fail |
| [Ermes Gasparini - East vs West Podcast](https://www.youtube.com/watch?v=NsLWax9GwZY) | `gemini-2.5-flash-lite` | $0.3326 | 0.0 | 0.0 | F | fail |
| [Evgeny Prudnyk - Ermes Gasparini - East vs West Podcast](https://www.youtube.com/watch?v=28S8Qd02rxI) | `gemini-3-flash-preview` | $0.0736 | 12.5 | 33.3333333333 | low | fail |
| [Evgeny Prudnyk - Ermes Gasparini - East vs West Podcast](https://www.youtube.com/watch?v=28S8Qd02rxI) | `gemini-2.5-flash-lite` | $0.3064 | 0 | 0 | low | fail |
| [Artyom Morozov - East vs West Podcast](https://www.youtube.com/watch?v=yGBrHvylMWs) | `gemini-3-flash-preview` | $0.0467 | 0 | 0 | low | fail |
| [Artyom Morozov - East vs West Podcast](https://www.youtube.com/watch?v=yGBrHvylMWs) | `gemini-2.5-flash-lite` | $0.1902 | 12.5 | 12.5 | low | fail |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-3-flash-preview` | $0.0371 | 62.5 | 71.43 | medium | pass |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | `gemini-2.5-flash-lite` | $0.1516 | 37.5 | 75 | moderate | pass |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=bZUOAv0Kzxs) | `gemini-3-flash-preview` | $0.0360 | 37.5 | 37.5 | low | fail |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=bZUOAv0Kzxs) | `gemini-2.5-flash-lite` | $0.1451 | 12.5 | 12.5 | low | fail |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-3-flash-preview` | $0.0026 | 100.0 | 100.0 | A | pass |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | `gemini-2.5-flash-lite` | $0.0056 | 100 | 100 | Excellent | pass |
| [Artyom Morozov Predicts Ermes Gasparini vs Levan Saginashvili I Rematch](https://www.youtube.com/watch?v=x5SXZArLVN0) | `gemini-3-flash-preview` | $0.0028 | 87.5 | 87.5 | B | pass |
| [Artyom Morozov Predicts Ermes Gasparini vs Levan Saginashvili I Rematch](https://www.youtube.com/watch?v=x5SXZArLVN0) | `gemini-2.5-flash-lite` | $0.0065 | 75 | 75 | high | pass |
| [Levan talks about Alizhan and his supermatch against Ermes](https://www.youtube.com/watch?v=HBfb57rQxTg) | `gemini-3-flash-preview` | $0.0154 | 0 | 0 | poor | fail |
| [Levan talks about Alizhan and his supermatch against Ermes](https://www.youtube.com/watch?v=HBfb57rQxTg) | `gemini-2.5-flash-lite` | $0.0572 | 0 | 0 | low | fail |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-3-flash-preview` | $0.0044 | 75.0 | 75.0 | B | pass |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | `gemini-2.5-flash-lite` | $0.0116 | 62.5 | 62.5 | B | pass |

## Recommendation

Use this report to select the default media model for the MVP. Promote a model only if it passes most high-signal videos and does not introduce unsupported claims. For videos where the cheaper model fails, fall back to cached/full `gemini-2.5-flash` analysis.

## Per-Source Notes

### Ermes Gasparini vs Artyom Morozov - East vs West Left Hand Superheavyweight World Title Match

Baseline sample claims:

- [01:15](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=75s) Ermes Gasparini was very happy and a little distracted about his victory over Dave Chaffee (right arm) earlier in the event.
- [01:59](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=119s) Artyom Morozov had a successful night on the right arm against Revaz Lutidze.
- [02:37](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=157s) Artyom Morozov's match against David Dadikyan was phenomenal, showing his heart, ability to go the distance, and fight to the death.
- [05:15](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=315s) Artyom Morozov cups deep on his right arm.
- [06:10](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=370s) Artyom Morozov has a huge frame and genetic God-given size, which is a significant physical advantage.

#### gemini-3-flash-preview

Gemini cost: $0.0111

Evaluation: Candidate coverage is partial (≈50%), with several high-value baseline claims not addressed and multiple candidate claims lacking clear baseline support. Timestamp alignment is weak, reducing reliability.

Candidate sample claims:

- [06:35](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=395s) Ermes initially takes the wrist, but Morozov's back pressure and height hold up.
- [07:15](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=435s) Morozov's natural size and the height of his joint allow him to apply massive pressure even when the wrist is sacrificed.
- [07:35](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=455s) Ermes appears to sacrifice the position or 'give up' the wrist early in the rounds.
- [10:15](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=615s) Ermes likely left too much emotion and energy in his previous match against Dave Chaffee.
- [11:22](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=682s) Morozov's hand and wrist are described as 'steel' during the setup and start.

#### gemini-2.5-flash-lite

Gemini cost: $0.0394

Evaluation: No candidate timestamped claims align with any baseline timestamps; none cover baseline high-value assertions. Candidate content is largely independent and lacks direct corroboration, leading to a failed evaluation.

Candidate sample claims:

- [01:03](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=63s) Ermes Gasparini is back on the arm wrestling table today, he already showed how great of a form he is in right now.
- [01:10](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=70s) 130 kilos of pure arm wrestling awesomeness.
- [01:21](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=81s) He's a little bit distracted about the victory over Dave Chaffey.
- [01:35](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=95s) This giant represents the arm wrestling nation of Kazakhstan.
- [01:50](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=110s) Here comes the man that is the current left arm overall world champion in the East vs West promotion.

### Ermes Gasparini - East vs West Podcast

Baseline sample claims:

- [02:42](https://www.youtube.com/watch?v=NsLWax9GwZY&t=162s) Jerry Cadorette is perceived as 'too powerful' by some fans.
- [11:35](https://www.youtube.com/watch?v=NsLWax9GwZY&t=695s) Ermes Gasparini's current weight is around 127-128 kg.
- [12:06](https://www.youtube.com/watch?v=NsLWax9GwZY&t=726s) Ermes Gasparini's current shape is at 80-85% of his best performance (against Bortolato with left arm).
- [13:07](https://www.youtube.com/watch?v=NsLWax9GwZY&t=787s) Ermes Gasparini believes his current 80-85% shape is 'enough' to beat Jerry Cadorette easily, even if they competed tomorrow.
- [14:24](https://www.youtube.com/watch?v=NsLWax9GwZY&t=864s) Ermes Gasparini doubts Jerry Cadorette's overall strength, believing Jerry would lose to a good hooker like Dave Chaffee.

#### gemini-3-flash-preview

Gemini cost: $0.0419

Evaluation: Candidate covers 4/8 baseline claims (50%), including 4 high-value overlaps with close timestamps (11:38/11:35, 12:05/12:06, 23:56/23:55, 24:35/24:05). Four baseline high-value claims are not represented (02:42, 13:07, 14:24, 22:00). Several candidate claims are not anchored to baseline (e.g., wrist-control assertion, primary-arm focus, Morozov-to-proll claim, and Morozov-shape claim). Timestamp alignment is generally tight for most overlaps (within 1–3 seconds) but one overlap is off by about 30 seconds. Overall assessment: moderate fit; not sufficient to replace baseline.

Candidate sample claims:

- [11:38](https://www.youtube.com/watch?v=NsLWax9GwZY&t=698s) Ermes is currently weighing between 127kg and 128kg.
- [12:05](https://www.youtube.com/watch?v=NsLWax9GwZY&t=725s) Ermes rates his current shape at 85% of his all-time peak (the Bortolato match).
- [19:19](https://www.youtube.com/watch?v=NsLWax9GwZY&t=1159s) Ermes claims he never loses once he has established control over the opponent's wrist.
- [23:56](https://www.youtube.com/watch?v=NsLWax9GwZY&t=1436s) Ermes states that 90% of his career focus and training is dedicated to his right arm.
- [24:35](https://www.youtube.com/watch?v=NsLWax9GwZY&t=1475s) Ermes mentions he is currently dealing with 'a little pain' in his arm.

#### gemini-2.5-flash-lite

Gemini cost: $0.3326

Evaluation: Candidate model provides no claims to cover baseline claims; coverage 0%. All baseline timestamped claims remain unsupported by the candidate, indicating inability to match the baseline's timestamped content. Given untrusted source claims, the replacement model fails to meet coverage requirements.

Candidate sample claims:

- No claims returned.

### Evgeny Prudnyk - Ermes Gasparini - East vs West Podcast

Baseline sample claims:

- [09:40](https://www.youtube.com/watch?v=28S8Qd02rxI&t=580s) Engin Terzi teases Ermes Gasparini about Dave Chaffee potentially 'kicking his ass' in their upcoming match.
- [10:44](https://www.youtube.com/watch?v=28S8Qd02rxI&t=644s) Engin Terzi informs Ermes Gasparini that fans in the chat are saying Dave Chaffee canceled his match after seeing Ermes, implying Dave was intimidated.
- [11:21](https://www.youtube.com/watch?v=28S8Qd02rxI&t=681s) Ermes Gasparini jokes that he doesn't want to post many photos or videos because Dave Chaffee might cancel his match if he sees them.
- [13:44](https://www.youtube.com/watch?v=28S8Qd02rxI&t=824s) Ermes Gasparini states he has a '100%' chance against Dave Chaffee, later adjusting it to '99%' due to potential illness.
- [15:59](https://www.youtube.com/watch?v=28S8Qd02rxI&t=959s) Ermes Gasparini claims Dave Chaffee has 'never felt the top roll like me,' emphasizing his unique wrist and pronation technique.

#### gemini-3-flash-preview

Gemini cost: $0.0736

Evaluation: Candidate covers only one baseline claim (13:44) and misses multiple high-value baseline claims; many candidate claims are not echoed in baseline, indicating insufficient coverage to replace the baseline model.

Candidate sample claims:

- [13:48](https://www.youtube.com/watch?v=28S8Qd02rxI&t=828s) Ermes claims a 100% chance of victory against Dave Chaffee.
- [29:00](https://www.youtube.com/watch?v=28S8Qd02rxI&t=1740s) Ermes admits he might have less endurance now because he is more muscular than ever before.
- [31:45](https://www.youtube.com/watch?v=28S8Qd02rxI&t=1905s) Ermes asserts that Dave Chaffee will not be able to take his wrist.
- [65:05](https://www.youtube.com/watch?v=28S8Qd02rxI&t=3905s) Prudnik predicts that Revaz Lutidze will beat Artyom Morozov.
- [65:55](https://www.youtube.com/watch?v=28S8Qd02rxI&t=3955s) Prudnik ranks Ermes and Revaz as tied for 3rd in the world, with Morozov ranked 5th.

#### gemini-2.5-flash-lite

Gemini cost: $0.3064

Evaluation: Candidate claims occur far earlier in the video (00:39–06:08) than the baseline's timestamps (09:40–37:07), yielding zero coverage of baseline claims. All eight high-value baseline claims are missed. Timestamp alignment is poor, and the candidate provides no overlapping or supporting content to baseline claims. Data treated as untrusted.

Candidate sample claims:

- [00:39](https://www.youtube.com/watch?v=28S8Qd02rxI&t=39s) Engin Terzi greets the audience, setting a conversational tone for the discussion.
- [01:56](https://www.youtube.com/watch?v=28S8Qd02rxI&t=116s) Engin Terzi expresses uncertainty about which style Prudnik might employ against Devon.
- [02:49](https://www.youtube.com/watch?v=28S8Qd02rxI&t=169s) Engin Terzi mentions that Ermes Gasparini had stem cells and then went to Wales as a trainer.
- [03:00](https://www.youtube.com/watch?v=28S8Qd02rxI&t=180s) Engin Terzi states that Ermes Gasparini is currently 261 pounds and aims to reach 253 pounds.
- [03:34](https://www.youtube.com/watch?v=28S8Qd02rxI&t=214s) Engin Terzi confirms that Devon Larratt's match was cancelled due to injury.

### Artyom Morozov - East vs West Podcast

Baseline sample claims:

- [00:08](https://www.youtube.com/watch?v=yGBrHvylMWs&t=8s) Artyom Morozov was sick before his match against Vitaly Laletin, but is now recovering from a partial tendon tear in his left arm, with swelling gone and no severe damage according to MRI.
- [04:03](https://www.youtube.com/watch?v=yGBrHvylMWs&t=243s) Artyom Morozov managed to stop Vitaly Laletin with only back pressure, even after his arm was already cracking.
- [01:34](https://www.youtube.com/watch?v=yGBrHvylMWs&t=94s) Artyom Morozov's wife played a crucial role in his mental preparation, helping him overcome self-doubt and maintain focus, which he believes is key to performance.
- [01:8:06](https://www.youtube.com/watch?v=yGBrHvylMWs&t=4086s) Attacking Michael Todd directly with a top roll is very dangerous for the wrist and side pressure, a strategy Ermes Gasparini correctly avoided.
- [02:00](https://www.youtube.com/watch?v=yGBrHvylMWs&t=120s) Vitaly Laletin has very long fingers, a big hand, and a very long arm, which gives him a significant advantage in pronation and side pressure.

#### gemini-3-flash-preview

Gemini cost: $0.0467

Evaluation: No candidate timestamped claims overlap with any baseline claims. Candidate content focuses on Ermes Gasparini and Morozov matchups not present in baseline, resulting in zero claim-coverage. All high-value baseline claims remain unmet.

Candidate sample claims:

- [17:25](https://www.youtube.com/watch?v=yGBrHvylMWs&t=1045s) Ermes is extremely strong and patient, often allowing opponents to work before capitalizing on their mistakes.
- [24:37](https://www.youtube.com/watch?v=yGBrHvylMWs&t=1477s) Ermes possesses significantly better shoulder pressure on the right arm than Vitaly Laletin.
- [25:05](https://www.youtube.com/watch?v=yGBrHvylMWs&t=1505s) Ermes' shorter arm lever is a tactical advantage for his specific style of pressing and side pressure.
- [38:02](https://www.youtube.com/watch?v=yGBrHvylMWs&t=2282s) Levan Saginashvili's wrist has not fully recovered, leading to a 'fear' of using it as aggressively as he did in the past.
- [39:10](https://www.youtube.com/watch?v=yGBrHvylMWs&t=2350s) Ermes has elite endurance and maintains very strong technical angles even when fatigued.

#### gemini-2.5-flash-lite

Gemini cost: $0.1902

Evaluation: Candidate claims mirror only one baseline timestamp (00:08). The remaining seven baseline claims—covering health status, injury severity, and opponent attributes—have no direct matches in the candidate set, resulting in very low coverage and a failed alignment.

Candidate sample claims:

- [00:05](https://www.youtube.com/watch?v=yGBrHvylMWs&t=5s) Artyom Morozov is feeling sick but is otherwise okay.
- [00:15](https://www.youtube.com/watch?v=yGBrHvylMWs&t=15s) Artyom Morozov got sick during the press conference.
- [01:24](https://www.youtube.com/watch?v=yGBrHvylMWs&t=84s) Artyom Morozov is recovering slowly and wants to train but needs to wait.
- [01:38](https://www.youtube.com/watch?v=yGBrHvylMWs&t=98s) Artyom Morozov believes having a goal is crucial for motivation.
- [02:50](https://www.youtube.com/watch?v=yGBrHvylMWs&t=170s) Artyom Morozov's arm is recovering well, with no swelling and no pain, but he is still being careful.

### ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM

Baseline sample claims:

- [02:22](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=142s) Morozov's arm feels better every day, recovering well, and he feels really good.
- [02:31](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=151s) Morozov trains a lot and uses IVs for recovery, indicating intense preparation.
- [11:14](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=674s) Morozov is confident that it will be a good fight.
- [12:15](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=735s) Morozov prefers to focus on hard work and showing results rather than boasting about winning, reflecting a humble and action-oriented approach.
- [39:21](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=2361s) Robert Smith believes Morozov would be a world champion if not for a past injury.

#### gemini-3-flash-preview

Gemini cost: $0.0371

Evaluation: Candidate covers 5 of 8 baseline claims (62.5%), including 5 of 7 high-value claims (71.4%), with generally close timestamps. One claim about peaking is unsupported and three high-value baseline claims (confidence, humble approach, past injury) are missed, but overall the candidate is sufficiently aligned to replace the baseline for practical use.

Candidate sample claims:

- [02:18](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=138s) Morozov's right arm is feeling better every day and is recovering well.
- [02:53](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=173s) Morozov is utilizing IVs and intensive training protocols for this preparation.
- [67:00](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4020s) Post-surgery, Morozov's 'rising' strength on his right hand does not drop or fatigue as it did before.
- [67:40](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4060s) Morozov feels he has more 'reserve' strength now than he had previously.
- [67:55](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4075s) Morozov's current body weight is 140kg.

#### gemini-2.5-flash-lite

Gemini cost: $0.1516

Evaluation: Candidate claims align with some baseline recovery/training points (e.g., 02:20/02:51) but largely omit several high-value baseline claims and include extraneous content (nicknames, event updates). Overall partial coverage with one notable high-value claim missed; meets a basic pass threshold.

Candidate sample claims:

- [00:51](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=51s) Artyom Morozov's right arm is strong and improving daily.
- [01:02](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=62s) Morozov received the nickname 'Kurt' from Alizhan.
- [01:10](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=70s) Alizhan gave Morozov cheese, and Morozov got the nickname 'Butter wrist'.
- [01:30](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=90s) Morozov received the 'Kurt' nickname from Alizhan, and Morozov got the 'Butter wrist' nickname.
- [02:20](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=140s) Morozov feels good, is training a lot, and his arm is getting better every day.

### ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM

Baseline sample claims:

- [03:03](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=183s) Artem Morozov's current weight is 138kg (~305 lbs).
- [15:04](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=904s) Morozov's self-assessment of his past match against Vitaly Laletin was that it was primarily a 'strength issue' and Vitaly is 'just power.' He believes if he were stronger, he would have had fewer injuries and pulled more efficiently.
- [16:11](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=971s) Morozov cannot definitively say if he is stronger now than when he pulled Vitaly Laletin, as Vitaly was not in peak shape then.
- [70:15](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=4215s) Morozov had a training plan from the beginning and stuck to it. He trains consistently but now goes by feeling, not a strict plan. He tried training twice a day but it's not for him.
- [69:14](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=4154s) Morozov's motivation is driven by the saying, 'A crazy head doesn't let your arms rest.'

#### gemini-3-flash-preview

Gemini cost: $0.0360

Evaluation: Only 3 of 8 baseline claims are covered by the candidate (37.5%). Several high-value claims are not supported by the candidate, and there is limited timestamp alignment with baseline claims, indicating the candidate is not adequate to replace the baseline model.

Candidate sample claims:

- [03:03](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=183s) Artyom Morozov's current weight is 138kg (approximately 304-305 lbs).
- [15:55](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=955s) Morozov attributes his loss to Vitaly Laletin to a lack of raw strength rather than technical errors.
- [17:15](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=1035s) Vitaly Laletin was in significantly better shape against Devon Sarratt than he was against Morozov.
- [47:00](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=2820s) Morozov advocates for removing elbow pad and foul rules after the 'Ready Go' to allow for pure grinding matches until someone quits.
- [55:45](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=3345s) Dave Chaffee's endurance appeared much improved in his match against Sagov compared to his match against Morozov.

#### gemini-2.5-flash-lite

Gemini cost: $0.1451

Evaluation: Candidate covers only one of the eight baseline claims (weight). The rest are not supported, yielding low coverage and insufficient alignment to replace baseline.

Candidate sample claims:

- [00:36](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=36s) The podcast will feature a discussion with Artyom Morozov and Oleksandr Telyatnik.
- [01:13](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=73s) Artyom Morozov's area of expertise is ensuring understanding between participants.
- [01:35](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=95s) Artyom Morozov is considered a 'beast' by some people.
- [03:09](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=189s) Artyom Morozov's weight is 305 lbs.
- [03:37](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=217s) There are a couple of former champions and one current champion in the podcast.

### Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch

Baseline sample claims:

- [00:00](https://www.youtube.com/watch?v=U0kDxaszCu8&t=0s) Many consider Morozov's victory against Jerry Cadorette a sure thing.
- [00:13](https://www.youtube.com/watch?v=U0kDxaszCu8&t=13s) Direct comparisons between athletes can be misleading.
- [00:17](https://www.youtube.com/watch?v=U0kDxaszCu8&t=17s) Morozov's hook is very powerful.
- [00:21](https://www.youtube.com/watch?v=U0kDxaszCu8&t=21s) If Jerry Cadorette manages to establish his position before Morozov, he can beat him.
- [00:27](https://www.youtube.com/watch?v=U0kDxaszCu8&t=27s) Jerry Cadorette's press is a serious threat if he sets his position, as demonstrated against Genadi Kvikvinia.

#### gemini-3-flash-preview

Gemini cost: $0.0026

Evaluation: All baseline timestamped claims are covered by candidate claims; high-value items are fully addressed; no unsupported or missed high-value claims; timestamps map to the same thematic points; overall evaluation passes.

Candidate sample claims:

- [00:45](https://www.youtube.com/watch?v=U0kDxaszCu8&t=45s) Fans believe Morozov will win easily based on Jerry's recent performances against Ermes and Levan.
- [01:05](https://www.youtube.com/watch?v=U0kDxaszCu8&t=65s) Direct comparisons between athletes are misleading because power levels vary across different technical points.
- [01:13](https://www.youtube.com/watch?v=U0kDxaszCu8&t=73s) Artyom Morozov's hook is 'super strong.'
- [01:18](https://www.youtube.com/watch?v=U0kDxaszCu8&t=78s) Jerry can win if he gets his position faster than Morozov.
- [01:28](https://www.youtube.com/watch?v=U0kDxaszCu8&t=88s) Jerry's press is a serious threat, citing his match where he pressed back against Genadi Kvikvinia.

#### gemini-2.5-flash-lite

Gemini cost: $0.0056

Evaluation: Candidate claims semantically cover all baseline claims (8/8). Coverage percent = 100; high-value coverage = 100. Timestamps are offset for most claims (only one exact match at 01:11), indicating imperfect timestamp alignment but content is preserved. No unsupported or missed high-value claims detected. The cheaper candidate model appears viable to replace the baseline for this dataset.

Candidate sample claims:

- [00:18](https://www.youtube.com/watch?v=U0kDxaszCu8&t=18s) Artyom Morozov's hook is very powerful.
- [00:22](https://www.youtube.com/watch?v=U0kDxaszCu8&t=22s) If Jerry Cadorette manages to establish his position before Morozov, he can beat him.
- [00:28](https://www.youtube.com/watch?v=U0kDxaszCu8&t=28s) Jerry Cadorette successfully pressed back Gennadi Kvikviniya when he tried to go in.
- [00:34](https://www.youtube.com/watch?v=U0kDxaszCu8&t=34s) If Jerry sets his position, his press is a serious threat.
- [00:41](https://www.youtube.com/watch?v=U0kDxaszCu8&t=41s) Many people think Morozov will win for sure.

### Artyom Morozov Predicts Ermes Gasparini vs Levan Saginashvili I Rematch

Baseline sample claims:

- [00:17](https://www.youtube.com/watch?v=x5SXZArLVN0&t=17s) The outcome of the Ermes vs Levan rematch will heavily depend on the condition of Levan's wrist.
- [00:22](https://www.youtube.com/watch?v=x5SXZArLVN0&t=22s) Levan's wrist 'cracked' during his last match against Devon Larratt.
- [00:30](https://www.youtube.com/watch?v=x5SXZArLVN0&t=30s) If Levan is 100% ready and his wrist is stronger, he is the favorite.
- [00:36](https://www.youtube.com/watch?v=x5SXZArLVN0&t=36s) Ermes Gasparini possesses a very strong press.
- [00:52](https://www.youtube.com/watch?v=x5SXZArLVN0&t=52s) Levan's wrist is not working with the same 'flexing' capability as before, possibly due to injury or fear.

#### gemini-3-flash-preview

Gemini cost: $0.0028

Evaluation: Candidate claims largely reflect baseline topics (Levan's wrist issues, Ermes' strength/endurance gains, Levan's speed). Seven of eight baseline claims are echoed; one high-value claim (00:30) about Levan's favorite status if ready is not directly covered by candidate claims; one new candidate claim is not grounded in baseline (50/50 toss-up). Overall, strong coverage with one miss and one unsupported claim.

Candidate sample claims:

- [00:51](https://www.youtube.com/watch?v=x5SXZArLVN0&t=51s) Levan's wrist may still be injured or he is psychologically hesitant to use it fully.
- [01:10](https://www.youtube.com/watch?v=x5SXZArLVN0&t=70s) Ermes has significantly increased his training weights and overall power.
- [01:40](https://www.youtube.com/watch?v=x5SXZArLVN0&t=100s) Ermes has specifically improved his endurance and is much better in long matches now.
- [01:45](https://www.youtube.com/watch?v=x5SXZArLVN0&t=105s) Levan will likely still have a speed advantage over Ermes.
- [01:52](https://www.youtube.com/watch?v=x5SXZArLVN0&t=112s) The match between Ermes and Levan is now a 50/50 toss-up.

#### gemini-2.5-flash-lite

Gemini cost: $0.0065

Evaluation: Candidate claims cover 6 of 8 baseline high-value items (75%), with 3 unrelated claims and 3 timestamps aligning with baseline. Overall quality is high, but several candidate claims are unsupported by baseline, and two high-value baseline claims are not covered.

Candidate sample claims:

- [00:04](https://www.youtube.com/watch?v=x5SXZArLVN0&t=4s) Artyom Morozov predicts a supermatch between Ermes Gasparini and Levan Saginashvili.
- [00:08](https://www.youtube.com/watch?v=x5SXZArLVN0&t=8s) Morozov believes the match will be incredible and a war.
- [00:17](https://www.youtube.com/watch?v=x5SXZArLVN0&t=17s) Morozov states the outcome depends on Levan's wrist in this match.
- [00:22](https://www.youtube.com/watch?v=x5SXZArLVN0&t=22s) Morozov recalls Levan's wrist cracking in a previous match against Devon.
- [00:30](https://www.youtube.com/watch?v=x5SXZArLVN0&t=30s) Morozov suggests if Levan's wrist is strong, he is the favorite.

### Levan talks about Alizhan and his supermatch against Ermes

Baseline sample claims:

- [04:25](https://www.youtube.com/watch?v=HBfb57rQxTg&t=265s) Levan states he identified and worked on his 'minuses' (weight, technique) after his match with Ermes.
- [11:47](https://www.youtube.com/watch?v=HBfb57rQxTg&t=707s) Levan believes Alizhan Muradov (at 150kg) can beat Morozov.
- [20:29](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1229s) Levan anticipates a close match between Ermes and Denis.
- [20:52](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1252s) Levan considers Ermes a slight favorite (10% edge) against Denis.
- [21:08](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1268s) Levan notes Denis possesses a 'huge hand' and 'very good static' that could challenge Ermes's wrist.

#### gemini-3-flash-preview

Gemini cost: $0.0154

Evaluation: Candidate claims are empty; no coverage of baseline timestamped claims. All baseline claims are unsupported and missed. Data treated as untrusted; cannot verify content.

Candidate sample claims:

- [](https://www.youtube.com/watch?v=HBfb57rQxTg) No claim text.

#### gemini-2.5-flash-lite

Gemini cost: $0.0572

Evaluation: Candidate claims do not align with any baseline claims; zero coverage of baseline content; only one high-value baseline claim (Morozov-related) is missed; overall data quality is insufficient for replacement.

Candidate sample claims:

- [00:14](https://www.youtube.com/watch?v=HBfb57rQxTg&t=14s) The interviewee expresses happiness about winning his match.
- [00:30](https://www.youtube.com/watch?v=HBfb57rQxTg&t=30s) The match was not easier or harder than expected.
- [01:39](https://www.youtube.com/watch?v=HBfb57rQxTg&t=99s) The interviewee believes Ermes uses all his power in the first round, which leads to him being less effective in later rounds.
- [02:48](https://www.youtube.com/watch?v=HBfb57rQxTg&t=168s) The interviewee believes he has better endurance than Ermes.
- [04:45](https://www.youtube.com/watch?v=HBfb57rQxTg&t=285s) The interviewee identified his weaknesses after the last match and has prepared better for future matches.

### Dave Chaffee vs Ermes Gasparini | East vs West 5

Baseline sample claims:

- [00:16](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=16s) Ermes Gasparini gained hand control after a slip, but it was very near to the pad, indicating an initial struggle for central control.
- [00:26](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=26s) After gaining hand control, Ermes immediately brought Dave Chaffee back to the center with a couple of surges.
- [00:42](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=42s) Dave Chaffee's side pressure was too much, causing Ermes Gasparini's elbow to slide off the pad, resulting in an elbow foul.
- [01:07](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=67s) Ermes Gasparini secured hand control, brought Dave Chaffee back to the center, got behind his shoulder, planted his elbow, and pressed him to the pad for a win.
- [02:49](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=169s) Ermes Gasparini, while losing his own wrist, intentionally 'dumped' it and immediately executed a very fast 'flop press'.

#### gemini-3-flash-preview

Gemini cost: $0.0044

Evaluation: Approximately 75% of baseline claims are covered by candidate claims (6 of 8). High-value claims coverage is also ~75% (3 of 4). There is 1 unsupported candidate claim (01:35) and 1 missed high-value baseline claim (03:39). Overall alignment is good with minor gaps; the candidate passes evaluation.

Candidate sample claims:

- [00:25](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=25s) Ermes gained hand control very near the pad and successfully brought Dave back to the center.
- [01:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=60s) Ermes gets behind his shoulder to press immediately after regaining center.
- [01:35](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=95s) You cannot beat Ermes Gasparini if you have not taken his wrist.
- [02:50](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=170s) Ermes brought Dave back to center with a single surge despite being less than an inch from being pinned.
- [03:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=180s) Ermes has an incredibly fast flop press transition when his wrist is compromised.

#### gemini-2.5-flash-lite

Gemini cost: $0.0116

Evaluation: Candidate claims cover 5 of 8 baseline claims (≈62.5%), including major moments such as early hand control, center re-centering, elbow foul, flop press, and behind-shoulder press. Three candidate claims are not supported by the baseline (01:33, 01:55, 03:07). Three baseline high-value moments (01:07, 03:39, 04:09) are missed. Timestamp alignment across matched claims averages ~22 seconds, indicating moderate temporal misalignment but reasonable coverage overall.

Candidate sample claims:

- [00:17](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=17s) Ermes Gasparini gains hand control early in the first round but it's very close to the pad.
- [00:49](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=49s) Ermes Gasparini brings Dave Chaffee back to the center with just a couple of surges.
- [00:50](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=50s) Ermes Gasparini's elbow slides off the back of the pad, resulting in an elbow foul.
- [01:33](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=93s) Both competitors were going two seconds before the go in the referee's grip, indicating a potential setup issue or eagerness.
- [01:55](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=115s) A pin is awarded to Dave Chaffee, but the call is reversed after review.

