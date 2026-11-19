# Night pass report (Thu Nov 19, 2026, 5:00 to 7:15 a.m. ET)

Owner, Nov 19, 5:00 a.m. ET: an all-night quality pass on PaperTrades.AI with all three AIs.
Asked: Gemini and ChatGPT, twice (`ops/asks/night-pass-nov19-a.txt` and `-b.txt`; answers in `ops/review/night-pass-nov19-a.json` and `-b.json`; Claude's votes, written first, in `ops/review/claude-votes-night-pass-nov19-a.json` and `-b.json`). ChatGPT had credit and answered both times.

## The short version

1. **The race was stuck and nobody knew.** From 10:14 p.m. ET (Nov 18) to 5:14 a.m. ET (Nov 19) no Gemini or ChatGPT check-in finished. Found the bug, fixed it, both are checking in again since 5:58 a.m. ET. No bet, result or balance changed.
2. **The site said the wrong place for trades.** Since Nov 16 every trade is posted on Discord, but eight places still said Telegram. Fixed, Discord first.
3. **Posts on Discord and Telegram read better**: what happened, the thing in plain words, and which number is which.
4. **Small things**: cut-off lines now read whole, a site-only fact check sits beside Gemini's two Colorado bets, older corrections fold up (the longest phone page is 21% shorter).
5. **Nothing about the race changed**: 7,404 money and percent figures on 25 tabs are the same before and after.

## 1. The race runner (urgent, before any polish)

| What | Who agreed |
|---|---|
| The stall: the code that draws the animated result cards could loop for ever (it told pictures apart by a number Python reuses). It hit on the night's first results; each hourly run was stopped at the 30-minute limit before saving. Fixed, with a test. | Only Claude (urgent). Shown to Gemini and ChatGPT afterwards; no objection. |
| A 9-minute limit shared by all of one AI's requests in a check-in, so one stuck AI can't take the other's turn. The log is written live, and a stuck run prints where it is. | Only Claude (urgent). Same. |
| Animated cards had been still pictures since about Nov 12: GitHub's new runner image has no ffmpeg. It is installed again. | Only Claude (restores your Nov 1 choice). |
| A public entry in Corrections (Rules & Audit) about the stall. | All three |

The stall of Nov 12-13 had the same pattern (overnight, after games ended). It was put down to a hung request then; its logs can't confirm either cause.

## 2. The site

All of these: **all three agreed** unless marked.

- **Where trades are posted (S1).** Overview alerts box, the Get notified cards and list, the Guide, How it works, About, guide.html, join.html. The "Every trade, instantly" tag moved from Telegram to Discord; Discord is first on phones too. The tiny "1st" mark on the Telegram icon is gone (B4).
- **Fact check beside a bet's reason (S2).** Gemini's Nov 12 bets G129 and G130 say Colorado was "the massive favorite (-380)"; the recorded line was Colorado +300, the underdog (it won, +C$9,000 each). A note now sits beside that reason wherever it shows. Gemini's words are untouched. I scanned all 237 sports bets for the same kind of slip: these two are the only ones. Picture: `img/night-nov19-factcheck-note.jpg`.
- **Lines that were cut or broken (S3, S5, S6).** The "Latest: ..." line wraps instead of ending in "…". On phones each market has its own line. On Sports, 37 bet names in the bars wrap instead of being cut.
- **"7:00 PM your time (EST), in 12h 36m" (S4)** instead of "7:00 PM EST your time (in 12h 36m)".
- **Phone leader box (B3, Gemini's idea).** The 2nd and 3rd amounts line up under the leader's; "(pretend)" is a small yellow tag.
- **A long "Big news" label on phones (B2).** It took half the width and squeezed the headline into eight lines; it now sits above the headline. Built as only Claude, then all three agreed.
- **Older corrections fold up (B5).** The three newest stay open; an older one shows its title and two lines and opens on a tap; one button opens them all. Nothing is removed. Rules & Audit on a phone: 20,990 px to 16,054 px. Picture: `img/night-nov19-corrections-folded-phone.jpg`.
- **Invisible (S7, S8).** A name for the day menu (screen readers), a canonical link, a description for the X card, the same title on the X card as everywhere else, today's date in sitemap.xml. One change from what was agreed: the sitemap date is set by hand, not by the build. A build that edits sitemap.xml would leave an uncommitted file in the other chats' folders and could block their updates. Only Claude.

Before and after pictures: `img/night-nov19-phone-overview-before.jpg` and `-after.jpg`, `img/night-nov19-desktop-overview-before.jpg` and `-after.jpg`, `img/night-nov19-desktop-bars-after.jpg`.

## 3. The words we post (Discord and Telegram)

All three agreed (W1 to W6, B1). The AI's reason stays word for word.

Before:
```
🔴 Options: Sell NVDA261120P00150000
NVDA Nov 20 $150 put
US$1.70 per share (15 contracts), C$3,651
```
After:
```
🔴 Sold · Options
NVDA Nov 20 $150 put
Sold for C$3,651 at US$1.70 per share (15 contracts)
```
- "Short" and "Cover" read "Sold short" and "Bought back".
- The last line names the brand: "PaperTrades.AI · Claude vs Gemini vs ChatGPT · https://papertrades.ai".
- "bet C$1,200 to win C$100" has its comma.
- Tested with dry runs only; nothing was sent to a channel as a test.

## 4. Proof that nothing in the race changed

- Same data, frozen clock, the site before tonight and the site now, 25 tabs, phone and computer: **7,404 money and percent figures, all the same.** The only wording differences are the ones listed here.
- No sideways scrolling and no console errors on any tab, phone (375 px) and computer (1280 px).
- Page length, all tabs together: phone 1.6% shorter, computer 0.5% shorter. Longer: About (+266 px on a phone, four new Site updates lines), Ledger (+79 px, bet names wrap), How it works (+44 px).
- The race code's tests: 20 pass (3 new tonight).

## 5. What I got wrong tonight

- **A wrong claim, live for about 25 minutes.** I first wrote (to Gemini and ChatGPT, and in the site's correction) that two results had been posted about ten times during the stall. I then counted both channels: one post went out twice on Telegram (Gemini's Miami Heat win) and nothing was repeated on Discord. The correction now says so, and says that it was corrected.
- **A failing test on main for about one minute** (6:42 to 6:43 a.m. ET). No race run started in that minute.
- **Race runs I started or stopped by hand.** One catch-up check-in at 5:58 a.m. ET after the fix. One test check-in I stopped after 5 minutes to read where it was stuck (it would have been killed anyway). My first start also replaced another chat's queued question to Gemini; that chat asked again and got its answer.

## 6. Prepared, waiting for your OK

1. **Say the result on a sale post** ("Result on this position: +C$X"). All three said yes. Not built: the number must match the Ledger's figure exactly, and that needs a careful build with tests.
2. **Delete the one repeated Telegram post.** Actions → "Repeated posts" → Run workflow → confirm = delete. It keeps the first copy. It can't be undone, and Telegram only allows it until about Sat Nov 21, 5:58 a.m. ET.

## 7. Not done

- YouTube titles, descriptions and thumbnails, the Discord channel and onboarding texts, the email banner: not reviewed.
- Widths other than 375 and 1280 px, and the eight colour themes: not re-tested tonight (Nov 18 tested 17 widths).
- I could not open papertrades.ai from here to look at the live page (it needs your approval). I confirmed that every "Publish the site" run succeeded and tested the same build locally.
- Gemini's note that the safety banner feels cramped on a computer.

## 8. Top 5 next, ranked

1. Sale posts that say the profit or loss (item 1 above).
2. Fold more on the longest phone pages: Ledger (19,200 px), How it works (15,800 px), Prediction markets (15,300 px). Gemini's pick.
3. First-load weight: the page is 1.3 MB and its data file 11 MB. Measure what a phone downloads first, then load each tab's data when it is opened.
4. A one-line "how to read this page" cue by the standings. ChatGPT's pick.
5. A pass over YouTube, Instagram and the Discord channel texts.

## How to reverse

- Looks: `ops/polish.css` blocks 22 to 30 and `ops/polish.js` behaviours 3 to 5. Delete a block and rebuild.
- Site wording: commit "Night pass, words" (`git show` it to see each line).
- Post wording: `post_lines` and `POST_VERB` in `ops/rivals.py` (commit "Move posts on Discord and Telegram").
- The site before tonight's site changes is commit 77c7a8f1.
