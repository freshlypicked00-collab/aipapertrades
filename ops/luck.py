"""L1 luck check (critique 2, Oct 31, 2026; Claude, Gemini and ChatGPT all agreed; ops/review/CRITIQUE2_DECISIONS.md).

For each AI and race: where does its result rank among 1,000 random portfolios that took the same kind of risk?
Display only: it never changes a score, a trade or the Nov 28 winner.

Trading races (Stocks, Crypto, China, Metals, Energy, Currencies, Safe): each random portfolio
  - trades the same race's market (a fixed list of liquid symbols, below), over the same dates;
  - is invested only in the hours the AI held something (cash before its first trade and whenever it sold out), and re-picks
    its holdings at exactly the AI's trade times (same number of trades);
  - holds k equal-weight positions (k = how many different holdings the AI traded, at most 4), long only unless the AI shorted;
  - is scaled so its hour-to-hour ups and downs (volatility) over those invested hours equal the AI's, capped at 5x;
  - pays the same costs as Season 1 (none on these races).
  The AI's percentile = the share of random portfolios that ended below it (ties count half), with a 95% band.
Sports: the AI's settled bets replayed 1,000 times, each won with the probability its odds implied (1 / decimal odds, the
bookmaker's margin left in, which slightly favours the random replays). Shows how lucky the results were given the odds taken.
Not yet: Options and Prediction markets (need option price history / enough settled markets), the All in side races, and
matching beta (ChatGPT's and Gemini's fuller definition): listed on the site as next steps.

Run where Yahoo Finance is reachable (GitHub Actions): python3 ops/luck.py   ->   ops/src/luck.json
"""
import hashlib
import json
import math
import os
import random
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'ops', 'src', 'luck.json')
N = 1000
RESTART = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)
UNIVERSE = {
    'Stocks': ['SPY', 'QQQ', 'IWM', 'DIA', 'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AVGO', 'JPM', 'XOM', 'UNH', 'LLY',
               'V', 'MA', 'HD', 'COST', 'WMT', 'BAC', 'NFLX', 'AMD', 'INTC', 'ORCL', 'CRM', 'KO', 'PEP', 'DIS', 'LMT', 'RSP'],
    'Crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'BNB-USD', 'DOGE-USD', 'ADA-USD', 'AVAX-USD', 'LINK-USD', 'LTC-USD'],
    'China': ['510300.SS', '510500.SS', '510050.SS', '588000.SS', '159915.SZ', '512880.SS', '510880.SS', '512100.SS', '159919.SZ', '512480.SS'],
    'Metals': ['GLD', 'SLV', 'GLDM', 'IAU', 'PPLT', 'PALL', 'GDX', 'GDXJ', 'SIL', 'COPX'],
    'Energy': ['XLE', 'USO', 'UNG', 'XOP', 'OIH', 'VDE', 'BNO', 'CVX', 'XOM', 'COP'],
    'Currencies': ['EURUSD=X', 'JPY=X', 'GBPUSD=X', 'AUDUSD=X', 'CAD=X', 'CHF=X', 'NZDUSD=X', 'MXN=X'],
    'Safe': ['BIL', 'SHV', 'SGOV', 'TLT', 'IEF', 'AGG', 'BND', 'GLD'],
}
AIS = ('claude', 'gemini', 'chatgpt')


def ts(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def fetch_hourly(sym):
    """Hourly closes from Yahoo Finance as {hour (UTC, floored): close}."""
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=60m&range=1mo'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (PaperTrades.AI luck check)'})
    j = json.load(urllib.request.urlopen(req, timeout=20))
    r = j['chart']['result'][0]
    out = {}
    for t, c in zip(r.get('timestamp') or [], r['indicators']['quote'][0].get('close') or []):
        if c:
            out[datetime.fromtimestamp(t, timezone.utc).replace(minute=0, second=0, microsecond=0)] = float(c)
    return out


def grid(end):
    t, g = RESTART.replace(minute=0), []
    while t <= end:
        g.append(t)
        t += timedelta(hours=1)
    return g


def ffill(points, g, start=None):
    """points: sorted [(time, value)] -> value at each grid hour (last known; `start` before the first point)."""
    out, i, last = [], 0, start
    for t in g:
        while i < len(points) and points[i][0] <= t + timedelta(minutes=59, seconds=59):
            last = points[i][1]
            i += 1
        out.append(last)
    return out


