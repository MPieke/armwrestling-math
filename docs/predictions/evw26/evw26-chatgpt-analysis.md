<!--
Provenance: written by ChatGPT after East vs West 26 had been contested, from
the four final forecast files plus the actual results. Reproduced verbatim as
supplied. Because the author had the outcomes while writing, its lessons are
hypotheses fitted to one event, not validated findings. See
evw26-retrospective.md for the surrounding discussion.
-->

# What LLM Forecasts of East vs West 26 Reveal About Armwrestling Prediction

## Introduction

The purpose of this experiment was not simply to test whether large language models could guess the winners of East vs West 26. The more useful question was whether internet-enabled LLMs could identify the information that actually matters for predicting armwrestling matches, combine that information coherently, recognize when the available evidence was weak or contradictory, and assign sensible confidence to their conclusions.

Four forecasts were produced: ChatGPT without the supplied historical dataset, ChatGPT with the dataset, Claude without the dataset, and Claude with the dataset. Each forecast covered the same 14 East vs West 26 matches and attempted to provide not only a winner and probability but also the factors and physical mechanisms believed to determine the match.

The results therefore provide two kinds of evidence. The first is ordinary predictive evidence: which winners were called correctly. The second, and more important for future work, is evidence about the **forecasting process itself**. Across the four runs, the models repeatedly exposed what information they considered important, where they lacked information, how they resolved conflicts between evidence types, and how plausible-sounding reasoning could sometimes increase confidence without improving prediction quality.

A methodological caveat is important. This was not a perfectly controlled four-cell experiment. One response independently located dataset-related material during its research process, while another dataset-enabled run reported that it hit a tool limit and could read all match results but only part of the associated commentary. Consequently, differences between “dataset” and “no dataset” conditions should not be interpreted as clean causal effects. The more robust analysis is to examine the reasoning patterns that recur across the four forecasts.

## Overall predictive performance

Taking the four files in the order of the experimental conditions, the reported final winner forecasts produced scores of approximately **8/14, 9/14, 9/14 and 7/14**, or 33 correct forecasts out of 56 individual predictions.

Those numbers are useful context, but they hide the more interesting result: agreement between the models did not behave like four independent expert votes.

Across the 14 matches there were seven unanimous 4–0 predictions, five 3–1 majorities, and two 2–2 splits.

| Consensus     | Matches | Majority correctly predicted |
| ------------- | ------: | ---------------------------: |
| 4–0 unanimous |       7 |                **4/7 (57%)** |
| 3–1 majority  |       5 |                **4/5 (80%)** |
| 2–2 split     |       2 |                  No majority |

The unanimous matches were Riekerd Bornman–Filip Larsson, Artur Makarov–Oleg Cherkasov, Barbora Bajčiová–Marta Volkova, Rustam Babaiev–Eldar Bubenko, Joseph Meranto–Valen Low, Kersten Mercieca–Tanapat Thammaya, and Ethan Lovei–Josh Nicholas. The models were unanimously correct on Bornman, Bajčiová, Meranto and Lovei, but unanimously wrong on Makarov, Bubenko and Tanapat. The four source tables show the forecast sets directly.
This immediately weakens a simple interpretation of consensus. Agreement was sometimes a sign that the evidence was strong, but it could also mean that all four LLM runs were exposed to the **same misleading public evidence and made the same inference from it**. Consensus among LLM runs using overlapping internet sources is therefore not equivalent to consensus among genuinely independent forecasters.

The 3–1 cases actually performed better. The majority correctly selected Devon Larratt, Bogdan Stoica, Raimonds Liepins and Zhuo Xiaohai, while three of four incorrectly selected John Brzenk over Zhao Zi Rui.

The two genuine 2–2 matches were Fia Reisek–Yrysty Orazkhan and Matt Mask–Leonidas Arkona. Both are important because the disagreement reflected genuine conflicts between plausible evidence rather than obviously poor research.

The major lesson is therefore not that consensus is useless. It is that **the cause of consensus matters**. Consensus based on several independent forms of strong evidence should be treated differently from consensus produced because every model found the same sparse databases and repeated the same inferential shortcut.

---

# 1. What information did the models use?

Across the four runs, the evidence can be organized into six broad feature families.

## Competitive-level features

