"""L2 wrong-if tracker (critique 2, Oct 31, 2026; Claude, Gemini and ChatGPT all agreed; ops/review/CRITIQUE2_DECISIONS.md).

From Oct 31 every buy and short carries "wrong_lvl": {"symbol": ..., "below"|"above": price}, the AI's own measurable "this
would prove me wrong" level. Each night this checks, with hourly price bars, whether that level was crossed while the AI still
held the position, and whether the AI got out (any sale or cover of that holding, including its stop) within 3 hours of the
crossing, about its next two check-ins. "Kept X of Y exit promises". Buys and shorts since the change without a measurable
level count as "untestable". Display only: never part of any score.

Run where Yahoo Finance is reachable (GitHub Actions): python3 ops/wrongif.py   ->   ops/src/wrongif.json
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'ops', 'src', 'wrongif.json')
SINCE = datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc)   # the prompts asked for measurable levels from here on (Oct 31, 10:30 p.m. ET)
GRACE = timedelta(hours=3)


def ts(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def bars(sym, start):
    """Hourly (time, low, high) bars from Yahoo Finance since `start`."""
    p1, p2 = int((start - timedelta(hours=1)).timestamp()), int(datetime.now(timezone.utc).timestamp())
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=60m&period1={p1}&period2={p2}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (PaperTrades.AI wrong-if check)'})
    r = json.load(urllib.request.urlopen(req, timeout=20))['chart']['result'][0]
    q = r['indicators']['quote'][0]
    return [(datetime.fromtimestamp(t, timezone.utc), lo, hi) for t, lo, hi in zip(r.get('timestamp') or [], q.get('low') or [], q.get('high') or []) if lo and hi]


def positions(data):
    """[(ai, key, entry trade, [exit times])]: every buy or short since SINCE, with the later sales/covers of the same holding."""
    out = []
    claude = [t for t in data.get('trades', []) if t.get('action') in ('Buy', 'Sell', 'Short', 'Cover')]
    rivals = [t for t in data.get('rivals_trades', []) if t.get('action') in ('Buy', 'Sell', 'Short', 'Cover')]
    for ai, rows, kf in (('claude', claude, lambda t: (t.get('portfolio'), t.get('holding'))),
                         (None, rivals, lambda t: (t.get('model'), t.get('experiment'), t.get('symbol'), t.get('outcome')))):
        for i, t in enumerate(rows):
            if t['action'] not in ('Buy', 'Short') or ts(t['at']) < SINCE:
                continue
            k = kf(t)
            exits = [ts(x['at']) for x in rows[i + 1:] if kf(x) == k and x['action'] in ('Sell', 'Cover') and ts(x['at']) >= ts(t['at'])]
            out.append((ai or t.get('model'), k, t, exits))
    return out


def main():
    data = json.load(open(os.path.join(ROOT, 'data.json')))
    res = {'at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'since': SINCE.isoformat().replace('+00:00', 'Z'), 'by_ai': {}}
    cache = {}
    for ai, key, t, exits in positions(data):
        a = res['by_ai'].setdefault(ai, {'kept': 0, 'broken': 0, 'pending': 0, 'closed_first': 0, 'untestable': 0, 'items': []})
        lvl = t.get('wrong_lvl')
        item = {'at': t['at'], 'what': t.get('holding') or t.get('name') or t.get('symbol'), 'race': t.get('portfolio') or t.get('experiment'), 'tx': t.get('tx')}
        if not lvl or not lvl.get('symbol'):
            a['untestable'] += 1
            item['result'] = 'untestable'
            a['items'].append(item)
            continue
        item['level'] = lvl
        t0 = ts(t['at'])
        try:
            if lvl['symbol'] not in cache:
                cache[lvl['symbol']] = bars(lvl['symbol'], SINCE)
            b = [x for x in cache[lvl['symbol']] if x[0] >= t0 - timedelta(minutes=59)]
        except Exception as e:
            item['result'] = 'no prices (' + str(e)[:60] + ')'
            a['pending'] += 1
            a['items'].append(item)
            continue
        first_exit = min(exits) if exits else None
        breach = None
        for when, lo, hi in b:
            if first_exit and when > first_exit:
                break
            if ('below' in lvl and lo <= lvl['below']) or ('above' in lvl and hi >= lvl['above']):
                breach = max(when, t0)
                break
        if breach is None:
            k = 'closed_first' if first_exit else 'pending'
            a[k] += 1
            item['result'] = 'closed before the level was reached' if first_exit else 'level not reached yet'
        else:
            item['breach_at'] = breach.isoformat().replace('+00:00', 'Z')
            out = next((x for x in sorted(exits) if x >= breach - timedelta(hours=1)), None)
            if out and out - breach <= GRACE:
                a['kept'] += 1
                item['result'] = 'kept: got out after the level was reached'
            elif datetime.now(timezone.utc) - breach <= GRACE:
                a['pending'] += 1
                item['result'] = 'level just reached'
            else:
                a['broken'] += 1
                item['result'] = 'held on after its own exit level'
        a['items'].append(item)
    for a in res['by_ai'].values():
        a['items'] = a['items'][-30:]
    json.dump(res, open(OUT, 'w'), indent=1)
    print('wrote', OUT, {k: {x: v[x] for x in ('kept', 'broken', 'pending', 'untestable')} for k, v in res['by_ai'].items()})


if __name__ == '__main__':
    main()
