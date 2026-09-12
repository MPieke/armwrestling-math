# East vs West match data (self-collected)

## What this file is

A dump of a private dataset covering four East vs West armwrestling events.
It has two parts:

1. **Match results** - final outcomes, collected from published event results.
2. **Commentary claims** - statements made by broadcast commentators during
   match videos, transcribed and then extracted into individual claims by a
   language model. Each claim may carry labels (also assigned by a language
   model) for claim type, time-reference, certainty, concept tags, and which
   athlete it is about.

## Coverage and provenance

- Events covered: 4 (East vs West 22, 23, 24 and 25).
- Date range: 2026-02-28 to 2026-08-01.
- Matches with recorded results: 57.
- Distinct athletes appearing: 90.
- Commentary claims: 323, covering 38 of the 57 matches.
  The remaining 19 matches have results but no commentary claims.
- Of those claims, 229 carry the model-assigned labels; the rest are unlabelled claim text only.

Characteristics of this data that bear on how much weight it should carry:

- Claims are commentator speech, not measurement. Commentators speculate,
  repeat received opinion, talk to fill time, and are sometimes wrong.
- Claim extraction and labelling were both done by a language model and have
  not been human-verified, so both the wording and the labels may contain errors.
- Concept tags come from a fixed vocabulary chosen by the dataset author. The
  vocabulary is not necessarily complete or well-chosen, and its categories
  should not be treated as the definitive set of factors that decide matches.
- Coverage is one promotion over roughly six months. It is not a sample of
  armwrestling generally.
- Timestamps are seconds into the source video, where recorded.

## Notation

Results are written `Winner (score) def. Loser (score)`. Scores are rounds won.
`arm` is which hand the match was contested on.

---

# Part 1: Match results


## East vs West 22 (2026-02-28)

- [match 1] left arm, Over 115 kg - **Eldar Bubenko** (3) def. Logan Bittinger (0)
- [match 2] left arm, Up to 60 kg - **Esra Kiraz** (3) def. Carolina Pettersson (1)
- [match 3] left arm, Up to 85 kg - **Luka Tsinadze** (3) def. Iliya Saidov (0)
- [match 4] right arm, Up to 105 kg - **Peter Čeleš** (3) def. Curtis Cameron (0)
- [match 5] right arm, Up to 105 kg - **Nugzari Chikadze** (3) def. Bogdan Stoica (2)
- [match 6] right arm, Up to 85 kg - **Oleksandr Telyatnik** (3) def. Vladislavs Krasovskis (0)
- [match 7] right arm, Over 115 kg - **Efe Komek** (3) def. Tarkhan Muzaffarov (0)
- [match 8] right arm, Up to 115 kg - **Matt Mask** (3) def. Davit Arabuli (0)
- [match 9] right arm, Up to 70 kg - **Fia Reisek** (4) def. Brigitta Ivanfi (0)
- [match 10] right arm, Up to 115 kg - **Yordan Tsonev** (3) def. Serhii Kalinichenko (0)
- [match 11] right arm, Over 115 kg - **Kamil Jablonski** (3) def. Michael Todd (0)
- [match 12] right arm, Up to 105 kg - **Oleg Petrenko** (4) def. Todd Hutchings (0)
- [match 13] left arm, Over 115 kg - **Vitalii Laletin** (4) def. Devon Larratt (0)

## East vs West 23 (2026-04-18)

- [match 14] right arm, Over 115 kg - **Duvan Bornman** (3) def. André Nykonenko (1)
- [match 15] right arm, Up to 77 kg - **Aleksi Zavrashvili** (3) def. Artem Oriabinskyi (0)
- [match 16] left arm, Up to 95 kg - **Zurab Tavberidze** (3) def. Maayan Shterengas (2)
- [match 17] right arm, Over 115 kg - **Riekerd Bornman** (3) def. Lars Rørbakken (0)
- [match 18] left arm, Over 80 kg - **Egle Vaitkute** (3) def. Azra Sari (0)
- [match 19] left arm, Up to 95 kg - **Betkili Oniani** (3) def. Rustam Babaiev (0)
- [match 20] left arm, Up to 105 kg - **Aymeric Pradines** (3) def. Matt Mask (0)
- [match 21] right arm, Up to 60 kg - **Ayane Takenaka** (4) def. Melek Sahin (0)
- [match 22] left arm, Over 115 kg - **Alizhan Muratov** (3) def. Artyom Morozov (0)
- [match 23] right arm, Up to 77 kg - **Artur Makarov** (4) def. Mindaugas Tarasaitis (0)
- [match 24] right arm, Up to 85 kg - **Oleksandr Telyatnik** (4) def. Davit Samushia (0)
- [match 25] right arm, Up to 115 kg - **Ivan Matyushenko** (4) def. Dave Chaffee (1)
- [match 26] right arm, Over 115 kg - **Leonidas Arkona** (3) def. Brian Shaw (2)
- [match 27] right arm, Over 115 kg - **Devon Larratt** (4) def. Vitalii Laletin (1)

## East vs West 24 (2026-06-06)

- [match 28] right arm, Up to 85 kg - **Bob Brown** (3) def. Isaiah Jones (0)
- [match 29] right arm, Up to 77 kg - **Courtney Huycke** (3) def. Nastasia Pastorkova (1)
- [match 30] right arm, Up to 95 kg - **Ryan Belanger** (3) def. Jason Merlo (0)
- [match 31] right arm, Up to 115 kg - **Jeremy Parker** (3) def. Auden Larratt (1)
- [match 32] right arm, Up to 105 kg - **Irakli Zirakashvili** (3) def. Yoshinobu Kanai (0)
- [match 33] right arm, Up to 95 kg - **Adam Wawrzynski** (3) def. Peter Čeleš (1)
- [match 34] right arm, Up to 77 kg - **Tom Holland** (3) def. Justin Bishop (1)
- [match 35] right arm, Up to 85 kg - **Janis Amolins** (3) def. Craig Tullier (0)
- [match 36] left arm, Open category - **Corey West** (3) def. Pavlo Derbedyenyev (0)
- [match 37] left arm, Open category - **Jerry Cadorette** (3) def. Kody Merritt (1)
- [match 38] left arm, Open category - **Tobias Sporrong** (3) def. Alex Kurdecha (0)
- [match 39] right arm, Open category - **Riekerd Bornman** (3) def. Alizhan Muratov (0)
- [match 40] right arm, Up to 95 kg - **Bogdan Stoica** (4) def. Todd Hutchings (1)
- [match 41] right arm, Open category - **Artyom Morozov** (4) def. Ermes Gasparini (1)
- [match 42] right arm, Up to 105 kg - **Michael Todd** (4) def. Oleg Petrenko (0)

## East vs West 25 (2026-08-01)

- [match 43] right arm, Up to 85 kg - **Vladislavs Krasovskis** (3) def. Artem Popov (0)
- [match 44] right arm, Up to 85 kg - **Tim Tallmadge** (3) def. Vala Ichkiti (0)
- [match 45] right arm, Up to 95 kg - **Zurab Tavberidze** (3) def. Ryan Belanger (0)
- [match 46] right arm, Open category - **Gabriela Vasconcelos** (3) def. Irina Driaeva (0)
- [match 47] right arm, Up to 95 kg - **Adam Wawrzynski** (3) def. Nurdaulet Aidarkhan (2)
- [match 48] right arm, Up to 95 kg - **Eldar Bubenko** (3) def. Paul Linn (0)
- [match 49] left arm, Up to 77 kg - **Daniel Procopciuc** (4) def. Vachagan Hovhannisyan (0)
- [match 50] right arm, Up to 105 kg - **Krasimir Kostadinov** (3) def. Nugzari Chikadze (0)
- [match 51] right arm, Up to 115 kg - **Ibragim Sagov** (3) def. Yordan Tsonev (0)
- [match 52] left arm, Up to 85 kg - **Oleh Zhokh** (4) def. Luka Tsinadze (0)
- [match 53] right arm, Over 115 kg - **Kamil Jablonski** (4) def. Georgi Tsvetkov (2)
- [match 54] left arm, Over 115 kg - **Vitalii Laletin** (4) def. Alizhan Muratov (0)
- [match 55] right arm, Up to 77 kg - **Aleksandre Koshadze** (2) def. Zhuo Xiaohai (0)
- [match 56] right arm, Over 115 kg - **Daniyar Roman** (2) def. Grigorii Liashchuk (1)
- [match 57] left arm, Up to 95 kg - **Oleksandr Telyatnik** (2) def. Omer Dror (0)

---

# Part 2: Commentary claims, by match

Each claim is followed by its labels where present:
`type` / `time-reference` / `certainty` / `about: athlete` / `concepts`.


## [match 1] Eldar Bubenko def. Logan Bittinger - East vs West 22, left arm, Over 115 kg

- [0:10] This is a cross-category left arm match between Eldar Bubenko (105kg) and Logan Bittinger (115kg), both having won their respective classes in the EVW Challenge tournament earlier today.
  - *other / historical_event / observed / matchup_specific_history*
- [0:27] Logan Bittinger is the heavier athlete at 115 kilos and a super heavyweight winner, while Eldar Bubenko is a 105 kilo class winner; the question posed is whether size matters.
  - *opponent_comparison / general_principle / community_narrative / arm_length, frame_and_leverage*
- [1:15] The match likely will go to the straps due to wrist positioning; Eldar stayed on top utilizing a top roll against Logan’s attempt, gaining wrist control.
  - *tactic / future_prediction / analyst_interpretation / about: Eldar Bubenko / wrist_control, top_roll*
