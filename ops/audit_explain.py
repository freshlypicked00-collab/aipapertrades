"""Explain the price flags of the full audit (owner, Oct 31): for each flagged Yahoo symbol, the daily bars (previous close, open,
high, low) and the quote the race runner reads (chart meta regularMarketPrice and its precision). Read-only; prints and writes
ops/review/full-audit-explain-<time>.json."""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades audit; papertrades.ai)'}
def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read())
        except Exception as e:
            err = e; time.sleep(1.5)
    raise err
out = {}
for sym in ['510300.SS', '159915.SZ', 'JPYUSD=X', 'SQQQ', 'EURUSD=X', 'AUDUSD=X']:
    rec = {}
    try:
        j = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=10d&interval=1d')
        res = j['chart']['result'][0]; q = res['indicators']['quote'][0]
        rec['daily'] = [{'day': datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M'), 'open': o, 'high': h, 'low': l, 'close': c}
                        for ts, o, h, l, c in zip(res['timestamp'], q['open'], q['high'], q['low'], q['close'])]
        m = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1d&interval=5m')['chart']['result'][0]['meta']
        rec['meta'] = {k: m.get(k) for k in ('regularMarketPrice', 'previousClose', 'chartPreviousClose', 'priceHint', 'currency', 'regularMarketTime')}
    except Exception as e:
        rec['error'] = str(e)[:200]
    out[sym] = rec
    print(sym, json.dumps(rec)[:1500])
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'review', 'full-audit-explain-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M') + '.json')
json.dump(out, open(p, 'w'), indent=1); print('written', p)
