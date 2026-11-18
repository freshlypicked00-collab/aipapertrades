# Slim top on every tab except the Overview (Nov 18)

Owner, Nov 18: the introduction (pick an AI, "You don't trade here", tagline, Fully autonomous, the long paragraph) should only be on the Overview; remove what isn't necessary in certain places for a better flowing page; work with Gemini.

Owner, Nov 18, 1:41 a.m. (sent through another chat, for this task): small changes are welcome too, not only big ones, whenever they are improvements the models agree on together.

Measured before: on a phone, a race's content started about 7,700 px down (about the tenth screen); on a computer about 3,000 px down.

Asked: Gemini only (owner said "work with Gemini"; ChatGPT's check-ins were failing for lack of OpenRouter credit). Answers: ops/review/layout-nov18.json. Claude's votes: ops/review/claude-votes-layout-nov18.json.
Result: Claude and Gemini agreed; Gemini SATISFIED.

Built:
- Overview: unchanged.
- Every other tab: the header shrinks to one line (leader, day, last check-in, Get alerts); status warnings stay; the race standings box, the big question and AI faces, the intro texts, Season 2 note, Best risk manager, disclaimer box, Model box, scoring line, the live alerts box, the headline strip and the definition strip are hidden.
- Gemini's change to P5: the short safety line goes at the TOP of each tab ("Pretend money, real prices. Not advice. We never take deposits or ask for money. Official accounts").
- Race pages: a one-tap AI switch (Claude | Gemini | ChatGPT); the race's own card and holdings first, then its scoreboard, that AI's take, the fact check and today's grades (Gemini's order).
- Phones: the long tab list above the content is hidden on every tab but the Overview (the Menu button does that job); tapping a tab opens it at its start.
- The "New here? 60-second tour" box is offered on the Overview only (Claude and Gemini).
- Computers: the logo row in the page header is hidden on non-Overview tabs (the sticky top bar already has it).

Measured after: phone, races start 280 to 610 px down, other tabs 360 to 780; computer 140 to 610. No console errors on any of the 26 tabs at 390 px or 1280 px.
