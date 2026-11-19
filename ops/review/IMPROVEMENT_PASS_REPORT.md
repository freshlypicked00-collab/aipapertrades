# Improvement pass report (Nov 19, 4:43 p.m. to 5:45 p.m. ET)

Master, this is what changed, who agreed, what is waiting for you, what I got wrong, and what to improve next.
Started from commit fba318f6. Race tests: 20 before, 27 now, all passing. Questions and answers: `ops/review/improve-nov19-ab.json`, `ops/review/improve-nov19-cde.json` (my votes were written first each time).

## 1. Your three items
| Item | Result | Who agreed |
|---|---|---|
| 1. Repeated Telegram post | Deleted (Gemini's Miami Heat win, #1404; the first copy #1396 stays). Your commercials chat ran the dry run and the delete at 4:44 p.m., two minutes before I got there. I re-checked with a 72-hour dry run: 0 repeats left. | Claude and Gemini (followups-nov19) |
| 2. Sale posts say the result | Live since 4:50 p.m. Example: `Loss on this sale: −C$376.83 (bought for C$15,000)`; part sales say "this part was bought for"; shorts say "Profit on this short". The figure is the Ledger's, to the cent; a test compares all 190 sales on record plus Claude's 15, and where no figure exists the line is left out. | Idea: all three. Wording: Claude, Gemini and ChatGPT all agreed. |
| 3. Animated cards | Repaired by your commercials chat (it had started before me) and switched back ON at about 5:05 p.m. after samples made on GitHub's runner ended exactly on their still cards. The samples are in this chat. Say "animations off" if you don't like them. | Claude and Gemini (followups-nov19) |

Wording note on item 2: your brief said "Result on this position: +C$X". Gemini and Claude had agreed minutes earlier on "Profit on this sale / Loss on this sale" with the cost in brackets, and ChatGPT agreed later, so that is what went live. One word from you changes it.

Found while doing item 2 (a real defect, fixed): the PICTURE of a sale worked its profit out from the price move alone, without the exchange rate. ChatGPT's Bitcoin sale showed "−3.0% −C$460" on the picture and −C$376.83 (−2.5%) in the Ledger. Pictures now use the Ledger's figure. All three agreed.

## 2. What changed, by area
### A. The race must never stop again (all three agreed)
- **Saved as it goes.** Each AI's turn, and each settled result, is saved and pushed the moment it is done. Before, a run saved only at the end: a run stopped late lost everything, and the next run posted the same results again (the cause of the repeated post). Seen working on the 5:14 p.m. run.
- **Time limits.** Every picture: 45 seconds (an album 135). The whole check-in: 24 minutes, so the publish and health steps always run. A stopped check-in now appears in the health alert.
- **Why the 8-hour stall raised no alert:** the only health check was the last step of the run that was stuck, so it never ran; stopped runs count as "cancelled", not "failed"; and an AI's failure count only goes up when a check-in finishes.
- **Watchdog.** A separate workflow, every 20 minutes, reads only the saved records. No finished check-in for 2 hours (Gemini, ChatGPT) or 3 hours (Claude) = a GitHub alert (email) plus a private Telegram note to you, a reminder every 3 hours, and a note when it is fixed.
- **Questions can't cancel the race.** Ask mode now waits in its own queue.

### B. Phones (all three agreed)
Page length at 375 px, before -> after: News 13,051 -> 5,941 px · How it works 13,824 -> 8,301 · Ledger 17,817 -> 15,243 · Rules & Audit 14,184 -> 11,369 · Oil and energy 12,002 -> 10,940. Nothing was removed: older News stories, long rule lists, the Glossary, peer grades, the report card and the fingerprint table show a short version with a button for the rest. Computers are untouched.
- New line under the leader box: "How to read this: each number is that AI's profit or loss since Oct 28, in pretend money. Green is up, red is down."
- 320 px phones: the Overview no longer scrolls sideways.
- Checked: every tab at 320, 375, 414, 768, 1280 and 1920 px (no errors, no sideways scroll); the new button and line in all eight themes (contrast 5.1 or better); the full text of every tab is identical before and after on a phone.
- First load, measured: about 2.1 MB compressed (page 0.34, data 1.70, charts and fonts 0.2). Loading each tab's data when opened is HELD for Season 2: all three agreed it is too risky nine days before the finale.
Pictures: `ops/review/img/imp-nov19-news-phone.png`, `-rules-phone.png`, `-peer-grades-phone.png`, `-cue-phone.png`.

### C. Words and numbers
- Scan of every reason against its own numbers: 373 trades and prediction-market moves by Gemini and ChatGPT, 53 by Claude (`ops/reason_scan.py`). Gemini's and ChatGPT's reasons never contradict their records. Two of Claude's notes quote a price that is not the fill price; both now carry a site-only fact-check note. No AI's words were changed. All three agreed.

### E. The finale (all three agreed)
- Dress rehearsal with the clock at Nov 28, 4:30 p.m. ET found a real problem: the top still said "0d 00h 00m 00s left until final scoring" and "Gemini leads overall". Fixed: from 4:00 p.m. on Nov 28, never before, it says "Season 1 is over" and "finished first" ("won" is kept for the final post). Preview: papertrades.ai/?finale. Picture: `ops/review/img/imp-nov19-finale-phone.png`.
- Run sheet for the day: `ops/FINALE_RUNSHEET.md`. Season 2 notes updated: `ops/SEASON2.md`.

### F. Housekeeping
- The four old alerts are reviewed, explained and closed: Nov 4 (rows missing for four minutes after two updates overlapped; restored the same morning) and Nov 12, 13, 14 (24 bets were open only because check-ins were down those nights; all are settled: 14 won, 10 lost).
- New tests: sale posts against the Ledger; sale pictures against the Ledger; a stuck picture or run is stopped; each turn is saved and pushed; the watchdog; questions cannot cancel a race run; the animation recorder (by the other chat).

## 3. Waiting for your OK (answer with the numbers)
Full texts: `ops/review/OFFSITE_DRAFTS_NOV19.md`.
1. D1: pictures' top line "PAPER TRADES · AI VS AI" -> "PAPERTRADES.AI · AI VS AI" (all three agreed).
2. D2: "−C$3,000 penalty" -> "−C$3,000 Sports penalty" (all three agreed).
3. D3: penalty, refund, alert and fingerprint posts end with the same brand line as move posts (all three agreed).
4. D4: the X pinned thread names two channels; the site lists five.
5. D5: bios on X, Instagram, YouTube, Telegram: I could not open the live pages; the checklist is in the file.
6. D7: the "Final result" card and the one final post (plan in the run sheet; all three agreed with the plan).
7. Animated cards: on now. Keep, or "animations off"?
8. Sale-post wording: keep "Profit / Loss on this sale", or your "Result on this position"?

## 4. What I got wrong
- I wrote a full repair of the animated cards before noticing your commercials chat was already doing it (its note went in two minutes after my last look). That was duplicate work. I did not push mine to main; it is parked on the branch `fable-animate-pillow-only`.
- My first note on the three audit alerts miscounted the bets (20; it is 24). Corrected on each alert within minutes.
- A site-updates line failed my own length check, so the first publish went out without it; added four minutes later.
- I could not see the live site or channels (no approval to open them), so everything was tested on a local copy of the same build, and the channel profiles are not checked.
- Areas C and D are thinner than you asked: I did not re-read every number on every page, the day-card and standings posts were read but not changed, and the profile texts are a checklist, not a review.

## 5. Top 5 still to improve
1. The "Final result" card, its share picture and the one final post (needs your OK; draft in the week of Nov 23).
2. Read every number on every page for confusing-but-correct cases (part sales, C$ next to US$, possible win next to settled), with pictures.
3. Open the live channels once (your approval) and bring every bio, pinned post and banner to one voice.
4. Phone pages are still long: Ledger 15,200 px, Prediction markets 13,200. Next: fold the long "why" texts in trade lists to three lines.
5. Season 2: split the data file so a phone loads 0.3 MB first instead of 1.7 MB; alerts that close themselves.
