"""Apply one UPDATE ALL to the Paper Trades data.

Usage:
    python3 ops/update.py ops/src path/to/input.json

Reads the data files in ops/src, applies the prices, trades, bets and log
entries from the input file, recomputes every value, and writes the files
back. Prints a summary and the list of data files that changed (these are
the ones to re-upload to the private tracker).

Input file format: see ops/RUNBOOK.md, section "The input file".
"""
import json
import os
import sys
from datetime import datetime, timedelta

SRC, INP = sys.argv[1], sys.argv[2]
START = 100000.0


def load(name):
    return json.load(open(os.path.join(SRC, name + '.json')))


def save(name, data):
    json.dump(data, open(os.path.join(SRC, name + '.json'), 'w'), indent=1)
    changed.add(name)


def ts(s):
    return datetime.fromisoformat(s)


changed = set()
inp = json.load(open(INP))
AT = inp['at']
at_dt = ts(AT)
warnings = []

holdings = load('holdings')
history = load('history')
bets = load('bets')
log = load('log')
rules = load('rules')
benchmark = load('benchmark')
indexes = load('indexes')
events = load('events')
prices = load('prices')
trades = load('trades')
bench = load('bench_history')
sources = load('sources')

fx = float(inp['fx']['usdcad'])
P = inp.get('prices', {})

# ---- price provenance checks (warnings only; the runbook sets the standard)
for asset, q in P.items():
    if not q.get('source') or not q.get('at'):
        warnings.append(f'{asset}: price has no source or time')
        continue
    age = at_dt - ts(q['at'])
    if age > timedelta(minutes=90) and not q.get('market_closed'):
        warnings.append(f'{asset}: price is {age} old')
if 'at' in inp['fx'] and at_dt - ts(inp['fx']['at']) > timedelta(hours=3):
    warnings.append('USD/CAD rate is more than 3 hours old')


def row(portfolio, holding):
    for r in holdings:
        if r['portfolio'] == portfolio and r['holding'] == holding:
            return r
    return None


def to_win(stake, odds):
    odds = float(odds)
    return round(stake * odds / 100, 2) if odds > 0 else round(stake * 100 / abs(odds), 2)


# ---- trades
for t in inp.get('trades', []):
    pf, h, action, cad = t['portfolio'], t['holding'], t['action'], float(t.get('cad', 0))
    price = float(t['price'])
    fund_name = t.get('funding') or ('USDC' if pf == 'Crypto' else 'Cash (CAD)')
    fund = row(pf, fund_name)
    r = row(pf, h)
    if action == 'Buy':
        qty = cad / fx / price
        if fund is None:
            raise SystemExit(f'No funding holding {fund_name} in {pf}')
        if fund_name == 'USDC':
            fund['quantity'] = round(fund['quantity'] - cad / fx, 6)
        else:
            fund['quantity'] = round(fund['quantity'] - cad, 2)
        fund['cost_cad'] = round(fund.get('cost_cad', 0) - cad, 2)
        if fund['quantity'] < -0.01:
            raise SystemExit(f'Not enough {fund_name} in {pf} for this buy')
        if r is None:
            r = {'portfolio': pf, 'holding': h, 'quantity': 0, 'entry_usd': price, 'price_usd': price,
                 'change_pct': 0, 'value_cad': 0, 'as_of': AT, 'cost_cad': 0, 'price_source': '', 'price_at': None}
            idx = max([i for i, x in enumerate(holdings) if x['portfolio'] == pf] or [len(holdings) - 1]) + 1
            holdings.insert(idx, r)
        q0 = r['quantity']
        r['entry_usd'] = round((q0 * r['entry_usd'] + qty * price) / (q0 + qty), 6)
        r['quantity'] = round(q0 + qty, 6)
        r['cost_cad'] = round(r.get('cost_cad', 0) + cad, 2)
    elif action == 'Sell':
        if r is None:
            raise SystemExit(f'Cannot sell {h}: not held in {pf}')
        q0 = r['quantity']
        qty = q0 * float(t['fraction']) if 'fraction' in t else cad / fx / price
        qty = min(qty, q0)
        cad = qty * price * fx
        cost_out = r.get('cost_cad', 0) * qty / q0
        r['realized_cad'] = round(r.get('realized_cad', 0) + cad - cost_out, 2)
        r['cost_cad'] = round(r.get('cost_cad', 0) - cost_out, 2)
        r['quantity'] = round(q0 - qty, 6)
        dest = row(pf, t.get('to') or fund_name)
        if dest is None:
            raise SystemExit(f'No destination holding for the sale proceeds in {pf}')
        if dest['holding'] == 'USDC':
            dest['quantity'] = round(dest['quantity'] + cad / fx, 6)
            dest['cost_cad'] = round(dest.get('cost_cad', 0) + cad, 2)
        elif dest['holding'] == 'Cash (CAD)':
            dest['quantity'] = round(dest['quantity'] + cad, 2)
            dest['cost_cad'] = round(dest.get('cost_cad', 0) + cad, 2)
        else:  # rotate into another asset
            dp = float(t['to_price'])
            dq = cad / fx / dp
            dest['entry_usd'] = round((dest['quantity'] * dest['entry_usd'] + dq * dp) / (dest['quantity'] + dq), 6)
            dest['quantity'] = round(dest['quantity'] + dq, 6)
            dest['cost_cad'] = round(dest.get('cost_cad', 0) + cad, 2)
            trades.append({'at': AT, 'portfolio': pf, 'holding': dest['holding'], 'action': 'Buy', 'price_usd': dp, 'cad': round(cad, 2)})
    else:
        raise SystemExit(f'Unknown trade action {action}')
    trades.append({'at': AT, 'portfolio': pf, 'holding': h, 'action': action, 'price_usd': price, 'cad': round(cad, 2)})
    save('trades', trades)

