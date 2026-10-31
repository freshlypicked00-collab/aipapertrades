"""Root cause, all fills (owner, Oct 31): for every Yahoo-priced fill since the restart (all three AIs, runner fills only), how old the
quote the runner used must have been = minutes since the last 1-minute bar whose range contains the fill price. Also the cache headers
Yahoo sends for the exact URL the runner uses. Read-only; writes ops/review/rootcause-all-<time>.json."""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades audit; papertrades.ai)'}
HERE = os.path.dirname(os.path.abspath(__file__))
def get(url, headers=False):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                body = json.loads(r.read())
                return (body, dict(r.headers)) if headers else body
        except Exception as e:
            err = e; time.sleep(1.5)
    raise err
R = json.load(open(os.path.join(HERE, 'src', 'rivals.json')))
FX = {'JPY': 'JPY=X', 'EUR': 'EURUSD=X', 'AUD': 'AUDUSD=X', 'GBP': 'GBPUSD=X', 'CAD': 'CAD=X', 'CHF': 'CHF=X', 'MXN': 'MXN=X'}
fills = []
for t in R['trades']:
    if t['at'] < '2026-10-28T17:45' or t.get('action') not in ('Buy', 'Sell', 'Short', 'Cover') or t.get('experiment') in ('Predictions', 'Options'):
        continue
    sym = t.get('symbol') or ''
    if len(sym) > 12:   # option symbols
        continue
    inv = False
    if t.get('experiment') == 'Currencies':
        if sym == 'USD': continue
        ys = sym + 'USD=X' if sym not in ('JPY', 'CAD', 'CHF', 'MXN') else FX[sym]; inv = sym in ('JPY', 'CAD', 'CHF', 'MXN')
    else:
        ys = sym
    fills.append((t['model'], t['experiment'], t['at'], t['action'], sym, ys, float(t['price']), inv))
for t in json.load(open(os.path.join(HERE, 'src', 'trades.json'))):
    if t.get('filled_by', '').startswith('race runner'):
        m = {'Silver': 'SI=F', 'Gold': 'GC=F', 'Bitcoin': 'BTC-USD'}.get(t['holding'], t['holding'])
        fills.append(('claude', t['portfolio'], datetime.fromisoformat(t['at']).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), t['action'], t['holding'], m, float(t['price_usd']), False))
cache = {}
def bars(ys, t):
    day = t.strftime('%Y-%m-%d')
    if (ys, day) not in cache:
        d0 = datetime(t.year, t.month, t.day, tzinfo=timezone.utc) - timedelta(hours=6); d1 = d0 + timedelta(hours=36)
        try:
            res = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ys)}?period1={int(d0.timestamp())}&period2={int(d1.timestamp())}&interval=1m&includePrePost=true')['chart']['result'][0]
            q = res['indicators']['quote'][0]
            cache[(ys, day)] = [(datetime.fromtimestamp(ts, timezone.utc), q['low'][i], q['high'][i]) for i, ts in enumerate(res.get('timestamp') or []) if q['low'][i] is not None]
        except Exception as e:
            cache[(ys, day)] = []
    return cache[(ys, day)]
rows = []
for who, race, at, act, sym, ys, px, inv in fills:
    t = datetime.fromisoformat(at.replace('Z', '+00:00'))
    b = [x for x in bars(ys, t) if x[0] <= t and x[0] >= t - timedelta(hours=20)]
    p = 1 / px if inv else px
    hit = [x for x in b if x[1] * 0.99995 <= p <= x[2] * 1.00005]
    lag = round((t - hit[-1][0]).total_seconds() / 60, 1) if hit else None
    rows.append({'model': who, 'race': race, 'at': at, 'action': act, 'symbol': sym, 'feed': ys, 'price': px, 'lag_min': lag, 'bars': len(b)})
    print(who, race, at, act, sym, px, 'lag', lag)
hdr = {}
try:
    _, h1 = get('https://query1.finance.yahoo.com/v8/finance/chart/SQQQ?range=1d&interval=5m', True)
    hdr = {k: v for k, v in h1.items() if k.lower() in ('age', 'cache-control', 'x-cache', 'date', 'expires', 'last-modified', 'via', 'x-yahoo-request-id', 'server-timing')}
except Exception as e:
    hdr = {'error': str(e)[:200]}
print('headers', hdr)
p = os.path.join(HERE, 'review', 'rootcause-all-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M') + '.json')
json.dump({'headers': hdr, 'rows': rows}, open(p, 'w'), indent=1); print('written', p)
