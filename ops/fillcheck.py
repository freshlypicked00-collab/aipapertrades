"""R3 of the root-cause vote (Oct 31; Claude, Gemini and ChatGPT all agreed, ChatGPT's amendment included): the automatic fill check.

About 20 minutes after every fill of every AI that the race runner makes (Gemini's and ChatGPT's trades, every AI's All in trades,
Claude's main-race fills under option B, stops included), the fill is compared with the Yahoo 1-minute bar of its minute:
  - outside that bar's low-high range by more than the tolerance (0.3% stocks, funds, China and futures; 0.4% currencies; 0.75% crypto):
    restated at that bar's close, in either direction, ONCE, as an appended price correction (the original fill is never changed);
    the book's cash moves by the difference; listed in Rules & Audit, hashed in the nightly fingerprint and announced on Telegram;
  - inside the range but priced from a quote older than the age limit (R1): flagged, not corrected;
  - otherwise ok. No bar after 6 hours: no_data (shown, nothing changes).
Correction in the book's currency: buy or cover: amount * (1 - bar / fill); sell or short: amount * (bar / fill - 1).
Options, prediction markets and bets are not covered (no public 1-minute history); every other rule still needs a vote.
"""
import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

import rivals as R

START = datetime(2026, 10, 31, 9, 0, tzinfo=timezone.utc)   # fills from the adoption of the rule on; earlier ones were audited by hand
SETTLE = timedelta(minutes=20)                              # let the minute's bar be published (futures data comes 10 minutes late)
GIVE_UP = timedelta(hours=6)
TOL = {'crypto': 0.0075, 'fx': 0.004, 'other': 0.003}
CLAUDE_MAP = {'Bitcoin': 'BTC-USD', 'Ethereum': 'ETH-USD', 'Solana': 'SOL-USD', 'Gold': 'GC=F', 'Silver': 'SI=F', 'CSI 300 ETF': '510300.SS',
              'SSE Dividend ETF': '510880.SS', 'STAR 50 ETF': '588000.SS', 'Japanese yen': 'JPY=X', 'Euro': 'EUR=X', 'British pound': 'GBP=X',
              'Swiss franc': 'CHF=X', 'Australian dollar': 'AUD=X', 'Mexican peso': 'MXN=X', 'Canadian dollar': 'CAD=X'}
INVERSE = {'JPY=X', 'EUR=X', 'GBP=X', 'CHF=X', 'AUD=X', 'MXN=X', 'CAD=X'}   # quoted as units per US$; fills are US$ per unit


def _t(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def kind(feed):
    return 'crypto' if feed.endswith('-USD') else 'fx' if feed.endswith('=X') else 'other'


def feed_of(model, exp, sym):
    """The Yahoo symbol behind a fill, and whether the feed is inverted. None = not covered (options, predictions, the US dollar)."""
    if exp in ('Predictions', 'Options', 'Sports', 'AllInSports') or R.OCC.match(sym or ''):
        return None
    if model == 'claude' and exp not in ('AllInTrading',):
        f = CLAUDE_MAP.get(sym) or (sym if (sym or '').replace('.', '').replace('-', '').isalnum() and sym.upper() == sym else None)
        return (f, f in INVERSE) if f else None
    if exp == 'Currencies':
        code = sym.upper()
        if code == 'USD':
            return None
        if code in ('JPY', 'CAD', 'CHF', 'MXN', 'CNY', 'HKD', 'INR', 'KRW', 'BRL', 'SGD'):
            return (f'{code}=X', True)
        return (f'{code}USD=X', False)
    return (sym, False)


def minute_bar(feed, t):
    """(open, high, low, close) of the 1-minute bar that contains time t, or None if Yahoo has not published it."""
    t0, t1 = int((t - timedelta(minutes=5)).timestamp()), int((t + timedelta(minutes=5)).timestamp())
    res = R.get_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(feed)}?period1={t0}&period2={t1}&interval=1m&includePrePost=true', timeout=20)['chart']['result'][0]
    q = res['indicators']['quote'][0]
    for i, ts in enumerate(res.get('timestamp') or []):
        if ts <= t.timestamp() < ts + 60 and q['close'][i] is not None:
            return (q['open'][i], q['high'][i], q['low'][i], q['close'][i])
    return None