- [1:42] Logan has the advantage of being on the 'good side' of the strap on the first round, which is believed to provide leverage.
  - *setup / current_form / community_narrative / about: Logan Bittinger / frame_and_leverage*
- [2:23] Logan froze after the start and did not initiate, was lower with his palm turned upwards, which is a weak position resulting in Eldar beating him in hand control and pulling back.
  - *form / historical_event / observed / about: Logan Bittinger / wrist_control, hand_size, supination*
- [3:12] Matches have shortened in duration from 2 minutes to 60 seconds, making endurance more important as keeping grip over time is challenging.
  - *endurance / recent_context / analyst_interpretation / reserve_strength, grip_strength*
- [4:00] In round two, Logan improved his hand control but received warnings and a foul for closing his hand and moving his elbow, which impacted his position negatively.
  - *tactic / historical_event / observed / about: Logan Bittinger / hand_size, elbow_discipline*
- [4:57] Logan went straight to the strap in round three due to previous slips; Eldar controlled the match with backward movement and wrist flexion making it hard for Logan to hook outside the strap.
  - *tactic / recent_context / observed / about: Eldar Bubenko / back_pressure, wrist_control, hook, start_position*
- [5:33] Eldar was in full control and dictating the match by effectively using wrist flexion, while Logan needs to adjust by rocking back to prevent flattening his wrist.
  - *tactic / current_form / analyst_interpretation / about: Eldar Bubenko / wrist_control, wrist_control*

## [match 2] Esra Kiraz def. Carolina Pettersson - East vs West 22, left arm, Up to 60 kg

- [2:00] Carolina Pedersen is known for her signature top roll on the left arm, aiming to keep her hand outside and stretch her opponent out.
- [2:10] Esra Kiraz is a strong hooker who benefits from going on the hook, reducing stress on her hand and increasing pulling effectiveness.
- [3:00] Kiraz received warnings for fouls, mostly related to elbows coming off the pad, which are a critical part of maintaining position and safety in left arm matches.
- [7:10] If Carolina can keep her wrist higher and maintain back pressure, she can better control Kiraz's wrist and defend her position.
- [7:20] Carolina Pettersson is taking damage from Kiraz's powerful pulls, indicating the match involves significant physical strain on her left arm.
- [11:50] Esra Kiraz's stronger power and ability to calm down emotionally helped her take control of the match eventually.

## [match 3] Luka Tsinadze def. Iliya Saidov - East vs West 22, left arm, Up to 85 kg

- [0:40] Luca Tsinadze is a reigning WAF world senior champion, very solid and experienced, while Iliya Saidov has only done open tournaments and no super matches.
- [1:28] Luka Tsinadze's signature style is inside arm wrestling with a very strong hook; he can also top roll or switch techniques if needed.
- [1:50] Luka tries to engage with an inside hook for leverage, seeking his favorite position despite Iliya Saidov's resistance.
- [2:10] Luka's speed and power create a 'wall' for Iliya; his strength and top-end power are at elite senior level despite young age.
- [2:20] After hitting the wall and failing to break Luka's defense, Iliya tries changing his line and attempts top rolling in the strap phase to find a winning chance.
- [3:40] Luka Tsinadze displays a calm and confident demeanor, maintaining dominant position and control throughout.
- [4:10] Iliya Saidov's biceps showed signs of giving up; he lost connection during the match which may indicate fatigue or endurance issues.
- [4:35] Luka Tsinadze maintains very solid angles, good side and back pressure, connection, and arm wrestling fundamentals.
- [5:00] Despite multiple rounds and pressure, Luka remains fresh, solid, and confident with significant endurance advantage over Iliya.

## [match 4] Peter Čeleš def. Curtis Cameron - East vs West 22, right arm, Up to 105 kg

- [0:00] Curtis Cameron will face Peter Čeleš in a right-hand supermatch in the light heavyweight division, 105 kilos.
- [1:04] Curtis Cameron is a bulldog style hooker, aiming to keep the match wrist to wrist, while Peter Čeleš is a top roller who prefers to keep it outside and make it a hand game.
  - *opponent_comparison / durable_style / community_narrative / hook, top_roll, wrist_control, hand_size, matchup_specific_history*
- [1:10] Curtis Cameron can keep his knuckle high to maintain wrist control against the taller Peter Čeleš who has to come inside to reach his hand.
  - *tactic / general_principle / analyst_interpretation / about: Curtis Cameron / wrist_control, arm_length, frame_and_leverage, start_position*
- [1:12] This match will likely go to strap since it's dangerous to hang on and risk fatigue or hand exhaustion, indicating strategical considerations if their hands slip or hold low on the wrist.
  - *tactic / future_prediction / analyst_interpretation / grip_strength, reserve_strength*
- [1:14] Hanging on or fighting wrist fatigue can cause hand damage, which is critical in supermatches taking multiple rounds.
  - *injury / general_principle / analyst_interpretation / hand_size, wrist_control, injury_or_recovery_status, reserve_strength*
- [1:18] Curtis Cameron prefers staying at the front and coming to the center of the table aiming to gain positional advantage.
  - *tactic / durable_style / analyst_interpretation / about: Curtis Cameron / start_position, frame_and_leverage*
- [1:20] Curtis Cameron tries to grab low on the wrist to control the inside position, which is risky but can be effective if the opponent keeps the knuckle high, but Peter Čeleš tends to use a low hand grip to keep distance.
  - *tactic / general_principle / analyst_interpretation / wrist_control, start_position, hand_size*
- [1:51] Peter Čeleš has had problems historically against good inside pullers like Curtis Cameron, even when having hand and wrist advantage, Curtis can overpower with side pressure and power.
  - *opponent_comparison / historical_event / community_narrative / side_pressure, wrist_control, grip_strength, matchup_specific_history*
- [2:00] Peter Čeleš must transition to a good press to finish the match quickly or risk burning out, and Curtis needs to have a press in his arsenal to be complete.
  - *tactic / current_form / analyst_interpretation / press, reserve_strength*
- [2:17] Curtis Cameron hesitated in round one and should have committed earlier, focusing more on pronation and keeping his hand perpendicular to the table to avoid losing the hand advantage.
  - *tactic / historical_event / analyst_interpretation / about: Curtis Cameron / supination, wrist_control*
- [2:35] Curtis Cameron needs to slip and commit fully or grab a lower wrist grip to control the match and take the hand out of the equation.
  - *tactic / current_form / analyst_interpretation / about: Curtis Cameron / wrist_control, grip_strength*
- [2:41] Curtis Cameron has Jody Laris and Devin in his corner, who are experienced and advise him to use energy wisely in this big match.
  - *tactic / recent_context / community_narrative / about: Curtis Cameron / mental_focus, reserve_strength*
- [2:58] Curtis Cameron must commit fully and try to hook or go forward aggressively as relying on back pressure or pronation is not enough against Peter Čeleš's cross-table control.
  - *tactic / recent_context / analyst_interpretation / about: Curtis Cameron / hook, back_pressure, press, arm_length, matchup_specific_history*
- [3:07] Peter Čeleš's top rolling skill and control is dominating, with Curtis Cameron unable to establish effective pronation and struggling to shift the position or hook effectively in later rounds.
  - *tactic / recent_context / analyst_interpretation / about: Peter Čeleš / top_roll, wrist_control, supination, hook*
- [3:24] Peter Čeleš won the prelims match decisively due to dominant top roll, smart tactics and early control preventing Curtis Cameron from utilizing his hook or pronation.
  - *tactic / historical_event / observed / about: Peter Čeleš / top_roll, hook, supination*
- [15:13] Curtis Cameron has rehabbed from his injury with Sureb and is now way more healthy and stronger, feeling the best he's ever been.
- [15:16] Curtis Cameron is an inside puller who relies on strong side pressure and arm strength.
- [15:19] Peter Čeleš is a strong top roller with a good wrist-cracking ability and a strong hand, but his side pressure and arm power may be weaker compared to Curtis Cameron's inside side pressure style.
- [15:20] Peter Čeleš uses top roll with strong wrist cracking techniques but lacks sufficient side pressure to finish effectively against strong inside pullers.
- [15:24] Prediction that Peter Čeleš will crack Curtis Cameron's wrist and win the match 3-1 or 4-1, estimating a 70-30 probability for Čeleš.

## [match 5] Nugzari Chikadze def. Bogdan Stoica - East vs West 22, right arm, Up to 105 kg

- [23:20] Богдан Стойка показал хорошую борьбу ранее, но против Нуго Чикадзе у него практически 0 шансов пройти вверх, так как у Чикадзе очень сильная кисть и он превосходит в крюках.
- [23:55] Нуго Чикадзе борется с очень железной кистью и предпочитает стиль, затрудняющий оппоненту проход в крюк, что усложняет Богдану Стойке пробиться его укороченной рукой.
- [24:10] Богдан Стойка пытается войти в крюк, так как это его сильная позиция, но против сильной кисти Чикадзе это малоэффективно; у Богдана максимум 20% шансов на успех.
- [24:25] Нугзари Чикадзе очень хорошо борется с большим соперником в крюке, имеет преимущество и выдержку даже против сильных противников в этом стиле.
- [25:20] По коэффициентам шансы на победу Чикадзе оценивают значительно выше, примерно 75% против 35% у Стоика, что соответствует моим ожиданиям.

## [match 6] Oleksandr Telyatnik def. Vladislavs Krasovskis - East vs West 22, right arm, Up to 85 kg

- [0:48] The match is in the 85-kilogram men's weight division on the right arm involving athletes from Ukraine and Latvia.
- [1:00] Oleksandr Telyatnik is introduced as an incredible new talent representing Ukraine.
- [1:15] Vladislavs Krasovskis is introduced as a multi-time Latvian national champion, multi-time European champion of EAF, and multi-time world champion of UAF.
  - *other / historical_event / community_narrative / about: Vladislavs Krasovskis / matchup_specific_history*