def rets(series):
    r = []
    for a, b in zip(series, series[1:]):
        r.append((b / a - 1) if a and b else 0.0)
    return r


def std(x):
    if len(x) < 2:
        return 0.0
    m = sum(x) / len(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def pct_rank(sims, x):
    below = sum(1 for s in sims if s < x) + 0.5 * sum(1 for s in sims if s == x)
    p = below / len(sims)
    return round(100 * p, 1), round(100 * 1.96 * math.sqrt(max(p * (1 - p), 1e-9) / len(sims)), 1)


def seed_for(*parts):
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)


def american_to_decimal(o):
    o = float(o)
    return 1 + (o / 100 if o > 0 else 100 / abs(o))


def load():
    data = json.load(open(os.path.join(ROOT, 'data.json')))
    riv = json.load(open(os.path.join(ROOT, 'ops', 'src', 'rivals.json')))
    hist, trades, bets = {}, {}, {}
    for h in data.get('history', []):   # Claude's ten races
        hist.setdefault(('claude', h['portfolio']), []).append((ts(h['at']), float(h['value'])))
    for h in riv.get('history', []):
        if h.get('model') in ('gemini', 'chatgpt'):
            hist.setdefault((h['model'], h['experiment']), []).append((ts(h['at']), float(h['value'])))
    for t in data.get('trades', []):
        if t.get('action') in ('Buy', 'Sell', 'Short', 'Cover') and not str(t.get('holding', '')).startswith('['):
            q = t.get('held_after')
            trades.setdefault(('claude', t['portfolio']), []).append((ts(t['at']), t['action'], t.get('holding'), float(t.get('qty') or t.get('shares') or 0), None if q is None else float(q)))
    for t in riv.get('trades', []):
        if t.get('model') in ('gemini', 'chatgpt') and t.get('action') in ('Buy', 'Sell', 'Short', 'Cover'):
            trades.setdefault((t['model'], t['experiment']), []).append((ts(t['at']), t['action'], t.get('symbol') + ('|' + t['outcome'] if t.get('outcome') else ''), float(t.get('qty') or 0), None))
    bets['claude'] = data.get('bets', [])
    for m in ('gemini', 'chatgpt'):
        bets[m] = (data.get('models', {}).get(m) or {}).get('bets', [])
    return hist, trades, bets


