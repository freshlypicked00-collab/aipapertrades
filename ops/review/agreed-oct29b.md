# Improvements all three AIs agreed on (Oct 29, two rounds)

Gemini 3.1 Pro Preview and ChatGPT (GPT-5.5) answered in ops/review/review-r1-oct29b.json and review-r2-oct29b.json. Claude's round 2 votes were written first, in claude-votes-r2-oct29b.json. Every item below got YES from all three. The owner decides.

1. Closing odds for every AI's bets. Today only Claude's bets have them: 1 of 2, against 0 of Gemini's 24 and 0 of ChatGPT's 7. So "Beat the closing line" only scores Claude. Gemini and ChatGPT flagged a conflict. Medium.
2. Heavy-favourite transparency (no rule change). The Sports page shows each AI's average odds and how much of its wagering is at −1000 or shorter. Example: Gemini has C$25,000 on Notre Dame at −6500 to win about C$385. Small.
3. Nightly ledger fingerprint (SHA-256) on Rules & Audit, Telegram and X, so later edits can be detected. Small.
4. "Since your last visit" box for returning visitors, stored only in their own browser. Medium.
5. A slim price ticker that stays at the top on phones. Computers and tablets already have it. Small.
6. Faster first load on phones. About 0.4 MB is downloaded and 2 MB unpacked before numbers show. The Overview's data would load first and the rest on demand. Medium.
7. A link from each trim or partial sale under a holding to its Ledger entry. Small.
8. Benchmark toggle: click S&P 500, Bitcoin and the like in a chart legend to hide or show its line. Small.
9. Rename "Overall (All Ten Races)" to "Races led (no money totals until Nov 28)". Small.
10. Betting-minimum audit table: every wager counted toward the daily and total minimums, with date, amount and link. Medium.
11. Price freshness: feed, quote time and age on every valuation, plus a "stale" flag when a price is more than 30 minutes old in market hours. Claude flagged a conflict. Medium.
12. Until same-moment fills ship, a one-line note under each race chart saying Claude's trades fill 10 to 20 minutes after the others'. All three flagged a conflict. Small.

Still waiting on the owner from before: "option B" same-moment fills, which all three already agreed to.

Not agreed (dropped):
- P3, the heavy-favourite rule change: ChatGPT said no to changing rules mid-race.
- R1, the total invested across all ten races: all said no because it adds races together.
- R3, the betting-minimum status on the Scoreboard: Claude said no because the Scoreboard is for results and the Sports page has it.

Issues found in the review and fixed the same day:
- one Bitcoin benchmark for all three views
- Sports and All in pies
- unchecked fact-check wording
- US dollar price source
- trims listed under holdings
- ounces for spot metals
- race-day close time after Nov 1
- closing-line stat label
- "two All in side races" wording
