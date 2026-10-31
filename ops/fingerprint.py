"""Nightly ledger fingerprint (agreed by all three AIs, item 3): a SHA-256 of every trade and bet of all three AIs up to each daily
close (00:00 UTC), published once and never changed, so any later edit to an earlier record shows. The site recomputes it in the
visitor's browser from its own data (Rules & Audit) with the same rules as here; keep the two in step.

Lines (sorted, joined with a newline, UTF-8):
  C|at|race|holding|action|amount cents|price millionths      Claude's trades (ops/src/trades.json)
  B|bet|placed_at|pick|odds|stake cents                       Claude's bets as placed (ops/src/bets.json)
  S|bet|settled_at|status|result cents                        a Claude bet's result, once settled before the close
  R|model|at|race|action|symbol|amount cents|price millionths Gemini's and ChatGPT's trades and bets, and every AI's All in moves
  P|model|at|race|symbol|fill time|amount cents               a price correction of a past fill (full-audit vote V3, from Oct 31)
Numbers are whole units (floor(x * 100 + 0.5) cents, floor(x * 1e6 + 0.5) millionths), the same in Python and in the browser.
Published at the first run 2 hours after the close (late records land first), in rivals.json "fingerprints" and on Telegram.
"""
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone

SRC = 'ops/src'


def _t(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def _s(x):
    return '' if x is None else str(x)


def _c(x):
    return '' if x is None or x == '' else str(math.floor(float(x) * 100 + 0.5))


def _p(x):
    return '' if x is None or x == '' else str(math.floor(float(x) * 1e6 + 0.5))


def corrections(state):
    """Every applied price correction: Gemini's and ChatGPT's from rivals.json, Claude's from ops/src/price_corrections.json."""
    return list(state.get('price_corrections', [])) + [c for c in _j('price_corrections') if c.get('model') == 'claude' and c.get('at')]


def lines(trades, bets, rtrades, close, corr=()):
    out = []
    for c in corr:
        if c.get('at') and _t(c['at']) < close:
            out.append('|'.join(['P', _s(c.get('model')), _s(c['at']), _s(c.get('experiment')), _s(c.get('symbol')), _s(c.get('fill_at')), _c(c.get('amount'))]))
    for t in trades:
        if t.get('at') and _t(t['at']) < close:
            amt = t.get('cad') if t.get('cad') is not None else t.get('usd')
            px = t.get('price_usd') if t.get('price_usd') is not None else t.get('price_local')
            out.append('|'.join(['C', _s(t['at']), _s(t.get('portfolio')), _s(t.get('holding')), _s(t.get('action')), _c(amt), _p(px)]))
    for b in bets:
        if b.get('placed_at') and _t(b['placed_at']) < close:
            out.append('|'.join(['B', _s(b.get('bet')), _s(b['placed_at']), _s(b.get('pick')), _c(b.get('odds')), _c(b.get('stake_cad'))]))
        if b.get('settled_at') and b.get('status') not in ('Open', None) and _t(b['settled_at']) < close:
            out.append('|'.join(['S', _s(b.get('bet')), _s(b['settled_at']), _s(b.get('status')), _c(b.get('result_cad'))]))
    for t in rtrades:
        if t.get('at') and _t(t['at']) < close and (t.get('model') != 'claude' or str(t.get('experiment', '')).startswith('AllIn')):
            out.append('|'.join(['R', _s(t.get('model')), _s(t['at']), _s(t.get('experiment')), _s(t.get('action')), _s(t.get('symbol')), _c(t.get('amount')), _p(t.get('price'))]))
    out.sort()
    return out


def digest(ls):
    return hashlib.sha256('\n'.join(ls).encode('utf-8')).hexdigest()


def _j(name):
    try:
        return json.load(open(os.path.join(SRC, name + '.json')))
    except Exception:
        return []


def maybe_publish(state, now, post=None):
    """At the first run 2 hours or more after a daily close that has no fingerprint yet: compute it, store it, post it."""
    fps = state.setdefault('fingerprints', [])
    have = {f['day'] for f in fps}
    first = datetime(2026, 10, 29, tzinfo=timezone.utc)   # the first full race day closed at 00:00 UTC Oct 29
    close = max(first, (now - timedelta(hours=2)).replace(hour=0, minute=0, second=0, microsecond=0))
    if now < close + timedelta(hours=2) or now > datetime(2026, 12, 1, tzinfo=timezone.utc):
        return None
    day = (close - timedelta(days=1)).date().isoformat()
    if day in have:
        return None
    ls = lines(_j('trades'), _j('bets'), state.get('trades', []), close, corrections(state))
    f = {'day': day, 'close_at': close.strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha256': digest(ls), 'records': len(ls), 'at': now.strftime('%Y-%m-%dT%H:%M:%SZ')}
    try:   # the search source ledger's day file gets its own SHA-256 beside it (all three AIs agreed, Oct 30); the rule above is unchanged
        import searchlog as SL
        h, n = SL.freeze(day, state)
        if h:
            f['search_sha256'], f['search_checkins'] = h, n
    except Exception as e:
        print('search ledger fingerprint failed', e)
    fps.append(f)
    if post:
        try:
            post(f)
        except Exception as e:
            print('fingerprint post failed', e)
    return f


if __name__ == '__main__':
    import sys
    st = json.load(open(os.path.join(SRC, 'rivals.json')))
    for f in st.get('fingerprints', []):
        ls = lines(_j('trades'), _j('bets'), st.get('trades', []), _t(f['close_at']))
        print(f['day'], 'published', f['sha256'][:16], 'now', digest(ls)[:16], 'OK' if digest(ls) == f['sha256'] else 'CHANGED', len(ls), 'records')
