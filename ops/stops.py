"""Stop and target orders, the same for all three AIs (part of "option B", owner's go Oct 29, 2026).

Any AI can leave a standing order on a position it holds:
  - a STOP sells (or covers a short) when the price moves against it to a level,
  - a TARGET sells (or covers) when the price reaches a level in its favour.
At every run of the race runner (every check-in and every Claude fill run) the runner checks every AI's stops and targets
against the same live feed and, when one is crossed, fills it right then at the live price, through the same code as any
other order (rivals.execute). There is no fill "at the level": like a real stop order, it fills at the first price the
runner sees. If the market is closed the stop waits for the next run; if the position is gone the stop is removed.

Gemini and ChatGPT place them in their reply (orders with action "stop" or "target", "level" and "fraction"; "cancel_stop"
with "id"); Claude places them with ops/orders.py. State: rivals.json "stops" {model: [ ... ]} and "stops_log".
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R  # noqa: E402

KINDS = ('stop', 'target')


def _book_pos(books, exp, key):
    b = (books or {}).get(exp) or {}
    return (b.get('positions') or {}).get(key)


def direction(kind, qty):
    """A long's stop is below the price and its target above; a short's the other way round."""
    long_ = qty > 0
    if kind == 'stop':
        return 'below' if long_ else 'above'
    return 'above' if long_ else 'below'


def price_now(stop, fx):
    """The live price the stop watches: its own quote, or a separate rate ("watch", e.g. CAD=X for a US dollar position)."""
    if stop.get('watch'):
        return R.yahoo(stop['watch'])[0]
    px, _, info = R.quote(stop['experiment'], stop['symbol'], stop.get('outcome'))
    return info.get('mid', px) if isinstance(info, dict) and info.get('mid') else px


def crossed(stop, px):
    lvl = float(stop['level'])
    return px <= lvl if stop['direction'] == 'below' else px >= lvl


def add(state, mid, order, books):
    """Validate and store one stop or target. Returns a short result text; raises ValueError when refused."""
    kind = str(order.get('action', '')).lower()
    if kind not in KINDS:
        raise ValueError('a stop order needs action "stop" or "target"')
    exp = order.get('experiment')
    if exp not in R.ALL_EXPS + R.ALLIN or R.BASE.get(exp, exp) == 'Sports':
        raise ValueError(f'stops and targets work in the trading experiments, not {exp!r}')
    sym = str(order.get('symbol', '')).strip()
    outcome = order.get('outcome') if exp == 'Predictions' else None
    if exp != 'Predictions':
        sym = sym.upper()
    key = R.pos_key(sym, outcome)
    p = _book_pos(books, exp, key)
    if not p or abs(float(p.get('qty', 0))) < 1e-12:
        raise ValueError(f'no {key} position in {R.EXP_LABEL.get(exp, exp)} to put a {kind} on')
    try:
        level = float(order.get('level'))
    except (TypeError, ValueError):
        raise ValueError('a stop or target needs a numeric "level" (a price in the quote\'s own units)')
    if level <= 0:
        raise ValueError('the level must be above 0')
    raw = order.get('fraction', 1)
    frac = 1.0 if raw in (None, '') else float(raw)
    if not 0 < frac <= 1:
        raise ValueError('fraction must be above 0 and at most 1 (1 = the whole position)')
    d = direction(kind, float(p['qty']))
    lst = state.setdefault('stops', {}).setdefault(mid, [])
    # one stop and one target per position: a new one replaces the old one of the same kind
    lst[:] = [s for s in lst if not (s['experiment'] == exp and s['symbol'] == sym and s.get('outcome') == outcome and s['kind'] == kind)]
    n = state.setdefault('stop_seq', {}).get(mid, 0) + 1
    state['stop_seq'][mid] = n
    s = {'id': f'{mid}-{n}', 'model': mid, 'experiment': exp, 'symbol': sym, 'outcome': outcome, 'kind': kind, 'direction': d,
         'level': level, 'fraction': frac, 'name': p.get('name', key), 'placed_at': R.iso(), 'reason': R.clip(order.get('reason', ''), 300)}
    if order.get('watch'):
        s['watch'] = str(order['watch'])
    lst.append(s)
    return f"{kind} set: {s['name']} {d} {level:g}" + (f" ({frac:.0%})" if frac < 1 else '') + f" [id {s['id']}]"


def cancel(state, mid, sid):
    lst = state.setdefault('stops', {}).setdefault(mid, [])
    keep = [s for s in lst if s['id'] != str(sid)]
    if len(keep) == len(lst):
        raise ValueError(f'no stop or target with id {sid!r}')
    lst[:] = keep
    return f'cancelled {sid}'


def due(state, mid, books, fx):
    """The stops of one AI that are crossed right now, as (stop, order) pairs ready for rivals.execute. Stops whose position is
    gone are removed. A stop whose price can't be read now stays for the next run."""
    lst = state.setdefault('stops', {}).setdefault(mid, [])
    out, keep = [], []
    for s in lst:
        key = R.pos_key(s['symbol'], s.get('outcome'))
        p = _book_pos(books, s['experiment'], key)
        if not p or abs(float(p.get('qty', 0))) < 1e-12:
            _log(state, mid, s, 'removed: the position is no longer held')
            continue
        try:
            px = price_now(s, fx)
        except Exception as e:
            keep.append(s)
            print(f'stop {s["id"]}: no price now ({str(e)[:80]}); kept for the next run')
            continue
        if not crossed(s, px):
            keep.append(s)
            continue
        act = 'sell' if float(p['qty']) > 0 else 'cover'
        what = 'Stop' if s['kind'] == 'stop' else 'Target'
        o = {'experiment': s['experiment'], 'action': act, 'symbol': s['symbol'], 'outcome': s.get('outcome'), 'fraction': s['fraction'],
             'reason': f"{what} order reached: {s['name']} {'fell to' if s['direction'] == 'below' else 'rose to'} {px:,.6g} (level {float(s['level']):,.6g}), "
                       f"filled at the live price by the race runner." + (f" Set because: {s['reason']}" if s.get('reason') else '')}
        out.append((s, o, px))
        keep.append(s)   # removed only once it has filled (see done())
    lst[:] = keep
    return out


