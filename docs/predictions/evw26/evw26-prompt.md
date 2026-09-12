# EVW26 prediction prompt

Paste the text below into the model.

**Attach `evw26-dataset.md` before sending the prompt, not later.** On a first
run where the file was only promised rather than attached, the model completed
Phase 1 and then correctly refused to invent Phase 2, wasting the run. Confirm
the upload has actually landed in the conversation first.

---

You are forecasting the results of an armwrestling event that has not yet been
contested. Today is 12 September 2026. The event is East vs West 26, held today
in Jiaxing, Zhejiang, China.

I want your best possible forecast for every match on the card, together with a
detailed technical account of the reasoning behind each one. Take the time this
needs. I would much rather you search extensively, think slowly and write at
length than return something quick and compressed.

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
| 7 | Rustam Babaiev | Eldar Bubenko | Left | 95 kg | Bo5 |
| 8 | Fia Reisek | Yrysty Orazkhan | Right | Women's lightweight world title | Bo7 |
| 9 | Joseph Meranto | Valen Low | Right | Featherweight | Bo5 |
| 10 | Kersten Mercieca | Tanapat Thammaya | Right | Welterweight | Bo5 |
| 11 | Ethan Lovei | Josh Nicholas | Right | Featherweight | Bo5 |
| 12 | Raimonds Liepins | Rui Jiale | Right | Welterweight | Bo5 |
| 13 | Zhuo Xiaohai | Joffey Jolly | Right | Lightweight | Bo5 |
| 14 | Matt Mask | Leonidas Arkona | Right | Heavyweight | Bo5 |

This card was assembled from secondary sources. Athlete name spellings,
nationalities and weight-class labels vary between those sources, and some list
athletes under alternative names. Verify the card as part of your research and
tell me about any discrepancy you find, but produce a forecast for the card as
listed above.

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
- Results tables and rankings are the easiest thing to find, and they are not
  sufficient on their own. Also seek out material that describes how these
  athletes actually compete: technique breakdowns, coaching content, training
  footage discussion, podcasts, interviews, match analysis, and anything that
  reports physical attributes or measurements. If you cannot find that for an
  athlete, say so explicitly rather than filling the gap with record-based
  inference and leaving it unmarked.

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

## Length

There is no length limit, and I am not looking for a summary. Be as long,
technical and detailed as the analysis genuinely warrants. A single match may
justify several hundred words. I would far rather read fifteen thousand words
of real analysis than two thousand words of compression. Do not trim, do not
prioritise readability over completeness, and do not stop early because the
answer is getting long.

## Attribution

Every substantive claim needs its origin marked.

- When a claim comes from something you found, give the URL inline, next to the
  claim it supports. Not a bibliography at the end - I need to see which
  specific source backs which specific claim.
- When a claim comes from your own prior knowledge rather than from something
  you retrieved in this session, tag it `<INTERNAL KNOWLEDGE>`. Do this even
  when you are confident it is correct.
- When you are inferring rather than reporting - reasoning from other facts to
  something no source states - say so.

I am using this to find out where the available information runs out, so
unmarked claims are worse than useless to me.

## What to output

For each of the fourteen matches:

1. **Winner.** The athlete you expect to win. This is the primary output.
2. **Probability.** How likely that athlete is to win, as a percentage. State
   the number you actually believe. Do not round toward 50% out of caution, and
   do not inflate toward certainty.
3. **Score.** The round score you expect, in the match's format. Secondary to
   the winner, but give one for every match.
4. **Evidence.** What you found that bears on this match, with sources.
5. **Factors and their interplay.** Described below. This is the part I care
   most about.
6. **What would flip it.** The condition or conditions under which the other
   athlete wins instead. Be specific about what would have to occur.
7. **What you would want to know.** The attributes, measurements or facts about
   these two athletes that would most improve this prediction, and that you
   could not find or do not have. List them even where you have no way to
   obtain them.

### On factors and their interplay

Name **every** factor you are actually using. If eight things bear on a match,
name all eight. Do not compress to the two or three most presentable - the
ones you would normally drop are the ones I most want to see. If a factor is
influencing your probability, it goes in the list, including factors you hold
with low confidence.

Then describe how they interact. Not a list of independent considerations, but
the actual structure: which factor dominates and under what conditions, which
ones cancel or offset each other, which only matter if another one is present,
which compound, and in what order they come into play as a match progresses.
An explanation that names factors but leaves them sitting side by side has not
answered the question.

Include the physical mechanism. Describe what you expect to physically happen
between these two competitors - the sequence, and why the attributes of each
athlete produce that sequence rather than a different one. "A is stronger" is
not a mechanism. What happens, in what order, and why does it follow from what
each athlete brings to the table?

Do not force any of this into a common template. Different matches turn on
entirely different things, and the factors that matter for one may be
irrelevant to the next. The set of factors, their names, and the structure of
the explanation should differ from match to match wherever the matches
genuinely differ. If a match hinges on something that applies to no other match
on the card, that is exactly what I want to see. Invent whatever vocabulary you
need; do not restrict yourself to terminology you think I already use.

If you are largely guessing on a match, say so plainly and say what you are
guessing about, rather than constructing a rationale to fill the space.

## Finally

Close with whatever you noticed across the card as a whole. Include, in
particular, anything you found yourself reasoning about repeatedly across
multiple matches, and anything you believe matters in this sport that you had
no way to assess from the information available to you.
