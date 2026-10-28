# Paper Trades: UPDATE ALL runbook

Paper Trades is a 30-day paper-trading experiment (Oct 26 to Nov 26, 2026). An AI
runs ten separate simulations with real-world prices, each with its own starting money:
- Trading: **Stocks** (anything, C$100,000), **Crypto** (C$100,000), **China** (Shanghai and
  Shenzhen stocks, US$100,000, counted in US dollars), **Metals** (C$100,000), **Energy**,
  **Options**, **Currencies** (forex with leverage) and **Safe** (a low-risk control), C$100,000 each.
- Betting: **Sports** (betting) and **Predictions** (prediction markets), C$100,000 each.
All but Safe are run high risk, high reward; Safe is deliberately cautious.
No real money moves. The public site is https://papertrades.ai (this repo,
served by GitHub Pages). A private tracker mirrors the same data; its link is
given in the task prompt.

**The ten are separate experiments.** Each started with its own C$100,000 (US$100,000 for China)
and is judged only against that amount and its own benchmark. Never add them together, never
quote a combined or overall total, and never describe them as one C$500,000 portfolio, in the log,
the ledger, the self-assessment or anywhere else.

An **UPDATE ALL** checks every portfolio: fresh prices, results, rules, trades,
then publishes everything. It runs every hour.

## Files

- `ops/src/*.json`: the source of truth. Never edit `data.json` at the repo root; it is built.
  - `holdings.json`: positions (quantity, entry, price, source, cost, value).
  - `rules.json`: the trading rules. Rules with `asset`/`level`/`direction` are price triggers.
  - `bets.json`: every bet (odds, stake, status, result, closing odds, `starts_at`).
  - `history.json`, `prices.json`, `bench_history.json`: time series (appended by the script).
  - `trades.json`, `log.json`, `events.json`, `benchmark.json`, `indexes.json`, `sources.json`.
  - `ledger.json`: the daily ledger (one row per portfolio per UTC day plus an `All` row with the write-up).
  - `fx.json`: the last USD/CAD and USD/CNY rates (used when a run has no fresh USD/CNY).
  - `index.html`: the tracker page source (the site is built from it).
- `ops/update.py`: applies one update from an input file and closes finished ledger days.
- `ops/ledger_note.py`: attaches the daily write-ups to a closed ledger day.
- `ops/build_site.py`: builds `index.html`, `data.json`, `CNAME`, `.nojekyll` at the repo root.

## Steps

1. **Get the repo.** Attach `freshlypicked00-collab/aipapertrades` with push access, clone it,
   and `git pull` so you start from the latest data. Read `ops/src/holdings.json`,
   `rules.json`, `bets.json`, `events.json` and the last ~20 entries of `log.json`.
2. **Check the time** (Eastern). Note whether US markets are open (9:30 a.m. to 4:00 p.m. ET,
   weekdays, closed Nov 26 for Thanksgiving). After **Nov 26, 4:00 p.m. ET**, do the final
   scoring run (see the end) and make no more trades or bets.
3. **Collect prices** using the price standard below. Use web search and fetch; never
   estimate or invent a price. If a fresh quote can't be confirmed, leave that asset out of
   the input (its last price stays) and say so in your summary.
4. **Sports.** For every open bet:
   - Game finished: settle it (`Won`/`Lost`/`Push`) from a final-score source.
   - Game starts within the next 75 minutes: record the current price as its closing odds
     (`bets_closing`); a later run before the start overwrites it.
   - Game already started with no closing odds: record the last pre-game line from a game
     page (ESPN, Covers) if one is shown; otherwise leave it empty.
   - **New bets:** once a day, at the first run between 11:00 a.m. and 3:00 p.m. ET, look at
     that day's games and place bets only with a real reason (a model edge over the posted
     odds, or sharp money clearly against the public). 1 unit = C$1,000, at most 2 units per
     bet, at most 8 units per day, no parlays. If the bankroll is below C$80,000, use half
     units. Use real posted odds (DraftKings, FanDuel or an exchange) and record `starts_at`.
     Number bets S6, S7, ... continuing from the highest id.
