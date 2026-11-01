"""Looking back: a short reflection by the AI that made a trade, after it is complete (owner's idea, Oct 31; Claude, Gemini and
ChatGPT all agreed on every point, L1-L7: ops/review/lookback-oct31.json).

A move is "complete" when it closes the holding: the sale or cover that brings it to zero, a bet that is won or lost, an option
that settles or expires. Partial sales are not complete. Only moves completed from GO_LIVE on get a reflection (L6: no
rewriting history). The reflection never replaces the original reason or the peer grades (L1) and is never fed back into
the AI's later prompts during Season 1 (L4): it is only displayed.

Format (L2): one verdict from VERDICTS plus at most 40 words (cut to 40 here, the same for all three AIs).
When (L3): at that AI's next regular check-in, no extra calls. Gemini and ChatGPT get the task in their check-in prompt
(rivals.py); Claude gets the same task in its run (`python3 ops/lookback.py due`, then `add`). If an AI does not answer at that
check-in, the site says so plainly ("No reflection returned at its next check-in"), as ChatGPT asked.

Where they live: Gemini's and ChatGPT's (and every AI's High risk) in rivals.json "lookbacks" {ID: {...}} (runner only);
Claude's ten races in ops/src/lookbacks_claude.json (Claude's run only). Keyed by the public transaction ID of the closing move.

  python3 ops/lookback.py due            -> Claude's completed moves still waiting for a reflection, with the original reasons
  python3 ops/lookback.py add ID VERDICT "text"   -> Claude's reflection on that closing move (ID like C-STK-004)
"""
from datetime import datetime, timezone
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import txids as TX

GO_LIVE = '2026-10-31T05:45:00Z'
VERDICTS = ['Good call', 'Bad call', 'Lucky', 'Unlucky', 'Too early', 'Too late']
MAX_WORDS = 40
MAX_PER_CHECKIN = 6
CLAUDE_FILE = os.path.join(TX.SRC, 'lookbacks_claude.json')
CLOSE_BET = ('Won', 'Lost')
CLOSE_OPT = ('Expired', 'Settled')
LABEL = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}