The most common inputs were recent wins and losses, opponent quality, same-arm results, championship results, rankings, direct head-to-heads, common opponents, activity level and time since the athlete last competed.

These are the closest thing armwrestling currently has to conventional sports statistics. They were also generally the most defensible information available.

Recent, arm-specific, internationally comparable results appeared particularly useful. Riekerd Bornman is a good example. One forecast emphasized his recent sequence of wins over increasingly strong and stylistically varied opposition and treated this as stronger evidence than isolated physical measurements or reputation. All four models selected Bornman and he won 3–0.

Joseph Meranto was another relatively straightforward level-based success. The reasoning relied heavily on his stronger recent professional sample and treated the lack of detailed technical information as a reason **not** to invent a highly specific mechanical explanation. All four selected Meranto and he won 3–1.

This suggests that a future predictive model should start from a robust estimate of **current competitive level**, especially using same-arm, similar-weight, recent results against opponent-adjusted competition.

However, raw win/loss data are not sufficient. The forecasts repeatedly recognized that armwrestling is highly non-transitive. A beats B and B beats C does not reliably imply A beats C because the styles that produced those results can be completely different. One forecast explicitly identified common-opponent transitivity as one of its most frequently used but weakest tools.

A future model therefore needs opponent-adjusted results **plus matchup context**, rather than treating the sport as a simple ranking ladder.

---

## Mechanical and stylistic features

The forecasts spent substantial effort reasoning about hook versus toproll, cup, pronation, rise, wrist containment, backpressure, side pressure, shoulder connection, first-hit explosiveness and endurance.

This was often the most impressive part of the outputs because it attempted to explain *why* one athlete should beat another rather than simply reporting records.

It was also one of the most dangerous parts.

The key problem is that the public data generally do not contain standardized measurements of these attributes. A model might know that an athlete is described as having a “strong hand” or “great side pressure,” but it usually does not know how much force the athlete produces, at what joint angle, on which arm, how rapidly the force can be produced, or how that value compares quantitatively with the opponent.

The models therefore inferred latent mechanical characteristics from match footage, commentary and past outcomes.

Sometimes this worked. Sometimes it produced extremely coherent but incorrect stories.

The difference between those outcomes is central to improving future prediction.

---

## Physical and physiological features

Age, height, bodyweight, forearm size, wrist circumference, biceps measurement, leverage, weight cuts and injury history appeared repeatedly.

These features are potentially important, but the experiment shows why they should rarely be used in isolation.

Age was repeatedly used as a proxy for declining start speed, recovery or endurance. Yet Rustam Babaiev, whose age was repeatedly treated as a major disadvantage against the younger Bubenko, won 3–0.

Mass was heavily discussed in Matt Mask–Leonidas Arkona. One forecast highlighted an almost 12 kg event-day weight difference and reasoned that this would become increasingly important if Leonidas successfully caught Matt's hit and converted the match into a connected static contest. Matt nevertheless won 3–0.

This does not imply that age or mass are irrelevant. It means they must be **conditional variables**. Mass matters if it can be mechanically connected to the table position. Age matters insofar as it affects the specific abilities the athlete depends on.

A useful future feature is therefore not simply:

> age = 44

but something closer to:

> age-related decline risk × reliance on first-hit speed

Likewise, bodyweight should interact with style:

> bodyweight advantage × ability to establish a connected inside position.

---

## Match-context features

The models considered Bo5 versus Bo7, tournament versus supermatch format, strap behavior, fouls, replacement opponents, refereeing, weight cuts and sometimes travel or home-region effects.

Format was particularly interesting.

The Fia Reisek–Yrysty Orazkhan match contained unusually strong evidence against Fia: Orazkhan had a direct same-arm, same-class tournament victory over her. One forecast described that as the single strongest individual piece of evidence in the matchup.

The counterargument was that Fia had much more evidence of repeatedly solving opponents in long professional supermatches. The pro-Fia forecasts reasoned that a tournament final asks whether Orazkhan can beat Fia once under those conditions, whereas a Bo7 asks whether she can reproduce that favorable position repeatedly after Fia has seen and adapted to it.

The four predictions split 2–2. Fia then won 4–1.

It would be wrong to conclude from one result that Bo7 experience “beats” direct H2H. The more useful conclusion is that **format is a legitimate interaction feature** and historical matches should be tagged by format rather than pooled indiscriminately.

