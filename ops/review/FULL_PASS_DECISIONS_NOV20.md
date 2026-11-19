# Full pass: decisions (Nov 19 evening to Nov 20, 2026)

Owner, Nov 19, 5:57 p.m. ET: "You own a full review of everything the public sees of PaperTrades.AI ... Check everything, fix what is
wrong, and improve what can be better."
Started from commit 66b2a887 (the end of the same day's improvement pass: `ops/review/IMPROVEMENT_PASS_REPORT.md`, which this builds on).
Questions and answers: `ops/asks/full-nov20.txt`, `ops/review/full-nov20.json`; Claude's votes first: `ops/review/claude-votes-full-nov20.json`.
Earlier the same day: `improve-nov19-ab.json`, `improve-nov19-cde.json`. Both AIs answered every time (ChatGPT had credit).

## 1. What changed (all live unless marked HELD)

| # | Area | Change | Who agreed | How to reverse |
|---|---|---|---|---|
| 1 | Phone, Ledger | "Every trade and bet" is short cards (when, race, action, what, profit) with one button, "Details and reason". It was a ten-column table 1,442 px wide in a 336 px box: the reason and the money sat off-screen. | All three | polish.js 6: `LEDGER_CARDS = false`; polish.css 38 |
| 2 | Phone, all lists | A reason longer than about six lines shows four with "more"; a "Looking back" box shows its title with "Read the look-back". A reason with a fact-check note is never folded. | All three | polish.js 6 e, f; polish.css 36 |
| 3 | Phone, Prediction markets | "Betting minimums" folds to its title, as it already does on Sports. | All three | polish.js 6 g |
| 4 | Phone, everything | Tap targets under 24 px: about 440 across the 25 tabs before (transaction ID chips, "?" marks, "✕", the slim line's two buttons), about 110 now, and those are text links inside sentences and lists, which the guideline allows. The look is the same. | All three | polish.css 37 |
| 5 | Header | "📅 Add to calendar" beside the countdown: saves the finish (Sat Nov 28, 4:00 p.m. ET) with a 15-minute reminder and the link. Gone at the finish. | All three picked it (12 a) | polish.js 10; polish.css 39 |
| 6 | Numbers | A currency fill read "63,297.8 units at US$1.10 per share"; now "US$1.0971 per euro" (a sale at 1.1078 and a buy-back at 1.0971 both looked like 1.10). | All three | ops/src/index.html, `px()` in the Ledger (one line) |
| 7 | Numbers | "100,000" with no currency in two site sentences (About timeline, the Ledger's "Showing ..." line) is now "C$100,000 (China stocks: US$100,000)"; the BUSTED posts say "the whole C$100,000". | All three | ops/src/index.html (two strings); ops/rivals.py |
| 8 | Posts, pictures | Top line of every card and chart: "PAPERTRADES.AI · AI VS AI" (was "PAPER TRADES · AI VS AI"). | All three (D1) | ops/sharecard.py, daycards.py, tgcharts.py |
| 9 | Posts | "−C$3,000 Sports penalty" (the race is named, like the other two penalty posts); penalty, refund, busted and eliminated posts end with "PaperTrades.AI · Claude vs Gemini vs ChatGPT · https://papertrades.ai"; a market alert ends "... react on PaperTrades.AI: link". | All three (D2, D3) | ops/rivals.py |
| 10 | YouTube Shorts | The picker takes a different game than the last Short when there is one (Nov 17 had two Shorts in a row on the same game with only the AI's name changed; 1 case in 35). | All three | ops/metricool.py `story()` |
| 11 | Link previews | The share picture is 1200 x 675 but the page declared 630 high; now 675. | Only Claude (a real defect, one number) | ops/build_site.py line 451 |
| 12 | Guide | One sentence about the phone cards, in the Guide tab and guide.html; two lines in the Site updates log. | - | - |
| H1 | HELD | The "Final result" card, hidden (only papertrades.ai/?finale shows it). | See section 3 | polish.js 9 |
| H2 | HELD | The final share picture: `ops/final_card.py` (nothing calls it). | All three | delete the file |

Changes to `ops/src/index.html`, `ops/build_site.py` or a posting script (you asked for a list): rows 6, 7, 8, 9, 10, 11 above, plus one Guide sentence. Everything else is in `ops/polish.css` (blocks 35 to 39) and `ops/polish.js` (behaviours 6, 9, 10).

## 2. Measurements
- **Page length on a 375 px phone** (start of Nov 19 -> now): News 13,051 -> 5,985 px; How it works 13,824 -> 8,346; Rules & Audit 14,184 -> 11,518; Prediction markets 13,888 -> 11,338; Ledger 17,817 -> 15,605 (and its trade list is readable now); Oil and energy 12,002 -> 10,840.
- **Every tab (25) at 320, 375, 390, 430, 820, 1024, 1280, 1440, 1920 px and a phone held sideways (844 x 390):** no sideways scrolling, no script error, no text under 12 px. The same sweep in each of the eight colour themes (375 px) and in Beginner mode (375 and 1280 px): the same result.
- **First visit on a phone:** on 375 x 667 the welcome card's "Right now: Gemini leads overall" ends at 569 px and "Get notified" at 618 px (both on the first screen); on 320 x 568 they end at 605 and 654 px (just under the fold). "Get notified" scrolls to the channel buttons: alerts are 2 taps. The countdown says "left until final scoring on Nov 28".
- **Links:** 1,426 visible links on the 25 tabs: no dead anchor, none opening a new tab without `rel=noopener`. Mail links are hello@ and press@ only.
- **Accessibility basics** (Overview, Ledger, Sports): every image has alt text, every button a name, every field a label, no repeated id, no skipped heading level, `lang="en"`.
- **Search files:** robots.txt allows all and names the sitemap; sitemap.xml has 6 pages; llms.txt, manifest, icons (192, 512, maskable, apple-touch 180) and structured data are in place and say "PaperTrades.AI".
- **Speed:** unchanged from the improvement pass: about 2.1 MB compressed before the Overview is readable (page 0.34, data 1.70). Splitting the data file is HELD for Season 2 (all three agreed).
- **Race untouched:** with the same data and a frozen clock, the full text of every tab (folded parts included) is identical before and after on a phone, except the wording changed on purpose (rows 6, 7, 12) and one hidden line the site itself repeats on a redraw. 27 race tests pass.

## 3. What the AIs changed in my proposals, and one split
- Final card, status line: ChatGPT: "N Sports bets are still open, so the Sports totals can still change" (not "games still being played"). Taken.
- Final card, links: Gemini and ChatGPT: shorter ("Audit pack", "Rules + fingerprints"). Taken.
- Final post: ChatGPT's shorter text is the one below (Gemini had agreed with mine; Claude prefers ChatGPT's).
- **Split, for you to settle:** between the finish and the last bet settling, the card says "{Leader} finished first" (Claude and Gemini; it matches the top line all three agreed on earlier). ChatGPT wants "leads" there until everything is settled. The heading over the ten races already says "who is first" until then.

## 4. HELD for master's OK (answer with the numbers)
1. **The Final result card.** Preview: papertrades.ai/?finale (picture: `ops/review/img/full-nov20-final-card-preview.png`). Yes = it appears by itself at the top of the Overview from Sat Nov 28, 4:00 p.m. ET, at papertrades.ai/#final.
2. **"finished first" or "leads"** on that card until the last bet settles (section 3).
3. **The final share picture** (`ops/review/img/full-nov20-final-share-preview.png`): the daily standings picture titled "Final result · Season 1 · Oct 28 to Nov 28, 2026" plus "OVERALL, the ten races added up: 1st ... 2nd ... 3rd ...". Yes = it also becomes the link preview at the finish.
4. **The one final post** (all five channels, once, after the last open bet settles):
   > 🏁 FINAL RESULT · PaperTrades.AI Season 1
   > 🏆 {Winner} won Season 1 with {+C$X} across ten races.
   > 🥈 {Second}: {±C$Y} · 🥉 {Third}: {±C$Z}
   > Three AIs, C$100,000 per race (US$100,000 for China stocks), pretend money, real prices, Oct 28 to Nov 28. No human picked a trade.
   > First in a race: {Winner} {n}, {Second} {n}, {Third} {n}.
   > Every trade, every reason and the audit pack: https://papertrades.ai/#final
   > Pretend money only. Not investment or betting advice.
5. **Telegram channel name:** now "Paper Trades - AI". Proposed: "PaperTrades.AI".
6. **YouTube channel name:** now "PaperTrades AI". Proposed: "PaperTrades.AI". Its description names the site but has no address; add a last line: "https://papertrades.ai".
7. **X pinned thread, post 5:** now names the site, Telegram and Instagram. Proposed: "Follow live: papertrades.ai · Discord (every trade, instantly) · Telegram @PaperTradesAI · Instagram @papertrades.ai · YouTube @PaperTradesAI".
8. **Shorts thumbnails.** What I found: every Short is uploaded with its bold cover as the thumbnail and the upload service confirms it kept it; the Short also starts on that cover. The second step, uploading the picture in YouTube Studio, was sent to Nini as a Telegram job after every Short: 32 jobs since Nov 4, none marked done (her last "Done" on any job was Nov 3). Proposed: one job a week listing the week's Shorts instead of one per Short, and a short message from you asking whether the jobs reach her. I could not open YouTube's video pages to see the thumbnails themselves.
9. **Email list (MISSION O1), proposal:** one box, "Get the final result and the weekly Race Report by email", under the leader box and inside the Final result card (all three: both places). Double opt-in, no selling, one-click unsubscribe. A service of the MailerLite / Buttondown kind costs roughly US$10 to 20 a month at 500 to 1,000 readers (free plans have shrunk this year; check the price page on the day). Two things only you can decide: the service (it needs an account and a payment method, which I never touch), and a mailing address shown in every email, which the law requires; a virtual mailbox keeps you anonymous.
10. **"Since your last visit" line** (how many new trades, settled bets and lead changes since this browser was last here; kept only in the visitor's browser). The AIs picked the calendar button first; this is the next return idea. Build it?

## 5. Could not check
- X and Instagram profiles and posts: both sites refuse automated reading. The bios are a checklist in `ops/review/OFFSITE_DRAFTS_NOV19.md` (D5).
- YouTube's list of videos and their thumbnails (the channel page showed the name and description only), Discord (server, pinned texts, onboarding, AutoMod), and the reserved TikTok, Threads and Reddit handles.
- How X, Discord and iMessage draw the link preview (the tags and the picture are right; the drawing happens on their side).
- On the live site I could read the page's fixed text only; everything drawn by script was tested on a local copy of the same build, and each deploy was confirmed.
- Not tested: the translated versions behind the language switch (it needs Google's translator), keyboard focus order, reduced motion, the notch and swipe-bar areas, and buttons that stay lit after a tap.

## 6. Notes for the next pass
- The watchdog: GitHub's timer had not started it once in its first 100 minutes (a hand-started run worked). It now has a second starter that does not depend on the timer: it runs after every "Post updates to Telegram" run (Claude's hourly update sets that off). Check `watchdog.yml` runs on Nov 20. After the finish, turn the workflow off (it is on the run sheet).
- Claude's own trade notes still say "All in" in places (the side race was renamed "High risk" on Nov 1). Old notes stay as written; new ones should say "High risk" (added to ops/RUNBOOK.md).
- The first standings card a new visitor meets is the High risk side race, because Auto-pick opens on the biggest profit anywhere (your choice of Nov 1). Worth a second look before Season 2.
- On a 320 px phone the welcome card ends 40 px under the first screen.
- One combined save-and-publish command was refused by a safety check. I did not work around it: the same steps were redone one at a time (tests, commit, rebuild, push) and all went through. Nothing was skipped.
- The new post wording (rows 8 and 9) has been drawn and printed in a dry run but had not yet gone out in a real check-in when this was written; the first one is the 7:14 p.m. ET run on Nov 19, and a check of it is scheduled.
- Top 5 next: (1) your OK on the Final result card, picture and post; (2) Nini and the Shorts thumbnails; (3) the email box; (4) one voice on X and Instagram once someone can read them; (5) Season 2: the lighter first load and alerts that close themselves.
