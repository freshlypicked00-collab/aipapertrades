# Follow-ups agreed by Claude and Gemini (owner, Nov 19, 4:38 p.m. ET: "ask Gemini and do whatever you guys agree on")

Question and answers: `ops/asks/followups-nov19.txt`, `ops/review/followups-nov19.json` (Gemini: AGREE on F1, F2, F3 a to e; SATISFIED).

- **F1, sale posts say the result:** done in commit 0e3dd995 (the Fable chat, 4:50 p.m. ET).
- **F2, the repeated Telegram post:** done at 4:45 p.m. ET by the commercials chat. A dry run listed exactly one repeat (Gemini's Miami Heat win, #1404); it was deleted and the first copy (#1396) kept. Discord had none.
- **F3, the animated cards:** done by the commercials chat, 5:05 p.m. ET. Repaired (a), every animation must end exactly on its still card (b), ffmpeg from the imageio-ffmpeg pip package (c), at most 30 s an animation and 90 s a run (d), and samples of real posts made on GitHub's own runner (Pillow 13.0, Python 3.14) all ended exactly on their still cards (e): `ops/review/gif-samples/` (summary.json and a strip of frames for each). On again, with the switch kept (Gemini's and Claude's note): the repository variable PT_GIFS set to 0 turns them off without touching the code.
