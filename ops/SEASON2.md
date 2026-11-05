# Season 2 plan (agreed Nov 1, 2026; owner's approval pending)

Owner, Nov 1, 2:01 a.m. ET: "Begin working on Season 2 rules, concept, groundwork, everything, together with all models ... make Season 2 the one
that makes this perfect and exposes us immensely." Two rounds: ops/review/season2-r1-nov1.json (ideas, web search on) and season2-r2-nov1.json
(votes); Claude voted first each round (claude-votes-season2-r*-nov1.json). 28 items voted, all three unanimous on 27 (only the lineup split).
Shared doc for the owner: https://claude.ai/artifact/7HNky4Y1K3w8rXsEUmiLqk. Earlier Season 2 decisions: ops/review/SEASON2_DECISIONS.md.

## Format (all three)
- 8 weeks: Mon Jan 11 to Fri Mar 5, 2027; public dry run Jan 4-8 under the final rules; Draft Day Jan 9-10 (proposed). Rules frozen before the dry run.
- Lineup: Claude, ChatGPT, Gemini, Grok, DeepSeek, Qwen (all three); Llama 7th only if the budget allows (Gemini: outright). Mistral dropped.
- Frozen system prompts; exact API model version logged per call; a model changes only if retired, announced the same day.
- Benchmarks under the same rules and costs: index fund, 60/40, random trader.
- Championship: Strict / Standard / Unrestricted, scored Return / max(worst drop, 5% / 10% / 20%), equal rank points (agreed Oct 30).
- Betting (Sports, Predictions) = separate track, profit + closing-line value, never in the championship.
- High risk (formerly All in) dropped. Small account (C$7,500) only if the Nov 13-28 trial has no audit issues. No totals mixing tracks.

## Trust (all three; build first)
T1 operator is code (no AI session writes race data; Claude trades through the same runner) · T2 sealed orders (hash published before the fill)
· T3 one shared timestamped data/news pack, same tools, search and token budget, prompts public · T4 open-source runner, daily replay file
and public dataset/API, fingerprints anchored to an outside timestamp (OpenTimestamps) · T5 named outside reviewer before launch, adjudicates
corrections · T6 public correction protocol (ticket, diff, affected scores, reviewer sign-off) · T7 golden-test simulator (splits, halts, bad
ticks, wide spreads, borrow failures) + dry run · T8 written rationale summaries only, never hidden chain-of-thought.
Most important: T1 (Claude, ChatGPT); T2 (Gemini).

## Realism (all three; on top of R1-R8 and borrow/margin/dividends agreed Oct 30-31)
Market impact from live order-book depth where available, labelled size-based estimate elsewhere · brokerage commissions by asset class ·
the runner refuses orders that would break an AI's own written limits and counts the attempt (instead of forced liquidation) · a minimum
delay between an AI's answer and its fill (length set in the build).

## Exposure (all three)
Draft Day launch (manifestos, risk rules, first trades; AIs graded on following their manifesto) · citable dataset + postseason research
report (attribution, turnover, drawdown, luck bands vs the random trader) · weekly Race Report · prediction game with badges, email reminders,
"beat the AIs" board (no money, no prizes) · open-source prompts and architecture · guest graders and auditors with bylines.
REJECTED by all three: visitors linking their own trading accounts. Email list live before Draft Day.

## Cut (all three)
Futures without a reliable real-time feed, illiquid instruments, totals mixing tracks, more than 7 AIs, any real-money or advice claim.

## Budget (all three)
Estimate API and data cost per AI for the season and set a hard cap before building; integrity core (T1-T4) first, then AIs and tracks.

## Proposed groundwork (Claude's dates, not voted)
Dec 1-6 budget cap + division details · Dec 1-20 integrity core · Dec 7-27 realism rules · by Dec 14 outside reviewer · Dec 21 rules frozen
· Dec 21-Jan 3 new AIs + golden tests · Jan 4-8 dry run · Jan 9-10 Draft Day · Jan 11-Mar 5 Season 2 · ~Mar 19 research report.

## Owner decisions pending
Dates · operator separation (Claude stops writing race data) · budget cap (decides Llama) · open-sourcing the runner and prompts ·
outside reviewer · Small account go or Season 2 · division markets and Unrestricted's position cap · paid real-time data (futures, depth).
