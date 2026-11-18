# Outage days and ChatGPT's refunded penalties (Nov 18, 2026)

Asked: Gemini (ops/asks/outage-refund-nov18.txt, answers in ops/review/outage-refund-nov18.json). ChatGPT could not answer: its OpenRouter
credit had run out. Claude's blind vote: ops/review/claude-votes-outage-refund-nov18.json.

| Item | Claude | Gemini | ChatGPT | Result |
|---|---|---|---|---|
| P1 Refund ChatGPT's four C$500 penalties for Nov 12 and Nov 17 (Sports and High risk: Sports, C$2,000) | AGREE | AGREE | no credit | passes 2 of 3 |
| P2 Standing rule: an ET day with NO successful check-in because the AI's API credit or service was down owes no daily betting minimum; each such day lowers the C$100,000 totals by C$3,000 | AGREE | AGREE | no credit | passes 2 of 3 |

Why: on both days ChatGPT could not run at all (every call failed with HTTP 402 Payment Required: the operator's OpenRouter credit was
empty), so the minimum, which exists to stop an AI choosing to skip a day, punished something it could not control. The refund changes
no positions (Sports: Gemini, Claude, ChatGPT; High risk: Sports: Gemini, ChatGPT, Claude).

How it is applied (ops/rivals.py, run by the race runner, the only writer of ops/src/rivals.json):
- OUTAGE_VOTED names the two voted days; from OUTAGE_FROM (Nov 18) outage days are found from each AI's day_log (ok / down / other per ET
  day); "down" means the check-in failed on the AI's API (402, 429, 5xx, credit, quota, timeouts), never on its own reply. For Claude, an
  outage day is a day with no update at all.
- apply_outage_refunds moves a refunded penalty to refunded_penalties and adds a Refund line (+C$500) to the ledger; the original Penalty
  line stays (the record is append-only). It posts the refund on Telegram and sends ChatGPT a one-time notice (Gemini's addition).
- The vote named the High risk: Sports total; the main Sports race has the same C$100,000 total, so the same C$3,000 per outage day
  comes off it too (same reason, same rule for all three AIs).
- Test: test_outage_days_owe_no_minimum_and_are_refunded.

Also tonight: the health alert was silenced since Oct 30 by an old open issue, so no email went out when ChatGPT ran dry on Nov 3, Nov 12
and Nov 16. Fixed (ops/health_issue.py), with a warning below US$15 of OpenRouter credit.
