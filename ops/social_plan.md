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

## Update, Oct 30, 11 p.m. ET: links and growth (ops/review/growth-r1-oct30.json)
The owner: funding is not an issue; post links until we grow, and tell me what I can do to help.
- **Links (all three AIs agreed):** money is no longer a reason to limit links; reach is. X main posts stay link-free and end with "👇 Link in reply"; the page they point to goes in the first reply, on every post that sends people somewhere (no one-a-day cap). Plain papertrades.ai links with `?utm_source=x`, no shorteners (ChatGPT). Built in ops/xpost.py (`reply_link`), used by the daily race card and lead-change posts; X cap raised to 24 posts a day, link replies included. Telegram and Discord can carry links freely.
- **The owner's own top actions (all three listed the same five; order differs):** pitch the AI and fintech newsletters with the media kit (Gemini's #1), 20 to 30 useful hand-written replies a day on X to AI and markets threads (ChatGPT's and Claude's #1), the hand-written Show HN and 3 Reddit posts under each forum's rules, answering every real comment and DM within a few hours, and tightly targeted ad tests.
- **Only one AI suggested:** TikTok and YouTube Shorts: repost the best Instagram reel daily (ChatGPT); X Premium on @papertradesai, about US$8 to 16 a month, for reach and reply priority (Gemini).
- **Paid:** Instagram boosts C$10 to 15 a day (all three); an X ads test: ChatGPT US$25 to 50 a day for 3 days, Gemini US$15 to 25 a day; positioned as an AI race with pretend money, never profit claims or stock picks (X restricts financial ads).
- **Avoid (all three):** bought followers, giveaways, pods, mass DMs, undisclosed paid promos, "AI beat the market" claims or anything that reads as investment advice.

## Paid newsletter ads, booked Oct 31 (owner's C$1,000 budget; dates agreed by all three AIs)
| Date | Ad | Cost | Status | Tracking link |
|---|---|---|---|---|
| Wed Nov 4 | Ben's Bites Unclassified | US$100 | paid (Stripe receipt #1813-2704) | ?utm_source=bensbites&utm_campaign=bensbites-unclassified-1 |
| Tue Nov 10 (backup Nov 17) | Launch Llama Classified (15.8k subs, 90% US) | US$150 + Passionfroot fee | paid Nov 2 (owner); confirmation DM sent | ?utm_source=launchllama&utm_campaign=launchllama-classified-1 |
| Wed Nov 11 | AI Valley Trending Tools | US$380 | paid Nov 2 (owner); confirmation sent to Evan Rai (theaivalley.com) | ?utm_campaign=aivalley (the link the owner sent them; shows as campaign "aivalley" in GoatCounter) |
Ad text: "Claude vs Gemini vs ChatGPT trade pretend money at real prices. Every move and reason is public. Watch the race, winner Nov 28."
Dropped: Big Brain (its newsletter stopped in Nov 2023 although the sponsor page is still up). Instagram boost (US$5/day) runs on the side, not part of the budget.
Measure in GoatCounter: visits per utm_source, follow/<channel>-<place> events, visitor/return-7d. First read: Wed Nov 4 evening / Thu Nov 5. Rule (all three AIs): scale only what costs under ~US$2 per real visitor.

## Next step, agreed Oct 31, 11:45 a.m. ET (ops/review/next-step-oct31.json)
- P1 race-lead post from live per-race standings (no totals): all three agreed; ChatGPT's fix adopted ("best result", not "biggest lead": C$22,842 is Gemini's Options profit, not its margin). Posted Oct 31 on X, Telegram and Discord.
- P2 Reddit first, one a day, owner-posted, "I built this with Claude" disclosed, ?utm_source=reddit: r/ClaudeAI Sun Nov 1, r/ChatGPT Mon Nov 2, r/singularity Tue Nov 3. Claude and Gemini agreed on the title; ChatGPT wanted it softened. Standings recomputed right before each post.
- P3 Show HN Tue Nov 3 about 9 a.m. ET, the day before the Ben's Bites ad, with the technical/audit/conflict-of-interest first comment; no vote asking: all three agreed. The single most important step this week (all three).
- P4 site ready for the spike before Show HN (fast first screen on phones, one-sentence explanation, audit page easy to find): all three agreed.
- Extra ideas: a weekly email recap sign-up before the spike (Gemini only); a launch checklist per post and the owner replying for the first hour (ChatGPT only).

### Ad log
- **Oct 31, 6:28 p.m. ET:** first Instagram boost live (ad-1-feed.jpg): C$10 a day for 7 days, Canada and US only, ages 19 to 44. Goal: profile visits. Paid in the iPhone app (web checkout kept failing on a new ad account; Apple fee about 30%). Ad account is the personal one Instagram made (…153572), not in the PaperTrades business portfolio. UK and Australia need phone verification on that account: use the blue "Verify phone number in Meta Business Suite" link on the boost page, then pay on the web to skip the Apple fee. Advantage+ creative off; AI label on; financial-products toggle off.
- **Budget rule (all three AIs agreed):** hold 2 to 4 days, then raise only if cost per profile visit is at or under about C$0.15 to 0.20 and at least 5 to 10% of profile visitors tap the site link. Step up gradually (C$10 → 15 → 25). Next: a Reel as a second ad (Instagram library music only).
- **Check results:** Tue Nov 3 or Wed Nov 4.
- **Oct 31, 7:51 p.m. ET:** Reddit Ads campaign "Reddit test 1" published (status Processing, under Reddit review). Objective Traffic, lowest-cost bid, C$70 daily budget, Nov 2 12:00 a.m. to Nov 3 11:59 p.m. EST (about C$140 total; the C$140 campaign cap was not shown on the review page, so the end date is the limit). Link https://papertrades.ai/?utm_source=redditads&utm_campaign=reddit-test-1. Communities r/ChatGPT, r/ClaudeAI, r/singularity, r/artificial, r/OpenAI, r/GeminiAI. Canada, US, UK, Australia. 3 headlines, ad-1-feed.jpg, icon-512.png thumbnail, Learn More button. Owner's card (not prepaid; Reddit refuses prepaid). Reddit Ads email still to verify.
- **Nov 2, 1:25 p.m. ET:** Reddit test 1 at C$20.55 spent, 3,286 impressions, 31 clicks (C$0.66 a click, CTR 0.94%); GoatCounter campaign reddit-test-1: 71 visits.
- **Reddit check:** Wed Nov 4 / Thu Nov 5. Scale only if under about US$2 per real visitor (redditads tag in the visitor counter).

