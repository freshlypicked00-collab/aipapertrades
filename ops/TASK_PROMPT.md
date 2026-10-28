Run one UPDATE ALL for the Paper Trades experiment.

Paper Trades is a 30-day paper-trading experiment (Oct 26 to Nov 26, 2026) in which you, acting as "an AI model", run TEN SEPARATE experiments with real-world prices. Each started with its own C$100,000 (US$100,000 for China stocks) and is judged only against its own start and benchmark. Never add them together, never quote a combined or overall total.
- Trading: Stocks (anything), Crypto, China (Shanghai/Shenzhen stocks, counted in US$), Metals, Energy (oil and energy), Options, Currencies (forex with leverage), Safe (low-risk control).
- Gambling: Sports (betting) and Predictions (prediction markets).
All except Safe are run high risk, high reward. No real money is involved and nothing is advice.

"UPDATE ALL" means: check every experiment (prices with highs and lows since the last run, game and market results, rules, opening orders), make any trades or bets the rules and evidence call for (holding is fine), then update BOTH the public website and the private tracker.

Do this:
1. Attach the GitHub repository freshlypicked00-collab/aipapertrades with push access (add_repo), clone it, `git pull`, and read ops/RUNBOOK.md. Follow the runbook exactly: data files, price standard, stop and limit orders between runs, extra runs around big events, China, Currencies and Predictions sections, the opening orders for Energy, Options and Safe at the first run after 9:30 a.m. ET on Oct 28, the sports procedure, the daily ledger (notes and self-assessment at the first run after 00:00 UTC), the input file for ops/update.py, building and pushing the site (papertrades.ai), and syncing the tracker. Every trade and bet must go through ops/update.py so it is recorded. If another run pushed while you worked, `git pull --rebase`, re-run your update on the latest data if needed, and push.
2. The private tracker is the Artifact https://claude.ai/artifact/M9pCF2ENeBxCRQDjVQogg5 (a Dashboard). Sync it as in the runbook: upload each changed ops/src/<name>.json as an asset with the Artifact tool, then update datasets/<name> with ArtifactData (read the datasets collection for versions first, write in one batch). Never edit its page.
3. Owner preferences: the site and tracker say "an AI model" or "the AI", never a model or company name; keep every disclaimer as it is; log entries are short, plain and factual; never invent or estimate a price or result. If a fresh price can't be confirmed, keep the last one and say so.
4. Work unattended: do not ask questions. If something blocks a step (no repo access, a tool refused, a quote not found), finish what you can, and report exactly what failed.
5. Finish with a short report: each experiment's value on its own line, any trades or bets with one-line reasons, settled bets and markets, extra runs scheduled, and anything you couldn't confirm.

After Nov 26, 4:00 p.m. ET, do the final scoring run described at the end of the runbook once; on later runs only confirm the final state and make no changes.
