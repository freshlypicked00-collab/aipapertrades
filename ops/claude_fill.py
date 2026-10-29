"""Option B (agreed by Claude, Gemini and ChatGPT; the owner's go, Oct 29, 2026): Claude's orders are filled by the same code as
Gemini's and ChatGPT's, at the same feed prices, at the moment the race runner sees them. Claude no longer records its own fills.

  Claude's session        ops/orders.py queue '{...}'  ->  ops/src/claude_orders.json, push, dispatch rivals.yml mode=fill
  The race runner         process(): Claude's books in the engine's format (from ops/src/holdings.json and bets.json), every
                          pending order through rivals.execute / rivals.place_bet (market hours, caps, leverage, lots, betting
                          limits, live price), Claude's crossed stops and targets, settlement and closing odds of the bets it placed
                          -> one ops/update.py input in /tmp (BATCH)
  Publish (rivals.yml)    apply(): ops/update.py applies the batch to the LATEST ops/src (so nothing Claude pushed meanwhile is
                          lost); an order that no longer fits is refused there; then post() sends the fills to Telegram.

Results: rivals.json "claude_main" (done ids, results). `python3 ops/orders.py status` shows them.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R  # noqa: E402
import stops as S  # noqa: E402

SRC = 'ops/src'
QUEUE = os.path.join(SRC, 'claude_orders.json')
BATCH = os.environ.get('CLAUDE_FILL_BATCH', '/tmp/claude_fill_batch.json')
POSTS = os.environ.get('CLAUDE_FILL_POSTS', '/tmp/claude_fill_posts.json')


def cutover():
    """The moment option B was switched on (ops/src/option_b.json); None = not switched on."""
    try:
        return datetime.fromisoformat(json.load(open(os.path.join(SRC, 'option_b.json')))['cutover'])
    except Exception:
        return None
MAIN = list(R.ALL_EXPS)
CODE_OF = {v: k for k, v in R.FX_NAMES.items()}   # 'Japanese yen' -> 'JPY'
NAMED = {'Bitcoin': 'BTC-USD', 'Ethereum': 'ETH-USD', 'Solana': 'SOL-USD', 'XRP': 'XRP-USD', 'Dogecoin': 'DOGE-USD',
         'Gold': 'GC=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 'Palladium': 'PA=F', 'Copper': 'HG=F'}
NAME_OF = {v: k for k, v in NAMED.items()}
FEED = {'Options': 'Cboe (15-min delayed)', 'Predictions': 'Polymarket', 'Sports': 'ESPN'}


def _j(name, default):
    try:
        return json.load(open(os.path.join(SRC, name + '.json')))
    except Exception:
        return default


def et_now():
    return R.NOW.astimezone(R.NY).isoformat(timespec='seconds')


def china_sym(code):
    code = str(code).strip()
    return code + ('.SS' if code[:1] in '569' else '.SZ')


def resolve_pred(holding, cm):
    """Claude's prediction holdings were named by hand: find the Polymarket market slug once and remember it."""
    codes = cm.setdefault('codes', {})
    if holding in codes:
        return codes[holding]
    try:
        import price_audit as PA
        slug, word, outcome = PA.PRED[holding]
        ev = R.get_json(f'https://gamma-api.polymarket.com/events?slug={slug}', timeout=20)
        for m in (ev[0].get('markets') if ev else []) or []:
            if word in (str(m.get('groupItemTitle', '')) + ' ' + str(m.get('question', ''))).lower():
                codes[holding] = f"{m['slug']}|{outcome}"
                return codes[holding]
    except Exception as e:
        print('prediction market lookup failed for', holding, e)
    return None


def sym_of(exp, row, cm):
    h = str(row['holding'])
    if row.get('code') and exp in ('Options', 'Predictions'):
        return row['code']
    if exp == 'China':
        return china_sym(row['code']) if row.get('code') else None
    if exp == 'Currencies':
        return CODE_OF.get(h)
    if exp == 'Predictions':
        return resolve_pred(h, cm)
    if h in NAMED:
        return NAMED[h]
    if re.fullmatch(r'[A-Z][A-Z0-9.\-=^]{0,11}', h):
        return h
    return None


