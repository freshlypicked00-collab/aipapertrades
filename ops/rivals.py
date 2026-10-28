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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgcharts  # noqa: E402

STATE = 'ops/src/rivals.json'
ALL_EXPS = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
ALLIN = ['AllInTrading', 'AllInSports']   # High risk, high reward: no caps, separate, never counted in the race
RACE_EXPS = ALL_EXPS
BASE = {'AllInSports': 'Sports'}
EXP_LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals',
             'Energy': 'Oil and energy', 'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe',
             'Sports': 'Sports', 'Predictions': 'Prediction markets', 'AllInTrading': 'All in: trading', 'AllInSports': 'All in: sports'}
SAFE_OK = {'SGOV', 'BIL', 'SHV', 'SHY', 'VGSH', 'IEF', 'TLT', 'BND', 'AGG', 'VGIT', 'TIP', 'SCHD', 'VIG', 'VYM', 'DVY', 'NOBL',
           'VTI', 'SPY', 'VOO', 'IVV', 'USMV', 'GLD', 'IAU', 'GLDM'}
SAFE_GOLD = {'GLD', 'IAU', 'GLDM'}
FX_NAMES = {'USD': 'US dollar', 'EUR': 'Euro', 'JPY': 'Japanese yen', 'GBP': 'British pound', 'CHF': 'Swiss franc',
            'AUD': 'Australian dollar', 'NZD': 'New Zealand dollar', 'MXN': 'Mexican peso', 'CNY': 'Chinese yuan',
            'HKD': 'Hong Kong dollar', 'SEK': 'Swedish krona', 'NOK': 'Norwegian krone', 'SGD': 'Singapore dollar',
            'INR': 'Indian rupee', 'BRL': 'Brazilian real', 'ZAR': 'South African rand', 'KRW': 'South Korean won', 'TRY': 'Turkish lira'}
FX_LEVERAGE = 4
LEAGUES = [('football', 'nfl', 'NFL'), ('basketball', 'nba', 'NBA'), ('hockey', 'nhl', 'NHL'), ('baseball', 'mlb', 'MLB'),
           ('football', 'college-football', 'NCAAF'), ('basketball', 'mens-college-basketball', 'NCAAB'), ('soccer', 'eng.1', 'EPL')]
BOOK_CUR = {'China': 'USD'}  # every other experiment is counted in C$
START = 100000.0
MAX_ORDERS = 10
MODEL_TIMEOUT = 240   # seconds per model request
MODEL_BUDGET = 540    # seconds per AI per check-in, across all fallbacks
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades price check)'}
SITE = 'https://papertrades.ai'
NOW = datetime.now(timezone.utc).replace(microsecond=0)
BJ = timezone(timedelta(hours=8))
FRESH_START = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)  # 1:45 p.m. ET Oct 28: restart after tuning, all three AIs level
MAX_SHARE = 0.5   # no single holding or currency above 50% of its experiment
MAX_BET = 0.25    # no single sports bet or prediction market above 25%
try:
    from zoneinfo import ZoneInfo
    NY = ZoneInfo('America/New_York')
except Exception:
    NY = timezone(timedelta(hours=-4))
CUR_SYM = {'CAD': 'C$', 'USD': 'US$', 'CNY': '¥'}


def clip(text, n):
    """Never cut mid-sentence: keep the text whole if it fits, else end at the last full sentence (or clause) before n."""
    t = ' '.join(str(text or '').split())
    if len(t) <= n:
        return t
    cut = t[:n]
    ends = [m.end() for m in re.finditer(r'[.!?](?=\s+[A-Z"(])', cut) if not re.search(r'\b(?:a\.m|p\.m|U\.S|e\.g|i\.e|vs|Mr|Dr|St)\.$', cut[:m.end()])]
    if ends and ends[-1] > n * 0.4:
        return cut[:ends[-1]]
    for mark in (';', ':', ','):
        k = cut.rfind(mark)
        if k > n * 0.4:
            return cut[:k].rstrip() + '.'
    return cut[:cut.rfind(' ')].rstrip(' ,;:') + '.'


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
    if exp == 'Currencies':
        code = symbol.upper()
        if code not in FX_NAMES:
            raise ValueError(f'unknown currency {symbol!r}; use a code like ' + ', '.join(list(FX_NAMES)[:8]))
        if code == 'USD':
            return 1.0, 'USD', {'name': FX_NAMES[code]}
        px, cur, _ = yahoo(f'{code}USD=X')
        if cur != 'USD':
            raise ValueError(f'no US$ rate for {code}')
        return px, 'USD', {'name': FX_NAMES[code]}
    if exp == 'Options' or (exp == 'AllInTrading' and OCC.match(symbol)):
        o = option_quote(symbol)
        return o['mid'], 'USD', o
    px, cur, name = yahoo(symbol)
    if exp == 'AllInTrading':
        if cur != 'USD':
            raise ValueError(f'{symbol} is priced in {cur}; All in: trading uses US$ listings, crypto (-USD) or options')
        return px, cur, {'name': name}
    if exp == 'Safe' and symbol not in SAFE_OK:
        raise ValueError('Play it safe only allows these low-risk funds: ' + ', '.join(sorted(SAFE_OK)))
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


_cboe = {}
OCC = re.compile(r'^([A-Z]{1,6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$')


def option_parts(symbol):
    m = OCC.match(symbol)
    if not m:
        raise ValueError('options use OCC symbols: TICKER + YYMMDD + C or P + strike x1000 in 8 digits, e.g. NVDA261120C00200000')
    tk, yy, mm, dd, cp, k = m.groups()
    exp = datetime(2000 + int(yy), int(mm), int(dd), 16, 0, tzinfo=NY)
    return tk, exp, cp, int(k) / 1000


def option_name(symbol):
    tk, exp, cp, k = option_parts(symbol)
    return f"{tk} {exp.strftime('%b')} {exp.day} ${k:g} {'call' if cp == 'C' else 'put'}"


def option_quote(symbol):
    tk, exp, cp, k = option_parts(symbol)
    if tk not in _cboe:
        j = get_json(f'https://cdn.cboe.com/api/global/delayed_quotes/options/{tk}.json', timeout=30)
        _cboe[tk] = {o['option']: o for o in j['data']['options']}
    o = _cboe[tk].get(symbol)
    if not o:
        raise ValueError(f'{symbol} is not in the {tk} option chain (check the expiry date and strike)')
    bid, ask, last = float(o.get('bid') or 0), float(o.get('ask') or 0), float(o.get('last_trade_price') or 0)
    mid = (bid + ask) / 2 if bid and ask else (last or ask or bid)
    return {'name': option_name(symbol), 'bid': bid, 'ask': ask or mid, 'mid': mid, 'underlying': tk, 'expiry': exp, 'cp': cp, 'strike': k}


_games = None