# ---- revalue every holding
for r in holdings:
    h = r['holding']
    if h == 'Cash (CAD)':
        r['value_cad'] = round(r['quantity'], 2)
    elif h == 'USDC':
        r['value_cad'] = round(r['quantity'] * fx, 2)
    else:
        if h in P:
            q = P[h]
            r['price_usd'] = float(q['price'])
            r['price_source'] = q.get('source', '')
            r['price_at'] = q.get('at')
        r['change_pct'] = round(r['price_usd'] / r['entry_usd'] - 1, 4) if r['entry_usd'] else 0
        r['value_cad'] = round(r['quantity'] * r['price_usd'] * fx, 2)
    r['as_of'] = AT
save('holdings', holdings)

# ---- bets
by_id = {b['bet']: b for b in bets}
for b in inp.get('bets_new', []):
    stake = float(b['stake_cad'])
    nb = {'bet': b['bet'], 'placed': AT[:10], 'sport': b['sport'], 'event': b['event'], 'pick': b['pick'],
          'odds': b['odds'], 'stake_cad': stake, 'to_win_cad': to_win(stake, b['odds']), 'status': 'Open',
          'result_cad': None, 'market': b.get('market', 'moneyline'), 'line': b.get('line'),
          'closing_odds': None, 'closing_line': None, 'starts_at': b.get('starts_at')}
    if nb['bet'] in by_id:
        raise SystemExit(f'Bet id {nb["bet"]} already exists')
    bets.append(nb)
    by_id[nb['bet']] = nb
for c in inp.get('bets_closing', []):
    b = by_id[c['bet']]
    b['closing_odds'] = c.get('closing_odds')
    b['closing_line'] = c.get('closing_line')
for s in inp.get('bets_settle', []):
    b = by_id[s['bet']]
    b['status'] = s['status']
    b['result_cad'] = {'Won': b['to_win_cad'], 'Lost': -b['stake_cad'], 'Push': 0}[s['status']]
if inp.get('bets_new') or inp.get('bets_closing') or inp.get('bets_settle'):
    save('bets', bets)

# ---- totals and history
tot = {}
for pf in ('Stocks', 'Crypto', 'Metals'):
    tot[pf] = round(sum(r['value_cad'] for r in holdings if r['portfolio'] == pf), 2)
tot['Sports'] = round(START + sum(b['result_cad'] or 0 for b in bets if b['status'] != 'Open'), 2)
is_close = at_dt.weekday() < 5 and at_dt.hour == 16
for pf, v in tot.items():
    history.append({'at': AT, 'portfolio': pf, 'value': v, 'close': is_close})
save('history', history)

# ---- price history, benchmarks, indexes
for asset, q in P.items():
    prices.append({'asset': asset, 'at': q.get('at') or AT, 'price': float(q['price'])})
save('prices', prices)
if 'Bitcoin' in P:
    bench.append({'series': 'Bitcoin', 'at': P['Bitcoin'].get('at') or AT, 'level': float(P['Bitcoin']['price']), 'fx': fx, 'source': P['Bitcoin'].get('source', '')})
    for r in benchmark:
        r['btc_now_usd'] = float(P['Bitcoin']['price'])
        r['fx_now'] = fx
        r['as_of'] = AT
    save('benchmark', benchmark)
ix = inp.get('indexes', {})
if 'sp500' in ix:
    bench.append({'series': 'S&P 500', 'at': ix['sp500'].get('at') or AT, 'level': float(ix['sp500']['level']), 'fx': fx, 'source': ix['sp500'].get('source', '')})
for r in indexes:
    if r['id'] in ix:
        r['now_level'] = float(ix[r['id']]['level'])
        r['fx_now'] = fx if r['currency'] == 'USD' else 1
        r['as_of'] = ix[r['id']].get('at') or AT
        changed.add('indexes')
if 'indexes' in changed:
    save('indexes', indexes)
save('bench_history', bench)

# ---- rules, events, log, sources
if inp.get('rules_remove') or inp.get('rules_add'):
    rm = set(inp.get('rules_remove', []))
    rules = [r for r in rules if r['rule'] not in rm] + inp.get('rules_add', [])
    save('rules', rules)
if inp.get('events_add'):
    events += inp['events_add']
    save('events', events)
for e in inp.get('log', []):
    log.append({'at': e.get('at') or AT, 'portfolio': e['portfolio'], 'action': e['action'], 'detail': e['detail']})
save('log', log)
if inp.get('sources_add'):
    seen = {s['url'] for s in sources}
    for s in inp['sources_add']:
        if s['url'] not in seen:
            sources.append(s)
            seen.add(s['url'])
    save('sources', sources)

print('Totals (C$):', json.dumps(tot))
print('Combined: C$%.0f (%+.0f)' % (sum(tot.values()), sum(tot.values()) - 4 * START))
if warnings:
    print('WARNINGS:')
    for w in warnings:
        print('  -', w)
print('Changed data files:', ' '.join(sorted(changed)))
