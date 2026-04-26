# Locator Cost / Quality Experiment v1

Generated: 2026-04-25 15:34 UTC

Goal: separate signal audio tokens from noise audio tokens by locating relevant windows
before final extraction.

Design:

- Baseline: full-video `gemini-2.5-flash` extraction at `fps=0.01`
- Locator: full-video `gemini-2.5-flash-lite` pass returning up to `4` windows
- Final extraction: `gemini-2.5-flash` only on located windows
- Human review target: compare recovered claim quality against full-video baseline

Important caveat: this still pays for one full-video locator pass. The experiment tests
whether a cheap locator plus window extraction is cheaper and good enough versus full final
extraction. True 10x savings likely require metadata/chapters/manual timestamps before any
full-video audio pass.

## Summary Table

| Source | Baseline claims | Baseline cost | Windows | Window claims | Locator+window cost | Cost delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [Ermes Gasparini - East vs West Podcast](https://www.youtube.com/watch?v=NsLWax9GwZY) | 0 | $0.2083 | 4 | 0 | $0.1700 | $-0.0383 |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=nvlNtq3T-Hw) | 0 | $0.1840 | 4 | 0 | $0.1502 | $-0.0338 |
| [ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM](https://www.youtube.com/watch?v=bZUOAv0Kzxs) | 0 | $0.1766 | 4 | 0 | $0.1439 | $-0.0327 |

## Per-Source Detail

### Ermes Gasparini - East vs West Podcast

Source: [Engin Terzi Enigma of Rage](https://www.youtube.com/watch?v=NsLWax9GwZY)

Type: long Ermes podcast

Baseline usage: `307964` tokens, $0.2083

Locator usage: `179049` tokens, $0.1700

Locator+window usage: `179049` tokens, $0.1700

Baseline sample claims:

- [02:42](https://www.youtube.com/watch?v=NsLWax9GwZY&t=162s) Jerry Cadorette is perceived as 'too powerful' by some fans.
- [11:35](https://www.youtube.com/watch?v=NsLWax9GwZY&t=695s) Ermes Gasparini's current weight is around 127-128 kg.
- [12:06](https://www.youtube.com/watch?v=NsLWax9GwZY&t=726s) Ermes Gasparini's current shape is at 80-85% of his best performance (against Bortolato with left arm).
- [13:07](https://www.youtube.com/watch?v=NsLWax9GwZY&t=787s) Ermes Gasparini believes his current 80-85% shape is 'enough' to beat Jerry Cadorette easily, even if they competed tomorrow.

Located windows:

- Window 1: `00:58-01:38`, relevance `0.7`. Reason: The speaker introduces himself and mentions his location, setting the context for the conversation. The mention of 'live from China' is interesting but not directly relevant to the MVP criteria.
- Window 2: `01:38-02:27`, relevance `0.8`. Reason: This section contains multiple claims about opponent comparison (Artyom vs. Jerry), tactical style (hook, toproll), and confidence (Jerry is too powerful). It also touches on the location of the event (Turkey).
- Window 3: `03:28-04:18`, relevance `0.7`. Reason: The speaker discusses the possibility of a match between Levan and Ivan, mentioning the need for an agreement and the difficulty of such a match. This touches on opponent comparison and tactical considerations.
- Window 4: `04:18-05:15`, relevance `0.8`. Reason: The speaker discusses the rules and regulations of organizing matches, specifically mentioning the need for permission from national federations and the involvement of federations like WAF. This provides context on the sport's structure and potential challenges.

Window extraction sample claims:

Window 1 `00:58-01:38`:
- No claims returned.
Window 2 `01:38-02:27`:
- No claims returned.
Window 3 `03:28-04:18`:
- No claims returned.
Window 4 `04:18-05:15`:
- No claims returned.

### ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM

Source: [East vs West Armwrestling](https://www.youtube.com/watch?v=nvlNtq3T-Hw)

Type: recent Morozov livestream

Baseline usage: `284206` tokens, $0.1840

Locator usage: `158254` tokens, $0.1502

Locator+window usage: `158254` tokens, $0.1502

Baseline sample claims:

- [02:22](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=142s) Morozov's arm feels better every day, recovering well, and he feels really good.
- [02:31](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=151s) Morozov trains a lot and uses IVs for recovery, indicating intense preparation.
- [11:14](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=674s) Morozov is confident that it will be a good fight.
- [12:15](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=735s) Morozov prefers to focus on hard work and showing results rather than boasting about winning, reflecting a humble and action-oriented approach.

Located windows:

- Window 1: `01:49-02:00`, relevance `0.8`. Reason: Morozov discusses his training and recovery, mentioning feeling good and improving daily, indicating confidence in his form.
- Window 2: `03:16-04:15`, relevance `0.9`. Reason: Alijan discusses his confidence, the confirmation of the match, and his training mindset, expressing belief in his ability to perform well.
- Window 3: `08:03-09:14`, relevance `0.9`. Reason: Morozov expresses confidence based on hard work and training, downplaying the need for luck and emphasizing results over claims.
- Window 4: `13:04-14:27`, relevance `0.8`. Reason: Discussion about past matches between the athletes, specifically mentioning a previous match in 2020 and the context of their previous encounters.

Window extraction sample claims:

Window 1 `01:49-02:00`:
- No claims returned.
Window 2 `03:16-04:15`:
- No claims returned.
Window 3 `08:03-09:14`:
- No claims returned.
Window 4 `13:04-14:27`:
- No claims returned.

### ARTYOM MOROZOV & ALIZHAN MURATOV | EVW 23 LIVESTREAM

Source: [East vs West Armwrestling](https://www.youtube.com/watch?v=bZUOAv0Kzxs)

Type: very recent Morozov livestream

Baseline usage: `263072` tokens, $0.1766

Locator usage: `151515` tokens, $0.1439

Locator+window usage: `151515` tokens, $0.1439

Baseline sample claims:

- [03:03](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=183s) Artem Morozov's current weight is 138kg (~305 lbs).
- [15:04](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=904s) Morozov's self-assessment of his past match against Vitaly Laletin was that it was primarily a 'strength issue' and Vitaly is 'just power.' He believes if he were stronger, he would have had fewer injuries and pulled more efficiently.
- [16:11](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=971s) Morozov cannot definitively say if he is stronger now than when he pulled Vitaly Laletin, as Vitaly was not in peak shape then.
- [70:15](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=4215s) Morozov had a training plan from the beginning and stuck to it. He trains consistently but now goes by feeling, not a strict plan. He tried training twice a day but it's not for him.

Located windows:

- Window 1: `00:11-01:02`, relevance `0.8`. Reason: The speaker discusses the upcoming match, introduces the participants, and mentions the 'left-handed title' and the fact that they are from the same town. This sets the stage for opponent comparison and tactical claims.
- Window 2: `01:11-02:04`, relevance `0.9`. Reason: The speaker talks about their area of expertise, which is ensuring understanding between participants, and mentions their kids' opinions on the participants' skills. This touches on confidence and opponent comparison.
- Window 3: `02:04-03:19`, relevance `0.95`. Reason: The speaker discusses the weight of the participants, specifically mentioning '305' and '300' pounds, and asks about the current weight and expected weight in 10 days. This is direct evidence for form claims.
- Window 4: `03:27-04:12`, relevance `0.9`. Reason: The speaker highlights the presence of former champions and a current champion in the podcast, specifically mentioning the 'heavyweight left-handed champion of the world'. This is a strong opponent comparison claim.

Window extraction sample claims:

Window 1 `00:11-01:02`:
- No claims returned.
Window 2 `01:11-02:04`:
- No claims returned.
Window 3 `02:04-03:19`:
- No claims returned.
Window 4 `03:27-04:12`:
- No claims returned.