def candidates(state):
    """Every runner fill since START: (key, model, race, at, action, symbol, price, amount, currency, quote_at, where)."""
    out = []
    for t in state.get('trades', []):
        if t.get('action') not in ('Buy', 'Sell', 'Short', 'Cover') or _t(t['at']) < START:
            continue
        out.append((f"{t['model']}|{t['at']}|{t['experiment']}|{t['action']}|{t['symbol']}", t['model'], t['experiment'], t['at'], t['action'],
                    t['symbol'], float(t['price']), float(t['amount']), t.get('cur') or 'CAD', t.get('quote_at'), 'rivals'))
    try:
        mine = json.load(open('ops/src/trades.json'))
    except Exception:
        mine = []
    for t in mine:
        if not str(t.get('filled_by', '')).startswith('race runner') or _t(t['at']) < START or t.get('action') not in ('Buy', 'Sell', 'Short', 'Cover'):
            continue
        px = t.get('price_usd') if t.get('price_usd') is not None else t.get('price_local')
        amt, cur = (t['cad'], 'CAD') if t.get('cad') is not None else (t.get('usd'), 'USD')
        if px is None or amt is None:
            continue
        out.append((f"claude|{t['at']}|{t['portfolio']}|{t['action']}|{t['holding']}", 'claude', t['portfolio'], t['at'], t['action'], t['holding'],
                    float(px), float(amt), cur, t.get('quote_at'), 'claude'))
    return out


def claude_cash(race, amount, cur, note, state):
    """Apply a correction to Claude's own books (ops/src): the race's cash, a history point with the new total, a Check log entry."""
    H = json.load(open('ops/src/holdings.json'))
    if race == 'China':
        usdcny = float((state.get('fx') or {}).get('USDCNY') or json.load(open('ops/src/fx.json')).get('usdcny'))
        row, delta = next((r for r in H if r['portfolio'] == 'China' and r['holding'] == 'Cash (CNY)'), None), amount * usdcny
    else:
        row, delta = next((r for r in H if r['portfolio'] == race and r['holding'] == 'Cash (CAD)'), None), amount
    if not row:
        raise ValueError(f'no cash row for {race}')
    now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-4 if datetime.now(timezone.utc) < datetime(2026, 11, 1, 6, tzinfo=timezone.utc) else -5))).isoformat(timespec='seconds')
    row['quantity'] = round(row['quantity'] + delta, 2)
    if race == 'China':
        row['value_usd'] = round(row['quantity'] / usdcny, 2)
    else:
        row['value_cad'] = row['cost_cad'] = row['quantity']
    row['as_of'] = now
    json.dump(H, open('ops/src/holdings.json', 'w'), indent=1, ensure_ascii=False)
    total = round(sum(r['value_usd'] if race == 'China' else r['value_cad'] for r in H if r['portfolio'] == race), 2)
    hist = json.load(open('ops/src/history.json'))
    hist.append({'at': now, 'portfolio': race, 'value': total, 'close': False})
    json.dump(hist, open('ops/src/history.json', 'w'), indent=1, ensure_ascii=False)
    log = json.load(open('ops/src/log.json'))
    log.append({'at': now, 'portfolio': race, 'action': 'Check', 'detail': note})
    json.dump(log, open('ops/src/log.json', 'w'), indent=1, ensure_ascii=False)
    return now