def claude_books(state, fx, cm):
    """Claude's ten experiments in the engine's book format, plus {(experiment, key): holding name}."""
    H, B, T = _j('holdings', []), _j('bets', []), _j('trades', [])
    pens = state.get('claude_penalties', [])
    books, names = {}, {}
    today_bj = R.NOW.astimezone(R.BJ).date()
    for exp in MAIN:
        cur = R.BOOK_CUR.get(exp, 'CAD')
        b = {'cur': cur, 'cash': 0.0, 'positions': {}}
        if exp == 'Sports':
            b['bets'] = [eng_bet(x) for x in B]
            b['penalties'] = [{'amount': float(x.get('amount') or 0)} for x in pens]
            books[exp] = b
            continue
        for r in [x for x in H if x['portfolio'] == exp]:
            h, q = r['holding'], float(r.get('quantity') or 0)
            if h == 'Cash (CAD)':
                b['cash'] += q if cur == 'CAD' else q / fx['USDCAD']
                continue
            if h == 'USDC':
                b['cash'] += q * fx['USDCAD'] if cur == 'CAD' else q
                continue
            if h == 'Cash (CNY)':
                b['cash'] += q / fx['USDCNY'] if cur == 'USD' else q / fx['USDCNY'] * fx['USDCAD']
                continue
            if h.startswith('Cash') or abs(q) < 1e-12:
                continue
            sym = sym_of(exp, r, cm)
            if not sym:
                b.setdefault('unmapped', []).append(h)
                continue
            key = sym
            pcur = 'CNY' if exp == 'China' else 'USD'
            entry = float((r.get('entry_local') if exp == 'China' else r.get('entry_usd')) or 0)
            last = float((r.get('price_local') if exp == 'China' else r.get('price_usd')) or entry)
            p = {'qty': q, 'entry': entry, 'pcur': pcur, 'name': h, 'last': last,
                 'opened_at': min([t['at'] for t in T if t.get('portfolio') == exp and t.get('holding') == h] or [R.iso()])}
            if exp == 'China':   # T+1: shares bought today (Beijing date) can't be sold until the next trading day
                p['today_qty'] = sum(float(t.get('shares', 0)) for t in T if t.get('portfolio') == 'China' and t.get('holding') == h and t.get('action') == 'Buy'
                                     and datetime.fromisoformat(t['at']).astimezone(R.BJ).date() == today_bj)
                p['today_date'] = today_bj.isoformat()
            b['positions'][key] = p
            names[(exp, key)] = h
        total = b['cash'] + sum(R.to_book(p['qty'] * p['last'], p['pcur'], cur, fx) for p in b['positions'].values())
        if total <= 0 and (b['positions'] or b['cash']):
            b['busted'] = R.iso()
        books[exp] = b
    return books, names


def eng_bet(x):
    """One of Claude's bets (ops/src/bets.json) in the engine's format (for the caps, daily limit and bankroll)."""
    res = x.get('result_cad')
    return {'id': x['bet'], 'game': x.get('game'), 'sport': x.get('espn_sport', ''), 'league': x.get('league', ''), 'short': x.get('sport', ''),
            'event': x.get('event', ''), 'pick': x.get('side', ''), 'pick_team': x.get('pick', ''), 'odds': x.get('odds'),
            'stake': float(x.get('stake_cad') or 0), 'to_win': float(x.get('to_win_cad') or 0), 'starts_at': x.get('starts_at') or (x.get('placed', '') + 'T12:00:00-04:00'),
            'placed_at': x.get('placed_at'), 'status': 'Void' if x.get('status') == 'Void' else x.get('status', 'Open'),
            'result': float(res) if res is not None else 0.0, 'legs': x.get('legs')}


