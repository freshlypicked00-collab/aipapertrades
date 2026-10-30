"""PRIVATE Season 2 test (Nov 1 to Nov 28). Owner, Oct 30; Claude, Gemini and ChatGPT all agreed:
  - the three Season 2 levels (Strict, Standard, Unrestricted) run quietly in the background to test the rules and the code;
  - NOT shown on the site or social media, and no effect on Season 1 (state lives in ops/src/s2test.json; ops/ is never published);
  - once a day (Gemini's condition) with a hard spending cap (ChatGPT's condition).
Rules here are the DRAFT limits from the Oct 30 discussions (ops/review/SEASON2_DECISIONS.md); the test exists to find what
breaks before they are final. Version 1 covers stocks, ETFs and crypto; options and sports come later.

Gemini and ChatGPT are asked once a day by this script. Claude writes its orders once a day to
ops/src/s2test_orders_claude.json (RUNBOOK, "Season 2 test"); this script fills all three at the same feed prices.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R  # noqa: E402

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
STATE = os.path.join(SRC, 's2test.json')
CLAUDE_ORDERS = os.path.join(SRC, 's2test_orders_claude.json')
NOW = datetime.now(timezone.utc)
START = datetime(2026, 11, 1, tzinfo=timezone.utc)
END = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)
CAP_CALLS_PER_DAY = 1          # per AI (Gemini's condition: once a day)
CAP_USD_TOTAL = 6.0            # hard cap on what the test may spend on OpenRouter (ChatGPT's condition)
START_CASH = 100000.0          # US$ per level

STRICT_OK = {'SPY', 'VOO', 'IVV', 'VTI', 'SCHB', 'VXUS', 'VEA', 'VWO', 'BND', 'AGG', 'SHY', 'IEF', 'TLT', 'BIL', 'SGOV', 'SCHD', 'VIG', 'DGRO', 'USMV',
             'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'BRK-B', 'JPM', 'V', 'MA', 'JNJ', 'WMT', 'PG', 'XOM', 'UNH', 'HD', 'KO', 'PEP', 'COST', 'ABBV', 'LLY', 'AVGO'}
LEVELS = {
    'strict': {'label': 'Strict', 'cap': 0.10, 'lev': 1.0, 'floor': 0.05,
               'rules': 'Only these broad funds and big companies: ' + ', '.join(sorted(STRICT_OK)) + '. No leverage, no crypto, at most 10% of the account in one holding.'},
    'standard': {'label': 'Standard', 'cap': 0.20, 'lev': 1.5, 'floor': 0.10,
                 'rules': 'Any US-listed stock or ETF (no leveraged or inverse ETFs) plus BTC-USD and ETH-USD. Leverage up to 1.5x (cash may go negative down to -0.5x the account value). At most 20% of the account in one holding.'},
    'unrestricted': {'label': 'Unrestricted', 'cap': 0.35, 'lev': 3.0, 'floor': 0.20,
                     'rules': 'Any US-listed stock or ETF (leveraged and inverse ETFs allowed) and any crypto (Yahoo symbols ending in -USD). Leverage up to 3x (cash may go negative down to -2x the account value). At most 35% of the account in one holding.'},
}
LEV_ETF = re.compile(r'^(TQQQ|SQQQ|SOXL|SOXS|UPRO|SPXU|SPXL|SPXS|TNA|TZA|LABU|LABD|FNGU|FNGD|UVXY|SVXY|NUGT|DUST|JNUG|JDST|GUSH|DRIP|TSLL|NVDL|NVDU|UDOW|SDOW|QLD|QID|SSO|SDS)$')


def load():
    try:
        return json.load(open(STATE))
    except Exception:
        return {'note': 'PRIVATE Season 2 test; not published (ops/ is excluded from the site).', 'books': {}, 'history': [], 'trades': [], 'runs': [], 'spent_usd': 0.0}


def book(st, ai, lv):
    return st['books'].setdefault(ai, {}).setdefault(lv, {'cash': START_CASH, 'pos': {}})


def price(sym):
    return R.yahoo(sym)[0]


def value(b):
    v = b['cash']
    for s, q in b['pos'].items():
        try:
            v += q * price(s)
        except Exception:
            pass
    return v


def allowed(lv, sym):
    crypto = sym.endswith('-USD')
    if lv == 'strict':
        return sym in STRICT_OK
    if lv == 'standard':
        return (sym in ('BTC-USD', 'ETH-USD')) or (not crypto and not LEV_ETF.match(sym))
    return bool(re.fullmatch(r'[A-Z0-9.\-]{1,12}', sym))


def fill(st, ai, lv, o):
    """One order at the feed price; refused or trimmed to the level's limits. Returns a note."""
    b, L = book(st, ai, lv), LEVELS[lv]
    sym, act = str(o.get('symbol', '')).upper().strip(), str(o.get('action', '')).lower()
    if not allowed(lv, sym):
        return f'refused {act} {sym}: not allowed in {L["label"]}'
    if not sym.endswith('-USD') and not R.us_open():
        return f'refused {act} {sym}: US market closed'
    try:
        px = price(sym)
    except Exception:
        return f'refused {act} {sym}: no price'
    eq = value(b)
    if act == 'buy':
        amt = float(o.get('amount') or 0)
        room_lev = eq * L['lev'] - (eq - b['cash'])          # buying power left under the leverage limit
        room_cap = eq * L['cap'] - b['pos'].get(sym, 0) * px  # room left under the one-holding cap
        amt = max(0.0, min(amt, room_lev, room_cap))
        if amt < 100:
            return f'refused buy {sym}: over the {L["label"]} limits'
        q = amt / px
        b['pos'][sym] = b['pos'].get(sym, 0) + q
        b['cash'] -= amt
    elif act == 'sell':
        q0 = b['pos'].get(sym, 0)
        if q0 <= 0:
            return f'refused sell {sym}: not held'
        fr = min(max(float(o.get('fraction', 1) or 1), 0.0), 1.0)
        q, amt = q0 * fr, q0 * fr * px
        b['pos'][sym] = q0 - q
        if b['pos'][sym] < 1e-9:
            b['pos'].pop(sym)
        b['cash'] += amt
    else:
        return f'refused {act}: unknown action'
    st['trades'].append({'at': NOW.isoformat(), 'ai': ai, 'level': lv, 'action': act, 'symbol': sym, 'price': px, 'amount': round(amt, 2),
                         'reason': str(o.get('reason', ''))[:300]})
    return f'{act} {sym} US${amt:,.0f} at {px:g}'


