Run the daily ACCURACY CHECK for the Paper Trades experiment. Do not make any new trades or bets in this run.

Paper Trades is a one-month paper-trading race (Oct 28 to Nov 28, 2026) between Claude, Gemini and ChatGPT: each runs ten separate experiments, each restarted at C$100,000 (US$100,000 for China stocks) on Oct 28 at 1:45 p.m. ET, with real-world prices. Each experiment is scored on its own; the overall winner is the AI with the most total profit in C$ since the restart.

Do this:
1. Attach the GitHub repository freshlypicked00-collab/aipapertrades with push access (add_repo), clone it, `git pull`, and read ops/RUNBOOK.md, especially "Daily accuracy check".
2. Check the last 24 hours of data independently, as a second pair of eyes, using fresh sources (not the ones the trading runs used where possible):
   - Every trade and bet in trades.json and bets.json from the last 24 hours: was the price real at that time (within the day's range), the amount and quantity right, the rule or reason sound, and was it logged?
   - Every settled bet and prediction market: is the result right (final score, official resolution)?
   - The latest price of every holding and the exchange rates: within 1% of a fresh source (2% for options and prediction markets)?
   - Stops and targets: from option B (Oct 29, 6:00 p.m. ET) they are runner orders for all three AIs, filled at the live price at a run (`python3 ops/orders.py status`, ops/src/rivals.json "stops_log"). Check that every crossed stop was filled at the next run in market hours; never fill one by hand.
   - Trades filled by the race runner (trades.json "filled_by": "runner"): the price is the feed's at that moment, like Gemini's and ChatGPT's. Do not edit them; if one looks wrong, describe it in your report and the log (a "Check" entry) instead.
   - The arithmetic: re-run `python3 ops/check.py ops/src` and fix anything it reports.
   - Claude's take at the top of the site (take.json): one honest sentence, current. (Gemini, not you, fact-checks Claude's takes.)
   - The daily ledger and self-assessment for the day that just closed: numbers match the history, nothing missing.
   - READS RIGHT, not only adds up (owner, Oct 30): look at the site the way a visitor does and flag any number that is correct but easy to misread. Example: a holding card said "Bought C$35,000" next to "Worth now C$22,339" and a loss of only −C$1,111, because a third had been sold the day before and the card did not say so. Check every card, table and post for: totals next to partial figures, a missing step (a sale, a refund, a currency change), labels that do not say what a number is (worth now vs profit vs cost), and figures that disagree between two places. Fix the wording or layout (never the data), or list it in the report.
   - ops/src/geo.json (the war and Strait of Hormuz box): refreshed today, every fact still matches reputable sources, claims labelled as claims.
3. Fix RECORDING errors only (a wrong price, quantity, arithmetic, a missing log line), following the runbook's correction rules. Never change any AI's decisions, takes or reasons: decisions are final, and factual mistakes in them go in a fact check on the site, not a correction. Fix what is wrong and add one "Check" log entry per experiment that had a problem, saying what was wrong and what changed. If everything checks out, say so in the report and add one "Check" log entry per experiment you verified: "Daily accuracy check: no problems found."
4. Rebuild and push the site, sync the tracker (runbook step 8).
5. Work unattended: do not ask questions. Finish with a short report listing every problem found and fixed, and anything you could not verify.
Owner preferences: the site names the three AIs (Claude, Gemini, ChatGPT); keep every disclaimer; never invent a price or result.
