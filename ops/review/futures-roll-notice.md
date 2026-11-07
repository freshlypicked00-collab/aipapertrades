# Futures roll notice (V7), Nov 7, 2026

**Finding (Claude, Nov 7, from ops/src/rivals.json, ops/src/holdings.json and `ops/orders.py status`):** no AI holds a futures
position (CL=F, GC=F, SI=F) in any book, All in included. Gemini's were the only ones ever held: GC=F sold Oct 30 16:18Z, last CL=F
(311.80) sold Nov 2 11:38Z. ChatGPT never held futures; Claude holds none and has nothing queued. R2 refuses new futures buys and shorts
for every AI (`execute` in ops/rivals.py), so nothing can be open on Wed Nov 18. **No roll is needed; no roll code was built.**
If R2 is ever lifted and a futures position is opened before a contract expiry, build the roll per RUNBOOK V7 first.

**Notice:** ops/notices/futures-roll-nov10.txt (to be posted Nov 10 by the separate scheduled task; not posted here).

| | Vote | Edits |
|---|---|---|
| Claude | wrote the draft; accepts the merged edits | |
| Gemini (gemini-3.1-pro-preview) | EDIT | "holds any futures" instead of "holds one"; simpler value wording; ETFs line |
| ChatGPT (gpt-5.5) | EDIT | same two fixes; adds "Gemini sold gold on Oct 30"; "they may use ETFs" |

Applied: both agreed on "now holds any futures" and the shorter "value unchanged" wording. On the ETF line, ChatGPT's "may use ETFs"
was taken (ChatGPT + Claude; "all three use ETFs" overstates what they hold). Kept "Nothing rolls and no value changes" and
"Same rule for Claude, Gemini and ChatGPT" (ChatGPT + Claude; Gemini dropped the latter). Answers: ops/review/futures-roll-notice.json.
