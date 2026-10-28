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
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

STATE = 'ops/src/rivals.json'
EXPS = ['Stocks', 'Crypto', 'Predictions']
EXP_LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'Predictions': 'Prediction markets'}
START_CAD = 100000.0
MAX_ORDERS = 8
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades price check)'}
SITE = 'https://papertrades.ai'
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def iso(t=None):
    return (t or NOW).isoformat().replace('+00:00', 'Z')


def get_json(url, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------------- prices ----------------
_cache = {}


def yahoo(symbol):
    """Last trade price in the quote's own currency, plus the currency."""
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
        except Exception as e:
            err = e
    raise ValueError(f'no price for {symbol}')


def usdcad():
    return yahoo('CAD=X')[0]


def poly(slug):
    j = get_json(f'https://gamma-api.polymarket.com/markets?slug={urllib.parse.quote(slug)}', timeout=20)
    if not j:
        raise ValueError(f'no Polymarket market {slug}')
    m = j[0]
    outs = json.loads(m['outcomes']) if isinstance(m['outcomes'], str) else m['outcomes']
    prices = json.loads(m['outcomePrices']) if isinstance(m['outcomePrices'], str) else m['outcomePrices']
    return {'question': m.get('question', slug), 'closed': bool(m.get('closed')), 'active': bool(m.get('active')),
            'prices': {o: float(p) for o, p in zip(outs, prices)}}


def price_usd(exp, symbol, outcome=None):
    """Price in US$ per unit (shares, coins, or prediction shares paying US$1)."""
    if exp == 'Predictions':
        m = poly(symbol)
        if outcome not in m['prices']:
            raise ValueError(f'{symbol} has no outcome {outcome!r} (has {list(m["prices"])})')
        return m['prices'][outcome], m
    px, cur, name = yahoo(symbol)
    if cur != 'USD':
        raise ValueError(f'{symbol} is priced in {cur}; only US$ listings are allowed')
    if exp == 'Crypto' and not symbol.endswith('-USD'):
        raise ValueError('crypto symbols look like BTC-USD')
    if exp == 'Stocks' and symbol.endswith('-USD'):
        raise ValueError('crypto belongs in the Crypto experiment')
    return px, {'name': name}


# ---------------- state ----------------
def new_book():
    return {'cash_cad': START_CAD, 'positions': {}}


def load_state():
    try:
        return json.load(open(STATE))
    except FileNotFoundError:
        return {'models': {}, 'trades': [], 'history': [], 'takes': []}


def pos_key(symbol, outcome):
    return f'{symbol}|{outcome}' if outcome else symbol


def value_book(exp, book, fx, notes):
    total = book['cash_cad']
    for key, p in book['positions'].items():
        sym, _, outcome = key.partition('|')
        try:
            px, _ = price_usd(exp, sym, outcome or None)
            p['last_usd'] = px
            p['priced_at'] = iso()
        except Exception as e:
            notes.append(f'kept last price for {key}: {e}')
        total += p['qty'] * p.get('last_usd', p['entry_usd']) * fx
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
    want = os.environ.get('GEMINI_MODEL')
    if want:
        return want
    ms = get_json(f'https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200')['models']
    names = [m['name'].split('/')[-1] for m in ms if 'generateContent' in m.get('supportedGenerationMethods', [])]
    pro = [n for n in names if re.fullmatch(r'gemini-\d+(\.\d+)?-pro(-preview(-[\d-]+)?)?', n)]
    def rank(n):
        v = float(re.match(r'gemini-(\d+(?:\.\d+)?)', n).group(1))
        return (v, 'preview' not in n)
    return max(pro, key=rank) if pro else 'gemini-2.5-pro'


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
    'gemini': {'label': 'Gemini', 'company': 'Google', 'env': 'GEMINI_API_KEY', 'pick': pick_gemini, 'ask': ask_gemini},
    'chatgpt': {'label': 'ChatGPT', 'company': 'OpenAI', 'env': 'OPENAI_API_KEY', 'pick': pick_openai, 'ask': ask_openai},
}


