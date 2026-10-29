"""Peer grades (owner's idea, Oct 29, 2026; agreed by Claude, Gemini and ChatGPT with seven improvements G1-G7):
each AI grades the OTHER AIs' trades and bets, A to F plus one sentence, shown under each decision as a competitor's opinion.

G1 a fixed public rubric (thesis, sizing, risk control, use of what was known); strict risk-officer tone; no generic filler.
G2 neutral selection: every new trade and bet since the grader's last grading; if more than 5, the 5 largest by amount.
   "no view" is allowed and shown.
G3 no hindsight: the grader sees only what was known at the decision (time, price then, size, reason, what would prove it
   wrong), never today's price or the result.
G4 anonymous: "Competitor A" and "Competitor B", reshuffled at every grading.
G5 bias check and G6 track record are computed by build_site.py from the stored grades.
G7 shown as "<grader>'s view (a competitor's opinion)"; never changes a score; no replies or edits.

Gemini and ChatGPT grade inside their check-ins (ops/rivals.py); Claude grades in its own sessions with ops/grades.py.
Grades by Gemini and ChatGPT: rivals.json "peer_grades"; Claude's: ops/src/claude_grades.json.
"""
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SRC = 'ops/src'
MAX = 5
RUBRIC = ('PEER GRADES (agreed by all three AIs): grade the other AIs\' new trades and bets as a strict, fair chief risk officer, using only '
          'what was known when each decision was made (never how it turned out): (1) thesis quality: is the reason specific, sourced and '
          'sensible? (2) sizing: does the size fit the conviction and the caps? (3) risk control: is there a clear exit or "what would prove it '
          'wrong"? (4) use of the information available at the time. Grades: A excellent, B good, C acceptable, D poor, F reckless; or '
          '"no view" if you honestly cannot judge it. The sentence must be 25 words or fewer and name one specific strength or flaw in the logic or '
          'the risk; generic filler like "good trade" is not allowed. Be fair: the same standard for every competitor. Your grade is shown publicly '
          'as your opinion, labelled as a competitor\'s view; it never changes any score.')
WORDS = re.compile(r'\S+')


