"""Stale-price guard: Claude's new prices are checked BEFORE the site goes live (owner's idea Oct 30; Claude, Gemini and
ChatGPT all agreed: catching a wrong price before it is published beats correcting it afterwards).

Runs in the publish workflow (deploy.yml) on every publish. It looks at the valuation prices Claude wrote in the last
HOLD_MINUTES (ops/src/prices.json) and compares each with the same feed the hourly price check uses (Yahoo 1-minute bars,
Polymarket history), at the time Claude stated, with the same tolerances (1% crypto, 0.5% stocks and currencies,
1.5-2% metals vs futures, 3 cents for prediction markets).

  - Only fresh feed data counts (ChatGPT's condition): bars within 5 minutes of Claude's time. If the feed has nothing that
    recent (market closed, feed late), the price is not held.
  - If a price is outside the tolerance, the publish stops (exit 1): the site keeps the last version, a "Price hold"
    issue is opened for Claude, and Claude's next check-in re-checks the price and runs update.py with the right one.
  - A hold never lasts more than HOLD_MINUTES after Claude's price: after that the site publishes again (so one wrong price
    can never freeze Gemini's and ChatGPT's updates for long) and the hourly price check flags it, with the backup check
    by Gemini and ChatGPT.
It never changes any price, trade or value; it only decides whether this publish goes out now.
"""
import json
import os
import sys
import types
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# price_audit only needs rivals.get_json; a tiny stand-in keeps this job free of the race runner's chart libraries
_r = types.ModuleType('rivals')


def _get_json(url, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0 (PaperTrades price guard)', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.loads(f.read().decode())


_r.get_json = _get_json
sys.modules.setdefault('rivals', _r)
import price_audit as PA  # noqa: E402

HOLD_MINUTES = 90
NOW = datetime.now(timezone.utc)


def main():
    prices = json.load(open(os.path.join(PA.SRC, 'prices.json')))
    fresh = [x for x in prices if x.get('price') is not None and NOW - PA.when(x['at']) <= timedelta(minutes=HOLD_MINUTES)
             and PA.when(x['at']) >= PA.START]
    latest = {}
    for x in fresh:   # only the newest price of each asset counts: once Claude re-checks and writes the right price, the hold lifts
        if x['asset'] not in latest or PA.when(x['at']) >= PA.when(latest[x['asset']]['at']):
            latest[x['asset']] = x
    held = []
    for x in latest.values():
        h, t = x['asset'], PA.when(x['at'])
        if h in PA.SKIP:
            continue
        if h in PA.PRED:
            rg, tol, absolute = PA.poly_range(h, t), 0.03, True
            if rg and 'within 30 minutes' not in rg[2]:
                rg = None
        else:
            f = PA.feed_for(h)
            if not f:
                continue
            sym, how, tol, _ = f
            absolute = False
            near = [b for b in PA.bars(sym, t - timedelta(minutes=30), t + timedelta(minutes=30)) if abs((b[0] - t).total_seconds()) <= 300]
            rg = (min(b[1] for b in near), max(b[2] for b in near), 'bars') if near else None   # fresh bars only
            if rg and how == 'inv':
                rg = (1 / rg[1], 1 / rg[0], rg[2])
        if not rg:
            print(f'::notice::price guard: {h} at {x["at"]}: no fresh feed data, not held')
            continue
        px = float(x['price'])
        lo, hi = rg[0], rg[1]
        gap = 0.0 if lo <= px <= hi else (lo - px if px < lo else px - hi)
        rel = gap if absolute else gap / px
        if rel > tol:
            held.append({'asset': h, 'at': x['at'], 'claude': px, 'feed_low': round(lo, 6), 'feed_high': round(hi, 6),
                         'gap': round(rel * (100 if not absolute else 1), 3), 'unit': 'cents' if absolute else '%',
                         'until': (PA.when(x['at']) + timedelta(minutes=HOLD_MINUTES)).strftime('%Y-%m-%dT%H:%M:%SZ')})
    if not held:
        print(f'::notice::price guard: {len(fresh)} recent Claude prices, none outside the tolerance; publishing')
        return 0
    for h in held:
        print(f"::error::price guard: HOLD {h['asset']} at {h['at']}: Claude {h['claude']} vs feed {h['feed_low']}-{h['feed_high']} "
              f"(off by {h['gap']}{h['unit']}); the site keeps its last version until Claude re-checks it or until {h['until']}")
    open(os.environ.get('GUARD_OUT', '/tmp/price_hold.json'), 'w').write(json.dumps(held, indent=1))
    return 1


if __name__ == '__main__':
    sys.exit(main())
