# Site polish (Nov 18)

Owner, Nov 18: "polish papertrades.ai, make it as human friendly as possible. work with gemini to improve the user interface and the entire site ... as high grade as top tier website with thought and care. if i dont like something i will ask for a reverse apply the changes and let me know what has been done".

Asked: Gemini only (the owner said "work with Gemini"; ChatGPT's API credit was out, its last ask that night failed with HTTP 402). The question, Claude's audit, 18 proposals and five screenshots: ops/asks/polish-nov18.txt. Gemini's answers: ops/review/polish-nov18.json.
Result: Claude and Gemini agreed. Gemini AGREED with 16 of the 18 proposals, CHANGED two (P4, P13), added ten ideas of its own, and ended SATISFIED.

Nothing about the race changed: no rule, no number, no word an AI wrote. Checked by comparing all 25 tabs of the untouched site and the polished site with the same data and a frozen clock, on a phone and on a computer: every money and percent figure is the same (up to 323 figures on a tab), and the only wording differences are the ones listed under "New words" below.

## Where it lives, and how to reverse it

- ops/polish.css (looks) and ops/polish.js (three small behaviours). ops/build_site.py adds both LAST to the page, so they only refine what is already there.
- Every numbered block in polish.css stands alone. To reverse one change, delete its block and rebuild. To reverse the whole pass, empty both files and rebuild (the hook in build_site.py copes with empty or missing files).
- Outside those two files the pass touched only: three lines in ops/src/index.html (the dot between two holdings in "Holding now" got a wrapper; two phone scroll offsets changed from 8 to 44), one sentence in the Guide (site and guide.html), and the colours of guide.html.

## What Claude measured before (15 tabs, phone 390 px and computer 1440 px)

- 57 kinds of text under 12 px on a phone, down to 8.5 px; 60 to 90 percent of all characters at 12 to 13 px.
- 34 kinds of buttons, links and menus under 30 px tall on a phone.
- White text on the Telegram button at 2.6 to 1 contrast (4.5 is the minimum); seven other buttons and badges under 4.5.
- Lines of 150 to 205 characters on a computer.
- Three controls with the browser's default grey look.
- A tab opened from a link landed with its title half under the sticky bar (computer) or under the price ticker (phone).
- The Overview's top on a computer: six settings spread unevenly over one row, three large clocks, the alerts box with two links floating in the middle; ragged on a tablet.
- Whole sentences set in the monospace font inside tables; chips stacked six to eight lines per bet.
- Small laptops and tablets on their side (1000 to 1140 px): the sticky bar was wider than the screen on race pages, so the page could be dragged sideways.

## What was built (P = Claude's proposal number, G = Gemini's idea number)

Reading
- P1 No text under 12 px anywhere (93 style rules; the one exception is the tiny "1st" corner mark on the 26 px Telegram icon).
- P2 Phones: all text 4 percent larger. Slimmer side margins and card padding pay for it: 24 of the 25 tabs are shorter than before on a phone (1 to 9 percent; all together 5.0 percent shorter). Support is 38 px longer because of the new footer links. The content of every tab starts 50 px higher and the Overview's race standings about 150 px higher.
- P3 Computers: running text stops at about 115 characters a line and small notes at about 150 (they ran to 205). A long list (six items or more) on How it works, Rules & Audit, About, Guide, Data and Support flows in two columns. All 25 tabs together are 2.0 percent shorter on a computer; How it works is 21 percent shorter; Data and Support are 9 to 10 percent longer (about 200 and 95 px: their paragraphs wrap sooner, plus the footer links); News, Guide and the race pages are 1 to 5 percent longer.
- P4 (Gemini's change: IBM Plex Sans for words, IBM Plex Mono for data) Tables: words in the normal font; numbers, prices, odds, times and transaction IDs stay monospace. On a computer the High risk ledger is 14 percent shorter because reasons no longer wrap to 11 lines in a narrow column.
- G10 The "?" help dots are larger and in the accent colour.

Touch and controls
- P5 Phones: buttons and menus at least 40 px tall; small chips, links and close buttons keep their look and get an invisible 38 px touch area.
- P6 One look for every menu and button (the three grey ones fixed); one focus ring for keyboard users; the same 150 ms hover and pressed feedback (P15), off for people who turned animations off.
- P7 Contrast: Telegram, Discord, the LIVE and DEVELOPING badges, the "Worst" and "Best" grade tags and the audit download button are darker under their white text (all 4.5 to 1 or better now).
- G2 (Claude's version) Instagram, YouTube and X are outlined buttons in their own colours; Telegram and Discord, the two alert channels, stay solid. Gemini wanted all five outlined.
- G6 Data tags are 4 px boxes and status badges are pills.

Layout
- P8 A tab opened from a link, a reload or the menu starts with its title clear of the sticky bar (computer) and of the price ticker (phone).
- P9 Overview top on computers and tablets: line 1 the day, the countdown, the last update and the system status; line 2 the clocks (normal size now) and the markets; line 3 the six settings as one even toolbar; line 4 the next-scoreboard note. The alerts box is one row: text and the latest move on the left, the five buttons on the right, the two small links under the text. Race standings start 108 to 122 px higher.
- G3 (smallest form) First-time visitors on a computer or tablet see the three overall totals on the right of the welcome card. polish.js reads them from the leader pill the site already fills, so they can never differ from it.
- Phones, Overview: the three AI faces are three full-width buttons with readable names; the leader pill has each place on its own line with the amount on the right; Telegram and Discord on the first row of alert buttons and the other three on the second; the price ticker no longer touches the logo.
- P11 AI vs AI "Holding now": left-aligned; the dot between two holdings stays with the name before it (the written " · " is still in the page for copying, translating and screen readers).
- P12 Bet and move rows: the chips sit side by side and wrap.
- P13 (Gemini's change: keep the card) An empty "Coming up" card says "Nothing scheduled right now."
- P14 Footer: one row of links to the main pages (they press the same tabs the menu does) and "Official accounts"; the small print is left-aligned in a readable column.
- G8 The 1st-place card on the scoreboard has a soft gold glow.
- Small laptops and tablets on their side: the AI badge beside the logo and the full-screen icon step aside between 701 and 1140 px, so no page can be dragged sideways (tested at twelve widths from 720 to 1366 px).
- Guide tab: "Show me" is a normal button instead of a bar across the card, and the "#" link to a section sits in the card's corner.
- guide.html (the standalone Guide page) is dark like about.html and what-is-papertrades-ai.html; it was the only light page.

Feel
- P16 (part) Tables: a row lights up under the mouse; a time stays on one line.
- P17 Themed scrollbars; text selection in the accent colour.
- P18 All eight colour themes checked on a computer (Overview) and a phone (race page).

## New words on the site (everything else is word for word the same)

- Guide, "Make it yours": "On a phone they are in the ☰ Menu; a round ☰ button comes back at the bottom right whenever you scroll up." (the Guide said the settings are at the top of the page, which is not true on a phone).
- "Nothing scheduled right now." in an empty Coming up card.
- The footer links: Overview, Ledger, AI vs AI, News, How it works, Rules & Audit, Guide, About, Support, Official accounts.
- The welcome card's box: "Overall right now · pretend money", "1st / 2nd / 3rd", "Profit across the ten races. The High risk side race is scored on its own."
- Six lines in Site updates (About).

## Not built, and why

- P10 A floating Menu button on phones: dropped. The site already has one (the round ☰ at the bottom right that comes back when you scroll up). Claude's audit missed it because it only shows while scrolling up; Gemini agreed to P10 on Claude's wrong description. Nothing was added.
- P16 (rest) A soft edge shadow and fixed column headers on tables that scroll sideways on a phone: left out. Every way tried either depended on the card's background colour or put a mask over very tall tables; not safe enough for one night. 18 tables scroll sideways on a phone; the cut-off column is still the only hint.
- G1 Right-align the standings numbers: they already are.
- G4 Fixed column widths for the bet tables: only the bet lists got a wider first column (56 percent); the others were left to the browser.
- G5 Less padding on the sticky top on phones: the only sticky part on a phone is the 28 px price ticker.
- G7 Robot faces inline in headers: done differently (the three full-width AI buttons on the Overview).
- G9 Row separators in logs: the tables already have a line under every row.
- Two-column text for every paragraph on the reading tabs: tried, looked uneven; only long lists use two columns.

## The change the owner is most likely to want back (Gemini's warning)

P4, the font inside tables. To reverse it alone: delete block 4 in ops/polish.css and rebuild. Tables are then monospace again and nothing else changes.
