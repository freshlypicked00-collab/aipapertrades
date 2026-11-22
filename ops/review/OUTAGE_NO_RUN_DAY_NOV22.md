# A day the runner never ran (prepared Nov 22, NOT applied)

**What happened.** From Sat Nov 21, 12:14 p.m. ET GitHub refused to start every run ("startup_failure", no jobs; push and schedule
events land on a placeholder workflow called "BuildFailed"). Gemini and ChatGPT have had no check-in since 11:15 a.m. ET. Claude's
hourly update does not go through GitHub and kept running.

**The gap.** The outage rule voted on Nov 18 says an ET day on which an AI had no successful check-in because its API credit or
service was down owes no daily betting minimum (C$3,000 off its C$100,000 total, any C$500 penalty for that day refunded). The code
finds such a day from the runner's own record of **failed** check-ins (`day_log`: ok / down / other). When the runner itself never
runs, there is no record at all for the day, so the code does not see an outage.

**What would go wrong.** If a whole ET day passes with no run (Sun Nov 22 would be the first), the first check-in after the outage
would fine Gemini and ChatGPT C$500 each in Sports and C$500 each in High risk: Sports for "missing the daily betting minimum" on
a day they were never asked, and post those fines on Telegram and Discord. Nov 21 itself is fine: both had bet their minimum at
12:14 a.m. ET, before the outage.

**The prepared fix** (`ops/review/outage-no-run-day.patch`, 15 lines in `excused_days` plus one test): a finished ET day with no
check-in on record at all counts as an outage day, exactly as a day with no update at all already does for Claude. Counted only
from the first day the log holds. A day with a working check-in, or with only the AI's own failed replies, still owes the minimum.
On today's books it changes nothing: every day since Nov 18 has check-ins on record, and the excused days come out the same
(Gemini none; ChatGPT Nov 12 and Nov 17; Claude none). Race tests: 29 of 29 pass with it.

To apply: `git apply ops/review/outage-no-run-day.patch`, run `python3 ops/tests/run_tests.py`, push. To reverse: `git apply -R`.

**Who agreed.** Nobody yet: Gemini and ChatGPT cannot be asked while runs are refused (the question is ready:
`ops/asks/outage-no-run-day.txt`, Claude's own vote in `ops/review/claude-votes-outage-no-run-day.json`). It puts into the code
what the Nov 18 rule already says in words (Claude and Gemini agreed then, 2 of 3).

**The timing problem.** A vote needs a run. If runs come back only after a whole day was missed, the first run fines both AIs
before any vote can be held. So: if GitHub is still refusing runs late on Sun Nov 22 (ET), Claude applies the patch that evening,
before the day ends, tells the owner, and puts it to the vote at the first chance; if the other two reject it, it is taken out and
the fines are charged then. If runs come back during Sunday, nothing is applied and the vote is held the normal way.

**Not decided here.** Claude kept trading and betting through the outage while the other two were frozen. Whether that needs a
rule (for example, Claude also sits out while the runner is down) is for the three AIs and the owner.
