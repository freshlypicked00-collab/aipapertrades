"""Head to head: Gemini and ChatGPT run their own copies of three experiments.

Run hourly by .github/workflows/rivals.yml. For each rival model whose API key is set
(GEMINI_API_KEY, OPENAI_API_KEY) it:
  1. prices that model's holdings with live public data (Yahoo Finance for stocks, ETFs and crypto,
     Polymarket for prediction markets) and settles any resolved prediction markets,
  2. sends the model its portfolio, the rules and the prices, lets it search the web, and asks for orders as JSON,
  3. checks each order, fills it at the live price, and records everything in ops/src/rivals.json,
  4. posts each new trade to Telegram.
Claude's own Stocks, Crypto and Prediction markets experiments are run by the main schedule; this file
only handles the rivals. Every rival starts with C$100,000 per experiment and no fees, like Claude.

Usage: python3 ops/rivals.py            (live)
       python3 ops/rivals.py --prices   (only test the price feeds, change nothing)
"""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

STATE = 'ops/src/rivals.json'
ALL_EXPS = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Predictions']
EXP_LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals',
             'Energy': 'Oil and energy', 'Predictions': 'Prediction markets'}
BOOK_CUR = {'China': 'USD'}  # every other experiment is counted in C$
START = 100000.0
MAX_ORDERS = 10
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades price check)'}
SITE = 'https://papertrades.ai'
NOW = datetime.now(timezone.utc).replace(microsecond=0)
BJ = timezone(timedelta(hours=8))
CUR_SYM = {'CAD': 'C$', 'USD': 'US$', 'CNY': '¥'}


def iso(t=None):
    return (t or NOW).isoformat().replace('+00:00', 'Z')