## [match 7] Efe Komek def. Tarkhan Muzaffarov - East vs West 22, right arm, Over 115 kg

- [1:04] Tarkhan prefers inside armwrestling, wants to control with his arm and hand.
  - *tactic / durable_style / community_narrative / about: Tarkhan Muzaffarov / grip_strength, wrist_control*
- [1:05] Efe is known for a great top roll style.
  - *form / durable_style / community_narrative / about: Efe Komek / top_roll*
- [1:43] Tarkhan is better with the straps and would likely prefer to go to the strap phase in the match.
  - *opponent_comparison / future_prediction / analyst_interpretation / about: Tarkhan Muzaffarov / grip_strength, reserve_strength*
- [1:48] Efe shows super power and a strong top roll that made Tarkhan unable to get a slip or a good bite without straps.
  - *form / current_form / observed / about: Efe Komek / top_roll, grip_strength*
- [2:04] Tarkhan possibly suffered an injury involving chest, shoulder, or bicep area but continued the match despite possible muscle strain.
  - *injury / recent_context / community_narrative / about: Tarkhan Muzaffarov / injury_or_recovery_status*
- [2:14] Tarkhan attempts a different setup going for a top roll but still needs to go into the straps to have a chance.
  - *setup / recent_context / analyst_interpretation / about: Tarkhan Muzaffarov / top_roll, matchup_specific_history*
- [2:19] Both competitors received double warnings during the match for hand closing and other fouls.
  - *other / historical_event / observed / injury_or_recovery_status*
- [2:24] Tarkhan appeared to have pain that might prevent him from moving effectively, limiting his ability to get a slip or perform moves.
  - *injury / current_form / observed / about: Tarkhan Muzaffarov / injury_or_recovery_status*
- [2:29] Referee was strict about grip and hand control, which may have affected the dynamics of the match.
  - *other / current_form / analyst_interpretation / grip_strength, wrist_control*
- [2:40] Suggestion that Tarkhan should try to go on the press or use King's move and needs a slip or strap first to enable those moves.
  - *tactic / future_prediction / analyst_interpretation / about: Tarkhan Muzaffarov / press, hook*
- [2:44] Efe's fingers, grip, and cup are extremely strong, making him dominant in hand control over Tarkhan.
  - *form / current_form / analyst_interpretation / about: Efe Komek / grip_strength, wrist_control*
- [3:31] In the final round with the strap, Efe maintained a good purchase on Tarkhan's hand and won by pinning Tarkhan with superior wrist and hand strength.
  - *other / historical_event / observed / about: Efe Komek / wrist_control, grip_strength*
- [3:46] Efe was completely dominant with wrist and hand throughout the match, winning both without and with straps.
  - *form / historical_event / observed / about: Efe Komek / wrist_control, grip_strength, hand_size*

## [match 8] Matt Mask def. Davit Arabuli - East vs West 22, right arm, Up to 115 kg

- [0:06] That looked like another stocking pin this time on the inside of the right arm.
- [0:13] The load arm looks pretty strong.
- [2:03] Matt Mask's top rolling ability is one of the best on the planet and he always goes for a top roll.
  - *form / general_principle / community_narrative / about: Matt Mask / top_roll*
- [2:08] Davit Arabuli is preparing a top roll and tries to counter Matt Mask's top roll with a slip and stirrups setup.
  - *tactic / current_form / self_reported / about: Davit Arabuli / top_roll, start_position*
- [2:45] Matt Mask pulls his shoulders forward, keeps elbow in tight close angle, attacks with pronator and side pressure rather than wrist or hand attack.
  - *tactic / current_form / observed / about: Matt Mask / side_pressure, shoulder_engagement, elbow_discipline*
- [2:58] Both fighters committed fouls during setup, indicating high intensity and aggressiveness in the match.
  - *setup / historical_event / observed / matchup_specific_history*
- [3:01] Davit Arabuli switches to a lower grip aiming for press or hook against Matt Mask.
  - *tactic / current_form / observed / about: Davit Arabuli / press, hook, grip_strength*
- [3:30] Matt Mask won the match 3-0 comfortably against Davit Arabuli, demonstrating strong endurance and dominance.
  - *endurance / historical_event / observed / about: Matt Mask / reserve_strength*
- [3:50] Matt Mask is known for his explosive, entertaining arm-wrestling style and high energy on the table, which contrasts with his calm off-table personality.
  - *form / durable_style / community_narrative / about: Matt Mask / explosive_strength, mental_focus*

## [match 9] Fia Reisek def. Brigitta Ivanfi - East vs West 22, right arm, Up to 70 kg

- [0:14] Her weakness is side pressure
- [3:33] Fia is putting a tremendous amount of side pressure
- [3:34] She's trying to just go through your arm, she's trying to hold instead of going over you
- [3:40] Brigitta is the first person from Hungary to fight for the world title on East versus West stage
- [3:53] Most of the time Fia has got the best of Brigitta in European and World championships
- [4:42] Fia is a more dominant champion on EVW stage especially in her weight class
- [12:31] Fia has iron hand and wrist, very strong side pressure
- [12:32] Fia was in some bad spots in one match but powered through it
- [12:34] It is gonna take an effort to dethrone her

## [match 10] Yordan Tsonev def. Serhii Kalinichenko - East vs West 22, right arm, Up to 115 kg

- [0:20] I will try to win you with three techniques.
  - *tactic / future_prediction / self_reported / top_roll, hook, press*
- [0:26] Sergei, I know that you are coming like a train with your tricep just to crash me. You said flop press. Oh no, no, nobody beat me in flop press.
  - *tactic / future_prediction / self_reported / about: Serhii Kalinichenko / press*
- [1:02] Of course, the bigger biceps goes to Sergei Kalinichenko, as well as almost 10 centimeter bigger forearm.
  - *opponent_comparison / current_form / observed / about: Serhii Kalinichenko / arm_length, grip_strength*
- [1:15] It's easier to pull him inside than on the outside. Kalinichenko really wants to do that.
  - *tactic / recent_context / analyst_interpretation / about: Serhii Kalinichenko / start_position, matchup_specific_history*
- [1:48] What a commitment that was. He absolutely dove on it. Dove directly on his bicep. I mean, completely different style of hook.
  - *tactic / recent_context / observed / hook*
- [1:48] I guess I have more endurance than Serhii
- [1:50] he can get into very good positions better than me
- [1:53] his press impressed me with Matushenko
- [1:55] even if I stop him and beat him in the first round, in the second and third rounds, I will be ready for even stronger hits
- [2:25] If that works. That's a foul for Kalinichenko. From Sergei, yeah. Yeah, yeah. I think, was it a floating elbow?
  - *other / current_form / observed / about: Serhii Kalinichenko / injury_or_recovery_status*
- [6:30] Did Serhii's press surprise you? Yeah, I mean, I didn't expect this. I thought that I will stop him somewhere close to the pinpad, but he just ran through me. So, yeah, he's stronger at the press than I expected.
  - *opponent_comparison / recent_context / observed / about: Yordan Tsonev / press, reserve_strength*

## [match 12] Oleg Petrenko def. Todd Hutchings - East vs West 22, right arm, Up to 105 kg

- [1:00] Oleg Petrenko is a multiple Ukrainian national champion, European air world champion, and independent world champion from Ukraine competing against Todd Hutchings in the 105-year world championship.
  - *other / historical_event / observed / matchup_specific_history*

## [match 15] Aleksi Zavrashvili def. Artem Oriabinskyi - East vs West 23, right arm, Up to 77 kg

- [0:58] The match was a classic battle of inside (Aleksi) versus outside (Artem) armwrestling styles at men's lightweight 77 kg right arm.
  - *tactic / historical_event / analyst_interpretation / hook, top_roll*
- [1:01] Aleksi Zavrashvili is a very accomplished armwrestler with multiple European and world championships, strong at different weight classes from 60 to 75 kilos.
  - *other / historical_event / community_narrative / about: Aleksi Zavrashvili / training_regimen, mental_focus*
- [1:23] Aleksi will try to get the slip as fast as he can and get to the straps to counter Artem's strong top roll.
  - *tactic / future_prediction / analyst_interpretation / about: Aleksi Zavrashvili / start_position, top_roll, grip_strength, explosive_strength, matchup_specific_history*
- [2:18] Artem Samson uses a low hand top roll trying to escape Aleksi's hand control and leverage height advantage.
  - *tactic / recent_context / analyst_interpretation / about: Artem Oriabinskyi / top_roll, wrist_control, frame_and_leverage*
- [2:19] Aleksi Zavrashvili has very good center control and is very sticky even when his hand is gone, using strong bicep and side pressure.
  - *form / current_form / analyst_interpretation / about: Aleksi Zavrashvili / side_pressure, reserve_strength*
- [3:13] Artem tries to hold on, separating and attacking with the shoulder to escape Aleksi's side pressure control.
  - *tactic / current_form / observed / about: Artem Oriabinskyi / side_pressure, shoulder_engagement*
- [3:38] Artem needs to climb and roll over the pronator muscle to supinate Aleksi more and counter side pressure effectively.
  - *tactic / current_form / analyst_interpretation / about: Artem Oriabinskyi / top_roll, supination, side_pressure*
- [3:44] Aleksi lost his wrist (broken back wrist) during the match but still maintained control using side pressure and arm power.
  - *injury / historical_event / observed / about: Aleksi Zavrashvili / injury_or_recovery_status, side_pressure*

## [match 16] Zurab Tavberidze def. Maayan Shterengas - East vs West 23, left arm, Up to 95 kg

