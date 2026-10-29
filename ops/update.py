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
ORDER = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
MARGIN = {'Currencies'}  # cash may go negative (borrowing); shorts allowed
CURRENCY = {p: ('USD' if p == 'China' else 'CAD') for p in ORDER}
BENCH_NAMES = {'sp500': 'S&P 500', 'csi300': 'CSI 300', 'uso': 'Oil (USO fund)', 'gold': 'Gold'}
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
_trades_before = [dict(x) for x in trades]   # restored if this run's buys break a position cap
bench = load('bench_history')
sources = load('sources')
ledger = load('ledger', [])
fxd = load('fx', {})
take = load('take', [])

# OPTION B (owner's go, Oct 29): from the switch, Claude's trades and bets are filled by the race runner (ops/claude_fill.py),
# the same code and feed as Gemini's and ChatGPT's. A session's own input may still value holdings, settle Claude's older bets,
# log, write takes and rules, but no longer trade or place bets: queue them with ops/orders.py.
try:
    _ob = json.load(open(os.path.join(SRC, 'option_b.json')))
    _cut = datetime.fromisoformat(_ob['cutover'])
except Exception:
    _ob, _cut = {}, None
if _cut and at_dt >= _cut and not inp.get('runner') and (inp.get('trades') or inp.get('bets_new')):
    raise SystemExit('Option B is on: trades and bets are filled by the race runner now, at the same feed prices as Gemini and ChatGPT. '
                     'Queue them with `python3 ops/orders.py queue \'{...}\'`, push, then dispatch rivals.yml with mode=fill (see ops/RUNBOOK.md). '
                     'Nothing was saved.')
# check the bet results before any file is written, so a bad status can't leave the data half-updated
for _s in inp.get('bets_settle', []):
    if _s.get('status') not in ('Won', 'Lost', 'Push', 'Void'):
        raise SystemExit(f"bets_settle: status must be Won, Lost, Push or Void (got {_s.get('status')!r} for {_s.get('bet')})")
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
                   'currency': 'CNY', 'shares': sh, 'cny': round(amt, 2), 'usd': round(amt / cny, 2),
                   **({'note': t['note']} if t.get('note') else {}), **({'filled_by': t['filled_by']} if t.get('filled_by') else {})})


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
        if 'qty' in t:  # exact number of shares / contracts x 100 / prediction shares
            qty = float(t['qty'])
            cad = qty * price * fx
        else:
            qty = cad / fx / price
        if fund is None:
            raise SystemExit(f'No funding holding {fund_name} in {pf}')
        if fund_name == 'USDC':
            fund['quantity'] = round(fund['quantity'] - cad / fx, 6)
        else:
            fund['quantity'] = round(fund['quantity'] - cad, 2)
        fund['cost_cad'] = round(fund.get('cost_cad', 0) - cad, 2)
        if fund['quantity'] < -0.01 and pf not in MARGIN:
            raise SystemExit(f'Not enough {fund_name} in {pf} for this buy')
        if r is None:
            r = {'portfolio': pf, 'holding': h, 'quantity': 0, 'entry_usd': price, 'price_usd': price,
                 'change_pct': 0, 'value_cad': 0, 'as_of': AT, 'cost_cad': 0, 'price_source': '', 'price_at': None}
            if t.get('code'):
                r['code'] = t['code']   # the feed symbol (option, prediction market slug, ...), so the runner can trade it later
            idx = max([i for i, x in enumerate(holdings) if x['portfolio'] == pf] or [len(holdings) - 1]) + 1
            holdings.insert(idx, r)
        q0 = r['quantity']
        r['entry_usd'] = round((q0 * r['entry_usd'] + qty * price) / (q0 + qty), 10)
        r['quantity'] = round(q0 + qty, 6)
        r['cost_cad'] = round(r.get('cost_cad', 0) + cad, 2)
    elif action == 'Sell':
        if r is None:
            raise SystemExit(f'Cannot sell {h}: not held in {pf}')
        q0 = r['quantity']
        qty = q0 * float(t['fraction']) if 'fraction' in t else float(t['qty']) if 'qty' in t else cad / fx / price
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
    elif action in ('Short', 'Cover'):
        if pf not in MARGIN:
            raise SystemExit(f'Short selling is only allowed in {sorted(MARGIN)}')
        qty = float(t['qty']) if 'qty' in t else cad / fx / price
        cad = qty * price * fx
        if r is None:
            r = {'portfolio': pf, 'holding': h, 'quantity': 0, 'entry_usd': price, 'price_usd': price,
                 'change_pct': 0, 'value_cad': 0, 'as_of': AT, 'cost_cad': 0, 'price_source': '', 'price_at': None}
            holdings.insert(max(i for i, x in enumerate(holdings) if x['portfolio'] == pf) + 1, r)
        q0 = r['quantity']
        if action == 'Short':  # borrow and sell: quantity goes negative, cash goes up
            r['entry_usd'] = round((abs(q0) * r['entry_usd'] + qty * price) / (abs(q0) + qty), 8)
            r['quantity'] = round(q0 - qty, 6)
            r['cost_cad'] = round(r.get('cost_cad', 0) - cad, 2)
            fund['quantity'] = round(fund['quantity'] + cad, 2)
            fund['cost_cad'] = round(fund.get('cost_cad', 0) + cad, 2)
        else:  # buy back
            qty = min(qty, abs(q0))
            cad = qty * price * fx
            cost_back = r.get('cost_cad', 0) * qty / abs(q0)  # negative
            r['realized_cad'] = round(r.get('realized_cad', 0) + (-cost_back) - cad, 2)
            r['cost_cad'] = round(r.get('cost_cad', 0) - cost_back, 2)
            r['quantity'] = round(q0 + qty, 6)
            fund['quantity'] = round(fund['quantity'] - cad, 2)
            fund['cost_cad'] = round(fund.get('cost_cad', 0) - cad, 2)
    else:
        raise SystemExit(f'Unknown trade action {action}')
    trades.append({'at': t.get('fill_at') or AT, 'portfolio': pf, 'holding': h, 'action': action, 'price_usd': price, 'cad': round(cad, 2), **({'note': t['note']} if t.get('note') else {}),
                   **({'filled_by': t['filled_by']} if t.get('filled_by') else {})})
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
# ---- position caps (the same hard rules the rivals' code enforces): a buy that leaves one holding above 50% of its
# experiment (Play it safe: gold funds at most 10%; Prediction markets: one market at most 25%) is refused, and the
# whole run is undone so nothing half-applied is saved. Currencies, Sports and All in have their own rules.
_CAP = {'Predictions': 0.25}
_GOLD = {'GLD', 'IAU', 'GLDM'}
_bought = {(t['portfolio'], t['holding']) for t in inp.get('trades', []) if t.get('action') in ('Buy', 'Short')}
_bad = []
for (pf_, h_) in _bought:
    if pf_ in ('Currencies', 'Sports') or pf_.startswith('AllIn'):
        continue
    key = 'value_usd' if pf_ == 'China' else 'value_cad'
    tot_ = sum(float(r.get(key) or 0) for r in holdings if r['portfolio'] == pf_)
    val_ = sum(float(r.get(key) or 0) for r in holdings if r['portfolio'] == pf_ and r['holding'] == h_)
    cap_ = 0.10 if (pf_ == 'Safe' and h_ in _GOLD) else _CAP.get(pf_, 0.50)
    if tot_ > 0 and val_ / tot_ > cap_ + 0.005:
        _bad.append(f'{pf_} {h_}: {val_ / tot_:.0%} of the experiment (cap {cap_:.0%})')
