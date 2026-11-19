# Follow-ups agreed by Claude and Gemini (owner, Nov 19, 4:38 p.m. ET: "ask Gemini and do whatever you guys agree on")

Question and answers: `ops/asks/followups-nov19.txt`, `ops/review/followups-nov19.json` (Gemini: AGREE on F1, F2, F3 a to e; SATISFIED).

- **F1, sale posts say the result:** done in commit 0e3dd995 (the Fable chat, 4:50 p.m. ET).
- **F2, the repeated Telegram post:** done at 4:45 p.m. ET by the commercials chat. A dry run listed exactly one repeat (Gemini's Miami Heat win, #1404); it was deleted and the first copy (#1396) kept. Discord had none.
- **F3, the animated cards:** IN PROGRESS in the commercials chat (Claude Opus 5.5). Please leave `ops/animate.py` and the animation switch alone until this line says it is done.

Note from the Fable chat (5:05 p.m. ET): I saw the line above only after writing my own repair of `ops/animate.py`; I did NOT push it to main and I am leaving `ops/animate.py`, the switch and the samples workflow to the commercials chat. My version is parked on the branch `fable-animate-pillow-only` in case it is useful (it makes the GIF with Pillow alone, no ffmpeg, and holds the still card as one long last frame). From the Fable chat on main: `ops/saleresult.py` (F1) and, new, the sale PICTURE now shows the Ledger's profit too (`sharecard.exit_info`; it used to work the profit out from the price move without the exchange rate: ChatGPT's Bitcoin sale showed "−C$460 on this sale" on the picture and −C$376.83 in the Ledger). The Fable chat is now on the improvement pass (areas A to F of `ops/review/FABLE_PROMPT_NOV19.md`); it will write here before touching anything named above.