def score(ai, lv, st):
    vals = [START_CASH] + [h['value'] for h in st['history'] if h['ai'] == ai and h['level'] == lv]
    peak, dd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak if peak else 0)
    ret, f = vals[-1] / START_CASH - 1, LEVELS[lv]['floor']
    d = max(dd, f)
    return {'ret_pct': round(ret * 100, 3), 'dd_pct': round(dd * 100, 3), 'score': round(ret / d if ret >= 0 else ret * d / f ** 2, 4)}


def prompt(st, label, ai):
    parts = [f'You are {label}, in a PRIVATE test of the next season of the Paper Trades race (pretend money, real prices). '
             'Nothing here is shown publicly or affects the current race. You manage three separate US$100,000 accounts, one per level, '
             'each with its own rules. Each level is judged on Return / max(worst drop, floor), so steady gains beat lucky moonshots; '
             'raw profit alone wins nothing. You decide once a day. Search the news if you can.', '']
    for lv, L in LEVELS.items():
        b = book(st, ai, lv)
        hold = ', '.join(f'{s} {q:.4g} (~US${q * price(s):,.0f})' for s, q in b['pos'].items()) or 'none'
        parts.append(f'{L["label"].upper()} ({lv}): {L["rules"]} Floor {int(L["floor"] * 100)}%. Value US${value(b):,.0f}; cash US${b["cash"]:,.0f}; holdings: {hold}.')
    parts += ['', 'Reply with ONLY this JSON: {"strict": [orders], "standard": [orders], "unrestricted": [orders], "note": "one sentence"} '
              'where an order is {"action": "buy", "symbol": "SPY", "amount": 10000, "reason": "..."} (amount in US$) or '
              '{"action": "sell", "symbol": "SPY", "fraction": 0.5, "reason": "..."}. Empty lists are fine.']
    return '\n'.join(parts)


def main():
    if NOW < START or NOW > END:
        print('Season 2 test: outside Nov 1 to Nov 28; nothing to do')
        return
    st = load()
    day = NOW.date().isoformat()
    run = {'at': NOW.isoformat(), 'day': day, 'notes': {}}
    for ai, r in R.RIVALS.items():
        if any(x['day'] == day and ai in x['notes'] for x in st['runs']):
            continue   # once a day
        key = os.environ.get(r['env'])
        if not key and ai == 'chatgpt' and os.environ.get('OPENROUTER_API_KEY'):
            key, r = os.environ['OPENROUTER_API_KEY'], {**r, 'pick': R.pick_openrouter, 'ask': R.ask_openrouter}
        if not key:
            continue
        if st.get('spent_usd', 0) >= CAP_USD_TOTAL:
            run['notes'][ai] = [f'skipped: the test spending cap (US${CAP_USD_TOTAL:.0f}) is reached']
            continue
        n0 = len(R.SEARCH_LOG)
        try:
            picks = r['pick'](key)
            text = ''
            for m in (picks if isinstance(picks, list) else [picks])[:CAP_CALLS_PER_DAY + 1]:
                try:
                    text, _ = r['ask'](key, m, prompt(st, r['label'], ai))
                    break
                except Exception as e:
                    print(f'::warning::s2 test: {ai} {m} failed: {str(e)[:120]}')
            j = R.parse_reply(text)
        except Exception as e:
            run['notes'][ai] = [f'no usable reply: {str(e)[:120]}']
            continue
        st['spent_usd'] = round(st.get('spent_usd', 0) + sum(float(x.get('cost_usd') or 0) for x in R.SEARCH_LOG[n0:]), 4)
        run['notes'][ai] = [str(j.get('note', ''))[:300]] + [f'{lv}: ' + fill(st, ai, lv, o) for lv in LEVELS for o in (j.get(lv) or [])[:8]]
    try:
        co = json.load(open(CLAUDE_ORDERS))
        if co.get('for_day') == day and not any(x['day'] == day and 'claude' in x['notes'] for x in st['runs']):
            run['notes']['claude'] = [str(co.get('note', ''))[:300]] + [f'{lv}: ' + fill(st, 'claude', lv, o) for lv in LEVELS for o in (co.get(lv) or [])[:8]]
    except FileNotFoundError:
        pass
    except Exception as e:
        run['notes']['claude'] = [f'orders file unreadable: {str(e)[:120]}']
    for ai in ('claude', 'gemini', 'chatgpt'):
        for lv in LEVELS:
            st['history'].append({'at': NOW.isoformat(), 'ai': ai, 'level': lv, 'value': round(value(book(st, ai, lv)), 2)})
    st['scores'] = {ai: {lv: score(ai, lv, st) for lv in LEVELS} for ai in ('claude', 'gemini', 'chatgpt')}
    st['runs'].append(run)
    json.dump(st, open(STATE, 'w'), indent=1)
    print('::notice::s2 test:', json.dumps(run['notes'])[:800])


if __name__ == '__main__':
    main()
