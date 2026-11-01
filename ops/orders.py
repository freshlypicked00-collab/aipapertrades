"""Claude's orders in the ten main experiments (option B, from Oct 29, 2026): filled by the race runner at the same feed prices
and with the same code as Gemini's and ChatGPT's orders. Claude never records its own fill prices.

  python3 ops/orders.py queue '{"experiment": "Stocks", "action": "buy", "symbol": "SPY", "amount": 20000, "reason": "...", "wrong_if": "... a measurable condition ...", "p_works": 0.6, "wrong_lvl": {"symbol": "SPY", "below": 735}}'
  python3 ops/orders.py queue '{"experiment": "Crypto", "action": "sell", "symbol": "Bitcoin", "fraction": 0.5, "reason": "..."}'
  python3 ops/orders.py queue '{"experiment": "China", "action": "buy", "symbol": "510300", "amount": 20000, "reason": "..."}'   (US$)
  python3 ops/orders.py queue '{"experiment": "Currencies", "action": "short", "symbol": "USD", "amount": 30000, "reason": "..."}'
  python3 ops/orders.py queue '{"experiment": "Options", "action": "buy", "symbol": "SPY261120P00700000", "contracts": 5, "reason": "..."}'
  python3 ops/orders.py queue '{"experiment": "Predictions", "action": "buy", "symbol": "<market slug>", "outcome": "Yes", "amount": 3000, "reason": "..."}'
  python3 ops/orders.py queue '{"experiment": "Sports", "action": "bet", "game": "<ESPN id>", "pick": "home", "amount": 3000, "reason": "...", "wrong_if": "..."}'
  python3 ops/orders.py queue '{"experiment": "Sports", "action": "bet", "team": "Boston Celtics", "amount": 3000, "reason": "...", "wrong_if": "..."}'   (by team)
  python3 ops/orders.py games [filter]   (the games open for betting with ids and moneylines, as of the last run: the list the rivals get)
  python3 ops/orders.py queue '{"experiment": "Sports", "action": "parlay", "legs": [{"game": "...", "pick": "away"}, ...], "amount": 3000, "reason": "..."}'
  python3 ops/orders.py queue '{"experiment": "Crypto", "action": "stop", "symbol": "Bitcoin", "level": 75500, "fraction": 1, "reason": "..."}'
  python3 ops/orders.py queue '{"experiment": "Crypto", "action": "target", "symbol": "Bitcoin", "level": 92000, "fraction": 0.5, "reason": "..."}'
  python3 ops/orders.py queue '{"action": "cancel_stop", "stop": "claude-3"}'
  python3 ops/orders.py status
Symbols: the holding's name as shown on the site (Bitcoin, Gold, CSI 300 ETF, Japanese yen, SPY) or the feed symbol (BTC-USD,
GC=F, 510300, JPY, an OCC option symbol, a Polymarket market slug). Amounts are in the experiment's currency (China in US$).
Then commit and push ops/src/claude_orders.json and dispatch the runner ONLY to fill (no extra rival check-in):
  gh api -X POST repos/freshlypicked00-collab/aipapertrades/actions/workflows/rivals.yml/dispatches -f ref=main -f 'inputs[mode]=fill'
The fills land in ops/src (holdings, trades, bets, log) within a few minutes: `git pull` and `python3 ops/orders.py status`.
"""
import json
import sys
from datetime import datetime, timezone

Q = 'ops/src/claude_orders.json'
ST = 'ops/src/rivals.json'
EXPS = ('Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions')
ACTIONS = ('buy', 'sell', 'short', 'cover', 'bet', 'parlay', 'stop', 'target', 'cancel_stop')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'games':
        from zoneinfo import ZoneInfo
        go = (json.load(open(ST)).get('games_open') or {})
        f = ' '.join(sys.argv[2:]).lower()
        print(f"Games open for betting as of {go.get('at', '(no list yet: the next run saves it)')} (id: league, away @ home, start ET, moneylines away / home).")
        print('The odds that count are the ones at the moment the race runner fills the bet; this list can be up to an hour old.')
        for g in go.get('games', []):
            st = datetime.fromisoformat(g['start'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/New_York')).strftime('%a %b %-d %-I:%M %p')
            line = f"  {g['id']}: {g['short']}, {g['away']} @ {g['home']}, {st}, {g['away_ml']:+d} / {g['home_ml']:+d}"
            if f in line.lower():
                print(line)
        sys.exit(0)
    try:
        q = json.load(open(Q))
    except FileNotFoundError:
        q = []
    if cmd == 'queue':
        o = json.loads(sys.argv[2])
        act = str(o.get('action', '')).lower()
        if act not in ACTIONS:
            sys.exit('action must be one of ' + ', '.join(ACTIONS))
        if act != 'cancel_stop' and o.get('experiment') not in EXPS:
            sys.exit('experiment must be one of ' + ', '.join(EXPS) + ' (High risk orders go through ops/allin.py)')
        if act == 'bet' and not ((o.get('game') and o.get('pick') in ('home', 'away')) or o.get('team')):
            sys.exit('a bet needs "game" (ESPN id) and "pick" ("home" or "away"), or "team"; see `python3 ops/orders.py games`')
        if act in ('buy', 'short', 'bet', 'parlay') and not (o.get('amount') or o.get('contracts')):
            sys.exit('a buy, short or bet needs "amount" (or "contracts" for options)')
        if act in ('buy', 'short', 'bet', 'parlay', 'sell', 'cover') and not str(o.get('reason', '')).strip():
            sys.exit('every order needs a "reason" in Claude\'s own words (and "wrong_if" for buys, shorts and bets)')
        if act in ('stop', 'target') and o.get('level') in (None, ''):
            sys.exit('a stop or target needs "level"')
        o['action'] = act
        o['id'] = 'c' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + f'-{len(q)}'
        o['queued_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        q.append(o)
        json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
        print('queued', o['id'])
    st = json.load(open(ST))
    cm = st.get('claude_main') or {}
    done = set(cm.get('done', []))
    print('pending:', [o['id'] for o in q if o['id'] not in done] or 'none')
    for k, v in (cm.get('waiting') or {}).items():
        if k not in done:
            print('  ', k, v)
    print('stops and targets:')
    for s in (st.get('stops') or {}).get('claude', []):
        print(f"   {s['id']}: {s['kind']} {s['experiment']} {s.get('name')} {s['direction']} {s['level']:g} ({s['fraction']:.0%})")
    for r in cm.get('results', [])[-15:]:
        print('result:', r)
