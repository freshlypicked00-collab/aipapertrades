# Check of Fable's changes (Nov 20, 11:06 p.m. ET to Nov 21)

Owner, Nov 20, 11:06 p.m. ET: "work with all models to see if anything needs to be changed from fables changes check the entire project".
Checked by Claude (the backup chat). Question and answers: `ops/asks/fable-check-nov21.txt`, `ops/review/fable-check-nov21.json`
(Gemini and ChatGPT: AGREE on P1, P3, P4; both SATISFIED). Pictures: `ops/review/img/check-nov21-phone-first-visit.jpg`, `-phone-pages.jpg`.

## What was checked, and what was fine
- Fable's three rounds since Nov 19, 5 p.m. ET: the race safety nets (IMPROVEMENT_PASS_REPORT.md), the full pass (FULL_PASS_DECISIONS_NOV20.md)
  and the phone pass (PHONE_PASS_NOV20.md).
- The race: all 100 race runs since then succeeded; Gemini and ChatGPT both checked in at 10:15 p.m. ET with no failures in a row; no open
  alerts; 43 watchdog runs, all fine; Discord #holdings updates after every publish.
- The site, all 25 pages at 390 px and 1280 px: no script errors, no sideways scrolling, nothing hidden under the new bottom bar.
- The finale switch (4:00 p.m. ET Nov 28 = 21:00 UTC) and the calendar event: right. Nini's email: on no public page.
- The race runner's tests: 27 passed before tonight, 28 now (one new).

## What changed tonight
| # | What | Why | Who agreed | How to reverse |
|---|---|---|---|---|
| P1 | The race runner no longer sends a post twice when Telegram is slow: a post that went out whole but got no answer in time is not sent again; an animated card gets 120 s instead of 60 s; the album sender follows the same rule. A post Telegram refuses, or one that never left, still falls back to the still card. New test: `test_a_picture_that_timed_out_is_not_posted_twice`. | Gemini's "Won · Sports, Houston Texans" went out twice on Telegram (#1431, #1433) at 11:16 p.m. ET Nov 19: the animated card got no answer within 60 s, Telegram posted it anyway, and the still card followed. Found by a 48-hour dry run of the repeat check (Discord: no repeats). | All three | `tg_photo` in ops/rivals.py and `tg_album` in ops/sharecard.py (commit "Telegram: a post that timed out is not sent twice") |
| P3 | The publish workflow tries the publish step once more, 45 s later, if GitHub's side fails it. | 17 failed publishes on Nov 19-20 ("Fetching artifact metadata failed"; 0 to 1 a day before), the site up to 57 minutes behind (also 42 and 38). It began before Fable's changes. | All three | .github/workflows/deploy.yml, the two steps after `deployment` |
| P4 | Phones: the "New here?" tour offer waits until the front page's podium is off the screen, steps out of the way when the podium scrolls back under it, and never comes up while the follow card shows. Computers: unchanged (it never covered anything there). | On a first visit it sat on 3rd place of the podium, the answer that screen is for. ChatGPT: "never cover the podium, even if the 20-second timer fires" (done: there is no timer that overrides it). | All three | ops/src/index.html, the tour offer (`podiumOnScreen`, `when`, `dodge`) |
| P5 | The tour's last step said "Every trade lands on Telegram"; it now says Discord, and that Telegram gets the results and the daily race update. | Trades moved to Discord on Nov 16; the night pass of Nov 19 fixed eight other places (all three agreed then) but not this one. | Follows the Nov 19 decision (all three) | ops/src/index.html, STEPS |

One line in Site updates (ops/src/changelog.json).

## Points the models raised that turned out not to need a change
- Gemini: the "Official channels" card lets the page show through. Measured: its background is solid (rgb 18, 18, 16); nothing shows through.
- Gemini and ChatGPT: a red "×" floating at the bottom right, over the bar or over headline text. It is the close button of the red BREAKING
  headline strip, in its place in the page; the tour offer had covered the rest of the strip in the picture. A long headline was tested at
  320 and 390 px: it wraps and stops before the button (at 320 px the text ends at 244 px, the button starts at 269 px).

## For the owner
1. **Delete the repeated Telegram post?** #1433 (the second copy of Gemini's Texans win; #1431 stays). Deleting can't be undone, and Telegram
   allows it until about Sat Nov 21, 11:16 p.m. ET. Say "delete it" and it is done with the "Repeated posts" workflow (confirm = delete).
2. **One YouTube Short without its thumbnail:** the Nov 20, 1:28 a.m. ET Short was published, but the upload service said "Could not upload
   video thumbnail". The Short still starts on its cover. Setting it by hand in YouTube Studio fixes that one.
3. Still waiting from Fable's reports: the Final result card, picture and post; channel names and bios; the email list; Nini's open jobs
   (FULL_PASS_DECISIONS_NOV20.md section 4).
