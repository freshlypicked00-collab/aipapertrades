"""Crypto standings check for the full audit (owner, Oct 31): the 1-minute Yahoo bars (BTC, ETH, SOL, USD/CAD) around the Oct 28 and
Oct 29 day closes (00:00 UTC) and the 9:14 p.m. ET Oct 28 Crypto moment, so each AI's Crypto value can be re-priced at the same feed
at the same minute. Read-only; writes ops/review/full-audit-crypto-<time>.json."""
import json, os, time, urllib.request, urllib.parse
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
WINDOWS = [('2026-10-28T22:00:00Z', '2026-10-29T03:00:00Z'), ('2026-10-29T22:00:00Z', '2026-10-30T01:00:00Z')]
out = {}
for sym in ['BTC-USD', 'ETH-USD', 'SOL-USD', 'CAD=X']:
    rows = []
    for a, b in WINDOWS:
        t0 = int(datetime.fromisoformat(a.replace('Z', '+00:00')).timestamp()); t1 = int(datetime.fromisoformat(b.replace('Z', '+00:00')).timestamp())
        try:
            res = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={t0}&period2={t1}&interval=1m')['chart']['result'][0]
            q = res['indicators']['quote'][0]
            for i, ts in enumerate(res.get('timestamp') or []):
                if q['close'][i] is not None:
                    rows.append([datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), q['low'][i], q['high'][i], q['close'][i]])
        except Exception as e:
            rows.append(['error', str(e)[:200]])
    out[sym] = rows
    print(sym, len(rows), rows[:2], rows[-2:])
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'review', 'full-audit-crypto-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M') + '.json')
json.dump(out, open(p, 'w')); print('written', p)
