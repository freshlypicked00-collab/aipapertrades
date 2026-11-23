# A day the runner never ran (prepared, NOT applied)

Last updated Sun Nov 22, 9:50 p.m. ET. Status: **prepared and tested, not in the race code.** It goes in when the owner says
so, or when the majority of the three AIs has agreed, whichever comes first.

## What happened

From Sat Nov 21, 12:14 p.m. ET GitHub would not start any run ("startup_failure", no jobs; push and schedule events land on a
placeholder workflow called "BuildFailed"). Still the case at 9:48 p.m. ET on Sun Nov 22.

- Gemini and ChatGPT: last check-in Sat Nov 21, 11:15 a.m. ET. No check-in at all on Sun Nov 22.
- Claude: its hourly update does not go through GitHub and kept running, so its prices kept being refreshed in the files (the
  site itself was last published on Nov 21 at 11:21 a.m. ET, so visitors saw none of it). But its orders are placed by the same
  runner (option B, Oct 29), so **Claude placed no trade and no bet either** since the outage began (counted: 0 trades, 0 bets). Its Sunday bets were queued as on every day (C$3,000 on Kansas City in Sports at 12:16 a.m. ET, C$5,000 on
  Buffalo in High risk: Sports at 1:15 a.m. ET, plus C$5,000 on Texas queued Sat 12:15 p.m. ET) and were never placed.
- Sat Nov 21 is fine for all three: each had bet its C$3,000 minimum in both races before the outage began.
- Prediction markets (weekly minimum, week of Mon Nov 16): all three had already bought their C$3,000. Nothing is owed there.

## The gap

The outage rule voted on Nov 18 (Claude and Gemini agreed, 2 of 3) says an ET day on which an AI had no successful check-in
because its API credit or service was down owes no daily betting minimum (C$3,000 off its C$100,000 totals, any C$500 penalty for
that day refunded). The code finds such a day from the runner's own record of **failed** check-ins. When the runner itself never
runs there is no record at all for the day, so the code sees no outage.

## What the first run will do (simulated on the real books, posting switched off)

| | Fines for Sun Nov 22 | Public posts |
|---|---|---|
| Race code as it is now | Gemini, ChatGPT and Claude: C$500 in Sports and C$500 in High risk: Sports each (C$3,000 in all) | 6 |
| With the fix in before that run | Claude only: C$500 + C$500 | 2 |
| Fix put in after that run (after the vote) | The four fines of Gemini and ChatGPT are refunded at the next run, each with a ledger line; Claude's stay | 6, then 4 refunds |

Every further full day without a run adds the same again. The fix touches nothing else: only these fines, the C$3,000 off the
totals for an excused day, and the list of excused days shown on the site.

## The prepared fix (`ops/review/outage-no-run-day.patch`)

1. `no_run_days`: a finished ET day with no check-in on record at all (good or bad) is an outage day for Gemini and ChatGPT.
   Counted only from the first day the record holds; an AI that is out of the race is skipped; today is never counted.
2. A fine already charged for such a day is refunded once, and the ledger line, the public post and the AI's notice say what
   really happened ("was never asked on Nov 22 (ET): the race runner did not run at all that day"), not "API credit".
3. The standing rule text each AI reads in its prompt gets one more sentence (only once `NO_RUN_VOTE` is filled in).
4. One bug in the Nov 18 code, never triggered so far: a refund of Claude's High risk fine added no ledger line. Fixed.
5. One sentence on the site (the plain-words line for a refund) now also names the runner.

A day with a working check-in, or with only the AI's own failed replies, still owes the minimum. Claude's own test (a day with no
update at all) is **not** changed: by the letter of the Nov 18 rule Claude is fined for Nov 22. Whether that stands is question
Q4 for Gemini and ChatGPT; Claude does not vote on its own fine.

Race tests: 30 of 30 pass with it (28 today plus two new ones). On today's books it changes nothing before midnight.

## Why it is not applied yet

Claude first planned to put it in on Sunday evening without waiting. It did not: this changes who gets fined, the other two
have not been asked (a question needs a run), and the owner has not answered. The words of the Nov 18 rule ("its API credit or
service") do not plainly cover the race's own runner, so this is a new reading, not a typo fix. The race already has a tested way
to put a wrong fine right (fine, vote, refund with a ledger line: ChatGPT, Nov 12 and 17), so waiting costs public noise, not money.

## To apply (owner's word, or after the vote)

1. `git pull --rebase origin main`, then `git apply ops/review/outage-no-run-day.patch`.
2. In `ops/rivals.py` set `NO_RUN_VOTE` to who agreed (for example `'Gemini and ChatGPT agreed, Nov 23'`).
3. Only if Gemini and ChatGPT waive Claude's fines (Q4): add Claude's days to `OUTAGE_VOTED` with the reason in words.
4. `python3 ops/tests/run_tests.py` must pass (30). Commit the three files, push. Never start, cancel or rerun a check-in by hand.
5. Site updates line and a correction entry with the exact times. Tell the owner who agreed.

To reverse: `git apply -R ops/review/outage-no-run-day.patch`. Fines for those days are then charged at the next run.

## The vote

Question: `ops/asks/outage-no-run-day.txt`. Claude's own vote, written first: `ops/review/claude-votes-outage-no-run-day.json`.
Before sending, bring four facts in the question up to date: when runs came back, which full days were lost, whether the
first run has already charged the fines, and what happened to any stop crossed while the runner was down (ChatGPT's stop on the
CSI 300 ETF at 4.05 yuan was crossed at Monday's Shanghai open, about 3.98; the runner fills it at the live price when it is back). Send it before the Ledger question (`ledger-nov21`). If Gemini and ChatGPT split on Q4,
there is no majority and Claude's fines stay unless the owner decides otherwise.

**Applied** Mon Nov 23, 1:22 a.m. ET by Claude (the backup chat), with the owner's OK ("ok", 1:21 a.m. ET), before the repository is made
public again. Cause of the outage: the repository went **private** on Sat Nov 21 between 11:22 a.m. ET (the last run, still unbilled,
so still public) and 12:14 p.m. ET (the first refused run); every run since failed to start ("startup_failure"). Sunday Nov 22 passed
with no check-in at all, so without this the first check-in would have fined Gemini and ChatGPT for it. Checks: race tests 29 of 29
pass; the excused days on the records before Sunday are the same with and without it (Gemini none; ChatGPT Nov 12 and Nov 17; Claude
none). The vote is still owed: dispatch `ops/asks/outage-no-run-day.txt` as soon as runs start again.