def build_prompt(label, books, values, fx, recent):
    lines = [
        f'You are {label}, taking part in Paper Trades (papertrades.ai), a public paper-trading experiment that compares AI models.',
        f'It is now {NOW.astimezone(timezone(timedelta(hours=-4))).strftime("%A %b %-d, %Y, %-I:%M %p")} ET ({iso()}).',
        'You run three SEPARATE experiments, each started with its own C$100,000 of pretend money. Each is judged only against its own start; they are never added together. The experiment ends Nov 26, 2026 at 4:00 p.m. ET.',
        'Goal: high risk, high reward. Try to finish each experiment with as much money as possible. Holding is allowed; trade only when you have a reason.',
        '',
        'Rules:',
        '- Stocks: any US-listed stock or ETF priced in US$ (including leveraged ETFs), Yahoo Finance symbols like NVDA, SOXL, SPY. Long only, no margin, no options.',
        '- Crypto: Yahoo Finance crypto symbols ending in -USD, like BTC-USD, ETH-USD, SOL-USD. Long only.',
        '- Predictions: Polymarket markets, named by their URL slug (the part after polymarket.com/event/... or /market/...), buying "Yes" or "No" shares that pay US$1 if right. A market must be open. Resolved markets are settled automatically.',
        f'- Prices are converted to C$ at USD/CAD {fx:.4f}. Fills are at the live price when this run executes. No fees. You cannot spend more cash than you have.',
        '- Use web search to check news and current prices before deciding.',
        '',
        'Your portfolios now:',
    ]
    for exp in EXPS:
        b = books[exp]
        lines.append(f'{EXP_LABEL[exp]}: value C${values[exp]:,.0f}, cash C${b["cash_cad"]:,.0f}')
        for key, p in b['positions'].items():
            lines.append(f'  - {key}: {p["qty"]:,.4f} units, bought at US${p["entry_usd"]:,.4f}, now US${p.get("last_usd", p["entry_usd"]):,.4f}')
    if recent:
        lines.append('\nYour recent trades:')
        lines += [f'  - {t["at"]} {t["experiment"]} {t["action"]} {t["symbol"]}{" " + t["outcome"] if t.get("outcome") else ""}: {t["reason"]}' for t in recent[-8:]]
    lines += [
        '',
        'Reply with ONLY one JSON object, no other text, in this form:',
        '{"take": "one sentence on how you are doing and what you are thinking",',
        ' "orders": [{"experiment": "Stocks" | "Crypto" | "Predictions", "action": "buy" | "sell", "symbol": "NVDA" | "BTC-USD" | "polymarket-slug",',
        '             "outcome": "Yes" | "No" (Predictions only), "amount_cad": 25000 (buy: C$ to spend), "fraction": 1.0 (sell: share of the position, 0 to 1),',
        '             "reason": "one plain sentence"}]}',
        f'Use an empty orders list to hold. At most {MAX_ORDERS} orders.',
    ]
    return '\n'.join(lines)


