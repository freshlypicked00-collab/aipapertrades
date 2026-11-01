# Report-card grades and race pickers (owner, Oct 31, 10 p.m. ET)
Owner: "make the other models make a grade here, work with ChatGPT and Gemini to set that up; #2 for Coming up make it so you can select the race you want, same for Distance to the next trade; do this for all ledgers including All in, for all models."

Votes (ops/review/reportcard-grades-oct31.json; Claude voted first, blind):
- Option B, a new grading step for report cards: all three agreed. Option A (average of existing trade grades) rejected by all three.
- Display D (a chip per grader, tap for the reason): all three agreed. Labels: Gemini and ChatGPT asked for "Competitor A/B" instead of model names (2 of 3; Claude had proposed names) -> anonymous labels used.
- Rubric additions adopted: judge candor and reasoning, not outcome alone; a material factual error caps at C, a materially misleading claim can be F; "no view" only when information is insufficient (ChatGPT); penalise hindsight excuses and unjustified overconfidence in the plan (Gemini).
- Risks noted: hindsight bias and tit-for-tat grading (both); cost of the backfill (Gemini) -> report cards take at most 20 of the 50 places per batch, so new trades are never delayed.

Built:
- ops/peer_grades.py: each AI's final report card per race and closed race day joins the same anonymous queue (action "Report"), with that day's result shown to the grader; RUBRIC_RC added. Gemini and ChatGPT grade in their check-ins, Claude with ops/grades.py. build_site.py moves them to data["report_grades"], so trade-grade averages and stories never mix them in. Test added.
- Ledger and All in ledger: report card lines show "Competitor A's view" / "Competitor B's view" chips.
- Race picker on Coming up and Distance to the next trade (Ledger: all ten races + both All in parts; All in ledger: both parts), every model. All in stops are now listed (priced from the All in feed).
- All in ledger: its own Distance, Coming up and Report card sections.
- Claude's task: report cards now include AllInTrading and AllInSports lines.