---

## Information-quality features

A major strength of the forecasts was that they often explicitly recognized missing or poor-quality information.

Examples included old data, contradictory databases, athlete measurements that might be stale, limited current footage, results from different arms, secondary-source rankings and commentary whose claims had not been independently verified.

The dataset itself was treated cautiously in some runs because its commentary consisted of commentator speech, machine-extracted and machine-labelled rather than measured biomechanics.

This distinction needs to become an explicit part of future prediction.

A result, a measured strength value, a commentator description, an athlete self-assessment and an LLM inference should **not enter the model with equal evidentiary weight**.

Every feature should ideally carry metadata such as:

**source type, date, arm, weight class, directness, reliability and uncertainty.**

Information quality should itself be a feature.

---

## Market information

One run also recorded pre-event betting-market probabilities, explicitly treating them as a calibration reference rather than a mechanical explanation.

Using the event results provided afterward, the favorite indicated by those listed prices would have gone **11/14**, better than any individual LLM run.

That result should be treated cautiously. We do not know the liquidity, sophistication or independence of that market, and one event is far too small a sample to establish betting-market efficiency.

Nevertheless, it is one of the most important practical findings.

The market correctly leaned toward **Rustam Babaiev and Kersten Mercieca**, two matches in which all four LLM forecasts went the other way.

This suggests a useful future approach: use the market as an **external prior or ensemble feature**, while requiring the model to justify large deviations from it.

The LLM should not blindly copy odds. But if a model wants to move substantially away from the market, it should be able to identify genuinely new and matchup-specific evidence rather than simply constructing a persuasive narrative from familiar public information.

---

# 2. How the models combined information

The models did not simply count features. They constructed causal chains.

A typical successful chain looked like:

**recent results → estimate current level → identify matchup-relevant strength → infer first critical position → account for format → assign probability.**

A typical failure looked similar on the surface:

**single prior performance → infer stable technical trait → assume trait transfers to new opponent → construct detailed mechanism → become more confident.**

The second chain is dangerous because every step can be individually plausible while the complete argument is unsupported.

This was particularly clear in Bubenko–Babaiev.

---

# 3. Bubenko–Babaiev: the clearest example of mechanism overfitting

All four forecasts selected Eldar Bubenko.

The predictions ranged from modest favorite to approximately 70%, yet Rustam Babaiev won 3–0.

The dataset-enabled reasoning was especially detailed. Bubenko had previously been described using a toproll, wrist control, backward movement and wrist flexion to prevent Logan Bittinger from entering a hook. Babaiev, meanwhile, had recently used an outside lane that commentators considered less natural for him. The model combined these observations into a coherent matchup thesis: Bubenko's hand-control game would deny Babaiev the position he needed for his hook.

This is sophisticated reasoning.

It was also badly wrong.

The likely reasoning error was not necessarily misunderstanding what Bubenko did against Bittinger. The error was assuming that success using that mechanism against one opponent demonstrated sufficient **magnitude** of the relevant strength to reproduce it against Babaiev.

A technique is not a scalar advantage.

Knowing that Bubenko can execute wrist flexion plus backpressure tells us what he attempts. It does not tell us whether his wrist flexion is strong enough to control Babaiev's cup, whether his first movement is fast enough, whether his fingers survive Babaiev's contact, or how the grip setup alters the exchange.

This suggests a crucial feature-design principle:

> Technique labels should describe **direction of force and preferred movement**, not substitute for measurements of how strong that movement is.

“Toproller versus hooker” is insufficient.

A future dataset should attempt to capture both **technique** and **capacity**.

This match also warns against overusing generic age assumptions. Babaiev's age was repeatedly treated as a liability because his historical game depended on speed. But age cannot substitute for current reaction-time or force-production measurements.

The appropriate feature is not “older athlete.” It is “measured or recently observed reduction in the specific physical property required by his style.”

---

# 4. Makarov–Cherkasov: duplication and false confidence

All four forecasts selected Artur Makarov. Oleg Cherkasov won 4–3.

This case differs from Babaiev–Bubenko because the actual result was extremely close. Picking Makarov was therefore not inherently unreasonable.

The problem is the **confidence progression**.

Two forecasts were near coin-flip territory around 54%. Other runs placed Makarov near 78–80%.

