# FPS Cost / Quality Experiment v1

Generated: 2026-04-25 15:12 UTC

Goal: test whether `fps=0.01` preserves audio-first analysis quality while reducing
Gemini video-token cost for the armwrestling narrative-check MVP.

Design:

- Model: `gemini-2.5-flash`
- Sources: one short commentary clip, one long livestream/podcast, one commentary-heavy match recap
- Conditions: `fps=0.1` baseline vs `fps=0.01` reduced visual sampling
- Human review target: compare claim usefulness, timestamp plausibility, and missed tactical detail

## Summary Table

| Source | Type | FPS | Claims | Usefulness | Usage / estimated cost |
| --- | --- | ---: | ---: | --- | --- |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | short commentary clip | 0.1 | 7 | high | `11014` total, `3227` audio, `2893` video, $0.0067 |
| [Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch](https://www.youtube.com/watch?v=U0kDxaszCu8) | short commentary clip | 0.01 | 7 | medium | `8939` total, `3227` audio, `526` video, $0.0061 |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | long livestream/podcast | 0.1 | 8 | low | `272285` total, `145442` audio, `119665` video, $0.1846 |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | long livestream/podcast | 0.01 | 8 | high | `222018` total, `145442` audio, `12098` video, $0.1522 |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | commentary-heavy match recap | 0.1 | 8 | high | `20342` total, `8866` audio, `7364` video, $0.0141 |
| [Dave Chaffee vs Ermes Gasparini | East vs West 5](https://www.youtube.com/watch?v=Fg5g-F7TwA4) | commentary-heavy match recap | 0.01 | 8 | high | `13825` total, `8866` audio, `789` video, $0.0121 |

## Preliminary Read

- If `fps=0.01` returns comparable spoken claims and timestamps, make it the MVP default.
- Use higher FPS only for match-footage segments where visual mechanics matter.
- Prefer podcasts/livestreams/commentary because their value is in audio claims, not frame detail.

## Per-Source Comparison

### Ermes Gasparini predicts the Jerry Cadorette vs Artyom Morozov supermatch

Source: [Victorcali Arm Wrestling](https://www.youtube.com/watch?v=U0kDxaszCu8)

Why selected: Audio-first Morozov tactical commentary from Ermes.

#### FPS 0.1

Summary: Ermes Gasparini analyzes the upcoming match between Jerry Cadorette and Artyom Morozov, challenging the popular belief of a guaranteed Morozov victory by emphasizing Morozov's powerful hook but also Jerry's potential to win by establishing position and utilizing his press.

Popular take: Many fans believe Artyom Morozov will easily defeat Jerry Cadorette, based on past performances against common opponents like Levan.

Counter-case: Ermes Gasparini suggests that direct comparisons are misleading. He believes Jerry Cadorette has a path to victory if he can establish his position first, leveraging his strong press to counter Morozov's powerful hook.

Key question: Can Ermes Gasparini establish his dominant position and counter Artyom Morozov's powerful hook, or will Morozov's speed and hook prevail?

Usefulness: `high`

Usage: `11014` total, `3227` audio, `2893` video, $0.0067

Claims:

- [00:06](https://www.youtube.com/watch?v=U0kDxaszCu8&t=6s) Many consider Artyom Morozov's victory against Jerry Cadorette a 'sure thing'. Confidence: `high`.
- [00:13](https://www.youtube.com/watch?v=U0kDxaszCu8&t=13s) Direct comparisons between athletes based on common opponents can be misleading. Confidence: `high`.
- [00:17](https://www.youtube.com/watch?v=U0kDxaszCu8&t=17s) Artyom Morozov's hook is very powerful. Confidence: `high`.
- [00:21](https://www.youtube.com/watch?v=U0kDxaszCu8&t=21s) If Jerry Cadorette manages to establish his position before Morozov, he can beat him. Confidence: `high`.
- [00:27](https://www.youtube.com/watch?v=U0kDxaszCu8&t=27s) Jerry Cadorette's press is a serious threat if he sets his position, as demonstrated by pressing back Genadi Kvikvinia. Confidence: `high`.

#### FPS 0.01

Summary: Ermes Gasparini analyzes the upcoming match between Jerry Cadorette and Artyom Morozov, noting the popular belief in Morozov's sure victory but cautioning against direct comparisons, while highlighting Morozov's powerful hook and the critical importance of establishing position early.

Popular take: Many fans believe Artyom Morozov will easily win his match against Jerry Cadorette, likely based on past performances against Jerry or Levan Saginashvili.

Counter-case: Ermes Gasparini suggests that direct comparisons between athletes can be misleading. While Morozov's hook is very strong, his success depends on establishing his position quickly. If an opponent like Jerry can establish their position first, they have a chance to win, implying Morozov is not invincible if his setup is disrupted.

Key question: Can Ermes Gasparini establish his position and execute his strategy faster than Artyom Morozov can deploy his powerful hook?

Usefulness: `medium`

Usage: `8939` total, `3227` audio, `526` video, $0.0061

Claims:

- [00:06](https://www.youtube.com/watch?v=U0kDxaszCu8&t=6s) Many people think Morozov will win for sure against Jerry Cadorette, often based on past matches. Confidence: `high`.
- [00:14](https://www.youtube.com/watch?v=U0kDxaszCu8&t=14s) Ermes suggests that direct comparisons between athletes based on common opponents can be misleading. Confidence: `high`.
- [01:05](https://www.youtube.com/watch?v=U0kDxaszCu8&t=65s) Ermes states that athletes are not equally strong in all aspects ('not same power in all the points'). Confidence: `high`.
- [01:11](https://www.youtube.com/watch?v=U0kDxaszCu8&t=71s) Morozov's hook is 'super strong'. Confidence: `high`.
- [01:14](https://www.youtube.com/watch?v=U0kDxaszCu8&t=74s) Morozov's success against Jerry depends on whether he can 'go faster than Jerry to have this position'. Confidence: `high`.

### ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM

Source: [East vs West Armwrestling](https://www.youtube.com/watch?v=nvlNtq3T-Hw)

Why selected: Recent Morozov self-assessment and preparation discussion.

#### FPS 0.1

Summary: The video features an interview with armwrestlers Artyom Morozov and Alizhan, discussing their upcoming left-hand match, general training, and other matches on the EVW 23 card, but does not specifically address an Ermes Gasparini vs Artyom Morozov right-hand match.

Popular take: Fans would likely perceive Artyom Morozov as highly confident and dedicated to his training, with his right arm feeling stronger than ever after surgery, making him a formidable opponent in any upcoming match.

Counter-case: The video does not provide any counter-narrative regarding a specific match against Ermes Gasparini, as that match is not discussed. However, Morozov's philosophy emphasizes hard work over luck, suggesting he relies on preparation rather than overconfidence.

Key question: What is Artyom Morozov's current peak right-hand strength and how does it compare to his past performance?

Usefulness: `low`

Usage: `272285` total, `145442` audio, `119665` video, $0.1846

Claims:

- [02:18](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=138s) Artyom Morozov feels good and trains a lot, with his arm recovering and getting better every day. Confidence: `high`.
- [02:30](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=150s) Artyom Morozov is training very hard, including getting IVs, and is determined to perform his best. Confidence: `high`.
- [05:30](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=330s) Artyom Morozov believes in working hard for success rather than relying on luck, stating that luck is only needed to avoid injury during training. Confidence: `high`.
- [06:20](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=380s) Artyom Morozov's confidence grows with each training session, and he is confident it will be a good match. Confidence: `high`.
- [12:00](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=720s) After surgery, Artyom Morozov's right wrist rising doesn't drop, and he feels stronger right-handed than ever before, weighing 140kg. Confidence: `high`.

#### FPS 0.01

Summary: Artyom Morozov and Alizhan discuss their current physical condition, training intensity, and confidence for their upcoming match, while also sharing their philosophies on hard work versus luck in armwrestling.

Popular take: Fans would believe that both Morozov and Alizhan are highly confident and dedicated to their training, with Morozov specifically feeling strong and ready after his recovery and intense preparation.

Counter-case: Despite the confidence, both athletes emphasize that hard work and actions are more important than boasting or relying on luck, suggesting a grounded and realistic approach to their competitive careers.

Key question: Can Artyom Morozov's improved right arm endurance and disciplined training overcome Ermes Gasparini's power and technique?

Usefulness: `high`

Usage: `222018` total, `145442` audio, `12098` video, $0.1522

Claims:

- [02:18](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=138s) Artyom Morozov states he feels good, trains a lot, and his arm is getting better every day, recovering well, including getting IVs. Confidence: `high`.
- [03:45](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=225s) Alizhan mentions that with the match finally confirmed, he has found consistency in his training and expects to be in good shape by April. Confidence: `high`.
- [08:09](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=489s) Alizhan expresses a philosophy that a person shouldn't be overly confident but should work hard and persevere, as success comes from effort, not luck. Confidence: `high`.
- [11:04](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=664s) Artyom Morozov reiterates feeling good and gaining confidence with each training session, stating he is confident it will be a good match. Confidence: `high`.
- [13:18](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=798s) Artyom Morozov and Alizhan confirm they pulled each other once in a tournament in Latoshino in 2020, with Alizhan noting he had a 'crazy start' back then. Confidence: `high`.

### Dave Chaffee vs Ermes Gasparini | East vs West 5

Source: [ARMWRESTLING NEWZ](https://www.youtube.com/watch?v=Fg5g-F7TwA4)

Why selected: Right-hand Ermes evidence with tactical commentary.

#### FPS 0.1

Summary: Ermes Gasparini defeated Dave Chaffee at East vs West 5, demonstrating exceptional hand control, powerful recovery surges, and an effective flop press, solidifying his status as a top armwrestler.

Popular take: Ermes Gasparini is now a confirmed elite armwrestler, capable of beating top-tier opponents by adapting his strategy and maintaining intense pressure, making him a formidable contender for future supermatches.

Counter-case: Despite his victory, Ermes Gasparini was repeatedly pushed very close to the pin pad by Dave Chaffee, suggesting that while his recovery and finishing power are exceptional, he might still be vulnerable to initial powerful surges from strong opponents.

Key question: Can Ermes Gasparini's powerful surges and deceptive flop press overcome Artyom Morozov's initial hit and sustained side pressure, or will Morozov's strength exploit Ermes's moments of vulnerability when taken deep?

Usefulness: `high`

Usage: `20342` total, `8866` audio, `7364` video, $0.0141

Claims:

- [00:16](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=16s) Ermes Gasparini demonstrated strong wrist and hand strength by gaining hand control even when Dave Chaffee had pushed him very near to the pad. Confidence: `high`.
- [00:26](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=26s) After gaining hand control, Ermes immediately brought Dave Chaffee back to the center with 'a couple of surges,' showcasing powerful recovery ability. Confidence: `high`.
- [00:42](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=42s) Dave Chaffee's side pressure was 'way too much' for Ermes in one instance, causing Ermes's elbow to slide off the pad for an elbow foul. Confidence: `high`.
- [01:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=60s) The commentator states, 'You cannot beat Ermes Gasparini if you have not taken his wrist,' emphasizing the critical importance of wrist control against him. Confidence: `high`.
- [02:49](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=169s) Ermes intentionally 'dumped' his wrist and executed a 'flop press' with surprising speed, flash pinning Dave Chaffee. Confidence: `high`.

#### FPS 0.01

Summary: The video analyzes Ermes Gasperini's intense victory over Dave Chaffee, highlighting his strategic use of the flop press, resilience in regaining control, and the critical importance of wrist control in his matches, all driven by high stakes.

Popular take: Ermes Gasperini is a top-tier armwrestler, possibly number two in the world, whose powerful flop press and ability to recover from difficult positions make him extremely hard to beat, especially if his wrist is not fully taken.

Counter-case: Despite his strength, Ermes showed vulnerability to strong side pressure leading to elbow fouls and sometimes struggled with initial hand control, suggesting opponents with strong top rolls or side pressure could find openings. His intentional wrist sacrifice, while effective, also indicates a potential weakness that could be exploited if the flop press doesn't land.

Key question: Can Artyom Morozov's top roll and side pressure prevent Ermes from establishing his hand control or effectively executing his powerful flop press, or will Ermes's resilience and strategic wrist sacrifice overcome Morozov's initial attack?

Usefulness: `high`

Usage: `13825` total, `8866` audio, `789` video, $0.0121

Claims:

- [00:27](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=27s) Ermes gained hand control and immediately brought Dave back to the center with a couple of surges, demonstrating strong recovery. Confidence: `high`.
- [00:42](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=42s) Dave's side pressure was way too much, causing Ermes's elbow to slide off for a foul. Confidence: `high`.
- [01:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=60s) The commentator states, 'You cannot beat Ermes Gasperini if you have not taken his wrist.' Confidence: `high`.
- [02:36](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=156s) Ermes was observed to be 'slightly pronated' but did not have his wrist cupped. Confidence: `medium`.
- [02:49](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=169s) Ermes was losing his own wrist and 'dumped it' to immediately execute a 'flop press.' Confidence: `high`.

