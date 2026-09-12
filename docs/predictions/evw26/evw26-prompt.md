# EVW26 prediction prompt

Paste the text below into the model, and supply `evw26-dataset.md` alongside it
(upload as a file, or paste it when the model reaches Phase 2).

---

You are forecasting the results of an armwrestling event that has not yet been
contested. Today is 12 September 2026. The event is East vs West 26, held today
in Jiaxing, Zhejiang, China.

I want your best possible forecast for every match on the card. Take the time
this needs. I would much rather you search extensively and think slowly than
return quickly.

## The card

Fourteen matches. Format is given as best-of-5 or best-of-7 (rounds won).

| # | Athlete A | Athlete B | Arm | Class / title | Format |
|---|-----------|-----------|-----|---------------|--------|
| 1 | Devon Larratt | Ivan Matyushenko | Left | Heavyweight | Bo5 |
| 2 | Bogdan Stoica | Irakli Zirakashvili | Right | Middleweight world title | Bo7 |
| 3 | John Brzenk | Zhao Zi Rui | Right | Middleweight | Bo5 |
| 4 | Riekerd Bornman | Filip Larsson | Right | Super heavyweight | Bo5 |
| 5 | Artur Makarov | Oleg Cherkasov | Right | Lightweight world title | Bo7 |
| 6 | Barbora Bajčiová | Marta Volkova | Right | Women's openweight world title | Bo7 |
| 7 | Rustam Babaiev | Maayan Shterengas | Left | Open | Bo5 |
| 8 | Fia Reisek | Yrysty Orazkhan | Right | Women's lightweight world title | Bo7 |
| 9 | Joseph Meranto | Valen Low | Right | Featherweight | Bo5 |
| 10 | Kersten Mercieca | Tanapat Thammaya | Right | Welterweight | Bo5 |
| 11 | Ethan Lovei | Josh Nicholas | Right | Featherweight | Bo5 |
| 12 | Raimonds Liepins | Rui Jiale | Right | Welterweight | Bo5 |
| 13 | Zhuo Xiaohai | Joffey Jolly | Right | Lightweight | Bo5 |
| 14 | Matt Mask | Leonidas Arkona | Right | Heavyweight | Bo5 |

This card was assembled from several secondary sources and may contain errors.
Sources disagreed about match 7: most listed Shterengas as Babaiev's opponent,
one listed Eldar Bubenko. Nationalities and weight-class labels also varied
between sources. Verify the card as part of your research and tell me about any
discrepancy you find, but still produce a forecast for the card as listed above.

## How to research

Use live web search, and use it heavily. Specific expectations:

- Iterate. Run many searches rather than few. If a search returns something
  interesting, follow it up with further searches rather than moving on.
- Go after niche and hard-to-find material, not just the obvious summaries.
  Smaller outlets, forums, federation and promotion pages, athlete and gym
  social accounts, results databases, foreign-language sources, and video
  descriptions are all in scope.
- When a source turns out to be useful, work through the whole of it rather
  than just the page you landed on. If page one of a results archive is useful,
  page two probably is as well. Keep going until the source is exhausted.
- Sources in languages other than English are welcome; translate as needed.
- Note where sources conflict, and say which you trust and why.

One restriction: **do not look up the results of East vs West 26 itself.** The
event is today and results may begin appearing while you work. If you encounter
one, stop reading it, exclude it, and tell me it happened. A forecast that has
seen the result is worthless to me.

## Procedure

Work in two phases and keep them separate in your output.

**Phase 1.** Research and forecast every match using whatever you can find
independently. Commit to a full set of predictions before looking at the dataset
I am supplying. Write these down.

**Phase 2.** Now read the supplied dataset (`evw26-dataset.md`). For each match,
state whether it changes your Phase 1 view, in which direction, and why. If it
contradicts what you found independently, say so and say which you believe.
Where it tells you nothing useful about a match, say that too. Then give your
final prediction.

The dataset is one input among many. It is small, covers only one promotion,
and its provenance is described inside the file. Weigh it as you judge
appropriate.

## What to output

For each of the fourteen matches:

1. **Winner.** The athlete you expect to win. This is the primary output.
2. **Probability.** How likely that athlete is to win, as a percentage. State
   the number you actually believe. Do not round toward 50% out of caution, and
   do not inflate toward certainty.
3. **Score.** The round score you expect, in the match's format. Secondary to
   the winner, but give one for every match.
4. **Reasoning.** Which factors you based the prediction on, and why you think
   the interplay between those factors produces this outcome.

On the reasoning: do not force it into a common template. Different matches may
turn on entirely different things, and the factors that matter for one may be
irrelevant to another. Use whatever concepts you actually think are doing the
work, at whatever length that match warrants. If a match hinges on something
that applies to no other match on the card, that is exactly what I want to see.
If you are largely guessing on a match, say so plainly rather than constructing
a rationale.

Finish with anything you noticed across the card as a whole, if there is
anything worth saying.
