# Finale run sheet: Saturday Nov 28, 2026 (Season 1, Day 32)

Written Nov 19 in the improvement pass, after a dress rehearsal (the site opened with the clock set past the finish, every tab, phone and
computer). All times ET. "Runner" = the Head to head workflow (rivals.yml). Nothing here changes a rule.

## What happens by itself
| When | What | Where to look |
|---|---|---|
| Fri Nov 27, 1:00 p.m. | Last US trading day closes early (day after Thanksgiving). Stocks, options, metals and energy funds can no longer trade; crypto, currencies, bets and prediction markets go on. | Runner log |
| Sat Nov 28, until 4:00 p.m. | Normal hourly check-ins (about :13 past the hour). Crypto, bets and prediction markets are still open. | Site, Discord, Telegram |
| 4:00 p.m. | **The finish.** No order is accepted from this second (ops/rivals.py RACE_END). The site's top line changes by itself to "Season 1 is over" and "leads" becomes "finished first" (ops/polish.js 8). | papertrades.ai |
| 4:01 p.m. (GitHub may start it up to 45 min late) | **Final scoring run**: freezes Gemini's and ChatGPT's final value in every race (`state.final`). Later runs only settle bets on games that started before 4:00 p.m. | Runner log: "final," lines |
| Claude's next update after 4:00 p.m. | Claude's ten final values, the same way. | UPDATE ALL commit |
| Evening | Bets on games still being played settle within about 15 minutes of each final whistle (the settle watcher). Only the Sports and High risk: sports totals can still move, and only by those bets. | Sports tab |
| 7:00 p.m. | The record of the last race day closes. Its fingerprint is published by the first run two hours later (9:00 p.m. or after), whatever kind of run it is (fixed Nov 24: before, it would not have been published once every bet was settled). A later day gets one only if the record changed. | Rules & Audit |
| After 9:00 p.m. | The watchdog stops watching (the race is over). | - |

## What a person must do (in order)
1. **Fri Nov 27, any time:** check API credit for the last day: OpenRouter (ChatGPT) at least US$15, Google (Gemini) billing active. The health check warns under US$15.
2. **Sat 3:45 p.m.:** open the Actions page. If a race run has been "queued" or "in progress" for more than 20 minutes, tell Claude ("the race is stalled"). Do not cancel or rerun anything by hand.
3. **Sat about 4:20 p.m.:** check the final scoring run finished (green). If GitHub has not started it by 4:50 p.m., tell Claude: the run can be started with mode "force"; it changes nothing but the freeze, because no order is accepted after 4:00 p.m.
4. **Sat evening, after the last game with an open bet ends:** the numbers are final. Only now publish the final result (below).
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
- Drafts of the card and the post: to be written with Gemini and ChatGPT in the week of Nov 23, from the real standings of that week.

## Found in the rehearsal (Nov 19)
- FIXED: after the finish the top of the site still said "0d 00h 00m 00s left until final scoring" and "leads overall" (the rule that hid the countdown hid the wrong line). See ops/polish.js 8, ops/polish.css 34. Preview: papertrades.ai/?finale
- CHECKED: every tab opens without an error with the clock at Nov 28, 4:30 p.m. ET, on a phone and a computer; no page scrolls sideways.
- NOT POSSIBLE TO REHEARSE HERE: the final scoring run itself (it needs live prices) and the posts. The code path is covered by the race tests; watch step 3.
- KNOWN: between 4:00 p.m. and the final scoring run the site shows the last check-in's values; they are replaced by the frozen ones a few minutes later.
- KNOWN: the animated cards and Shorts scheduled for Sat evening still run; they show the day's results as usual.
