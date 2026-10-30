"""Big moments for Instagram stories (owner, Oct 30): found only in the race's own data, so every one is a checked fact.
  - a swing: an AI's value in one race moved 5% or more in the last 24 hours (once per AI, race and day);
  - a big bet: settled in the last 6 hours with C$10,000 or more staked, or C$5,000 or more won or lost;
"""
import json
from datetime import timedelta

import racecard

NAME = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}


def _t(s):
    from datetime import datetime, timezone
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def find(now, data, src='ops/src'):
    out = []
    ser = racecard._series(src)
    for (mid, e), pts in ser.items():   # swings
        if mid not in NAME or e not in racecard.ORDER or e in ('Sports', 'Predictions'):   # betting values jump when stakes go out; big bets are covered below
            continue
        old = [v for t, v in pts if t <= now - timedelta(hours=24)]
        new = [v for t, v in pts if t <= now]
        if not old or not new or old[-1] <= 0:
            continue
        ch = new[-1] / old[-1] - 1
        if abs(ch) >= 0.05:
            out.append({'id': f'swing-{e}-{mid}-{now.date().isoformat()}', 'type': 'swing', 'who': mid, 'race': e, 'pct': ch,
                        'amount': new[-1] - old[-1], 'cur': 'USD' if e == 'China' else 'CAD'})
    bets = []   # big bets, every AI
    for mid, m in (json.load(open(f'{src}/rivals.json')).get('models') or {}).items():
        for b in ((m.get('books') or {}).get('Sports') or {}).get('bets', []):
            if b.get('status') in ('Won', 'Lost') and b.get('settled_at'):
                bets.append((mid, b.get('bet') or b.get('id') or str(b.get('settled_at'))[:16], b.get('pick_team') or b.get('pick'), b.get('event'), float(b.get('stake') or 0), float(b.get('result') or 0), b['status'], b['settled_at']))
    for b in json.load(open(f'{src}/bets.json')):
        if b.get('status') in ('Won', 'Lost') and b.get('settled_at'):
            bets.append(('claude', b.get('bet'), b.get('pick'), b.get('event'), float(b.get('stake_cad') or 0), float(b.get('result_cad') or 0), b['status'], b['settled_at']))
    for mid, bid, pick, ev, stake, res, st, at in bets:
        if now - _t(at) <= timedelta(hours=6) and (stake >= 10000 or abs(res) >= 5000):
            out.append({'id': f'bet-{mid}-{bid}', 'type': 'bet', 'who': mid, 'race': 'Sports', 'pick': str(pick).replace(' moneyline', ''), 'event': ev,
                        'stake': stake, 'amount': res, 'won': st == 'Won', 'cur': 'CAD'})
    return out