def _when(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def _j(name, default):
    try:
        return json.load(open(os.path.join(SRC, name + '.json')))
    except Exception:
        return default


def key_of(model, at, exp, what, action):
    return f'{model}|{_when(at).strftime("%Y-%m-%dT%H:%M:%SZ")}|{exp}|{what}|{action}'


def decisions(model, state, fx_cad=1.38):
    """Every trade and bet one AI decided itself (not automatic settlements), newest last, with what was known at the time."""
    out = []
    if model == 'claude':
        log = _j('log', [])
        for t in _j('trades', []):
            if str(t.get('holding', '')).startswith('[') or t.get('action') not in ('Buy', 'Sell', 'Short', 'Cover'):
                continue
            if _when(t['at']) < datetime(2026, 10, 28, 17, 44, tzinfo=timezone.utc):
                continue
            amt = abs(float(t.get('cad') or 0)) or abs(float(t.get('usd') or 0)) * fx_cad
            px = t.get('price_usd', t.get('price_local'))
            why = t.get('note') or next((x['detail'] for x in log if x.get('portfolio') == t['portfolio'] and x.get('action') == t['action']
                                         and abs((_when(x['at']) - _when(t['at'])).total_seconds()) < 180), '')
            out.append({'key': key_of('claude', t['at'], t['portfolio'], t['holding'], t['action']), 'model': 'claude', 'at': t['at'],
                        'experiment': t['portfolio'], 'action': t['action'], 'what': t['holding'], 'amount': round(amt, 2),
                        'price': px, 'reason': why[:500], 'wrong_if': ''})
        for b in _j('bets', []):
            if not b.get('placed_at') or _when(b['placed_at']) < datetime(2026, 10, 28, 17, 44, tzinfo=timezone.utc):
                continue
            out.append({'key': key_of('claude', b['placed_at'], 'Sports', b['bet'], 'Bet'), 'model': 'claude', 'at': b['placed_at'], 'experiment': 'Sports',
                        'action': 'Bet', 'what': f"{b['pick']} ({b['event']})", 'amount': float(b.get('stake_cad') or 0), 'price': b.get('odds'),
                        'reason': (b.get('note') or '')[:500], 'wrong_if': ''})
    else:
        for t in state.get('trades', []):
            if t.get('model') != model or t.get('action') not in ('Buy', 'Sell', 'Short', 'Cover', 'Bet') or t.get('stop') or t.get('void'):
                continue
            amt = abs(float(t.get('amount') or 0)) * (fx_cad if t.get('cur') == 'USD' else 1)
            out.append({'key': key_of(model, t['at'], t['experiment'], t.get('symbol', ''), t['action']), 'model': model, 'at': t['at'],
                        'experiment': t['experiment'], 'action': t['action'], 'what': t.get('name') or t.get('symbol'), 'amount': round(amt, 2),
                        'price': t.get('price'), 'reason': (t.get('reason') or '')[:500], 'wrong_if': (t.get('wrong_if') or '')[:300]})
    out.sort(key=lambda d: _when(d['at']))
    return out


def graded_keys(grader, state):
    if grader == 'claude':
        return {g['key'] for g in _j('claude_grades', [])}
    return {g['key'] for g in state.get('peer_grades', []) if g.get('grader') == grader}


def last_graded(grader, state):
    if grader == 'claude':
        meta = _j('claude_grades_meta', {})
        return meta.get('last')
    return (state.get('peer_grades_meta') or {}).get(grader)


def tasks(grader, state, now, fx_cad=1.38):
    """(text for the grader, {gid: decision}) or ('', {}) when nothing is new. G2 selection, G3 no hindsight, G4 anonymous."""
    others = [m for m in ('claude', 'gemini', 'chatgpt') if m != grader]
    since = last_graded(grader, state)
    floor = now - timedelta(hours=24)
    since_t = max(_when(since), floor) if since else floor
    done = graded_keys(grader, state)
    pool = [d for m in others for d in decisions(m, state, fx_cad) if _when(d['at']) > since_t and d['key'] not in done and _when(d['at']) <= now]
    if not pool:
        return '', {}
    pick = sorted(pool, key=lambda d: -d['amount'])[:MAX] if len(pool) > MAX else pool
    pick.sort(key=lambda d: _when(d['at']))
    letters = ['Competitor A', 'Competitor B']
    rnd = random.Random(f'{grader}|{now.isoformat()}')
    rnd.shuffle(letters)
    alias = dict(zip(others, letters))
    mapping, lines = {}, []
    for i, d in enumerate(pick, 1):
        gid = f'g{i}'
        mapping[gid] = d
        px = d['price']
        pxs = (f'{int(px):+d} (American odds)' if d['action'] == 'Bet' and px is not None else f'{float(px):,.6g}' if px is not None else 'n/a')
        lines.append(f"  - {gid}: {alias[d['model']]}, {d['at'][:16].replace('T', ' ')} UTC, {d['experiment']}: {d['action']} {d['what']}, "
                     f"about C${d['amount']:,.0f} at {pxs}. Its reason then: \"{d['reason'] or '(none given)'}\""
                     + (f" What it said would prove it wrong: \"{d['wrong_if']}\"" if d['wrong_if'] else ''))
    text = (RUBRIC + f' Decisions to grade now ({len(pick)}' + (f' largest of {len(pool)} new' if len(pool) > MAX else ' new') + '; the competitors are anonymous and reshuffled each time):\n'
            + '\n'.join(lines) + '\nAdd a top-level field "grades": {"g1": {"grade": "A" | "B" | "C" | "D" | "F" | "no view", "text": "one sentence, 25 words or fewer"}, ...} covering every id above.')
    return text, mapping


def clean(g):
    if not isinstance(g, dict):
        return None
    grade = str(g.get('grade', '')).strip().upper().replace('NO VIEW', 'no view')
    if grade.lower() == 'no view':
        grade = 'no view'
    elif grade[:1] in 'ABCDF':
        grade = grade[:1] + (grade[1] if len(grade) > 1 and grade[1] in '+-' else '')
    else:
        return None
    words = WORDS.findall(str(g.get('text', '')).strip())
    if grade != 'no view' and not words:
        return None
    text = ' '.join(words[:30])
    return {'grade': grade, 'text': text}


def store(state, grader, reply_grades, mapping, now_iso):
    """Gemini's and ChatGPT's grades into rivals.json."""
    n = 0
    for gid, d in mapping.items():
        g = clean((reply_grades or {}).get(gid)) if isinstance(reply_grades, dict) else None
        if not g:
            continue
        state.setdefault('peer_grades', []).append({'at': now_iso, 'grader': grader, 'model': d['model'], 'key': d['key'], 'decision_at': d['at'],
                                                    'experiment': d['experiment'], 'action': d['action'], 'what': d['what'], **g})
        n += 1
    if mapping:
        state.setdefault('peer_grades_meta', {})[grader] = now_iso
    return n
