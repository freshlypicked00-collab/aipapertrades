# Season 2 decisions (record)

All agreed by Claude, Gemini and ChatGPT unless noted. Sources: ops/review/risk-*.json, three-items-oct30.json, unrestricted-r2-oct30.json.

- Oct 30: Season 2 starts after Nov 28. Three headline competitions, Strict / Standard / Unrestricted; each AI plays all three. (all three)
- Oct 30: Season 1's ten races and profit-only scoring stay exactly as agreed until Nov 28. (all three)
- Oct 30: Strict won on Return / max(Max drawdown, 5%); Standard on Return / max(Max drawdown, 10%); a rule breach makes an AI ineligible. (all three)
- Oct 30, second discussion: Unrestricted won on Return / max(Max drawdown, 20%); raw profit shown as a separate "Biggest profit" mention with no title and no champion points (compromise a). Gemini changed its view from raw profit. (all three)
- Oct 30, second discussion: overall Season 2 champion = equal rank points across Strict, Standard and Unrestricted. (all three)
- Oct 30: announce now as a broad teaser, no detailed rules. (all three)
- Oct 30: private test of the three levels from Nov 1 to Nov 28, not shown publicly, once a day (Gemini), with a hard spending cap (ChatGPT). (all three)
- Draft limits (not final; to settle before launch): Strict 10% max position, no leverage, no options/crypto/parlays; Standard 20%, up to 1.5x; Unrestricted leverage 3-5x, position cap 35% (ChatGPT) or none (Gemini).

## Trading costs (Oct 30; owner asked, majority decides; Claude, Gemini and ChatGPT ALL AGREED, ops/review/limits-oct30.json)
- Season 2 charges a realistic trading cost on stock, ETF and crypto fills, the same for every AI: buy at the ask and sell at the bid where the feed gives quotes; otherwise a fixed cost per side of 0.05% for large US ETFs, 0.10% for other stocks and 0.10% for major crypto. Options keep ask/bid fills as now.
- NOT applied to the current race (Season 1): changing fill rules mid-race would change the game the AIs planned for.
- ChatGPT's condition: freeze and publish the cost model before Season 2's first trade; change it only between seasons.
- Gemini's note: market impact on large orders in low-volume assets is the one remaining gap; the fixed costs mostly cover it at our sizes.

# Season 1: Best risk manager (separate award, added Oct 30; never changes the Nov 28 profit winner)
- Loss rule (a bigger drop always scores worse) and the 2% floor: Claude's choices, then accepted by Gemini and ChatGPT (all three).
- How it is crowned: average score (Claude, ChatGPT) vs races won (Gemini). Owner's decision, Oct 30: show BOTH, side by side. Race-win ties broken by the average.

## Private test cancelled (owner, Oct 30, 11:05 p.m. ET)
- The Nov 1 to Nov 28 private test was cancelled before it started (workflow s2test.yml turned off). Reasons: it would spend the OpenRouter credit ChatGPT needs for the main race (estimated to run out around Nov 13); the main race already exercises the same fill code; the Season 2 rules may change after Season 1.
- Instead: a short test of a few days just before Season 2 launches, with the final rules and the trading costs above.

## Real trading costs in the fills (Oct 31; all three AIs agreed, C6 in ops/review/costs-oct31.json)
Season 2 builds real costs into the fills from day one: buys at the ask and sales at the bid (or the order book where there is one),
plus fees by market (start from Season 1's display table v1.1 in ops/costs.py). Raised by Gemini and ChatGPT for Season 2 as well:
fill-size limits for thin markets (options strikes, prediction markets, small coins), borrow costs and margin interest for shorts and
leverage, funding and contract rolls, dividends and interest on cash, settlement times, and the rule version shown on the scoreboard.

## Real-world rules for Season 2 (Oct 31, 9:15 p.m. ET; owner: "we need to blueprint real investment strategy")
Question and answers: ops/review/realworld-oct31.json; Claude's votes first: claude-votes-realworld-oct31.json. Season 1 unchanged.
ALL THREE AGREED (R1-R8, with ChatGPT's wording fixes adopted):
- R1 Costs on every fill: bid/ask where quotes exist; otherwise a labelled house estimate of 0.05% per side (large US ETFs), 0.10% (other stocks, major crypto); options at bid/ask.
- R2 Fills at the first live quote AFTER the decision, never older than 60 s; futures' delayed quotes flagged with a small extra cost; limit orders fill only when the market trades through the limit with volume after the order, partial fills possible.
- R3 Liquidity: no order above 1% of average daily dollar volume; options need open interest >= 500, a nonzero bid, spread <= 10% of mid, and a per-order cap against option volume/open interest.
- R4 Event check-ins within 15 minutes of a big event (S&P 500 or Nasdaq 1.5%+ in an hour, VIX +20%, a central-bank surprise defined by a timestamped source).
- R5 Each AI writes its own risk rules before Season 2; every break is counted publicly.
- R6 Shown, never scored: average days held for losers vs winners; how often a stop was moved further away.
- R7 Every race shows a plain buy-and-hold index benchmark after the same costs.
- R8 Results are pre-tax; the site says so plainly.
ALSO AGREED BY ALL THREE (named independently by Gemini and ChatGPT; Claude agrees): borrow and margin costs (overnight interest on leverage, borrow fees on shorts, hard-to-borrow names) and corporate actions (dividends credited, splits and spinoffs adjusted, expiries handled).
ONLY CHATGPT: a market-impact model with order-book depth, queue position and trading halts (Gemini noted the same gap on Oct 30 but said fixed costs mostly cover it at our sizes). To settle before launch.
Criticisms: emotion = fair premise, overstated (R5 measures it); frictions = fair for Season 1, handled for Season 2 by R1-R3 and the quote-age fix; macro = mostly wrong (live hourly news search), fair about the gap between check-ins (R4). All three agreed.

## Outside Gemini review (owner, Nov 1; ops/review/outside-gemini-nov1.json)
- G1 ALL THREE AGREED: from Season 2 every trade and bet also gives a short structured TRIGGER (a JSON key in the prompt, Gemini's note), shown as a tag next to the free-text reason, which always stays visible (ChatGPT's condition). Season 1 unchanged.
- G2 ALL THREE AGREED (Claude and Gemini: on condition it's clearly labelled estimated): Season 1 ledger filter grouping reasons by type by keyword, labelled "estimated", never shown as the AI's own trigger.
- G3 ALL THREE AGREED: "You don't trade here: you watch three AIs trade." on the home page and in llms.txt (done Nov 1).
- Already covered: execution realism (R1-R3, costs), stress drill (L3), write-ups (What happened next), discipline (R5/R6), pre-tax (R8). Not adopted: live broker integration, user strategy tools (not a user trading platform).

## Season 2 design rounds (owner, Nov 1; ops/SEASON2.md is the full plan)
- 8 weeks, Jan 11 - Mar 5, 2027, dry run Jan 4-8; six AIs (+ Llama within budget); index, 60/40 and random-trader benchmarks; Betting as its own
  track; High risk (formerly All in) dropped; Small account only after a clean trial; operator separation, sealed orders, shared data pack, open-source runner,
  replay files, named outside reviewer, correction protocol, golden tests; market impact, commissions, refuse-and-count risk checks,
  minimum fill delay; Draft Day, dataset and research report, prediction game. ALL THREE AGREED on 27 of 28 items (lineup split on Llama).
- Rejected by all three: visitors linking their trading accounts.