- [1:05] Maayan exhibited dominant hand control in the initial round, effectively decimating the opponent's hand.
  - *form / current_form / observed / about: Maayan Shterengas / hand_size, grip_strength*
- [1:35] Maayan used fast twitch muscle and connection between back pressure and hand for fluid, hitch-free movement maintaining balance and pronation.
  - *form / general_principle / analyst_interpretation / about: Maayan Shterengas / back_pressure, explosive_strength, wrist_control*
- [1:50] He maintained pronation and opened opponent's hand, applying strong top rolling technique.
  - *tactic / current_form / observed / top_roll, wrist_control, supination*
- [3:00] Maayan was tested in round three and seemed to make a mistake allowing opponent to hook, resulting in a pin against him.
  - *tactic / historical_event / observed / about: Maayan Shterengas / hook*
- [3:20] Maayan was aggressive and fast, looking to finish matches quickly, often opting not to 'pose' in later rounds.
  - *form / current_form / analyst_interpretation / about: Maayan Shterengas / explosive_strength, mental_focus, reserve_strength*
- [3:40] Maayan's endurance was tested as the match progressed, especially when Zurab applied sustained arm power and hook defense.
  - *endurance / current_form / analyst_interpretation / about: Maayan Shterengas / hook, reserve_strength*
- [4:20] When Zurab got on Maayan's arm, it became difficult for Maayan to finish, suggesting he might need to add cup or shoulder techniques to keep off his arm.
  - *tactic / recent_context / analyst_interpretation / about: Maayan Shterengas / shoulder_engagement, side_pressure*

## [match 19] Betkili Oniani def. Rustam Babaiev - East vs West 23, left arm, Up to 95 kg

- [0:30] Betkili Oniani is making his debut on the left hand in this match.
- [0:50] Rustam Babaiev is a legendary arm wrestling icon with numerous accolades from European and World Championships, while Betkili Oniani is a former East versus West champion and multiple national champion from Georgia.
  - *other / historical_event / community_narrative / matchup_specific_history*
- [2:20] Betkili Oniani showed an explosive style in his left hand debut, contrasting his known reputation for endurance and slow pulls.
  - *form / current_form / observed / about: Betkili Oniani / explosive_strength, reserve_strength*
- [3:10] Rustam Babaiev showed a change-up by attempting a top roll early while Betkili Oniani expects a hook contest.
  - *tactic / current_form / analyst_interpretation / about: Rustam Babaiev / top_roll, hook*
- [3:20] Rustam Babaiev tried to top roll, which is out of his element against Betkili Oniani’s inside power and high hooking pressure.
  - *tactic / historical_event / analyst_interpretation / top_roll, hook, side_pressure, frame_and_leverage*
- [3:30] Betkili Oniani’s cut is very secure and confident, making it hard for Rustam Babaiev to get a bite despite his crashing down on the wrist style.
  - *tactic / current_form / observed / about: Betkili Oniani / wrist_control, start_position*
- [5:50] Rustam Babaiev received a warning and an elbow foul during the match, affecting his performance.
  - *injury / historical_event / observed / about: Rustam Babaiev / injury_or_recovery_status*
- [7:10] Betkili Oniani stays very close in to use strong inside power despite having a bigger frame, which is unusual for his size advantage but effective against Rustam.
  - *tactic / current_form / analyst_interpretation / about: Betkili Oniani / frame_and_leverage, press, side_pressure*
- [8:00] Betkili Oniani was breathing heavily but maintained high side pressure and showed strong endurance through the rounds.
  - *endurance / current_form / observed / about: Betkili Oniani / side_pressure*
- [8:20] Rustam Babaiev’s top roll was working but he was dropping his shoulder early and pulling back too much, reducing effectiveness.
  - *form / current_form / analyst_interpretation / about: Rustam Babaiev / top_roll, shoulder_engagement*
- [11:10] Betkili Oniani expressed respect for Rustam Babaiev as a legend, and committed to winning the match and aiming for a world title shot next.
  - *other / future_prediction / self_reported / about: Betkili Oniani / mental_focus, matchup_specific_history*

## [match 20] Aymeric Pradines def. Matt Mask - East vs West 23, left arm, Up to 105 kg

- [2:00] Matt Mask is a superior top roller with a venomous top roll that he hits so hard and efficiently. With his left hand, he can hook and transition to a press, showing versatility he doesn't use with his right hand.
  - *form / current_form / community_narrative / about: Matt Mask / top_roll, hook, press*
- [2:10] Aymeric Pradines uses a very high setup while Matt Mask uses a low hand top roll. There is a dynamic interaction based on these styles in their left arm match.
  - *setup / current_form / analyst_interpretation / start_position, top_roll*
- [2:55] Aymeric seemed to execute a wrist bend attempt (squeaky cup) which bent the wrist slightly, possibly to gain an advantage.
  - *tactic / current_form / analyst_interpretation / about: Aymeric Pradines / wrist_control, supination*
- [3:04] Matt Mask made a big jump with lots of finger pulling which resulted in an elbow foul and loss of the round.
  - *tactic / historical_event / observed / about: Matt Mask / start_position, elbow_discipline*
- [3:10] Matt Mask often uses finger pulling to gain an advantage in matches, capable of breaking opponents' fingers including three of his own.
  - *tactic / durable_style / community_narrative / about: Matt Mask / grip_strength*
- [3:40] Aymeric Pradines displays great elbow durability and strength, can pull any position effectively, and is not easily taken lightly especially when wrist control is involved.
  - *form / current_form / analyst_interpretation / about: Aymeric Pradines / elbow_discipline, reserve_strength, wrist_control*
- [4:00] Matt Mask uses back pressure and pronation effectively on the left hand, though the strap makes it more difficult. His hand is large but he is efficient with thumb pronation.
  - *form / current_form / analyst_interpretation / about: Matt Mask / back_pressure, press, supination, wrist_control, hand_size*
- [4:20] Aymeric applies strong back pressure which mitigates Matt Mask’s top roll and keeps the match competitive on left arm.
  - *tactic / current_form / analyst_interpretation / about: Aymeric Pradines / back_pressure, top_roll*
- [4:50] Aymeric has been busted open many times by very powerful athletes but consistently shows arm strength, elbow strength and durability.
  - *endurance / durable_style / analyst_interpretation / about: Aymeric Pradines / reserve_strength, elbow_discipline, injury_or_recovery_status*
- [5:00] Aymeric is a well-rounded arm wrestler with excellent arm strength and endurance on his left side, enabling him to dominate in this match.
  - *form / current_form / analyst_interpretation / about: Aymeric Pradines / arm_length, reserve_strength, arm_length*

## [match 21] Ayane Takenaka def. Melek Sahin - East vs West 23, right arm, Up to 60 kg

- [1:35] Ayane Takenaka opens her wrist up a little bit. This probably will go to the strap.
  - *tactic / current_form / analyst_interpretation / about: Ayane Takenaka / wrist_control, start_position*
- [1:38] One warning for Melek Zahin because two warnings. You can see how serious they both are. One foul, one warning for Melek Zahin. She needs to keep her composure. You don't want to lose a round on fouls and warnings.
  - *other / recent_context / observed / about: Melek Sahin / injury_or_recovery_status*
- [1:43] Ayane Takenaka, top rolls. Gets the hand. And we go into the straps.
  - *form / historical_event / observed / about: Ayane Takenaka / top_roll*
- [1:53] Wow. What a top roll attempt from... Here's the top roll. Wow. Perfect. Ayane Takenaka takes the first pin. Lots of motion just to calm herself down.
  - *form / historical_event / observed / about: Ayane Takenaka / top_roll*
- [2:59] Ayane Takenaka, 2-0. She's just two pins away for her first EVW title. Very impressive from young Ayane Takenaka. Compact and ton of back pressure with the side.
  - *form / current_form / observed / about: Ayane Takenaka / back_pressure, side_pressure*
- [3:34] Go! Elbow fall for Melek. Coming forward. Going over this... Over the pad. Very dominant from Ayane.
  - *other / current_form / observed / about: Ayane Takenaka / matchup_specific_history*
- [3:59] Too compact. Too much side pressure. Too much everything. Ayane Takenaka, 3-0. One more round.
  - *form / current_form / analyst_interpretation / about: Ayane Takenaka / side_pressure*
- [4:03] She has to go outside, right? She can't continue to... I think she must. She must try an outside option. She's got the height advantage. She's got a little bit of length in her arm. She should be able to possibly get out of the index finger.
  - *tactic / current_form / analyst_interpretation / arm_length, top_roll*
- [4:26] Ayane is so confident. She allows Melek to hit. Allows and then just easily rolls over to her side. Puts it on A-side and pins her.
  - *tactic / current_form / analyst_interpretation / about: Ayane Takenaka / top_roll*
- [4:42] Ayane Takenaka does what she couldn't do two years ago and wins the featherweight title on the right arm. Too much power.
  - *other / historical_event / observed / about: Ayane Takenaka / explosive_strength*

## [match 22] Alizhan Muratov def. Artyom Morozov - East vs West 23, left arm, Over 115 kg

- [2:22] Alizhan Muratov is so impressive versus the former champion Artyom Morozov, who has only lost before to Vitaly Letin and Alizhan Muratov.
  - *opponent_comparison / historical_event / community_narrative / matchup_specific_history*
- [2:22] Alizhan Muratov shows speed, power, and venom in his attacks against Artyom Morozov, overwhelming him.
  - *form / current_form / observed / about: Alizhan Muratov / explosive_strength, mental_focus*
