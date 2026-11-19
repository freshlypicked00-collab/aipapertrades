"""The result of a sale, for the posts (owner, Nov 19: "sale posts say the result"; Claude and Gemini agreed, ops/review/followups-nov19.json).

A post that closes something (Sold, Bought back, Settled, Expired) gets one more line: the profit or loss on what was closed.
The number is worked out exactly as the Ledger on the site works it out (ops/build_site.py: _annotate_rivals for Gemini, ChatGPT and
Claude's High risk book; _annotate_claude and _claude_realized_fix for Claude's ten races), so the post and the Ledger always agree.
ops/tests/run_tests.py runs both over every sale on record and fails if one cent differs. Where no figure can be had, there is no line.
Nothing here writes to the race's records: every function reads, and works on its own copies."""
import copy
from datetime import datetime

CLOSES = ('Sell', 'Cover', 'Settled', 'Expired')
SYM = {'CAD': 'C$', 'USD': 'US$', 'CNY': '¥'}


def rival_results(trades):
    """[(trade, cost, pnl, part)] for every closing trade in the runner's list: average cost, in the book's own currency
    (the same steps as _annotate_rivals). part is True when some of the position is still held after it."""
    lots, out = {}, []
    for t in sorted(trades, key=lambda t: t['at']):
        a = t['action']
        if a in ('Bet', 'Parlay', 'Won', 'Lost', 'Push', 'Void'):
            continue
        key = (t.get('model'), t['experiment'], f"{t['symbol']}|{t['outcome']}" if t.get('outcome') else t['symbol'])
        L = lots.setdefault(key, {'qty': 0.0, 'cost': 0.0})
        qty, amt = float(t.get('qty') or 0), float(t.get('amount') or 0)
        if a in ('Buy', 'Short'):
            L['qty'] += qty; L['cost'] += amt
        elif a in CLOSES and L['qty'] > 1e-12:
            f = min(1.0, qty / L['qty']) if qty else 1.0
            part = L['cost'] * f
            pnl = (part - amt) if a == 'Cover' else (amt - part)
            L['qty'] -= L['qty'] * f; L['cost'] -= part
            out.append((t, round(part, 2), round(pnl, 2), L['qty'] > 1e-9))
    return out


def for_rival(trades, t):
    """The result of trade t (one of the runner's records), or None. Found by the record itself, else by an identical record."""
    try:
        res = rival_results(trades)
    except Exception:
        return None
    hit = [r for r in res if r[0] is t] or [r for r in res if r[0] == t]
    if len(hit) != 1:
        return None
    _, cost, pnl, part = hit[0]
    return {'pnl': pnl, 'cost': cost, 'part': part, 'cur': t.get('cur') or 'CAD'}


def claude_results(trades, holdings=None):
    """Claude's ten races (ops/src/trades.json): [(row number, cost, pnl, part)] for every closing row, the same steps as
    _annotate_claude and _claude_realized_fix. China is in US$, everything else in C$."""
    rows = copy.deepcopy(trades)
    for i, t in enumerate(rows):
        t['_i'] = i
    lots = {}
    for t in sorted(rows, key=lambda t: datetime.fromisoformat(str(t['at']).replace('Z', '+00:00'))):
        a, china = t['action'], t['portfolio'] == 'China'
        val = float((t.get('usd') if china else t.get('cad')) or 0)
        px = float((t.get('price_local') if china else t.get('price_usd')) or 0)
        units = float(t.get('shares') or t.get('qty') or 0) or ((float(t.get('cny') or 0) if china else val) / px if px else 0)
        L = lots.setdefault((t['portfolio'], t['holding'], 'short' if a in ('Short', 'Cover') else 'long'), {'u': 0.0, 'c': 0.0})
        if a in ('Buy', 'Short'):
            L['u'] += units; L['c'] += val
        elif a in CLOSES and L['u'] > 1e-12:
            f = min(1.0, units / L['u']) if units else 1.0
            part = L['c'] * f
            t['cost'] = round(part, 2); t['pnl'] = round((part - val) if a == 'Cover' else (val - part), 2)
            if t.get('pnl_cad') is not None and not china:
                t['pnl'] = round(float(t['pnl_cad']), 2); t['cost'] = round(val + t['pnl'] if a == 'Cover' else val - t['pnl'], 2)
            if t.get('held_after') is not None and float(t.get('held_after') or 0) <= 1e-12:
                L['u'] = 0.0; L['c'] = 0.0
            else:
                L['u'] -= L['u'] * f; L['c'] -= part
            t['_part'] = (float(t['held_after']) > 1e-9) if t.get('held_after') is not None else L['u'] > 1e-9
    for h in holdings or []:
        rz = h.get('realized_cad')
        if rz is None or h.get('portfolio') == 'China':
            continue
        sales = [t for t in rows if t.get('portfolio') == h.get('portfolio') and t.get('holding') == h.get('holding') and t.get('action') == 'Sell']
        loose = [t for t in sales if t.get('pnl_cad') is None]
        if len(loose) == 1:
            t = loose[0]; others = sum(float(x.get('pnl') or 0) for x in sales if x is not t)
            t['pnl'] = round(float(rz) - others, 2); t['cost'] = round(float(t.get('cad') or 0) - t['pnl'], 2)
    return [(t['_i'], t['cost'], t['pnl'], bool(t.get('_part'))) for t in rows if t.get('pnl') is not None and t['action'] in CLOSES]


def for_claude(trades, holdings, portfolio, holding, action):
    """The result of Claude's newest row for this holding and action (the fill that was just written), or None."""
    try:
        idx = [i for i, t in enumerate(trades) if t.get('portfolio') == portfolio and t.get('holding') == holding and t.get('action') == action]
        if not idx:
            return None
        hit = [r for r in claude_results(trades, holdings) if r[0] == idx[-1]]
        if len(hit) != 1:
            return None
        _, cost, pnl, part = hit[0]
        return {'pnl': pnl, 'cost': cost, 'part': part, 'cur': 'USD' if portfolio == 'China' else 'CAD'}
    except Exception:
        return None


def line(action, res):
    """'Loss on this sale: −C$376.82 (bought for C$15,000)'. The profit to the cent, as the Ledger shows it; '' when there is none."""
    if not res or action not in CLOSES or res.get('pnl') is None:
        return ''
    s = SYM.get(res.get('cur') or 'CAD', 'C$')
    pnl, cost = float(res['pnl']), res.get('cost')
    what = {'Sell': 'sale', 'Cover': 'short'}.get(action, 'position')
    head = (f'Profit on this {what}: +{s}{pnl:,.2f}' if pnl >= 0.005 else f'Loss on this {what}: −{s}{-pnl:,.2f}' if pnl <= -0.005
            else f'Broke even on this {what}: {s}0.00')
    if cost is None or float(cost) <= 0:
        return head
    how = 'sold short for' if action == 'Cover' else 'bought for'
    return f"{head} ({'this part was ' if res.get('part') else ''}{how} {s}{float(cost):,.0f})"
