# Finale run sheet: Saturday Nov 28, 2026 (Season 1, Day 32)

Written Nov 19 in the improvement pass, after a dress rehearsal (the site opened with the clock set past the finish, every tab, phone and
computer). All times ET. "Runner" = the Head to head workflow (rivals.yml). Nothing here changes a rule.

## What happens by itself
| When | What | Where to look |
|---|---|---|
| Fri Nov 27, 1:00 p.m. | Last US trading day closes early (day after Thanksgiving). Stocks, options, metals and energy funds can no longer trade; crypto, currencies, bets and prediction markets go on. | Runner log |
| Sat Nov 28, until 4:00 p.m. | Normal hourly check-ins (about :13 past the hour). Crypto, bets and prediction markets are still open. | Site, Discord, Telegram |
| 4:00 p.m. | **The finish.** No order is accepted from this second (ops/rivals.py RACE_END). The site's top line changes by itself to "Season 1 is over" and "leads" becomes "finished first" (ops/polish.js 8). | papertrades.ai |
| 4:01 p.m. (GitHub may start it up to 45 min late) | **Final scoring run**: freezes the final value of all three AIs in every race, in the same run and at the same prices (Gemini's and ChatGPT's in `final`, Claude's ten as final rows of `claude_feed`; since Nov 25). Later runs only settle bets on games that started before 4:00 p.m. Three things can start it: this timer, Claude's 4:13 p.m. hourly task, and the 4:25 p.m. task (it forces a run if the freeze is missing). | Runner log: "final," lines |
| 4:25 p.m. | Claude's scheduled task "Paper Trades: FINAL scoring": checks the freeze, backs up, writes the Final result report, sends its Telegram note, switches the hourly tasks off. It leaves a bet on a game still being played open (runbook, Nov 25). | its commit |
| Evening | Bets on games still being played settle at the race runner's first run after each final whistle, for all three AIs. The settle watcher has a timer every 15 minutes until 2 a.m., but GitHub delivers only a few of them (see "Found in the rehearsal (Nov 25)"): expect an hour or three, unless the finish watch is switched on. Only the Sports and High risk: sports totals can still move, and only by those bets. A bet of Claude's shows as settled first; its Sports total follows at the watcher's next pass, and until then the site says "its result is being added to the totals" and not "Final" (Nov 25). | Sports tab |
| 7:00 p.m. | The record of the last race day closes. Its fingerprint is published by the first run two hours later (9:00 p.m. or after), whatever kind of run it is (fixed Nov 24: before, it would not have been published once every bet was settled). A later day gets one only if the record changed. | Rules & Audit |
| After 9:00 p.m. | The watchdog stops watching (the race is over). | - |

## What a person must do (in order)
1. **Fri Nov 27, any time:** check API credit for the last day: OpenRouter (ChatGPT) at least US$15, Google (Gemini) billing active. The health check warns under US$15.
2. **Sat 3:45 p.m.:** open the Actions page. If a race run has been "queued" or "in progress" for more than 20 minutes, tell Claude ("the race is stalled"). Do not cancel or rerun anything by hand.
3. **Sat about 4:20 p.m.:** check the final scoring run finished (green). Later in the evening, if a game has ended and its bet still shows open half an hour on, tell Claude ("settle the late bets"): after the finish a run calls no AI and takes no order, it only settles and records. If GitHub has not started it by 4:50 p.m., tell Claude: the run can be started with mode "force"; it changes nothing but the freeze, because no order is accepted after 4:00 p.m.
4. **Sat evening, after the last game with an open bet ends:** the numbers are final when the Final result card says "Final" (papertrades.ai/?finale shows the card even while it is switched off). Only then publish the final result (below).
5. **Sun Nov 29:** turn off the "Race watchdog" workflow (Actions, Race watchdog, the ⋯ menu, Disable workflow): after the finish it only uses up minutes. Then the post-season steps: the correction window, the research notes, Season 2 decisions (ops/SEASON2.md).

## The final result: prepared, HELD for the owner's OK
Updated Nov 24: the card is built and switched off (preview: papertrades.ai/?finale); the card's words, its place on a phone, the one
post and the share picture were agreed by all three AIs that day. What is ready, the vote and the two words the owner can say are in
`ops/review/FINAL_RESULT_DRAFT.md`. Nothing is shown or posted yet (new public content needs the owner's yes).
- **One place to cite:** a "Final result" card at the top of the Overview (winner, the three totals, the ten race winners, the date, "pretend money", a link to the audit pack) with its own address (papertrades.ai/#final) and share picture.
- **One post on every channel**, same words, sent once after step 4: Discord #announcements, Telegram, X, Instagram, YouTube community. Totals may be named for the first time in this post ("never total the races before Nov 28").
- **The record freezes:** final fingerprint of the whole ledger, the audit pack rebuilt, and both linked from the card.
- The card must also say (Gemini and ChatGPT, Nov 19): when the last open bet settled, the time the result was made final (ET), the final fingerprint with its link, and that the result includes penalties, refunds, voided bets and every settled bet.
- The site says "finished first" from 4:00 p.m.; "won" is used only in this final post (all three AIs agreed, ops/review/improve-nov19-cde.json).
- Drafts of the card and the post: written with Gemini and ChatGPT on Nov 24 (`ops/review/FINAL_RESULT_DRAFT.md`).

## Found in the rehearsal (Nov 19)
- FIXED: after the finish the top of the site still said "0d 00h 00m 00s left until final scoring" and "leads overall" (the rule that hid the countdown hid the wrong line). See ops/polish.js 8, ops/polish.css 34. Preview: papertrades.ai/?finale
- CHECKED: every tab opens without an error with the clock at Nov 28, 4:30 p.m. ET, on a phone and a computer; no page scrolls sideways.
- NOT POSSIBLE TO REHEARSE HERE: the posts. (The final scoring run itself was rehearsed on Nov 25, below.)
- KNOWN: between 4:00 p.m. and the final scoring run the site shows the last check-in's values; they are replaced by the frozen ones a few minutes later.
- KNOWN: the animated cards and Shorts scheduled for Sat evening still run; they show the day's results as usual.

## Found in the rehearsal (Nov 25)
The race runner itself was run on a throwaway copy (no network, no posting), the clock set to Saturday, each position at its last
known price, today's open bets standing in for bets still open at the finish; the site was built after every run. The whole story:
`ops/review/FINISH_CLAUDE_NOV25.md`.
- FIXED (Gemini and ChatGPT agreed; Claude did not vote on its own result): after the finish the runner stopped writing Claude's public values and stopped settling its main Sports bets. A bet of Claude's on a game still being played would never have settled, and the card would never have said who won. Now Claude's ten main races are closed by the same rules as the other two's.
- FIXED (same vote for Claude's part; all three agreed on the rest): a late bet of Claude's was in the bet list up to an hour or more before it was in its Sports total (only an hourly run recorded it), and the site would have said "Final" in between. Now the 15-minute watcher records it, a rival's late bet goes on its final record with the final mark, and the site says "Final" only when every settled bet is in the totals.
- CHECKED: with no bet open at the finish the site says "Final" right after the final scoring run. With late bets: finish, then "its result is being added to the totals", then Final; the last day's fingerprint appears on the card after 9:00 p.m. ET. Both orders end on the same three totals.
- KNOWN, waits for the owner (`finish watch yes`): after the finish nobody starts the race runner but GitHub's own timers. Claude's runs stop at the finish and its hourly task is switched off by the 4:25 p.m. task. Counted on Nov 25 from GitHub's list of runs: the timers deliver 8 to 14 runs a day of about 150 slots; on the last two Saturdays about 4:27, 7:23, 8:52 and 9:26 p.m., then nothing until after 2 a.m. So a late bet can wait hours, and the result can become final only on Sunday morning. Nothing is lost and no rule is broken; it is slow. Prepared, agreed by all three AIs, NOT switched on: a finish watch that starts the runner every 12 minutes while something is waiting and ends by itself (`ops/review/finish-watch.patch`).
- KNOWN, waits for the owner: the 4:25 p.m. task's Telegram note is written to name "the final standings and the winner" while bets may still be open (`final post yes` or `keep the 4:25 note`, in `ops/review/FINAL_RESULT_DRAFT.md`).

## The last days: ChatGPT's API credit (written Thu Nov 26, 5:23 p.m. ET)
- The OpenRouter credit that pays for ChatGPT's calls was US$14.84 on Wed 8:20 a.m. ET (alert issue 19) and US$1.00 on Thu 5:16 p.m. ET. The owner was told on Wed at 11:00 a.m., noon (phone), 2:10 p.m. and 6:42 p.m., and on Thu at 9:35 a.m., 11:01 a.m. (phone) and 5:22 p.m. (phone). Only he can top up.
- Since Thu 2:15 p.m. ET OpenRouter refuses ChatGPT's own model: "openai/gpt-5.5: HTTP 402 This request requires more credits, or fewer max_tokens". The runner's backup answers: openai/gpt-5.4 (about US$0.11 a check-in). No check-in was missed up to 5:16 p.m. ET. The site shows the model of the latest check-in. With credit, the next check-in goes back to gpt-5.5 by itself.
- When the credit is gone every call fails with HTTP 402 (as on Nov 11 to 13 and Nov 16 to 17). A whole ET day without one good check-in is an outage day by the rule in the code since Nov 18 (no betting-minimum fine for that day, found from the runner's own records); a day with some good check-ins is not.
- FOR THE FINAL REPORT: say plainly which model answered for ChatGPT in the last days and from when (the run logs have a line "ChatGPT (openai/...)" for every check-in), and which check-ins it missed, if any.