One dataset-enabled forecast explicitly stated that the dataset added almost no new information. It merely reproduced Makarov's already-known 4–0 win over Tarasaitis. Nevertheless, the model increased Makarov from 79% to 80% because the dataset independently agreed with the previously retrieved result.

This is an important reasoning flaw.

The same underlying match result appearing in two sources is not equivalent to two independent pieces of predictive evidence.

The distinction needed here is between **source corroboration** and **evidence multiplication**.

Corroboration can increase confidence that a historical fact is recorded correctly.

It should not substantially increase confidence that the fact predicts a different future matchup.

The forecasts also tended to emphasize Makarov's modern supermatch activity and repeated Bo7 success while discounting Cherkasov's elite historical pedigree and potentially relevant head-to-head/tournament evidence. One analysis explicitly recognized Cherkasov's world-class credentials but preferred recent activity and modern long-format evidence.

The lesson is not that historical pedigree should always beat recent form. It is that **recency needs to be balanced against opponent-specific evidence**, particularly when the supposedly inactive athlete has previously demonstrated an elite ceiling.

A future model should therefore distinguish:

**fact confidence** — are we sure this result happened?

from

**predictive weight** — how much should this result change the current matchup probability?

---

# 5. Tanapat–Mercieca: the regional-level translation problem

All four forecasts ultimately selected Tanapat Thammaya. Kersten Mercieca won 3–0.

This is one of the strongest examples of sparse-data consensus.

The forecasts repeatedly acknowledged that high-quality current technical information on Tanapat was poor. His evidence consisted largely of junior achievements, Southeast Asian standing, youth/development potential and regional rankings. Mercieca had more conventionally comparable European senior evidence.

In one run, the initial prediction was actually Kersten at 54%. A later ranking check found Tanapat listed as the current 85 kg Southeast Asian champion, which was enough to flip the forecast to Tanapat 55%. Importantly, that run explicitly said the actual dataset contributed nothing useful; the flip came from later external verification.

This is revealing because the logic was not irrational. The model had an almost even prior and discovered fresher evidence that Tanapat had progressed.

The weak link was the **conversion from regional success to East vs West competitive level**.

The four forecasts had no reliable calibration function for questions such as:

> How much is a current Southeast Asian championship worth relative to seventh place at a European senior championship?

The models answered that implicitly.

They should have treated it explicitly as an unresolved parameter.

The result suggests that future prediction data need some form of **cross-ecosystem competition strength**. A regional title should not be entered as a generic “champion = strong” feature. Its predictive value depends on the depth and quality of the field.

This same issue appeared with Zhao Zi Rui, Rui Jiale, Zhuo Xiaohai, Joffey Jolly and Josh Nicholas. One forecast explicitly identified the China/Southeast Asia level question as a recurring weakness across the card.

---

# 6. Bogdan–Irakli: when new information overturns the prior

Three forecasts ultimately selected Bogdan Stoica and one selected Irakli Zirakashvili. Bogdan won 4–3.

The dissenting forecast is particularly informative because it began with Bogdan 53% and then **flipped to Irakli 55% after reading additional technical material**.

The new evidence described Irakli as quick but controlled, able to gain an early hand advantage without sacrificing wrist position and capable of pacing his effort. The same run also found commentary suggesting that Bogdan had difficulty entering his preferred hook when faced with a very strong wrist/hand. The model concluded that Irakli might deny Bogdan access to the side-pressure position on which the original prediction depended.

Bogdan ultimately won, but 4–3.

This should not be classified as a catastrophic reasoning failure.

The update identified a genuinely relevant mechanism and moved the probability only slightly across 50%. The final result itself was extremely close.

The important future lesson is that prediction evaluation should distinguish between:

**wrong side of a genuine 50–50 match**

and

**high-confidence structural error.**

Bogdan–Irakli is closer to the first category. Bubenko–Babaiev is closer to the second.

For feature engineering, the Bogdan match supports retaining detailed hand-entry and positioning information. What needs improvement is the estimation of **how large** the advantage is and whether performance against one opponent transfers to another.

---

# 7. Fia–Orazkhan: useful disagreement

The predictions split 2–2.

This is arguably what healthy model disagreement should look like.

The pro-Orazkhan argument had unusually direct evidence: she had already defeated Fia in a same-arm, same-class championship setting.