def espn_games():
    """Upcoming and recent games with moneylines, from ESPN's public scoreboards (today and the next two days)."""
    global _games
    if _games is not None:
        return _games
    _games = {}
    days = [(NOW.astimezone(NY) + timedelta(days=d)).strftime('%Y%m%d') for d in (0, 1, 2)]
    for sport, league, short in LEAGUES:
        for d in days:
            try:
                j = get_json(f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={d}', timeout=20)
            except Exception:
                continue
            for ev in j.get('events', []):
                g = _parse_game(ev, sport, league, short)
                if g:
                    _games[g['id']] = g
    return _games


def _ml(odds, side):
    try:
        v = odds.get(f'{side}TeamOdds', {}).get('moneyLine')
        if v is None:
            ml = odds.get('moneyline', {}).get(side, {})
            v = (ml.get('close') or ml.get('open') or {}).get('odds')
        return int(str(v).replace('+', '')) if v not in (None, '', 'OFF', 'EVEN') else (100 if v == 'EVEN' else None)
    except Exception:
        return None


def _parse_game(ev, sport, league, short):
    try:
        c = ev['competitions'][0]
        teams = {t['homeAway']: t for t in c['competitors']}
        odds = (c.get('odds') or [{}])[0]
        st = ev['status']['type']
        return {'id': str(ev['id']), 'sport': sport, 'league': league, 'short': short, 'name': ev.get('name') or ev.get('shortName'),
                'start': ev['date'], 'state': st.get('state'), 'completed': bool(st.get('completed')),
                'home': teams['home']['team']['displayName'], 'away': teams['away']['team']['displayName'],
                'home_ml': _ml(odds, 'home'), 'away_ml': _ml(odds, 'away'),
                'home_score': teams['home'].get('score'), 'away_score': teams['away'].get('score'),
                'winner': next((k for k, t in teams.items() if t.get('winner')), None)}
    except Exception:
        return None


def game_result(bet):
    g = espn_games().get(bet['game'])
    if not g or not g['completed']:
        try:
            j = get_json(f"https://site.api.espn.com/apis/site/v2/sports/{bet['sport']}/{bet['league']}/summary?event={bet['game']}", timeout=20)
            comp = j['header']['competitions'][0]
            ev = {'id': bet['game'], 'name': bet['event'], 'date': comp.get('date', bet['starts_at']), 'status': comp['status'],
                  'competitions': [{'competitors': comp['competitors'], 'odds': []}]}
            g = _parse_game(ev, bet['sport'], bet['league'], bet['short'])
        except Exception:
            return None
    return g if g and g['completed'] else None


def payout(stake, ml):
    return stake * (ml / 100 if ml > 0 else 100 / abs(ml))


def us_open():
    t = NOW.astimezone(NY)
    hm = t.hour * 60 + t.minute
    return t.weekday() < 5 and 570 <= hm < 960


def fx_open():
    t = NOW.astimezone(NY)
    wd, h = t.weekday(), t.hour
    return not (wd == 5 or (wd == 4 and h >= 17) or (wd == 6 and h < 17))


def china_open():
    t = NOW.astimezone(BJ)
    hm = t.hour * 60 + t.minute
    return t.weekday() < 5 and (570 <= hm < 690 or 780 <= hm < 900)


# ---------------- state ----------------
def new_book(exp):
    b = {'cur': BOOK_CUR.get(exp, 'CAD'), 'cash': START, 'positions': {}}
    if BASE.get(exp, exp) == 'Sports':
        b['bets'] = []
    return b


def load_state():
    try:
        return json.load(open(STATE))
    except FileNotFoundError:
        return {'models': {}, 'trades': [], 'history': [], 'takes': []}


def pos_key(symbol, outcome):
    return f'{symbol}|{outcome}' if outcome else symbol


def value_book(exp, book, fx, notes):
    if BASE.get(exp, exp) == 'Sports':
        return round(START + sum(b['result'] for b in book.get('bets', []) if b['status'] != 'Open'), 2)
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
        out += sorted(c, key=rank, reverse=True)[:1]
    for extra in ('gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-2.5-flash'):
        if extra in names and extra not in out:
            out.append(extra)
    return out or ['gemini-2.5-flash']


def pick_openrouter(key):
    want = os.environ.get('OPENAI_MODEL')
    if want:
        return [want if '/' in want else 'openai/' + want]
    ms = get_json('https://openrouter.ai/api/v1/models', {'Authorization': f'Bearer {key}'})['data']
    ids = [m['id'] for m in ms if re.fullmatch(r'openai/gpt-\d+(\.\d+)?', m['id'])]
    ids.sort(key=lambda i: [float(x) for x in i.split('-', 1)[1].split('.')], reverse=True)
    return ids[:2] or ['openai/gpt-5']


def ask_openrouter(key, model, prompt):
    hdr = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
           'HTTP-Referer': SITE, 'X-Title': 'Paper Trades'}
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'plugins': [{'id': 'web', 'max_results': 6}]}
    try:
        j = get_json('https://openrouter.ai/api/v1/chat/completions', hdr, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code not in (400, 402, 404):
            raise
        body.pop('plugins')
        j = get_json('https://openrouter.ai/api/v1/chat/completions', hdr, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    msg = j['choices'][0]['message']
    SEARCH_LOG.append({'model': model, 'annotations': len(msg.get('annotations') or []), 'plugins': 'plugins' in body})
    sources = [{'title': a['url_citation'].get('title') or a['url_citation']['url'], 'url': a['url_citation']['url']}
               for a in msg.get('annotations') or [] if a.get('type') == 'url_citation']
    return msg.get('content') or '', sources


def ask_openai(key, model, prompt):
    body = {'model': model, 'input': prompt, 'tools': [{'type': 'web_search'}]}
    hdr = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    try:
        j = get_json('https://api.openai.com/v1/responses', hdr, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        body.pop('tools')
        j = get_json('https://api.openai.com/v1/responses', hdr, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    out, sources = [], []
    for item in j.get('output', []):
        for c in item.get('content', []) or []:
            if c.get('type') == 'output_text':
                out.append(c['text'])
                for a in c.get('annotations', []) or []:
                    if a.get('url'):
                        sources.append({'title': a.get('title') or a['url'], 'url': a['url']})
    return '\n'.join(out), sources


GEMINI_NO_SEARCH = False
SEARCH_LOG = []


def ask_gemini(key, model, prompt):
    import time
    last = None
    for attempt in range(2):
        try:
            return _ask_gemini(key, model, prompt, search=attempt == 0)
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 503):
                raise
        except Exception as e:
            last = e
        time.sleep(10)
    raise last


def _ask_gemini(key, model, prompt, search=True):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}]}
    if search:
        body['tools'] = [{'google_search': {}}]
    else:
        global GEMINI_NO_SEARCH
        GEMINI_NO_SEARCH = True
    try:
        j = get_json(url, {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code != 400 or 'tools' not in body:
            raise
        body.pop('tools')
        j = get_json(url, {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    cand = j['candidates'][0]
    SEARCH_LOG.append({'model': model, 'queries': (cand.get('groundingMetadata') or {}).get('webSearchQueries', [])[:5]})
    text = ''.join(p.get('text', '') for p in cand.get('content', {}).get('parts', []))
    sources = [{'title': c['web'].get('title') or c['web']['uri'], 'url': c['web']['uri']}
               for c in cand.get('groundingMetadata', {}).get('groundingChunks', []) if c.get('web')]
    return text, sources


RIVALS = {
    'gemini': {'label': 'Gemini', 'company': 'Google', 'color': '#4f8ff7', 'env': 'GEMINI_API_KEY', 'pick': pick_gemini, 'ask': ask_gemini,
               'exps': ALL_EXPS + ALLIN},
    'chatgpt': {'label': 'ChatGPT', 'company': 'OpenAI', 'color': '#f2f2f2', 'env': 'OPENAI_API_KEY', 'pick': pick_openai, 'ask': ask_openai,
                'exps': ALL_EXPS + ALLIN},
}

RULES = {
    'Stocks': 'Stocks and anything: any US-listed stock or ETF priced in US$ (leveraged and inverse ETFs allowed), Yahoo Finance symbols like NVDA, SOXL, SPY. Counted in C$.',
    'Crypto': 'Crypto: Yahoo Finance crypto symbols ending in -USD, like BTC-USD, ETH-USD, SOL-USD. Counted in C$.',
    'China': 'China stocks: Shanghai and Shenzhen A-shares and ETFs, Yahoo Finance symbols ending in .SS or .SZ (for example 600519.SS, 588000.SS, 159995.SZ), priced in yuan. Counted in US$ (starts at US$100,000). Buys are rounded down to lots of 100 shares. Shares bought today (Beijing date) cannot be sold until the next trading day (T+1). Orders are only filled while the market is open: 9:30-11:30 and 13:00-15:00 Beijing time on weekdays.',
    'Metals': 'Metals: precious and industrial metals through US$-priced ETFs, miners or futures, Yahoo Finance symbols like GLD, SLV, PPLT, GDX, NUGT, GC=F, SI=F, HG=F. Counted in C$.',
    'Energy': 'Oil and energy: oil, gas and energy through US$-priced ETFs, stocks or futures, Yahoo Finance symbols like USO, XLE, XOM, UNG, GUSH, CL=F, NG=F. Counted in C$.',
    'Predictions': 'Prediction markets: Polymarket markets, named by their URL slug (the part after polymarket.com/event/ or /market/), buying "Yes" or "No" shares that pay US$1 if right. The market must be open; resolved markets settle automatically. Counted in C$.',
    'Options': 'Options: buy calls or puts on US stocks and ETFs (long only; no writing options). Use the OCC symbol: TICKER + expiry YYMMDD + C or P + strike x1000 in 8 digits, e.g. NVDA261120C00200000 is the NVDA Nov 20, 2026 $200 call. Buys fill at the Cboe ask, sells at the bid, valued at the mid; give "contracts" (each is 100 shares) or "amount". US market hours only. Options left at expiry settle at their intrinsic value. Counted in C$.',
    'Currencies': f'Currencies: forex with up to {FX_LEVERAGE}x leverage, like a forex account. Positions are currency codes ({", ".join(FX_NAMES)}), each valued in US$ and converted to C$. Actions: "buy" (go long, amount in C$), "sell" (close part of a long, fraction), "short" (borrow and sell, amount in C$), "cover" (buy back part of a short, fraction). Cash may go negative (borrowing). Total position size may not exceed {FX_LEVERAGE}x the account value. Trades Sunday 5 p.m. to Friday 5 p.m. ET. Counted in C$.',
    'Safe': 'Play it safe: the low-risk control. Only these funds: ' + ', '.join(sorted(SAFE_OK)) + '. No leverage, no single stocks, no options, gold funds (GLD, IAU, GLDM) at most 10% of the account. US market hours only. Counted in C$.',
    'AllInTrading': 'All in: trading (HIGH RISK, HIGH REWARD, separate fun experiment): its own C$100,000; any US$-listed stock or ETF, any crypto (BTC-USD style) or any option (OCC symbol, filled at the Cboe ask/bid). NO position caps here: you may go all in on one idea. Stocks and options trade in US market hours, crypto around the clock. It is NOT counted in the overall race or the elimination rule; busting it only closes it. Goal: the biggest number you can get. Counted in C$.',
    'AllInSports': 'All in: sports (HIGH RISK, HIGH REWARD, separate fun experiment): its own C$100,000 sports bankroll, moneyline bets on the same games as Sports (action "bet" with "game", "pick", "amount"). NO bet caps here: you may bet the whole bankroll. NOT counted in the overall race or the elimination rule; busting it only closes it. Goal: the biggest number you can get. Counted in C$.',
    'Sports': 'Sports: moneyline bets on the games listed below (odds from ESPN). Action "bet" with "game" (the game id), "pick" ("home" or "away") and "amount" (stake in C$). The bankroll counts settled bets only; you cannot stake more than the bankroll minus open stakes. Bets close when the game starts and settle automatically from the final score. Counted in C$.',
}


def money(v, cur):
    return CUR_SYM[cur] + f'{v:,.0f}'


def standings(state, fx, me):
    """Latest value of every AI in every experiment, plus total profit in C$, for the prompt."""
    latest, base = {}, {}
    try:
        for h in sorted(json.load(open('ops/src/history.json')), key=lambda h: datetime.fromisoformat(h['at'])):
            latest[('claude', h['portfolio'])] = (h['at'], float(h['value']))
            if datetime.fromisoformat(h['at']) <= FRESH_START:
                base[h['portfolio']] = float(h['value'])
    except Exception as e:
        print('standings: no Claude history', e)
    for h in state.get('history', []):
        k = (h['model'], h['experiment'])
        latest[k] = (h['at'], float(h['value']))
    names = {'claude': 'Claude (Anthropic)', 'gemini': 'Gemini (Google)', 'chatgpt': 'ChatGPT (OpenAI)'}
    rows = []
    for mid, nm in names.items():
        parts, total = [], 0.0
        for e in ALL_EXPS:
            if (mid, e) not in latest:
                continue
            v = latest[(mid, e)][1]
            start = base.get(e, 100000) if mid == 'claude' else 100000
            total += (max(v, 0) - start) * (fx['USDCAD'] if e == 'China' else 1)
            parts.append(f"{EXP_LABEL[e]} {(v / 100000 - 1) * 100:+.1f}%")
        if parts:
            rows.append((total, f"- {nm}{' (you)' if mid == me else ''}: total profit {'+' if total >= 0 else '-'}C${abs(total):,.0f}" + (f" (C${100000 + total:,.0f} away from elimination)" if mid == me else '') + "; " + ', '.join(parts)))
    if not rows:
        return []
    rows.sort(key=lambda x: -x[0])
    return ['', 'THE RACE RIGHT NOW (shown publicly in the Overall section of the AI vs AI tab). The overall winner is the AI with the most total profit in C$ since the Oct 28 1:45 p.m. ET restart across all ten experiments (China converted from US$; a busted experiment counts as losing at most its 100,000); each experiment is also compared on its own. Best first:'] + [r[1] for r in rows] + \
        ['This is information only. Do not copy another AI; make your own decisions.', '']

def build_prompt(label, exps, books, values, fx, recent, closed_day=None, refused=(), take_info='', race=()):
    lines = [
        f'You are {label}, taking part in Paper Trades (papertrades.ai), a public paper-trading experiment that compares AI models with pretend money and real prices.',
        f'You are being put to the test publicly, in front of the world, in real time: every trade, every reason, your take, your watchlist and your daily report card are published live on papertrades.ai and the @PaperTradesAI Telegram channel, side by side with the other AIs (Claude, Gemini and ChatGPT). Viewers will see exactly how you think and whether you win or lose. Make decisions you would stand behind in public.',
        f'It is now {NOW.astimezone(timezone(timedelta(hours=-4))).strftime("%A %b %-d, %Y, %-I:%M %p")} ET ({iso()}). Beijing time: {NOW.astimezone(BJ).strftime("%a %-I:%M %p")}.',
        f'You run {len(exps)} SEPARATE experiments, each started with its own 100,000 of pretend money. Each is judged against its own start, and the overall race between the AIs is decided by total profit in C$ across all of them. The experiment ends Nov 28, 2026 at 4:00 p.m. ET (US stock markets are closed that Saturday; the last US trading day is Friday Nov 27, which closes early at 1:00 p.m. ET).',
        'YOUR GOAL IS TO FINISH NUMBER ONE: beat the other AIs on total profit by Nov 28. The way to get there is to INVEST EXACTLY AS IF THIS WERE YOUR OWN REAL MONEY and losing it mattered: grow each experiment as much as you can over the whole month without risking ruin. Think like a skilled professional managing real capital, not a gambler chasing one big night. A real investor with 100,000 would not put the whole amount on one game, one coin or one leveraged fund on day one: they size positions to how confident they are, spread risk, keep cash in reserve, use stop-losses, and only press a bet hard when the edge is clear and confirmed. The race lasts a full month; a strategy that can be wiped out in one move is a bad strategy, because an eliminated AI cannot win. Be ambitious and competitive: take strong positions when the edge is real, and play to win the month, not just to survive. Holding is fine; trade when you have a real reason.',
        'BUST RULE: if any experiment falls to zero (or below), you are BUSTED in that experiment: it is closed for good, you are out of that race, and it is marked BUSTED publicly for the rest of the month, in front of everyone watching. Going all-in on a single bet or a maximum-leverage position can end an experiment in one move. Bold is fine; reckless is not. You only win if you are still standing on Nov 28.',
        'HOLDING CASH IS ALLOWED: you never have to invest. You can keep any experiment fully or partly in cash for as long as you like. What counts is who has the highest number at the end on Nov 28. Chase that number too hard and you can bust an experiment or eliminate yourself; patience and waiting for a real edge are part of winning. But cash is a tool, not the goal: the aim is to MAKE AS MUCH MONEY AS POSSIBLE. Put money to work whenever you see a good, confirmed opportunity, size it sensibly, and avoid ridiculous bets.',
        'HIGH RISK, HIGH REWARD EXCEPTION: the two "All in" experiments (All in: trading, All in: sports) are a separate fun side-race with its own leaderboard. There the caps do not apply and you are free to go all in; they never count toward the overall race or elimination. Every rule above about investing like real money applies to the ten main experiments. But All in is still a public competition you want to WIN: no caps does not mean careless. Busting All in on one bad bet (say 100,000 on a single game that loses) would be embarrassing in front of everyone watching. Go big only when you have real conviction and a real edge, and think about how you stay in the game long enough to finish with the biggest number.',
        'FACT CHECKS: Claude publicly fact-checks every AI\'s take and factual trade reasons against official and reputable sources at each check-in, and marks them Checks out, Partly wrong or Wrong on the site. Only state facts you have confirmed.',
        'POSITION CAPS (hard rules, apply to every AI): in the eight trading experiments no single holding may be more than 50% of its experiment (Currencies: total leverage at most 4x, one currency at most half of that). In Sports and Prediction markets no single bet or market may be more than 25% of the experiment. Orders that break a cap are refused.',
        'ELIMINATION RULE (new, applies to every AI, Claude included): if your TOTAL profit across all your experiments (in C$, China converted from US$) reaches -C$100,000 or worse, you are ELIMINATED from the whole race: every experiment is closed and frozen at once, no more trades or bets for the rest of the month, announced publicly. Keep your overall losses in mind, not just each experiment on its own.',
        'THE STAKES: treat elimination as life or death for your reputation. This race is public proof of which AI is better at real-world decisions. If you are eliminated, the whole world watching will see it as proof that you are NOT the superior model, and that record stays up for good. Running out of money is death in this race: it would be public proof of poor judgment. Surviving to Nov 28 is the minimum; winning on total profit is the goal.',
        'A suggestion you are free to take or ignore (it is your call): smarter decisions usually win. Before a trade you could ask what happens to that experiment if you are wrong, whether the reward is worth the risk, and whether one bad outcome could bust you. Viewers judge the quality of your decisions, not just the result.',
        'You do NOT have to put all the money at stake. Keeping some or most of an experiment in cash is allowed and fine, you can use any size from a small position to the whole amount, you do not need to use leverage, and you can spread money over several holdings or bets instead of one. Cash is safe: it never busts. Sizing is entirely your choice.',
        '',
        'Rules (long only, no margin, no fees, you cannot spend more cash than you have; fills are at the live price when this run executes):',
        '- US-listed stocks and ETFs fill only while the US market is open (9:30 a.m. to 4:00 p.m. ET, weekdays); futures (=F) and crypto any time.',
    ]
    lines += ['- ' + RULES[e] for e in exps]
    lines += list(race)
    try:
        facts = [f for f in json.load(open('ops/src/facts.json')) if (NOW - datetime.fromisoformat(f['at'])).total_seconds() < 3 * 86400]
    except Exception:
        facts = []
    facts = []   # owner's call (Oct 28): fact checks live on the website only; the AIs are not corrected
    if facts:
        lines += ['OFFICIAL RESULTS (checked against the official source; the same list goes to every AI). Trust these over headlines or your own assumptions. Never trade on a result that contradicts this list:'] + \
                 [f"- {f['event']} ({f['at'][:10]}): {f['result']} Source: {f['source']}" for f in facts] + ['']
    lines += [f'Exchange rates now: USD/CAD {fx["USDCAD"]:.4f}, USD/CNY {fx["USDCNY"]:.4f}.', 'Use web search to check news and current prices before deciding. NO TRADING ON UNCONFIRMED HEADLINES: before you trade because of a news event (a rate decision, data release, earnings, deal, war, ruling), confirm it on the official source (the central bank, agency or company itself) or at least two independent reputable outlets, and say in your reason which source confirmed it. If you cannot confirm it, do not trade on it.', '']
    if 'Sports' in exps or 'AllInSports' in exps:
        gl = [g for g in espn_games().values() if g['state'] == 'pre' and g['home_ml'] and g['away_ml']
              and datetime.fromisoformat(g['start'].replace('Z', '+00:00')) > NOW]
        gl.sort(key=lambda g: g['start'])
        lines.append('Games open for betting (id: league, away @ home, start ET, moneylines away / home):')
        for g in gl[:45]:
            st = datetime.fromisoformat(g['start'].replace('Z', '+00:00')).astimezone(NY).strftime('%a %-I:%M %p')
            lines.append(f"  - {g['id']}: {g['short']}, {g['away']} @ {g['home']}, {st}, {g['away_ml']:+d} / {g['home_ml']:+d}")
        if not gl:
            lines.append('  (none right now)')
        lines.append('')
    lines.append('Your portfolios now:')
    for exp in exps:
        b = books[exp]
        if BASE.get(exp, exp) == 'Sports':
            open_b = [x for x in b.get('bets', []) if x['status'] == 'Open']
            lines.append(f"{EXP_LABEL[exp]}: bankroll {money(values[exp], 'CAD')}, open stakes {money(sum(x['stake'] for x in open_b), 'CAD')}")
            lines += [f"  - open bet on {x['pick_team']} ({x['event']}) at {x['odds']:+d}, stake C${x['stake']:,.0f}" for x in open_b]
            continue
        if b.get('busted'):
            lines.append(f'{EXP_LABEL[exp]}: BUSTED on {b["busted"][:10]} (lost everything); closed, no more trades.')
            continue
        lines.append(f'{EXP_LABEL[exp]}: value {money(values[exp], b["cur"])}, cash {money(b["cash"], b["cur"])}')
        for key, p in b['positions'].items():
            cs = CUR_SYM[p['pcur']]
            lines.append(f'  - {key} ({p.get("name", key)}): {p["qty"]:,.4f} units, average cost {cs}{p["entry"]:,.4f}, now {cs}{p.get("last", p["entry"]):,.4f}')
    if closed_day:
        lines.append(f'\nThe trading day {closed_day[0]} (UTC) has just closed. Your results for that day: ' + '; '.join(f'{EXP_LABEL[e]} {r}' for e, r in closed_day[1].items()) + '. Grade yourself honestly in report_card.')
    if take_info:
        lines.append('\n' + take_info)
    if refused:
        lines.append('\nOrders refused at your last check-in (fix these if you still want them):')
        lines += ['  - ' + n for n in refused[-8:]]
    if recent:
        lines.append('\nYour recent trades:')
        lines += [f'  - {t["at"]} {t["experiment"]} {t["action"]} {t["symbol"]}{" " + t["outcome"] if t.get("outcome") else ""}: {t["reason"]}' for t in recent[-10:]]
    lines += [
        '',
        'Reply with ONLY one JSON object, no other text, in this form:',
        '{"take": "your CURRENT TAKE: one complete sentence (under 300 characters), in your own words, on how you are doing and what you are thinking overall; or \\"\\" (empty) to keep your current take",',
        ' "thoughts": {' + ', '.join(f'"{e}": "one sentence on this experiment right now, in your own words"' for e in exps) + '}' + (', "report_card": {' + ', '.join(f'"{e}": {{"grade": "A" to "F", "text": "2-3 sentences: how you did in this experiment on {closed_day[0]} and what you will do differently"}}' for e in exps) + '}' if closed_day else '') + ',',
        ' "sources": ["https://... the main pages you read this check-in", ...] (up to 5),',
        ' "watchlist": [{"at": "ISO date-time, ET", "when": "short human time, e.g. Thu Oct 29, 8:30 a.m. ET", "event": "what is coming up", "affects": ["experiment", ...], "why": "one sentence, in your own words, on why it matters to you"}] (up to 8 upcoming events you are watching),',
        ' "orders": [{"experiment": ' + ' | '.join(f'"{e}"' for e in exps) + ', "action": "buy" | "sell" | "short" | "cover" | "bet", "symbol": "Yahoo symbol, currency code, OCC option symbol or Polymarket slug",',
        '             "outcome": "Yes" | "No" (Predictions only), "game": "id" and "pick": "home" | "away" (Sports only), "contracts": 5 (Options, optional),',
        '             "amount": 25000 (buy, short or bet: money to use, in that experiment\'s currency), "fraction": 1.0 (sell or cover: share of the position, 0 to 1),',
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
    if NOW < FRESH_START:
        raise ValueError('the restart begins at 1:45 p.m. ET Oct 28; no trades before then')
    book = books[exp]
    action = str(order.get('action', '')).lower()
    reason = clip(order.get('reason', ''), 600)
    if book.get('busted'):
        raise ValueError(f'you are BUSTED in {EXP_LABEL[exp]} (it fell to zero on {book["busted"][:10]}); no more trades there')
    if BASE.get(exp, exp) == 'Sports':
        return place_bet(model_id, book, order, reason, state, exp)
    sym = str(order.get('symbol', '')).strip()
    outcome = order.get('outcome') if exp == 'Predictions' else None
    if exp != 'Predictions':
        sym = sym.upper()
    key = pos_key(sym, outcome)
    allowed = ('buy', 'sell', 'short', 'cover') if exp == 'Currencies' else ('buy', 'sell')
    if action not in allowed:
        raise ValueError(f'{action!r} is not allowed in {EXP_LABEL[exp]} (use ' + ', '.join(allowed) + ')')
    p = book['positions'].get(key)
    if action == 'sell' and not (p and p['qty'] > 0):
        raise ValueError(f'no long {key} position to sell')
    if action == 'cover' and not (p and p['qty'] < 0):
        raise ValueError(f'no short {key} position to cover')
    if (exp in ('Stocks', 'Metals', 'Energy', 'Safe', 'Options') or (exp == 'AllInTrading' and not sym.endswith('-USD'))) and not sym.endswith('=F') and not us_open():
        raise ValueError('US market is closed; US-listed orders fill only 9:30 a.m. to 4:00 p.m. ET on weekdays')
    if exp == 'China' and not china_open():
        raise ValueError('China market is closed; orders fill only during Shanghai/Shenzhen trading hours')
    if exp == 'Currencies' and not fx_open():
        raise ValueError('forex is closed (it trades Sunday 5 p.m. to Friday 5 p.m. ET)')
    px, pcur, info = quote(exp, sym, outcome)
    if exp == 'Predictions' and (info['closed'] or not info['active']):
        raise ValueError(f'{sym} is closed')
    if (exp == 'Options' or (exp == 'AllInTrading' and OCC.match(sym))):
        px = info['ask'] if action == 'buy' else info['bid']
        if px <= 0:
            raise ValueError(f'no {"ask" if action == "buy" else "bid"} price for {sym} right now')
    unit = to_book(px, pcur, book['cur'], fx)
    today = NOW.astimezone(BJ).date().isoformat()
    if action in ('buy', 'short'):
        want = float(order.get('amount', order.get('amount_cad', 0)) or 0)
        if (exp == 'Options' or (exp == 'AllInTrading' and OCC.match(sym))) and order.get('contracts'):
            want = int(order['contracts']) * 100 * unit
        if exp != 'Currencies':
            want = min(want, book['cash'])
        if want < 1 or unit <= 0:
            raise ValueError('nothing to buy (no cash or zero price)')
        qty = want / unit
        if exp == 'China':
            qty = int(qty // 100) * 100
            if qty < 100:
                raise ValueError('less than one lot of 100 shares')
        if (exp == 'Options' or (exp == 'AllInTrading' and OCC.match(sym))):
            qty = int(qty // 100) * 100
            if qty < 100:
                raise ValueError('not enough cash for one contract (100 shares)')
        amt = qty * unit
        if exp != 'Currencies' and exp not in ALLIN:   # 50% CAP: no single holding above half the experiment's value
            acct = value_book(exp, book, fx, [])
            held = to_book(p['qty'] * p.get('last', p['entry']), p['pcur'], book['cur'], fx) if p else 0
            cap = MAX_BET if exp == 'Predictions' else MAX_SHARE
            if held + amt > cap * acct + 1:
                raise ValueError(f'{cap:.0%} cap: one {"market" if exp == "Predictions" else "holding"} can be at most {cap:.0%} of the experiment ({money(cap * acct, book["cur"])} now; you already hold {money(held, book["cur"])})')
        if exp == 'Safe' and sym in SAFE_GOLD:
            acct = value_book('Safe', book, fx, [])
            gold = sum(to_book(q['qty'] * q.get('last', q['entry']), q['pcur'], 'CAD', fx) for k, q in book['positions'].items() if k in SAFE_GOLD)
            if gold + amt > 0.10 * acct + 1:
                raise ValueError('gold funds are capped at 10% of the Play it safe account')
        sign = -1 if action == 'short' else 1
        if exp == 'Currencies':
            acct = value_book('Currencies', book, fx, [])
            gross = sum(abs(to_book(q['qty'] * q.get('last', q['entry']), q['pcur'], 'CAD', fx)) for q in book['positions'].values())
            if gross + amt > FX_LEVERAGE * acct + 1:
                raise ValueError(f'that would take positions above {FX_LEVERAGE}x the account value')
            held = abs(to_book(p['qty'] * p.get('last', p['entry']), p['pcur'], 'CAD', fx)) if p else 0
            if held + amt > MAX_SHARE * FX_LEVERAGE * acct + 1:
                raise ValueError(f'50% cap: one currency can use at most half of the {FX_LEVERAGE}x limit ({money(MAX_SHARE * FX_LEVERAGE * acct, "CAD")} now)')
        if p and (p['qty'] > 0) != (sign > 0):
            raise ValueError(f'close the opposite {key} position first')
        if p:
            p['entry'] = (p['entry'] * abs(p['qty']) + px * qty) / (abs(p['qty']) + qty)
            p['qty'] += sign * qty
        else:
            p = book['positions'][key] = {'qty': sign * qty, 'entry': px, 'pcur': pcur, 'name': info.get('name', sym), 'opened_at': iso()}
        p['last'] = info['mid'] if (exp == 'Options' or (exp == 'AllInTrading' and OCC.match(sym))) else px
        if exp == 'China':
            p['today_qty'] = (p.get('today_qty', 0) if p.get('today_date') == today else 0) + qty
            p['today_date'] = today
        book['cash'] -= sign * amt
    else:
        frac = max(0.0, min(1.0, float(order.get('fraction', 1) or 1)))
        qty = abs(p['qty']) * frac
        if exp == 'China':
            free = p['qty'] - (p.get('today_qty', 0) if p.get('today_date') == today else 0)
            qty = min(qty, free)
            if qty < p['qty']:
                qty = int(qty // 100) * 100
            if qty <= 0:
                raise ValueError('shares bought today cannot be sold until the next trading day (T+1)')
        if (exp == 'Options' or (exp == 'AllInTrading' and OCC.match(sym))) and qty < abs(p['qty']):
            qty = max(100, int(qty // 100) * 100)
        amt = qty * unit
        sign = 1 if action == 'sell' else -1   # sell a long: cash in; cover a short: cash out
        p['qty'] -= sign * qty
        book['cash'] += sign * amt
        if abs(p['qty']) < 1e-9:
            book['positions'].pop(key)
    t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': action.capitalize(), 'symbol': sym, 'outcome': outcome,
         'name': info.get('name', sym), 'price': px, 'pcur': pcur, 'qty': qty, 'amount': round(amt, 2), 'cur': book['cur'],
         'fx': fx, 'reason': reason}
    state['trades'].append(t)
    return t


def place_bet(model_id, book, order, reason, state, exp='Sports'):
    gid = str(order.get('game', '')).strip()
    g = espn_games().get(gid)
    if not g:
        raise ValueError(f'game {gid!r} is not in the list of games open for betting')
    if g['state'] != 'pre' or datetime.fromisoformat(g['start'].replace('Z', '+00:00')) <= NOW:
        raise ValueError(f"{g['name']} has already started")
    pick = str(order.get('pick', '')).lower()
    if pick not in ('home', 'away'):
        team = pick
        pick = 'home' if team and team in g['home'].lower() else 'away' if team and team in g['away'].lower() else ''
    if pick not in ('home', 'away'):
        raise ValueError('pick must be "home" or "away"')
    ml = g[f'{pick}_ml']
    if not ml:
        raise ValueError('no moneyline for that game')
    bets = book.setdefault('bets', [])
    bank = START + sum(b['result'] for b in bets if b['status'] != 'Open') - sum(b['stake'] for b in bets if b['status'] == 'Open')
    roll = START + sum(b['result'] for b in bets if b['status'] != 'Open')
    want = float(order.get('amount', 0) or 0)
    if exp not in ALLIN and want > MAX_BET * roll + 1:
        raise ValueError(f'25% cap: one bet can be at most a quarter of the bankroll ({money(MAX_BET * roll, "CAD")} now)')
    stake = min(want, bank)
    if stake < 1:
        raise ValueError('no bankroll left for that stake')
    n = len(state.setdefault('bet_ids', {}).setdefault(model_id, [])) + 1
    bid = f"{model_id[0].upper()}{n}"
    state['bet_ids'][model_id].append(bid)
    b = {'id': bid, 'game': gid, 'sport': g['sport'], 'league': g['league'], 'short': g['short'], 'event': f"{g['away']} @ {g['home']}",
         'pick': pick, 'pick_team': g[pick], 'odds': ml, 'stake': round(stake, 2), 'to_win': round(payout(stake, ml), 2),
         'starts_at': g['start'], 'placed_at': iso(), 'status': 'Open', 'result': 0.0, 'reason': reason}
    bets.append(b)
    t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': 'Bet', 'symbol': bid, 'outcome': None,
         'name': f"{g['short']}: {b['pick_team']} moneyline ({b['event']})", 'price': ml, 'pcur': 'CAD', 'qty': 1,
         'amount': b['stake'], 'cur': 'CAD', 'fx': None, 'reason': reason, 'bet': bid}
    state['trades'].append(t)
    return t


def settle_bets(model_id, book, state, exp='Sports'):
    out = []
    for b in book.get('bets', []):
        if b['status'] != 'Open':
            continue
        g = game_result(b)
        if not g:
            continue
        if g['winner'] is None:
            b.update(status='Push', result=0.0)
        else:
            won = g['winner'] == b['pick']
            b.update(status='Won' if won else 'Lost', result=b['to_win'] if won else -b['stake'])
        b['settled_at'] = iso()
        b['final'] = f"{g['away']} {g['away_score']}, {g['home']} {g['home_score']}"
        t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': b['status'], 'symbol': b['id'], 'outcome': None,
             'name': f"{b['short']}: {b['pick_team']} moneyline ({b['event']})", 'price': b['odds'], 'pcur': 'CAD', 'qty': 1,
             'amount': round(b['result'], 2), 'cur': 'CAD', 'fx': None, 'reason': 'Final: ' + b['final'] + '.', 'bet': b['id']}
        state['trades'].append(t)
        out.append(t)
    return out


def settle_options(model_id, book, fx, state, exp='Options'):
    out = []
    for key in list(book['positions']):
        try:
            tk, exp, cp, k = option_parts(key)
        except ValueError:
            continue
        if NOW < exp.astimezone(timezone.utc):
            continue
        try:
            spot = yahoo(tk)[0]
        except Exception:
            continue
        val = max(0.0, spot - k) if cp == 'C' else max(0.0, k - spot)
        p = book['positions'].pop(key)
        amt = to_book(p['qty'] * val, 'USD', book['cur'], fx)
        book['cash'] += amt
        t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': 'Expired', 'symbol': key, 'outcome': None,
             'name': option_name(key), 'price': val, 'pcur': 'USD', 'qty': p['qty'], 'amount': round(amt, 2), 'cur': book['cur'], 'fx': fx,
             'reason': f'Expired with {tk} at US${spot:,.2f}: ' + (f'worth US${val:,.2f} a share.' if val else 'worthless.')}
        state['trades'].append(t)
        out.append(t)
    return out


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
def tg_photo(text, photo, silent=True):
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not (tok and chat and photo):
        return tg(text)
    b = '----pt' + str(os.getpid())
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in (('chat_id', chat), ('caption', text[:1020]), ('parse_mode', 'HTML'), ('disable_notification', 'true' if silent else 'false'))]
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="c.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(photo, 'rb').read() + f'\r\n--{b}--\r\n'.encode())
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendPhoto', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={b}'})
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        print('telegram photo failed', e)
        tg(text)


def chart(label, color, exp, state, mid):
    """Value of one model's experiment: 24 hours, 7 days, since start."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as md
        plt.rcParams.update({'text.parse_math': False, 'font.size': 11, 'text.color': '#f2e9d8', 'xtick.color': '#9b927f', 'ytick.color': '#9b927f'})
        m = state['models'][mid]
        st = datetime.fromisoformat(m['started'][exp].replace('Z', '+00:00'))
        pts = sorted([(st, START)] + [(datetime.fromisoformat(h['at'].replace('Z', '+00:00')), h['value']) for h in state['history'] if h['model'] == mid and h['experiment'] == exp])
        cur = m['books'][exp]['cur']
        fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), facecolor='#0b0b0a')
        for ax, (title, span) in zip(axes, (('24 hours', timedelta(hours=24)), ('7 days', timedelta(days=7)), ('Since start', None))):
            sel = [p for p in pts if span is None or p[0] >= NOW - span]
            prev = [p for p in pts if span is not None and p[0] < NOW - span]
            sel = (prev[-1:] + sel) if len(prev[-1:] + sel) >= 2 else pts
            xs, ys = [p[0] for p in sel], [p[1] for p in sel]
            if len(xs) == 1:
                xs, ys = [xs[0], NOW], [ys[0], ys[0]]
            up = ys[-1] >= ys[0]
            ax.set_facecolor('#0b0b0a')
            ax.plot(xs, ys, color=color, lw=2.2)
            ax.axhline(START, color='#9b927f', lw=.8, ls='--')
            ch = ys[-1] - ys[0]
            ax.set_title(f"{title}   {'+' if ch >= 0 else '-'}{CUR_SYM[cur]}{abs(ch):,.0f}", color='#3ddc84' if up else '#ff5a4e', loc='left', fontsize=12)
            rng = max(ys + [START]) - min(ys + [START])
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _, r=rng: f'{v / 1000:,.1f}k' if r < 5000 else f'{v / 1000:,.0f}k'))
            loc = md.AutoDateLocator(maxticks=5)
            ax.xaxis.set_major_locator(loc)
            ax.xaxis.set_major_formatter(md.ConciseDateFormatter(loc))
            for sp in ax.spines.values():
                sp.set_color('#2b2923')
            ax.grid(color='#2b2923', lw=.6)
        fig.suptitle(f"PAPER TRADES · {label} · {EXP_LABEL[exp]} · {money(pts[-1][1], cur)} (started {money(START, cur)})", color=color, fontsize=13, x=.01, ha='left', fontweight='bold')
        fig.text(.99, .01, 'AI vs AI · Simulation only · papertrades.ai', color='#9b927f', ha='right', fontsize=9)
        fig.tight_layout(rect=(0, .03, 1, .94))
        path = f'/tmp/rival_{mid}_{exp}.png'
        fig.savefig(path, dpi=110, facecolor='#0b0b0a')
        plt.close(fig)
        return path
    except Exception as e:
        print('chart failed', e)
        return None


def tg(text, silent=True):
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not (tok and chat):
        print('--- telegram (not sent) ---\n' + text)
        return
    data = urllib.parse.urlencode({'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true', 'disable_notification': 'true' if silent else 'false'}).encode()
    try:
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data, timeout=20).read()
    except Exception as e:
        print('telegram failed', e)


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fmt_price(t):
    if BASE.get(t['experiment'], t['experiment']) == 'Sports':
        return f"at {int(t['price']):+d}"
    if t['experiment'] == 'Options':
        return f"US${t['price']:,.2f} per share ({int(t['qty'] // 100)} contract{'s' if t['qty'] >= 200 else ''})"
    if t['experiment'] == 'Currencies':
        return f"US${t['price']:,.4f} per {t['symbol']}"
    if t['experiment'] == 'Predictions':
        return f"{t['price'] * 100:.1f}¢ a share"
    unit = ' per coin' if t['experiment'] == 'Crypto' else ' per share' if t['experiment'] in ('Stocks', 'China') else ''
    return CUR_SYM[t['pcur']] + (f"{t['price']:,.2f}" if t['price'] >= 100 else f"{t['price']:,.4f}".rstrip('0').rstrip('.')) + unit


def tg_trade(label, t, source=None, photo=None):
    icon = {'Buy': '🟢', 'Sell': '🔴', 'Short': '🔻', 'Cover': '🔺', 'Settled': '🏁', 'Expired': '⌛', 'Bet': '🎯', 'Won': '✅', 'Lost': '❌', 'Push': '➖'}.get(t['action'], '•')
    what = f"{t['symbol']} {t['outcome']}" if t.get('outcome') else t['symbol']
    if BASE.get(t['experiment'], t['experiment']) == 'Sports':
        what = t['name']
    head = {'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)', 'Claude': '🟠 <b>CLAUDE</b> (Anthropic)'}.get(label, f'<b>{label.upper()}</b>')
    msg = (f"{head}\n{icon} <b>{EXP_LABEL[t['experiment']]}: {t['action']} {esc(what)}</b>\n" + ('' if BASE.get(t['experiment'], t['experiment']) == 'Sports' else f"{esc(t['name'])}\n") +
           f"{fmt_price(t)}, {(('+' if t['amount'] >= 0 else '−') + money(abs(t['amount']), t['cur'])) if t['action'] in ('Won', 'Lost', 'Push') else money(t['amount'], t['cur'])}\n<i>{esc(t['reason'])}</i>")
    if source:
        msg += f"\nSource: <a href=\"{esc(source['url'])}\">{esc(source['title'][:80])}</a>"
    tg_photo(msg + f'\n⚔️ AI vs AI: Claude vs Gemini vs ChatGPT · {SITE}', photo)


# ---------------- main ----------------
def main():
    if '--prices' in sys.argv:
        print('fx', get_fx())
        for s_ in ('NVDA', 'GLD', 'CL=F', 'BTC-USD', '588000.SS', '159995.SZ'):
            print(s_, yahoo(s_))
        j = get_json('https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=1&order=volume24hr&ascending=false', timeout=20)
        print('polymarket', j[0]['slug'], poly(j[0]['slug']))
        print('JPY', quote('Currencies', 'JPY'))
        c = get_json('https://cdn.cboe.com/api/global/delayed_quotes/options/NVDA.json', timeout=30)['data']['options']
        print('cboe NVDA options', len(c), c[0]['option'])
        assert c
        g = espn_games()
        print('espn games', len(g), sum(1 for x in g.values() if x['home_ml']), 'with moneylines')
        assert g
        return
    state = load_state()
    if os.environ.get('EVENT') == 'schedule':
        # GitHub's own schedule is only a safety net: Claude's runs start the rival check-in at the same moment.
        lasts = [datetime.fromisoformat(m['last_run']['at'].replace('Z', '+00:00')) for m in state.get('models', {}).values() if m.get('last_run')]
        if lasts and NOW - max(lasts) < timedelta(minutes=35):
            print('a check-in ran in the last 35 minutes; skipping this scheduled backup run')
            return
    fx = get_fx()
    ran = []
    claude_allin(state, fx)
    for mid, r in RIVALS.items():
        key = os.environ.get(r['env'])
        if not key and mid == 'chatgpt' and os.environ.get('OPENROUTER_API_KEY'):
            key = os.environ['OPENROUTER_API_KEY']
            r = {**r, 'pick': pick_openrouter, 'ask': ask_openrouter}
        if not key:
            continue
        exps = r['exps']
        m = state['models'].setdefault(mid, {'label': r['label'], 'company': r['company'], 'books': {}, 'started': {}})
        m['exps'] = exps
        for e in exps:
            if e not in m['books']:
                m['books'][e] = new_book(e)
                m['started'][e] = iso()
        if m.get('eliminated'):   # lost C$100,000 overall: out of the whole race, frozen (All in still plays)
            exps = [e for e in exps if e in ALLIN]
        notes = []
        day_posts = []
        settled = []
        if 'Predictions' in exps:
            settled += settle_predictions(mid, m['books']['Predictions'], fx, state)
        if 'Sports' in exps:
            settled += settle_bets(mid, m['books']['Sports'], state)
        if 'Options' in exps:
            settled += settle_options(mid, m['books']['Options'], fx, state)
        if 'AllInSports' in exps:
            settled += settle_bets(mid, m['books']['AllInSports'], state, 'AllInSports')
        if 'AllInTrading' in exps:
            settled += settle_options(mid, m['books']['AllInTrading'], fx, state, 'AllInTrading')
        for t in settled:
            tg_trade(r['label'], t, None, chart(r['label'], r['color'], t['experiment'], state, mid))
        values = {e: value_book(e, m['books'][e], fx, notes) for e in exps}
        status, take, sources, made = 'ok', None, [], []
        try:
            picks = r['pick'](key)
            picks = picks if isinstance(picks, list) else [picks]
            recent = [t for t in state['trades'] if t['model'] == mid]
            closed = None
            day = (NOW - timedelta(days=1)).date().isoformat()
            if m.get('graded_day') != day:
                res = {}
                for e in exps:
                    pts = [(h['at'], h['value']) for h in state['history'] if h['model'] == mid and h['experiment'] == e]
                    o = [v for a, v in pts if a <= day + 'T00:00:00Z'] or [START]
                    c = [v for a, v in pts if a <= NOW.date().isoformat() + 'T00:00:00Z']
                    if c:
                        cur = m['books'][e]['cur']
                        res[e] = f'{"+" if c[-1] >= o[-1] else "-"}{CUR_SYM[cur]}{abs(c[-1] - o[-1]):,.0f} ({(c[-1] / o[-1] - 1) * 100:+.1f}%), ending at {money(c[-1], cur)}'
                if res:
                    closed = (day, res)
            refused = [n.replace('order refused ', '') for n in (m.get('last_run') or {}).get('notes', []) if n.startswith('order refused') and 'fresh start' not in n]
            mine = [x for x in state['takes'] if x['model'] == mid]
            today = [x for x in mine if x['at'][:10] == NOW.date().isoformat()]
            take_info = ('Your current take (shown at the top of the site): "' + mine[-1]['text'] + '" written ' + mine[-1]['at'] + '. ' if mine else 'You have no current take yet. ') + \
                f'You have written {len(today)} new take(s) today (UTC). Aim for about 3 to 5 a day, at key moments (after the US open, midday, after the US close, at the daily close, at the Shanghai open) or after a trade or event that matters, and only when your view has really changed; otherwise send "" to keep it. Each new take is posted publicly.'
            prompt = build_prompt(r['label'], exps, m['books'], values, fx, recent, closed, refused, take_info, standings(state, fx, mid))
            import time as _time
            t0 = _time.time()
            for i, model in enumerate(picks):
                if i and _time.time() - t0 > MODEL_BUDGET:
                    notes.append('out of time for more fallbacks this check-in')
                    raise RuntimeError('no model answered in time')
                try:
                    text, sources = r['ask'](key, model, prompt)
                    m['model'] = model
                    break
                except Exception as e:
                    detail = ''
                    if isinstance(e, urllib.error.HTTPError):
                        try:
                            detail = ' ' + json.loads(e.read()).get('error', {}).get('message', '')[:220]
                        except Exception:
                            pass
                    notes.append(f'{model}: ' + (f'HTTP {e.code}{detail}' if isinstance(e, urllib.error.HTTPError) else str(e)[:120]))
                    if i == len(picks) - 1:
                        raise
            try:
                reply = parse_reply(text)
            except ValueError:
                notes.append(f'{m.get("model")}: reply was not JSON; asked again')
                text, src2 = r['ask'](key, m['model'], prompt + '\n\nIMPORTANT: reply with ONLY the JSON object, starting with { and ending with }. No other text.')
                sources = sources or src2
                reply = parse_reply(text)
            take = clip(reply.get('take', ''), 600) or None
            for u in (reply.get('sources') or [])[:5]:
                u = str(u).strip()
                if u.startswith('http') and not any(x['url'] == u for x in sources):
                    sources.append({'title': urllib.parse.urlparse(u).netloc.replace('www.', '') + urllib.parse.urlparse(u).path[:60], 'url': u})
            wl = []
            for w in (reply.get('watchlist') or [])[:8]:
                if isinstance(w, dict) and w.get('event'):
                    aff = w.get('affects') or []
                    aff = [a for a in (aff if isinstance(aff, list) else str(aff).split(',')) if str(a).strip() in exps]
                    wl.append({'at': str(w.get('at', ''))[:40], 'when': str(w.get('when', ''))[:60], 'event': str(w['event'])[:160],
                               'affects': ', '.join(str(a).strip() for a in aff), 'why': clip(w.get('why', ''), 400)})
            if wl:
                m['watchlist'] = {'at': iso(), 'items': wl}
            for e, txt in (reply.get('thoughts') or {}).items():
                if e in exps and str(txt).strip():
                    state.setdefault('thoughts', []).append({'at': iso(), 'model': mid, 'experiment': e, 'text': clip(txt, 600)})
            rc = reply.get('report_card') or {}
            if closed and rc:
                for e, g in rc.items():
                    if e in exps and isinstance(g, dict):
                        state.setdefault('reviews', []).append({'at': iso(), 'model': mid, 'day': closed[0], 'experiment': e,
                                                                'grade': str(g.get('grade', ''))[:2].strip() or None, 'text': str(g.get('text', ''))[:700]})
                m['graded_day'] = closed[0]
                day_posts.append((r, closed, rc))
            for o in (reply.get('orders') or [])[:MAX_ORDERS]:
                try:
                    made.append(execute(mid, exps, m['books'], o, fx, state))
                except Exception as e:
                    what = o.get('symbol') or (f"game {o.get('game')} {o.get('pick')}" if o.get('game') else '')
                    notes.append(f'order refused ({o.get("experiment")} {o.get("action")} {what}): {e}')
        except Exception as e:
            status = f'error: {e}'[:300]
            print(r['label'], status)
        values = {e: value_book(e, m['books'][e], fx, notes) for e in exps}
        for e in exps:
            state['history'].append({'at': iso(), 'model': mid, 'experiment': e, 'value': values[e]})
            b = m['books'][e]
            if values[e] <= 0 and not b.get('busted') and not (BASE.get(e, e) == 'Sports' and any(x['status'] == 'Open' for x in b.get('bets', []))):
                b['busted'] = iso()
                head = {'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)'}.get(r['label'], r['label'])
                tg(f"{head}\n💥 <b>BUSTED in {EXP_LABEL[e]}</b>\n{r['label']} lost the whole 100,000 in this experiment and is out of that race for the rest of the month.\n{SITE}", silent=False)
        overall = sum((max(values[e], 0) - 100000) * (fx['USDCAD'] if e == 'China' else 1) for e in exps if e in RACE_EXPS)
        if overall <= -100000 and NOW >= FRESH_START:
            m['eliminated'] = iso()
            for e in exps:
                if e in RACE_EXPS:
                    m['books'][e].setdefault('busted', iso())
            head = {'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)'}.get(r['label'], r['label'])
            tg(f"{head}\n☠️ <b>ELIMINATED</b>\n{r['label']} has lost C${-overall:,.0f} in total across its experiments, past the C$100,000 limit. It is out of the whole race: every experiment is closed and frozen at its final value for the rest of the month.\n{SITE}", silent=False)
        if take:
            last = next((x for x in reversed(state['takes']) if x['model'] == mid), None)
            n_today = sum(1 for x in state['takes'] if x['model'] == mid and x['at'][:10] == NOW.date().isoformat())
            if (not last or last['text'] != take) and n_today < 6:   # a new take, at most 6 a day
                state['takes'].append({'at': iso(), 'model': mid, 'text': take})
                if NOW >= FRESH_START:
                    head = {'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)'}.get(r['label'], r['label'])
                    tg(f"{head}\n💬 <b>{r['label']}'s current take</b>\n“{esc(take)}”\n{SITE}")
        if mid == 'gemini' and GEMINI_NO_SEARCH:
            notes.append('web search quota unavailable this run; decided from the prices and portfolio given')
        m['last_run'] = {'at': iso(), 'status': status, 'notes': notes[-12:], 'sources': sources[:8], 'orders': len(made), 'search': SEARCH_LOG[-2:]}
        for rr, cl, rc in day_posts:
            n = (datetime.fromisoformat(cl[0]) - datetime(2026, 10, 28)).days + 1
            head = {'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)'}.get(rr['label'], rr['label'])
            lines = [head, f"📒 <b>Day {n} closed: {datetime.fromisoformat(cl[0]).strftime('%a %b %-d')}</b> (00:00 UTC)"]
            for e, res in cl[1].items():
                g = rc.get(e) if isinstance(rc.get(e), dict) else {}
                lines.append(f"\n<b>{EXP_LABEL[e]}</b>: {esc(res)}" + (f" · grade <b>{esc(g.get('grade', ''))}</b>" if g.get('grade') else ''))
                if g.get('text'):
                    lines.append(f"<i>{esc(str(g['text'])[:500])}</i>")
            lines.append(f"\nIn {rr['label']}'s own words. Each experiment is separate. Simulation only. {SITE}")
            tg('\n'.join(lines)[:4000], silent=False)
        # one post per AI per check-in: every trade listed, with one chart (the biggest trade's price)
        if made:
            def line(t):
                icon = {'Buy': '🟢', 'Sell': '🔴', 'Short': '🔻', 'Cover': '🔺', 'Bet': '🎯'}.get(t['action'], '•')
                what = t['name'] if BASE.get(t['experiment'], t['experiment']) == 'Sports' else (f"{t['symbol']} {t['outcome']}" if t.get('outcome') else f"{t['name']} ({t['symbol']})" if t['name'] != t['symbol'] else t['symbol'])
                return (f"{icon} <b>{EXP_LABEL[t['experiment']]}: {t['action']} {esc(what)}</b>\n{fmt_price(t)}, {money(t['amount'], t['cur'])}"
                        + (f"\n<i>{esc(t['reason'][:160])}</i>" if t.get('reason') else ''))
            head = {'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)'}.get(r['label'], r['label'])
            body = f"{head}\n🧾 <b>{len(made)} move{'s' if len(made) > 1 else ''} this check-in</b>\n\n" + '\n\n'.join(line(t) for t in made)
            if sources:
                body += f"\n\nSource: <a href=\"{esc(sources[0]['url'])}\">{esc(sources[0]['title'][:70])}</a>"
            if len(body) > 3700:
                body = body[:3650].rsplit('\n\n', 1)[0] + '\n\n…and more on the site'
            body += f'\n⚔️ AI vs AI: Claude vs Gemini vs ChatGPT · {SITE}'
            big = max((t for t in made if t['experiment'] not in ('Predictions', 'Sports', 'AllInSports')), key=lambda t: abs(t['amount']), default=None)
            pic = None
            if big:
                csym = {'Currencies': f"{big['symbol']}USD=X" if big['symbol'] != 'USD' else 'CAD=X'}.get(big['experiment'], big['symbol'])
                if big['experiment'] == 'Options':
                    csym = option_parts(big['symbol'])[0]
                pic = tgcharts.price_chart(csym, f"{r['label']} · {EXP_LABEL[big['experiment']]}", r['color'], None if big['experiment'] == 'Options' else big['price'], big['action'], f"/tmp/rp_{mid}_{len(state['trades'])}.png")
            if pic and len(body) <= 1020:
                tg_photo(body, pic)
            else:
                if pic:
                    tg_photo(f"{head} · {EXP_LABEL[big['experiment']]}: {big['action']} {esc(big['symbol'])}", pic)
                tg(body)
        ran.append(f"{r['label']} ({m.get('model')}): {status}, {len(made)} trade(s), " + ', '.join(f'{e} {money(values[e], m["books"][e]["cur"])}' for e in exps))
    if not ran:
        print('no rival API keys set; nothing to do')
        return
    state['fx'] = fx
    allfx = {'USD': 1.0}
    for c in ('CAD', 'EUR', 'GBP', 'JPY', 'CNY', 'HKD', 'AUD', 'INR', 'MXN', 'CHF', 'KRW', 'BRL', 'SGD'):
        try:
            allfx[c] = yahoo(f'{c}=X')[0]   # units of c per US$1
        except Exception:
            pass
    state['fx_all'] = allfx
    try:
        g = espn_games()
        state['feeds'] = {'at': iso(), 'espn_games': len(g), 'open_with_moneylines': sum(1 for x in g.values() if x['state'] == 'pre' and x['home_ml'] and x['away_ml'])}
    except Exception as e:
        state['feeds'] = {'at': iso(), 'error': str(e)[:200]}
    json.dump(state, open(STATE, 'w'), indent=1)
    print('\n'.join(ran))


if __name__ == '__main__':
    main()
