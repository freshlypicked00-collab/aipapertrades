# Filters and sorting on every list (owner, Oct 31, 11:25 p.m. ET)
Owner: "if you're in bets there should be a button to sort losses, and for other things sort buys, sort sells, etc. Make sure filtering on the website is very good; work with all models and check everywhere."

Votes (ops/review/filters-oct31.json; Claude first, blind):
- F1 one shared bar on every list: all three agreed.
- F2 Buys / Sells / Shorts / Covers as separate pills (shorts no longer under Sells, covers no longer under Buys): all three agreed (Claude and Gemini: a combined pill is acceptable on phones; the pills wrap instead).
- F3 Won / Lost / Open (+ Push or void only when any): all three agreed.
- F4 Sort: newest, oldest, biggest profit, biggest loss, largest amount; no-result rows last, ties newest first: all three agreed.
- F5 hide a pill with no matches, "Every move" stays: all three agreed.
- F6 remember the choice in the page, not the link: Claude and ChatGPT (Gemini wanted it in the link).
- F7 "Showing x of y ... Clear" line: all three agreed.

Built (one helper, mfApply, in ops/src/index.html):
- Ledger "Every trade and bet", each race's Decision log, the Sports bets table, the All in page's Recent moves, the All in ledger, each AI's page; for all three models.
- Profit sorts use realised results only (sales and bet results), so nothing is counted twice; China's US$ amounts are compared in C$.
- Sort menus keep their own order (the site's alphabetical-menu rule skips them); "All races", "All bets" and "Every entry" stay on top of their menus.
