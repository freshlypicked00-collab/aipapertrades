"""One-off restart (Oct 28, 2026, 1:45 p.m. ET): every AI, every experiment back to 100,000.

The morning (9:30 a.m. to 1:45 p.m. ET) was a tuning run: the AIs had been told "high risk, high reward"
and several went all-in. Its results go into the ledger as a tuning run that does not count, and
everything is archived first. Run once: python3 ops/reset_all.py
"""
import json, os, shutil
from datetime import datetime, timezone

SRC = 'ops/src'
ALL = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
RS = '2026-10-28T17:45:00Z'
FS = '2026-10-28T13:30:00Z'
NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)
AT = NOW.isoformat().replace('+00:00', 'Z')
TAG = 'Tuning run, Oct 28 9:30 a.m.–1:45 p.m. ET (does not count): '
T = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
arch = f'ops/archive/{NOW:%Y-%m-%d-%H%M}-tuning-run'
os.makedirs(arch, exist_ok=True)
for f in os.listdir(SRC):
    if f.endswith('.json'):
        shutil.copy(os.path.join(SRC, f), arch)
L = lambda n: json.load(open(f'{SRC}/{n}.json'))
def S(n, d): json.dump(d, open(f'{SRC}/{n}.json', 'w'), indent=1, ensure_ascii=False)
fx = L('fx')

# ---- Claude
hist = sorted(L('history'), key=lambda h: T(h['at']))
last = {}
for h in hist:
    last[h['portfolio']] = float(h['value'])
trades = L('trades')
ledger = [r for r in L('ledger') if not (r['day'] == '2026-10-27' and r['portfolio'] in ALL)]
old27 = {r['portfolio']: r for r in L('ledger') if r['day'] == '2026-10-27'}
for p in ALL:
    close = last.get(p, 100000.0)
    moves = [t for t in trades if t['portfolio'] == p and T(t['at']) >= T(FS)]
    what = '; '.join(f"{t['action']} {t['holding'].replace('[Pre-race] ', '')}" for t in moves[:6]) or 'no trades'
    note = TAG + f"ended at {('US$' if p == 'China' else 'C$')}{close:,.0f} ({close / 1000 - 100:+.1f}%). Moves: {what}."
    if p in old27:
        note += ' Earlier simulation before the race (Oct 27–28 bets): ' + old27[p].get('note', '').replace('Simulation before the race started (does not count): ', '')
    ledger.append({'day': '2026-10-27', 'start_at': FS, 'end_at': RS, 'portfolio': p, 'currency': 'USD' if p == 'China' else 'CAD',
                   'open': 100000.0, 'close': close, 'pnl': round(close - 100000, 2), 'pct': close / 100000 - 1, 'note': note, 'practice': True})
S('ledger', ledger)
for t in trades:
    if not t['holding'].startswith('['):
        t['holding'] = '[Tuning run] ' + t['holding']
S('trades', trades)
lg = L('log')
for r in lg:
    if r['portfolio'] in ALL and not r['detail'].startswith(('Tuning run', 'Simulation before')):
        r['detail'] = TAG + r['detail']
lg += [{'at': RS, 'portfolio': p, 'action': 'Reset', 'detail': 'Restart: back to ' + ('US$' if p == 'China' else 'C$') + '100,000 for every AI at 1:45 p.m. ET, with the new rules (invest as if it were real money, 50% cap). The morning tuning run is in the ledger and does not count.'} for p in ALL]
S('log', lg)
rv = L('review')
for r in rv:
    if not r['text'].startswith(('Tuning run', 'Simulation before')):
        r['text'] = TAG + r['text']
S('review', rv)
h = []
for p in ALL:
    if p == 'China':
        h.append({'portfolio': 'China', 'holding': 'Cash (CNY)', 'currency': 'CNY', 'quantity': round(100000 * fx['usdcny'], 2), 'entry_local': None,
                  'price_local': None, 'change_pct': 0, 'value_usd': 100000.0, 'value_cad': round(100000 * fx['usdcad'], 2), 'as_of': RS,
                  'cost_usd': 100000.0, 'price_source': '', 'price_at': None})
    else:
        h.append({'portfolio': p, 'holding': 'Cash (CAD)', 'quantity': 100000.0, 'entry_usd': None, 'price_usd': None, 'change_pct': 0,
                  'value_cad': 100000.0, 'as_of': RS, 'cost_cad': 100000.0, 'price_source': '', 'price_at': None})
S('holdings', h)
S('history', [{'at': RS, 'portfolio': p, 'value': 100000.0, 'close': False} for p in ALL])
S('bets', [])
S('rules', [])
S('take', [])
ix = L('indexes')
for r in ix:
    r['start_at'] = None
    if r.get('kind') != 'rate':
        r.update(start_level=None, fx_start=None)
S('indexes', ix)
bm = L('benchmark')
for r in bm:
    r.update(start_at=None, btc_start_usd=None, fx_start=None)
S('benchmark', bm)
if os.path.exists(f'{SRC}/bench_history.json'):
    S('bench_history', [])

# ---- Gemini and ChatGPT
r = L('rivals')
tuning = r.get('tuning', [])
lastv = {}
for x in sorted(r.get('history', []), key=lambda x: x['at']):
    lastv[(x['model'], x['experiment'])] = float(x['value'])
for (mid, e), v in lastv.items():
    moves = [t for t in r['trades'] if t['model'] == mid and t['experiment'] == e]
    what = '; '.join(f"{t['action']} {t['name']} ({('C$' if t.get('cur') != 'USD' else 'US$')}{t['amount']:,.0f})" for t in moves[:6]) or 'no trades'
    tuning.append({'model': mid, 'experiment': e, 'open': 100000.0, 'close': v, 'start_at': FS, 'end_at': RS,
                   'note': TAG + f"ended at {('US$' if e == 'China' else 'C$')}{v:,.0f} ({v / 1000 - 100:+.1f}%). Moves: {what}."})
r.setdefault('tuning_trades', []).extend(r['trades'])
r.update(tuning=tuning, models={}, trades=[], history=[], takes=[], thoughts=[], reviews=[], bet_ids={})
S('rivals', r)
print('restart', RS, 'archive', arch)
