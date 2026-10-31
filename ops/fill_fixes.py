"""V3 of the full-audit vote (Oct 31; Claude, Gemini and ChatGPT all agreed, ops/review/audit-fix-oct31.json): restate the fills that
were filled at a stale or rounded feed price (P1 to P4) at the close of the Yahoo 1-minute bar of the fill minute. Read-only: fetches the
bars and writes ops/review/full-audit-fixes-<time>.json with every number; nothing in the race changes here. The corrections themselves
are applied once by the race runner from ops/src/price_corrections.json.

Correction in the book's currency (amount = the fill's own book amount, so its exchange rate is the fill's own):
  buy or cover: amount * (1 - bar / fill)      (positive = the AI paid too much and gets the difference back)
  sell or short: amount * (bar / fill - 1)     (negative = the AI received too much)
"""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades audit; papertrades.ai)'}
HERE = os.path.dirname(os.path.abspath(__file__))
# (who, race, fill time UTC, action, symbol in the record, Yahoo symbol, qty, fill price, book amount, book currency, problem)
FILLS = [
    ('gemini', 'China', '2026-10-29T01:36:43Z', 'Buy', '510300.SS', '510300.SS', 80200, 4.152, 49973.05, 'USD', 'P1'),
    ('gemini', 'China', '2026-10-29T01:36:43Z', 'Buy', '159915.SZ', '159915.SZ', 100600, 2.649, 39993.01, 'USD', 'P1'),
    ('chatgpt', 'China', '2026-10-29T01:36:43Z', 'Buy', '510300.SS', '510300.SS', 32000, 4.152, 19939.37, 'USD', 'P1'),
    ('chatgpt', 'China', '2026-10-29T01:36:43Z', 'Buy', '159915.SZ', '159915.SZ', 25100, 2.649, 9978.37, 'USD', 'P1'),
    ('gemini', 'China', '2026-10-30T01:36:45Z', 'Sell', '159915.SZ', '159915.SZ', 100600, 2.535, 38291.44, 'USD', 'P1'),
    ('gemini', 'China', '2026-10-30T01:36:45Z', 'Sell', '510300.SS', '510300.SS', 80200, 4.111, 49504.83, 'USD', 'P1'),
    ('chatgpt', 'China', '2026-10-30T01:36:45Z', 'Sell', '159915.SZ', '159915.SZ', 12500, 2.535, 4757.88, 'USD', 'P1'),
    ('gemini', 'Currencies', '2026-10-28T18:32:55Z', 'Short', 'JPY', 'JPY=X', 5649966.49569868, 0.0063, 50000.0, 'CAD', 'P2'),
    ('gemini', 'Currencies', '2026-10-29T02:14:30Z', 'Cover', 'JPY', 'JPY=X', 5649966.49569868, 0.0063, 49736.6, 'CAD', 'P2'),
    ('claude', 'Metals', '2026-10-30T13:52:17Z', 'Sell', 'Silver', 'SI=F', None, 49.825, 13885.77, 'CAD', 'P3'),
    ('gemini', 'AllInTrading', '2026-10-30T19:44:20Z', 'Buy', 'SQQQ', 'SQQQ', 837.2345322908592, 42.795, 50000.0, 'CAD', 'P4'),
]


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read())
        except Exception as e:
            err = e; time.sleep(1.5)
    raise err


def minute_bars(ysym, t):
    t0, t1 = int((t - timedelta(minutes=20)).timestamp()), int((t + timedelta(minutes=20)).timestamp())
    res = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ysym)}?period1={t0}&period2={t1}&interval=1m')['chart']['result'][0]
    q = res['indicators']['quote'][0]
    out = []
    for i, ts in enumerate(res.get('timestamp') or []):
        if q['close'][i] is not None:
            out.append({'minute': datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'open': q['open'][i], 'high': q['high'][i], 'low': q['low'][i], 'close': q['close'][i]})
    return out


rows = []
for who, race, at, act, sym, ysym, qty, fill, amount, cur, prob in FILLS:
    t = datetime.fromisoformat(at.replace('Z', '+00:00'))
    rec = {'model': who, 'race': race, 'fill_at': at, 'action': act, 'symbol': sym, 'feed': ysym, 'qty': qty, 'fill_price': fill, 'amount': amount, 'currency': cur, 'problem': prob}
    try:
        bars = minute_bars(ysym, t)
        m = t.strftime('%Y-%m-%dT%H:%MZ')
        bar = next((b for b in bars if b['minute'] == m), None) or ([b for b in bars if b['minute'] <= m] or [None])[-1]
        if not bar:
            raise ValueError('no bar at or before the fill minute')
        px = float(bar['close'])
        if ysym == 'JPY=X':      # yen per US$ -> US$ per yen
            px = 1.0 / px
            bar = {**bar, 'as_usd_per_yen': px}
        corr = amount * (1 - px / fill) if act in ('Buy', 'Cover') else amount * (px / fill - 1)
        rec.update(bar=bar, bar_price=round(px, 8), correction=round(corr, 2), nearby=[b for b in bars if abs((datetime.fromisoformat(b['minute'].replace('Z', '+00:00')) - t).total_seconds()) <= 360])
    except Exception as e:
        rec['error'] = str(e)[:200]
    rows.append(rec)
    print(who, race, at, act, sym, fill, '->', rec.get('bar_price'), 'correction', rec.get('correction'), cur, rec.get('error', ''))
tot = {}
for r in rows:
    if 'correction' in r:
        k = f"{r['model']}|{r['race']}|{r['currency']}"
        tot[k] = round(tot.get(k, 0) + r['correction'], 2)
print('totals', tot)
p = os.path.join(HERE, 'review', 'full-audit-fixes-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M') + '.json')
json.dump({'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'totals': tot, 'rows': rows}, open(p, 'w'), indent=1)
print('written', p)
