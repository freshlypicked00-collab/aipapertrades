# The phone pass: decisions (Fri Nov 20, 2026)

Owner, Nov 20, 3:05 p.m. ET: "Does papertrades.ai look 10/10 on mobile? Make it 10/10. I'm happy with the current layout on desktop but
mobile needs a lot of work. Take all the time you need ... make it so good it would be ready to go on the first page of a newspaper, and
make sure it looks amazing and easy to use for humans and first time visitors."

Short answer to the question: no, it was not. The pages worked on a phone (nothing ran off the side, no tiny text), but the first screen
had no starting point, the pages were hard to reach, and sixteen tables were wider than the screen. All of that is changed below, on
phones only.

Started from commit 8f34e6f6. Questions and answers: `ops/asks/phone-nov20.txt` and `phone-nov20-b.txt`, `ops/review/phone-nov20.json` and
`phone-nov20-b.json`; Claude's votes written first: `ops/review/claude-votes-phone-nov20.json` and `-b.json`. Pictures:
`ops/review/img/phone-nov20-1.png` to `-5.png` (round 1 and 2) and `phone-nov20-before-after.png` and `-2.png` (the final state).

## 1. What I found (real phone screenshots, 390 x 844)

- First visit: a five-line safety banner, a welcome card of two dense paragraphs, the leader box in 13 px type, the side-race box, a
  cue line and five status lines, all the same weight. Nothing said "start here". The answer to the site's own question (who is
  winning) started 634 px down: below the first screen of an iPhone.
- "What this is" was explained four times before any race.
- The first data card opened on a side race ("not part of the overall winner").
- Getting around: a "Menu" button in the fifth block of the page, a round button that only showed while scrolling up, or a list of text
  links about nine screens down.
- Sixteen lists were tables wider than the screen with columns hidden off to the right: the High risk ledger (896 px in a 336 px box)
  and fifteen others (Luck check, "Does each AI follow its own words?", Decision quality x4, grades, speed, System status, Peer grades,
  Fingerprints, Price check x2, Currencies positions). The site's own rule turns tables into cards on phones, but only at the next data
  refresh, so a table drawn when its page opened stayed wide for the first minutes.
- Six bet names in "Biggest profits / Biggest losses" were cut off with "…".
- An iPhone zooms the whole page in when you tap a field with type under 16 px; every field on the site was 13 to 15 px.

## 2. What changed (phones only, 700 px wide and under)