def normalize(o, names):
    """Claude may name a holding the way it is shown ("Bitcoin", "CSI 300 ETF", "Japanese yen") or by its feed symbol."""
    o = dict(o)
    exp = o.get('experiment')
    sym = str(o.get('symbol') or o.get('holding') or '').strip()
    for (e, key), h in names.items():
        if e == exp and sym.lower() in (h.lower(), key.lower()):
            if exp == 'Predictions':
                slug, _, out = key.partition('|')
                o['symbol'], o['outcome'] = slug, o.get('outcome') or out
            else:
                o['symbol'] = key
            return o
    if sym in NAMED and exp in ('Crypto', 'Metals'):
        o['symbol'] = NAMED[sym]
    elif exp == 'China' and re.fullmatch(r'\d{6}', sym):
        o['symbol'] = china_sym(sym)
    elif exp == 'Currencies' and sym in CODE_OF:
        o['symbol'] = CODE_OF[sym]
    else:
        o['symbol'] = sym
    return o


def holding_name(exp, key, t, names):
    if (exp, key) in names:
        return names[(exp, key)]
    sym = t['symbol']
    if exp == 'Currencies':
        return R.FX_NAMES.get(sym, sym)
    if sym in NAME_OF:
        return NAME_OF[sym]
    if exp == 'Predictions':
        return f"{R.clip(t.get('name') or sym, 90)} ({t.get('outcome')})"
    if exp == 'Options':
        return R.option_name(sym)
    if exp == 'China':
        return R.clip(t.get('name') or sym, 60)
    return sym


def funding(exp):
    if exp == 'Crypto' and any(x['portfolio'] == 'Crypto' and x['holding'] == 'USDC' for x in _j('holdings', [])):
        return 'USDC'
    return 'Cash (CAD)'


def next_bet_id():
    n = [int(m.group(1)) for x in _j('bets', []) for m in [re.fullmatch(r'S(\d+)', str(x.get('bet')))] if m]
    return n


def fill_fragment(t, o, names, books, used_ids):
    """The engine's fill as ops/update.py input pieces."""
    exp, act = t['experiment'], t['action']
    at = et_now()
    note = 'Filled by the race runner at the ' + FEED.get(exp, 'Yahoo Finance') + ' price, the same code and feed as Gemini\'s and ChatGPT\'s orders.'
    reason = R.clip(o.get('reason', ''), 600)
    wrong = R.clip(o.get('wrong_if', ''), 300)
    detail = (reason + (' What would prove it wrong: ' + wrong if wrong and act in ('Buy', 'Short', 'Bet') else '') + ' ' + note).strip()
    if exp == 'Sports':
        b = next(x for x in books['Sports']['bets'] if x['id'] == t['bet'])
        ids = used_ids
        sid = f'S{(max(ids) if ids else 0) + 1}'
        ids.append(int(sid[1:]))
        nb = {'bet': sid, 'sport': b['short'], 'event': b['event'], 'pick': (b['pick_team'] + ' moneyline') if not b.get('legs') else t['name'],
              'odds': b['odds'], 'stake_cad': b['stake'], 'starts_at': b['starts_at'], 'market': 'moneyline' if not b.get('legs') else 'parlay',
              'game': b['game'], 'league': b['league'], 'espn_sport': b['sport'], 'side': b['pick'], 'note': reason}
        if b.get('legs'):
            nb['legs'] = b['legs']
        b['id'] = sid   # later orders in the same batch see Claude's own numbering
        t['symbol'] = t['bet'] = sid
        return {'bets_new': [nb], 'log': [{'portfolio': 'Sports', 'action': 'Bet', 'detail': f"Bet C${b['stake']:,.0f} on {nb['pick']} ({b['event']}) at {b['odds']:+d}. " + detail}]}, sid
    key = R.pos_key(t['symbol'], t.get('outcome'))
    name = holding_name(exp, key, t, names)
    names[(exp, key)] = name
    if exp == 'China':
        tr = {'portfolio': 'China', 'holding': name, 'code': t['symbol'].split('.')[0], 'action': act, 'shares': int(round(t['qty'])), 'price': t['price'], 'filled_by': 'race runner, Yahoo Finance'}
    else:
        own = (reason + (' What would prove it wrong: ' + wrong if wrong and act in ('Buy', 'Short') else '')).strip()
        tr = {'portfolio': exp, 'holding': name, 'action': act, 'qty': round(float(t['qty']), 8), 'price': t['price'], 'filled_by': 'race runner, ' + FEED.get(exp, 'Yahoo Finance')}
        if own:
            tr['note'] = own   # Claude's own words: the site shows a trade's note as its "Why"
        if exp in ('Options', 'Predictions') or (name != t['symbol'] and exp not in ('Currencies',) and t['symbol'] not in NAME_OF):
            tr['code'] = key
        if act == 'Buy':
            tr['funding'] = funding(exp)
        elif act == 'Sell':
            tr['to'] = funding(exp)
    words = {'Buy': 'Bought', 'Sell': 'Sold', 'Short': 'Shorted', 'Cover': 'Covered'}[act]
    money = R.money(t['amount'], t['cur'])
    pxs = (f"¥{t['price']:,.3f}" if exp == 'China' else f"{t['price'] * 100:.1f}¢" if exp == 'Predictions' else f"US${t['price']:,.6g}")
    return {'trades': [tr], 'prices': {name: {'price': t['price'], 'source': FEED.get(exp, 'Yahoo Finance') + ' (race runner fill)', 'at': at}},
            'log': [{'portfolio': exp, 'action': act, 'detail': f"{words} {name}: {money} at {pxs}. {detail}"}]}, name


