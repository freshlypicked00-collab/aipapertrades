"""Arithmetic and consistency check for the Paper Trades data.

Usage: python3 ops/check.py ops/src
Prints every problem found (exit code 1) or "OK" (exit code 0). Read-only.
"""
import json, os, sys
from datetime import datetime

SRC = sys.argv[1]
L = lambda n: json.load(open(os.path.join(SRC, n + '.json')))
H, hist, bets, trades, ledger, fx = L('holdings'), L('history'), L('bets'), L('trades'), L('ledger'), L('fx')
START = 100000.0
MARGIN = {'Currencies'}
problems = []
usdcad, usdcny = fx.get('usdcad'), fx.get('usdcny')

for r in H:
    h, pf = r['holding'], r['portfolio']
    if r.get('currency') == 'CNY':
        exp = r['quantity'] / usdcny if h == 'Cash (CNY)' else r['quantity'] * r['price_local'] / usdcny
        if abs(exp - r['value_usd']) > max(1, abs(exp) * 1e-4):
            problems.append(f'{pf} {h}: value_usd {r["value_usd"]} but quantity x price / USDCNY = {exp:.2f}')
        if h != 'Cash (CNY)' and r['quantity'] % 100:
            problems.append(f'{pf} {h}: {r["quantity"]} shares is not a whole lot of 100')
        if h == 'Cash (CNY)' and r['quantity'] < -0.01:
            problems.append(f'{pf}: negative yuan cash')
        continue
    if h == 'Cash (CAD)':
        exp = r['quantity']
        if r['quantity'] < -0.01 and pf not in MARGIN:
            problems.append(f'{pf}: negative cash {r["quantity"]} (only {sorted(MARGIN)} may borrow)')
    elif h == 'USDC':
        exp = r['quantity'] * usdcad
    else:
        if r.get('price_usd') is None:
            problems.append(f'{pf} {h}: no price'); continue
        exp = r['quantity'] * r['price_usd'] * usdcad
        if r['quantity'] < 0 and pf not in MARGIN:
            problems.append(f'{pf} {h}: negative quantity (short) outside a margin experiment')
        if pf == 'Predictions' and not (0 <= r['price_usd'] <= 1):
            problems.append(f'{pf} {h}: prediction price {r["price_usd"]} outside 0..1')
    if abs(exp - r['value_cad']) > max(1, abs(exp) * 1e-4):
        problems.append(f'{pf} {h}: value_cad {r["value_cad"]} but expected {exp:.2f} at USD/CAD {usdcad}')

# latest history total per portfolio vs holdings
latest = {}
for e in hist:
    _t = lambda x: datetime.fromisoformat(x['at'].replace('Z', '+00:00'))
    if e['portfolio'] not in latest or _t(e) >= _t(latest[e['portfolio']]):
        latest[e['portfolio']] = e
for pf, e in latest.items():
    if pf == 'Sports':
        exp = START + sum(b['result_cad'] or 0 for b in bets if b['status'] != 'Open')
    elif pf == 'China':
        exp = sum(r['value_usd'] for r in H if r['portfolio'] == pf)
    else:
        exp = sum(r['value_cad'] for r in H if r['portfolio'] == pf)
    if abs(exp - e['value']) > 2:
        problems.append(f'{pf}: latest history value {e["value"]} but holdings add up to {exp:.2f}')

for b in bets:
    if b['status'] == 'Won' and abs(b['result_cad'] - b['to_win_cad']) > 0.01:
        problems.append(f'Bet {b["bet"]}: won but result {b["result_cad"]} != to_win {b["to_win_cad"]}')
    if b['status'] == 'Lost' and abs(b['result_cad'] + b['stake_cad']) > 0.01:
        problems.append(f'Bet {b["bet"]}: lost but result {b["result_cad"]} != -stake')
    o = float(b['odds'])
    tw = b['stake_cad'] * (o / 100 if o > 0 else 100 / abs(o))
    if abs(tw - b['to_win_cad']) > 0.02:
        problems.append(f'Bet {b["bet"]}: to_win {b["to_win_cad"]} but odds {b["odds"]} give {tw:.2f}')
    if b['status'] == 'Open' and b.get('starts_at') and datetime.fromisoformat(b['starts_at']).timestamp() < datetime.now().timestamp() - 12 * 3600:
        problems.append(f'Bet {b["bet"]}: still open 12+ hours after its start time')

for r in ledger:
    if r['portfolio'] != 'All' and r.get('open') is not None and abs(r['close'] - r['open'] - r['pnl']) > 0.02:
        problems.append(f'Ledger {r["day"]} {r["portfolio"]}: pnl {r["pnl"]} != close - open')

ids = [t.get('at', '') + t['portfolio'] + t['holding'] + t['action'] for t in trades]
if len(ids) != len(set(ids)):
    problems.append('trades.json has duplicate trades (same time, portfolio, holding, action)')

if problems:
    print('PROBLEMS:')
    for p in problems:
        print(' -', p)
    sys.exit(1)
print('OK: holdings, history totals, bets and ledger are consistent.')
