# A day the runner never ran (Nov 21 to 23)

Last updated Tue Nov 24, 8:18 a.m. ET. **Status: closed for the betting minimums and for the two SQQQ stops** (A below; the owner
agreed Mon 9:58 p.m. ET). **Two things still wait for the owner: China (B) and options (C).**

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

## Three things found on Nov 23: one decided, two waiting for the owner

Found on Nov 23 while checking the outage. Question `ops/asks/stops-nov23.txt`, asked Mon 5:47 p.m. ET, answers in
`ops/review/stops-nov23.json`, Claude's own vote first in `ops/review/claude-votes-stops-nov23.json`. The question said that
nothing would be applied on a vote alone. A went in only once the owner had agreed; for B and C **nothing has been changed**.

**A. ChatGPT's two SQQQ stops filled 51 hours late.** Stops at US$56.20 (Stocks) and US$55.90 (High risk: Trading); last price
before the outage US$57.59; both crossed while nothing ran and filled at the first run back at US$45.61. The rule says a
crossed stop fills at the live price the runner sees then. All three AIs ask the owner for a remedy: restate both fills at the
1-minute price of the first scheduled check-in after each stop was crossed (Mon 9:35 a.m. ET if SQQQ opened below them), as a
cash correction, the way the Oct 31 fills were restated (`ops/src/price_corrections.json`); if that price cannot be
established, keep US$45.61.

*What it would come to* (worked out Mon 9:20 p.m. ET by the read-only report `ops/outage_stops.py`, from Yahoo's 1-minute bars):
SQQQ opened far below both stops. At the first scheduled run of the day, 9:35 a.m. ET, it was US$46.93, so both stops would
have filled there. Restating US$45.61 to US$46.93 gives ChatGPT **+C$181.26 in Stocks and +C$453.14 in High risk: Trading**
(C$634.40 in all). The rest of the fall from US$57.59 was the market's gap over the weekend, not the outage.

*Decided and applied.* The owner agreed on Mon Nov 23 at 9:58 p.m. ET, in another Claude chat, which entered the two
corrections as PC12 and PC13 in `ops/src/price_corrections.json` (commit `5ce113453`). The race runner applied them once, at
10:15:56 p.m. ET: ChatGPT's Stocks cash C$73,917.55 to C$74,098.81 and its High risk: Trading cash C$44,070.83 to C$44,523.97.
The two original fills at US$45.61 stay in the ledger as they were. Public: the Corrections entry on Rules & Audit, the list of
price corrections under it, and a Telegram notice (10:19 p.m. ET). Checked Tue Nov 24, about 8:10 a.m. ET, by this chat: both amounts equal
the read-only report, the race tests pass (31 of 31) and the morning's full audit found no problem. To reverse: a new entry
with the opposite amounts (an applied correction is never deleted).

**B. China: no stop can be checked in an open Shanghai session, and no order has filled, since Oct 30.** The fresh-price rule
of Oct 31 (no fill and no stop on a previous close; a quote at most 3 minutes old in an open market) is never met by the feed's
Shanghai quotes while that market is open. The runner's own logs: every China stop and target skipped with "no price now (no
price from today's session yet)" in 14 of 14 runs on Fri Nov 20 and in the samples taken on Nov 4, 10 and 17. ChatGPT's stop on
the CSI 300 ETF (4.05 yuan) has been crossed since Thu Nov 19, 9:16 p.m. ET and is still waiting. All three AIs want China
orders and stops to use the newest price up to the feed's measured delay plus 5 minutes (never more than 30), from the next
Shanghai session after the owner agrees, with nothing restated for the past. A log-only line (`china feed age:`) measures the
delay from Mon Nov 23's evening session on; it changes no price, fill or stop. **Measured that evening: 15 minutes**, and the
same in every run sampled through the whole session (900 to 910 seconds, Mon 9:15 p.m. to Tue 1:16 a.m. ET); every China stop
was skipped again in each of them. Three Shanghai sessions are left before the finale; the next opens Tue Nov 24, 8:30 p.m. ET.
The rest of this story (the second vote, on buys; the prepared patch) is in `ops/review/CHINA_FEED_NOV23.md`.

**C. Options: the price source has refused the runner since Thu Nov 19 evening.** Found Mon Nov 23, 9:17 p.m. ET, when the
price-feed test stopped on it. The runner prices options from Cboe's delayed quotes; that address now answers "403 Forbidden".
From the runner's logs it still worked at 3:14 p.m. ET on Thu Nov 19 and was refusing by 9:10 p.m. ET that evening, and it
refused again tonight. So no option order has been able to fill for any AI since Fri Nov 20: the last option fill was ChatGPT's
on Nov 18 at 9:36 a.m. ET, and Claude's QQQ put order of Fri Nov 20 was refused after six hours ("no price from the feed (HTTP
Error 403: Forbidden); check the symbol"). Nobody holds an option, so nothing is stuck. Options race now, all cash: Gemini
C$150,417, Claude C$92,815, ChatGPT C$87,009. Claude will not dress the runner up as a browser to get around a refusal. The
owner's choices: close options for the rest of the race and tell the AIs, or name another price source (it would need an account
and a key, which only the owner can set up). Nothing changed.

*Checked again Tue Nov 24, 8:21 a.m. ET* (price-feed run 45402466568, with one new read-only line that says where the request
ended up): Cboe's address now redirects to `cdn-api.cboe.com`, a host behind Cloudflare, which answers 403 with Cloudflare's
block page ("Attention Required!"). So this is a deliberate block of automated requests, not a passing fault, and the free
source is gone for the runner. The same refusal also stops the look-back figures for past option trades from refreshing
(`after:` lines in the check-in logs). Gemini and ChatGPT are being asked what they want (`ops/asks/options-nov24.txt`).

Never start, cancel or rerun a race check-in by hand.
