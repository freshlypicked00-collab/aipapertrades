# Discord commercial, v1 (Nov 4)
Owner, Nov 4 1:48 a.m. ET: "make a comercial for papertrades.ai adveritsing the discord channel work with gpt and gemini for the ideas make it high production"
Answers: ops/review/discord-ad-nov4.json (Gemini 3.1 Pro, GPT-5.5). Claude's concept, written first: ops/review/discord-ad-claude-concept.md.

## What all three agreed
- One real story as the spine: Gemini's C$35,000 on underdog USC at +200 (G-AIS-019/024/026), graded by its rivals BEFORE the game
  (Claude C, ChatGPT B), final USC 30 - Ohio State 18, then the channels and the invite.
- Each AI speaks its own words (Gemini its reason, Claude its grade); our robots in their colours; the real cards the server posts.
- Code-made motion graphics (camera moves, depth, springy easing, particles), our own synthesized music with the voice ducking it,
  our own UI sounds (no Discord sounds), burned-in captions, everything inside the safe zone.
- End card: the logo, a small "Join on Discord" badge only (Discord is never our brand), the invite, not advice.
- Leave out the -6500 "virtually safe" bet (Gemini and ChatGPT; Claude agrees).

## Where they differed, and what was used
- The payout: Gemini said +C$40,000 (one ticket); ChatGPT and Claude said +C$70,000 (all three tickets). Used C$70,000 (2 of 3),
  with the ticket IDs on screen; the feed shows the single C$40,000 post as the server posted it.
- ChatGPT's grade (B) also gets its own voice line (Claude's addition), so all three AIs speak.
- Avoided words both flagged for ad review: "all in", "8 wins in a row", "bankroll" (Claude's quote is cut before "bankroll").

## Risks (both): sports odds, stakes and payouts can trip gambling-ad review on Instagram, TikTok, YouTube and Reddit even as
pretend money. Organic posts are fine; a PAID ad may be rejected: a trading-story version would be the safer paid ad.

Video: ops/discord_ad.py (renders from data.json; stops if a fact changed). Voice: ops/voice/discord-ad-v1.json (Gemini TTS).
Music and sounds: ops/ad_audio.py (synthesized, nothing licensed). 1080x1920, 30 fps, 35.8 s, -14 LUFS.
Title (<= 70): "Gemini bet C$35K on USC. Claude gave it a C. AI vs AI, live"
Caption: see ops/nicole/2026-11-04-discord-ad.md
