"""Odds check (owner, Nov 1: "double check the odds on all the website for the All in and sports... are they correct to the real world?").

For every moneyline bet of all three AIs (main Sports and All in: sports), from the Oct 28 restart on, read-only:
  1. ESPN's own record of that game's moneyline (the game summary's betting lines: each provider's opening and closing line),
  2. compare the odds we recorded for the pick with that range.
A line moves during the day, and past minute-by-minute odds are not public, so a bet is:
  ok     - recorded odds lie between ESPN's opening and closing line for that side (any provider ESPN lists)
  close  - outside that range by at most 3 percentage points of implied probability (a normal intraday move)
  flag   - further off than that: to be looked at by hand
  no_data- ESPN lists no line for the game (common for some college games once they are over)
Writes ops/review/odds-audit-<UTC time>.json and a short .md summary. Changes nothing else.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import full_audit as FA

UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades.AI odds check)'}


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            time.sleep(2 + 3 * i)
    raise RuntimeError('fetch failed')


def implied(o):
    o = float(o)
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def num(x):
    try:
        if x in (None, '', 'EVEN', 'even'):
            return 100.0 if x in ('EVEN', 'even') else None
        return float(str(x).replace('+', ''))
    except Exception:
        return None


_lines = {}


def lines(sport, league, gid):
    """[(provider, side, open, close)] from ESPN's game summary."""
    k = (sport, league, str(gid))
    if k in _lines:
        return _lines[k]
    out = []
    try:
        j = get(f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={gid}')
        for pc in (j.get('pickcenter') or []) + (j.get('odds') or []):
            prov = ((pc.get('provider') or {}).get('name')) or '?'
            ml = pc.get('moneyline') or {}
            for side in ('home', 'away'):
                o = num(((ml.get(side) or {}).get('open') or {}).get('odds'))
                c = num(((ml.get(side) or {}).get('close') or {}).get('odds'))
                cur = num((pc.get(f'{side}TeamOdds') or {}).get('moneyLine'))
                opn = num(((pc.get(f'{side}TeamOdds') or {}).get('open') or {}).get('moneyLine'))
                vals = [v for v in (o, c, cur, opn) if v is not None]
                if vals:
                    out.append({'provider': prov, 'side': side, 'open': o if o is not None else opn, 'close': c if c is not None else cur, 'all': vals})
    except Exception as e:
        out = [{'error': str(e)[:100]}]
    _lines[k] = out
    return out


def side_of(b, g):
    """Which side the pick was: 'home' or 'away'."""
    s = str(b.get('side') or '').lower()
    if s in ('home', 'away'):
        return s
    pick = str(b.get('pick') or b.get('side') or '').lower()
    if g.get('home') and g['home'].lower().split()[-1] in pick:
        return 'home'
    if g.get('away') and g['away'].lower().split()[-1] in pick:
        return 'away'
    return None


def main():
    rows, n = [], {'ok': 0, 'close': 0, 'flag': 0, 'no_data': 0, 'skipped': 0}
    for b in FA.all_bets():
        if b.get('legs') or b.get('odds') in (None, ''):
            continue
        if b.get('placed_at') and FA.t(b['placed_at']) < FA.FS:
            continue
        r = {k: b.get(k) for k in ('model', 'race', 'id', 'event', 'pick', 'odds', 'stake', 'status', 'placed_at')}
        if not b.get('game') or not b.get('sport') or not b.get('league'):
            r['status_check'] = 'skipped'; r['note'] = 'no ESPN game id on the record'; n['skipped'] += 1; rows.append(r); continue
        g = FA.espn(b['sport'], b['league'], b['game'])
        sd = side_of(b, g)
        L = [x for x in lines(b['sport'], b['league'], b['game']) if 'error' not in x and x['side'] == sd]
        if not sd or not L:
            r['status_check'] = 'no_data'; r['note'] = 'ESPN lists no moneyline for this game/side'; n['no_data'] += 1; rows.append(r); continue
        rec = float(b['odds']); p = implied(rec)
        best = None
        for x in L:
            ps = [implied(v) for v in x['all']]
            lo, hi = min(ps), max(ps)
            gap = 0.0 if lo - 1e-9 <= p <= hi + 1e-9 else min(abs(p - lo), abs(p - hi))
            if best is None or gap < best[0]:
                best = (gap, x)
        gap, x = best
        st = 'ok' if gap == 0 else 'close' if gap <= 0.03 else 'flag'
        n[st] += 1
        r.update(status_check=st, side=sd, espn_provider=x['provider'], espn_open=x['open'], espn_close=x['close'], espn_seen=x['all'],
                 gap_pct_points=round(gap * 100, 2))
        rows.append(r)
        time.sleep(0.3)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')
    out = {'at': now, 'method': __doc__.split('\n\n')[1] if '\n\n' in __doc__ else '', 'counts': n, 'bets': rows}
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'review'), exist_ok=True)
    p = os.path.join(FA.HERE, 'review', f'odds-audit-{now}.json')
    json.dump(out, open(p, 'w'), indent=1, ensure_ascii=False)
    md = [f'# Odds check {now} UTC', '', 'Counts: ' + ', '.join(f'{k} {v}' for k, v in n.items()), '']
    for r in rows:
        if r.get('status_check') in ('flag', 'no_data', 'skipped'):
            md.append(f"- {r['status_check'].upper()}: {r['model']} {r['race']} {r.get('id')} {r.get('pick')} ({r.get('event')}) at {r.get('odds')}"
                      + (f"; ESPN {r.get('espn_provider')} open {r.get('espn_open')} close {r.get('espn_close')}, off by {r.get('gap_pct_points')} pts" if r.get('espn_provider') else '; ' + r.get('note', '')))
    open(p[:-5] + '.md', 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