if _bad:
    save('trades', _trades_before)
    raise SystemExit('position cap: order refused, nothing saved. ' + '; '.join(_bad) + '. Buy less so the holding stays within the cap.')
save('holdings', holdings)

# ---- bets
by_id = {b['bet']: b for b in bets}
for b in inp.get('bets_new', []):
    stake = float(b['stake_cad'])
    nb = {'bet': b['bet'], 'placed': AT[:10], 'placed_at': AT, 'sport': b['sport'], 'event': b['event'], 'pick': b['pick'],
          'odds': b['odds'], 'stake_cad': stake, 'to_win_cad': to_win(stake, b['odds']), 'status': 'Open',
          'result_cad': None, 'market': b.get('market', 'moneyline'), 'line': b.get('line'),
          'closing_odds': None, 'closing_line': None, 'starts_at': b.get('starts_at')}
    for _k in ('game', 'league', 'espn_sport', 'side', 'legs', 'note', 'filled_by'):   # placed by the race runner (option B)
        if b.get(_k) is not None:
            nb[_k] = b[_k]
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
    b['result_cad'] = {'Won': b['to_win_cad'], 'Lost': -b['stake_cad'], 'Push': 0, 'Void': 0}[s['status']]
    if inp.get('runner') and s.get('result_cad') is not None:   # the runner's own result (a parlay with a pushed leg pays less)
        b['result_cad'] = float(s['result_cad'])
    if s.get('final'):
        b['final'] = s['final']
    b['settled_at'] = AT
if inp.get('bets_new') or inp.get('bets_closing') or inp.get('bets_settle'):
    save('bets', bets)

# ---- totals and history
tot = {}
for pf in ORDER:
    if pf in ('Sports', 'China') or not any(r['portfolio'] == pf for r in holdings):
        continue
    tot[pf] = round(sum(r['value_cad'] for r in holdings if r['portfolio'] == pf), 2)
