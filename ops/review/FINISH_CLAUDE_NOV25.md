# The finish: Claude's ten main races would not be closed like the other two's (found Nov 25)

Written Wed Nov 25, 10:00 a.m. ET; updated 10:22 a.m. ET. **Status: both parts APPLIED on Wed Nov 25 (the first at 10:02 a.m. ET, the second,
"the hours after the finish", at 10:22 a.m. ET), each after Gemini and ChatGPT agreed. Claude did not vote where its own result is concerned.
Nothing changes before Sat Nov 28, 4:00 p.m. ET, and the owner can undo either part with one word (`undo finish fix`: revert the
commits).**

## The vote

`ops/asks/finish-nov25.txt`, asked Wed Nov 25, 10:01 a.m. ET; answers in `ops/review/finish-nov25.json`.

| | Claude | Gemini | ChatGPT | Result |
|---|---|---|---|---|
| G1 after the finish the runner treats Claude's ten main races exactly as the other two's | no vote (its own result) | AGREE | AGREE | Gemini and ChatGPT agreed; applied |

Gemini: "Applying the exact same final scoring and bet settlement logic to all competitors ensures fairness and prevents the final
results from hanging." ChatGPT: "it applies the same final pricing, fines, and eligible Sports settlement rules to Claude as to the others."

## The rehearsal

On a throwaway copy of the project with no link to GitHub (no network, no posting), the clock set to Saturday: the final scoring run
at 4:06 p.m. ET, the settle watcher at 6:18 p.m., a normal run at 6:40 p.m. and one at 9:13 p.m.; then the site built from that copy
and the Final result card read with the clock on Saturday night. Prices were each position's last known price; the bets open today
(Gemini G179 and G180, ChatGPT C52 and C53, Claude's High risk C25 and its main bet S28) stood in for bets still open at the finish.

## What works as agreed

- Gemini and ChatGPT: the first run after 4:00 p.m. ET records their final values at that run's prices (26 final points in the value
  history); after that only their bets on games that started before the finish settle, and each result is added to Sports.
- Claude's two High risk books are closed the same way.
- The last day's fingerprint is published at the first run after 9:00 p.m. ET (the fix of Nov 24), then "nothing left to do".
- The share picture and the card change their words by themselves.

## What does not: Claude's ten main races

1. **Claude's public values stop before the finish.** Since Oct 31 (R4 and V5, all three agreed) every public figure of Claude's
   comes from the runner's feed, written at each check-in (`claude_feed_values`). That step returns at once after 4:00 p.m. ET, so
   Claude's final public values would be those of the last check-in BEFORE the finish: up to an hour older than Gemini's and
   ChatGPT's for Crypto and Predictions, and without a fine charged at the final run (the rehearsal's last-day fine of C$500 was
   in the record but not in Claude's Sports value, while the other two's fines were in theirs).
2. **A bet of Claude's still open at the finish is never settled.** The runner settles Claude's main Sports bets inside its fill
   step (`ops/claude_fill.py process`), and that step also returns at once after the finish. In the rehearsal S28 stayed open for
   ever and its result never counted.
3. **The runner then says "every bet is settled"** (it looks only at Gemini's, ChatGPT's and Claude's High risk bets) and stops,
   while the Final result card counts Claude's open bet and stays at "1 Sports bet is still open": it would never say who won, and
   the share picture would never say "Final standings".
4. The runbook's Final scoring section (Oct 28, older than the runner's fills for Claude) tells Claude's own task to "settle or
   void any remaining bets" at 4:00 p.m. Voiding a bet on a game still being played would not be the rule Gemini and ChatGPT get
   (their bets settle when the games end), and the task "Paper Trades: FINAL scoring" says the same: bets on games that started
   before 4:00 p.m. settle when they finish.

It can help or hurt Claude; that depends on Saturday's prices and results. Today the gap between Claude (2nd) and ChatGPT (3rd)
overall is about C$6,300, so one late bet or fine is not nothing.

## The prepared fix: after the finish the runner treats Claude's ten main races exactly as Gemini's and ChatGPT's

`ops/review/finish-claude.patch` (two files and three tests; 35 pass with it):

- `ops/rivals.py claude_feed_values`: at the first run after the finish each of Claude's ten races gets one final row, valued at
  that run like the other two's; afterwards only Sports gets a new final row, when a bet on a game that started before the finish
  settles or a fine is charged. Later price moves change nothing. Before the finish nothing changes.
- `ops/claude_fill.py`: after the finish the fill step does one thing only, settling Claude's bets on games that started before
  the finish, with the same code as the other two's (`settle_bets`) and the same publish step. No order, no stop.