5. **Decide trades.** Apply `rules.json` strictly, then judgment on new information (news,
   earnings, central banks). Stocks trade only while the market is open. Each trade needs a
   one-sentence reason. Current plans not fully captured as price rules:
   - SOXL: the "trim a quarter at $108.60" rule only applies until Wed Oct 28, 4:00 p.m. ET;
     remove it after. On Thu Oct 29 at the first market-hours run, if Microsoft or Alphabet
     cut AI spending plans in their Oct 28 earnings, sell most of the SOXL.
   - Crypto: USDC reserve is deployed by the Bitcoin rules; whatever is left goes into the
     portfolio after the Nov 3 US midterms unless the picture has clearly soured.
   - Metals: cash reserve is deployed only by the gold rules.
   - China: see the China section below.
   Update rules when plans change (`rules_add` / `rules_remove`), keeping `label`, `asset`,
   `level`, `direction` on price rules.
6. **Write the input file** (format below) to a temp path and run
   `python3 ops/update.py ops/src <input.json>`. Read the warnings. Fix and re-run from a
   fresh `git checkout ops/src` if something is wrong.
6b. **Check the arithmetic:** run `python3 ops/check.py ops/src`. If it reports problems, fix them
   before publishing.
7. **Build and publish the site:** `python3 ops/build_site.py ops/src .`, then commit
   (`UPDATE ALL <Mon D, h:mm a.m./p.m. ET>`), `git pull --rebase`, and push to `main`.
7b. **Daily ledger.** If `update.py` printed `LEDGER DAY CLOSED <day>` (the first run after
   00:00 UTC, i.e. 8 p.m. ET until Nov 1, 7 p.m. ET after), write the day's notes and run
   `python3 ops/ledger_note.py ops/src notes.json`, then rebuild the site before committing. Notes:
   - `All`: 2 to 4 sentences of general notes on the day (market backdrop, common lessons). No
     money figures and no combined total: each experiment's numbers belong only in its own note.
   - Two or three sentences per portfolio that has a row (each one gets its own box on the page):
     its result, what moved it, any trades or bets, and an honest take on how that simulation did.
   - Plain past tense, no hype, no naming the AI model or company. Write it even on bad days.
   - Then append a fresh self-assessment to `ops/src/review.json` (keep the old entries): one row
     per portfolio plus `All`, all with the same `at` (now), fields `portfolio`, `grade` (A to F,
     or "—" if too early; `null` for All) and `text` (2 to 4 sentences per portfolio: how that
     experiment is going since its own start, honest about luck vs. skill and mistakes; for All,
     general lessons only, with no money figures or combined total).
     The page shows the latest set at the top of the Ledger tab. Sync `review` to the tracker too.
8. **Sync the private tracker** (link in the task prompt). For each data file the script
   listed as changed (and `ledger` if you ran ledger_note.py), except `fx`: upload `ops/src/<name>.json` to the tracker as an
   asset, then update the dataset document `datasets/<name>` with
   `source: {kind: "file", url: <the new /_blob/... url>, name: "<name>.json"}` and
   `updated: {at: <now ISO>, by: "AI"}`. Read the `datasets` collection first for the
   versions and write all updates in one batch. Do not change the tracker page itself.
9. **Report** in a few lines: each experiment's value on its own line, any trades or bets with reasons, settled
   bets, and anything you couldn't confirm.

## China (Shanghai and Shenzhen)

- Counted in **US dollars**; prices are in **yuan**. Give `fx.usdcny` (with `cny_source`, `cny_at`)
  on every run; check two sources (a spot quote such as Pound Sterling Live/Barchart, and the
  PBOC fixing or its market estimate) and use the spot rate.
- **Trading hours:** 9:30–11:30 a.m. and 1:00–3:00 p.m. Beijing time, weekdays. That is
  9:30–11:30 p.m. and 1:00–3:00 a.m. ET until Nov 1, then 8:30–10:30 p.m. and 12:00–2:00 a.m. ET.
  Trade China only in a run that falls inside those hours; otherwise just revalue it with the last
  close (`"market_closed": true`).
