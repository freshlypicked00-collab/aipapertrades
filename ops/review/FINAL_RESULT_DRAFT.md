# The final result: the card and the one post (HELD for the owner's OK)

Written Tue Nov 24, 2:39 p.m. ET. **Status: ready and switched off. Waiting for the owner's two words: `final card yes` and
`final post yes`.** Nothing here is shown to visitors or posted until then.

## The card

It has existed since Nov 20 in `ops/polish.js` block 9, hidden behind `FINAL_LIVE = false`. Anyone can preview it at
papertrades.ai/?finale. With `FINAL_LIVE = true` it appears by itself from Sat Nov 28, 4:00 p.m. ET at the top of the Overview,
with its own address (papertrades.ai/#final). Every figure is read from the same data as the leader box and the race standings.

Its status line changes by itself:

| When | Status line | Headline |
|---|---|---|
| after 4:00 p.m., before the final scoring run | "The race ended at 4:00 p.m. ET. Final scoring is being done now; the figures below are from the last check-in." | "... finished first with the most total profit" |
| scored, a bet still open | "Final scoring done (time). N Sports bets are still open, so the Sports totals can still change. Until then this is the order at the finish." | "... finished first ..." |
| scored, no bet open | "Final. Scoring done (time); the last open bet settled (time). Includes every penalty, refund, voided bet and settled bet. Nothing changes after this." and the final fingerprint line | "... won Season 1 ..." |

Changed on Nov 24 (still hidden):
- **The final fingerprint line** (Gemini and ChatGPT asked for it on Nov 19): the first nightly fingerprint whose daily close
  comes after the finish and after the last bet settled, its first 16 characters, the number of records, and a button to Rules &
  Audit where anyone can re-check it. Until that fingerprint exists the line says it is published after the next daily close.
- **On a phone it sits right under the podium** and leaves out its own list of the three totals there (the podium shows them).
  Before, it sat about two and a half screens down, after "The ten races".
- On a computer the three totals sit side by side; the four buttons have the same height; the first-visit tour offer stays off it.

Rehearsed with the clock set to Sat Nov 28, 11:30 p.m. ET and stand-in data (final points, no open bet, a made-up fingerprint):
the card moves through its states by itself, phone and computer, no sideways scroll, no error.

## The one post

The same words on Discord, Telegram, X, Instagram and the YouTube community tab, sent once when the card says Final. Names and
numbers are filled in then. 265 characters by X's count with today's numbers.

```
🏁 PaperTrades.AI Season 1: final result

🥇 (1st, with its model) won: (total)
🥈 (2nd, with its model): (total)
🥉 (3rd, with its model): (total)

Ten races, one month, pretend money, real prices. Every trade and bet: https://papertrades.ai/#final

Not investment or betting advice.
```

## The vote

`ops/asks/final-nov24.txt`, asked Tue Nov 24, 2:28 p.m. ET; answers in `ops/review/final-nov24.json`; Claude's vote first in
`ops/review/claude-votes-final-nov24.json`.

| | Claude | Gemini | ChatGPT | Result |
|---|---|---|---|---|
| F1 the card's words | AGREE | AGREE | AGREE (one bet "is", several "are": the card already does) | all three agreed |
| F2 place on a phone | UNDER PODIUM | UNDER PODIUM | UNDER PODIUM | all three agreed; done (hidden) |
| F3 the one post | AGREE | AGREE | AGREE | all three agreed; waits for the owner |
| F4 share picture: "Standings at the finish", then "Final standings" | AGREE | AGREE | AGREE | all three agreed; done (`ops/build_site.py`; nothing changes before the finish) |
| F5 the last fingerprints must still be published after the finish | AGREE | AGREE | AGREE | all three agreed; done (below) |

## Found while preparing it

1. **The last day's fingerprint would not have been published (fixed, commit `a5921c692`).** Once the race is over and every bet is
   settled, a normal run stops with "nothing left to do" and the settle watcher with "nothing to do"; Claude's hourly task no
   longer starts fill runs. All three stopped before the step that publishes the nightly fingerprint. Now, after the finish,
   every run first publishes what is due: Nov 28 always, a later day only if the record changed (`ops/fingerprint.py
   after_finish`, `ops/rivals.py publish_fingerprints`). Publishing only. One new test (32 pass). Rehearsed on a copy of the real record.
2. **An automatic Telegram note at 4:25 p.m. ET on Saturday (NOT changed; the owner decides).** The scheduled task "Paper Trades:
   FINAL scoring" (set up Oct 28) writes the Race Report entry "Final result" and posts "the final standings and the winner" to
   Telegram at 4:25 p.m. ET. Bets on games still being played are open then, and on Nov 19 all three AIs agreed that "won" is
   said only once no bet is open. Proposal, as part of `final post yes`: that note says who finished first, how many bets are
   still open, and that the final result follows; the one post above goes out when the card says Final.

## When the owner says yes

- `final card yes`: set `FINAL_LIVE = true` in `ops/polish.js` block 9, rebuild, publish, one Site updates line. Nothing shows
  before Sat 4:00 p.m. ET.
- `final post yes`: on Saturday, when the card says Final, fill in the post and send it on Telegram and Discord; give Nicole the
  same text for X, Instagram and YouTube (Telegram only). With the same yes, reword step 7 of the "FINAL scoring" task as above.
