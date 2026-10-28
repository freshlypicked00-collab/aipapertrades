"""One-off (Oct 28, 2026): reset Claude's Sports and Predictions to a fresh C$100,000, like the other eight.

The earlier bets were a simulation before the race started. They stay visible in the ledger, log and
trades, labelled as such, but no longer count. Everything is first copied to ops/archive/.
"""
import json, os, shutil
from datetime import datetime, timezone

SRC = 'ops/src'
BET = ['Sports', 'Predictions']
TAG = 'Simulation before the race started (does not count): '
NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)
AT = NOW.isoformat().replace('+00:00', 'Z')
arch = f'ops/archive/{NOW:%Y-%m-%d-%H%M}-before-betting-reset'
os.makedirs(arch, exist_ok=True)
for f in os.listdir(SRC):
    if f.endswith('.json'):
        shutil.copy(os.path.join(SRC, f), arch)
L = lambda n: json.load(open(f'{SRC}/{n}.json'))
def S(n, d): json.dump(d, open(f'{SRC}/{n}.json', 'w'), indent=1, ensure_ascii=False)

S('holdings', [r for r in L('holdings') if r['portfolio'] not in BET] + [
    {'portfolio': p, 'holding': 'Cash (CAD)', 'quantity': 100000.0, 'entry_usd': None, 'price_usd': None, 'change_pct': 0,
     'value_cad': 100000.0, 'as_of': AT, 'cost_cad': 100000.0, 'price_source': '', 'price_at': None} for p in BET])
S('bets', [r for r in L('bets') if r.get('portfolio') not in BET and r.get('status') != 'Open'])
S('history', [r for r in L('history') if r['portfolio'] not in BET] + [{'at': AT, 'portfolio': p, 'value': 100000.0, 'close': False} for p in BET])
tr = L('trades')
for r in tr:
    if r['portfolio'] in BET and not r['holding'].startswith('[Pre-race]'):
        r['holding'] = '[Pre-race] ' + r['holding']
S('trades', tr)
lg = L('log')
for r in lg:
    if r['portfolio'] in BET and not r['detail'].startswith(TAG):
        r['detail'] = TAG + r['detail']
lg += [{'at': AT, 'portfolio': p, 'action': 'Reset', 'detail': 'Fresh start: reset to C$100,000 so Claude starts level with Gemini and ChatGPT. Earlier bets were a simulation before the race started, kept in the ledger and archived, and do not count.'} for p in BET]
S('log', lg)
ld = L('ledger')
for r in ld:
    if r['portfolio'] in BET and not r.get('note', '').startswith(TAG):
        r['note'] = TAG + r.get('note', '')
        r['practice'] = True
S('ledger', ld)
rv = L('review')
for r in rv:
    if r['portfolio'] in BET and not r['text'].startswith(TAG):
        r['text'] = TAG + r['text']
S('review', rv)
print('betting reset at', AT, '; archive in', arch)