## Week 1 traffic estimate, Oct 31, 8:30 p.m. ET (ops/review/week-estimate-oct31.json)
Real outside visitors Nov 1-7, combined (Claude / Gemini / ChatGPT most likely: 1,000 / 700 / 700): low about 300, most likely about 800, high 7,000-15,000 only if Show HN reaches the front page (Gemini <10%, ChatGPT 5-8%, Claude ~20%); without that, the practical ceiling is about 1,500-2,000.
- Risk (Claude and Gemini): Reddit Ads in the same subreddits on the same days as the owner's organic posts can read as astroturfing. Gemini's fix: move the ads to Nov 5-6. Claude agrees.
- ChatGPT's fix: one "Start here" page linked everywhere (standings, how fills work, pretend money / no deposits / not advice, the audit, a follow or email sign-up).
- Show HN with the audit story is the best piece (all three).

## Headline casing (Oct 31; Claude, Gemini and ChatGPT all agreed, ops/review/headline-case-oct31.json)
- On the site: sentence case, "Which AI makes the most (pretend) money?" (matches every other heading).
- Social post titles, video titles and pictures made for socials: standard Title Case with lowercase "the": "Which AI Makes the Most (Pretend) Money?". Never capitalise "The" mid-title.

## Hacker News
- Account: papertrades_dev (owner, Oct 31). Show HN Tue Nov 3 ~9 a.m. ET; facts sheet ops/hn/first-comment-facts.md (owner rewrites it in his own words).

## Growth plan from the numbers, Nov 2 (owner; ops/review/growth-nov2.json, Claude's votes first)
Numbers then: site 963 visits (~340-410 real outside), 105 new visitors since Oct 31; Reddit ad C$20.55, 3,286 impressions, 31 clicks, CTR 0.94%, CPC C$0.66, 71 page views (2.3 per ad visitor); Instagram 1,200 account views/7 days, 16 followers; YouTube 3 subs, best Short 191 views (Sports race replay), stories 24-90; Telegram 5; Discord 1.
- P1 ALL THREE AGREED: fix visitor -> follower first. DONE Nov 2: timed follow prompt (20 s or a second tab, once per 3 days, never over the tour); events prompt/shown, prompt/closed, follow/<channel>-prompt.
- P2 Reddit test 2, Nov 5-9, ~C$40/day, US/CA/UK first, not on days with organic posts in the same subreddits. Gemini and Claude agreed; ChatGPT's AMEND adopted: only after P1 is live (done) and test 1 has a full day under US$2 per real visitor; split by subreddit/country, cut losers fast. Owner sets it up.
- P3 Instagram: daily cliffhanger posts ("result tomorrow"), 3 Reels a week (Nicole), bio "Follow to see who wins Nov 28". Gemini and Claude agreed; ChatGPT's AMEND adopted: raise boost C$10 -> C$15 only if a profile visit costs <= C$0.20 AND profile-view-to-follow improves.
- P4 ALL THREE: YouTube daily race replay is the format (biggest daily move); site link in description + pinned comment.
- P5 ALL THREE: site ready for Show HN (Tue) and Ben's Bites (Wed) spikes before Tue 9 a.m.
- P6 ALL THREE: Telegram is the core channel; Discord stays an automated mirror until Telegram has 100.
- P7 ALL THREE: targets by Mon Nov 9, reviewed Sunday by source: Claude 1,200-1,800 real visits / Telegram 40 / Instagram 60 / YouTube 20; Gemini 1,500 / 50 / 65 / 25; ChatGPT 1,300-1,900 / 35-55 / 60-85 / 15-30. Working target: 1,500 / 50 / 65 / 25.
- P8 ALL THREE: week-2 spend = Reddit test 2 (~C$200) + existing Instagram boost; no new paid channel until visitors follow.
- Missing, named by Claude and ChatGPT (2 of 3): a weekly email recap sign-up for Show HN / newsletter visitors who won't use Telegram (owner: free Buttondown account). Gemini: strict UTM tags on every paid link (Ben's Bites and Launch Llama have source+campaign; AI Valley uses ?utm_campaign=aivalley as sent).

- **Reddit test 1, day 1 (Nov 2, at 5:20 p.m. ET):** C$48.93 spent of C$70 (lowest-cost bidding underspends in the pricey North American evening), 7,125 impressions, 73 clicks, CTR 1.025%, CPC C$0.67 (~US$0.48), 118 ad page views on the site (~1.6 per visitor). Most delivery went to Australia (overnight, cheap); US flat. PASSES the US$2 rule. Test 2: separate US ad group, no Australia, consider a cost cap.