- [2:22] Artyom Morozov was never able to establish an endurance advantage and was blown out of the water by Alizhan Muratov.
  - *endurance / historical_event / community_narrative / about: Alizhan Muratov / reserve_strength*

## [match 24] Oleksandr Telyatnik def. Davit Samushia - East vs West 23, right arm, Up to 85 kg

- [0:25] The match is contested on the right arm between Davit Samushia and Oleksandr Telyatnik.
- [0:32] Oleksandr Telyatnik, also known as Manifestor, is a dominant athlete with ten successful world championship defenses.
  - *form / historical_event / community_narrative / about: Oleksandr Telyatnik / mental_focus, matchup_specific_history*
- [0:40] Davit Samushia is the reigning and defending East versus West welterweight world champion, multiple Georgia national champion and WAF world champion, known for his endurance and calm demeanor.
  - *form / current_form / community_narrative / about: Davit Samushia / reserve_strength, mental_focus, training_regimen*
- [1:55] Davit Samushia is known for his exceptional endurance and ability to outlast opponents in long matches.
  - *endurance / durable_style / community_narrative / about: Davit Samushia / reserve_strength*
- [2:05] Manifestor uses a higher knuckle and low hand to adjust his grip in the match.
  - *tactic / historical_event / observed / grip_strength, start_position*
- [2:50] Manifestor shows fluid and confident transitions between hook and top roll techniques, dictating the pace and position of the match.
  - *form / current_form / analyst_interpretation / hook, top_roll, mental_focus*
- [3:10] Davit Samushia attempts to use hook and outside top roll techniques to counter Manifestor's speed and hand dominance.
  - *tactic / current_form / observed / about: Davit Samushia / hook, top_roll, hand_size*
- [3:15] Manifestor's style features a brave approach without fully committing to top roll, exploiting his speed and ability to finish quickly regardless of inside or outside position.
  - *form / durable_style / analyst_interpretation / top_roll, explosive_strength, start_position*
- [3:50] There was possibly an elbow foul or edge contact during the match involving David Samushia, though it was unclear if it was a foul.
  - *other / historical_event / unclear / injury_or_recovery_status*
- [4:25] Manifestor maintains confidence and control throughout multiple rounds not showing signs of fatigue while wearing down the champion David Samushia.
  - *endurance / historical_event / analyst_interpretation / about: Davit Samushia / reserve_strength, mental_focus*
- [4:30] Manifestor's technique involves dictating pace, making all choices, and maintaining fluidity and explosiveness in his arm wrestling style.
  - *tactic / durable_style / analyst_interpretation / start_position, explosive_strength, mental_focus*
- [5:25] Manifestor is described as young, extraordinarily talented, strong, and explosive at 24 years old, contrasting with Samushia's calm and experienced style.
  - *opponent_comparison / recent_context / community_narrative / explosive_strength, mental_focus*
- [6:30] Manifestor wins the right arm welterweight championship match against David Samushia, ending Samushia's 10-title defense streak.

## [match 25] Ivan Matyushenko def. Dave Chaffee - East vs West 23, right arm, Up to 115 kg

- [0:56] Maybe Dave has a little advantage in power, but Ivan Matyushenko is more explosive and very technical with the ability to hook almost anybody.
  - *opponent_comparison / current_form / analyst_interpretation / explosive_strength, hook, top_roll*
- [1:42] Both athletes have a history of excellence; Ivan is multiple national and world champion, Dave is defending EVW heavyweight champion and multiple national champion in the US.
  - *other / historical_event / community_narrative / matchup_specific_history*
- [3:38] Dave has a unique style. He doesn't really top-roll people. He sweeps them with side pressure and back pressure to take their hand away.
  - *tactic / durable_style / analyst_interpretation / about: Dave Chaffee / side_pressure, back_pressure*
- [4:21] Ivan Matyushenko uses speed and explosiveness to hit hooks and apply pressure quickly, often catching Dave off guard early in the rounds.
  - *tactic / recent_context / analyst_interpretation / about: Ivan Matyushenko / explosive_strength, hook, press*
- [4:42] Ivan executes a hook while Dave tries to hold on flat-handed; Dave's form is flat and defensive but gives access to Ivan's pronator.
  - *form / historical_event / analyst_interpretation / about: Ivan Matyushenko / hook, wrist_control, mental_focus*
- [4:57] Dave relies heavily on his bicep and gym strength; when exposed on his bicep, he becomes vulnerable and his endurance is questionable.
  - *form / general_principle / analyst_interpretation / about: Dave Chaffee / reserve_strength, training_regimen, mental_focus*
- [4:58] Ivan appeared to have an endurance advantage, making the match last and putting Dave into defensive positions; Dave was not known for endurance but showed improvement this match.
  - *endurance / historical_event / analyst_interpretation / reserve_strength, mental_focus*
- [5:30] Ivan uses his frame well defensively, twisting into strong arm wrestling positions and playing defense to counter Dave's power.
  - *tactic / current_form / analyst_interpretation / about: Ivan Matyushenko / frame_and_leverage, side_pressure*
- [6:25] Dave is prone to elbow fouls due to his style of loading up and back pressure, which costs him points in the match.
  - *tactic / general_principle / community_narrative / about: Dave Chaffee / back_pressure, elbow_discipline*
- [20:07] After the match, Ivan commented he could not curl his arm, indicating significant arm strain.
  - *injury / historical_event / self_reported / about: Ivan Matyushenko / injury_or_recovery_status*

## [match 28] Bob Brown def. Isaiah Jones - East vs West 24, right arm, Up to 85 kg

- [0:51] Bob Brown is using as much of that elbow pad as possible to gain leverage and control in the match.
  - *tactic / current_form / observed / about: Bob Brown / frame_and_leverage*
- [0:58] Bob Brown is built for the side hook and uses control to achieve the desired arm angle.
  - *form / general_principle / observed / about: Bob Brown / hook, side_pressure, wrist_control*
- [1:09] Bob Brown is coming back from a bicep tear injury two years ago but continues to pull strong.
  - *injury / recent_context / self_reported / about: Bob Brown / injury_or_recovery_status, reserve_strength*
- [1:15] Bob Brown shows impressive longevity and endurance in arm wrestling despite his age and injuries.
  - *endurance / current_form / observed / about: Bob Brown / reserve_strength, injury_or_recovery_status*
- [1:29] Bob Brown effectively uses a top roll and climbing technique to finish his opponent.
  - *tactic / historical_event / observed / about: Bob Brown / top_roll*
- [1:42] Bob Brown uses patient attacks and carefully controls pronation to negate his opponent's moves.
  - *tactic / durable_style / analyst_interpretation / about: Bob Brown / mental_focus, wrist_control, supination*
- [2:30] Bob Brown gains positional advantage by taking the center and trapping the opponent.
  - *tactic / current_form / observed / about: Bob Brown / start_position, grip_strength, frame_and_leverage*
- [3:36] Bob Brown executes an explosive start right from the go and transitions quickly to a winning hand position.
  - *form / historical_event / observed / about: Bob Brown / explosive_strength, start_position*
- [4:10] Bob Brown is a legendary figure with 43 years experience and can beat much younger competitors like 21-year-old Isaiah Jones.
  - *form / durable_style / community_narrative / about: Bob Brown / reserve_strength, mental_focus, training_regimen*

## [match 29] Courtney Huycke def. Nastasia Pastorkova - East vs West 24, right arm, Up to 77 kg

- [5:03] Courtney impressed with strong inside hook strength, power in straps and eagerness, while Nastasia is a fast junior world champion with good top rolling speed.
- [6:15] Courtney grips very low and tries to block Nastasia’s anticipated top roll, using strong center position control.
- [6:35] Courtney is in a center position at about 90 degrees from the table, suitable for a shoulder press.
- [7:48] Courtney uses a trenches transition effectively during the match, which gives her greater control.
- [8:13] Nastasia looks worried when Courtney controls the match tightly, especially regarding lateral thumb pressure.
- [9:19] Courtney is fully supinated with palm up, which is a very good position for her right arm in the match versus Nastasia Pastorkova.
- [12:57] Courtney shows no sign of wrist or hand fatigue despite the high-intensity grips in the match.

## [match 30] Ryan Belanger def. Jason Merlo - East vs West 24, right arm, Up to 95 kg

- [3:20] Jason Merlo is noted for having one of the best top row techniques in the community, showing superior hand, wrist, and forearm strength early in the match.
- [4:10] Jason Merlo had a short start and had to be more aware, as his elbow was about an inch off the pad.
- [6:30] Jason Merlo uses a low hand top roll setup to keep his wrist away from Ryan Belanger, making it harder for Ryan to get in the strap and hook.
- [6:30] Ryan Belanger is committed to keeping his wrist in position to get close to the straps and utilize the hook, often forcing Jason Merlo to adjust.
- [10:20] Ryan Belanger looks a lot stronger arm-to-arm and is one step ahead in every move compared to Jason Merlo in this right arm match.
- [12:30] Ryan worked intensely on his hand and wrist for 12-13 weeks to improve his right arm technique and result, which paid off in this match against Jason Merlo.

## [match 31] Jeremy Parker def. Auden Larratt - East vs West 24, right arm, Up to 115 kg