try:   # betting-minimum penalties (kept by ops/rivals.py, same rule for every AI)
    _pen = sum(float(x['amount']) for x in json.load(open(os.path.join(SRC, 'rivals.json'))).get('claude_penalties', []))
except Exception:
    _pen = 0.0
tot['Sports'] = round(START + sum(b['result_cad'] or 0 for b in bets if b['status'] != 'Open') - _pen, 2)
if any(r['portfolio'] == 'China' for r in holdings):
    tot['China'] = round(sum(r['value_usd'] for r in holdings if r['portfolio'] == 'China'), 2)
is_close = at_dt.weekday() < 5 and at_dt.hour == 16
for pf, v in tot.items():
    history.append({'at': AT, 'portfolio': pf, 'value': v, 'close': is_close})
save('history', history)

# ---- price history, benchmarks, indexes
for asset, q in P.items():
    e = {'asset': asset, 'at': q.get('at') or AT, 'price': float(q['price'])}
    for k in ('high', 'low', 'range_from'):
        if q.get(k) is not None:
            e[k] = q[k]
    prices.append(e)
save('prices', prices)
# stop/limit check: did any price rule's level get crossed since the last run (by the recorded high/low or the new price)?
crossed = []
for r in rules:
    a, lvl, d = r.get('asset'), r.get('level'), r.get('direction')
    if not a or lvl is None or a not in P:
        continue
    q = P[a]
    hi = float(q.get('high', q['price']))
    lo = float(q.get('low', q['price']))
    if (d == 'above' and hi >= float(lvl)) or (d == 'below' and lo <= float(lvl)):
        crossed.append((r['portfolio'], a, r.get('label'), lvl, d, q['price'], hi, lo))
if 'Bitcoin' in P:
    bench.append({'series': 'Bitcoin', 'at': P['Bitcoin'].get('at') or AT, 'level': float(P['Bitcoin']['price']), 'fx': fx, 'source': P['Bitcoin'].get('source', '')})
    _started = {t['portfolio'] for t in trades}
    for r in benchmark:
        if r.get('btc_start_usd') is None:  # after a fresh start the comparison begins at the first trade
            if r['portfolio'] not in _started:
                continue
            r['btc_start_usd'] = float(P['Bitcoin']['price'])
            r['fx_start'] = fx
            r['start_at'] = min(t['at'] for t in trades if t['portfolio'] == r['portfolio'])
        r['btc_now_usd'] = float(P['Bitcoin']['price'])
        r['fx_now'] = fx
        r['as_of'] = AT
    save('benchmark', benchmark)
ix = dict(inp.get('indexes', {}))
if 'Gold' in P and 'gold' not in ix:  # the Metals benchmark follows the gold price
    ix['gold'] = {'level': P['Gold']['price'], 'at': P['Gold'].get('at'), 'source': P['Gold'].get('source', '')}
for key, name in BENCH_NAMES.items():
    if key in ix:
        f = 1 / cny if key == 'csi300' else fx  # bench_history fx turns the level into the portfolio's currency
        bench.append({'series': name, 'at': ix[key].get('at') or AT, 'level': float(ix[key]['level']), 'fx': f, 'source': ix[key].get('source', '')})
started = {t['portfolio'] for t in trades}
for r in indexes:
    if r.get('kind') == 'rate':  # savings-account benchmark: starts with the portfolio's first trade
        if r.get('start_at') is None and r['portfolio'] in started:
            r['start_at'] = min(t['at'] for t in trades if t['portfolio'] == r['portfolio'])
            changed.add('indexes')
        continue
    feed = r.get('feed', r['id'])
    if feed in ix:
        q = ix[feed]
        f = fx if r['currency'] == 'USD' else (1 / cny if r['currency'] == 'CNY' else 1)
        if r.get('start_level') is None:
            if r['portfolio'] not in started:
                continue  # the comparison starts when the portfolio makes its first trade
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
if inp.get('take'):  # the AI's one-sentence take for the top of the site
    take.append({'at': AT, 'text': inp['take'].strip()})
    save('take', take)
_RT = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
if isinstance(inp.get('race_takes'), dict):  # one take per race, shown when a visitor picks that race
    for _e, _t in inp['race_takes'].items():
        if _e in _RT and str(_t).strip():
            take.append({'at': AT, 'experiment': _e, 'text': str(_t).strip()[:400]})
    save('take', take)
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
if first_points and not inp.get('no_ledger_close'):
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
for pf_, a, lab, lvl, d, px, hi, lo in crossed:
    print(f'RULE LEVEL CROSSED: {pf_} {a} "{lab}" {d} {lvl} (now {px}, high {hi}, low {lo}). If not already done, make the trade: fill at the level, or at the price after a gap if it opened beyond the level; then remove or update the rule.')
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
