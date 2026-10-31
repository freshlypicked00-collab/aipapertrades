"""Root cause of the off-market fills (owner, Oct 31: "figure out exactly why that happened"). Read-only: for each fill, the 1-minute
bars of the 3 hours before it, and the last minute whose range contains the fill price (how old the quote the runner used must have
been). Writes ops/review/rootcause-<time>.json."""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades audit; papertrades.ai)'}
FILLS = [('silver stop (Claude)', 'SI=F', '2026-10-30T13:52:17Z', 49.825), ('SQQQ buy (Gemini All in)', 'SQQQ', '2026-10-30T19:44:20Z', 42.795),
         ('USO buy (Claude)', 'USO', '2026-10-30T14:31:56Z', 170.77), ('gold sell (Claude)', 'GC=F', '2026-10-30T18:14:52Z', 3887.7),
         ('QQQ sell (Claude)', 'QQQ', '2026-10-30T18:36:02Z', 684.97)]
def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read())
        except Exception as e:
            err = e; time.sleep(1.5)
    raise err
out = []
for what, sym, at, px in FILLS:
    t = datetime.fromisoformat(at.replace('Z', '+00:00'))
    rec = {'what': what, 'symbol': sym, 'fill_at': at, 'fill_price': px}
    try:
        res = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={int((t - timedelta(hours=3)).timestamp())}&period2={int((t + timedelta(minutes=10)).timestamp())}&interval=1m&includePrePost=true')['chart']['result'][0]
        q = res['indicators']['quote'][0]
        bars = [(datetime.fromtimestamp(ts, timezone.utc), q['low'][i], q['high'][i], q['close'][i]) for i, ts in enumerate(res.get('timestamp') or []) if q['close'][i] is not None]
        before = [b for b in bars if b[0] <= t]
        hit = [b for b in before if b[1] - 1e-9 <= px <= b[2] + 1e-9]
        rec['meta'] = {k: res['meta'].get(k) for k in ('exchangeName', 'exchangeDataDelayedBy', 'dataGranularity', 'priceHint')}
        rec['last_minute_containing_fill'] = hit[-1][0].strftime('%Y-%m-%dT%H:%MZ') if hit else None
        rec['lag_minutes'] = round((t - hit[-1][0]).total_seconds() / 60, 1) if hit else None
        rec['bars_around'] = [(b[0].strftime('%H:%M'), b[1], b[2], b[3]) for b in bars if abs((b[0] - t).total_seconds()) <= 1500]
    except Exception as e:
        rec['error'] = str(e)[:200]
    out.append(rec)
    print(what, rec.get('lag_minutes'), rec.get('last_minute_containing_fill'), rec.get('meta'), rec.get('error', ''))
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'review', 'rootcause-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M') + '.json')
json.dump(out, open(p, 'w'), indent=1); print('written', p)
