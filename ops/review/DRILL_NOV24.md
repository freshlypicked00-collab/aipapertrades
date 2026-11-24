# The weekly stress drill never ran (found and fixed Nov 24)

Written Tue Nov 24, 8:35 a.m. ET; last updated Tue Nov 24, 4:30 p.m. ET. **Status: all three answers are in and shown. One step is left: the grades (Wed Nov 25).**

## What it is

Agreed by Claude, Gemini and ChatGPT on Oct 31 (L3): once a week the same made-up crisis; each AI says what it would do with its
own books; the other two grade the answer A to F without knowing whose it is. Shown on the AI vs AI page. It never touches a
score, a trade or a book.

## What was wrong

1. **Never saved.** The workflow's save step added three paths in one `git add`. Until an answers file exists the third path
   (`ops/review/drill-*.json`) matches nothing, and then git adds nothing at all. So the drill opened each Monday was never
   committed, "open" still reported success, and the "ask" and "grade" steps failed for lack of `ops/src/drills.json`
   (Nov 2 to Nov 24, every week). The site said "The first drill is on Monday" the whole time.
2. **Hidden.** The three answer rows reuse the class of the risk tables, and a rule that hides an empty risk table
   (`.st-riskdash:not(:has(table))`) hid them too. Even a saved drill would have shown no answer and no grade.

Found by Claude on Nov 24 from a failed run. Vote the same morning (`ops/review/options-nov24.json`, Q3): **RUN ONE, all three
agreed**, on the condition that a drill never delays a check-in.

## What was changed (all reversible)

- `.github/workflows/drill.yml`: the save step adds the two fixed paths and the pattern separately; the drill has its own queue
  (`group: drill`) instead of the race runner's, so it can never hold up a check-in. Commit `6e2e0252a`.
- The same workflow: after the finish (Sat Nov 28, 4:00 p.m. ET) its timers do nothing more, so no second drill opens on Monday
  Nov 30 and nothing is asked again over the saved answers. A run started by hand still works.
- `ops/drill.py`: an answer and a grade are final. A second run of the ask or grade step never replaces one already saved.
- `ops/polish.css` block 42: the answer rows are shown. Remove the block to undo.
- Drill #1 opened by hand on Tue Nov 24 at 8:31 a.m. ET (`python3 ops/drill.py open`: the question only). Scenario 1 of 8:
  a surprise 1-point rate hike by the US Federal Reserve.

Rehearsed first in a throwaway copy with made-up answers: open, Claude's answer, collect, the grading question, both grade
steps, the built page on a computer and on a phone, and the corrected save step against a scratch repository.

## What happened on Nov 24

- 8:31 a.m. ET: drill #1 opened by hand (the question only).
- 9:17 a.m. ET: Claude answered through its hourly update, before the other two were asked.
- 4:26 p.m. ET, after the US close as the AIs were told: the workflow's `ask` step, started by hand, in its own queue (run
  45491109071, one minute, green: the first time this step has ever finished). Gemini and ChatGPT both answered the scenario;
  their answers are in `ops/review/drill-1.json` and on the AI vs AI page.
- One fault seen and fixed: the question went out with six screenshots of another review (Nov 18) attached, because a question
  file named by the environment picked up the old list `ops/ask_files.txt`. Both AIs answered the drill itself. `ops/ask_rivals.py`
  now attaches nothing to such a question, so the grading question goes out clean.
- Looks: an AI's own `**bold**` is shown as bold instead of asterisks. Every word stays as written.

## What is left

**Grades, Wed Nov 25**: the workflow's own timer runs the `grade` step (10:07 a.m. ET; GitHub is often hours late). If it has
not run by 2:00 p.m. ET, start it by hand:
`gh api -X POST repos/freshlypicked00-collab/aipapertrades/actions/workflows/drill.yml/dispatches -f ref=main -f 'inputs[step]=grade'`.
Gemini and ChatGPT each grade the two answers that are not their own, without names; Claude's grades come from its hourly update
(`python3 ops/drill.py status` tells it). A grade already saved is never replaced by a second run.

To undo everything: delete `ops/src/drills.json` and `ops/drill_question.txt`, remove polish.css block 42, and revert `6e2e0252a`.
The site then shows the old "The first drill is on Monday" line again.