def run(state, now=None):
    now = now or datetime.now(timezone.utc)
    checks = state.setdefault('fill_checks', {})
    made = []
    for key, model, race, at, act, sym, px, amt, cur, quote_at, where in candidates(state):
        if key in checks and checks[key]['status'] != 'pending':
            continue
        t = _t(at)
        if now - t < SETTLE:
            continue
        f = feed_of(model, race, sym)
        if not f:
            checks[key] = {'status': 'not_covered', 'at': R.iso()}
            continue
        feed, inv = f
        try:
            bar = minute_bar(feed, t)
        except Exception as e:
            bar = None
            print('fill check: no bars for', feed, str(e)[:80])
        if not bar:
            checks[key] = {'status': 'no_data' if now - t > GIVE_UP else 'pending', 'at': R.iso()}
            continue
        o, hi, lo, cl = bar
        if inv:
            o, hi, lo, cl = 1 / o, 1 / lo, 1 / hi, 1 / cl
        tol = TOL[kind(feed)]
        gap = 0.0 if lo <= px <= hi else ((lo - px) if px < lo else (px - hi)) / px
        rec = {'at': R.iso(), 'feed': feed, 'bar': [round(o, 8), round(hi, 8), round(lo, 8), round(cl, 8)], 'gap_pct': round(gap * 100, 3), 'tolerance_pct': tol * 100}
        age = (t - _t(quote_at)).total_seconds() if quote_at else None
        if gap > tol:
            corr = round(amt * (1 - cl / px) if act in ('Buy', 'Cover') else amt * (cl / px - 1), 2)
            pcs = state.setdefault('price_corrections', [])
            cid = f"AC{sum(1 for c in pcs if str(c.get('id', '')).startswith('AC')) + 1}"
            why = f"automatic fill check: {gap * 100:.2f}% outside the 1-minute range (tolerance {tol * 100:.2f}%)"
            entry = {'id': cid, 'at': R.iso(), 'model': model, 'experiment': race, 'symbol': sym, 'fill_at': at, 'action': act, 'fill_price': px,
                     'bar_price': round(cl, 8), 'bar': rec['bar'], 'bar_minute': t.strftime('%Y-%m-%dT%H:%MZ'), 'amount': corr, 'currency': cur,
                     'why': why, 'source': f'Yahoo Finance 1-minute bars ({feed})', 'auto': True}
            try:
                if where == 'rivals' and model in R.RIVALS:
                    book = state['models'][model]['books'][race]
                    entry['cash_before'] = round(book['cash'], 2); book['cash'] += corr; entry['cash_after'] = round(book['cash'], 2)
                elif where == 'rivals' and model == 'claude':
                    book = state['claude_allin']['books'][race]
                    entry['cash_before'] = round(book['cash'], 2); book['cash'] += corr; entry['cash_after'] = round(book['cash'], 2)
                else:   # Claude's own books live in ops/src: applied in the publish step on the LATEST files (apply_claude), like Claude's fills
                    entry['pending_claude'] = True
                    entry['note'] = (f"Automatic fill check (rule agreed by all three AIs, Oct 31): Claude's {act.lower()} of {sym} at {at} filled at {px:g}, "
                                     f"{gap * 100:.2f}% outside the 1-minute range; restated at that minute's close {cl:.6g}: "
                                     f"{'+' if corr >= 0 else '-'}{'C$' if cur == 'CAD' else 'US$'}{abs(corr):,.2f}. The original fill stays as it was.")
            except Exception as e:
                print('fill check: correction not applied', key, e)
                checks[key] = {**rec, 'status': 'error', 'error': str(e)[:160]}
                continue
            pcs.append(entry)
            checks[key] = {**rec, 'status': 'corrected', 'correction': cid}
            made.append(entry)
        elif age is not None and age > (R.MAX_AGE_FUT if feed.endswith('=F') else R.MAX_AGE):
            checks[key] = {**rec, 'status': 'stale_quote', 'quote_age_s': int(age)}
        else:
            checks[key] = {**rec, 'status': 'ok'}
    if made:
        names = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
        lines = ['⚠️ <b>Automatic price correction</b> (rule agreed by all three AIs, Oct 31)']
        for c in made:
            lines.append(f"{names.get(c['model'], c['model'])}, {R.EXP_LABEL.get(c['experiment'], c['experiment'])}: {c['action']} {c['symbol']} filled at {c['fill_price']:g}, "
                         f"1-minute price {c['bar_price']:.6g}: {'+' if c['amount'] >= 0 else '−'}{'C$' if c['currency'] == 'CAD' else 'US$'}{abs(c['amount']):,.2f}")
        lines.append('The original fills stay in the ledger; details in Rules &amp; Audit on PaperTrades.AI')
        try:
            R.tg('\n'.join(lines))
        except Exception as e:
            print('fill check post failed', e)
    return made


def apply_claude(state_path='ops/src/rivals.json'):
    """Publish step (rivals.yml), on the latest ops/src: apply Claude's pending automatic corrections to Claude's own files."""
    st = json.load(open(state_path))
    n = 0
    for c in st.get('price_corrections', []):
        if c.get('pending_claude'):
            c['at'] = claude_cash(c['experiment'], float(c['amount']), c['currency'], c.get('note', ''), st)
            c.pop('pending_claude', None)
            n += 1
    if n:
        json.dump(st, open(state_path, 'w'), indent=1)
    print('fill check: Claude corrections applied:', n)


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['apply-claude']:
        apply_claude()
