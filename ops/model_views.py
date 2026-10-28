"""Turn ops/src/rivals.json into per-model datasets with the same shapes the site uses for Claude.

build_site.py puts the result in data.json under "models": {"gemini": {...}, "chatgpt": {...}}.
When a viewer picks a model in the site's model menu, the page swaps these datasets in place of Claude's,
so every tab, chart, ledger and table shows that model's own experiments.
"""
import json
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
CASH_NAME = {'CAD': 'Cash (CAD)', 'USD': 'Cash (US$)'}


def _t(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def _clean(name, exp):
    return name[:-4] if exp == 'Crypto' and name.endswith(' USD') else name


def _nearest_level(bench, series, at):
    """First benchmark reading at or after `at`, else the last one before it."""
    rows = sorted((r for r in bench if r['series'] == series), key=lambda r: _t(r['at']))
    after = [r for r in rows if _t(r['at']) >= at]
    pick = after[0] if after else (rows[-1] if rows else None)
    return pick


def build(rivals, claude):
    """rivals: parsed rivals.json; claude: dict of Claude's datasets (indexes, bench_history, benchmark, prices, events, fx)."""
    out = {}
    fx_now = rivals.get('fx') or {'USDCAD': claude['fx'].get('usdcad'), 'USDCNY': claude['fx'].get('usdcny')}
    for mid, m in rivals.get('models', {}).items():
        exps = m.get('exps', list(m['books']))
        started = {e: _t(m.get('started', {}).get(e) or m.get('started_at') or rivals['history'][0]['at']) for e in exps}
        trades = [t for t in rivals['trades'] if t['model'] == mid]
        hist = [h for h in rivals['history'] if h['model'] == mid]
        d = {k: [] for k in ('holdings', 'history', 'trades', 'log', 'take', 'ledger', 'prices', 'review', 'rules', 'bets', 'sources')}

        # cost basis per position, from the trade list
        cost = {}
        for t in trades:
            key = (t['experiment'], f"{t['symbol']}|{t['outcome']}" if t.get('outcome') else t['symbol'])
            c = cost.setdefault(key, {'qty': 0.0, 'cost': 0.0})
            if t['action'] == 'Buy':
                c['qty'] += t['qty']
                c['cost'] += t['amount']
            elif c['qty'] > 0:
                frac = min(1.0, t['qty'] / c['qty'])
                c['cost'] *= (1 - frac)
                c['qty'] -= t['qty']

        last_at = max([h['at'] for h in hist] or [datetime.now(UTC).isoformat()])
        for e in exps:
            b = m['books'][e]
            cur = b['cur']
            for key, p in b['positions'].items():
                price = p.get('last', p['entry'])
                c = cost.get((e, key), {'cost': p['qty'] * p['entry']})
                row = {'portfolio': e, 'holding': _clean(p.get('name') or key, e), 'code': key.split('|')[0], 'quantity': p['qty'],
                       'change_pct': price / p['entry'] - 1 if p['entry'] else 0, 'as_of': last_at, 'price_at': p.get('priced_at'),
                       'price_source': 'Yahoo Finance' if e != 'Predictions' else 'Polymarket'}
                if e == 'China':
                    usd = p['qty'] * price / fx_now['USDCNY']
                    row.update(currency='CNY', entry_local=p['entry'], price_local=price, value_usd=round(usd, 2),
                               value_cad=round(usd * fx_now['USDCAD'], 2), cost_usd=round(c['cost'], 2))
                else:
                    if key.count('|'):
                        row['holding'] = f"{p.get('name') or key.split('|')[0]} ({key.split('|')[1]})"
                    row.update(entry_usd=p['entry'], price_usd=price, value_cad=round(p['qty'] * price * fx_now['USDCAD'], 2),
                               cost_cad=round(c['cost'], 2))
                d['holdings'].append(row)
            cash = {'portfolio': e, 'holding': CASH_NAME[cur], 'quantity': b['cash'], 'change_pct': 0, 'as_of': last_at,
                    'price_at': None, 'price_source': ''}
            if e == 'China':
                cash.update(currency='USD', entry_local=None, price_local=None, value_usd=round(b['cash'], 2),
                            value_cad=round(b['cash'] * fx_now['USDCAD'], 2), cost_usd=round(b['cash'], 2))
            else:
                cash.update(entry_usd=None, price_usd=None, value_cad=round(b['cash'], 2), cost_cad=round(b['cash'], 2))
            d['holdings'].append(cash)
            d['history'].append({'at': started[e].isoformat(), 'portfolio': e, 'value': 100000.0, 'close': False})
        for h in hist:
            d['history'].append({'at': h['at'], 'portfolio': h['experiment'], 'value': h['value'], 'close': False})

        for t in trades:
            what = _clean(t.get('name') or t['symbol'], t['experiment'])
            if t.get('outcome'):
                what = f"{what} ({t['outcome']})"
            row = {'at': t['at'], 'portfolio': t['experiment'], 'holding': what, 'action': 'Sell' if t['action'] == 'Settled' else t['action'],
                   'note': t['reason']}
            if t['experiment'] == 'China':
                row.update(price_local=t['price'], currency='CNY', shares=t['qty'], cny=round(t['qty'] * t['price'], 2), usd=t['amount'])
            else:
                row.update(price_usd=t['price'], cad=t['amount'], qty=t['qty'])
            d['trades'].append(row)
            sym = {'CAD': 'C$', 'USD': 'US$'}[t['cur']]
            d['log'].append({'at': t['at'], 'portfolio': t['experiment'], 'action': row['action'],
                             'detail': f"{t['action']} {what} ({sym}{t['amount']:,.0f}). {t['reason']}"})
            d['prices'].append({'asset': what if t['experiment'] != 'China' else what, 'at': t['at'], 'price': t['price']})
        for h in d['holdings']:
            if h.get('price_at') and (h.get('price_usd') or h.get('price_local')):
                d['prices'].append({'asset': h['holding'], 'at': h['price_at'], 'price': h.get('price_usd') or h.get('price_local')})
        for e in exps:
            d['log'].append({'at': started[e].isoformat(), 'portfolio': e, 'action': 'Start',
                             'detail': 'Started with ' + ('US$' if e == 'China' else 'C$') + '100,000.'})
        for th in rivals.get('thoughts', []):
            if th['model'] == mid and th['experiment'] in exps:
                d['log'].append({'at': th['at'], 'portfolio': th['experiment'], 'action': 'Note', 'detail': th['text']})
        lr = m.get('last_run') or {}
        for n in lr.get('notes', []):
            if n.startswith('order refused'):
                pf = next((e for e in exps if f'({e} ' in n), exps[0])
                d['log'].append({'at': lr['at'], 'portfolio': pf, 'action': 'Not filled', 'detail': n.replace('order refused ', 'Order not filled ') + '.'})
        if lr.get('at'):
            d['log'].append({'at': lr['at'], 'portfolio': 'All', 'action': 'Check-in', 'detail': f"Check-in ({m.get('model') or m['label']})."})
        d['log'].sort(key=lambda r: _t(r['at']))
        d['review'] = [{'at': x['at'], 'portfolio': x['experiment'], 'grade': x['grade'], 'text': x['text']} for x in rivals.get('reviews', []) if x['model'] == mid]
        d['take'] = [{'at': x['at'], 'text': x['text']} for x in rivals.get('takes', []) if x['model'] == mid]
        d['sources'] = [{'title': s['title'], 'url': s['url'], 'portfolios': exps} for s in lr.get('sources', [])]

        # daily ledger at 00:00 UTC, from the hourly check-ins
        for e in exps:
            pts = sorted([(started[e], 100000.0)] + [(_t(h['at']), h['value']) for h in hist if h['experiment'] == e])
            day = started[e].astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            now = datetime.now(UTC)
            while day + timedelta(days=1) <= now:
                end = day + timedelta(days=1)
                before_open = [v for t, v in pts if t <= day]
                before_close = [v for t, v in pts if t <= end]
                if before_close and end > started[e]:
                    o = before_open[-1] if before_open else 100000.0
                    c = before_close[-1]
                    d['ledger'].append({'day': day.date().isoformat(), 'start_at': day.isoformat().replace('+00:00', 'Z'),
                                        'end_at': end.isoformat().replace('+00:00', 'Z'), 'portfolio': e,
                                        'currency': 'USD' if e == 'China' else 'CAD', 'open': o, 'close': c,
                                        'pnl': round(c - o, 2), 'pct': c / o - 1 if o else 0,
                                        'note': next((x['text'] for x in reversed(rivals.get('reviews', [])) if x['model'] == mid and x['experiment'] == e and x['day'] == day.date().isoformat()), '')})
                day = end

        # benchmarks re-based to the day this model started each experiment
        idx = []
        for r in claude['indexes']:
            if r['portfolio'] not in exps:
                continue
            r = dict(r)
            st = started[r['portfolio']]
            if r.get('kind') == 'rate':
                r['start_at'] = st.isoformat()
            else:
                series = {'sp500': 'S&P 500', 'csi300': 'CSI 300'}.get(r['id'], r.get('index'))
                pick = _nearest_level(claude['bench_history'], series, st)
                if pick:
                    r.update(start_at=pick['at'], start_level=pick['level'], fx_start=pick.get('fx', r.get('fx_start')))
                elif r.get('now_level'):
                    r.update(start_at=st.isoformat(), start_level=r['now_level'], fx_start=r.get('fx_now'))
            idx.append(r)
        d['indexes'] = idx
        btc = sorted((p for p in claude['prices'] if p['asset'] == 'Bitcoin'), key=lambda p: _t(p['at']))
        bm = []
        for r in claude['benchmark']:
            if r['portfolio'] not in exps:
                continue
            r = dict(r)
            st = started[r['portfolio']]
            after = [p for p in btc if _t(p['at']) >= st]
            p0 = after[0] if after else (btc[-1] if btc else None)
            if p0:
                r.update(start_at=st.isoformat(), btc_start_usd=p0['price'], fx_start=fx_now['USDCAD'])
            bm.append(r)
        d['benchmark'] = bm
        skip = ('check-in', 'opening orders', 'rule', 'bet ', 'Bet ')
        d['events'] = [ev for ev in claude['events'] if any(x.strip() in exps for x in str(ev.get('affects', '')).split(','))
                       and not any(k in ev['event'] + ' ' + ev.get('why', '') for k in skip)]
        d['_meta'] = {'id': mid, 'label': m['label'], 'company': m.get('company'), 'model': m.get('model'), 'exps': exps,
                      'last_run': lr}
        out[mid] = d
    return out
