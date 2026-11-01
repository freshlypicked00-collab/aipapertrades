"""Claude's "High risk" side-race (High risk, high reward), filled by the same GitHub job and price sources as Gemini and ChatGPT.

Claude queues orders here; ops/rivals.py fills them at its next run (no caps in High risk), values the books,
and posts them to Telegram. State: ops/src/rivals.json "claude_allin". Queue: ops/src/allin_orders.json.

  python3 ops/allin.py queue '{"experiment": "AllInTrading", "action": "buy", "symbol": "TSLA", "amount": 50000, "reason": "..."}'
  python3 ops/allin.py queue '{"experiment": "AllInSports", "action": "bet", "game": "401909886", "pick": "home", "amount": 20000, "reason": "..."}'
  python3 ops/allin.py status
Then commit, push, and dispatch the rivals workflow (mode run) so the orders fill now.
"""
import json, sys
from datetime import datetime, timezone

Q = 'ops/src/allin_orders.json'
ST = 'ops/src/rivals.json'

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    try:
        q = json.load(open(Q))
    except FileNotFoundError:
        q = []
    if cmd == 'queue':
        o = json.loads(sys.argv[2])
        if o.get('experiment') not in ('AllInTrading', 'AllInSports'):
            sys.exit('experiment must be AllInTrading or AllInSports')
        o['id'] = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + f'-{len(q)}'
        o['queued_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        q.append(o)
        json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
        print('queued', o['id'])
    st = json.load(open(ST))
    c = st.get('claude_allin') or {}
    done = set(c.get('done', []))
    print('pending:', [o['id'] for o in q if o['id'] not in done])
    for e, b in (c.get('books') or {}).items():
        print(e, 'cash', round(b['cash']), 'positions', list(b['positions']), 'open bets', [x['pick_team'] for x in b.get('bets', []) if x['status'] == 'Open'], 'BUSTED' if b.get('busted') else '')
    for r in c.get('results', [])[-10:]:
        print('result:', r)
