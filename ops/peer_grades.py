"""Peer grades (owner's idea, Oct 29, 2026; agreed by Claude, Gemini and ChatGPT with seven improvements G1-G7):
each AI grades the OTHER AIs' trades and bets, A to F plus one sentence, shown under each decision as a competitor's opinion.

G1 a fixed public rubric (thesis, sizing, risk control, use of what was known); strict risk-officer tone; no generic filler.
G2 every decision (owner, Oct 29: "make sure all decisions are graded by the two opposite models"): every trade and bet of the other
   two AIs since the Oct 28 restart, until all are graded; up to 50 per check-in, the newest first so new decisions are graded at the
   next check-in, and the older ones over the following check-ins. "no view" is allowed and shown.
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
MAX = 50   # raised from 20 so the backlog clears within about two check-ins (owner, Oct 29)
RESTART = datetime(2026, 10, 28, 17, 44, tzinfo=timezone.utc)
RUBRIC = ('PEER GRADES (agreed by all three AIs): grade every one of the other AIs\' trades, bets and holds (a hold: its latest decision not to trade in a race on a day) as a strict, fair chief risk officer, using only '
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


def _log_reason(log, t):
    """The log entry that explains one of Claude's trades: same race, same action, within 3 minutes, and naming this holding (two buys
    at the same minute each have their own entry; the first fix after a grader was shown the wrong one, Oct 29)."""
    near = [x for x in log if x.get('portfolio') == t['portfolio'] and x.get('action') == t['action']
            and abs((_when(x['at']) - _when(t['at'])).total_seconds()) < 180]
    name = str(t.get('holding', '')).lower()
    words = [w for w in re.findall(r'[a-z0-9]{3,}', name) if w not in ('etf', 'the', 'fund', 'shares', 'trust')]
    code = str(t.get('code') or '')
    def named(x):
        d = str(x.get('detail', '')).lower()
        return name and name in d or (code and code in d) or (words and all(w in d for w in words))
    for x in near:
        if named(x):
            return x['detail']
    if len(near) == 1:
        return near[0]['detail']
    # one entry can explain a paired trade under a different action, e.g. a "Buy" entry for "short US dollars and long yen":
    # the short is named in it, so its reason is that entry (fix, Oct 30: the US dollar short was graded F for "no reason" when it had one)
    pair = [x for x in log if x.get('portfolio') == t['portfolio'] and x.get('action') in ('Buy', 'Sell', 'Short', 'Cover')
            and abs((_when(x['at']) - _when(t['at'])).total_seconds()) < 180 and named(x)]
    return pair[0]['detail'] if len(pair) == 1 else ''


def claude_key_for_log(row, trades, bets):
    """The peer-grade key of the trade or bet one of Claude's log entries is about (same race and action, within 3 minutes, naming
    the holding or the bet), or None."""
    try:
        at = _when(row['at'])
    except Exception:
        return None
    d = str(row.get('detail', '')).lower()
    if row.get('action') == 'Bet':
        near = [b for b in bets if b.get('placed_at') and abs((_when(b['placed_at']) - at).total_seconds()) < 180]
        hit = [b for b in near if str(b.get('bet', '')).lower() in re.findall(r'\bs\d+\b', d) or str(b.get('pick', '')).lower().replace(' moneyline', '') in d]
        b = hit[0] if len(hit) == 1 else near[0] if len(near) == 1 else None
        return key_of('claude', b['placed_at'], 'Sports', b['bet'], 'Bet') if b else None
    if row.get('action') not in ('Buy', 'Sell', 'Short', 'Cover'):
        return None
    near = [t for t in trades if t.get('portfolio') == row.get('portfolio') and t.get('action') == row['action'] and not str(t.get('holding', '')).startswith('[')
            and abs((_when(t['at']) - at).total_seconds()) < 180]
    def named(t):
        name = str(t.get('holding', '')).lower()
        words = [w for w in re.findall(r'[a-z0-9]{3,}', name) if w not in ('etf', 'the', 'fund', 'shares', 'trust')]
        return (name and name in d) or (t.get('code') and str(t['code']) in d) or (words and all(w in d for w in words))
    hit = [t for t in near if named(t)]
    t = hit[0] if len(hit) == 1 else near[0] if len(near) == 1 else None
    return key_of('claude', t['at'], t['portfolio'], t['holding'], t['action']) if t else None


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
            why = t.get('note') or _log_reason(log, t)
            out.append({'key': key_of('claude', t['at'], t['portfolio'], t['holding'], t['action']), 'model': 'claude', 'at': t['at'],
                        'experiment': t['portfolio'], 'action': t['action'], 'what': t['holding'], 'amount': round(amt, 2),
                        'price': px, 'reason': why[:500], 'wrong_if': ''})
        for b in _j('bets', []):
            if not b.get('placed_at') or _when(b['placed_at']) < datetime(2026, 10, 28, 17, 44, tzinfo=timezone.utc):
                continue
            out.append({'key': key_of('claude', b['placed_at'], 'Sports', b['bet'], 'Bet'), 'model': 'claude', 'at': b['placed_at'], 'experiment': 'Sports',
                        'action': 'Bet', 'what': f"{b['pick']} ({b['event']})", 'amount': float(b.get('stake_cad') or 0), 'price': b.get('odds'),
                        'reason': (b.get('note') or '')[:500], 'wrong_if': ''})
    # every AI's All in moves (Claude's are in rivals.json too) and Gemini's and ChatGPT's main-race moves
    for t in state.get('trades', []):
        if t.get('model') != model or t.get('action') not in ('Buy', 'Sell', 'Short', 'Cover', 'Bet') or t.get('stop'):   # cancelled (void) bets were decisions too: graded (owner, Oct 29)
            continue
        if model == 'claude' and not str(t.get('experiment', '')).startswith('AllIn'):
            continue
        amt = abs(float(t.get('amount') or 0)) * (fx_cad if t.get('cur') == 'USD' else 1)
        out.append({'key': key_of(model, t['at'], t['experiment'], t.get('symbol', ''), t['action']), 'model': model, 'at': t['at'],
                    'experiment': t['experiment'], 'action': t['action'], 'what': t.get('name') or t.get('symbol'), 'amount': round(amt, 2),
                    'price': t.get('price'), 'reason': (t.get('reason') or '')[:500], 'wrong_if': (t.get('wrong_if') or '')[:300]})
    out.extend(_holds(model, state, out))
    out.sort(key=lambda d: _when(d['at']))
    return out


ACTING = re.compile(r'\b(initiat\w*|buying|selling|adding|shorting|covering|placing|trimming|exiting|opening a|closing out|taking a|entering)\b', re.I)


def _holds(model, state, acted):
    """HOLDS (owner's request, Oct 29; all three AIs voted yes): the decision NOT to trade in a race, graded as "was waiting the right call?".
    One per AI, race and race day: its latest note on that race (Claude's race take; Gemini's and ChatGPT's per-race note) written at a
    check-in where it made no trade or bet in that race (none within 15 minutes), for race days that have closed (00:00 UTC). Routine
    record-keeping (accuracy checks, closing odds, daily close lines) is never a note, so it is never graded."""
    notes = [x for x in _j('take', []) if x.get('experiment')] if model == 'claude' else \
        [x for x in state.get('thoughts', []) if x.get('model') == model and x.get('experiment')]
    today = datetime.now(timezone.utc).date()
    moves = {}
    for d in acted:
        moves.setdefault(d['experiment'], []).append(_when(d['at']))
    last = {}
    for x in notes:
        try:
            at = _when(x['at'])
        except Exception:
            continue
        e = x['experiment']
        if at < RESTART or at.date() >= today or not str(x.get('text', '')).strip():
            continue
        if any(-900 < (m - at).total_seconds() < 3 * 3600 for m in moves.get(e, [])) or ACTING.search(str(x.get('text', ''))):
            continue   # a note written with a trade, or about one it was placing (filled within 3 hours), is not a hold
        k = (e, at.date())
        if k not in last or at > _when(last[k]['at']):
            last[k] = x
    return [{'key': key_of(model, x['at'], x['experiment'], 'hold', 'Hold'), 'model': model, 'at': _when(x['at']).strftime('%Y-%m-%dT%H:%M:%SZ'),
             'experiment': x['experiment'], 'action': 'Hold', 'what': '(no trade in this race)', 'amount': 0.0, 'price': None,
             'reason': str(x['text'])[:500], 'wrong_if': ''} for x in last.values()]


def _voids(grader):
    """{key: withdrawn at} for this grader's grades withdrawn by the site (ops/src/peer_grades_void.json: the grader was shown wrong
    information because of a site bug); such a decision is offered again with the right information."""
    return {v['key']: v.get('at', '') for v in _j('peer_grades_void', []) if v.get('grader') == grader}


def graded_keys(grader, state):
    rows = _j('claude_grades', []) if grader == 'claude' else [g for g in state.get('peer_grades', []) if g.get('grader') == grader]
    vo = _voids(grader)
    return {g['key'] for g in rows if g['key'] not in vo or str(g.get('at', '')) > vo[g['key']]}


def last_graded(grader, state):
    if grader == 'claude':
        meta = _j('claude_grades_meta', {})
        return meta.get('last')
    return (state.get('peer_grades_meta') or {}).get(grader)


def tasks(grader, state, now, fx_cad=1.38):
    """(text for the grader, {gid: decision}) or ('', {}) when nothing is new. G2 selection, G3 no hindsight, G4 anonymous."""
    others = [m for m in ('claude', 'gemini', 'chatgpt') if m != grader]
    done = graded_keys(grader, state)
    pool = [d for m in others for d in decisions(m, state, fx_cad) if d['key'] not in done and RESTART <= _when(d['at']) <= now]
    if not pool:
        return '', {}
    pick = sorted(pool, key=lambda d: _when(d['at']), reverse=True)[:MAX]   # every decision gets graded: the newest first, the rest over the next check-ins
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
        if d['action'] == 'Hold':
            lines.append(f"  - {gid}: {alias[d['model']]}, {d['at'][:16].replace('T', ' ')} UTC, {d['experiment']}: HOLD (it chose not to trade in this race "
                         f"that day; judge whether waiting was the right call given what was known). Its view then: \"{d['reason']}\"")
            continue
        lines.append(f"  - {gid}: {alias[d['model']]}, {d['at'][:16].replace('T', ' ')} UTC, {d['experiment']}: {d['action']} {d['what']}, "
                     f"about C${d['amount']:,.0f} at {pxs}. Its reason then: \"{d['reason'] or '(none given)'}\""
                     + (f" What it said would prove it wrong: \"{d['wrong_if']}\"" if d['wrong_if'] else ''))
    text = (RUBRIC + f' Decisions to grade now ({len(pick)}' + (f' newest of {len(pool)} not yet graded by you; the rest come at your next check-ins' if len(pool) > MAX else ' not yet graded by you') + '; the competitors are anonymous and reshuffled each time; grade each only on what was known when it was made, even if it was made a while ago):\n'
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
