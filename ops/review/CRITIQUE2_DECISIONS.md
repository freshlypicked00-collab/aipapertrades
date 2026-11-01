# Critique 2 (Oct 31, 2026, ~10 p.m. ET): randomness, safeguards, confirmation bias
Owner relayed a Gemini chat's critique and asked all three AIs to decide on solutions. Season 1 rules and scoring unchanged.
Rounds: critique2-oct31.json (Claude's votes first: claude-votes-critique2-oct31.json), critique2-r2-oct31.json.

Criticisms: randomness FAIR (all three); confirmation bias FAIR (all three); safeguards PARTLY FAIR (Claude, ChatGPT) / FAIR (Gemini).

ALL THREE AGREED (display only; never changes a score, trade or the Nov 28 winner):
- L1 Luck check: per AI and race, the percentile vs 1,000 random portfolios with the same risk (same dates, eligible universe, long/short permissions,
  number of trades, holding windows, dollar turnover/trading frequency, gross/net exposure, volatility and beta bucket, costs, liquidity caps);
  published with a confidence band and the method.
- L2 Wrong-if tracker: when an objectively checkable "what would prove it wrong" condition happened, did the AI exit within its next two check-ins?
  "Kept X of Y exit promises"; vague conditions shown as "untestable".
- L3 Weekly stress drill: one made-up scenario for all three (incl. correlation breakdowns, liquidity gaps); exact actions (hold/sell/trim/add/hedge,
  sizes, order, what would change the answer); published side by side and peer-graded. Never affects any score or trade.
- L4 No fake prices or shocks in the real race.
- L5 Public line: Season 1 tests an LLM as portfolio manager (judgment and behaviour), not production trading infrastructure; Season 2 tests safeguards.
- E1 Calibration record: each AI states a probability its thesis works; scored later (Brier score).
- E2 Risk dashboard beside returns: max drawdown, volatility, beta, concentration, turnover, average hold time, cost drag.
- E3 Blind peer grading: ALREADY BUILT since Oct 29 (graders see "Competitor A/B", reshuffled each time; ops/peer_grades.py G4).
- E4 Conviction cost: result of holding vs exiting right after peers graded the decision D or F.
- Q5 From now on (Season 1), the AIs are asked to write wrong-if conditions as measurable numbers and give a probability; prospective only
  (tagged "from Oct 31 onward"), no retrofit, display and calibration only.
Most important: L1 (Claude, ChatGPT); L2 (Gemini).
