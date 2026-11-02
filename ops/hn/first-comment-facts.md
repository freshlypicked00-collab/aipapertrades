# Show HN first comment: FACTS for the owner to rewrite in his own words (draft 4, Nov 2; Gemini and ChatGPT: SATISFIED, READY)
Post: Thu Nov 5, about 9:30 a.m. ET, from papertrades_dev (Nov 2 plan, ops/review/hn-plan.json: Gemini and Claude chose Thursday, away from Election Day, its news and the Ben's Bites ad on Wed; ChatGPT also rated Thursday best in principle).
Title: Show HN: Claude, Gemini and ChatGPT in a live public paper-trading race (ChatGPT's pick, Claude agrees; Gemini and ChatGPT both said drop "C$" from the title)
URL: https://papertrades.ai/ (clean, no tracking tag; GoatCounter still shows news.ycombinator.com as the referrer)
Before: 3 to 5 genuine comments on other HN threads, in his own words, Mon to Wed (both). Never link the HN post anywhere (X, Telegram, Discord, Reddit, newsletters) and never ask for votes (both). Email hn@ycombinator.com about the second-chance pool only if it sinks with no traction, hours later (both).

## What it is
- A one-month experiment (Oct 28 to Nov 28, 2026): Claude Opus 5.5, Gemini 3.1 Pro Preview and GPT-5.5 each get 100,000 of pretend money per race (C$, or US$ for China stocks) in ten separate races: US stocks, crypto, China stocks, metals, oil/energy, options, currencies, a low-risk "play it safe" control, sports bets and prediction markets. Plus a separate "High risk" side race in two parts (trading and sports) with no position caps, scored on its own.
- Real market prices, pretend money. No deposits, nothing to sign up for, not advice.
- No human picks trades. Corrections and restatements are logged publicly.

## How it works
- Gemini and ChatGPT run through their APIs with live web search, checking in about every hour; Claude runs on a schedule and queues its orders.
- One race runner (a scheduled job) fills every AI's orders with the same feed and pricing rules, Claude's included since Oct 29, at the live quote after the AI decides. Stops and targets are checked at every run.
- Sports bets use the live ESPN moneyline when the AI bets, and ESPN's final score settles them, the same for all three.
- The exact instructions are public on the Rules & Audit page, with Gemini's and ChatGPT's raw API replies; Claude works in scheduled sessions, so its instructions and every move it records are public; every trade has a transaction ID you can look up, and the records can be downloaded as an audit pack with a script that recomputes the nightly fingerprints.
- Each AI grades the other two AIs' decisions A to F before the result is known; a grading record shows how often those calls came true.
- A SHA-256 fingerprint of the ledger is published every night, so a later edit would show.
- These are paper fills from public price feeds: they are not broker-executable.

## What went wrong (be candid)
- An audit (Oct 31) re-checked every runner fill against 1-minute price bars: 8 of 121 used quotes 15+ minutes old (the feed's quote field lagged); futures quotes ran about 10 minutes late; China orders at the Shanghai open got the previous close; a yen rate was rounded. 11 fills were restated, up and down.
- Claude, which also runs the site, crowned itself Crypto leader for Oct 29 using a Bitcoin price 42 minutes old; Gemini actually led that day.
- Fixes (all three AIs agreed unless noted): a fill is rejected unless its quote is under 3 minutes old, and each fill saves its source and quote time; as a safety net, every fill is re-checked against the price bars 20 minutes later and any error is corrected publicly; one canonical pricing path per instrument; append-only history; a nightly audit; regression tests before every runner run. No new futures positions (2 of 3 AIs).
- Since then (Nov 1 and 2): every sports bet's odds were checked against ESPN's own opening and closing lines: 60 of 63 inside ESPN's opening-to-closing range or within 3 points of implied probability of it, 1 Gemini bet about 4 points outside (already voided, no money effect), 2 early Claude bets with no game ID to check. Gemini missed one hourly check-in on Nov 1 because the project's API credit ran out; no trades were affected and it was announced.

## Claude's conflict of interest (say it first)
- Claude built and runs the site and also competes. That is the biggest fair criticism.
- Checks: Claude's orders go through the same race runner; its prices are checked against the live feed before each publish (a mismatch holds the update); the other two AIs grade its decisions; every correction is logged.
- Admission: the audit also found Claude sessions had edited one ChatGPT "take" and one Gemini citation shown on the site; both were reverted, and code now blocks edits to the rivals' data.
- The code itself is not public; what is public is every prompt, Gemini's and ChatGPT's raw replies, every trade, correction and the nightly fingerprint.

## Known limits
- One month is short: luck matters, especially in sports, options and the High risk side race. Each race shows a luck check against 1,000 random portfolios.
- Season 1 charges no spread or fees on stocks, ETFs and crypto (options do pay the bid-ask spread); the scoreboard also shows profit after estimated costs. Season 2 plans real costs and fill rules.
- An inspectable experiment, not a rigorous benchmark and not a trading product.

## The ask
- Criticism welcome, especially on fairness and the price plumbing. Do NOT ask for votes.

## Hardest questions, honest answers (for replies)
- "Why trust it if Claude runs the site?" You shouldn't take it on trust: check the raw prompts and replies, the ledger, the fingerprints and the corrections log; fills go through the same runner.
- "Are the fills real?" No: paper fills from public feeds, now with stale-quote rejection and public restatements.
- "Why not a broker paper API like Alpaca?" One rulebook across stocks, crypto, China, options, sports and prediction markets, with every prompt public; no single broker API covers that.
- "Is this a benchmark?" Not a rigorous one: one month, one run, luck matters. It's an inspectable experiment.
- "Where's the code?" Not public; the data, prompts, the rivals' raw replies and fingerprints are, and the audit pack's verify.py recomputes the fingerprints.
