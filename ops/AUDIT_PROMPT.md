Run the daily ACCURACY CHECK for the Paper Trades experiment. Do not make any new trades or bets in this run.

Paper Trades is a one-month paper-trading race (Oct 28 to Nov 28, 2026) between Claude, Gemini and ChatGPT: each runs ten separate experiments, each restarted at C$100,000 (US$100,000 for China stocks) on Oct 28 at 1:45 p.m. ET, with real-world prices. Each experiment is scored on its own; the overall winner is the AI with the most total profit in C$ since the restart.

Do this:
1. Attach the GitHub repository freshlypicked00-collab/aipapertrades with push access (add_repo), clone it, `git pull`, and read ops/RUNBOOK.md, especially "Daily accuracy check".
2. Check the last 24 hours of data independently, as a second pair of eyes, using fresh sources (not the ones the trading runs used where possible):
   - Every trade and bet in trades.json and bets.json from the last 24 hours: was the price real at that time (within the day's range), the amount and quantity right, the rule or reason sound, and was it logged?
   - Every settled bet and prediction market: is the result right (final score, official resolution)?
   - The latest price of every holding and the exchange rates: within 1% of a fresh source (2% for options and prediction markets)?
   - Stop and limit rules: were any levels crossed in the last 24 hours (by the day's high/low) without the trade being made?
   - The arithmetic: re-run `python3 ops/check.py ops/src` and fix anything it reports.
   - Claude's take at the top of the site (take.json): one honest sentence, current. (Gemini, not you, fact-checks Claude's takes.)
   - The daily ledger and self-assessment for the day that just closed: numbers match the history, nothing missing.
   - ops/src/geo.json (the war and Strait of Hormuz box): refreshed today, every fact still matches reputable sources, claims labelled as claims.
3. Fix RECORDING errors only (a wrong price, quantity, arithmetic, a missing log line), following the runbook's correction rules. Never change any AI's decisions, takes or reasons: decisions are final, and factual mistakes in them go in a fact check on the site, not a correction. Fix what is wrong and add one "Check" log entry per experiment that had a problem, saying what was wrong and what changed. If everything checks out, say so in the report and add one "Check" log entry per experiment you verified: "Daily accuracy check: no problems found."
4. Rebuild and push the site, sync the tracker (runbook step 8).
5. Work unattended: do not ask questions. Finish with a short report listing every problem found and fixed, and anything you could not verify.
Owner preferences: the site names the three AIs (Claude, Gemini, ChatGPT); keep every disclaimer; never invent a price or result.
