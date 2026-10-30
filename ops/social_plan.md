# Paper Trades: social media plan (agreed Oct 30)

Asked by the owner on Oct 30: grow the socials; only what Claude, Gemini and ChatGPT all agree on. Two rounds:
`ops/review/social-r1-oct30.json` and `ops/review/social-r2-oct30.json`. Unless marked otherwise, **all three AIs agreed** to everything below.

## The rules for every post
- Pretend money, real prices; say it. No deposits, nothing to sign up for.
- Each race is its own experiment. No overall totals before Nov 28.
- Quotes word for word, with their date. No performance or accuracy claims beyond the visible scoreboard and dated quotes (ChatGPT's last word; Claude and Gemini agree).
- Never call anyone a scam. "Not affiliated with Papertrade (papertrade.xyz)" goes in the pinned X thread, the Start-here post and the site's About, not in every bio.
- Never: bought followers, engagement pods, prize giveaways, mass DMs, automated replies or mentions.

## X (@papertradesai): the main channel
- **3 to 5 posts a day:** the daily scoreboard picture, 1 or 2 AI-conflict posts (the "Grades of the day" picture: harshest AND best grade together, never a roast alone), and live posts only for big moves.
- **Links:** none in post bodies. One link a day, in a reply under the scoreboard post, tagged `?utm_source=x`.
- **Automation through the official API only** (pay-per-use, about US$0.015 a post, about US$0.20 with a link). Never by driving the X website: X's automation rules say that can get an account permanently suspended, and they forbid automated replies based on keyword searches.
- **Replies to other people's threads:** about 15 minutes a day of useful replies (a chart, no link) to AI-agent and finance-experiment threads. Claude can draft; a person picks the threads and posts by hand.
- **"Automated" label:** turn it on (X's rules require automated accounts to show it and stay connected to a human-run account). It shows "Automated by @<managing account>" publicly, so connect an anonymous human-run account, never the owner's personal one (Claude's note, for anonymity).

Suggested day (ET): 8:30 a.m. scoreboard + link reply · 12:30 p.m. Grades of the day · 5 p.m. race replay (Mon, Wed, Fri) or a big moment · Sunday: weekly recap + the "Who wins on Nov 28?" poll (no prizes, no odds; fandom only).

### Bio
Claude vs Gemini vs ChatGPT: 3 AIs, 10 races, C$100k of pretend money each. Real prices · no deposits · Oct 28–Nov 28. Every trade and reason live 👇

### Pinned thread (Start here)
1/ Three AIs. C$100,000 of pretend money each. Ten separate races. One month.
Claude vs Gemini vs ChatGPT trade at real prices from Oct 28 to Nov 28, and no human picks the trades.
Pretend money. No deposits. Nothing to sign up for. 🧵

2/ The ten races: stocks, crypto, China stocks, metals, oil and energy, options, currencies, a "play it safe" control, sports bets and prediction markets. Each is scored on its own. On Nov 28, the AI with the most total profit wins.

3/ Every trade is published as it happens, with the AI's own reason. The AIs also grade each other's decisions (A to F, anonymously, before the result) and fact-check each other. Grades never change the score.

4/ Every price is checked against a second source, and a fingerprint of the full record is published every night, so nothing can be quietly changed later.

5/ Follow live: papertrades.ai · Telegram @PaperTradesAI (every trade as it happens) · Instagram @papertrades.ai
Not affiliated with Papertrade (papertrade.xyz), Anthropic, Google or OpenAI. Not financial advice.

## Instagram (@papertrades.ai)
- Keep the daily carousel and stories (already automated).
- **Race-replay Reel 3 times a week (Mon, Wed, Fri) plus a Sunday recap**; review after 2 weeks. Template: `ops/reel.py` (16 s, 1080x1920, words in the frame, inside the Reels safe area). Add a sound in the app when posting by hand.
- **Grades of the day:** `ops/grades_card.py` (feed + story).
- **Start here:** the pinned intro carousel; add "Not affiliated with Papertrade (papertrade.xyz)" to its caption.
- **Bio:** must include "pretend money · real prices · no deposits".

### Ads (owner pays)
- **What to run:** post `social/ads/ad-1-feed.jpg` as a normal post, then tap **Boost post** under it.
  Story version: `social/ads/ad-1-story.jpg`.
- **Goal:** more profile visits (the ad sends people to the Instagram profile, not the website).
- **Budget:** C$10 to 15 a day for 7 days, then keep what worked.
- **Audience (create your own):** Canada, United States, United Kingdom, Australia · ages 21 to 44 · interests like artificial intelligence, ChatGPT, stock market, investing. No crypto or gambling interests.
- **Never in an ad (picture or text):** crypto, betting, options, profit numbers. Meta needs written permission for crypto-trading and gambling ads.
- `ad-2` (the grades quote) is for **organic posts only**: Claude and Gemini were fine with it as an ad; ChatGPT warned the quote could read like a live prediction, so it is not used as a paid ad.

## Other channels
- **Discord:** a read-only `#daily-digest` channel that mirrors the scoreboard and grades pictures (owner: create the channel and a webhook).
- **Telegram:** unchanged (every trade live).
- **TikTok, YouTube Shorts:** reuse the race-replay video later.

## Free outreach (disclose who we are; be useful)
- AI newsletters (for example The Rundown AI, Ben's Bites, TLDR AI) through their tip or submit pages, with a small media kit: 3 screenshots, the 50-word description below, the logo, the rules, an anonymous project email.
- One "Show HN" on Hacker News with a technical angle (how three models trade, grade and get fact-checked; the nightly fingerprint).
- One post each in r/ClaudeAI, r/ChatGPT and r/singularity, following each subreddit's self-promotion rules.
- Mention Alpha Arena only as respectful context: "Alpha Arena used real money on crypto; Paper Trades uses pretend money across ten markets, with every reason, grade and fact-check public." No "safer than" claims.
- Tag @AnthropicAI, @GoogleDeepMind or @OpenAI only on real milestones.

**50-word description:** Paper Trades is a one-month public experiment: Claude, Gemini and ChatGPT each get C$100,000 of pretend money in ten separate races, from stocks to prediction markets, at real prices. No human picks trades. Every decision and its reason is published live, the AIs grade and fact-check each other, and the winner is decided on Nov 28.

## Measure
Tagged links per channel (`?utm_source=x`, `instagram`, `telegram`, `reddit`, `newsletter`) in the site's visitor counter, plus follows, saves, replies, profile visits and Telegram joins. A short review every Sunday.

## For tomorrow: connecting X (the owner's steps)
1. Sign in to the X developer console with @papertradesai, create an app, and choose pay-per-use. Add a small credit (US$5 to 10 covers a month at this pace).
2. Give the app **Read and write** permission and create the four keys (API key and secret, access token and secret).
3. Paste them into GitHub → the repo → Settings → Secrets and variables → Actions as `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`. (Claude never types keys or passwords anywhere.)
4. Tell Claude. Claude then adds X posting to the same workflow that posts to Instagram and Telegram.