- [11:06] Jeremy Parker uses a top roll technique with great side pressure and timing, focusing tension on his pronator.
- [11:22] Jeremy Parker's buckle position gives him some advantage by gaining height and a better position if he can't top roll.
- [11:25] Jeremy Parker's weight cut to reach the heavyweight class raises questions about possible impact on his endurance or strength.
- [11:40] Jeremy Parker needs to work his hand and pronation to turn the match around when he's in the buckle position.
- [11:53] Jeremy Parker mentions that due to surgery his elbow is back further and he's aware of having two elbows in how he pulls.
- [12:13] Auden Larratt improved his setup in the second round by going up with a lot of cup and keeping his pronation intact, gaining height over Jeremy Parker who expected the same earlier setup.
- [12:33] Auden Larratt uses a cup and pronation-heavy technique to gain height and stay tense during the match.
- [12:34] Auden Larratt has very strong hand strength and is aware enough to talk during the match showing his experience.
- [12:41] Auden Larratt climbs and pushes in the center of the pad during his match against Jeremy Parker, which caused some controversy over whether it's a push or a legal move given his elbow center position.
- [13:22] Jeremy Parker shows patience and strategy by choosing to let some rounds go and concentrate on a good winning position later in the match.

## [match 32] Irakli Zirakashvili def. Yoshinobu Kanai - East vs West 24, right arm, Up to 105 kg

- [0:07] Irakli Zirakashvili is very young and very strong, while Yoshinobu Kanai is older and experienced.
- [0:29] Match will be contested over five rounds of arm wrestling on the right arm in the men's 105 kilogram light heavyweight division.
- [1:33] Kanai uses back pressure and tries to force the match to the strap early; Zirakashvili is fast and tries to control Kanai's hand without going to the strap.
- [1:50] Zirakashvili is very quick, deliberate, controlled, and uses his speed to gain early advantages without rushing or compromising his wrist position.
- [2:00] Zirakashvili paced himself well to avoid early lactic acid buildup and waited for the appropriate moment to hit hard and finish the match.
- [2:05] Kanai is expected to excel in endurance phases after strap engagement and when lactic acid builds up, showing his experience and back pressure strength.
- [2:15] Zirakashvili maintains tight stance and good calf engagement for stability.
- [3:10] Zirakashvili executed an incredible game plan, dominated the match quickly, and defeated Kanai in about seven minutes despite Kanai's experience and toughness.
- [4:30] Zirakashvili expressed calm confidence before and during the match, stating he could also compete in 95kg without problem and showing a clear game plan.

## [match 34] Tom Holland def. Justin Bishop - East vs West 24, right arm, Up to 77 kg

- [0:21] This arm is blasting through you. It's going to be like you're not even there.
- [1:52] We know that Bishop's hand and wrist is his biggest weapon.
- [2:44] Justin is so powerful at that start. His hand and wrist is ridiculous. His hand first. And he was the quicker man by a mile to his position there.
- [8:34] Justin is so aggressive. He always starts with 100% focus on quick victory. His hand and wrist is rock strong.
- [8:39] Justin Bishop talks about his positioning on the pad and how it really puts you off your game when you don't find that spot.
- [11:54] Justin is incredible from the go. He will take you the first round to the pad easily, but you can get a stop. He will have problems later, and Tom Holland is the problem he's facing.
- [14:16] If Justin is able to control Tom's pronator from that position, he wins. But if he just thinks he's going to pull him sideways, I don't think that's going to happen.
- [14:47] Justin Bishop needs to get it done quickly. The longer this match goes on the board favors Mr. Tom Holland.

## [match 36] Corey West def. Pavlo Derbedyenyev - East vs West 24, left arm, Open category

- [0:00] There is mention of the left arm with the question about a strap and pulling the kick weak, which suggests concern or setup related to arm positioning or injury management in the match.
- [1:00] Pavlo is a different arm wrestler; he thinks he has something for Corey West, showing great progression on the left arm in the last two years, while Corey West is very solid and ambidextrous, strong in both arms.
- [2:43] Corey West is very hard to top roll due to his thick, strong hand which makes his technique difficult to counter on the left arm.
- [2:49] Pavlo needs to try an inside wrist-to-wrist hook rather than going outside since the outside lane against Corey West looks closed.
- [6:17] Pavlo must knock Corey West off center by getting on his bicep and standing up to gain positional advantage for any chance at winning the left arm match.
- [6:35] Corey West shows excellent posture with a tight, tall position and his hand near the collar bone area in left arm matches, which is a perfect technique to look at.
- [7:26] Corey West has been recognized as the number one left hand super heavyweight in North America, showing dominant power over Pavlo Derbedyenyev in this match held in Little Rock, Arkansas.

## [match 39] Riekerd Bornman def. Alizhan Muratov - East vs West 24, right arm, Open category

- [2:58] Alizhan Muratov has tremendous hand and wrist strength, fast switch explosivity, and strong forearm strength on the right arm.
  - *form / current_form / analyst_interpretation / about: Alizhan Muratov / wrist_control, explosive_strength, grip_strength*
- [5:10] Riekerd Bornman adjusted his hand and wrist control to improve his position and ultimately secured a dominant win against Alizhan Muratov.
  - *tactic / historical_event / analyst_interpretation / about: Riekerd Bornman / wrist_control*
- [8:28] Riekerd Bornman suffered an elbow injury that affected his performance during the match.
  - *injury / recent_context / self_reported / about: Riekerd Bornman / injury_or_recovery_status*
- [9:45] Alizhan Muratov tried to use an open top roll technique effectively on the right hand but was countered by Riekerd Bornman’s strategy.
  - *tactic / historical_event / analyst_interpretation / about: Alizhan Muratov / top_roll*
- [10:30] Riekerd Bornman kept calm, remained diligent, and timed his maneuvers well to maintain balance and deny his opponent.
  - *tactic / historical_event / analyst_interpretation / about: Riekerd Bornman / mental_focus, matchup_specific_history*
- [16:00] Riekerd mentioned needing rest for his elbow after some scans and wants to become stronger and better.
  - *injury / recent_context / self_reported / about: Riekerd Bornman / injury_or_recovery_status, training_regimen*

## [match 42] Michael Todd def. Oleg Petrenko - East vs West 24, right arm, Up to 105 kg

- [2:26] Oleg Petrenko has probably the strongest hand and wrist in this class, maybe anywhere, and is very powerful compared to Michael Todd.
  - *opponent_comparison / general_principle / analyst_interpretation / grip_strength, wrist_control, reserve_strength*
- [3:20] Michael Todd believes stylistically he is a poor matchup for Oleg Petrenko because of his well-rounded skill set and power.
  - *opponent_comparison / current_form / self_reported / about: Michael Todd / reserve_strength, explosive_strength, mental_focus*
- [3:37] Oleg Petrenko prefers to keep the arm wrestling grip loose rather than tightly connected, which is an intelligent strategic move.
  - *tactic / durable_style / analyst_interpretation / about: Oleg Petrenko / grip_strength, mental_focus*
- [4:04] Oleg Petrenko is not known as a great climber or technician but uses brute force and power in his arm wrestling style.
  - *form / durable_style / community_narrative / about: Oleg Petrenko / explosive_strength, reserve_strength*
- [4:19] Michael Todd is comfortable and experienced working in difficult and uncomfortable positions, often using diligent work and adjustments to gain advantage.
  - *form / durable_style / analyst_interpretation / about: Michael Todd / shoulder_engagement, elbow_discipline, mental_focus*
- [6:51] Michael Todd uses micro adjustments and pulses during the match to deny his opponent's balance and unsettle them.
  - *tactic / current_form / analyst_interpretation / about: Michael Todd / mental_focus, grip_strength*
- [7:29] Michael Todd is preparing to deploy a powerful shoulder press as part of his finishing tactics.
  - *tactic / future_prediction / self_reported / about: Michael Todd / press, shoulder_engagement*
- [8:45] Oleg Petrenko is panicking and struggling to find effective moves as his wrist and hand fatigue become apparent during the match.
  - *endurance / current_form / analyst_interpretation / about: Oleg Petrenko / wrist_control, grip_strength, reserve_strength*
- [9:23] Oleg Petrenko's wrist and hand are heavily fatigued and damaged from the high-intensity match, affecting his endurance and performance.
  - *injury / current_form / observed / about: Oleg Petrenko / injury_or_recovery_status, reserve_strength, mental_focus, arm_length*

## [match 43] Vladislavs Krasovskis def. Artem Popov - East vs West 25, right arm, Up to 85 kg

- [5:23] There is a big drive from Artem but Vlad equal to it and the brakes are well and truly on
  - *other / current_form / observed / reserve_strength, mental_focus*
- [6:16] Artem has explosivity but Vlad's experience and style adaptation gave him the edge
  - *form / recent_context / analyst_interpretation / explosive_strength, matchup_specific_history*
- [6:20] Vlad is known for explosivity and fast starts but here used cerebral and technical pulling style
  - *other / general_principle / community_narrative / about: Vladislavs Krasovskis / explosive_strength, start_position, mental_focus*
- [11:10] Artem might consider playing the endurance card as he is in a tough position needing to adjust radically
  - *endurance / current_form / analyst_interpretation / about: Artem Popov / reserve_strength, mental_focus*
- [11:50] Vlad used hook technique and wrist chopping to force Artem to lose height and control the match
  - *tactic / historical_event / observed / about: Vladislavs Krasovskis / hook, wrist_control*
- [11:52] Vlad is forcing Artem's fingers way down below his thumb applying prominent down pressure on hand
  - *tactic / current_form / observed / about: Vladislavs Krasovskis / top_roll, wrist_control, press*
- [12:09] Artem was reaching around Vlad and stretching, a move not favored, as Vlad blocked well and controlled the load
  - *tactic / historical_event / observed / about: Artem Popov / top_roll, grip_strength*
- [12:12] Vlad is controlling the match with high knuckle, back pressure and rise not leaving a lot of options
  - *tactic / current_form / observed / about: Vladislavs Krasovskis / back_pressure*
- [12:30] Vlad looked more relaxed and comfortable as the match progressed, settling in to dominate the match
  - *form / recent_context / observed / about: Vladislavs Krasovskis / mental_focus*
