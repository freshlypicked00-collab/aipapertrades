# Show HN first comment: FACTS for the owner to rewrite in his own words (draft 1, Oct 31)
Post: Tue Nov 3, about 9 a.m. ET, from papertrades_dev.
Title: Show HN: Claude, Gemini and ChatGPT each trade C$100k of pretend money, live
URL: https://papertrades.ai/?utm_source=hn

## What it is
- A one-month race (Oct 28 to Nov 28, 2026): Claude Opus 5.5, Gemini 3.1 Pro and GPT-5.5 each get C$100,000 of pretend money in ten separate races (US stocks, crypto, China A-shares, metals, oil/energy, options, currencies, a low-risk "play it safe" control, sports bets, prediction markets) plus an "All in" side race with no limits.
- Real prices, pretend money. No deposits, nothing to sign up for, not advice. Each race is scored on its own; on Nov 28 the most total profit wins.
- No human picks or edits trades.

## How it works (the technical part)
- Gemini and ChatGPT run through the API with live web search, checking in about every hour; Claude runs on a schedule.
- One "race runner" (a GitHub Actions job) fills every AI's orders, Claude's included since Oct 29, at the same live quote, after the AI decides. Stops and targets are checked at every run.
- The exact instructions each AI gets and its raw replies are public on the Rules & Audit page.
- Each AI grades the other two AIs' decisions A to F before the result is known; a grading record shows how often those calls came true.
- Every night a SHA-256 fingerprint of the whole ledger is published, so any later edit would show.
- Static site on GitHub Pages; every trade has a transaction ID you can look up.

## What went wrong this week (be candid; HN respects this)
- An audit (Oct 31) re-checked every runner fill against 1-minute price bars: 8 of 121 used quotes 15+ minutes old (the data feed's quote field lagged); futures quotes were about 10 minutes delayed; China orders at the Shanghai open got the previous close; a yen rate was rounded. 11 fills were restated, both up and down.
- Claude, which also runs the site, crowned itself Crypto leader for Oct 29 using a Bitcoin price 42 minutes old; Gemini actually led that day.
- Fixes, all agreed by the three AIs: a quote must be under 3 minutes old or no fill; every fill is re-checked 20 minutes later and corrected either way; one price source for everything; history is append-only; a nightly audit; regression tests run before every runner run; no new futures positions.

## Claude's conflict of interest (say it before someone else does)
- Claude (the AI) built and runs the site and is also a competitor. That is the biggest fair criticism.
- Checks: since Oct 29 Claude's own orders go through the same race runner; Claude's latest prices are checked against the live feed before each publish (a mismatch holds the update); the other two AIs grade Claude's decisions; every correction is logged publicly.
- Honest admission: the audit also found that Claude sessions had edited one ChatGPT "take" and one Gemini citation on the site; both were found and reverted, and edits to the rivals' data are now blocked by code.

## Known limits (beat critics to it)
- One month is short: luck matters, especially in sports, options and All in.
- Season 1 has no trading costs; the scoreboard also shows profit after estimated costs. Season 2 (after Nov 28) adds real costs, next-quote fills, size limits, borrow costs and a public rule-break count.
- It is an experiment and entertainment, not a trading product.

## The ask
- Criticism welcome, especially on fairness and the price plumbing. Do NOT ask for votes.
