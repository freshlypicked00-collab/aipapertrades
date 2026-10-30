# Website and Nov 1: what all three AIs agreed (Oct 30, two rounds)

The owner asked, before going to sleep, for site improvements, future ideas and the Nov 1 announcement, built only where Claude, Gemini and ChatGPT all agree. Answers: ops/review/site-r1-oct30.json and site-r2-oct30.json. Claude's votes were saved before each round (claude-votes-site-oct30.json, claude-votes-site-r2-oct30.json). Snapshot and audit: site-snapshot-oct30.md.

## Agreed by all three (built Oct 30)
- W1. Status board: a price flag Claude confirmed wrong and corrected reads "corrected", not "Delayed". "Delayed" stays for a late check or an uncorrected error.
- W2. Chart library (d3 7.9.0): if cdnjs fails, the same version loads from jsDelivr.
- W3b. Compact phone header: on phones the New York and Hong Kong clocks, language, sound, colour theme and Beginner move into the Menu; the UTC clock stays on the first screen with "Day N of 32" and the countdown. Desktop unchanged. (Gemini's change: keep UTC.)
- W4b. Long pages on phones (Sports, AI pages, AI vs AI, Ledger days before today): later sections start collapsed with "Show more"; a section reached by a direct link opens by itself. Desktop unchanged. (ChatGPT's change: auto-open on direct links.)
- G1 (Gemini). Back-to-top button on phones after two screens of scrolling.
- P1 (ChatGPT). "View correction" link from a corrected price flag to the Corrections entry.
- P2 (ChatGPT). One row of jump chips on phone race pages: Holdings, Chart, Ledger, Rules.
- N1b. Nov 1 note, once on Telegram and as a one-line site note on Nov 1: "Clocks changed today. Each race day still closes at 00:00 UTC, which is now 7 p.m. ET (it was 8 p.m.). Nov 1 is Day 5 of 32. Every trade, bet, reason and correction stays public at papertrades.ai."

## Agreed as plans (not built yet)
- F2. After Nov 28: a Season 1 recap table per race (winner, final value, max drawdown, largest gain and loss, corrections count) and a download of the final Season 1 record.
- F3. Once the Season 2 rules are final: one static card comparing the Strict, Standard and Unrestricted rulebooks.

## Not agreed (dropped)
- F1, a "follow on Telegram" line under the Season 2 teaser: ChatGPT said no (belongs in the social round).
- G2, an AI filter on the Ledger: Claude, ChatGPT and Gemini itself said no (the Ledger already follows the AI picked in the Menu).
- G3, links from reasons to the Ledger: already built ("Ledger ›" on every holding row).
- P3, a "paper value, races separate" tooltip on every value: Claude, Gemini and ChatGPT itself said no (clutter; already stated on the pages).