def get_json(url, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------------- prices ----------------
_cache = {}


def yahoo(symbol):
    """Last trade price in the quote's own currency: (price, currency, name)."""
    if symbol in _cache:
        return _cache[symbol]
    for host in ('query1', 'query2'):
        try:
            j = get_json(f'https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=1d&interval=5m', timeout=20)
            m = j['chart']['result'][0]['meta']
            px = m.get('regularMarketPrice')
            if px:
                _cache[symbol] = (float(px), m.get('currency', 'USD'), m.get('longName') or m.get('shortName') or symbol)
                return _cache[symbol]
        except Exception:
            pass
    raise ValueError(f'no price for {symbol}')


def get_fx():
    return {'USDCAD': yahoo('CAD=X')[0], 'USDCNY': yahoo('CNY=X')[0]}


def to_book(amount, cur, book_cur, fx):
    usd = amount if cur == 'USD' else amount / fx['USDCNY'] if cur == 'CNY' else amount / fx['USDCAD']
    return usd if book_cur == 'USD' else usd * fx['USDCAD']


def poly(slug):
    j = get_json(f'https://gamma-api.polymarket.com/markets?slug={urllib.parse.quote(slug)}', timeout=20)
    if not j:
        raise ValueError(f'no Polymarket market {slug}')
    m = j[0]
    outs = json.loads(m['outcomes']) if isinstance(m['outcomes'], str) else m['outcomes']
    prices = json.loads(m['outcomePrices']) if isinstance(m['outcomePrices'], str) else m['outcomePrices']
    return {'question': m.get('question', slug), 'closed': bool(m.get('closed')), 'active': bool(m.get('active')),
            'prices': {o: float(p) for o, p in zip(outs, prices)}}


def quote(exp, symbol, outcome=None):
    """(price per unit, price currency, info) with the experiment's rules checked."""
    if exp == 'Predictions':
        m = poly(symbol)
        if outcome not in m['prices']:
            raise ValueError(f'{symbol} has no outcome {outcome!r} (has {list(m["prices"])})')
        return m['prices'][outcome], 'USD', {**m, 'name': m['question']}
    px, cur, name = yahoo(symbol)
    if exp == 'China':
        if not re.search(r'\.(SS|SZ)$', symbol) or cur != 'CNY':
            raise ValueError('China stocks must be Shanghai (.SS) or Shenzhen (.SZ) listings priced in yuan')
    else:
        if cur != 'USD':
            raise ValueError(f'{symbol} is priced in {cur}; this experiment uses US$ listings')
        if exp == 'Crypto' and not symbol.endswith('-USD'):
            raise ValueError('crypto symbols look like BTC-USD')
        if exp != 'Crypto' and symbol.endswith('-USD'):
            raise ValueError('crypto belongs in the Crypto experiment')
    return px, cur, {'name': name}


def china_open():
    t = NOW.astimezone(BJ)
    hm = t.hour * 60 + t.minute
    return t.weekday() < 5 and (570 <= hm < 690 or 780 <= hm < 900)


# ---------------- state ----------------
def new_book(exp):
    return {'cur': BOOK_CUR.get(exp, 'CAD'), 'cash': START, 'positions': {}}


def load_state():
    try:
        return json.load(open(STATE))
    except FileNotFoundError:
        return {'models': {}, 'trades': [], 'history': [], 'takes': []}


def pos_key(symbol, outcome):
    return f'{symbol}|{outcome}' if outcome else symbol


def value_book(exp, book, fx, notes):
    total = book['cash']
    for key, p in book['positions'].items():
        sym, _, outcome = key.partition('|')
        try:
            px, cur, _ = quote(exp, sym, outcome or None)
            p['last'] = px
            p['priced_at'] = iso()
        except Exception as e:
            notes.append(f'kept last price for {key}: {e}')
        total += to_book(p['qty'] * p.get('last', p['entry']), p['pcur'], book['cur'], fx)
    return round(total, 2)


# ---------------- models ----------------
def pick_openai(key):
    want = os.environ.get('OPENAI_MODEL')
    if want:
        return want
    ids = [m['id'] for m in get_json('https://api.openai.com/v1/models', {'Authorization': f'Bearer {key}'})['data']]
    flagship = [i for i in ids if re.fullmatch(r'gpt-\d+(\.\d+)?', i)]
    return max(flagship, key=lambda i: [float(x) for x in i[4:].split('.')]) if flagship else 'gpt-5'


def pick_gemini(key):
    """Best models first: newest Pro, then newest Flash (Google's free tier often has no Pro quota)."""
    want = os.environ.get('GEMINI_MODEL')
    ms = get_json(f'https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200')['models']
    names = [m['name'].split('/')[-1] for m in ms if 'generateContent' in m.get('supportedGenerationMethods', [])]
    def rank(n):
        v = float(re.match(r'gemini-(\d+(?:\.\d+)?)', n).group(1))
        return (v, 'preview' not in n)
    out = [want] if want else []
    for tier in ('pro', 'flash'):
        c = [n for n in names if re.fullmatch(r'gemini-\d+(\.\d+)?-' + tier + r'(-preview(-[\d-]+)?)?', n)]
        out += sorted(c, key=rank, reverse=True)[:2]
    return out or ['gemini-2.5-flash']


def ask_openai(key, model, prompt):
    body = {'model': model, 'input': prompt, 'tools': [{'type': 'web_search'}]}
    hdr = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    try:
        j = get_json('https://api.openai.com/v1/responses', hdr, json.dumps(body).encode(), timeout=600)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        body.pop('tools')
        j = get_json('https://api.openai.com/v1/responses', hdr, json.dumps(body).encode(), timeout=600)
    out, sources = [], []
    for item in j.get('output', []):
        for c in item.get('content', []) or []:
            if c.get('type') == 'output_text':
                out.append(c['text'])
                for a in c.get('annotations', []) or []:
                    if a.get('url'):
                        sources.append({'title': a.get('title') or a['url'], 'url': a['url']})
    return '\n'.join(out), sources


def ask_gemini(key, model, prompt):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'tools': [{'google_search': {}}]}
    try:
        j = get_json(url, {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=600)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        body.pop('tools')
        j = get_json(url, {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=600)
    cand = j['candidates'][0]
    text = ''.join(p.get('text', '') for p in cand.get('content', {}).get('parts', []))
    sources = [{'title': c['web'].get('title') or c['web']['uri'], 'url': c['web']['uri']}
               for c in cand.get('groundingMetadata', {}).get('groundingChunks', []) if c.get('web')]
    return text, sources


RIVALS = {
    'gemini': {'label': 'Gemini', 'company': 'Google', 'env': 'GEMINI_API_KEY', 'pick': pick_gemini, 'ask': ask_gemini,
               'exps': ['Stocks', 'Crypto', 'China', 'Metals', 'Energy']},
    'chatgpt': {'label': 'ChatGPT', 'company': 'OpenAI', 'env': 'OPENAI_API_KEY', 'pick': pick_openai, 'ask': ask_openai,
                'exps': ['Stocks', 'Crypto', 'Predictions']},
}

RULES = {
    'Stocks': 'Stocks and anything: any US-listed stock or ETF priced in US$ (leveraged and inverse ETFs allowed), Yahoo Finance symbols like NVDA, SOXL, SPY. Counted in C$.',
    'Crypto': 'Crypto: Yahoo Finance crypto symbols ending in -USD, like BTC-USD, ETH-USD, SOL-USD. Counted in C$.',
    'China': 'China stocks: Shanghai and Shenzhen A-shares and ETFs, Yahoo Finance symbols ending in .SS or .SZ (for example 600519.SS, 588000.SS, 159995.SZ), priced in yuan. Counted in US$ (starts at US$100,000). Buys are rounded down to lots of 100 shares. Shares bought today (Beijing date) cannot be sold until the next trading day (T+1). Orders are only filled while the market is open: 9:30-11:30 and 13:00-15:00 Beijing time on weekdays.',
    'Metals': 'Metals: precious and industrial metals through US$-priced ETFs, miners or futures, Yahoo Finance symbols like GLD, SLV, PPLT, GDX, NUGT, GC=F, SI=F, HG=F. Counted in C$.',
    'Energy': 'Oil and energy: oil, gas and energy through US$-priced ETFs, stocks or futures, Yahoo Finance symbols like USO, XLE, XOM, UNG, GUSH, CL=F, NG=F. Counted in C$.',
    'Predictions': 'Prediction markets: Polymarket markets, named by their URL slug, buying "Yes" or "No" shares that pay US$1 if right. The market must be open; resolved markets settle automatically. Counted in C$.',
}


def money(v, cur):
    return CUR_SYM[cur] + f'{v:,.0f}'


def build_prompt(label, exps, books, values, fx, recent):
    lines = [
        f'You are {label}, taking part in Paper Trades (papertrades.ai), a public paper-trading experiment that compares AI models with pretend money and real prices.',
        f'It is now {NOW.astimezone(timezone(timedelta(hours=-4))).strftime("%A %b %-d, %Y, %-I:%M %p")} ET ({iso()}). Beijing time: {NOW.astimezone(BJ).strftime("%a %-I:%M %p")}.',
        f'You run {len(exps)} SEPARATE experiments, each started with its own 100,000 of pretend money. Each is judged only against its own start; they are never added together. The experiment ends Nov 26, 2026 at 4:00 p.m. ET.',
        'Goal: high risk, high reward. Try to finish each experiment with as much money as possible. Holding is fine; trade when you have a reason.',
        '',
        'Rules (long only, no margin, no fees, you cannot spend more cash than you have; fills are at the live price when this run executes):',
    ]
    lines += ['- ' + RULES[e] for e in exps]
    lines += [f'Exchange rates now: USD/CAD {fx["USDCAD"]:.4f}, USD/CNY {fx["USDCNY"]:.4f}.', 'Use web search to check news and current prices before deciding.', '', 'Your portfolios now:']
    for exp in exps:
        b = books[exp]
        lines.append(f'{EXP_LABEL[exp]}: value {money(values[exp], b["cur"])}, cash {money(b["cash"], b["cur"])}')
        for key, p in b['positions'].items():
            cs = CUR_SYM[p['pcur']]
            lines.append(f'  - {key} ({p.get("name", key)}): {p["qty"]:,.4f} units, average cost {cs}{p["entry"]:,.4f}, now {cs}{p.get("last", p["entry"]):,.4f}')
    if recent:
        lines.append('\nYour recent trades:')
        lines += [f'  - {t["at"]} {t["experiment"]} {t["action"]} {t["symbol"]}{" " + t["outcome"] if t.get("outcome") else ""}: {t["reason"]}' for t in recent[-10:]]
    lines += [
        '',
        'Reply with ONLY one JSON object, no other text, in this form:',
        '{"take": "one sentence on how you are doing and what you are thinking",',
        ' "orders": [{"experiment": ' + ' | '.join(f'"{e}"' for e in exps) + ', "action": "buy" | "sell", "symbol": "Yahoo symbol or Polymarket slug",',
        '             "outcome": "Yes" | "No" (Predictions only), "amount": 25000 (buy: money to spend, in that experiment\'s currency), "fraction": 1.0 (sell: share of the position, 0 to 1),',
        '             "reason": "one plain sentence"}]}',
        f'Use an empty orders list to hold. At most {MAX_ORDERS} orders.',
    ]
    return '\n'.join(lines)


def parse_reply(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        raise ValueError('no JSON in reply')
    return json.loads(m.group(0))


def execute(model_id, exps, books, order, fx, state):
    exp = order.get('experiment')
    if exp not in exps:
        raise ValueError(f'unknown experiment {exp!r}')
    book = books[exp]
    sym = str(order.get('symbol', '')).strip()
    outcome = order.get('outcome') if exp == 'Predictions' else None
    if exp != 'Predictions':
        sym = sym.upper()
    key = pos_key(sym, outcome)
    action = str(order.get('action', '')).lower()
    if action not in ('buy', 'sell'):
        raise ValueError(f'unknown action {action!r}')
    if action == 'sell' and key not in book['positions']:
        raise ValueError(f'no {key} position to sell')
    if exp == 'China' and not china_open():
        raise ValueError('China market is closed; orders fill only during Shanghai/Shenzhen trading hours')
    px, pcur, info = quote(exp, sym, outcome)
    if exp == 'Predictions' and (info['closed'] or not info['active']):
        raise ValueError(f'{sym} is closed')
    unit = to_book(px, pcur, book['cur'], fx)
    today = NOW.astimezone(BJ).date().isoformat()
    if action == 'buy':
        amt = min(float(order.get('amount', order.get('amount_cad', 0)) or 0), book['cash'])
        if amt < 1 or unit <= 0:
            raise ValueError('nothing to buy (no cash or zero price)')
        qty = amt / unit
        if exp == 'China':
            qty = int(qty // 100) * 100
            if qty < 100:
                raise ValueError('less than one lot of 100 shares')
        amt = qty * unit
        p = book['positions'].get(key)
        if p:
            p['entry'] = (p['entry'] * p['qty'] + px * qty) / (p['qty'] + qty)
            p['qty'] += qty
        else:
            p = book['positions'][key] = {'qty': qty, 'entry': px, 'pcur': pcur, 'name': info.get('name', sym), 'opened_at': iso()}
        p['last'] = px
        if exp == 'China':
            p['today_qty'] = (p.get('today_qty', 0) if p.get('today_date') == today else 0) + qty
            p['today_date'] = today
        book['cash'] -= amt
    else:
        p = book['positions'][key]
        frac = max(0.0, min(1.0, float(order.get('fraction', 1) or 1)))
        qty = p['qty'] * frac
        if exp == 'China':
            free = p['qty'] - (p.get('today_qty', 0) if p.get('today_date') == today else 0)
            qty = min(qty, free)
            if qty < p['qty']:
                qty = int(qty // 100) * 100
            if qty <= 0:
                raise ValueError('shares bought today cannot be sold until the next trading day (T+1)')
        amt = qty * unit
        p['qty'] -= qty
        book['cash'] += amt
        if p['qty'] < 1e-9:
            book['positions'].pop(key)
    t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': action.capitalize(), 'symbol': sym, 'outcome': outcome,
         'name': info.get('name', sym), 'price': px, 'pcur': pcur, 'qty': qty, 'amount': round(amt, 2), 'cur': book['cur'],
         'fx': fx, 'reason': str(order.get('reason', ''))[:400]}
    state['trades'].append(t)
    return t


def settle_predictions(model_id, book, fx, state):
    out = []
    for key in list(book['positions']):
        sym, _, outcome = key.partition('|')
        try:
            m = poly(sym)
        except Exception:
            continue
        if m['closed'] and m['prices'].get(outcome) in (0.0, 1.0):
            p = book['positions'].pop(key)
            px = m['prices'][outcome]
            amt = to_book(p['qty'] * px, 'USD', book['cur'], fx)
            book['cash'] += amt
            t = {'at': iso(), 'model': model_id, 'experiment': 'Predictions', 'action': 'Settled', 'symbol': sym, 'outcome': outcome,
                 'name': m['question'], 'price': px, 'pcur': 'USD', 'qty': p['qty'], 'amount': round(amt, 2), 'cur': book['cur'], 'fx': fx,
                 'reason': 'Market resolved ' + ('in its favour, paid US$1 a share.' if px == 1 else 'against it; shares expired worthless.')}
            state['trades'].append(t)
            out.append(t)
    return out


# ---------------- telegram ----------------
def tg(text):
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not (tok and chat):
        print('--- telegram (not sent) ---\n' + text)
        return
    data = urllib.parse.urlencode({'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}).encode()
    try:
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data, timeout=20).read()
    except Exception as e:
        print('telegram failed', e)


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fmt_price(t):
    if t['experiment'] == 'Predictions':
        return f"{t['price'] * 100:.1f}¢ a share"
    unit = ' per coin' if t['experiment'] == 'Crypto' else ' per share' if t['experiment'] in ('Stocks', 'China') else ''
    return CUR_SYM[t['pcur']] + (f"{t['price']:,.2f}" if t['price'] >= 100 else f"{t['price']:,.4f}".rstrip('0').rstrip('.')) + unit


def tg_trade(label, t, source=None):
    icon = {'Buy': '🟢', 'Sell': '🔴', 'Settled': '🏁'}.get(t['action'], '•')
    what = f"{t['symbol']} {t['outcome']}" if t.get('outcome') else t['symbol']
    msg = (f"{icon} <b>{label} · {EXP_LABEL[t['experiment']]}: {t['action']} {esc(what)}</b>\n{esc(t['name'])}\n"
           f"{fmt_price(t)}, {money(t['amount'], t['cur'])}\n<i>{esc(t['reason'])}</i>")
    if source:
        msg += f"\nSource: <a href=\"{esc(source['url'])}\">{esc(source['title'][:80])}</a>"
    tg(msg + f'\n⚔️ AI vs AI: Claude vs Gemini vs ChatGPT · {SITE}')


# ---------------- main ----------------
def main():
    if '--prices' in sys.argv:
        print('fx', get_fx())
        for s_ in ('NVDA', 'GLD', 'CL=F', 'BTC-USD', '588000.SS', '159995.SZ'):
            print(s_, yahoo(s_))
        j = get_json('https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=1&order=volume24hr&ascending=false', timeout=20)
        print('polymarket', j[0]['slug'], poly(j[0]['slug']))
        return
    state = load_state()
    fx = get_fx()
    ran = []
    for mid, r in RIVALS.items():
        key = os.environ.get(r['env'])
        if not key:
            continue
        exps = r['exps']
        m = state['models'].setdefault(mid, {'label': r['label'], 'company': r['company'], 'books': {}, 'started': {}})
        m['exps'] = exps
        for e in exps:
            if e not in m['books']:
                m['books'][e] = new_book(e)
                m['started'][e] = iso()
        notes = []
        if 'Predictions' in exps:
            for t in settle_predictions(mid, m['books']['Predictions'], fx, state):
                tg_trade(r['label'], t)
        values = {e: value_book(e, m['books'][e], fx, notes) for e in exps}
        status, take, sources, made = 'ok', None, [], []
        try:
            picks = r['pick'](key)
            picks = picks if isinstance(picks, list) else [picks]
            recent = [t for t in state['trades'] if t['model'] == mid]
            prompt = build_prompt(r['label'], exps, m['books'], values, fx, recent)
            for i, model in enumerate(picks):
                try:
                    text, sources = r['ask'](key, model, prompt)
                    m['model'] = model
                    break
                except urllib.error.HTTPError as e:
                    notes.append(f'{model}: HTTP {e.code}')
                    if e.code not in (429, 403, 404, 503) or i == len(picks) - 1:
                        raise
            reply = parse_reply(text)
            take = str(reply.get('take', ''))[:300] or None
            for o in (reply.get('orders') or [])[:MAX_ORDERS]:
                try:
                    made.append(execute(mid, exps, m['books'], o, fx, state))
                except Exception as e:
                    notes.append(f'order refused ({o.get("experiment")} {o.get("action")} {o.get("symbol")}): {e}')
        except Exception as e:
            status = f'error: {e}'[:300]
            print(r['label'], status)
        values = {e: value_book(e, m['books'][e], fx, notes) for e in exps}
        for e in exps:
            state['history'].append({'at': iso(), 'model': mid, 'experiment': e, 'value': values[e]})
        if take:
            last = next((x for x in reversed(state['takes']) if x['model'] == mid), None)
            if not last or last['text'] != take:
                state['takes'].append({'at': iso(), 'model': mid, 'text': take})
        m['last_run'] = {'at': iso(), 'status': status, 'notes': notes[-12:], 'sources': sources[:8], 'orders': len(made)}
        for t in made:
            tg_trade(r['label'], t, sources[0] if sources else None)
        ran.append(f"{r['label']} ({m.get('model')}): {status}, {len(made)} trade(s), " + ', '.join(f'{e} {money(values[e], m["books"][e]["cur"])}' for e in exps))
    if not ran:
        print('no rival API keys set; nothing to do')
        return
    json.dump(state, open(STATE, 'w'), indent=1)
    print('\n'.join(ran))


if __name__ == '__main__':
    main()
