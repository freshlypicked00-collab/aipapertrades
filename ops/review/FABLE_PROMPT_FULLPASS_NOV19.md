# Fable full-pass prompt (Nov 19, evening)

Owner, Nov 19, 4:54 p.m. ET: "make a prompt for fable to go over the full papertrades.ai on mobile/desktop/social medias/posts. everything. tell him to check everything and make improvements".
Drafted by Claude (the backup chat). It builds on this morning's prompt (ops/review/FABLE_PROMPT_NOV19.md) and Fable's night pass report (ops/review/NIGHT_PASS_REPORT.md).
Reviewed by Gemini and ChatGPT (ops/asks/fable-fullpass-nov19.txt, answers ops/review/fable-fullpass-nov19.json); both said CHANGE, and every edit below is in:
- Hold the big "load each tab's data when opened" change for Season 2 (or master's OK); small safe savings only: all three agreed.
- Posts moved up to third, right after the first visit and the finale: Gemini and Claude.
- A focus line for the 9 days left; click every link and button; more post checks (repeats, channel, timing, failed uploads); favicon, manifest, robots.txt, titles: ChatGPT and Claude.
- Hold changes to navigation, tab order, data loading or a channel's identity for master's OK: ChatGPT and Claude (Claude narrowed ChatGPT's wider list, keeping small agreed polish autonomous, as master prefers).
- Asks avoid the minutes when check-ins start: Gemini's idea, with Claude's correction of the times (check-ins start at about :13 and :43 past each hour, so Gemini's "10 to 45 past the hour" would have hit them).

```
PAPERTRADES.AI: FULL PASS. THE SITE, EVERY POST, EVERY CHANNEL
Call me "master". You own a full review of everything the public sees of PaperTrades.AI: the site on every screen, every automatic post, every social channel and profile, every picture and video. Check everything, fix what is wrong, and improve what can be better. Work on your own and make the calls yourself; use as much time and effort as it takes. Quality over speed. The goal: well before the finale (Sat Nov 28, after 4:00 p.m. ET), everywhere a person meets PaperTrades.AI looks and reads like one polished product, is easy to follow in 5 seconds, and gives them a reason to come back.

S1. START HERE
- Repo: freshlypicked00-collab/aipapertrades. Other chats commit all day: the hourly race check-ins and Claude's UPDATE ALL runs, the commercials chat, and the backup chat. `git pull --rebase origin main` before you start and before every push; never force-push. The site is built by ops/build_site.py from ops/src/index.html: never hand-edit built files; if a built file conflicts, take main's copy and rebuild.
- Read first: ops/MISSION.md (every change is judged by it); your own ops/review/NIGHT_PASS_REPORT.md (sections 6 to 8 list what is left); ops/review/POLISH_DECISIONS_NOV18.md, LAYOUT_DECISIONS_NOV18.md, FOLLOW_CARD_DECISIONS_NOV18.md, RECENT_MOVES_DECISIONS_NOV18.md, followups-nov19-status.md, SOCIAL_STANDARD.md; ops/social_plan.md; and these ops/RUNBOOK.md sections: Social media plan, Instagram, YouTube-first Shorts, Social standard, The polish layer, Official channels, Landing on the exact thing, Keep the Guide current, Site updates log, The logo, Asking Gemini and ChatGPT from several chats at once. Build on what was agreed; don't undo it without a measured reason and the models' agreement.
- New since your night pass: F1 (sale posts say the result, yours) and F2 (the repeated Telegram post deleted) are done. The race pages now show "Value over time" right under the score tiles, and the High risk page was rebuilt to match the race pages (commit b454c20e). Review both like everything else.
- F3, the animated cards, is IN PROGRESS in the commercials chat: leave ops/animate.py and the PT_GIFS switch alone until ops/review/followups-nov19-status.md says it is done.

S2. GROUND RULES (not up for change)
- My standing rules, word for word: "Never edit ops/src/rivals.json data by hand." "Keep disclaimers." "Never invent prices." "Claude never types keys or passwords." "AI decisions, takes and reasons are never edited."
- The Season 1 rules, every number and every word an AI wrote stay exactly as they are. Where an AI's words contradict its own numbers, add a site-only fact-check note beside them. Don't touch trading, betting, scoring, settling, the ledgers or the append-only record.
- Nothing is deleted from the site. The safety wording (pretend money, no deposits, not advice) stays everywhere it is.
- Keep the dark Terminal look, IBM Plex Sans and Mono, the three AI colours, the tab order and the slim top. The only logo is brand/logo.png and the sizes made from it.
- Pages stay compact, above all on a phone. A change that makes a page longer needs a clear reason.
- Write "PaperTrades.AI" (lowercase only in the web address). The side race is "High risk", never "All in". Holdings always show in full: no cut-off names, no "+N more".
- I stay anonymous. Nini (Nicole) gets tasks by Telegram only (nicole.yml), and her email never appears anywhere public. Hacker News comments are written by me only: never draft or edit one. Bot tokens live only in GitHub secrets.

S3. CHECK EVERYTHING (in this order, so the most important is done first)
For the 9 days left, put race-critical clarity, the finale, broken links, overflow, defects in posts and templates, and consistent profiles ahead of broad redesigns or experiments.
1. First visit, on a phone first. In 5 seconds, can a stranger tell what this is, who is winning, and that it is pretend money? Is the countdown clearly to the Nov 28 finale? Can they turn on alerts in 2 taps? Add a one-line "how to read this" cue by the standings (ChatGPT's pick). Strengthen what is there rather than adding blocks.
2. The finale. On Nov 28, where will a visitor, a journalist or a newsletter find the final result in one place they can cite and share (MISSION plan item 3)? Audit what exists, then prepare what is missing: page, share card, posts. Hold anything new for my OK.
3. The automatic posts (they go out all day, so they come before the long screen checks). Read what actually went out in the last 7 days (ops/src/discord_sent.json, x_sent.json, social.json, youtube.json, tg_video_sent.json, and the Telegram channel), then fix the templates:
   - Discord: #live-trades, every race channel, #holdings and its pictures, #daily-results, #lead-changes, #big-moments, #announcements, the pinned START HERE texts, Onboarding, the bot's name and avatar, AutoMod.
   - Telegram, X, Instagram (posts, carousels, Reels, Stories) and YouTube (titles, descriptions, pinned comments, thumbnails: I have complained that Shorts don't get the right thumbnail, so check every recent one).
   - Share cards and the link previews for X, Discord and iMessage.
   Also check that a post can't go out twice, goes to the right channel at the right time, says ET or UTC clearly, and that a failed picture or video upload can't leave a confusing text-only post.
   One voice and one brand everywhere, formatted for each platform, readable on a small phone. Test with dry runs only; never send a test to a public channel.
4. Every tab at 320, 375, 390, 430, 820, 1024, 1280, 1440 and 1920 px, phone sideways too, in all eight colour themes and in Beginner mode. Check: sideways scrolling, overflow, spacing and alignment, text size, tap targets, contrast, focus with a keyboard, reduced motion, empty and error states, the notch and swipe-bar areas, buttons that stay lit after a tap, and two languages through the language switch. Click every link, button, alert and follow button, share button and tab: list any dead link, wrong destination, missing UTM tag, or action that fails silently.
5. Long phone pages: Ledger (about 19,200 px), How it works (15,800), Prediction markets (15,300). Fold or tighten them (Gemini's pick) without hiding numbers.
6. Speed: the page is 1.3 MB and its data file 11 MB. Measure what a phone downloads before it can read the Overview, and ship small, low-risk savings. Plan loading each tab's data only when it is opened and agree the plan with the models, but hold that big change for Season 2 unless I say otherwise: it must not risk the live site before the finale.
7. Numbers that are right but read confusingly, on every page and in every post (my standing rule): C$ vs US$, potential win vs settled, partial sales, totals that don't obviously add up, percent vs points, "since the start" vs "24 hours", time zones.
8. The site's words: labels, buttons, headings, tooltips, help text, the Guide, About, Rules & Audit, guide.html, join.html, the 404 page. Short, plain, consistent, friendly; the same name for the same thing everywhere.
9. Profiles and channel pages: names, bios, avatars (the logo only), banners (YouTube safe areas), links (papertrades.ai with UTM tags), pinned posts, descriptions, and the same five official channels in the same order as the top bar (Discord, Telegram, Instagram, X, YouTube). Also the reserved TikTok, Threads and Reddit handles: do they at least show the logo and the link? Hacker News: look only.
10. Graphics and video: daily cards, share cards, holdings cards, thumbnails, Short covers and first frames, icons. Consistent and sharp on a phone and on high-resolution screens. The animated cards: review only (F3).
11. Accessibility and SEO: alt text, labels, headings, meta and Open Graph tags, sitemap.xml, llms.txt, structured data, the favicon and app icons, the manifest, canonical links, robots.txt, and the page title a phone browser and a share show.
12. Coming back (MISSION: the 7-day return rate). What brings a visitor back tomorrow? Propose the few best ideas; build only small, agreed ones.
13. The email list (MISSION O1) does not exist yet. Prepare a short proposal (where the box goes, which service, cost, double opt-in) for my decision.

To see the live pages, ask me ONCE at the start to approve opening papertrades.ai and the public pages of our channels (t.me/s/papertradesai, youtube.com/@PaperTradesAI, x.com/papertradesai, instagram.com/papertrades.ai). If a page still can't be opened, use the repo's records, the existing bots (read-only) and local builds, and list what you could not see. Tip: the site loads d3 from a CDN that your workspace may block. If /opt/npm-tools/node_modules/d3/dist/d3.min.js exists, point that request at it in Playwright to see the real charts.

S4. WORK WITH ALL THREE MODELS
- Each area: audit and measure first, write numbered proposals, send them with screenshots to Gemini and ChatGPT, then build. Batch your questions: one ask per area, not one per detail.
- Asks: write ops/asks/<name>.txt plus <name>.files.txt (.png and .jpg files go as pictures), then dispatch rivals.yml with mode=ask and name=<name> through the REST API (gh api .../actions/workflows/rivals.yml/dispatches). Answers land in ops/review/<name>.json.
- The race check-ins and every ask share one queue ("rivals"), and a newer waiting run CANCELS the older waiting one, which could be a race check-in. Dispatch only when nothing is waiting in that queue (a running one is fine), and not in the minutes when check-ins start: about :13 to :16 and :43 to :47 past every hour, and :03, :18, :33 and :48 in the evening, overnight and on weekends.
- If an answer shows ChatGPT out of OpenRouter credit, tell me in one line and continue with Gemini.
- Ship the low-risk improvements the models agree on; small polish counts too. Hold for my OK anything that changes navigation, the tab order, how data loads, or a channel's identity (name, handle, avatar). If the three disagree, go with the two that agree and write down the dissent. If only two models answer and they split 1-1, ship only small, reversible fixes of real defects (a broken link, a typo, overflow or sideways scrolling, contrast under 4.5 to 1), marked "only Claude", and hold design or wording splits for me with each side's view in one line.

S5. HOW TO WORK
- Start with a task list, one item per area in S3, and tick them off. Note the commit you started from.
- Keep changes reversible: looks in numbered, stand-alone blocks in ops/polish.css and ops/polish.js. Change ops/src/index.html, ops/build_site.py or a posting script only when there is no other way, as small as possible, and list each such change in the report.
- Small commits with clear messages; rebuild, verify, push; check the live site after each deploy.
- Prove nothing about the race changed: compare every tab before and after with the same data and a frozen clock; every money and percent figure must match.
- Measure, don't guess: page length per tab on a phone and a computer, sideways scrolling at every width, smallest text, smallest tap target, contrast. Before and after screenshots for everything visual.
- When a visitor-facing feature changes, update the Guide and guide.html in the same change, and add a line to the Site updates log (ops/src/changelog.json).

S6. HARD STOPS (prepare it, then leave it for me)
- Never type or reveal keys, passwords or card numbers; never open payment screens.
- Nothing that costs money, can't be undone, or puts out new public content (a new post, video, channel, ad or announcement) without my explicit OK. Improving the wording of the existing automatic posts is fine.
- Profile and channel texts (bios, descriptions, banners, pinned messages): prepare the exact new text or picture and hold it for my OK in one list. After my OK, do what the bots can, and send Nini one Telegram task for the rest.
- Never cancel, rerun or delay a race run. Never change an AI's trades, bets, results or words. No human picks for the AIs.
- If a safety check blocks an action, don't work around it: put it on the list for me.

S7. REPORT
Write ops/review/FULL_PASS_DECISIONS_NOV20.md in the style of POLISH_DECISIONS_NOV18.md: what changed, the measurements, before and after screenshots, how to reverse each change, a "Held for master's OK" list with the exact texts, and a "Could not check" list.
Then leave me a short, beginner-friendly summary in this chat with ONLY:
- The main improvements, grouped by area (site on phone, site on computer, posts, each channel).
- For every decision: whether all three AIs agreed, which two agreed, or only Claude.
- One numbered list of everything waiting for my OK, so I can answer it in one message.
- Your top 5 next improvements, ranked.

Begin now. Make every place PaperTrades.AI appears the best it has ever been.
```
