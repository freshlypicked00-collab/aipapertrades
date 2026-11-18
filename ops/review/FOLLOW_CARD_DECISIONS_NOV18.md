# The follow pop-up becomes "Official channels" (Nov 18)

Owner, Nov 18, 10:24 a.m. ET: "the pop up button that appears on the right hand side for the socials dont look very good and often i find myself [...] closing it because it feels like a pop up ad more then a professional display on where to find us". Then: "work with gemini on making that better".

Asked: Gemini only, as the owner said (`ops/asks/follow-card-nov18.txt`, three pictures). Answer: `ops/review/follow-card-nov18.json`. Gemini: SATISFIED with its changes; Claude took all of them.

## Before
The growth plan's follow prompt (Nov 2): bottom right after about 20 s (or 1.5 s after a second tab), every 3 days, until closed. Amber border, bell emoji, a bold amber headline, the latest move, "Who wins on Nov 28? Follow the race free:", four buttons of four shapes and colours (no Discord), a disclaimer and a link. 394 x 223 px on a computer; 240 px tall on a phone, on top of the Top and Menu buttons.

## Now
- Look: a slim bar in the site's own panel colours and card-title style (follows all eight themes). Title "Official channels", line "Follow the race live." (Gemini's words: the title first, no "free"), then the five channels as the same round icons as the top bar: Discord, Telegram, Instagram, X, YouTube.
- Where (Gemini's change): not on computers, where the sticky top bar already shows the same five icons all the time. Claude's finding while building it: on tablets the top bar has no room for those icons, so the rule is "only where the five icons are not already on screen": phones and tablets.
- Size: 374 x 124 px on a phone (was 240 tall), with the names under the icons; 457 x 62 px on a tablet, icons only. On phones the Top and Menu buttons step up above it.
- When: after 45 s (was 20), or 10 s after a second tab is opened (was 1.5); never on the tour; not while the Overview's own alerts box is on screen.
- It leaves by itself after 20 s (it stayed until closed); a thin line at its bottom runs out so people can see that (Gemini's idea). Pointing at it holds it.
- At most once every 30 days per device (was 3); after a click on a channel, not for a year.
- The card at the end of every tab (Gemini's change; the owner had not mentioned it): the same treatment. Before: a bell, "Don't miss the next move", two big buttons (Telegram, Discord), a blue tint. Now: "Official channels", "Follow the race live.", all five channels, each with its name and, on wider screens, what you find there (Discord: real-time custom alerts; Telegram: every trade as it happens; Instagram: daily results; X: race updates; YouTube: short race videos). 116 px on a computer (was 128), 143 px on a phone (was 219).

## Checked
- 30 behaviour checks with a controlled clock: when it shows and does not (computer, tablet, phone, Overview alerts box, tour), leaving by itself, the mouse holding it, Close and Escape, the 30-day and one-year rules, counting of shown / closed / left by itself / each channel click, `?follow`.
- Phones from 320 to 430 px wide, a tablet, a computer; all eight themes.
- Every tab: no console errors, no sideways scrolling; before/after text identical except the end card.

## To reverse
- Show it on computers too: remove the line in the follow card's `show()` that returns when the top bar icons are on screen.
- The old end-of-tab card or the old pop-up: `git show b75bcc14:ops/src/index.html` has both.
