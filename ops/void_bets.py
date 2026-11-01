"""One-off (Oct 28, 5:15 p.m. ET): the organiser cancels Gemini's and ChatGPT's open main-race Sports bets before any game started,
refunds every stake, and asks them to bet again under the new daily limit. High risk bets are not touched. Archived in ops/archive/."""
import json, os
from datetime import datetime, timezone

P = 'ops/src/rivals.json'
s = json.load(open(P))
os.makedirs('ops/archive', exist_ok=True)
json.dump(s, open('ops/archive/rivals_before_void_2026-10-28.json', 'w'))
now = datetime.now(timezone.utc)
at = now.strftime('%Y-%m-%dT%H:%M:%SZ')
WHY = ('Cancelled by the organiser before the game started and the stake refunded in full: too much was riding on one night, '
       'so every AI was asked to bet again under the new daily limit (at most 25% of the bankroll on one day\'s games). Does not count toward the weekly minimum.')
NOTE = ('At 5:15 p.m. ET on Oct 28 the organiser cancelled all your open main-race Sports bets before any game started and refunded every dollar; '
        'they no longer count toward the weekly minimum. Too much was riding on a single night. NEW RULE from now on, for every AI: at most 25% of the Sports bankroll '
        'can ride on the games of any one day, and at most 25% of the Prediction markets balance can be bought in one day. Please decide your Sports bets again now, '
        'sized as if this were your own real money: each bet only needs the C$3,000 minimum, the weekly minimum is C$25,000 (about C$3,500 a day), and you do not have '
        'to bet tonight at all if you see no value. Your High risk bets are not affected.')
n = 0
for mid, m in s['models'].items():
    b = m['books'].get('Sports')
    if not b:
        continue
    ids = set()
    for x in b.get('bets', []):
        if x['status'] == 'Open' and datetime.fromisoformat(x['starts_at'].replace('Z', '+00:00')) > now:
            x.update(status='Void', result=0.0, settled_at=at, final='cancelled by the organiser before the start, stake refunded')
            ids.add(x['id'])
            s['trades'].append({'at': at, 'model': mid, 'experiment': 'Sports', 'action': 'Void', 'symbol': x['id'], 'outcome': None,
                                'name': f"{x['short']}: {x['pick_team']}", 'price': x['odds'], 'pcur': 'CAD', 'qty': 1,
                                'amount': 0.0, 'cur': 'CAD', 'fx': None, 'reason': WHY, 'bet': x['id']})
            n += 1
    for t in s['trades']:
        if t.get('model') == mid and t.get('experiment') == 'Sports' and t.get('action') == 'Bet' and t.get('bet') in ids:
            t['void'] = True
    if ids:
        s.setdefault('notices', {})[mid] = NOTE
json.dump(s, open(P, 'w'), indent=1)
print('voided', n)