def done(state, mid, s, result):
    lst = state.setdefault('stops', {}).setdefault(mid, [])
    lst[:] = [x for x in lst if x['id'] != s['id']]
    _log(state, mid, s, result)


def _log(state, mid, s, result):
    lg = state.setdefault('stops_log', [])
    lg.append({'at': R.iso(), 'model': mid, 'id': s['id'], 'experiment': s['experiment'], 'name': s.get('name'), 'kind': s['kind'],
               'level': s['level'], 'result': R.clip(result, 300)})
    del lg[:-200]


def is_closed_market(msg):
    m = str(msg).lower()
    return any(x in m for x in ('market is closed', 'forex is closed', 'no price for', 'no bid price', 'no ask price'))


def run_rivals(state, fx, books_of, post=None):
    """Check and fill every crossed stop of Gemini and ChatGPT. books_of(mid) -> (exps, books)."""
    made = []
    for mid in [m for m in (state.get('stops') or {}) if m != 'claude']:
        try:
            exps, books = books_of(mid)
        except Exception:
            continue
        for s, o, px in due(state, mid, books, fx):
            try:
                t = R.execute(mid, exps + [e for e in R.ALLIN if e not in exps], books, o, fx, state)
                t['stop'] = s['id']
                done(state, mid, s, f"filled: {t['action']} {t['name']} {R.money(t['amount'], t['cur'])} at {t['price']:,.6g}")
                made.append((mid, t))
                if post:
                    post(mid, t)
            except Exception as e:
                if is_closed_market(e):
                    print(f'stop {s["id"]} crossed but can\'t fill now ({e}); it waits for the next run')
                else:
                    done(state, mid, s, f'not filled: {e}')
    return made