def parse_reply(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        raise ValueError('no JSON in reply')
    return json.loads(m.group(0))


def execute(model_id, label, books, order, fx, state, notes):
    exp = order.get('experiment')
    if exp not in EXPS:
        raise ValueError(f'unknown experiment {exp!r}')
    book = books[exp]
    sym = str(order.get('symbol', '')).strip()
    outcome = order.get('outcome') if exp == 'Predictions' else None
    if exp != 'Predictions':
        sym = sym.upper()
    key = pos_key(sym, outcome)
    action = str(order.get('action', '')).lower()
    if action == 'sell' and key not in book['positions']:
        raise ValueError(f'no {key} position to sell')
    px, info = price_usd(exp, sym, outcome)
    if exp == 'Predictions' and (info['closed'] or not info['active']):
        raise ValueError(f'{sym} is closed')
    if action == 'buy':
        amt = min(float(order.get('amount_cad', 0)), book['cash_cad'])
        if amt < 1 or px <= 0:
            raise ValueError('nothing to buy (no cash or zero price)')
        qty = amt / fx / px
        p = book['positions'].get(key)
        if p:
            p['entry_usd'] = (p['entry_usd'] * p['qty'] + px * qty) / (p['qty'] + qty)
            p['qty'] += qty
        else:
            book['positions'][key] = {'qty': qty, 'entry_usd': px, 'name': info.get('name') or info.get('question', sym)}
        book['positions'][key]['last_usd'] = px
        book['cash_cad'] -= amt
        cad = amt
    elif action == 'sell':
        p = book['positions'].get(key)
        if not p:
            raise ValueError(f'no {key} position to sell')
        frac = max(0.0, min(1.0, float(order.get('fraction', 1))))
        qty = p['qty'] * frac
        cad = qty * px * fx
        p['qty'] -= qty
        book['cash_cad'] += cad
        if p['qty'] < 1e-9 or frac >= 0.999:
            book['positions'].pop(key)
    else:
        raise ValueError(f'unknown action {action!r}')
    t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': action.capitalize(), 'symbol': sym, 'outcome': outcome,
         'name': (info.get('name') or info.get('question') or sym), 'price_usd': px, 'qty': qty, 'cad': round(cad, 2), 'usdcad': fx,
         'reason': str(order.get('reason', ''))[:400]}
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
            cad = p['qty'] * px * fx
            book['cash_cad'] += cad
            t = {'at': iso(), 'model': model_id, 'experiment': 'Predictions', 'action': 'Settled', 'symbol': sym, 'outcome': outcome,
                 'name': m['question'], 'price_usd': px, 'qty': p['qty'], 'cad': round(cad, 2), 'usdcad': fx,
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


def tg_trade(label, t, source=None):
    icon = {'Buy': '🟢', 'Sell': '🔴', 'Settled': '🏁'}.get(t['action'], '•')
    what = f"{t['symbol']} {t['outcome']}" if t.get('outcome') else t['symbol']
    px = f"{t['price_usd'] * 100:.1f}¢ a share" if t['experiment'] == 'Predictions' else f"US${t['price_usd']:,.4f}".rstrip('0').rstrip('.')
    msg = (f"{icon} <b>{label} · {EXP_LABEL[t['experiment']]}: {t['action']} {esc(what)}</b>\n{esc(t['name'])}\n{px}, C${t['cad']:,.0f}\n"
           f"<i>{esc(t['reason'])}</i>")
    if source:
        msg += f"\nSource: <a href=\"{esc(source['url'])}\">{esc(source['title'][:80])}</a>"
    tg(msg + f'\n⚔️ Head to head: Claude vs Gemini vs ChatGPT · {SITE}')


# ---------------- main ----------------
def main():
    if '--prices' in sys.argv:
        fx = usdcad()
        print('USDCAD', fx)
        for s in ('NVDA', 'SOXL', 'BTC-USD', 'ETH-USD'):
            print(s, yahoo(s))
        j = get_json('https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=1&order=volume24hr&ascending=false', timeout=20)
        print('polymarket', j[0]['slug'], poly(j[0]['slug']))
        return
    state = load_state()
    fx = usdcad()
    ran = []
    for mid, r in RIVALS.items():
        key = os.environ.get(r['env'])
        if not key:
            continue
        m = state['models'].setdefault(mid, {'label': r['label'], 'company': r['company'], 'started_at': iso(),
                                              'books': {e: new_book() for e in EXPS}})
        notes = []
        for t in settle_predictions(mid, m['books']['Predictions'], fx, state):
            tg_trade(r['label'], t)
        values = {e: value_book(e, m['books'][e], fx, notes) for e in EXPS}
        status, take, sources, made = 'ok', None, [], []
        try:
            model = r['pick'](key)
            m['model'] = model
            recent = [t for t in state['trades'] if t['model'] == mid]
            text, sources = r['ask'](key, model, build_prompt(r['label'], m['books'], values, fx, recent))
            reply = parse_reply(text)
            take = str(reply.get('take', ''))[:300] or None
            for o in (reply.get('orders') or [])[:MAX_ORDERS]:
                try:
                    made.append(execute(mid, r['label'], m['books'], o, fx, state, notes))
                except Exception as e:
                    notes.append(f'order refused ({o.get("experiment")} {o.get("action")} {o.get("symbol")}): {e}')
        except Exception as e:
            status = f'error: {e}'[:300]
            print(r['label'], status)
        values = {e: value_book(e, m['books'][e], fx, notes) for e in EXPS}
        for e in EXPS:
            state['history'].append({'at': iso(), 'model': mid, 'experiment': e, 'value': values[e]})
        if take:
            last = next((x for x in reversed(state['takes']) if x['model'] == mid), None)
            if not last or last['text'] != take:
                state['takes'].append({'at': iso(), 'model': mid, 'text': take})
        m['last_run'] = {'at': iso(), 'status': status, 'notes': notes[-12:], 'sources': sources[:8], 'orders': len(made)}
        for t in made:
            tg_trade(r['label'], t, sources[0] if sources else None)
        ran.append(f"{r['label']} ({m.get('model')}): {status}, {len(made)} trade(s), " + ', '.join(f'{e} C${values[e]:,.0f}' for e in EXPS))
    if not ran:
        print('no rival API keys set; nothing to do')
        return
    json.dump(state, open(STATE, 'w'), indent=1)
    print('\n'.join(ran))


if __name__ == '__main__':
    main()
