# Recent moves on every race page (Nov 18)

Owner, Nov 18, 9:05 a.m. ET: "there should be recent moves like how high risk has on all no?"
He was right: the High risk page lists every move by all three AIs; the ten race pages only had a Decision log for the one AI being viewed.

Asked: Gemini and ChatGPT (`ops/asks/recent-moves-nov18.txt`, three pictures). Answers: `ops/review/recent-moves-nov18.json`.
Result: Claude and Gemini agreed; Gemini SATISFIED. ChatGPT could not answer: its OpenRouter credit was too low for a review (HTTP 402).

## Built
- A "Recent moves" card on each of the ten race pages, right before the Decision log (Claude and Gemini: Q1 a). The same list as on High risk, one shared piece of code: AI menu, Show, Sort, "Why (estimated)", transaction IDs, competitors' grades, Looking back.
- 5 moves a page on computers and tablets, 3 on phones (Q2). Gemini's change: the High risk list uses the same numbers (it showed 10).
- Phones: the card starts folded to its title and one-line note with "Show more" (Gemini's change, Q3; Claude had built it open). A "Moves" chip in the jump row opens it (Q4).
- Gemini's Q7: the "Holding now" pill is hidden on a list of bets only, where it repeated "Open bets".

## Words fixed in every move list (High risk, High risk ledger, the three AI pages, AI vs AI, the race lists); numbers unchanged
- W1 A buy that was sold later said "open"; now "sold" (a short: "bought back"; "expired" / "settled" when that is how it ended). 51 buys on High risk alone.
- W2 Shorts: "sold short C$X" and "bought back for C$Y" instead of "put in" and "took out" (a cheaper buy-back is the profit).
- W3 A cancelled bet: "refunded C$10,000.00" (the stake), not "refunded C$0.00".
- W4 Fines: "Penalty refunded (outage day) · refunded C$500.00" and "Penalty: missed daily betting minimum · fined C$500.00".
- W5 AI vs AI "Recent trades": Claude's bets were missing (only its trades were listed); they are in. Claude's rows show its own reason, as in the Ledger.
Gemini agreed with all five.

## Checked
- Counts per race against the raw data (Claude's trades and bets + the race runner's list): Stocks 77, Crypto 67, China 10, Metals 32, Energy 51, Options 61, Currencies 56, Safe 20, Sports 267, Predictions 15. "Holding now" matches each AI's open positions and open bets.
- Before/after on every tab with a frozen clock: nothing else changed (Overview, Ledger, News, Data, Rules, Audit, Guide, About, Support identical; race pages only gained the card).
- 16 affected tabs at 10 widths (320 to 1440 px): no console errors, no sideways scrolling.

## Measured (Stocks page)
Computer: 4,591 px before, about 5,950 with the card. Phone: about 8,000 before and after (the card is folded: +126 px). High risk: computer 5,409 to 4,565 px, phone about 11,400 to 8,500.

## To reverse
- The card: remove the ten `pt-moves-card` sections in `ops/src/index.html`.
- 10 a page on High risk again: pass 10 as the last argument of `movesList(` in the High risk draw.
- Open on phones: remove the `pt-moves-card` line in `blocksOf()`.
