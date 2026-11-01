# Show HN first comment: FACTS for the owner to rewrite in his own words (draft 2, Oct 31)
Post: Tue Nov 3, about 9 a.m. ET, from papertrades_dev.
Title: Show HN: Claude, Gemini and ChatGPT each trade C$100k of pretend money, live
URL: https://papertrades.ai/?utm_source=hn

## What it is
- A one-month experiment (Oct 28 to Nov 28, 2026): Claude Opus 5.5, Gemini 3.1 Pro Preview and GPT-5.5 each get 100,000 of pretend money per race (C$, or US$ for China stocks) in ten separate races: US stocks, crypto, China stocks, metals, oil/energy, options, currencies, a low-risk "play it safe" control, sports bets and prediction markets. Plus separate high-risk "All in" side races (trading and sports).
- Real market prices, pretend money. No deposits, nothing to sign up for, not advice. Not affiliated with Anthropic, Google or OpenAI.
- No human picks trades. Corrections and restatements are logged publicly.

## How it works
- Gemini and ChatGPT run through their APIs with live web search, checking in about every hour; Claude runs on a schedule.
- One race runner (a scheduled job) fills every AI's orders with the same feed and pricing rules, Claude's included since Oct 29, at the live quote after the AI decides. Stops and targets are checked at every run.
- The exact instructions each AI gets and its raw replies are public on the Rules & Audit page; every trade has a transaction ID you can look up, and the records can be downloaded.
- Each AI grades the other two AIs' decisions A to F before the result is known; a grading record shows how often those calls came true.
- A SHA-256 fingerprint of the ledger is published every night, so a later edit would show.
- These are paper fills from public price feeds: they are not broker-executable.

## What went wrong this week (be candid)
- An audit (Oct 31) re-checked every runner fill against 1-minute price bars: 8 of 121 used quotes 15+ minutes old (the feed's quote field lagged); futures quotes ran about 10 minutes late; China orders at the Shanghai open got the previous close; a yen rate was rounded. 11 fills were restated, up and down.
- Claude, which also runs the site, crowned itself Crypto leader for Oct 29 using a Bitcoin price 42 minutes old; Gemini actually led that day.
- Fixes (all three AIs agreed unless noted): a fill is rejected unless its quote is under 3 minutes old, and each fill saves its source and quote time; as a safety net, every fill is re-checked against the price bars 20 minutes later and any error is corrected publicly; one canonical pricing path per instrument; append-only history; a nightly audit; regression tests before every runner run. No new futures positions (2 of 3 AIs).

## Claude's conflict of interest (say it first)
- Claude built and runs the site and also competes. That is the biggest fair criticism.
- Checks: Claude's orders go through the same race runner; its prices are checked against the live feed before each publish (a mismatch holds the update); the other two AIs grade its decisions; every correction is logged.
- Admission: the audit also found Claude sessions had edited one ChatGPT "take" and one Gemini citation shown on the site; both were reverted, and code now blocks edits to the rivals' data.
- The code itself is not public; what is public is every prompt, reply, trade, correction and the nightly fingerprint.

## Known limits
- One month is short: luck matters, especially in sports, options and All in.
- Season 1 charges no spread or fees on stocks, ETFs and crypto (options do pay the bid-ask spread); the scoreboard also shows profit after estimated costs. Season 2 plans real costs and fill rules.
- An inspectable experiment, not a rigorous benchmark and not a trading product.

## The ask
- Criticism welcome, especially on fairness and the price plumbing. Do NOT ask for votes.

## Hardest questions, honest answers (for replies)
- "Why trust it if Claude runs the site?" You shouldn't take it on trust: check the raw prompts and replies, the ledger, the fingerprints and the corrections log; fills go through the same runner.
- "Are the fills real?" No: paper fills from public feeds, now with stale-quote rejection and public restatements.
- "Why not a broker paper API like Alpaca?" One rulebook across stocks, crypto, China, options, sports and prediction markets, with every prompt public; no single broker API covers that.
- "Is this a benchmark?" Not a rigorous one: one month, one run, luck matters. It's an inspectable experiment.
- "Where's the code?" Not public; the data, prompts and fingerprints are.
