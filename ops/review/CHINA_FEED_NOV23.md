# China: no stop could fire and no order could fill since Oct 31 (prepared fix, NOT applied)

Written Mon Nov 23, 9:20 p.m. ET; last checked Wed Nov 25, 9:47 a.m. ET. **Status: waiting for the owner.** The fix is prepared
and tested in `ops/review/china-feed-delay.patch`; nothing in the race code has changed except one log line that measures the
feed. **Two Shanghai sessions are left before the finale: they open Wed Nov 25 and Thu Nov 26 at 8:30 p.m. ET.**

*The session of Tue Nov 24 (8:30 p.m. to Wed 2:00 a.m. ET) passed the same way*, the third since the fault was found: the feed 900 to
910 seconds behind in the runs sampled (Tue 10:19 p.m., Wed 1:16 a.m. ET), all four China stops and targets skipped. The CSI 300 fund
closed that session at 3.970 yuan (4.033 the day before), so ChatGPT's stop at 4.05 is now 0.08 yuan a share behind the market on
32,000 shares (2,560 yuan, about US$350); Claude's stop on the same fund is at 3.85 and has not been reached.

## What is wrong

The fresh-price rule voted on Oct 31 says: no fill and no stop on a previous close, and in an open market the quote must be at
most 3 minutes old. The price feed for Shanghai and Shenzhen runs 15 minutes behind, so while that market is open the test is
never passed. Since Oct 31:

- no China stop or target has been checked in an open session, for any AI;
- no China order has filled. The last China fill by any AI was on Oct 30.

Evidence, from the runner's own logs: every China stop and target skipped with "no price now (no price from today's session
yet); kept for the next run" in 14 of 14 runs on Fri Nov 20, and in the samples taken on Nov 4, 10 and 17 (ChatGPT's stop and
target on the CSI 300 ETF, Claude's two stops). ChatGPT's stop on the CSI 300 ETF (4.05 yuan, placed Nov 14) has been below its
level since Thu Nov 19, 9:16 p.m. ET and is still waiting.

Where each AI stands in China (Nov 23, evening): Claude two ETFs, about -US$590; ChatGPT 32,000 CSI 300 ETF, about -US$950;
Gemini cash only, about -US$2,570.

## Measured (Mon Nov 23 evening session, the runner's new log line "china feed age:")

| Time (ET) | Symbol | The feed's newest price was |
|---|---|---|
| 8:38:59 p.m. (9 minutes after the open) | 510300.SS, 510880.SS | the previous close, 18.6 hours old |
| 8:41:30 p.m. | 510300.SS, 159915.SZ | a pre-open price, 988 and 910 seconds old |
| 8:46:36 p.m. | 510300.SS, 510880.SS | 900 and 902 seconds old |
| 8:47:45 p.m. | 159915.SZ, 510300.SS | 901 and 903 seconds old |

So the feed is 15 minutes behind, and for the first 15 minutes of a session it shows only prices from before the session.
The rest of that session gave the same answer in every run sampled (Mon 9:15 p.m., 10:15 p.m., Tue 12:16 a.m., 12:58 a.m. and
1:16 a.m. ET): 900 to 910 seconds, and all four China stops and targets (ChatGPT's stop and its target, Claude's two stops) skipped each time.

## The votes

1. `ops/review/stops-nov23.json` (asked Mon 5:47 p.m. ET; Claude's own vote first in `claude-votes-stops-nov23.json`): should
   China orders and stops be allowed to use an older price? **Claude YES, Gemini YES, ChatGPT YES.** How old: the measured delay
   plus 5 minutes, never more than 30; only from the next session after the owner agrees; nothing restated for the past.
   All three.
2. `ops/review/china-feed-nov23.json` (asked Mon 9:08 p.m. ET, with the measurement): exits only, or buys too? A 15-minute-old
   price can in principle be gamed, which is why new futures positions were stopped on Oct 31 (R2).
   **Gemini: BUYS TOO**, with no buy in the first 30 minutes after the open. **ChatGPT: EXITS ONLY.**
   **Claude: no vote** (it is first in China, and exits only would lock the other two out, which favours it).
   So there is no majority on buys. Both of them accept exits.

One fact that bears on the gaming worry: the automatic fill check (in force since Oct 31) already compares every fill with the
1-minute bar of its own minute about 20 minutes later and restates it if it is more than 0.3% outside that bar. A China fill at
a 15-minute-old price would be put right the same way, so what could be gained from the lag is small.

## The prepared fix (`ops/review/china-feed-delay.patch`)

- A China price (.SS, .SZ) up to 20 minutes old counts as live (`MAX_AGE_CN`). A price from before the session is never used,
  however recent, so nothing fills in about the first 15 minutes after the open or after the lunch break.
- `CN_NEW_BUYS = False`: sells, stops and targets only; a buy is refused with a plain message. Set it to `True` for buys too:
  then a buy is refused before 10:00 a.m. Beijing (`CN_BUY_FROM`), the guard Gemini and Claude named.
- The rule text each AI reads says so, and a notice tells them once. The independent fill check uses the same limit.
- One sentence in the public Rules list.

Race tests with it: 38 of 38 (two new; run again Wed Nov 25, 10:25 a.m. ET on the current code, which has 36 of its own since
the two finish fixes of that morning; the patch still applies cleanly). Simulated on the real books for Tuesday's session with a 15-minute-old price of 4.02:
ChatGPT's waiting stop fills (32,000 CSI 300 ETF sold, about US$19,300), nothing else moves. As the code is today, the same run fills
nothing.

## To apply (only on the owner's word)

1. `git pull --rebase origin main`, then `git apply ops/review/china-feed-delay.patch`.
2. In `ops/rivals.py` set `CN_NEW_BUYS` (False = exits only, True = buys too) and `CN_RULE_DAY` to the day it goes in.
3. If buys too: in `ops/src/index.html` change the new sentence in the Rules list to say "a China order, stop or target uses a
   price up to 20 minutes old, and buys fill only from 10:00 a.m. Beijing time" instead of "new China buys are refused".
4. `python3 ops/tests/run_tests.py` must pass (34). Publish. Never start, cancel or rerun a check-in by hand.
5. A Site updates line and a correction entry: since Oct 31 no China order or stop could fill while Shanghai was open; what
   changes; who agreed and who decided.

To reverse: `git apply -R ops/review/china-feed-delay.patch` (after setting the two switches back), tests, publish.
