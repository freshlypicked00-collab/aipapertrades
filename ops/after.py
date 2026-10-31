"""What happened next (owner, Oct 30): the latest price of everything an AI has SOLD (or bought back from a short) in the last
31 days, so the site can show, under each sale, how the price moved afterwards and what keeping it would have meant.

Runs in every rivals check-in (rivals.yml), after px_long.py. Uses the race runner's own feeds (ops/rivals.py quote(): Yahoo
Finance, Cboe options, Polymarket), so a later price is read the same way the fills were. Information only: it never changes
any book, score or grade.

Writes ops/src/after.json:
  {"at": <UTC ISO>, "q": {"<model>|<race>|<holding as the site shows it>": {"px": <price, same units as the trade>, "at": <UTC ISO>}}}
Never raises: a feed problem leaves the last good price in place.
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R                 # noqa: E402  (quote(): the runner's feeds)
from price_audit import feed_for   # noqa: E402  (Claude's holding name -> feed symbol)

SRC = 'ops/src'
OUT = os.path.join(SRC, 'after.json')
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(days=31)
SKIP_EXP = {'Sports', 'AllInSports'}   # bets: their result is the whole story


def when(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def clean(name, exp):   # the holding name the site shows (ops/model_views.py)
    return name[:-4] if exp == 'Crypto' and name.endswith(' USD') else name


def wanted():
    """{site key: (kind, args)} for every sale or buy-back in the last 31 days, all three AIs."""
    out = {}
    try:
        for t in json.load(open(os.path.join(SRC, 'trades.json'))):
            if t.get('action') not in ('Sell', 'Cover') or when(t['at']) < SINCE:
                continue
            name, pf = t.get('holding') or '', t.get('portfolio')
            if not name or name.startswith('Cash') or name == 'US dollar' or pf in SKIP_EXP:
                continue
            f = feed_for(name)
            if f:
                out[f'claude|{pf}|{name}'] = ('yahoo', (f[0], f[1] == 'inv'))
    except Exception as e:
        print('claude trades:', e)
    try:
        r = json.load(open(os.path.join(SRC, 'rivals.json')))
        for t in r.get('trades', []):
            if t.get('action') not in ('Sell', 'Cover') or t.get('experiment') in SKIP_EXP or when(t['at']) < SINCE:
                continue
            if t['experiment'] == 'Currencies' and str(t.get('symbol')).upper() == 'USD':
                continue
            what = clean(t.get('name') or t['symbol'], t['experiment'])
            if t.get('outcome'):
                what = f"{what} ({t['outcome']})"
            out[f"{t['model']}|{t['experiment']}|{what}"] = ('quote', (t['experiment'], t['symbol'], t.get('outcome')))
    except Exception as e:
        print('rival trades:', e)
    return out


def main():
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {}
    q = {k: v for k, v in (old.get('q') or {}).items() if when(v['at']) >= SINCE}
    ok = bad = 0
    for key, (kind, args) in wanted().items():
        try:
            if kind == 'yahoo':
                sym, inv = args
                px = R.yahoo(sym)[0]
                px = 1 / px if inv else px
            else:
                px = R.quote(*args)[0]
            if px and px > 0:
                q[key] = {'px': round(float(px), 8), 'at': NOW.strftime('%Y-%m-%dT%H:%M:%SZ')}
                ok += 1
        except Exception as e:
            bad += 1
            print('after:', key, str(e)[:120])
    json.dump({'at': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'q': q}, open(OUT, 'w'), indent=1, sort_keys=True)
    print(f'after.json: {ok} prices updated, {bad} not available')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('after.py failed:', e)
