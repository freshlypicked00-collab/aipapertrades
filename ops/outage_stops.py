"""ChatGPT's two SQQQ stops that filled 51 hours late (GitHub started no run from Sat Nov 21, 12:14 p.m. ET to Mon Nov 23, 3:12 p.m. ET).

READ-ONLY. It works out what the remedy all three AIs asked the owner for would come to (ops/review/stops-nov23.json, Nov 23):
each fill restated at the 1-minute price of the first scheduled check-in after its stop was crossed, as a cash correction, the way
the Oct 31 fills were restated (ops/src/price_corrections.json). Nothing in the race changes here: it prints the numbers, and the
owner decides. Run by the price-feed test (python3 ops/rivals.py --prices), which never touches the books.

The rule it follows:
  - a US-listed stop can only fill while the US market is open, so the first chance was the scheduled run at the open, 9:35 a.m. ET;
  - at each scheduled run the runner compares the live price with the level; the price it would have seen is taken as the close of
    the Yahoo 1-minute bar of that minute (the same bar the automatic fill check uses);
  - the first scheduled run at which that price is at or below the level is where the stop would have filled, at that price;
  - correction for a sell, in the book's currency: amount * (bar / fill - 1), amount being the fill's own book amount.
"""
import urllib.parse
from datetime import datetime, timedelta, timezone

DAY = '2026-11-23'
FILL_AT = '2026-11-23T20:16:06Z'
FILL_PRICE = 45.61
FILLS = [   # (stop id, race, level, shares sold, the fill's own amount in the book's currency, currency)
    ('chatgpt-224', 'Stocks', 56.2, 95.54959946624458, 6262.91, 'CAD'),
    ('chatgpt-225', 'AllInTrading', 55.9, 238.87399866561145, 15657.28, 'CAD'),
]


def scheduled_minutes():
    """Every run .github/workflows/rivals.yml had scheduled on Mon Nov 23 while the US market was open (14:30 to 21:00 UTC), in
    order: the open check-in (35 14), the hourly (13 *), the half-hourly (43 13-20), the close ones (5 20,21) and the stops-only
    runs (8,23,38,53 13-21)."""
    out = set()
    for h in range(14, 21):
        for m in (5, 8, 13, 23, 35, 38, 43, 53):
            if m == 35 and h != 14:
                continue
            if m == 5 and h != 20:
                continue
            t = datetime.fromisoformat(f'{DAY}T{h:02d}:{m:02d}:00+00:00')
            if datetime.fromisoformat(f'{DAY}T14:30:00+00:00') <= t < datetime.fromisoformat(f'{DAY}T21:00:00+00:00'):
                out.add(t)
    return sorted(out)


def plan(bars):
    """bars: {minute start (epoch seconds): close}. Returns one dict per fill: where its stop would have filled and the correction."""
    out = []
    for sid, race, level, qty, amount, cur in FILLS:
        hit = None
        for t in scheduled_minutes():
            c = bars.get(int(t.timestamp()))
            if c is not None and c <= level:
                hit = (t, float(c))
                break
        row = {'stop': sid, 'race': race, 'level': level, 'qty': qty, 'fill_at': FILL_AT, 'fill_price': FILL_PRICE, 'amount': amount, 'currency': cur}
        if hit:
            row.update(bar_minute=hit[0].strftime('%Y-%m-%dT%H:%MZ'), bar_price=round(hit[1], 8), correction=round(amount * (hit[1] / FILL_PRICE - 1), 2))
        out.append(row)
    return out


def report(get_json):
    t0 = int(datetime.fromisoformat(f'{DAY}T14:25:00+00:00').timestamp())
    t1 = int(datetime.fromisoformat(f'{DAY}T21:05:00+00:00').timestamp())
    res = get_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote("SQQQ")}?period1={t0}&period2={t1}&interval=1m', timeout=30)['chart']['result'][0]
    cl = res['indicators']['quote'][0].get('close') or []
    bars = {int(ts) - int(ts) % 60: c for ts, c in zip(res.get('timestamp') or [], cl) if c is not None}
    print(f'outage stops (read-only): {len(bars)} one-minute bars of SQQQ for {DAY}')
    et = timezone(timedelta(hours=-5))
    for t in scheduled_minutes()[:6]:
        print(f'  scheduled run {t.astimezone(et).strftime("%-I:%M %p ET")}: SQQQ {bars.get(int(t.timestamp()))}')
    for r in plan(bars):
        if 'bar_price' in r:
            when = datetime.fromisoformat(r['bar_minute'].replace('Z', ':00+00:00')).astimezone(et).strftime('%-I:%M %p ET')
            print(f"outage stops: {r['stop']} ({r['race']}, stop at {r['level']}) would have filled at the {when} run at {r['bar_price']:.4f} "
                  f"instead of {r['fill_price']} at 3:16 p.m. ET; correction {'+' if r['correction'] >= 0 else '-'}C${abs(r['correction']):,.2f} on a fill of C${r['amount']:,.2f}")
        else:
            print(f"outage stops: {r['stop']} ({r['race']}): the price was never at or below {r['level']} at a scheduled run; nothing to restate")
    return bars
