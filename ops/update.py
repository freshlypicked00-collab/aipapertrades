"""Apply one UPDATE ALL to the Paper Trades data.

Usage:
    python3 ops/update.py ops/src path/to/input.json

Reads the data files in ops/src, applies the prices, trades, bets and log
entries from the input file, recomputes every value, closes any finished
ledger day (days end at 00:00 UTC), and writes the files back. Prints a
summary and the list of data files that changed (these are the ones to
re-upload to the private tracker).

Input file format: see ops/RUNBOOK.md, section "The input file".
"""
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

SRC, INP = sys.argv[1], sys.argv[2]
START = 100000.0
ORDER = ['Stocks', 'Crypto', 'Metals', 'Sports', 'China']
CURRENCY = {'Stocks': 'CAD', 'Crypto': 'CAD', 'Metals': 'CAD', 'Sports': 'CAD', 'China': 'USD'}
BJ = timezone(timedelta(hours=8))


def path(name):
    return os.path.join(SRC, name + '.json')


def load(name, default=None):
    if not os.path.exists(path(name)):
        return default
    return json.load(open(path(name)))


def save(name, data):
    json.dump(data, open(path(name), 'w'), indent=1, ensure_ascii=False)
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
ledger = load('ledger', [])
fxd = load('fx', {})

fx = float(inp['fx']['usdcad'])
cny = inp['fx'].get('usdcny') or fxd.get('usdcny')
if inp['fx'].get('usdcny') is None:
    warnings.append('No USD/CNY rate given; reused the last one (%s)' % cny)
cny = float(cny) if cny else None
fxd.update({'usdcad': fx, 'usdcad_at': inp['fx'].get('at', AT), 'usdcad_source': inp['fx'].get('source', '')})
if inp['fx'].get('usdcny') is not None:
    fxd.update({'usdcny': cny, 'usdcny_at': inp['fx'].get('cny_at', inp['fx'].get('at', AT)), 'usdcny_source': inp['fx'].get('cny_source', inp['fx'].get('source', ''))})
save('fx', fxd)
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


def china_open(dt):
    b = dt.astimezone(BJ)
    if b.weekday() >= 5:
        return False
    m = b.hour * 60 + b.minute
    return 9 * 60 + 30 <= m <= 11 * 60 + 30 or 13 * 60 <= m <= 15 * 60