- **Rules of the market** (enforced by `update.py`): buy in lots of 100 shares (`"shares"`),
  shares bought on a Beijing date can't be sold until the next trading day, sells by `"shares"` or
  `"fraction"` (rounded down to whole lots unless selling everything). Cash is `Cash (CNY)`.
- **Prices:** ETNet quote pages work: `https://www.etnet.com.hk/www/sc/ashares/quote.php?code=588000`
  (always check the name on the page matches the code; some codes return the wrong stock). Find
  others through web search. Holdings: `STAR 50 ETF` (588000), `Semiconductor ETF` (512480).
- **Benchmark:** CSI 300 (`indexes.csi300`). The first level you supply becomes its start (it was
  not recorded at entry), so supply the Oct 28 close at the first run after 3:00 p.m. Beijing, then
  every run when you have it.
- **Plan:** the portfolio is a rebound bet on beaten-down Chinese tech (STAR 50 down ~40% from its
  July peak) supported by state-backed ETF buying and strong chip earnings. Follow the price rules
  in `rules.json`. Watch the Fifth Plenum communique (Oct 29) and the plenum rule.
- **Events:** add China events with `"affects": "China"` only.

## Daily accuracy check

A separate scheduled task runs every evening (9:27 p.m. ET) with `ops/AUDIT_PROMPT.md`. It makes
no trades; it re-checks the last 24 hours against fresh sources and fixes mistakes. Correction rules:
- **Wrong current price:** run `update.py` with the correct price (normal update; it revalues).
- **Wrong trade price or amount** (the price wasn't real at that time, or the maths is off): edit
  that entry in `trades.json`, adjust the holding's `quantity`, `entry_usd`/`entry_local` and
  `cost_cad`/`cost_usd` (and the funding cash) to what they would have been, then run `update.py`
  with current prices so values and history update. Never delete a trade to hide a loss.
- **Wrong bet result:** fix `status` and `result_cad` in `bets.json`, then run `update.py`.
- **Missed stop or limit:** make the trade now at the rule's level with `fill_at` set to when it
  was crossed, as in the stop-order section.
- **Ledger mistakes:** fix the numbers or notes in `ledger.json` for that day.
- Every correction gets a `Check` log entry in that experiment saying what was wrong and what
  changed. Then run `ops/check.py`, rebuild, push and sync.

## Stop and limit orders between runs

Treat every price rule (one with `asset`, `level`, `direction`) like a real order sitting at the
broker. At each run, for each asset with a price rule, find the **high and low since the last
run** (the day's range from the quote page, or an intraday chart; for prices fetched within the
same day, the day's high/low is fine) and pass them as `"high"` and `"low"` with the price.
`update.py` prints `RULE LEVEL CROSSED` for any rule whose level was touched. Then:
- If the level was crossed and the trade hasn't been made, make it now at **the rule's level**,
  with `"fill_at"` set to when it was crossed (if known, else the run time) and a `"note"` saying
  it filled as a stop or limit. If the price **gapped** past the level (opened beyond it), fill at
  the first real price after the gap instead, which is worse. Never fill at a better price than
  the level, and never use a price you didn't see recorded.
- Remove or replace the rule after it executes (`rules_remove` / `rules_add`).
- If you can't find a reliable high/low for an asset, use the current price only and say so.

## Extra runs around big events

Events in `events.json` with `"extra_run": true` get a one-time extra run 5 minutes after them.
At the end of every run, list the scheduled tasks (`list_triggers`), and for each such event in
the next 3 hours without one, create a one-time scheduled task (`create_trigger` with
`run_once_at` = event time + 5 minutes, `initiation` = `human_schedule`, name
`Paper Trades: extra run after <event>`, not requiring a local device) whose prompt is the
contents of `ops/TASK_PROMPT.md`. Never create duplicates. Market opens and closes already have their own recurring runs (US 9:35 a.m. and 4:05 p.m. ET; China 9:35 a.m. and 3:05 p.m. Beijing), plus every hour at :13 and every 30 minutes in US market hours (:43), and a daily accuracy check at 9:27 p.m. ET; don't schedule extras that land within 10 minutes of those.
**Breaking news:** if something important is developing that could move a position (a Hormuz deal
or attack, a surprise central-bank statement, an earnings shock, a game-changing injury before a
bet starts), you may also schedule one extra run 20 to 30 minutes later, the same way. Use
judgment: at most 6 such news runs a day, and none for routine moves. Mark new big events (rate decisions,
major earnings for held names, key data, election night, market opens with planned orders) with
`extra_run` when you add them.

## Opening orders, Wed Oct 28 (do these at the first run after 9:30 a.m. ET)

Do each once; skip if `trades.json` already has trades for that portfolio. Use live quotes, put
the reasons in the log, then add price rules (with `asset`, `level`, `direction`, `label`)
computed from the actual fill prices.

- **Energy** (high risk; oil near $100 on Strait of Hormuz attacks, a US blockade of Iran and low
  diesel stocks; the risk is a Hormuz deal): buy C$40,000 UCO (2x crude oil), C$20,000 FRO
  (Frontline, oil tankers; freight rates are soaring), C$20,000 VLO (Valero, refiner; diesel
  margins), keep C$20,000 cash. Rules: sell half UCO at the next run after any announced deal to
  reopen Hormuz; sell half UCO if it falls 15% below entry; sell a third of UCO at 25% above entry;
  if WTI falls below $92 without a deal, add C$10,000 UCO.
- **Options** (high risk, high reward; earnings week): buy calls, about 5% out of the money, using
  the ask price and whole contracts (`qty` = contracts x 100): MSFT expiring Oct 30, about
  C$12,000; GOOGL expiring Oct 30, about C$12,000; AMZN expiring Oct 30 (earnings Oct 29), about
  C$12,000; NVDA expiring Nov 20, about 10% out of the money, about C$20,000. Keep the rest in cash
  for later plays (AMD Nov 3, post-midterm moves, Nvidia earnings). Rules: sell the MSFT and GOOGL
  calls at the first market-hours run on Oct 29, win or lose (don't hold through time decay); sell
  the AMZN calls at the first run on Oct 30; sell half of any option that doubles. Name holdings
  like `MSFT Oct 30 $560 call`; price = premium per share. If you can't find a live option quote
  from a chain page (search "<ticker> option chain <expiry date>"; Barchart, Nasdaq, Yahoo, MarketChameleon), skip that trade and log why.
- **Safe** (the control; low risk): buy C$40,000 SGOV (US Treasury bills), C$25,000 SCHD
  (dividend stocks), C$15,000 BND (US bonds), C$10,000 GLD (gold), keep C$10,000 cash. Rules: no
  leverage, no single stocks, no options; rebalance only if a holding drifts more than 5 points
  from its target; gold never more than 10%. Its benchmark is a savings account at 2.25% a year
  (the Bank of Canada rate), calculated by the page from its first trade.

## Currencies (forex, high risk)

- Opened Oct 28, 12:25 a.m. ET with C$100,000 and leverage: positions up to 8x the account.
  Currencies are holdings priced in US dollars per unit: `US dollar` (always 1.0), `Japanese yen`
  (1 / USD/JPY), and add others the same way (`Euro` = EUR/USD, `British pound` = GBP/USD).
- `Buy` a currency to go long (cash may go negative; that's borrowing). `Short` (with `cad` or
  `qty`) borrows and sells it; `Cover` buys it back. A short US dollar position profits when
  USD/CAD falls. Value = cash + all positions; the update tool handles the maths.
- Trades Sunday 5 p.m. to Friday 5 p.m. ET. Give the `Japanese yen` price every run (from
  Trading Economics or another USD/JPY quote) and the `US dollar` price 1.0.
- Benchmark: a savings account at 2.25% a year, from the first trade.

## Predictions (prediction markets)

- Prices are Polymarket (or Kalshi) share prices in US dollars, 0 to 1. Holding names say the
  outcome bought, e.g. `Republicans win the Senate (Yes)`. Get prices from the Polymarket event
  pages or FrenzyCap pages in `sources.json`; use the buy (ask) price when buying.
- Trades any time. Settle a resolved market as a `Sell` with `fraction` 1 at price 1.0 (won) or
  0.0 (lost), and log it. The Fed bet resolves at 2:00 p.m. ET Oct 28; the midterm bets once
  results are called (from Nov 4).
- Only bet where data or a forecast model clearly disagrees with the market price; record the
  model number in the log. Any size is allowed; it is a high-risk experiment.

## Benchmarks

Metals is compared with holding gold (from its Oct 27, 7:30 p.m. start); the update tool takes this from the `Gold` price automatically.

## Benchmarks for the new experiments

Supply `indexes.uso` (the USO fund's price, for Energy) and `indexes.sp500` every market-hours
run. The Energy and Options comparisons start from the first level after each one's first trade.

## Events

Write `when` in Eastern time (e.g. "Wed Oct 28, 9:45 a.m."); the page adds the UTC time from `at`. Each portfolio's tab shows only events whose `affects` lists it, so tag events precisely
(`"Stocks"`, `"Crypto, Metals"`, ...). Never use `"All"`; list the portfolios instead.

## Price standard

- Every price has a `source` and the `at` time of the quote.
- **Crypto** (Bitcoin, Ethereum, Solana, XRP): quotes under 30 minutes old; check two
  sources and use one that agrees with the other within 0.5%.
- **Stocks** (SOXL, TQQQ) and the **S&P 500 / S&P/TSX** levels: live quotes during market
  hours; outside them use the last close and set `"market_closed": true`. Include
  `indexes` (`sp500`, `tsx`) whenever you have them.
- **Metals** (Gold, Silver): spot prices, not futures. If only futures are available, say
  so in the source text.
- **USD/CAD**: a quote under 3 hours old.

## Sources

Every new source in `sources_add` needs `"portfolios"`: the list of simulations it was used for
(`Stocks`, `Crypto`, `China`, `Metals`, `Energy`, `Options`, `Currencies`, `Safe`, `Sports`,
`Predictions`). Each tab shows only its own sources; the Ledger tab shows all of them.

## Every trade is tracked

Every buy, sell, bet and settlement must go through `ops/update.py` (never edit the data files by
hand), so it lands in `trades.json` / `bets.json` with its time, price and amount and appears in the
Ledger tab's "Every trade" table and in that day's entry. Each trade also needs a log entry with
the reason.

## The AI's take (top of the site)

The site opens with one sentence from the AI about how things are going. Write a new one (pass
`"take": "..."` in the input file) whenever the story changes: at every daily ledger close, after
a trade or settled bet that matters, and after big events. One sentence, about 20 to 35 words,
plain and honest, starting with the day number ("Day 4: ..."). Name the best and worst
experiment by name, never a combined or overall total, no hype, no promises.

## Logging

Add log entries only when something happens: a trade, a bet placed or settled, a rule
change, or news that changes the plan. At the 4 p.m. ET weekday run, add one short
"Daily close" entry per portfolio. Quiet hours need no log entry; the value history still
updates. Write plainly, in past tense, without naming the AI model or company.

## The input file

```json
{
  "at": "2026-10-28T10:05:00-04:00",
  "fx": {"usdcad": 1.4021, "source": "Trading Economics", "at": "2026-10-28T09:58:00-04:00"},
  "prices": {
    "SOXL": {"price": 103.10, "source": "TheStreet Pro", "at": "2026-10-28T10:01:00-04:00"},
    "Bitcoin": {"price": 80900, "source": "CoinGecko (Kraken within 0.1%)", "at": "2026-10-28T10:02:00-04:00"},
    "Gold": {"price": 4031.5, "source": "Kitco spot", "at": "2026-10-28T10:00:00-04:00"}
  },
  "indexes": {"sp500": {"level": 7731.2, "at": "2026-10-28T10:01:00-04:00", "source": "Yahoo Finance"}},
  "trades": [
    {"portfolio": "Stocks", "holding": "SOXL", "action": "Sell", "fraction": 0.25, "price": 108.9, "to": "Cash (CAD)"},
    {"portfolio": "Crypto", "holding": "Bitcoin", "action": "Buy", "cad": 10000, "price": 81050, "funding": "USDC"},
    {"portfolio": "Crypto", "holding": "Solana", "action": "Sell", "fraction": 1, "price": 95.5, "to": "Bitcoin", "to_price": 79800}
  ],
  "bets_new": [{"bet": "S6", "sport": "NBA", "event": "Celtics vs. Knicks", "pick": "Knicks +4.5", "market": "spread", "line": 4.5, "odds": -110, "stake_cad": 1000, "starts_at": "2026-10-28T19:30:00-04:00"}],
  "bets_closing": [{"bet": "S6", "closing_odds": -115, "closing_line": 4.0}],
  "bets_settle": [{"bet": "S3", "status": "Won"}],
  "log": [{"portfolio": "Stocks", "action": "Sell", "detail": "Sold a quarter of SOXL at $108.90; the trim rule triggered before earnings."}],
  "rules_add": [], "rules_remove": [],
  "events_add": [{"at": "...", "when": "Wed Oct 28, 7:30 p.m.", "event": "...", "affects": "Sports", "why": "..."}],
  "sources_add": [{"title": "Kitco – Gold spot", "url": "https://...", "portfolios": ["Metals"]}]
}
```

Asset names must match `holdings.json` (`SOXL`, `TQQQ`, `Bitcoin`, `Ethereum`, `Solana`,
`XRP`, `Gold`, `Silver`, `STAR 50 ETF`, `Semiconductor ETF`, plus the Predictions, Energy,
Options and Safe holdings). Buys may give `qty` (exact shares) instead of `cad`. Asset names are
global keys for prices, so if two portfolios hold the same ticker, give each the same price. Prices are US dollars except
China, which is in yuan. `cad` amounts are Canadian dollars.

China extras for the input file:

```json
"fx": {"usdcad": 1.4049, "source": "...", "at": "...", "usdcny": 6.678, "cny_source": "...", "cny_at": "..."},
"prices": {"STAR 50 ETF": {"price": 1.362, "source": "ETNet (SH 588000)", "at": "..."}},
"indexes": {"csi300": {"level": 4090.1, "source": "...", "at": "..."}},
"trades": [{"portfolio": "China", "holding": "STAR 50 ETF", "code": "588000", "action": "Buy", "shares": 48800, "price": 1.25}]
```
Use `fraction` for sells as a share of the position. Log actions: `Buy`, `Sell`, `Bet`,
`Settle`, `Hold`, `Rule`, `Check`.

## Final scoring (after Nov 26, 4:00 p.m. ET)

Stocks, Energy, Options and Safe score at the Nov 25 close (US markets are closed Nov 26;
options still open then are valued at that close). Predictions scores at Nov 26, 4:00 p.m. ET
with open markets at their last price. China scores at the
Nov 26 Shanghai close (3:00 p.m. Beijing, 2:00 a.m. ET Nov 26). Crypto, Metals and
Sports score at Nov 26, 4:00 p.m. ET; settle or void any remaining bets. Add a
"Final result" log entry per portfolio with the result, versus its benchmark, and the
biggest win and loss. Then stop: later runs only confirm the final state.

## AI vs AI (Gemini and ChatGPT)
- The owner chose to name the models on the "AI vs AI" tab: Claude vs Gemini vs ChatGPT. That tab, its Telegram posts and the README may name Claude, Gemini (Google) and ChatGPT (OpenAI). Everywhere else keep saying "an AI model" / "the AI".
- Gemini and ChatGPT are run by `.github/workflows/rivals.yml` (hourly at :37) and `ops/rivals.py`, not by these scheduled runs. Gemini plays Stocks, Crypto, China, Metals and Energy; ChatGPT plays Stocks, Crypto and Predictions. Their state is `ops/src/rivals.json`.
- Scheduled runs must NOT edit `ops/src/rivals.json` or trade for the rivals. Just keep it when rebuilding (build_site.py reads it). If `git pull --rebase` conflicts on index.html or data.json, take the latest origin version and rebuild.
- The daily accuracy check may read rivals.json and report anything odd (a price far off, a refused-order pattern, `last_run.status` errors) in its report, but changes nothing there.
