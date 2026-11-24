# The weekly stress drill never ran (found and fixed Nov 24)

Written Tue Nov 24, 8:36 a.m. ET. **Status: drill #1 is open; two steps are left (below).**

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
- `ops/drill.py`: an answer and a grade are final. A second run of the ask or grade step never replaces one already saved.
- `ops/polish.css` block 42: the answer rows are shown. Remove the block to undo.
- Drill #1 opened by hand on Tue Nov 24 at 8:31 a.m. ET (`python3 ops/drill.py open`: the question only). Scenario 1 of 8:
  a surprise 1-point rate hike by the US Federal Reserve.

Rehearsed first in a throwaway copy with made-up answers: open, Claude's answer, collect, the grading question, both grade
steps, the built page on a computer and on a phone, and the corrected save step against a scratch repository.

## What is left

1. **Claude's answer**: its hourly update does it by itself (`ops/TASK_PROMPT.md`: `python3 ops/drill.py status`, then
   `python3 ops/drill.py claude "<answer>"`). It must be in before step 2; after that Claude can no longer answer.
2. **Gemini's and ChatGPT's answers, after the US close on Tue Nov 24** (the AIs were told so): start the workflow
   "Weekly stress drill" by hand with step `ask`
   (`gh api -X POST repos/freshlypicked00-collab/aipapertrades/actions/workflows/drill.yml/dispatches -f ref=main -f 'inputs[step]=ask'`).
   It asks both, stores the answers and closes answering. Do not start it while Claude's answer is being pushed.
3. **Grades, Wed Nov 25**: the workflow's own timer runs the `grade` step (10:07 a.m. ET; GitHub is often hours late). If it has
   not run by the afternoon, start it by hand with step `grade`. Claude's grades come from its hourly update.

To undo everything: delete `ops/src/drills.json` and `ops/drill_question.txt`, remove polish.css block 42, and revert `6e2e0252a`.
The site then shows the old "The first drill is on Monday" line again.