- [14:20] Vlad switched his style using hips movement and pressing for last round to secure victory
  - *tactic / historical_event / observed / about: Vladislavs Krasovskis / press, shoulder_engagement*

## [match 45] Zurab Tavberidze def. Ryan Belanger - East vs West 25, right arm, Up to 95 kg

- [1:52] Ryan Belanger and Zurab Tavberidze arm wrestle very similarly, both using strap bent back and inside pull techniques; it is described as a mirror match with both known for stamina and endurance.
  - *other / general_principle / community_narrative / hook, back_pressure, arm_length, reserve_strength, mental_focus*
- [2:08] Zurab Tavberidze capitalized on Ryan Belanger's pronation loss by rolling over and pinning him after Ryan tried to pin sideways.
  - *tactic / historical_event / observed / about: Zurab Tavberidze / top_roll, press*
- [4:10] Ryan Belanger displayed a very concerned look during the match, possibly indicating he was injured, with specific attention to his collateral ligament by Adam and Wojcicki, causing concern for his ability to compete effectively.
  - *injury / historical_event / analyst_interpretation / about: Ryan Belanger / injury_or_recovery_status*

## [match 47] Adam Wawrzynski def. Nurdaulet Aidarkhan - East vs West 25, right arm, Up to 95 kg

- [1:21] Adam has a very powerful, redesigned, reformed right arm; he's super strong with great endurance and excellent ability to contain top rollers.
  - *form / current_form / self_reported / about: Adam Wawrzynski / reserve_strength, back_pressure, arm_length*
- [2:04] Nurdaulet known for his speed, but it did not move too far against Adam's strong endurance and position control.
  - *form / general_principle / community_narrative / about: Nurdaulet Aidarkhan / reserve_strength, mental_focus, frame_and_leverage*
- [3:00] Adam's ability to keep the arm in the center and contain his opponent is incredible, making it hard for Nurdaulet to gain leverage.
  - *form / current_form / analyst_interpretation / about: Adam Wawrzynski / frame_and_leverage*
- [3:30] Nurdaulet tries to put as many 'bullets' as possible into Adam by fair means or foul given Adam's static strength and stamina.
  - *tactic / current_form / unclear / about: Nurdaulet Aidarkhan / reserve_strength, mental_focus*
- [5:25] Adam used better defense engaging the upper part of his hand fluidly and not committing hard with supination which works well against Nurdaulet's speed.
  - *tactic / historical_event / analyst_interpretation / about: Adam Wawrzynski / wrist_control, supination, mental_focus*
- [5:50] Adam maintains excellent wrist containment and his hand is a significant factor in neutralizing Nurdaulet's pronation and power.
  - *form / current_form / analyst_interpretation / about: Adam Wawrzynski / wrist_control, supination*
- [11:25] In the deciding rounds, Adam's strategic use of his hook and timing outmaneuvered Nurdaulet's chaotic power style despite multiple fouls.
  - *tactic / historical_event / analyst_interpretation / about: Adam Wawrzynski / hook, explosive_strength*
- No explicit injury claims mentioned, focus is on endurance and technical skill.
  - *endurance / unclear / unclear / reserve_strength, mental_focus*

## [match 48] Eldar Bubenko def. Paul Linn - East vs West 25, right arm, Up to 95 kg

- [0:00] In the match, Bubenko focused on hand and wrist control on the right arm to dominate Paul Linn.
  - *tactic / historical_event / analyst_interpretation / about: Eldar Bubenko / wrist_control*
- [0:10] Paul Linn was very coiled up with shoulder up and strong posture indicating readiness to drop on the arm.
  - *form / current_form / observed / about: Paul Linn / shoulder_engagement, mental_focus*
- [0:15] Eldar Bubenko looked very relaxed and super calm, showing experience as the strap came down on the right arm.
  - *form / historical_event / observed / about: Eldar Bubenko / mental_focus, start_position*
- [0:50] Bubenko got a massive advantage on Paul Linn's hand and wrist right at the start by scooping them up and running to the back of the pad.
  - *tactic / historical_event / observed / about: Eldar Bubenko / grip_strength, wrist_control, start_position*
- [1:00] Eldar had wonderful hand position and all the angles right, overpowering Paul Linn's arm and wrist throughout the start.
  - *form / historical_event / observed / about: Eldar Bubenko / wrist_control, hand_size, start_position*
- [1:30] Bubenko’s movement with his elbow changed the angle sharply and completely decimated Paul Linn's hand and wrist, effectively ending the contest.
  - *tactic / historical_event / observed / about: Eldar Bubenko / wrist_control, elbow_discipline*
- [1:40] Paul Linn was very tense and rigid in his right arm posture while Bubenko was calm and relaxed, which seemed to give Bubenko an advantage.
  - *form / current_form / analyst_interpretation / about: Eldar Bubenko / mental_focus, arm_length, shoulder_engagement*
- [2:10] Bubenko was very dominant in side push aided by Linn being coiled behind his arm, allowing Bubenko to blast him to the side and gain control over the right arm.
  - *tactic / historical_event / observed / about: Eldar Bubenko / side_pressure, start_position, frame_and_leverage*
- [2:15] Paul Linn’s shoulder was far behind his arm early, reducing his engagement and giving Bubenko a tremendous advantage in right arm control.
  - *form / historical_event / observed / about: Paul Linn / shoulder_engagement, arm_length, arm_length, arm_length*
- [2:25] Paul Linn might have to concede wrist control and focus on fighting with his arm instead as he was not getting any hand position on his right arm.
  - *tactic / current_form / analyst_interpretation / about: Paul Linn / wrist_control, mental_focus*
- [2:40] Fatigue was becoming an issue for Paul Linn as he repeatedly was caught on the right arm underneath and had to catch up to Bubenko's powerful drive.
  - *endurance / current_form / analyst_interpretation / about: Paul Linn / reserve_strength, explosive_strength*
- [2:50] Bubenko showed excellent pronation and a strong cup grip on the right arm, preventing Paul Linn from opening his arm.
  - *form / historical_event / observed / about: Eldar Bubenko / wrist_control, grip_strength, supination*
- [3:00] Bubenko received an elbow foul during the match while maintaining pressure on Paul Linn's right arm.
  - *injury / historical_event / observed / about: Eldar Bubenko / elbow_discipline*
- [3:10] Bubenko was relaxed, square, and calm while Paul Linn was tight and tense in his right arm posture from the start.
  - *form / historical_event / observed / start_position, mental_focus*
- [3:20] The fundamental prerequisite that Bubenko exploited was to disengage Paul Linn's body line, allowing superior right hand control to dominate.
  - *tactic / historical_event / analyst_interpretation / about: Eldar Bubenko / wrist_control, frame_and_leverage*
- [3:40] Paul Linn tried to perform a flop wrist press with his right arm late in the match in an attempt to gain control but it was too late to be effective.
  - *tactic / historical_event / analyst_interpretation / about: Paul Linn / press, wrist_control*
- [5:10] Bubenko stated that his tactic was to fight Paul's top roll technique at high speed focusing on control, which was effective in the right arm match.
  - *tactic / historical_event / self_reported / about: Eldar Bubenko / top_roll, mental_focus*

## [match 49] Daniel Procopciuc def. Vachagan Hovhannisyan - East vs West 25, left arm, Up to 77 kg

- [1:01] Vachagan usually pulls hook. This time going for a top roll.
  - *tactic / durable_style / community_narrative / about: Vachagan Hovhannisyan / top_roll, hook*
- [1:10] Vachagan said he has prepared some special lane, especially for Daniel.
  - *setup / future_prediction / self_reported / about: Vachagan Hovhannisyan / matchup_specific_history*
- [1:40] Vachagan put his foot up on the peg. He's clearly looking to generate a lot of side pressure.
  - *tactic / current_form / observed / about: Vachagan Hovhannisyan / side_pressure*
- [1:58] Daniel is so impressive on that slow pull. Like he has so much power that so many times he just kind of slowly, slowly pins his opponents.
  - *form / current_form / analyst_interpretation / about: Daniel Procopciuc / reserve_strength, explosive_strength*
- [8:32] Daniel Procopciuc remains the champion on the left arm at 77 kg, very dominant and controlled.
  - *form / current_form / observed / about: Daniel Procopciuc / matchup_specific_history*
- [9:26] Almost every single round looked the same. Absolute domination from Daniel Procopciuc on the left arm.
  - *form / historical_event / observed / about: Daniel Procopciuc / top_roll, hook, press*

## [match 50] Krasimir Kostadinov def. Nugzari Chikadze - East vs West 25, right arm, Up to 105 kg

- [3:23] Krasimir Kostadinov is a principled and powerful arm wrestler, a world and European champion, known for his heavy choke, lean-in style and excellent hand containment.
  - *form / durable_style / analyst_interpretation / about: Krasimir Kostadinov / hand_size, frame_and_leverage, mental_focus*
- [4:05] Krasimir Kostadinov wants to turn the match into a hook match and avoid an outside top roll because Nugo can stay almost completely vertical and use top roll effectively, but Krasimir has lost mobility and is super open.
  - *tactic / recent_context / analyst_interpretation / about: Krasimir Kostadinov / hook, top_roll, arm_length, frame_and_leverage*
- [4:06] Krasimir needs to get the match into a strap, not lose his wrist, keep as much center as possible and pronation, then turn it into a hook match.
  - *tactic / future_prediction / analyst_interpretation / about: Krasimir Kostadinov / wrist_control, supination, hook*
- [5:32] Nugo is extremely strong, explosive, versatile, strong side pressure, very good biceps, strong pronation and top roll attack.
  - *form / current_form / self_reported / about: Nugzari Chikadze / explosive_strength, side_pressure, top_roll*