def prompt_lines(state, mid):
    """What the rival sees about its own stops and targets (and what happened to them since its last check-in)."""
    lst = (state.get('stops') or {}).get(mid) or []
    out = ['\nSTOPS AND TARGETS (new, the same for all three AIs, Claude included): you can leave a standing order on any position you hold in a trading experiment. '
           'Order {"experiment": "...", "action": "stop" or "target", "symbol": "the position\'s symbol", "outcome": "Yes"/"No" (Predictions only), "level": price, "fraction": 0 to 1, "reason": "..."}. '
           'A stop sells a long (or covers a short) when the price moves against you to the level; a target does it when the price reaches the level in your favour. '
           'The runner checks every stop and target at every run (each check-in, about every 30 to 60 minutes) against the same live feed as your fills, '
           'and fills a crossed one at the live price it sees then (not at the level). One stop and one target per position: a new one replaces the old. '
           'Cancel one with {"action": "cancel_stop", "id": "..."}. They count toward your order limit.']
    if lst:
        out.append('Your stops and targets now:')
        out += [f"  - {s['id']}: {s['kind']} on {s['symbol']}{' ' + s['outcome'] if s.get('outcome') else ''} ({R.EXP_LABEL.get(s['experiment'], s['experiment'])}), "
                f"{'sell' if s['direction'] == ('below' if s['kind'] == 'stop' else 'above') else 'cover'} {s['fraction']:.0%} when the price is {s['direction']} {s['level']:g}" for s in lst]
    last = (state.get('models', {}).get(mid, {}).get('last_run') or {}).get('at', '')
    hits = [x for x in state.get('stops_log', []) if x['model'] == mid and x['at'] > last]
    if hits:
        out.append('Since your last check-in:')
        out += [f"  - {x['kind']} {x['id']} on {x.get('name')}: {x['result']}" for x in hits[-8:]]
    return out


def migrate_claude(state, rules, fx, books):
    """Once, at the switch: Claude's price rules (ops/src/rules.json) become runner stops, so nothing is left that Claude fills
    itself. Gold and silver levels were set on the spot price; the runner watches COMEX futures (the same feed the price check
    uses), so those levels keep the same distance from the price (scaled by today's futures/spot ratio)."""
    if (state.get('stops_migrated') or {}).get('claude'):
        return []
    made = []
    for r in rules or []:
        try:
            exp = r.get('portfolio')
            rule = str(r.get('rule', ''))
            if exp == 'Currencies' and r.get('asset') is None and re.search(r'cover the us dollar short.*usd/cad rises to ([\d.]+)', rule, re.I):
                lvl = float(re.search(r'rises to ([\d.]+)', rule, re.I).group(1))
                p = _book_pos(books, 'Currencies', 'USD')
                if not p or float(p['qty']) >= 0:
                    continue
                state.setdefault('stops', {}).setdefault('claude', [])
                n = state.setdefault('stop_seq', {}).get('claude', 0) + 1
                state['stop_seq']['claude'] = n
                state['stops']['claude'].append({'id': f'claude-{n}', 'model': 'claude', 'experiment': 'Currencies', 'symbol': 'USD', 'outcome': None,
                                                 'kind': 'stop', 'direction': 'above', 'level': lvl, 'fraction': 1.0, 'name': 'US dollar', 'watch': 'CAD=X',
                                                 'placed_at': R.iso(), 'reason': rule})
                made.append(rule)
                continue
            if not r.get('asset') or r.get('level') is None or r.get('direction') not in ('above', 'below'):
                continue
            yield_pair = _claude_key(exp, r['asset'], books)
            if not yield_pair:
                continue
            key, p = yield_pair
            level = float(r['level'])
            if exp == 'Metals' and str(r['asset']) in ('Gold', 'Silver'):
                fut = R.yahoo('GC=F' if r['asset'] == 'Gold' else 'SI=F')[0]
                spot = float(p.get('last') or 0)
                if spot > 0:
                    level = round(level * fut / spot, 2)
            kind = 'stop' if r['direction'] == direction('stop', float(p['qty'])) else 'target'
            sym, _, out = key.partition('|')
            state.setdefault('stops', {}).setdefault('claude', [])
            n = state.setdefault('stop_seq', {}).get('claude', 0) + 1
            state['stop_seq']['claude'] = n
            state['stops']['claude'].append({'id': f'claude-{n}', 'model': 'claude', 'experiment': exp, 'symbol': sym, 'outcome': out or None,
                                             'kind': kind, 'direction': r['direction'], 'level': level, 'fraction': 1.0, 'name': r['asset'],
                                             'placed_at': R.iso(), 'reason': rule + (f' (level {float(r["level"]):g} on the spot price, {level:g} on the futures the runner watches)' if level != float(r['level']) else '')})
            made.append(rule)
        except Exception as e:
            print('stop migration skipped a rule:', r, e)
    state.setdefault('stops_migrated', {})['claude'] = R.iso()
    return made


def _claude_key(exp, asset, books):
    b = (books or {}).get(exp) or {}
    for key, p in (b.get('positions') or {}).items():
        if str(p.get('name', '')).lower() == str(asset).lower():
            return key, p
    return None