def trading(hist, trades, prices, now):
    g = grid(now)
    out = {}
    for race, syms in UNIVERSE.items():
        mats = {s: ffill(sorted(prices[s].items()), g) for s in syms if prices.get(s)}
        uni = [s for s, col in mats.items() if sum(1 for v in col if v) > len(g) * 0.3]   # enough data to use
        ur = {s: rets([v if v else None for v in mats[s]]) for s in uni}
        for ai in AIS:
            key = (ai, race)
            pts = sorted(p for p in hist.get(key, []) if p[0] >= RESTART - timedelta(minutes=5))
            tr = sorted(t for t in trades.get(key, []) if t[0] >= RESTART - timedelta(minutes=1))
            rec = {'n_trades': len(tr)}
            if not pts or not tr or len(uni) < 3:
                rec['status'] = 'no trades yet' if not tr else 'not enough data'
                out.setdefault(race, {})[ai] = rec
                continue
            v = ffill(pts, g, start=100000.0)
            ai_total = v[-1] / 100000.0 - 1
            ai_r = rets(v)
            # which hours the AI held anything: positions tracked from its own trades (held_after when recorded, else quantities;
            # a sale without a quantity closes the holding)
            held, inv = {}, [False] * (len(g) - 1)
            marks = []
            for t in tr:
                a, key, q, after = t[1], t[2], t[3], t[4]
                if after is not None:
                    held[key] = after
                elif a in ('Buy', 'Short'):
                    held[key] = held.get(key, 0) + (q or 1)
                else:
                    held[key] = max(0.0, held.get(key, 0) - q) if q else 0.0
                    if held[key] < 1e-9:
                        held[key] = 0.0
                marks.append((min(len(g) - 1, max(0, int((t[0] - g[0]).total_seconds() // 3600))), any(x > 1e-9 for x in held.values())))
            for j, (h0, on) in enumerate(marks):
                h1 = marks[j + 1][0] if j + 1 < len(marks) else len(g) - 1
                for h in range(h0, h1):
                    inv[h] = on
            ih = [h for h in range(len(g) - 1) if inv[h]]
            vol = std([ai_r[h] for h in ih]) if len(ih) > 1 else 0.0
            rec['invested_hours'] = len(ih)
            rec.update({'ai_return': round(ai_total, 5), 'ai_vol_hourly': round(vol, 6)})
            if vol == 0:
                rec['status'] = 'no ups and downs to compare (cash)'
                out.setdefault(race, {})[ai] = rec
                continue
            k = max(1, min(4, len({t[2] for t in tr})))
            shorts = any(t[1] == 'Short' for t in tr)
            idx = sorted({min(len(g) - 1, max(0, int((t[0] - g[0]).total_seconds() // 3600))) for t in tr})
            rng = random.Random(seed_for(race, ai, now.date().isoformat()))
            sims, scales = [], []
            for _ in range(N):
                sr = [0.0] * (len(g) - 1)
                for j, start in enumerate(idx):
                    stop = idx[j + 1] if j + 1 < len(idx) else len(g) - 1
                    pick = rng.sample(uni, min(k, len(uni)))
                    sg = [(-1 if shorts and rng.random() < 0.5 else 1) for _ in pick]
                    for h in range(start, stop):
                        if inv[h]:   # cash whenever the AI was in cash
                            sr[h] = sum(s * ur[p][h] for p, s in zip(pick, sg)) / len(pick)
                sv = std([sr[h] for h in ih])
                sc = min(5.0, vol / sv) if sv > 0 else 0.0
                scales.append(sc)
                tot = 1.0
                for x in sr:
                    tot *= max(0.0, 1 + sc * x)
                sims.append(tot - 1)
            p, band = pct_rank(sims, ai_total)
            ss = sorted(sims)
            rec.update({'status': 'ok', 'percentile': p, 'band': band, 'k': k, 'shorts_allowed': shorts, 'universe': uni,
                        'random_median': round(ss[len(ss) // 2], 5), 'random_p10': round(ss[len(ss) // 10], 5), 'random_p90': round(ss[9 * len(ss) // 10], 5),
                        'capped_share': round(sum(1 for s in scales if s >= 5.0) / len(scales), 3)})
            out.setdefault(race, {})[ai] = rec
    return out


def sports(bets, now):
    out = {}
    for ai in AIS:
        settled = [b for b in bets.get(ai, []) if b.get('status') in ('Won', 'Lost') and b.get('odds') is not None]
        rec = {'n_bets': len(settled)}
        if len(settled) < 3:
            rec['status'] = 'fewer than 3 settled bets'
            out[ai] = rec
            continue
        actual = sum(float(b.get('result_cad') or 0) for b in settled)
        rng = random.Random(seed_for('Sports', ai, now.date().isoformat()))
        sims = []
        for _ in range(N):
            pl = 0.0
            for b in settled:
                d, st = american_to_decimal(b['odds']), float(b.get('stake_cad') or 0)
                pl += st * (d - 1) if rng.random() < 1 / d else -st
            sims.append(pl)
        p, band = pct_rank(sims, actual)
        ss = sorted(sims)
        rec.update({'status': 'ok', 'percentile': p, 'band': band, 'actual_cad': round(actual, 2), 'random_median_cad': round(ss[len(ss) // 2], 2)})
        out[ai] = rec
    return out


def main(prices=None, now=None):
    now = now or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hist, trades, bets = load()
    if prices is None:
        prices, missing = {}, []
        for s in sorted({s for v in UNIVERSE.values() for s in v}):
            try:
                prices[s] = fetch_hourly(s)
            except Exception as e:
                missing.append(s)
                print('no prices for', s, str(e)[:80])
    else:
        missing = []
    res = {'at': now.isoformat().replace('+00:00', 'Z'), 'n': N, 'method': 'ops/luck.py (see the docstring); display only',
           'races': trading(hist, trades, prices, now), 'sports': sports(bets, now), 'missing_symbols': missing}
    json.dump(res, open(OUT, 'w'), indent=1)
    print('wrote', OUT)
    return res


if __name__ == '__main__':
    main()
