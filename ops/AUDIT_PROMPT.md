Run the daily ACCURACY CHECK for the Paper Trades experiment. Do not make any new trades or bets in this run.

Paper Trades is a 30-day paper-trading experiment (Oct 26 to Nov 26, 2026): ten separate experiments, each with its own C$100,000 (US$100,000 for China stocks), run by "an AI model" with real-world prices. Never add them together.

Do this:
1. Attach the GitHub repository freshlypicked00-collab/aipapertrades with push access (add_repo), clone it, `git pull`, and read ops/RUNBOOK.md, especially "Daily accuracy check".
2. Check the last 24 hours of data independently, as a second pair of eyes, using fresh sources (not the ones the trading runs used where possible):
   - Every trade and bet in trades.json and bets.json from the last 24 hours: was the price real at that time (within the day's range), the amount and quantity right, the rule or reason sound, and was it logged?
   - Every settled bet and prediction market: is the result right (final score, official resolution)?
   - The latest price of every holding and the exchange rates: within 1% of a fresh source (2% for options and prediction markets)?
   - Stop and limit rules: were any levels crossed in the last 24 hours (by the day's high/low) without the trade being made?
   - The arithmetic: re-run `python3 ops/check.py ops/src` and fix anything it reports.
   - The daily ledger and self-assessment for the day that just closed: numbers match the history, notes have no money totals across experiments, nothing missing.
3. Fix what is wrong, following the runbook's correction rules, and add one "Check" log entry per experiment that had a problem, saying what was wrong and what changed. If everything checks out, say so in the report and add one "Check" log entry per experiment you verified: "Daily accuracy check: no problems found."
4. Rebuild and push the site, sync the tracker (runbook step 8).
5. Work unattended: do not ask questions. Finish with a short report listing every problem found and fixed, and anything you could not verify.
Owner preferences: say "an AI model" or "the AI", never a model or company name; keep every disclaimer; never invent a price or result.