The pro-Fia argument had strong format-specific evidence: repeated professional supermatch dominance and a documented ability to continue generating side pressure and power from imperfect positions. One dataset-enhanced forecast explicitly argued that this provided a mechanism through which a Bo7 EvW match might differ from the previous tournament result.

Fia won 4–1.

The useful conclusion is not that direct H2H should be downweighted. It remains one of the best available features.

Instead, H2H should be contextualized by:

**date, arm, weight, tournament/supermatch format, strap conditions, number of rounds and athlete development since the previous match.**

The disagreement here was informative because it exposed the unresolved variable rather than hiding it.

That is the behavior a future prediction system should encourage.

---

# 8. John–Zhao: abundant information on one side, sparse information on the other

Three forecasts selected John Brzenk. One selected Zhao Zi Rui. Zhao won 3–0.

This matchup exposed a different kind of information asymmetry.

John had a massive body of internationally visible information but significant age and current-condition uncertainty. Zhao had less internationally comparable recent material, but potentially strong current domestic level.

One run explicitly described the forecast as having unusually wide error bars because recent Zhao information was sparse.

Other analysis relied on old international results, Chinese domestic success, reputation, age, arm preference and John's recent physical condition.

The models therefore faced a common forecasting trap:

> The athlete we know more about feels easier to model.

But **information availability is not athlete strength**.

A future model needs an explicit missingness penalty. When one athlete has substantially less available data, the result should be wider uncertainty, not an implicit bias toward the athlete with a richer Western/international record.

---

# 9. Matt–Arkona: why a pre-match coin flip can end 3–0

The four forecasts split 2–2. Matt Mask won 3–0.

The main conflict was clear.

Mask had height, reach, technical experience and first-hit speed. Arkona had much greater mass, youth and static-strength potential. The matchup was repeatedly framed around whether Mask could create hand separation before Arkona established a closed, connected position.

This was sensible reasoning.

The 3–0 outcome does not prove the match should have been predicted as overwhelmingly one-sided.

Armwrestling can repeatedly reproduce the same positional advantage. If athlete A wins the decisive first-contact interaction, three rounds can look dominant even when there was substantial uncertainty beforehand about which athlete would win that interaction.

This is another reason not to infer pre-match predictability from final score alone.

It also suggests that future prediction should model not only match-winning probability but the probability of winning the **decisive first state** of the match.

---

# 10. Successful feature combinations

The experiment also produced several cases where the reasoning seems more robust.

Riekerd Bornman's unanimous prediction was grounded primarily in strong, current results against varied elite opponents rather than one narrow technical claim. That broad base appears preferable to extrapolating heavily from a single stylistic example.

Barbora Bajčiová combined proven professional openweight results, a very large physical frame and repeated long-match experience. The uncertainty surrounding Volkova was acknowledged rather than converted into a highly specific invented matchup.

Joseph Meranto's prediction was similarly level/form based, with the forecast explicitly admitting that it lacked enough technical information for a high-resolution mechanical story.

Ethan Lovei was favored largely because his recent senior and international evidence was fresher and more comparable than Josh Nicholas's older youth evidence, while the models still recognized that Josh's lack of recent public data increased uncertainty.

These successes suggest that **broad, current, comparable evidence may be more robust than a narrow but detailed mechanical narrative**.

---

# 11. Confidence: some signal, substantial overconfidence risk

Pooling the 56 final forecasts gives a weak but real relationship between stated confidence and correctness.

| Stated probability | Forecasts |         Correct |
| ------------------ | --------: | --------------: |
| 50–59%             |        26 | **11/26 (42%)** |
| 60–69%             |        20 | **15/20 (75%)** |
| 70%+               |        10 |  **7/10 (70%)** |

The average stated confidence on correct forecasts was about **63.6%**, compared with about **59.7%** on incorrect forecasts.

So confidence was not meaningless.

But the sample is tiny, the observations are correlated by match, and the confidence estimates were clearly not calibrated enough to treat these bins as stable probabilities.

The more important finding is qualitative.

Some of the worst errors became more confident when richer explanatory data were available.

Makarov reached 78–80% in some runs and lost.

Bubenko reached 70% and lost 0–3.

Tanapat was unanimously selected despite multiple forecasts acknowledging severe information limitations.

