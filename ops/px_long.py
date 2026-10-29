"""Long price history (up to 5 years) for every holding the three AIs have right now, for the site's
per-holding price chart: 30 days, 3 months, 1 year and 5 years (owner's request, Oct 29).

Runs in every rivals check-in (rivals.yml); refreshes a symbol at most every 12 hours. Writes
ops/src/px_long.json, which build_site.py copies to the site root as px_long.json (loaded only when
someone opens a long range):
  {"at": ..., "series": {"<yahoo symbol>": {"at": ..., "inv": false, "d": [[unix_minute, close], ...] (1 year, daily),
                                           "w": [[unix_minute, close], ...] (5 years, weekly)}},
   "names": {"claude|SPY": "SPY", "gemini|Invesco S&P 500 Equal Weight ETF": "RSP", ...}}
Prices are in the same units the site uses for that holding (US$ per unit for currencies, yuan for China).
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from price_audit import feed_for, SKIP   # noqa: E402  (Claude's holding name -> feed symbol)

SRC = 'ops/src'
OUT = os.path.join(SRC, 'px_long.json')
NOW = datetime.now(timezone.utc)
UA = {'User-Agent': 'Mozilla/5.0 (paper-trades price history)'}
NO_FEED = ('Options', 'Predictions', 'Sports', 'AllInSports')


def clean(name, exp):   # the same holding name the site shows (ops/model_views.py)
    return name[:-4] if exp == 'Crypto' and name.endswith(' USD') else name


def wanted():
    """{site key 'model|holding name': (yahoo symbol, invert)} for every current holding with a price feed."""
    out = {}
    try:
        for h in json.load(open(os.path.join(SRC, 'holdings.json'))):
            name, pf = h.get('holding'), h.get('portfolio')
            if not name or str(name).startswith('Cash') or name in SKIP or pf in NO_FEED or abs(float(h.get('quantity') or 0)) < 1e-9:
                continue
            f = feed_for(name)
            if f:
                out['claude|' + name] = (f[0], f[1] == 'inv')
    except Exception as e:
        print('claude holdings:', e)
    try:
        r = json.load(open(os.path.join(SRC, 'rivals.json')))
        for mid, m in (r.get('models') or {}).items():
            for exp, b in (m.get('books') or {}).items():
                if exp in NO_FEED:
                    continue
                for key, p in (b.get('positions') or {}).items():
                    sym = key.split('|')[0]
                    if exp == 'AllInTrading' and re.match(r'^[A-Z]{1,6}\d{6}[CP]\d{8}$', sym):
                        continue   # options: no long history
                    ys = f'{sym.upper()}USD=X' if exp == 'Currencies' else sym
                    out[f"{mid}|{clean(p.get('name') or key, exp)}"] = (ys, False)
    except Exception as e:
        print('rivals:', e)
    return out


def fetch(sym, rng, interval):
    u = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range={rng}&interval={interval}'
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as f:
        j = json.loads(f.read())['chart']['result'][0]
    ts, cl = j.get('timestamp') or [], (j['indicators']['quote'][0].get('close') or [])
    return [[int(t // 60), c] for t, c in zip(ts, cl) if c is not None]


def main():
    old = {}
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT))
        except Exception:
            old = {}
    series = old.get('series') or {}
    want = wanted()
    syms = {v for v in want.values()}
    changed = False
    for sym, inv in sorted(syms):
        s = series.get(sym)
        if s and NOW - datetime.fromisoformat(s['at']) < timedelta(hours=12):
            continue
        try:
            d, w = fetch(sym, '1y', '1d'), fetch(sym, '5y', '1wk')
            if inv:   # the feed quotes units per US$; the site uses US$ per unit
                d = [[t, 1 / c] for t, c in d if c]
                w = [[t, 1 / c] for t, c in w if c]
            sig = lambda x: round(x, 6 if x < 1 else 4)
            series[sym] = {'at': NOW.isoformat(), 'd': [[t, sig(c)] for t, c in d], 'w': [[t, sig(c)] for t, c in w]}
            changed = True
        except Exception as e:
            print(f'{sym}: {e}')
    keep = {v[0] for v in want.values()}
    for sym in list(series):   # drop symbols nobody holds any more
        if sym not in keep:
            series.pop(sym); changed = True
    names = {k: v[0] for k, v in want.items()}
    if changed or names != old.get('names'):
        json.dump({'at': NOW.isoformat(), 'series': series, 'names': names}, open(OUT, 'w'), separators=(',', ':'))
        print(f'px_long: {len(series)} symbols, {len(names)} holdings')
    else:
        print('px_long: nothing to refresh')


if __name__ == '__main__':
    main()
