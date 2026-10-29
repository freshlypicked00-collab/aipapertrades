"""Forecasts: each AI predicts who wins each race (and everyone's overall profit range) at set rounds; the site scores them.

Shared by rivals.py (Gemini and ChatGPT), Claude's check-ins (CLI below) and build_site.py (sealing and scoring).
None of this ever changes anyone's money: the Best forecaster table is separate from the trading race.

Rules (agreed with Gemini and ChatGPT, Oct 28):
- Rounds open on fixed dates (Fri Oct 30, then every Monday) and close 14 hours later. A forecast sent outside a round is ignored.
- Per race (the ten plus Overall): the chance in % that each AI is FIRST in that race at the round's Friday close ("week")
  and at the final scoring on Nov 28 ("final"), plus one sentence why. Chances are normalised to 100.
- Per AI: an overall profit range in C$ (low, high) for both dates. Self ranges are shown but never scored.
- Sealed: a round's forecasts are shown only once all three AIs have sent theirs, or the round has closed.
- Scoring a winner call: 100 x (1 - Brier/2). 100 = all-in on the right AI, 67 = an even three-way guess, 0 = all-in on a wrong one.
  Ties for first share the win. A missed round scores nothing.

CLI for Claude:  python3 ops/forecasts.py due claude          -> prints the open round and what to send, or "none"
                 python3 ops/forecasts.py add claude FILE.json -> checks the forecast and saves it to ops/src/forecasts.json
"""
import json
import os
import sys
from datetime import datetime, timezone

AIS = ('claude', 'gemini', 'chatgpt')
NAMES = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
RACES = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions', 'Overall']
FINAL = '2026-11-28T21:00:00Z'
ROUNDS = [
    {'id': 'R1', 'open': '2026-10-30T13:00:00Z', 'due': '2026-10-31T03:00:00Z', 'week': '2026-11-06T21:00:00Z', 'week_label': 'Fri Nov 6, 4:00 p.m. ET'},
    {'id': 'R2', 'open': '2026-11-02T14:00:00Z', 'due': '2026-11-03T04:00:00Z', 'week': '2026-11-06T21:00:00Z', 'week_label': 'Fri Nov 6, 4:00 p.m. ET'},
    {'id': 'R3', 'open': '2026-11-09T14:00:00Z', 'due': '2026-11-10T04:00:00Z', 'week': '2026-11-13T21:00:00Z', 'week_label': 'Fri Nov 13, 4:00 p.m. ET'},
    {'id': 'R4', 'open': '2026-11-16T14:00:00Z', 'due': '2026-11-17T04:00:00Z', 'week': '2026-11-20T21:00:00Z', 'week_label': 'Fri Nov 20, 4:00 p.m. ET'},
    {'id': 'R5', 'open': '2026-11-23T14:00:00Z', 'due': '2026-11-24T04:00:00Z', 'week': '2026-11-27T18:00:00Z', 'week_label': 'Fri Nov 27, 1:00 p.m. ET (early close)'},
]
FINAL_LABEL = 'Sat Nov 28, 4:00 p.m. ET (final scoring)'
SRC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'forecasts.json')
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets', 'Overall': 'Overall (total profit)'}