def _j(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def _clip_words(s, n=MAX_WORDS):
    w = str(s or '').split()
    return ' '.join(w[:n]).rstrip(',;:') + ('…' if len(w) > n else '')


def verdict(v):
    v = str(v or '').strip().lower().replace('-', ' ')
    return next((x for x in VERDICTS if x.lower() == v), None)


def _money(v):
    return ('+' if v >= 0.5 else '−' if v <= -0.5 else '') + f'C${abs(v):,.0f}'


def closings(model, state):
    """Every completed move of this AI from GO_LIVE on: [{id, key, at, exp, what, result, reasons}], oldest first.
    id is None until the race runner gives the closing move its transaction ID."""
    reg = state.get('txids', {})
    out = []
    # 1. moves in rivals.json: Gemini's and ChatGPT's ten races, and every AI's High risk
    rows = sorted([t for t in state.get('trades', []) if t.get('model') == model], key=lambda t: TX.utc(t['at']))
    held, cash_in, reasons, bets = {}, {}, {}, {}
    for t in rows:
        a, k = t.get('action'), (t.get('experiment'), t.get('symbol'))
        amt = float(t.get('amount') or 0)
        if a == 'Bet':
            bets[(t.get('experiment'), t.get('bet') or t.get('symbol'))] = t
            continue
        if a in CLOSE_BET:
            b = bets.get((t.get('experiment'), t.get('bet') or t.get('symbol')))
            if TX.utc(t['at']) >= GO_LIVE:
                out.append({'key': TX.rival_key(t), 'at': t['at'], 'exp': t['experiment'], 'what': (b or t).get('name') or t.get('name', ''),
                            'result': f"{a} ({_money(amt)})", 'reasons': [b['reason']] if b and b.get('reason') else []})
            continue
        if a in ('Buy', 'Short'):
            q0 = held.get(k, 0.0)
            if abs(q0) < 1e-12:
                cash_in[k] = 0.0; reasons[k] = []
            held[k] = q0 + (float(t.get('qty') or 0) * (1 if a == 'Buy' else -1))
            cash_in[k] = cash_in.get(k, 0.0) + (-amt if a == 'Buy' else amt)
            if t.get('reason'):
                reasons.setdefault(k, []).append(t['reason'])
            continue
        if a in ('Sell', 'Cover') or a in CLOSE_OPT:
            q0 = held.get(k, 0.0); q = float(t.get('qty') or 0)
            q1 = q0 - q if a == 'Sell' else q0 + q if a == 'Cover' else 0.0
            cash_in[k] = cash_in.get(k, 0.0) + (amt if a != 'Cover' else -amt)
            held[k] = q1
            if abs(q1) <= max(1e-9, abs(q0) * 1e-6):   # nothing left: the trade is complete
                held[k] = 0.0
                if TX.utc(t['at']) >= GO_LIVE:
                    out.append({'key': TX.rival_key(t), 'at': t['at'], 'exp': t['experiment'], 'what': t.get('name') or t.get('symbol', ''),
                                'result': f"closed, about {_money(cash_in.get(k, 0.0))} over the whole holding", 'reasons': reasons.get(k, [])[-3:]})
    # 2. Claude's ten races (its own files)
    if model == 'claude':
        trs = sorted(_j(os.path.join(TX.SRC, 'trades.json'), []), key=lambda t: TX.utc(t['at']))
        rs = {}
        for t in trs:
            if str(t.get('holding', '')).startswith('['):
                continue
            k = (t.get('portfolio'), t.get('holding'))
            if t.get('action') in ('Buy', 'Short'):
                if not t.get('held_before'):
                    rs[k] = []
                rs.setdefault(k, []).append(re.split(r' What would prove it wrong:', t.get('note', ''))[0])
            elif t.get('action') in ('Sell', 'Cover') and not float(t.get('held_after') or 0) and TX.utc(t['at']) >= GO_LIVE:
                pnl = t.get('pnl_cad')
                out.append({'key': TX.claude_trade_key(t), 'at': t['at'], 'exp': t['portfolio'], 'what': t.get('holding', ''),
                            'result': 'closed' + (f', {_money(float(pnl))} on the last sale' if pnl is not None else ''), 'reasons': rs.get(k, [])[-3:]})
        for b in _j(os.path.join(TX.SRC, 'bets.json'), []):
            k1, k2 = TX.claude_bet_keys(b)
            if b.get('status') in CLOSE_BET and k2 and k2.split('|')[2] >= GO_LIVE:
                r = b.get('result_cad')
                out.append({'key': k2, 'at': b.get('settled_at') or b.get('placed_at'), 'exp': 'Sports', 'what': f"{b.get('pick', '')} ({b.get('event', '')})",
                            'result': b['status'] + (f' ({_money(float(r))})' if r is not None else ''), 'reasons': [b['note']] if b.get('note') else []})
    for c in out:
        c['id'] = reg.get(c['key'])
    return sorted(out, key=lambda c: TX.utc(c['at']))


def done_ids(state):
    return set(state.get('lookbacks', {})) | {x.get('id') for x in _j(CLAUDE_FILE, [])}


def tasks(model, state):
    """(prompt text, [IDs asked]) for Gemini's or ChatGPT's next check-in; ('', []) when nothing is due."""
    done = done_ids(state)
    due = [c for c in closings(model, state) if c['id'] and c['id'] not in done][:MAX_PER_CHECKIN]
    if not due:
        return '', []
    lines = [f"  - {c['id']}: {LABEL_EXP(c['exp'])}, {c['what']}, completed {TX.utc(c['at'])[:16].replace('T', ' ')} UTC: {c['result']}. "
             f"Your reason(s) when you opened it: " + (' / '.join(f'"{r}"' for r in c['reasons']) if c['reasons'] else '(none recorded)') for c in due]
    text = ('LOOKING BACK (new, the same for all three AIs): these trades of yours are now complete. For each, look back honestly in your own words: '
            'pick one verdict (' + ' / '.join(VERDICTS) + ') and write at most 40 words on what went right or wrong and one lesson. It is shown publicly '
            'under the closing move, labelled as written after the result; it never changes your original reason, the grades or the scores, and it is '
            'not shown to you again later this season.\n' + '\n'.join(lines) +
            '\nAdd a top-level field "looking_back": {' + ', '.join(f'"{c["id"]}": {{"verdict": "...", "text": "..."}}' for c in due) + '}.')
    return text, [c['id'] for c in due]


def LABEL_EXP(e):
    return {'AllInTrading': 'High risk: trading', 'AllInSports': 'High risk: sports'}.get(e, e)


def store(state, model, reply, asked, at):
    """After the check-in: save each reflection; an asked ID with no usable answer is saved as missing (shown plainly)."""
    lb = state.setdefault('lookbacks', {})
    got = reply if isinstance(reply, dict) else {}
    n = 0
    for i in asked:
        r = got.get(i) if isinstance(got.get(i), dict) else {}
        v, txt = verdict(r.get('verdict')), _clip_words(r.get('text'))
        if v and txt:
            lb[i] = {'at': at, 'model': model, 'verdict': v, 'text': txt}; n += 1
        elif i not in lb:
            lb[i] = {'at': at, 'model': model, 'missing': True}
    return n


def public(state, now=None):
    """{ID: reflection} for the site: everyone's, plus Claude's misses (a completed move of Claude's with no reflection 3 hours on)."""
    out = {k: dict(v) for k, v in state.get('lookbacks', {}).items()}
    for x in _j(CLAUDE_FILE, []):
        if x.get('id'):
            out[x['id']] = {'at': x['at'], 'model': 'claude', 'verdict': x['verdict'], 'text': x['text']}
    now = now or datetime.now(timezone.utc)
    for c in closings('claude', state):
        if c['id'] and c['id'] not in out and (now - datetime.fromisoformat(TX.utc(c['at']).replace('Z', '+00:00'))).total_seconds() > 3 * 3600:
            out[c['id']] = {'at': TX.utc(c['at']), 'model': 'claude', 'missing': True}
    return out


if __name__ == '__main__':
    st = _j(os.path.join(TX.SRC, 'rivals.json'), {})
    if len(sys.argv) > 1 and sys.argv[1] == 'due':
        done = done_ids(st)
        due = [c for c in closings('claude', st) if c['id'] not in done]
        if not due:
            print('Nothing due: no completed Claude move is waiting for a reflection.')
        for c in due:
            print(f"{c['id'] or '(ID pending: wait for the next race-runner run)'} | {LABEL_EXP(c['exp'])} | {c['what']} | {c['result']} | reasons then: "
                  + (' / '.join(c['reasons']) or '(none recorded)'))
        if due:
            print('\nFor each ID: python3 ops/lookback.py add ID "' + '|'.join(VERDICTS) + '" "at most 40 words: what went right or wrong, one lesson"')
    elif len(sys.argv) == 5 and sys.argv[1] == 'add':
        i, v, txt = sys.argv[2].strip().upper(), verdict(sys.argv[3]), _clip_words(sys.argv[4])
        if not re.match(r'^C-[A-Z]{3}-\d{3,}$', i) or not v or not txt:
            sys.exit('usage: add C-XXX-000 "' + '|'.join(VERDICTS) + '" "text" (a Claude ID, a listed verdict, some text)')
        if i in done_ids(st):
            sys.exit(f'{i} already has a reflection (they are never rewritten)')
        L = _j(CLAUDE_FILE, [])
        L.append({'id': i, 'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'verdict': v, 'text': txt})
        json.dump(L, open(CLAUDE_FILE, 'w'), indent=1, ensure_ascii=False)
        print(f'saved {i}: {v}: {txt}')
    else:
        print(__doc__)
