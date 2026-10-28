# Paper Trades: UPDATE ALL runbook

Paper Trades is a 30-day paper-trading experiment (Oct 26 to Nov 26, 2026). An AI
manages four pretend C$100,000 portfolios using real-world prices: **Stocks**
(anything), **Crypto**, **Metals** (precious metals) and **Sports** (betting), plus a fifth,
**China** (Shanghai and Shenzhen stocks), started Oct 28 with US$100,000 and counted in US dollars.
No real money moves. The public site is https://papertrades.ai (this repo,
served by GitHub Pages). A private tracker mirrors the same data; its link is
given in the task prompt.

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
7. **Build and publish the site:** `python3 ops/build_site.py ops/src .`, then commit
   (`UPDATE ALL <Mon D, h:mm a.m./p.m. ET>`), `git pull --rebase`, and push to `main`.
7b. **Daily ledger.** If `update.py` printed `LEDGER DAY CLOSED <day>` (the first run after
   00:00 UTC, i.e. 8 p.m. ET until Nov 1, 7 p.m. ET after), write the day's notes and run
   `python3 ops/ledger_note.py ops/src notes.json`, then rebuild the site before committing. Notes:
   - `All`: 3 to 6 sentences on how the day went overall and an honest self-assessment: what was a
     good call, what was luck, what was a mistake, ending with a one-word grade for the day
     (for example "Grade for the day: good"). Use the printed numbers; don't invent figures.
   - Two or three sentences per portfolio that has a row (each one gets its own box on the page):
     its result, what moved it, any trades or bets, and an honest take on how that simulation did.
   - Plain past tense, no hype, no naming the AI model or company. Write it even on bad days.
8. **Sync the private tracker** (link in the task prompt). For each data file the script
   listed as changed (and `ledger` if you ran ledger_note.py), except `sources` and `fx`: upload `ops/src/<name>.json` to the tracker as an
   asset, then update the dataset document `datasets/<name>` with
   `source: {kind: "file", url: <the new /_blob/... url>, name: "<name>.json"}` and
   `updated: {at: <now ISO>, by: "AI"}`. Read the `datasets` collection first for the
   versions and write all updates in one batch. Do not change the tracker page itself.
9. **Report** in a few lines: the four totals, any trades or bets with reasons, settled
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

## Events

Each portfolio's tab shows only events whose `affects` lists it, so tag events precisely
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
  "sources_add": [{"title": "Kitco – Gold spot", "url": "https://..."}]
}
```

Asset names must match `holdings.json` (`SOXL`, `TQQQ`, `Bitcoin`, `Ethereum`, `Solana`,
`XRP`, `Gold`, `Silver`, `STAR 50 ETF`, `Semiconductor ETF`). Prices are US dollars except
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

Stocks score at the Nov 25 close (US markets are closed Nov 26). China scores at the
Nov 26 Shanghai close (3:00 p.m. Beijing, 2:00 a.m. ET Nov 26). Crypto, Metals and
Sports score at Nov 26, 4:00 p.m. ET; settle or void any remaining bets. Add a
"Final result" log entry per portfolio with the result, versus its benchmark, and the
biggest win and loss. Then stop: later runs only confirm the final state.
