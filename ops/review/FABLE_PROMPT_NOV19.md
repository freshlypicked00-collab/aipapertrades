# Fable all-night prompt (Nov 19)

Drafted by Claude, reviewed in two rounds by Gemini (ops/review/fable-prompt-nov19-r1.json, -r2.json). Gemini: SATISFIED. ChatGPT was not asked (the owner asked for Claude and Gemini).

```
PAPERTRADES.AI: ALL-NIGHT POLISH PASS
Call me "master". Tonight you own a full quality pass on PaperTrades.AI. Work autonomously through the night and make the calls yourself; use as much time, effort and usage as it takes. Quality over speed. The goal: by morning, PaperTrades.AI is the cleanest, easiest, best-feeling AI race a visitor has ever used, on the site and everywhere we post, down to the last detail.

S1. CONTEXT
- PaperTrades.AI is a public Season 1 race (Oct 28 to Nov 28, 2026): Claude vs Gemini vs ChatGPT trading and betting pretend money in ten races, plus the High risk side race. Final scoring Sat Nov 28, 4:01 p.m. ET. Everything tonight should help a first-time visitor get it fast and make the finale land.
- Repo: freshlypicked00-collab/aipapertrades. Run `git pull --rebase origin main` before you start and before every push (other chats and the hourly UPDATE ALL runs commit too). Never force-push.
- The site is built by ops/build_site.py from ops/src/index.html. Never hand-edit the built files.
- Read first: ops/review/POLISH_DECISIONS_NOV18.md (last night's polish with Gemini: what was built, what was measured, what was taken back and why), ops/polish.css and ops/polish.js. Build on that pass; don't redo or undo it without a measured reason.
- To ask the other AIs: write ops/asks/<name>.txt (+ <name>.files.txt; .png files are sent as pictures), run rivals.yml with mode=ask and name=<name> (only=gemini or only=chatgpt to ask one). Answers land in ops/review/<name>.json; ops/review/diag.json shows the OpenRouter credit left.
- The race check-ins, Claude's updates and every ask share one GitHub queue ("rivals"), and a new run CANCELS the run that is waiting in it. Start an ask only when nothing is waiting in that queue (a running one is fine), or you will cancel a race check-in. Use the REST API (gh api .../actions/workflows/rivals.yml/dispatches); gh's GraphQL commands are blocked here.

S2. GROUND RULES (not up for change)
- The Season 1 rules, every number, and every word an AI wrote stay exactly as they are. Don't touch trading, betting, scoring, settling, the ledgers or the append-only record.
- Nothing is deleted from the site. The safety wording (pretend money, no deposits, not advice) stays.
- Keep the dark "Terminal" look, IBM Plex Sans and Mono, the three AI colours, the tab order and the slim top. The only logo is brand/logo.png and its derived sizes.
- Pages stay compact, especially on a phone; master dislikes long pages. A change that makes a page longer needs a clear reason.
- The brand is always written "PaperTrades.AI" (lowercase only in the web address). The side race is "High risk", never "All in".
- Holdings are always shown in full: no cut-off names, no "+N more".
- Fact checks live on the site only; the AIs are never corrected. Where an AI's reason contradicts its own numbers, add a clear fact-check note next to it and never edit the AI's words (example: Gemini's Nov 12 bet on Colorado says "the massive favorite (-380)", but Colorado was the +300 underdog).

S3. REVIEW EVERY SURFACE, EVERY WORD
Work in this order, so the most important things are done even if the night runs short: (1) first visit and the Overview on a phone; (2) the words posted for every trade, bet and result on Telegram and Discord; (3) race pages, the ledger and the numbers; (4) graphics, share cards and YouTube; (5) everything else.
a) The site: every tab at 320, 390, 430, 820, 1024, 1440 and 1920 px wide: spacing, alignment, sideways scrolling, text size, tap targets, contrast, empty, loading and error states, all eight colour themes. Check phone hazards too: the notch and the bottom swipe bar (safe areas), and buttons that stay highlighted after a tap on a touch screen ("sticky hover").
b) Numbers: correct AND easy to read. Flag numbers that are right but confusing (a partial sale, C$ vs US$, potential win vs settled, totals that don't obviously add up).
c) The site's own words: labels, buttons, headings, tooltips, help text, the Guide, About, Rules & Audit. Short, plain, consistent, friendly.
d) What we post: the text for trades, bets, results and alerts on Telegram and Discord (channels, onboarding, #new-to-discord, bot messages), YouTube titles, descriptions, pinned comments and thumbnails, the email banner, share cards, the app manifest and icons. One voice and one brand everywhere; the AI's own words stay word for word. Format each post for its platform: Discord embeds and markdown used properly, Telegram bold and monospace without clutter, and thumbnails and share cards readable at a glance on a small phone.
e) First visit: in 5 seconds, can a new visitor tell what this is, who's winning, and that it's pretend money? Can they turn on alerts (Discord or Telegram) in 2 taps? Is the countdown in the top line clearly the countdown to the Nov 28 finale, and noticed in the first 5 seconds? Strengthen what is there rather than add a new block.
f) Graphics: charts, badges, cards, AI colours, icons and videos: consistent, and crisp on a phone and on high-resolution screens (no blurry icons).
g) Speed, accessibility and SEO: page weight, alt text, labels, headings, meta tags, sitemap, llms.txt.

S4. WORK WITH ALL THREE MODELS
- Check ops/review/diag.json first; if ChatGPT's OpenRouter credit is out, say so and continue with Gemini.
- For each area: audit and measure first, write numbered proposals, send them with screenshots to Gemini and ChatGPT (ask mode), then build.
- Ship what the models agree improves things; small polish counts too. If the three disagree, go with the two that agree and write down the dissent.
- If only two models are answering and they split 1-1: ship only small, reversible fixes of real defects (a broken link, a typo, text overflowing or a page scrolling sideways, contrast under 4.5 to 1) and mark them "only Claude". Hold every split on design or wording for me, with each side's view in one line.
- Batch your questions (one ask per area, not one per detail) to save credit and Actions minutes.

S5. HOW TO WORK
- Start with a task list, one item per area in S3, and tick them off.
- Keep every change reversible: new looks go in numbered, stand-alone blocks in ops/polish.css or ops/polish.js. Note the commit you started from.
- Change ops/src/index.html, ops/build_site.py or a posting script only when there is no other way, as small as possible, and list each such change in the report.
- Small commits with clear messages; rebuild, verify, then push. Check the live site after each deploy.
- Prove nothing about the race changed: compare every tab before and after with the same data and a frozen clock; every money and percent figure must match.
- Measure, don't guess: page length per tab (phone and computer), sideways scrolling at every width, smallest text, smallest tap target, contrast ratios. Screenshot before and after for anything visual.
- Test changes to posting text with dry runs or a private test channel; never send test messages to public channels.

S6. HARD STOPS (prepare it, then leave it for me)
- Never type or reveal keys, passwords or card numbers; never open card screens.
- Nothing that costs money, can't be undone, or posts new public content (YouTube, socials, new channels) without my explicit OK. Improving the wording of the existing automatic posts is fine.
- Never cancel, rerun or delay a race run, and never change an AI's trades, bets, results or words.
- No human picks for the AIs. Keep Nini's (Nicole's) email off public pages; Nini is reached by Telegram only.

S7. MORNING REPORT
Write ops/review/NIGHT_PASS_DECISIONS_NOV19.md in the same style as POLISH_DECISIONS_NOV18.md: what changed, the measurements, before and after screenshots, and how to reverse each change.
Then leave me a short, beginner-friendly summary in this chat containing ONLY:
- The main improvements you made, grouped by area.
- For every decision: whether all three AIs agreed, which two agreed, or only Claude.
- What you prepared but held for my explicit OK.
- Your top 5 next improvements, ranked.

Begin now. Make it the best PaperTrades.AI has ever been.
```