This suggests that LLM confidence can increase when the model can produce a **more detailed story**, even if the new detail does not materially improve comparative evidence.

Future confidence estimation therefore needs to distinguish:

**explanatory richness** from **evidentiary strength**.

---

# 12. The main reasoning holes

The largest failures can be summarized as failures of representation rather than simple lack of intelligence.

The models often knew *what* might matter but did not possess the features required to quantify it.

They knew cup and pronation matter, but not the athletes' cup and pronation strength.

They knew reaction time matters, but had no reaction-time measurement.

They knew injury matters, but often had only a binary historical mention rather than current functional impairment.

They knew style interaction matters, but relied on coarse labels such as hooker or toproller.

They knew regional competition quality matters, but lacked cross-region calibration.

They knew bodyweight matters, but could not quantify when that mass could actually be connected to the relevant table position.

The forecasts themselves repeatedly identified these gaps. One summarized the missing variables as hand dimensions, rise/cup/pronation/backpressure, side pressure, reaction latency, elbow range of motion, current bodyweight, preferred start path and fatigue across repeated maximal efforts. Another emphasized referee grip, strap rules, travel, pad geometry and unreliable listed bodyweights as important but unavailable contextual variables.

These are not minor missing details. They are much closer to the physical causes of match outcomes than many of the proxies currently being used.

---

# 13. Features that should be collected for future prediction

The next generation of prediction data should move away from simply accumulating more unstructured commentary and toward standardized athlete and matchup features.

A useful dataset would contain four layers.

### Competitive level

Results should be arm-specific, weight-specific and time-stamped. Opponent strength should be estimated so that beating a strong athlete contributes more than beating a weak one. Tournament and supermatch results should be separated. Recency should be modeled rather than handled informally.

### Mechanical profile

Each athlete should ideally have measurements or structured ratings for cup, rise, pronation, supination, backpressure, side pressure, finger containment, press strength, start speed and endurance.

Even imperfect standardized measurements would be more useful than repeatedly inferring these attributes from commentator adjectives.

### Current condition

Injury should be recorded by movement and severity rather than as a yes/no flag. Current bodyweight, weigh-in weight, rehydrated weight, recent training emphasis, time since last competition and dominant-arm preparation should be included where possible.

### Match-context and evidence quality

Bo5/Bo7, tournament/supermatch, expected strap behavior, foul frequency, replacement status, travel, referee tendencies and grip setup should be considered.

Every observation should also include provenance and reliability.

A commentator saying “iron wrist” is information.

A measured wrist-flexion value is different information.

The model should know the difference.

---

# 14. The feature interactions are more important than isolated features

Perhaps the strongest lesson from the experiment is that many useful armwrestling features are **conditional**.

Age alone is weak.

Age × reliance on first-hit explosiveness is more meaningful.

Weight alone is weak.

Weight × ability to establish a connected static position is more meaningful.

Hook versus toproll is too coarse.

Cup strength × opponent pronation/rise × start timing is closer to the real matchup.

Injury alone is ambiguous.

Injury × affected force vector × athlete's preferred technique is useful.

Bo7 alone says little.

Bo7 × adaptation ability × endurance profile × style is more predictive.

Direct H2H is strong.

Direct H2H × recency × same arm × same weight × same format is stronger.

The future model should therefore be built around **interactions and mechanisms**, not a flat list of athlete attributes.

---

# 15. A better prediction process

The findings suggest a more disciplined forecasting architecture.

The first stage should estimate **baseline current level** using recent, arm-specific, opponent-adjusted results.

The second should assess **evidence quality and missingness**. A matchup with poor data should begin with wider uncertainty.

The third should construct a mechanical profile of each athlete using measured data where available and structured observations where not.

The fourth should identify the critical matchup interaction: what happens at first contact, and which athlete's preferred force vector attacks the other's weakest structure?

The fifth should adjust for match context: format, strap likelihood, fouls, weight, injury, replacement status and similar factors.

The sixth should compare the resulting estimate with an external prior such as the betting market. A substantial deviation should require substantial independent evidence.

Finally, the system should preserve multiple competing hypotheses rather than immediately collapsing them into one narrative.

For example:

> Scenario A: Irakli wins the hand before Bogdan connects his shoulder.
> Scenario B: Bogdan contains the hand and forces the inside match.
> Current evidence does not strongly resolve which first state occurs.