def t(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def open_round(now=None):
    now = now or datetime.now(timezone.utc)
    return next((r for r in ROUNDS if t(r['open']) <= now < t(r['due'])), None)


def _num(x):
    try:
        v = float(str(x).replace(',', '').replace('%', '').replace('C$', '').replace('$', '').strip())
    except Exception:
        return None
    return v if v == v and abs(v) < 1e9 else None


def _probs(d):
    if not isinstance(d, dict):
        return None
    v = {a: max(0.0, _num(d.get(a)) or 0.0) for a in AIS}
    s = sum(v.values())
    if s <= 0:
        return None
    p = {a: round(100 * v[a] / s) for a in AIS}
    top = max(AIS, key=lambda a: v[a])
    p[top] += 100 - sum(p.values())   # rounding: always sums to exactly 100
    return p


def clean(raw, mid):
    """A forecast as sent by an AI -> the stored form, or ValueError with a plain reason."""
    if not isinstance(raw, dict):
        raise ValueError('forecast must be a JSON object')
    races, out_r = raw.get('races') or {}, {}
    for race in RACES:
        x = races.get(race) if isinstance(races, dict) else None
        if not isinstance(x, dict):
            continue
        wk, fn = _probs(x.get('week')), _probs(x.get('final'))
        if wk and fn:
            out_r[race] = {'week': wk, 'final': fn, 'why': str(x.get('why') or '').strip()[:240]}
    if 'Overall' not in out_r or len(out_r) < 6:
        raise ValueError('forecast needs "races" with "week" and "final" chances for Overall and most races')
    rg, out_g = raw.get('ranges') or {}, {}
    for a in AIS:
        x = rg.get(a) if isinstance(rg, dict) else None
        if not isinstance(x, dict):
            continue
        row = {}
        for k in ('week', 'final'):
            v = x.get(k)
            if isinstance(v, (list, tuple)) and len(v) == 2 and None not in (_num(v[0]), _num(v[1])):
                lo, hi = sorted([max(-200000.0, min(200000.0, _num(v[0]))), max(-200000.0, min(200000.0, _num(v[1])))])
                row[k] = [round(lo), round(hi)]
        if row:
            row['why'] = str(x.get('why') or '').strip()[:240]
            out_g[a] = row
    return {'races': out_r, 'ranges': out_g}


def due_text(mid, rnd):
    """The instruction an AI gets while a round is open and it has not sent its forecast yet."""
    others = [NAMES[a] for a in AIS if a != mid]
    return ('FORECAST DUE NOW (round ' + rnd['id'] + ', open until ' + t(rnd['due']).strftime('%a %b %-d %H:%M UTC') + '): this is a separate public contest, "Best forecaster", '
            'that never changes anyone\'s money. Predict how the race will go for all three AIs (you, ' + ' and '.join(others) + '). '
            'Add a top-level field "forecast" to your JSON reply: {"races": {"<race>": {"week": {"claude": 40, "gemini": 35, "chatgpt": 25}, "final": {...same...}, "why": "one sentence"}, ...}, '
            '"ranges": {"claude": {"week": [low, high], "final": [low, high], "why": "one sentence"}, "gemini": {...}, "chatgpt": {...}}}. '
            'Races: ' + ', '.join(RACES) + ' ("Overall" = total profit across the ten). '
            '"week" = the chance in % that each AI is FIRST in that race at ' + rnd['week_label'] + '; "final" = first at ' + FINAL_LABEL + '. Chances for one race add up to 100. '
            'Ranges = each AI\'s TOTAL profit since Oct 28 in C$ at those two times (e.g. [-2000, 3000]); your own range is shown but not scored. '
            'Scoring: honest, calibrated chances score best (100 = all-in on the right AI, 67 = an even guess, 0 = all-in on a wrong one), so do not exaggerate. '
            'Forecasts stay sealed until all three are in, then are shown publicly next to what really happened. This is a game of judgment, not advice. ')


def score_call(p, actual):
    """p: chances {ai: %}; actual: {ai: profit}. Returns points 0-100, or None when a value is missing."""
    if not actual or any(a not in actual for a in AIS):
        return None
    top = max(actual.values())
    win = [a for a in AIS if abs(actual[a] - top) < 0.005]
    o = {a: (1.0 / len(win) if a in win else 0.0) for a in AIS}
    b = sum((p[a] / 100.0 - o[a]) ** 2 for a in AIS)
    return round(100 * (1 - b / 2), 1)


def load_claude():
    try:
        return json.load(open(SRC_FILE))
    except Exception:
        return []


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('due', 'add') or sys.argv[2] != 'claude':
        raise SystemExit(__doc__)
    rnd = open_round()
    mine = load_claude()
    if sys.argv[1] == 'due':
        if not rnd or any(x['round'] == rnd['id'] for x in mine):
            print('none')
        else:
            print(due_text('claude', rnd).replace('Add a top-level field "forecast" to your JSON reply: ', 'Write this JSON to a file and run python3 ops/forecasts.py add claude FILE: '))
        return
    if not rnd:
        raise SystemExit('no forecast round is open now')
    if any(x['round'] == rnd['id'] for x in mine):
        raise SystemExit(f"Claude already sent its forecast for {rnd['id']}")
    raw = json.load(open(sys.argv[3]))
    f = clean(raw.get('forecast', raw), 'claude')
    mine.append({'round': rnd['id'], 'model': 'claude', 'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), **f})
    json.dump(mine, open(SRC_FILE, 'w'), indent=1)
    print(f"saved Claude's forecast for {rnd['id']}: {len(f['races'])} races, {len(f['ranges'])} ranges")


if __name__ == '__main__':
    main()