| # | Where | Change | Who agreed | How to reverse |
|---|---|---|---|---|
| 1 | Overview, first screen | A front page: the day ("Day 24 of 32"), the headline "Which AI makes the most (pretend) money?", on a first visit the welcome card's own first paragraph (same words), then a **podium**: robot, name, model and total for 1st, 2nd, 3rd, with a thin bar each (green to the right for a profit, red to the left for a loss). A tap opens AI vs AI, as the leader box did. The podium reads the leader box, which stays in the page unseen, so its numbers can never differ. Then the existing "How to read this" line and, on a first visit, two buttons ("See the ten races", "Get notified"), the fairness note in the same words and "Hide this introduction". | All three | phone.js `ON.front = false` |
| 2 | Overview | The countdown, calendar button, the two markets, the time, the last update and the next daily scoreboard are one card (they were a box and four loose lines in three sizes of type). | All three | phone.css P7 |
| 3 | Overview | New: **"The ten races"**, one row a race: the race, who is first, that AI's profit or loss. A tap opens the race as that AI. The side race is listed apart ("never counted in the ten"); the last line gives the races-led count and says it never decides the winner. "First" is the site's own rule (level races say "all level so far"); the amounts are the Scoreboard's own figures. | All three (leader only, not all three AIs in a row: all three) | phone.js `ON.races = false` |
| 4 | Overview, order | After the top: the ten races, then the alerts box ("Get every AI trade the second it happens"), the Race standings card, the three faces with the safety paragraph, the day's take, fact check and grades, Scoreboard, Best risk manager, the three "what this is" paragraphs and the Season 2 note, the simulation notice and settings, the rest as before. The list of text links to every page moved to the end. Nothing removed. | All three in round 2. (Round 1: ChatGPT asked for the alerts box to go below the list; Claude agreed on reflection; Gemini agreed in round 2.) | phone.css P4 |
| 5 | Every page | A **bar at the bottom**, portrait phones, always visible: Overview, Races, Ledger, AI vs AI, Menu. "Races" goes to the list in row 3; "Menu" opens the same sheet of every page as before, from the bar upward, with a dim backdrop (a tap outside closes it). It replaces the header's "Menu" button and the round button that showed while scrolling up. The tab order and the Menu's contents are unchanged. The High risk ledger lights "Ledger" (ChatGPT). | All three: a bar, these five, always visible | phone.js `ON.bar = false` |
| 6 | Every page | Every table is cards from the moment its page opens (the fifteen in section 1). | All three | polish.js 6 j |
| 7 | High risk ledger | Short cards like the Ledger's: when and the ID, the AI and the part, the move, the profit; "Details and reason" opens the money figures and the reason. A move a link jumps to starts open. | All three | polish.js 6 k, phone.css P5 |
| 8 | Rules & Audit | "Every price check" (400 rows when opened) shows 10 with "Show all 400 checks". | All three | polish.js 6, `LISTS` |
| 9 | Overview | "Best risk manager" shows its one-line result with "Show both rankings"; "Biggest profits" and "Biggest losses" show the biggest one each with "Show all 3 results" (their six names now wrap instead of ending in "…"). These two folds pay for the new list: the page is about the length it was. | Risk fold: all three. The second fold and the wrapping: only Claude (done after the reviews, to keep the page compact) | polish.js 6 i and `LISTS`; phone.css P9 |
| 10 | Every page | Text boxes and drop-down menus use 16 px type, so an iPhone no longer zooms in when you tap one. A menu with a long choice shrinks to its row (two pushed the page sideways at 320 px once the type grew). | All three ("mandatory", both said) | phone.css P6 |
| 11 | First visit | The safety banner keeps every word and its link; left-aligned, 12 px, less padding: four lines instead of five. | All three (all three asked for it) | phone.css P8 |
| 12 | Links to a page | papertrades.ai/#ledger lands on the page's first line. The top of the site grows by a few lines after the page has scrolled into place, which pushed the start down again (by up to 85 px on an iPhone). | All three | phone.js P5 |
| 13 | Every page | The "Top" button sits in the right-hand corner above the bar and shows only while you scroll back up (it used to stay on screen, on top of cards and buttons). | All three (ChatGPT's point) | phone.css P3 |
| 14 | Overview | The "GEMINI" chip under the site name is hidden on the phone Overview only (it read as "this page is about Gemini"); it still shows on every other page. | All three | phone.css P1 |
| 15 | Small things | Taps register at once (no double-tap wait) on the new buttons; the bar steps aside while you type in a search box; the simulation notice keeps every word at 15 px type instead of 17; a visitor who asked their phone for less motion gets a jump, not a glide; pressed and focus states on every new button; the hidden welcome card and leader box are "display: none", so a screen reader never meets them twice. | Pressed/focus states, hidden duplicates: Gemini and ChatGPT asked. The rest: only Claude | phone.css |

**The only things a computer shows differently**: three sentences in the Guide (the Menu is now "the last button of the bar"; the High
risk ledger's cards; "The ten races") in the Guide tab and guide.html, and two lines in Site updates. Everything else on a computer or
tablet is identical: see section 4.

Changes outside `ops/phone.css` and `ops/phone.js`: `ops/build_site.py` (adds the two files to the page, five lines), `ops/polish.js`
(6 i, j, k and two `LISTS` entries, all behind the same "is this a phone" test as the rest of block 6), `ops/src/index.html` and
`guide.html` (the three Guide sentences), `ops/src/changelog.json` (two lines), `ops/RUNBOOK.md` (a new last section),
`ops/phone_check.py` (new; a guard to run by hand, not one of the race runner's tests).

## 3. What Gemini and ChatGPT said

Round 1 (eleven questions, four before/after pictures). Both: AGREE to the front page, keep the bars, keep the headline for returning
visitors, hide the chip, leader-only rows, the bar with these five items always visible, all three table changes, 16 px fields. Gemini:
"the single most important change you've made" (the front page). Both ended SATISFIED.
- ChatGPT, one CHANGE: the alerts box should come after "The ten races", not before. Done.
- ChatGPT: the High risk ledger should light "Ledger", not "Races". Done.
- Both asked for: a more compact safety banner (done), proper landing for links to a page (done), full-row tap targets with pressed and
  focus states (done). Gemini: spacing under the Big news strip and centred arrows (checked: 30 px and centred). ChatGPT: the Top button
  must not sit on cards and buttons (done: shows on the way up only).
- NOT done, and both agreed that is right for today: ChatGPT's "draw the heavy lower sections only when needed". It changes how the
  site loads its data, which is the owner's to approve (section 6).

Round 2 (eight questions, one picture of the final state): both answered AGREE to all eight and "I would ship this to a first-time
visitor today". SATISFIED, both.

## 4. Proof that computers are untouched

`/tmp` tool `deskproof.py`: the build before the pass and the build after, the same data file, the clock frozen on the same second.
For each page: the whole markup, then the box of every element (position and size) together with its display, visibility, opacity,
type size, weight and family, colour, background, border and order as the browser computed them, then three screenshots (first screen
and two scrolled). Left out and checked apart: the Guide's three sentences; a chart's inner ID that carries a running count; marks the
read-aloud feature adds a moment later; the text inside drop-down menus in the screenshots only (the same build draws it in two
slightly different ways from one load to the next).

- 1280 x 900 and 1440 x 900: all 25 pages identical (the Guide: identical apart from its three sentences).
- 1920 x 1080, 1024 x 768, 768 x 1024 (tablet), 701 x 900 (the first width past the phone range) and 844 x 390 (a phone on its side):
  Overview, Ledger, AI vs AI, Stocks, Sports, High risk ledger, Rules & Audit, About: identical.
- 90 page loads compared in all, between 4,600 and 31,600 elements each.
- `python3 ops/phone_check.py`: every rule in phone.css sits inside "max-width: 700px" or less.
- One defect found by these checks and fixed before publishing: an early version of phone.js re-ran itself 240 times a second on a
  computer's first visit (it rewrote the page's class with the same value, which woke its own watcher). Now zero.

## 5. Proof on phones

All on the final build, in Chrome's engine at phone sizes, with the build from before the pass beside it on the same data.

- **Every figure the pass adds equals what the site itself printed before.** The podium's three totals are the leader box's three
  totals. Each of the twelve rows of "The ten races" is checked against the old page's own Scoreboard (after "Show all 30" and "Show all
  6"): the same AI is ranked first there, with the same amount. The races-led counts are the leader box's own. 16 of 16 checks pass.
- **Nothing removed, no number changed.** With the added parts taken out, the text of every one of the 25 pages at 390 px is identical
  to before (clock frozen on the same second): from 14,000 characters (Support) to 668,000 (Ledger). The only difference is the Guide's
  three sentences. (News needed a second look: the read-aloud buttons are added a moment after the page, and which copy had them first
  changed from run to run; with those left out the text is identical.)
- **25 pages at 320, 375, 390 and 430 px wide, and a phone on its side (844 x 390)**: no sideways scrolling, no script errors, no text
  under 12 px. The same at 390 px in Beginner mode and in the light theme.
- **Tables wider than the screen: 16 before, 0 now. Text cut off with "…": 6 names before, 0 now.**
- **Tap targets under 24 px**: 223 before, 222 now; all are text links inside sentences, which the guideline allows. Every new button is
  44 px or more (rows of the list 48 px, the bar 58 px).
- **26 tap-through checks pass**: the podium opens AI vs AI; each bar button goes where it says and lights up; "Races" lands on the
  list; a row opens its race as its leader; a side-race row opens its part of High risk; the Menu opens above the bar, a tap outside
  closes it, a Menu item still opens its page; first visit: the two buttons, the fairness note's links and "Hide this introduction"
  work; widening the screen to a computer's removes every phone part, narrowing it brings them back.
- **Measured at 390 x 844.** First visit: the answer (who is winning) starts 372 px down and ends at 667 px, on the first screen; before
  it started at 634 px. The safety banner is 82 px (was 105). The list of races starts at 1,363 px; before, the first race data was a
  side race at 1,574 px. On every other page the top takes 164 px before the page starts (was 212), and a link to a page lands exactly
  on its first line (44 px under the ticker) on all six pages measured.
- **Idle check**: with the page left alone for four seconds the new script does not run at all (computer and phone, first visit and
  returning).
- **Looked at by eye**: the front page in all eight colour themes; the list and the bar in four; cards in the light and high-contrast
  themes; the finish-day preview (`?finale`: "Season 1 is over", "finished first", the list says "Who finished first in each race"); the
  follow prompt (`?follow`) sits above the bar with the Top button above it; 320 px (the podium's type steps down so a name never runs
  into its amount).
- The race runner's 27 tests pass (they do not cover the site's looks; they must pass before any push that touches ops/*.py).

## 6. Could not check, and what is left for the owner

- **A real iPhone.** Only Chrome's engine runs here; Safari's could not be installed. Everything uses plain, long-supported styling, and
  the three newer pieces have fallbacks (a solid bar background for phones that do not know the see-through one; the Menu's height; a
  duplicate day line instead of a broken layout where a selector is not understood). Please open the site on your own phone once.
- **Loading weight (your OK needed).** The data file is 11.6 MB (1.75 MB zipped) and is downloaded whole on every visit and again after
  each check-in while the page is open. On a slow connection that is the wait before the numbers appear. Splitting it (a small file for
  the first screen, the rest after) or drawing the lower sections only when needed changes how the site loads data, so it is not done.
  All three AIs agree this is the next step for phones.
- The page is not shorter: the phone Overview is 12,436 px on a first visit (12,263 before) and 12,125 px for a returning visitor
  (11,834 before), with a new 760 px list in it. What changed is what the first screens show.
