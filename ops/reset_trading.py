"""One-off fresh start (Oct 28, 2026): reset Claude's eight trading experiments and Gemini's books.

Betting (Sports, Predictions) is left exactly as it is. Everything removed is first copied to
ops/archive/<stamp>/ so nothing is lost. Run once: python3 ops/reset_trading.py
"""
import json, os, shutil
from datetime import datetime, timezone

SRC = 'ops/src'
TRADING = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe']
NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)
AT = NOW.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
arch = f'ops/archive/{NOW:%Y-%m-%d-%H%M}-before-fresh-start'
os.makedirs(arch, exist_ok=True)
for f in os.listdir(SRC):
    if f.endswith('.json'):
        shutil.copy(os.path.join(SRC, f), arch)
L = lambda n: json.load(open(f'{SRC}/{n}.json'))
def S(n, d): json.dump(d, open(f'{SRC}/{n}.json', 'w'), indent=1, ensure_ascii=False)
fx = L('fx')

h = [r for r in L('holdings') if r['portfolio'] not in TRADING]
for p in TRADING:
    if p == 'China':
        h.append({'portfolio': 'China', 'holding': 'Cash (CNY)', 'currency': 'CNY', 'quantity': round(100000 * fx['usdcny'], 2), 'entry_local': None,
                  'price_local': None, 'change_pct': 0, 'value_usd': 100000.0, 'value_cad': round(100000 * fx['usdcad'], 2), 'as_of': AT,
                  'cost_usd': 100000.0, 'price_source': '', 'price_at': None})
    else:
        h.append({'portfolio': p, 'holding': 'Cash (CAD)', 'quantity': 100000.0, 'entry_usd': None, 'price_usd': None, 'change_pct': 0,
                  'value_cad': 100000.0, 'as_of': AT, 'cost_cad': 100000.0, 'price_source': '', 'price_at': None})
S('holdings', h)
S('history', [r for r in L('history') if r['portfolio'] not in TRADING] + [{'at': AT, 'portfolio': p, 'value': 100000.0, 'close': False} for p in TRADING])
S('trades', [r for r in L('trades') if r['portfolio'] not in TRADING])
S('log', [r for r in L('log') if r['portfolio'] not in TRADING and r['portfolio'] != 'All'] + [
    {'at': AT, 'portfolio': p, 'action': 'Reset', 'detail': 'Fresh start: this experiment was reset to ' + ('US$' if p == 'China' else 'C$') + '100,000 in cash so Claude and Gemini start level. First trades at the next market open. The earlier run is archived.'} for p in TRADING])
S('ledger', [r for r in L('ledger') if r['portfolio'] in ('Sports', 'Predictions')])
S('review', [r for r in L('review') if r['portfolio'] in ('Sports', 'Predictions')])
S('rules', [r for r in L('rules') if r['portfolio'] not in TRADING])
S('take', [])
ix = L('indexes')
for r in ix:
    if r['portfolio'] in TRADING:
        r['start_at'] = None
        if r.get('kind') != 'rate':
            r.update(start_level=None, fx_start=None)
S('indexes', ix)
bm = L('benchmark')
for r in bm:
    if r['portfolio'] in TRADING:
        r.update(start_at=None, btc_start_usd=None, fx_start=None)
S('benchmark', bm)
ev = [e for e in L('events') if not any(k in e['event'] + ' ' + e.get('why', '') for k in ('Key check-in', 'opening orders', 'SOXL', 'trim'))]
ev.append({'at': '2026-10-28T09:30:00-04:00', 'when': 'Wed Oct 28, 9:30 a.m.', 'event': 'Fresh start: Claude and Gemini make their opening investments',
           'affects': ', '.join(TRADING), 'why': 'Every trading experiment restarts from 100,000 in cash at the US open, so both AIs start level. China stocks start at the Shanghai open (9:30 p.m. ET).'})
ev.sort(key=lambda e: e['at'])
S('events', ev)
rv = 'ops/src/rivals.json'
if os.path.exists(rv):
    r = json.load(open(rv))
    json.dump({'models': {}, 'trades': [], 'history': [], 'takes': [], 'thoughts': [], 'reviews': [], 'fx': r.get('fx')}, open(rv, 'w'), indent=1)
print('reset at', AT, '; archive in', arch)
