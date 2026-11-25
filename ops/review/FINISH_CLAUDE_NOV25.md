# The finish: Claude's ten main races would not be closed like the other two's (found Nov 25)

Written Wed Nov 25, 10:00 a.m. ET. **Status: found in a rehearsal, fix prepared and tested in `ops/review/finish-claude.patch`, NOT applied.
Gemini and ChatGPT are asked (`ops/asks/finish-nov25.txt`); Claude does not vote, because it is about its own result.**

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
- To add when it is applied: one sentence in the runbook's Final scoring section and in `ops/TASK_PROMPT.md` (a bet on a game
  that started before 4:00 p.m. ET stays open; the race runner settles it; never settle or void one by hand), a corrections
  entry and a Site updates line.

Rehearsed again with the fix: Claude's ten final values recorded at 4:06 p.m. (Sports with the fine), S28 settled by the settle
watcher at 6:18 p.m. and added to Sports at the next run, the fingerprint at 9:13 p.m., "nothing left to do", and the card said
"Final. Scoring done Nov 28, 4:06 p.m. ET; the last open bet settled Nov 28, 6:40 p.m. ET", with the fingerprint and "won".

To apply: `git apply ops/review/finish-claude.patch`, `python3 ops/tests/run_tests.py` (35), the two sentences, the entries.
To undo once applied: revert that commit; before Sat 4:00 p.m. ET nothing has happened differently.

## Also seen (no public figure affected)

When the settle watcher settles a late bet of Gemini or ChatGPT, the new Sports value is written to the value history without
the "final" mark, and the stored final value is refreshed by the next normal run. If that bet was the last one open, the next
normal run stops first, so the stored final value stays the older one. The site reads the value history, so its figures are
right either way; only the internal mark is missing.