That representation is more useful than producing a polished deterministic explanation for whichever athlete the model happens to put at 55%.

---

# 16. Match-by-match summary

| Match           | Cross-run consensus | Result   | Main forecasting lesson                                                                                                                   |
| --------------- | ------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Devon–Ivan      | 3–1 Devon           | Devon    | Strong current level could overcome a plausible stylistic threat; one run may have over-weighted arm/style assumptions.                   |
| Bogdan–Irakli   | 3–1 Bogdan          | Bogdan   | Additional hand-control evidence produced a defensible but ultimately wrong 53→55 flip; good example of genuine near-coin-flip reasoning. |
| John–Zhao       | 3–1 John            | Zhao     | Severe information asymmetry and poor China-to-international calibration.                                                                 |
| Riekerd–Filip   | 4–0 Riekerd         | Riekerd  | Strong recent opponent-adjusted form appears robust; broad evidence outperformed narrow narrative.                                        |
| Artur–Oleg      | 4–0 Artur           | Oleg     | Recent activity and duplicated evidence created excess confidence; historical elite ceiling was underweighted.                            |
| Barbora–Marta   | 4–0 Barbora         | Barbora  | Proven current professional level plus physical advantages produced a strong, stable forecast.                                            |
| Rustam–Eldar    | 4–0 Eldar           | Rustam   | Clearest mechanism-overfitting failure; style descriptions were treated as strength measurements.                                         |
| Fia–Yrysty      | 2–2                 | Fia      | Healthy disagreement between direct H2H and supermatch/format-specific evidence.                                                          |
| Joseph–Valen    | 4–0 Joseph          | Joseph   | Current comparable professional evidence worked well despite limited technical detail.                                                    |
| Kersten–Tanapat | 4–0 Tanapat         | Kersten  | Regional-ranking translation failure; unanimity emerged despite acknowledged weak data.                                                   |
| Ethan–Josh      | 4–0 Ethan           | Ethan    | Fresh senior/international evidence seems more reliable than older youth pedigree alone.                                                  |
| Raimonds–Rui    | 3–1 Raimonds        | Raimonds | One fresh regional/open result was potentially overweighted relative to a deeper established résumé.                                      |
| Zhuo–Jolly      | 3–1 Zhuo            | Zhuo     | Sparse technical information but majority weighting of current domestic standing happened to work.                                        |
| Matt–Arkona     | 2–2                 | Matt     | Genuine opposing feature profiles; uncertain first-contact matchup can still produce a 3–0 result.                                        |

---

# Conclusion

The most important result of the experiment is not the percentage of winners each LLM predicted correctly.

The models were already reasonably good at finding public results, identifying likely styles and constructing plausible physical explanations. Their main limitation was that the publicly available data forced them to infer the variables that actually determine armwrestling matches from weak proxies.

The largest errors occurred when those inferences became too specific.

Bubenko–Babaiev shows that a detailed mechanical story can be completely wrong if technique is confused with the magnitude of the underlying physical ability.

Makarov–Cherkasov shows that repeated confirmation of an already-known result can create false confidence without creating new predictive information.

Tanapat–Mercieca shows that regional rankings require explicit strength-of-field calibration.

John–Zhao shows that information availability itself can bias prediction.

Fia–Orazkhan shows that disagreement can be healthy when genuinely strong forms of evidence conflict.

The successes point in the opposite direction. Forecasts were generally more robust when they rested on broad, recent, same-arm and internationally comparable competitive evidence and when the models resisted inventing technical precision they did not actually possess.

The clearest route to better future prediction is therefore not simply “give the LLM more information.” It is to give it **better structured information**.

Future work should prioritize current arm-specific strength measurements, opponent-adjusted competitive ratings, style-component measurements, start speed, endurance, injury-specific functional status, real bodyweights, strap/setup behavior, and evidence-quality metadata. Betting-market information may also be valuable as an external prior, particularly because the recorded market favorite in this event would have outperformed the individual LLM forecasts.

The fundamental forecasting problem can be summarized as follows:

**Existing data describe what happened. The LLMs then try to infer why it happened. Better prediction will require collecting more of the variables that describe why it happened directly.**

That is likely where the largest improvement in armwrestling forecasting will come from.
