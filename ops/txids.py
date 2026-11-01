"""Public transaction IDs (owner's idea; Claude, Gemini and ChatGPT all agreed, Oct 30: ops/review/txid-oct30.json).

Every move since the Oct 28 restart gets a short ID that never changes and is never reused:
  AI letter + race code + number in that AI's race, e.g. G-MET-007 (Gemini's 7th move in Metals).
  AI: C = Claude, G = Gemini, X = ChatGPT. Races: see RACE below (AIT / AIS = High risk trading / sports).
A move is one record: a buy, sell, short, cover, bet, or a bet's result (won, lost, void, push), an option settling or expiring.

ONE writer: rivals.py calls assign() at every run (the race runner), so two runs can never hand out the same number.
The registry lives in rivals.json: "txids" {move key: ID} and "txseq" {prefix: last number}. A number, once given, is
never changed or reused; a voided move keeps its ID. Moves made since the last run show "ID pending" until the next run.
build_site.py only reads the registry (lookup) and puts each move's ID on its record in data.json.
"""
from datetime import datetime, timezone
import json
import os

AI = {'claude': 'C', 'gemini': 'G', 'chatgpt': 'X'}
RACE = {'Stocks': 'STK', 'Crypto': 'CRY', 'China': 'CHN', 'Metals': 'MET', 'Energy': 'ENE', 'Options': 'OPT', 'Currencies': 'CUR',
        'Safe': 'SAF', 'Sports': 'SPT', 'Predictions': 'PRD', 'AllInTrading': 'AIT', 'AllInSports': 'AIS'}
RESTART = '2026-10-28T17:45:00Z'   # Oct 28, 1:45 p.m. ET: everything before it was the tuning run (kept, never counted, no ID)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')   # works from any folder


def utc(s):
    """Any ISO time to 'YYYY-MM-DDTHH:MM:SSZ' (the key's form)."""
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def key(model, exp, at, action, sym):
    return f"{model}|{exp}|{utc(at)}|{action}|{sym}"


def _j(name):
    try:
        return json.load(open(os.path.join(SRC, name)))
    except Exception:
        return []


def claude_trade_key(t):
    return key('claude', t['portfolio'], t['at'], t['action'], t.get('holding', ''))


def claude_bet_keys(b):
    """(the bet's key, its result's key or None)"""
    placed = b.get('placed_at') or (b.get('placed', '') + 'T12:00:00-04:00')
    k1 = key('claude', 'Sports', placed, 'Bet', b['bet'])
    k2 = None
    if b.get('status') and b['status'] != 'Open':
        settled = b.get('settled_at') or placed
        k2 = key('claude', 'Sports', settled, b['status'], b['bet'])
    return k1, k2


def rival_key(t):
    return key(t['model'], t['experiment'], t['at'], t['action'], t.get('symbol', ''))


def moves(state):
    """Every move that gets an ID, oldest first: (time, key, model, race)."""
    out = []
    for t in state.get('trades', []):   # Gemini's and ChatGPT's moves, and every AI's High risk moves
        if t.get('model') in AI and t.get('experiment') in RACE:
            out.append((utc(t['at']), rival_key(t), t['model'], t['experiment']))
    for t in _j('trades.json'):   # Claude's ten races
        if str(t.get('holding', '')).startswith('[') or t.get('portfolio') not in RACE:
            continue
        out.append((utc(t['at']), claude_trade_key(t), 'claude', t['portfolio']))
    for b in _j('bets.json'):
        k1, k2 = claude_bet_keys(b)
        out.append((k1.split('|')[2], k1, 'claude', 'Sports'))
        if k2:
            out.append((k2.split('|')[2], k2, 'claude', 'Sports'))
    out = [m for m in out if m[0] >= RESTART]
    order = {'Buy': 0, 'Short': 0, 'Bet': 0, 'Parlay': 0}
    return sorted(out, key=lambda m: (m[0], m[2], m[3], order.get(m[1].split('|')[3], 1), m[1]))


def assign(state):
    """rivals.py, every run: give the next number to every move that has none yet. Never changes a given ID."""
    reg = state.setdefault('txids', {})
    seq = state.setdefault('txseq', {})
    new = 0
    for _, k, model, race in moves(state):
        if k in reg:
            continue
        p = AI[model] + '-' + RACE[race]
        seq[p] = seq.get(p, 0) + 1
        reg[k] = f"{p}-{seq[p]:03d}"
        new += 1
    return new


def check(state):
    """Every ID unique, every number used once per prefix (both rivals asked for this check before publishing)."""
    reg = state.get('txids', {})
    ids = list(reg.values())
    dup = {i for i in ids if ids.count(i) > 1}
    bad = []
    for p, n in state.get('txseq', {}).items():
        have = sorted(int(i.rsplit('-', 1)[1]) for i in ids if i.startswith(p + '-'))
        if have != list(range(1, n + 1)):
            bad.append(p)
    return dup, bad


if __name__ == '__main__':
    st = json.load(open(os.path.join(SRC, 'rivals.json')))
    before = len(st.get('txids', {}))
    n = assign(st)
    dup, bad = check(st)
    print(f'{before} IDs before, {n} new, {len(st["txids"])} now; duplicates: {sorted(dup) or "none"}; gaps: {bad or "none"}')