- `ops/rivals.py claude_finished`: the runs go on until none of Claude's bets on a game is open and its final values are on record.
- Applied with it: the runbook's Final scoring section and `ops/TASK_PROMPT.md` now tell Claude's own task that a bet on a game
  that started before 4:00 p.m. ET stays open for the race runner to settle and is never settled or voided by hand; one line in
  Site updates.

Rehearsed again with the fix: Claude's ten final values recorded at 4:06 p.m. (Sports with the fine), S28 settled by the settle
watcher at 6:18 p.m. and added to Sports at the next run, the fingerprint at 9:13 p.m., "nothing left to do", and the card said
"Final. Scoring done Nov 28, 4:06 p.m. ET; the last open bet settled Nov 28, 6:40 p.m. ET", with the fingerprint and "won".

To apply: `git apply ops/review/finish-claude.patch`, `python3 ops/tests/run_tests.py` (35), the two sentences, the entries.
To undo once applied: revert that commit; before Sat 4:00 p.m. ET nothing has happened differently.

## Second pass: the hours after the finish (applied Wed Nov 25, 10:22 a.m. ET)

The rehearsal was run again with the first part in place, this time building the site after every run and reading what it says.

**Found.** A late bet of Claude's is settled by the settle watcher (every 15 minutes), but the bet is written to Claude's file by
that run's publish step, after the runner has stopped. The new Sports value could therefore be recorded only by a later run, and
only an hourly run did that. GitHub starts its hourly runs 30 to 45 minutes late or not at all, and Claude's own hourly task is
switched off after the finish. In between (6:33 p.m. to the next hourly run in the rehearsal) no bet was open any more, Claude's
Sports total was one bet behind, and both the Final result card and the share picture would have said "Final" with that total.
Also: when the watcher settled Gemini's or ChatGPT's last bet, their "final" entry in the records kept the old Sports value for
good (the site's figure was right; the record in the audit pack was not).

**The vote** (`ops/asks/finish2-nov25.txt`, asked 10:21 a.m. ET; answers in `ops/review/finish2-nov25.json`; Claude's vote was
written before theirs were seen):

| | Claude | Gemini | ChatGPT | Result |
|---|---|---|---|---|
| H1 the settle watcher also records Claude's final Sports value at its next pass | no vote (its own result) | AGREE | AGREE | Gemini and ChatGPT agreed; applied |
| H2 a late bet of Gemini's or ChatGPT's goes on their final record with the final mark | AGREE | AGREE | AGREE | all three agreed; applied |
| H3 the site says "Final" and "won" only when every settled bet is in the totals | AGREE | AGREE | AGREE | all three agreed; applied |

**What changed** (`ops/review/finish2-claude.patch`; one new test, 36 pass):

- `ops/rivals.py claude_value_due` and `settle_watch`: after the finish, when all ten of Claude's final values are on record and
  the Sports one no longer equals its settled bets and fines, the watcher records it (same function as the hourly run). Never
  before the finish; never before the final scoring run has valued all ten races.
- `ops/rivals.py settle_watch`: after the final scoring a rival's newly settled bet is written with `freeze_final`, as a full run
  writes it. Before the final scoring, and during the race, a plain value point as always.
- `ops/build_site.py`: the "final" verdict (the share picture's title) also needs Claude's ten final values on record and its
  Sports value equal to its settled bets and fines; the verdict is handed to the page as `finale`.
- `ops/polish.js` block 9: the card says "Final" and "won" only when that verdict is final. In the gap it keeps "finished first" and
  says: "Final scoring done (time). The last bet has settled and its result is being added to the totals, so a Sports total can
  still change. Until then this is the order at the finish."

**Rehearsed with it** (clock on Saturday, site built after every run):

| Run | What happened | The site said |
|---|---|---|
| 4:02 p.m. final scoring, three games still on | all three frozen; Claude's ten final values written | finish |
| 6:18 p.m. watcher | Gemini's and ChatGPT's bets settled, on their final record at once | finish (Claude's bet open) |
| 6:33 p.m. watcher | Claude's bet settled; written by the publish step | finish: "its result is being added to the totals" |
| 6:48 p.m. watcher | Claude's final Sports value recorded | **Final**, "won" |
| 7:13 p.m. hourly | "nothing left to do" | Final |
| 9:03 p.m. watcher | the last day's fingerprint published | Final, with the fingerprint (1,140 records in the copy) |

With no bet open at the finish the site said "Final" right after the 4:02 p.m. run. Both orders ended on the same three totals.

To undo this part alone: revert its commit; before Sat 4:00 p.m. ET nothing has happened differently.
