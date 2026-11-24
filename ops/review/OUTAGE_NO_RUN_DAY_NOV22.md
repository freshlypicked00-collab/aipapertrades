# A day the runner never ran (Nov 21 to 23)

Last updated Mon Nov 23, 6:21 p.m. ET. **Status: closed for the betting minimums.** Two things about stops wait for the owner
(last section).

## What happened

- Sat Nov 21, 12:14 p.m. ET: GitHub stopped starting the project's jobs ("startup_failure", no jobs). Last good run 11:22 a.m.
  ET. The repository had been set to private around then.
- Mon Nov 23, about 1:21 a.m. ET: the repository was made public again. From 1:22 a.m. ET every job was created and failed within
  seconds with GitHub's own message: "The job was not started because your account is locked due to a billing issue."
- Mon Nov 23, 3:12 p.m. ET: the first job that ran again (the site publish; the first check-in started at 3:14 p.m.). About
  51 hours in all.
- Gemini and ChatGPT: last check-in Sat 11:15 a.m. ET, next one Mon 3:16 p.m. ET. None at all on Sun Nov 22.
- Claude: its hourly update does not go through GitHub and kept running, but its orders are placed by the same runner, so Claude
  placed no trade and no bet either (0 and 0). Its Sunday bets were queued just after midnight and never placed.
- The site was not updated from Sat 11:22 a.m. ET to Mon 3:13 p.m. ET. The automatic posts did not go out.

## Betting minimums: what was decided, and by whom

The outage rule of Nov 18 (Claude and Gemini agreed, 2 of 3) covers an ET day on which an AI had no successful check-in because
its API credit or service was down. The code found such a day from the runner's record of failed check-ins, so a day on which
the runner itself never ran (no record at all) was not seen as one.

1. **Mon 1:22 a.m. ET** (commit `7151f593`, Claude's backup chat, with the owner's OK as that chat recorded): a finished ET day
   with no check-in on record at all is an outage day for Gemini and ChatGPT. Put in before the vote, because a vote needs a run.
2. **Mon 3:16 p.m. ET**, the first run: Gemini and ChatGPT were not fined for Sunday. Claude was fined C$500 in Sports and C$500
   in High risk: Sports, because by the letter of the Nov 18 rule its own updates had run.
3. **Mon 3:26 p.m. ET**, the vote (`ops/asks/outage-no-run-day.txt`, answers in `ops/review/outage-no-run-day.json`, Claude's
   own vote written first in `ops/review/claude-votes-outage-no-run-day.json`):

| Question | Claude | Gemini | ChatGPT | Result |
|---|---|---|---|---|
| Q1 a day the runner never ran counts as an outage day | YES | YES | YES | all three agreed |
| Q2 the same remedy as now, nothing more | YES | YES | YES | all three agreed |
| Q3 a partly missed day still owes the minimum | KEEP | KEEP | KEEP | all three agreed |
| Q4 Claude's fines for Sun Nov 22 | no vote (its own fine) | WAIVE | WAIVE | Gemini and ChatGPT: waive |
| Q5 anything else unfair | one note | NOTHING | NOTHING | |

4. **Mon 5:33 p.m. ET** (commit `8dc34a778`, this chat): the vote recorded in the race code. `NO_RUN_VOTE` says who agreed; Nov 22
   is a voted outage day for Claude (`OUTAGE_VOTED`) with its own "who decided" sentence (`OUTAGE_CITE`); the rule text each AI
   reads has the new sentence; a refund of Claude's High risk fine now writes a ledger line (a bug from Nov 18, never triggered
   before). Race tests: 30 of 30.
5. **Mon 6:17 p.m. ET**, the next run: Claude's two fines were refunded, once. Sports through `claude_penalties_refunded`,
   High risk: Sports with the ledger line `RA-2026-11-22`. Sun Nov 22 is now excused for all three, C$3,000 off each total.

To reverse step 4: `git revert 8dc34a778` (then rebuild). To reverse step 1 as well:
`git apply -R ops/review/outage-no-run-day.patch` on the code as it was before step 4. Either way the fines for the day are
charged again at the next run. `ops/review/outage-no-run-day-followup.patch` is now part of step 4 and kept only as a record.

## Missed while nothing ran

- **Posts.** The posting job only sends what is new in the push that started it, so nothing is sent late on its own. Not posted:
  Claude's daily closes for Sat Nov 21 and Sun Nov 22 (Telegram, Discord, the daily X card), the daily cards and videos, and
  everything the runner posts for Gemini and ChatGPT. Posting any of it late is the owner's call.
- **Nightly fingerprint.** None of its own for Nov 21. The one for Nov 22 was published Mon 3:16 p.m. ET and covers every ledger
  line up to its close.
- **Bets.** Games played meanwhile were settled once, at ESPN's final scores, Mon 3:16 p.m. ET. Claude's queued bets on games
  that had started were refused.
- **Options.** Nobody held an option, so no expiry was missed.

## Two things about stops, waiting for the owner

Found on Nov 23 while checking the outage. Question `ops/asks/stops-nov23.txt`, asked Mon 5:47 p.m. ET, answers in
`ops/review/stops-nov23.json`, Claude's own vote first in `ops/review/claude-votes-stops-nov23.json`. The question said that
nothing would be applied on a vote alone, so **nothing has been changed**.

**A. ChatGPT's two SQQQ stops filled 51 hours late.** Stops at US$56.20 (Stocks) and US$55.90 (High risk: Trading); last price
before the outage US$57.59; both crossed while nothing ran and filled at the first run back at US$45.61. The rule says a
crossed stop fills at the live price the runner sees then. All three AIs ask the owner for a remedy: restate both fills at the
1-minute price of the first scheduled check-in after each stop was crossed (Mon 9:35 a.m. ET if SQQQ opened below them), as a
cash correction, the way the Oct 31 fills were restated (`ops/src/price_corrections.json`); if that price cannot be
established, keep US$45.61.

**B. China: no stop can be checked in an open Shanghai session, and no order has filled, since Oct 30.** The fresh-price rule
of Oct 31 (no fill and no stop on a previous close; a quote at most 3 minutes old in an open market) is never met by the feed's
Shanghai quotes while that market is open. The runner's own logs: every China stop and target skipped with "no price now (no
price from today's session yet)" in 14 of 14 runs on Fri Nov 20 and in the samples taken on Nov 4, 10 and 17. ChatGPT's stop on
the CSI 300 ETF (4.05 yuan) has been crossed since Thu Nov 19, 9:16 p.m. ET and is still waiting. All three AIs want China
orders and stops to use the newest price up to the feed's measured delay plus 5 minutes (never more than 30), from the next
Shanghai session after the owner agrees, with nothing restated for the past. A log-only line (`china feed age:`) measures the
delay from Mon Nov 23's evening session on; it changes no price, fill or stop. **Measured that evening: 15 minutes.** The rest of
this story (the second vote, on buys; the prepared patch) is in `ops/review/CHINA_FEED_NOV23.md`.

Never start, cancel or rerun a race check-in by hand.