def merge(frags):
    out = {}
    for f in frags:
        for k, v in f.items():
            if isinstance(v, list):
                out.setdefault(k, []).extend(v)
            elif isinstance(v, dict):
                out.setdefault(k, {}).update(v)
    return out


def process(state, fx):
    """Fill Claude's queued orders and crossed stops; settle and close the odds of the bets the runner placed for Claude."""
    c = cutover()
    if not c or R.NOW < c or R.NOW >= R.RACE_END:
        return
    cm = state.setdefault('claude_main', {'done': [], 'results': [], 'codes': {}})
    cm.setdefault('done', []); cm.setdefault('results', []); cm.setdefault('codes', {})
    queue = _j('claude_orders', [])
    pending = [o for o in queue if o.get('id') and o['id'] not in cm['done']]
    books, names = claude_books(state, fx, cm)
    try:
        S.migrate_claude(state, _j('rules', []), fx, books)
    except Exception as e:
        print('stop migration failed', e)
    scratch = {'trades': [], 'bet_ids': {}}
    today = R.et_day(R.iso())
    for t in _j('trades', []):   # Claude's prediction buys today count toward the 25%-a-day limit, like the rivals'
        if t.get('portfolio') == 'Predictions' and t.get('action') == 'Buy' and R.et_day(t['at']) == today:
            scratch['trades'].append({'model': 'claude', 'experiment': 'Predictions', 'action': 'Buy', 'amount': float(t.get('cad') or 0), 'at': t['at']})
    frags, posts, used = [], [], next_bet_id()
    waiting = cm.setdefault('waiting', {})
    for o in pending:
        oid = o['id']
        act = str(o.get('action', '')).lower()
        try:
            if act in S.KINDS:
                txt = S.add(state, 'claude', normalize(o, names), books)
                cm['results'].append(f'{oid}: {txt}')
                cm['done'].append(oid)
                continue
            if act in ('cancel', 'cancel_stop'):
                txt = S.cancel(state, 'claude', o.get('id_to_cancel') or o.get('stop') or o.get('rule'))
                cm['results'].append(f'{oid}: {txt}')
                cm['done'].append(oid)
                continue
            on = normalize(o, names)
            t = R.execute('claude', MAIN, books, on, fx, scratch)
            frag, what = fill_fragment(t, on, names, books, used)
            frags.append({'id': oid, 'frag': frag, 'engine': t})
            cm['results'].append(f"{oid}: filled {t['action']} {what} {R.money(t['amount'], t['cur'])}"
                                 + (f" at {t['price']:+d}" if t['action'] == 'Bet' else f" at {t['price']:,.6g}"))
            cm['done'].append(oid)
            waiting.pop(oid, None)
        except Exception as e:
            msg = str(e)
            if not isinstance(e, ValueError) or msg.startswith('no price for'):   # a feed outage: the order waits for the next run...
                first = (cm.setdefault('waiting_since', {}).setdefault(oid, R.iso()))
                if R.NOW - datetime.fromisoformat(first.replace('Z', '+00:00')) < timedelta(hours=6):
                    waiting[oid] = f'{R.iso()}: waiting ({msg[:160]})'
                    continue
                msg = f'no price from the feed for 6 hours ({msg[:120]}); check the symbol'   # ...but not forever: a wrong symbol is refused
            cm['results'].append(f'{oid}: refused ({msg[:300]})')
            cm['done'].append(oid)
            waiting.pop(oid, None)
            cm.get('waiting_since', {}).pop(oid, None)
    # Claude's stops and targets, the same check as Gemini's and ChatGPT's
    for s, o, px in S.due(state, 'claude', books, fx):
        try:
            on = normalize(o, names)
            t = R.execute('claude', MAIN, books, on, fx, scratch)
            frag, what = fill_fragment(t, on, names, books, used)
            frags.append({'id': s['id'], 'frag': frag, 'engine': t, 'stop': s['id']})
            S.done(state, 'claude', s, f"filled: {t['action']} {what} {R.money(t['amount'], t['cur'])} at {t['price']:,.6g}")
            cm['results'].append(f"{s['id']}: {s['kind']} filled {t['action']} {what} {R.money(t['amount'], t['cur'])} at {t['price']:,.6g}")
        except Exception as e:
            if S.is_closed_market(e):
                print(f'Claude stop {s["id"]} crossed but can\'t fill now ({e}); it waits')
            else:
                S.done(state, 'claude', s, f'not filled: {e}')
    # the bets the runner placed for Claude: closing odds before the start, settlement from the final score (same code as the rivals')
    settle, closing = [], []
    for x in _j('bets', []):
        if x.get('status') != 'Open' or not x.get('game'):
            continue
        eb = eng_bet(x)
        try:
            if not eb.get('legs'):
                g = R.espn_games().get(eb['game'])
                st = datetime.fromisoformat(str(eb['starts_at']).replace('Z', '+00:00'))
                if g and g.get('state') == 'pre' and timedelta(0) < st - R.NOW <= timedelta(minutes=75):
                    ml = g['home_ml'] if eb['pick'] == 'home' else g['away_ml']
                    if ml is not None and ml != x.get('closing_odds'):
                        closing.append({'bet': x['bet'], 'closing_odds': ml, 'closing_line': None})
            tmp = {'bets': [eb]}
            res = R.settle_bets('claude', tmp, scratch, 'Sports')
            if res:
                b2 = tmp['bets'][0]
                settle.append({'bet': x['bet'], 'status': b2['status'], 'result_cad': round(float(b2['result']), 2), 'final': b2.get('final', '')})
                posts.append({**res[0], 'symbol': x['bet'], 'bet': x['bet']})
        except Exception as e:
            print('claude bet check failed', x.get('bet'), e)
    cm['results'] = cm['results'][-60:]
    if not frags and not settle and not closing:
        return
    batch = {'at': et_now(), 'fx': {'usdcad': fx['USDCAD'], 'usdcny': fx['USDCNY'], 'source': 'Yahoo Finance (race runner)', 'at': et_now(),
                                     'cny_source': 'Yahoo Finance (race runner)', 'cny_at': et_now()},
             'fills': frags, 'settle': settle, 'closing': closing, 'posts': posts}
    json.dump(batch, open(BATCH, 'w'), indent=1, default=str)
    print(f'Claude: {len(frags)} fill(s), {len(settle)} settled bet(s), {len(closing)} closing odds for publish')