- [7:26] Krasimir Kostadinov rarely uses toproll; he prefers inside matches and aims to supinate his opponent before the opponent can turn him on pronation.
  - *form / durable_style / analyst_interpretation / about: Krasimir Kostadinov / top_roll, supination, start_position*
- [8:00] Nugo will fully commit to a top roll but might switch to forward hook depending on the round progression.
  - *tactic / future_prediction / analyst_interpretation / about: Nugzari Chikadze / top_roll, hook*
- [9:59] Krasimir Kostadinov maintains heavy lean and uses his whole frame to choke the life out of the match, making him a very difficult opponent to arm wrestle.
  - *form / durable_style / analyst_interpretation / about: Krasimir Kostadinov / frame_and_leverage, side_pressure*
- [10:19] Krasimir Kostadinov conditions are excellent because he trains multiple sessions daily including pulling with training partners, whereas Nugo has high explosiveness but might burn out.
  - *form / current_form / analyst_interpretation / about: Krasimir Kostadinov / training_regimen, explosive_strength, reserve_strength*
- [14:05] Krasimir aims to keep hand containment and side pressure while slowly supinating Nugo and eating his pronation.
  - *tactic / current_form / analyst_interpretation / about: Krasimir Kostadinov / side_pressure, supination*
- [16:28] Krasimir Kostadinov successfully makes Nugo play his game and controls the pace by containing his hand and forcing him to play under his conditions, especially in straps.
  - *tactic / historical_event / analyst_interpretation / about: Krasimir Kostadinov / grip_strength, matchup_specific_history, mental_focus*
- [19:00] Krasimir's heavy lean and controlled drives with locked in position, no outs, and no relenting of pressure characterize his dominant form in the match.
  - *form / current_form / observed / about: Krasimir Kostadinov / press, elbow_discipline, mental_focus*

## [match 51] Ibragim Sagov def. Yordan Tsonev - East vs West 25, right arm, Up to 115 kg

- [1:34] Yordan Tsonev is considered the best hook specialist with a very long and excellent form, especially comfortable in the 115 kg division with a strong opening, making it difficult to pull him out of position.
  - *form / durable_style / community_narrative / about: Yordan Tsonev / hook, explosive_strength, start_position*
- [1:45] The match-up in the 115 kg category is tough due to Yordan's comfort and strong form, and Ibragim's ability to resist being pulled from center, indicating a strong contest on right arm.
  - *other / current_form / analyst_interpretation / reserve_strength, mental_focus*
- [2:02] Ibragim Sagov is so powerful in extreme pulling and does not plan to pull Yordan Tsonev, indicating a tactic focused on controlled strength rather than maximum pulling.
  - *tactic / current_form / analyst_interpretation / about: Ibragim Sagov / reserve_strength, explosive_strength*
- [3:02] Yordan Tsonev was unable to pull Ibragim Sagov effectively and was possibly strained, suggested by mention that Yordan might have been 'turned'.
  - *other / historical_event / community_narrative / about: Yordan Tsonev / injury_or_recovery_status, matchup_specific_history*
- [3:08] Ibragim Sagov indicated readiness and confidence, expressing he was prepared to quickly finish the match and avoid a prolonged contest, showing strong endurance and match control.
  - *endurance / current_form / self_reported / about: Ibragim Sagov / reserve_strength, mental_focus*
- [4:06] The match between Ibragim Sagov and Yordan Tsonev was the fastest in history, lasting about two seconds, showing Sagov's extraordinary speed and power on the right arm.
  - *form / historical_event / observed / about: Ibragim Sagov / explosive_strength*

## [match 53] Kamil Jablonski def. Georgi Tsvetkov - East vs West 25, right arm, Over 115 kg

- [6:18] Georgi cannot close his hand, he's touching the strap there, indicating possible strain or injury affecting his grip.
  - *injury / current_form / observed / about: Georgi Tsvetkov / injury_or_recovery_status, grip_strength*
- [6:56] Georgi is in a horrible position, nowhere to go, arm cut off from his body, very close to going over the pad, which is dangerous in the match context.
  - *other / current_form / observed / about: Georgi Tsvetkov / frame_and_leverage, shoulder_engagement, matchup_specific_history*
- [7:03] Georgi has exceptional endurance, able to come back round after round very strong with very little fade, typical of Bulgarian conditioning.
  - *endurance / general_principle / community_narrative / about: Georgi Tsvetkov / reserve_strength, training_regimen*
- [7:09] Kamil uses so much frame in his technique that he often is not muscularly exhausted during the match, allowing better endurance.
  - *tactic / general_principle / analyst_interpretation / about: Kamil Jablonski / frame_and_leverage, reserve_strength, arm_length, training_regimen, mental_focus, injury_or_recovery_status*
- [11:14] Georgi does not have an outside top roll; he focuses on hooking and rolling to gain separation from his arm and bring opponent out of shoulder.
  - *tactic / durable_style / analyst_interpretation / about: Georgi Tsvetkov / top_roll, hook, wrist_control, shoulder_engagement*
- [14:50] Kamil Jablonski is versatile, successfully using king's move and open top roll techniques, enabling seamless transition and strong offensive capability.
  - *form / durable_style / analyst_interpretation / about: Kamil Jablonski / top_roll, training_regimen*
- [16:45] Kamil's press has opened up again later in the match, suggesting possible fatigue or vulnerability that Georgi tries to capitalize on.
  - *form / recent_context / analyst_interpretation / about: Kamil Jablonski / press, reserve_strength, mental_focus*

## [match 54] Vitalii Laletin def. Alizhan Muratov - East vs West 25, left arm, Over 115 kg

- [0:22] This is the main event for the left arm in the men's super heavyweight division over 7 rounds at East vs. West, a world championship bout for the left arm.
- [0:51] Vitalii was trying to pull Alizhan back, implying a defensive or controlling tactic on the left arm.
  - *tactic / unclear / analyst_interpretation / about: Vitalii Laletin / side_pressure, back_pressure, start_position*
- [0:53] Alizhan Muratov appeared to be holding a very deep grip and was very fast in hooking on the left arm fight early in the first round.
  - *form / current_form / observed / about: Alizhan Muratov / hook, grip_strength, start_position*
- [1:11] Vitalii Laletin looked like he had cut a hand, suggesting some potential injury during the match on the left arm.
  - *injury / historical_event / observed / about: Vitalii Laletin / injury_or_recovery_status*
- [1:21] There was a question about the penalty (foul) on the hands of Alizhan Muratov, with discussion about high and low penalties, and whether Muratov looked high with his arms.
  - *other / recent_context / community_narrative / about: Alizhan Muratov / injury_or_recovery_status*
- [1:37] Vitalii Laletin was in full control and dominated with powerful strikes (left arm strikes) against Alizhan Muratov in the first round.
  - *tactic / historical_event / observed / about: Vitalii Laletin / explosive_strength*
- [1:42] There is a huge size difference between Alizhan Muratov and Vitalii Laletin, making it very difficult to handle the individual matchup on the left arm.
  - *opponent_comparison / general_principle / analyst_interpretation / arm_length, frame_and_leverage*
- [1:46] Alizhan Muratov lost the first continuous left arm penalty (round) here on the EVW professional stage, which is a rare occurrence for him, indicating some endurance or performance aspect.
  - *endurance / current_form / observed / about: Alizhan Muratov / reserve_strength, mental_focus*

## [match 56] Daniyar Roman def. Grigorii Liashchuk - East vs West 25, right arm, Over 115 kg

- [0:41] Daniyar showed speed as a weapon, being very fast for a super heavyweight and had refined technique.
  - *form / current_form / analyst_interpretation / about: Daniyar Roman / explosive_strength, mental_focus*
- [0:58] Daniyar's shot hook started to get his wrist taken so he switched to a top roll and came out on top in that transaction very quickly.
  - *tactic / historical_event / observed / about: Daniyar Roman / hook, wrist_control, top_roll*
- [1:08] Despite being just 20 years old, Daniyar is a giant super heavyweight with refined technique and lots of table time.
  - *form / current_form / analyst_interpretation / about: Daniyar Roman / training_regimen, matchup_specific_history*
- [1:47] When Grigorii went sideways and rolled on his pronation, Daniyar fully opened his opponent and kept his shoulder in, giving a great follow through and ultimately scored.
  - *tactic / historical_event / observed / about: Daniyar Roman / top_roll, supination, shoulder_engagement*
- [2:31] Daniyar fought till the end in round two and managed a comeback to pin Grigorii despite having his shoulder partially committed and being fully turned over.
  - *endurance / historical_event / observed / about: Daniyar Roman / shoulder_engagement*
- [3:20] There was damage done to Daniyar's pronator and wrist early in the match and his pronator is gone for sure, impacting his ability to fight tightly.
  - *injury / current_form / observed / about: Daniyar Roman / injury_or_recovery_status, wrist_control*
- [3:34] Daniyar needs to get his shoulder behind his body to avoid his wrist bending back and to have a better position against Grigorii's attacks.
  - *tactic / current_form / analyst_interpretation / about: Daniyar Roman / shoulder_engagement, wrist_control, frame_and_leverage*
- [4:19] In round three Daniyar executed a top roll that stretched Grigorii fully out and may have won him the pin, though there was a foul call and review.
  - *form / historical_event / observed / about: Daniyar Roman / top_roll*
- [4:58] Daniyar lost his wrist and hand control early but his ability to battle through injury and keep pressing was remarkable.
  - *injury / historical_event / observed / about: Daniyar Roman / wrist_control, press, injury_or_recovery_status*

---

Generated 2026-09-12.
