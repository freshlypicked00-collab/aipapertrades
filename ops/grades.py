"""Claude's side of the peer grades (agreed by all three AIs, Oct 29): Claude grades Gemini's and ChatGPT's new trades and bets
with the same rubric, selection and anonymity they use for Claude's (see ops/peer_grades.py).

  python3 ops/grades.py todo
      prints the rubric and up to 5 decisions to grade, as "Competitor A/B" (who is who is not shown), and saves the list
  python3 ops/grades.py submit '{"g1": {"grade": "B", "text": "one sentence, 25 words or fewer"}, "g2": {"grade": "no view", "text": ""}}'
      stores Claude's grades in ops/src/claude_grades.json (shown on the site as "Claude's view (a competitor's opinion)")
Grade only on what was known when each decision was made, never on how it turned out. Then commit and push ops/src.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_grades as P  # noqa: E402

TODO = os.path.join(P.SRC, 'claude_grades_todo.json')
OUT = os.path.join(P.SRC, 'claude_grades.json')
META = os.path.join(P.SRC, 'claude_grades_meta.json')


def _state():
    try:
        return json.load(open(os.path.join(P.SRC, 'rivals.json')))
    except Exception:
        return {}


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if cmd == 'todo':
        st = _state()
        fx = (st.get('fx') or {}).get('USDCAD', 1.38)
        text, mapping = P.tasks('claude', st, now, fx)
        if not mapping:
            print('Nothing new to grade.')
            json.dump({}, open(TODO, 'w'))
            sys.exit(0)
        json.dump({'at': now.isoformat(), 'items': mapping}, open(TODO, 'w'), indent=1, ensure_ascii=False)
        print(text.replace('Add a top-level field "grades": ', 'Then run: python3 ops/grades.py submit \'').rstrip() + "'")
    elif cmd == 'submit':
        todo = json.load(open(TODO)) if os.path.exists(TODO) else {}
        mapping = todo.get('items') or {}
        if not mapping:
            sys.exit('Run `python3 ops/grades.py todo` first (or there was nothing to grade).')
        given = json.loads(sys.argv[2])
        out = json.load(open(OUT)) if os.path.exists(OUT) else []
        n = 0
        for gid, d in mapping.items():
            g = P.clean(given.get(gid))
            if not g:
                print(f'{gid}: missing or invalid (grade A-F or "no view", plus one sentence); skipped')
                continue
            out.append({'at': now.isoformat().replace('+00:00', 'Z'), 'grader': 'claude', 'model': d['model'], 'key': d['key'], 'decision_at': d['at'],
                        'experiment': d['experiment'], 'action': d['action'], 'what': d['what'], **g})
            n += 1
        json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
        json.dump({'last': now.isoformat().replace('+00:00', 'Z')}, open(META, 'w'))
        json.dump({}, open(TODO, 'w'))
        print(f'saved {n} grade(s)')
    else:
        sys.exit(__doc__)
