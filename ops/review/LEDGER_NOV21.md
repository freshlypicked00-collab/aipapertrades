# The Ledger, one race at a time (Nov 21)

**Asked by the owner, Sat Nov 21, 7:32 p.m. ET**, with three pictures of the China stocks page (the Value over time chart, the
holdings pie and table):

> what if the ledger had this and u can select each race to view better ( also show like a view winner button next to models)
> to show whos winning too. make improvements to the ledger. and make sure it looks A1

**Who agreed.** The owner's own request; the design is Claude's. Gemini and ChatGPT could **not** be asked before it was built:
GitHub refused to start every run from 12:14 p.m. ET on Nov 21 (see the end of this note). The question is written and waiting
(`ops/asks/ledger-nov21.txt`, Claude's own vote first in `ops/review/claude-votes-ledger-nov21.json`). It goes out as soon as runs
start again, and whatever the two of them reject is changed or taken out.

## What changed

| # | Where | What | Where it lives |
|---|---|---|---|
| L1 | Ledger, top | **Pick a race.** Buttons on a computer, a menu on a phone: All races, then the ten races, each with that AI's profit so far in percent and a crown where it is first. "All races" is the Ledger as it was. A race swaps the ten race cards for that race: its own numbers (the same lines as its card), its Value over time chart, the pie, the "What <AI> holds now" table and a link to the race's page; every list on the page then shows only that race. Before: seven separate race menus, one per list, and no chart outside the report card. | ops/src/index.html: `#lg-race` and the script "The Ledger, one race at a time"; polish.css 40 |
| L2 | Every Value over time chart | Each AI's button also shows its profit in that race (the Race standings figures). | ops/src/index.html: `raceProfits()`, the chart's AI switch; polish.css 40 |
| L3 | Every Value over time chart | **👑 View who's winning: <AI>** next to the three AI buttons (one tap switches the site to the AI in first place); "👑 1st in this race" when you already view it. The Overview chart had it as "X is 1st · view"; race pages had only the crown. From the finish it says "View who finished first" (never "winner" or "won" before the final scoring). | ops/src/index.html, the chart's "who" line |
| L4 | Ledger, computers | **Every trade and bet fits the screen.** It was a ten-column table 1,604 px wide in a 1,142 px box on every computer: Profit, Return and the reason were off-screen behind a sideways scroll bar, and each row was as tall as the hidden reason. Now nine columns on one line and the reason on its own full-width line; on a small laptop (961 to 1179 px) the four money figures go on a second line, each with its name. Same cells, order and words. A highlighted move is one band across the row. | polish.css 41 a; one class (`lg-why-none`) in the list's draw |
| L5 | Under every chart, computers | **"What <AI> holds in <race> now" fits.** Its "Why" column was cut off for about one race in three (the owner's picture of the China page shows it). | polish.css 41 b |
| L6 | Phones | The picker is a menu, in A to Z order like every menu; the three AI buttons are two lines each (name, amount) and fit one row at 360 px. | polish.css 40 |
| — | Guide, Site updates | One sentence each in "Who's winning" and "Every trade and bet" (the Guide tab and guide.html); two lines in Site updates. | ops/src/index.html, guide.html, ops/src/changelog.json |

## What did not change

No rule, price, trade, bet, AI-written word or figure. The chart, the pie, the tables and the race's numbers in the new view are
the race pages' own parts pointed at the picked race; nothing is worked out a second way.

## Proof

- **Figures:** every tab's text was dumped before and after from the same data, at phone (375 px) and computer (1280 px) width,
  with the clock frozen. All 7,415 money and percent figures from before are still there. New: three per chart (the AI buttons'
  amounts) and ten on the Ledger (the picker's percents), all figures the site already showed elsewhere.
- **The race view against the race cards:** for all three AIs and all ten races (30 cases, phone and computer), the view's numbers
  equal the race card's, the chart's value equals the card's value, the picker's percent equals the card's, and the viewed AI's
  amount on its button equals the card's profit.
- **Layout:** no page, list or cell wider than its box at 1024, 1093, 1179, 1180, 1280 and 1536 px for all three AIs, "All races"
  and each of the ten races, up to six pages of the trade list each; no script errors.
- **Flows:** switching AI inside a race keeps the race; "View who's winning" switches the AI; leaving the Ledger and coming back
  keeps the view; a list's own menu changes that list only; "View original buy" from the race view still finds and highlights
  the trade; "All races" restores the page.
- **Race tests:** 28 of 28 pass.

## To reverse

- L1: remove `<section id="lg-race">` and the script block "The Ledger, one race at a time" from ops/src/index.html, and block 40
  from ops/polish.css.
- L2, L3: in the chart's "who" line, drop the `gx-ai-pl` amounts and put the leader button back under `if (el.id === 'perf-overview')`.
- L4, L5: delete block 41 from ops/polish.css.

## Left for later

- Tablets held upright (601 to 960 px) still scroll the trade list sideways.
- The High risk ledger has no picker like this (its page has its own charts). Question Q2 to the other two AIs.

## GitHub runs (not part of this work, but it blocks publishing it)

From 12:14 p.m. ET on Sat Nov 21 every run was refused before it started ("startup_failure", no jobs): the hourly Gemini and
ChatGPT check-ins, the posts, the site publish, the watchdog. Last good run: 11:22 a.m. ET. GitHub's status page showed no
incident; the repository is private (private repositories have a monthly limit on run minutes), so the likely cause is billing
(the minutes or the spending limit used up, or a failed payment). Only the owner can see or change that. Until it is fixed the
site stays on its 11:21 a.m. ET version and none of the above is live.