def china_trade(t):
    """China A-shares: prices in yuan, lots of 100 shares, shares bought today can't be sold until the next trading day."""
    h, action, price = t['holding'], t['action'], float(t['price'])
    if not cny:
        raise SystemExit('China trades need a USD/CNY rate')
    if not china_open(at_dt):
        warnings.append(f'China trade in {h} placed outside Shanghai/Shenzhen trading hours')
    cash = row('China', 'Cash (CNY)')
    r = row('China', h)
    if action == 'Buy':
        sh = int(t['shares'])
        if sh <= 0 or sh % 100:
            raise SystemExit(f'China buys must be whole lots of 100 shares ({h}: {sh})')
        amt = sh * price
        cash['quantity'] = round(cash['quantity'] - amt, 2)
        cash['cost_usd'] = round(cash.get('cost_usd', 0) - amt / cny, 2)
        if cash['quantity'] < -0.01:
            raise SystemExit('Not enough yuan cash in China for this buy')
        if r is None:
            r = {'portfolio': 'China', 'holding': h, 'code': t.get('code', ''), 'currency': 'CNY', 'quantity': 0,
                 'entry_local': price, 'price_local': price, 'change_pct': 0, 'value_usd': 0, 'value_cad': 0,
                 'as_of': AT, 'cost_usd': 0, 'price_source': '', 'price_at': None}
            idx = max(i for i, x in enumerate(holdings) if x['portfolio'] == 'China')
            holdings.insert(idx, r)  # keep cash last
        q0 = r['quantity']
        r['entry_local'] = round((q0 * r['entry_local'] + sh * price) / (q0 + sh), 4)
        r['quantity'] = q0 + sh
        r['cost_usd'] = round(r.get('cost_usd', 0) + amt / cny, 2)
    elif action == 'Sell':
        if r is None:
            raise SystemExit(f'Cannot sell {h}: not held in China')
        q0 = r['quantity']
        if 'shares' in t:
            sh = int(t['shares'])
        elif float(t['fraction']) >= 1:
            sh = q0
        else:
            sh = int(q0 * float(t['fraction']) // 100 * 100)
        today = at_dt.astimezone(BJ).date()
        bought_today = sum(x.get('shares', 0) for x in trades if x['portfolio'] == 'China' and x['holding'] == h
                           and x['action'] == 'Buy' and ts(x['at']).astimezone(BJ).date() == today)
        if sh > q0 - bought_today:
            raise SystemExit(f'{h}: only {q0 - bought_today} shares can be sold today (shares bought today settle tomorrow)')
        amt = sh * price
        cost_out = r.get('cost_usd', 0) * sh / q0
        r['realized_usd'] = round(r.get('realized_usd', 0) + amt / cny - cost_out, 2)
        r['cost_usd'] = round(r.get('cost_usd', 0) - cost_out, 2)
        r['quantity'] = q0 - sh
        cash['quantity'] = round(cash['quantity'] + amt, 2)
        cash['cost_usd'] = round(cash.get('cost_usd', 0) + amt / cny, 2)
    else:
        raise SystemExit(f'Unknown trade action {action}')
    trades.append({'at': AT, 'portfolio': 'China', 'holding': h, 'action': action, 'price_local': price,
                   'currency': 'CNY', 'shares': sh, 'cny': round(amt, 2), 'usd': round(amt / cny, 2)})


# ---- trades
for t in inp.get('trades', []):
    pf, h, action, cad = t['portfolio'], t['holding'], t['action'], float(t.get('cad', 0))
    if pf == 'China':
        china_trade(t)
        save('trades', trades)
        continue
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
    if r.get('currency') == 'CNY':
        if h == 'Cash (CNY)':
            r['value_usd'] = round(r['quantity'] / cny, 2)
        else:
            if h in P:
                q = P[h]
                r['price_local'] = float(q['price'])
                r['price_source'] = q.get('source', '')
                r['price_at'] = q.get('at')
            r['change_pct'] = round(r['price_local'] / r['entry_local'] - 1, 4) if r['entry_local'] else 0
            r['value_usd'] = round(r['quantity'] * r['price_local'] / cny, 2)
        r['value_cad'] = round(r['value_usd'] * fx, 2)
    elif h == 'Cash (CAD)':
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
    b['settled_at'] = AT
if inp.get('bets_new') or inp.get('bets_closing') or inp.get('bets_settle'):
    save('bets', bets)

# ---- totals and history
tot = {}
for pf in ('Stocks', 'Crypto', 'Metals'):
    tot[pf] = round(sum(r['value_cad'] for r in holdings if r['portfolio'] == pf), 2)
tot['Sports'] = round(START + sum(b['result_cad'] or 0 for b in bets if b['status'] != 'Open'), 2)
if any(r['portfolio'] == 'China' for r in holdings):
    tot['China'] = round(sum(r['value_usd'] for r in holdings if r['portfolio'] == 'China'), 2)
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
SERIES = {'sp500': 'S&P 500', 'csi300': 'CSI 300'}
for key, name in SERIES.items():
    if key in ix:
        f = fx if key == 'sp500' else 1 / cny  # bench_history fx turns the level into the portfolio's currency
        bench.append({'series': name, 'at': ix[key].get('at') or AT, 'level': float(ix[key]['level']), 'fx': f, 'source': ix[key].get('source', '')})
for r in indexes:
    if r['id'] in ix:
        q = ix[r['id']]
        if r['currency'] == 'USD':
            f = fx
        elif r['currency'] == 'CNY':
            f = 1 / cny
        else:
            f = 1
        if r.get('start_level') is None:
            r['start_level'] = float(q['level'])
            r['fx_start'] = f
            r['start_at'] = q.get('at') or AT
        r['now_level'] = float(q['level'])
        r['fx_now'] = f
        r['as_of'] = q.get('at') or AT
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

# ---- daily ledger: each day runs 00:00 to 00:00 UTC
UTC = timezone.utc
series = {pf: sorted(((ts(h['at']).astimezone(UTC), float(h['value'])) for h in history if h['portfolio'] == pf)) for pf in ORDER}


def value_at(pf, T):
    """The check-in nearest T within an hour (later one on a tie), else the last one before T, else None."""
    s = series[pf]
    near = [(abs((t - T).total_seconds()), -t.timestamp(), v) for t, v in s if abs((t - T).total_seconds()) <= 3600]
    if near:
        return min(near)[2]
    before = [v for t, v in s if t <= T]
    return before[-1] if before else None


done = {r['day'] for r in ledger}
first_points = [s[0][0] for s in series.values() if s]
closed_now = []
if first_points:
    d = min(first_points).date()
    now_utc = at_dt.astimezone(UTC)
    while True:
        start = datetime(d.year, d.month, d.day, tzinfo=UTC)
        end = start + timedelta(days=1)
        if end > now_utc:
            break
        key = d.isoformat()
        if key not in done:
            rows = []
            for pf in ORDER:
                s = series[pf]
                if not s or s[0][0] > end + timedelta(hours=1):
                    continue
                o = value_at(pf, start)
                o = START if o is None else o
                c = value_at(pf, end)
                rows.append({'day': key, 'start_at': start.isoformat().replace('+00:00', 'Z'), 'end_at': end.isoformat().replace('+00:00', 'Z'),
                             'portfolio': pf, 'currency': CURRENCY[pf], 'open': round(o, 2), 'close': round(c, 2),
                             'pnl': round(c - o, 2), 'pct': round(c / o - 1, 5), 'note': ''})
            if rows:
                # 'All' only holds the general notes for the day; the experiments are never added together
                rows.insert(0, {'day': key, 'start_at': rows[0]['start_at'], 'end_at': rows[0]['end_at'], 'portfolio': 'All', 'currency': None,
                                'open': None, 'close': None, 'pnl': None, 'pct': None, 'note': ''})
                ledger.extend(rows)
                closed_now.append((key, rows))
        d += timedelta(days=1)
if closed_now:
    save('ledger', ledger)

print('Each experiment on its own (never add them together):')
for pf, v in tot.items():
    print('   %-7s %s%.0f (%+.0f since start)' % (pf, 'US$' if pf == 'China' else 'C$', v, v - START))
for key, rows in closed_now:
    print('LEDGER DAY CLOSED', key, '- write notes with ops/ledger_note.py:')
    for r in rows:
        if r['portfolio'] != 'All':
            print('   %-7s %+12.2f %s' % (r['portfolio'], r['pnl'], r['currency']))
if warnings:
    print('WARNINGS:')
    for w in warnings:
        print('  -', w)
print('Changed data files:', ' '.join(sorted(changed)))