def _update_input(batch, fills, settle=True):
    inp = merge([f['frag'] for f in fills])
    inp.update({'at': batch['at'], 'fx': batch['fx'], 'runner': True, 'no_ledger_close': True})
    if settle:
        if batch.get('settle'):
            inp['bets_settle'] = [{k: v for k, v in s.items() if k in ('bet', 'status', 'result_cad', 'final')} for s in batch['settle']]
        if batch.get('closing'):
            inp['bets_closing'] = batch['closing']
    return inp


def _run_update(inp):
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(inp, f)
    r = subprocess.run([sys.executable, 'ops/update.py', SRC, path], capture_output=True, text=True)
    os.unlink(path)
    return r.returncode, (r.stdout + r.stderr)[-600:]


def apply(path=BATCH):
    """Apply the batch to the CURRENT ops/src with ops/update.py (all at once; if that fails, one fill at a time, so one
    order that no longer fits is refused without blocking the rest). Updates rivals.json "claude_main" for refusals."""
    if not os.path.exists(path):
        return
    batch = json.load(open(path))
    fills = batch.get('fills') or []
    snap = tempfile.mkdtemp()
    shutil.copytree(SRC, os.path.join(snap, 'src'))
    ok, refused = [], []
    rc, out = _run_update(_update_input(batch, fills))
    if rc == 0:
        ok = fills
    else:
        print('batch did not apply as a whole; applying one at a time:', out)
        shutil.rmtree(SRC); shutil.copytree(os.path.join(snap, 'src'), SRC)
        for f in fills:
            shutil.rmtree(os.path.join(snap, 'one'), ignore_errors=True)
            shutil.copytree(SRC, os.path.join(snap, 'one'))
            rc1, out1 = _run_update(_update_input(batch, [f], settle=False))
            if rc1 == 0:
                ok.append(f)
            else:
                shutil.rmtree(SRC); shutil.copytree(os.path.join(snap, 'one'), SRC)
                refused.append((f, out1.strip().splitlines()[-1] if out1.strip() else 'update failed'))
        if batch.get('settle') or batch.get('closing'):
            rc2, out2 = _run_update(_update_input(batch, [], settle=True))
            if rc2 != 0:
                print('settlement did not apply:', out2)
    if refused:
        st = json.load(open(R.STATE))
        cm = st.setdefault('claude_main', {})
        for f, why in refused:   # replaces its "filled" line
            cm['results'] = [x for x in cm.get('results', []) if not x.startswith(f"{f['id']}: filled") and not x.startswith(f"{f['id']}: stop filled") and not x.startswith(f"{f['id']}: target filled")]
            cm['results'].append(f"{f['id']}: refused at publish ({why[:200]})")
        json.dump(st, open(R.STATE, 'w'), indent=1)
    posts = [f['engine'] for f in ok] + (batch.get('posts') or [])
    json.dump(posts, open(POSTS, 'w'), default=str)
    shutil.rmtree(snap, ignore_errors=True)
    print(f'Claude fills applied: {len(ok)} ok, {len(refused)} refused at publish')


def post(path=POSTS):
    """After the push: each fill and settled bet to Telegram, like the rivals' (All in fills already post this way)."""
    if not os.path.exists(path):
        return
    for t in json.load(open(path)):
        try:
            R.tg_trade('Claude', t)
        except Exception as e:
            print('telegram post failed', e)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'apply':
        apply(sys.argv[2] if len(sys.argv) > 2 else BATCH)
    elif cmd == 'post':
        post(sys.argv[2] if len(sys.argv) > 2 else POSTS)
    else:
        sys.exit('usage: claude_fill.py apply [batch] | post [posts]')
