# A day the runner never ran

Last updated Mon Nov 23, 8:10 a.m. ET.

**Status: the fix is IN the race code** since Mon Nov 23, 1:22 a.m. ET (commit `7151f593`, put in by Claude's backup chat with
the owner's OK, "ok" at 1:21 a.m. ET, as that chat recorded). **The vote is still owed.** Nothing has run yet, so nobody has
been fined or refunded.

## What happened

- Sat Nov 21, around noon ET: the repository went private (between the last good run at 11:22 a.m. and the first refused one at
  12:14 p.m.). From then GitHub started no run at all ("startup_failure", no jobs).
- Mon Nov 23, about 1:21 a.m. ET: the repository was made public again.
- Since 1:22 a.m. ET every run is created and its job fails within seconds. GitHub's own message on each job:
  **"The job was not started because your account is locked due to a billing issue."** Still so on the newest run (7:15 a.m. ET).
  Only the owner can clear that (GitHub, Settings, Billing).
- Gemini and ChatGPT: last check-in Sat Nov 21, 11:15 a.m. ET. No check-in at all on Sun Nov 22.
- Claude: its hourly update does not go through GitHub and kept running, so its prices kept being refreshed in the files (the
  last successful publish of the site was Nov 21 at 11:21 a.m. ET). But its orders are placed by the same runner (option B,
  Oct 29), so **Claude placed no trade and no bet either** since the outage began (counted: 0 trades, 0 bets). Its Sunday bets
  were queued as on every day (C$3,000 on Kansas City in Sports at 12:16 a.m. ET, C$5,000 on Buffalo in High risk: Sports at
  1:15 a.m. ET) and were never placed.
- Sat Nov 21 is fine for all three: each had bet its C$3,000 minimum in both races before the outage began.
- Prediction markets (weekly minimum, week of Mon Nov 16): all three had already bought their C$3,000. Nothing is owed there.
- No stop or target of any AI is checked while nothing runs. ChatGPT's stop on the CSI 300 ETF at 4.05 yuan was crossed in
  Monday's Shanghai session (Claude's hourly update saw 3.983 at the open and 4.02 at the close). The runner fills it at the
  live price when it is back.

## The gap, and what went in

The outage rule voted on Nov 18 (Claude and Gemini agreed, 2 of 3) says an ET day on which an AI had no successful check-in
because its API credit or service was down owes no daily betting minimum (C$3,000 off its C$100,000 totals, any C$500 penalty for
that day refunded). The code found such a day from the runner's own record of **failed** check-ins. When the runner itself never
runs there is no record at all for the day, so the code saw no outage.

In the code now: a finished ET day with no check-in on record at all (good or bad) is an outage day for Gemini and ChatGPT.
Counted only from the first day the record holds; today is never counted. A day with a working check-in, or with only the AI's
own failed replies, still owes the minimum. Claude's own test (a day with no update at all) is **not** changed.

## What the first run will do (simulated on the real books, posting switched off)

| First run comes | Gemini and ChatGPT | Claude | Public posts |
|---|---|---|---|
| Today, Mon Nov 23 | No fine. Sun Nov 22 is excused, C$3,000 off each C$100,000 total | Fined C$500 in Sports and C$500 in High risk: Sports for Sunday | 2 |
| Tomorrow, Tue Nov 24 | No fine. Sunday and Monday excused, C$6,000 off | Fined for Sunday and Monday: C$2,000 in all | 4 |

Claude is fined by the letter of the Nov 18 rule: its test is "no update all day", and its updates ran. Whether that stands is
question Q4 for Gemini and ChatGPT; Claude does not vote on its own fine. Race tests: 29 of 29 pass on main.

## Still prepared, NOT in the code (`ops/review/outage-no-run-day-followup.patch`, for after the vote)

1. The standing rule text each AI reads in its prompt gets one more sentence, with who agreed (`NO_RUN_VOTE`).
2. If a fine for a day the runner never ran ever has to be refunded, the ledger line, the public post and the AI's notice say
   what really happened ("was never asked on Nov 22 (ET): the race runner did not run at all that day"), not "API credit".
3. One bug in the Nov 18 code, never triggered so far: a refund of Claude's High risk fine added no ledger line. Needed only if
   Gemini and ChatGPT waive Claude's fines.
4. One sentence on the site (the plain-words line for a refund) also names the runner.
5. An AI that is out of the race is skipped; the comment in the code no longer says "proposed".

Race tests with it: 30 of 30. On today's books it changes nothing: same fines, same excused days as the table above.

## To reverse what went in

`git apply -R ops/review/outage-no-run-day.patch` (that file is exactly the change of `7151f593`), run the race tests, push.
The fines for those days are then charged at the next run.

## The vote

Question: `ops/asks/outage-no-run-day.txt`. Claude's own vote, written first: `ops/review/claude-votes-outage-no-run-day.json`.
Before sending, bring the facts in the question up to date: when runs came back, which full days were lost, what the first run
charged, and what happened to ChatGPT's CSI 300 stop. Send it before the Ledger question (`ledger-nov21`).

- If Gemini and ChatGPT both say NO to Q1: take the fix out again (see above).
- If the majority says YES: apply the follow-up patch, set `NO_RUN_VOTE`, run the tests (30), push.
- Q4 (Claude's fines): only if Gemini and ChatGPT both say WAIVE, add Claude's days to `OUTAGE_VOTED` with the reason in words.
  If they split there is no majority and Claude's fines stay unless the owner decides otherwise.
- Then: a Site updates line and a correction entry with the exact times, and tell the owner who agreed on each point.

Never start, cancel or rerun a race check-in by hand.
