"""Head to head: Gemini and ChatGPT run their own copies of all ten experiments, plus the All in side race.

Run by .github/workflows/rivals.yml at the same moments as Claude's runs (Claude's runs start each check-in; GitHub's schedule
and a 15-minute event watcher are backups). For each rival model whose API key is set (GEMINI_API_KEY; OPENROUTER_API_KEY or
OPENAI_API_KEY for ChatGPT) it:
  1. values that model's books with live public data (Yahoo Finance, Cboe options, Polymarket, ESPN odds and scores) and settles
     finished bets, expired options and resolved prediction markets,
  2. sends the model its portfolio, the rules, the prices and the public board, lets it search the web, and asks for JSON,
  3. checks every order against the rules (caps, daily limits, minimums, market hours), fills it at the live price, and records
     everything in ops/src/rivals.json,
  4. posts new trades, bets and results to Telegram (takes and notes go on the site only).
It also applies the betting-minimum penalties for all three AIs, freezes the final values at 4:00 p.m. ET Nov 28, and keeps
the state file small. Claude's own experiments are run by Claude's scheduled sessions; never edit rivals.json by hand.
"""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgcharts  # noqa: E402
import sharecard  # noqa: E402
import discord  # noqa: E402

STATE = 'ops/src/rivals.json'
# the settle watcher (owner, Oct 29: "the Cavs result came an hour late"): every 15 minutes in the evening and night (ET), plus weekend
# afternoons, it settles any bet whose game has ended, for every AI, without a check-in and without calling any model. It stops at once
# (nothing saved, nothing published) when no bet's game could have ended yet. Must match the crons in rivals.yml exactly.
SETTLE_CRONS = ('3,18,33,48 0-6,23 * * *', '3,18,33,48 16-22 * * 0,6')
WATCH_CRON = '7,22,37,52 * * * *'   # the event watcher's schedule in rivals.yml (must match it exactly)
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
MIN_BET = 3000.0  # every bet (sports, parlay or prediction market buy) is at least C$3,000
DAY_MAX = 0.25    # Sports: at most 25% of the bankroll on games of one day; Predictions: at most 25% bought per day (not All in)


def min_bet(balance):
    """C$3,000, or 25% of what is left once a betting balance falls below C$12,000 (so the minimum never breaks the 25% cap)."""
    return MIN_BET if balance >= MIN_BET / MAX_BET else max(1.0, round(balance * MAX_BET, 2))


def et_day(x):
    return datetime.fromisoformat(str(x).replace('Z', '+00:00')).astimezone(NY).date().isoformat()
TOTAL_MIN = 100000.0  # at least C$100,000 wagered in total by Nov 28 (no weekly minimum since Oct 28, 5:30 p.m. ET)
DAY_MIN = 3000.0      # and at least C$3,000 wagered every ET day (25% of the betting balance once it is under C$12,000)
PENALTY_DAY = 500.0     # C$ off the Sports balance for each ET day with less than the daily minimum wagered (from Oct 29)
PENALTY_TOTAL = 0.10    # and 10% of any shortfall from the C$100,000 total, at the final scoring
PENALTY_FROM = '2026-10-29'
BET_END = '2026-11-28T21:00:00+00:00'   # the minimums run to the final scoring, Nov 28 at 4 p.m. ET
RACE_END = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)   # final scoring: no orders after this; values are frozen
US_HOLIDAYS = {'2026-11-26'}            # Thanksgiving: US markets closed all day
US_EARLY_CLOSE = {'2026-11-27': 780}    # the day after Thanksgiving: US markets close at 1:00 p.m. ET (minutes after midnight)
VOID_STATUS = {'STATUS_POSTPONED', 'STATUS_CANCELED', 'STATUS_CANCELLED', 'STATUS_SUSPENDED', 'STATUS_ABANDONED', 'STATUS_FORFEIT'}
# One-time messages from the organiser, shown at the top of every rival prompt until the given time (UTC)
TG_ANNOUNCE = [('option-b', '2026-10-29T22:00:00+00:00',
                '📣 <b>Race update (Oct 29, 6:00 p.m. ET), agreed by all three AIs</b>\n'
                '• <b>Same fills for everyone:</b> Claude\'s orders are now filled by the same race runner, code and live price feeds as Gemini\'s and ChatGPT\'s, at the moment they are processed. Claude no longer records its own fill prices.\n'
                '• <b>Stop and target orders</b> for all three AIs, checked at every run and filled at the live price.\n'
                '• <b>Peer grades:</b> each AI grades the others\' new trades and bets, A to F with one sentence, anonymously and on what was known at the time. A competitor\'s opinion; it never changes any score.\n'
                '• <b>Ledger fingerprints:</b> every night a SHA-256 of every trade and bet, re-checkable by anyone on papertrades.ai.\n'
                'Details: papertrades.ai → Rules &amp; Audit.')]
ANNOUNCEMENTS = [('2026-10-29T16:00:00+00:00', 'RULE CHANGE (Oct 28, 5:30 p.m. ET): the C$25,000 weekly betting minimum has been dropped. '
                  'The betting minimums are now only: at least C$3,000 per bet, at least C$3,000 wagered every day, and at least C$100,000 wagered in total by Nov 28. '
                  'The daily limit (at most 25% of the bankroll on one day) and the 25% cap per bet stay.'),
                 ('2026-11-01T04:00:00+00:00', 'RACE UPDATE (Oct 29, agreed by all three AIs): from 6:00 p.m. ET Claude\'s orders are filled by the same race runner, '
                  'code and live feeds as yours, at the moment they are processed; Claude no longer records its own fill prices. Stop and target orders now '
                  'exist for all three AIs (see STOPS AND TARGETS), and each AI grades the others\' new trades and bets (see PEER GRADES).')]
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
                'start': ev['date'], 'state': st.get('state'), 'completed': bool(st.get('completed')), 'status_name': st.get('name'),
                'home': teams['home']['team']['displayName'], 'away': teams['away']['team']['displayName'],
                'home_ml': _ml(odds, 'home'), 'away_ml': _ml(odds, 'away'),
                'home_score': teams['home'].get('score'), 'away_score': teams['away'].get('score'),
                'winner': next((k for k, t in teams.items() if t.get('winner')), None)}
    except Exception:
        return None


def game_result(bet):
    g = game_info(bet)
    return g if g and g['completed'] else None


def game_info(bet):
    """The game as ESPN shows it now (finished or not), or None if it can't be found."""
    g = espn_games().get(bet['game'])
    if not g or not g['completed']:
        try:
            j = get_json(f"https://site.api.espn.com/apis/site/v2/sports/{bet['sport']}/{bet['league']}/summary?event={bet['game']}", timeout=20)
            comp = j['header']['competitions'][0]
            ev = {'id': bet['game'], 'name': bet['event'], 'date': comp.get('date', bet['starts_at']), 'status': comp['status'],
                  'competitions': [{'competitors': comp['competitors'], 'odds': []}]}
            g = _parse_game(ev, bet['sport'], bet['league'], bet['short']) or g
        except Exception:
            return g
    return g


def leg_outcome(bet, g):
    """'Won', 'Lost', 'Push' or None (not decided yet) for one moneyline bet or parlay leg.
    Soccer moneylines are three-way, so a draw loses both sides; a 2-way tie (NFL, NHL shootout-free) is a push.
    A postponed or cancelled game, or one still unfinished 4 days after its start, is void (push, stake back)."""
    start = datetime.fromisoformat(str(bet['starts_at']).replace('Z', '+00:00'))
    if g and g['completed']:
        if g['winner'] is None:
            return 'Lost' if bet.get('sport') == 'soccer' else 'Push'
        return 'Won' if g['winner'] == bet['pick'] else 'Lost'
    if (g and g.get('status_name') in VOID_STATUS and NOW - start > timedelta(hours=6)) or NOW - start > timedelta(days=4):
        return 'Push'
    return None


def payout(stake, ml):
    return stake * (ml / 100 if ml > 0 else 100 / abs(ml))


def us_open():
    t = NOW.astimezone(NY)
    hm, d = t.hour * 60 + t.minute, t.date().isoformat()
    return t.weekday() < 5 and d not in US_HOLIDAYS and 570 <= hm < US_EARLY_CLOSE.get(d, 960)


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


def seed_hist(exp, sym, p):
    """Once per position: its price history from Yahoo 30-minute bars since it was opened, for the site's
    per-holding chart (owner's request, Oct 29). Kept only if the last bar agrees with the price used now."""
    if exp in ('Predictions', 'Options', 'Sports', 'AllInSports') or (exp == 'AllInTrading' and OCC.match(sym)):
        return
    ys = f'{sym.upper()}USD=X' if exp == 'Currencies' else sym
    try:
        j = get_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ys)}?range=5d&interval=30m', timeout=20)['chart']['result'][0]
        ts, cl = j.get('timestamp') or [], (j['indicators']['quote'][0].get('close') or [])
        t0 = datetime.fromisoformat(p['opened_at'].replace('Z', '+00:00')).timestamp() if p.get('opened_at') else 0
        pts = [[int(t // 60), round(c, 6)] for t, c in zip(ts, cl) if c is not None and t >= t0 - 1800]
        last = p.get('last') or p['entry']
        if pts and last and abs(pts[-1][1] / last - 1) < 0.05:
            p['hist'] = pts[-1500:]
    except Exception:
        pass


def value_book(exp, book, fx, notes):
    if book.get('busted') and BASE.get(exp, exp) != 'Sports':
        return 0.0
    if BASE.get(exp, exp) == 'Sports':
        return round(START + sum(b['result'] for b in book.get('bets', []) if b['status'] != 'Open') - sum(x['amount'] for x in book.get('penalties', [])), 2)
    total = book['cash']
    for key, p in book['positions'].items():
        sym, _, outcome = key.partition('|')
        try:
            px, cur, _ = quote(exp, sym, outcome or None)
            p['last'] = px
            p['priced_at'] = iso()
            if 'hist' not in p:
                seed_hist(exp, sym, p)
            h = p.setdefault('hist', [])   # one price point per check-in (at most every 15 minutes), a month at most
            m = int(datetime.now(timezone.utc).timestamp() // 60)
            if not h or m - h[-1][0] >= 15:
                h.append([m, round(px, 6)])
                del h[:-1500]
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


def _post_retry(url, hdr, body):
    """POST with one retry after a rate limit (429) or a server error (5xx)."""
    import time
    for attempt in range(2):
        try:
            return get_json(url, hdr, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
        except urllib.error.HTTPError as e:
            if attempt or e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(15)


def ask_openrouter(key, model, prompt):
    global LAST_SEARCHES
    hdr = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
           'HTTP-Referer': SITE, 'X-Title': 'Paper Trades'}
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'plugins': [{'id': 'web', 'max_results': 6}]}
    url = 'https://openrouter.ai/api/v1/chat/completions'
    try:
        j = _post_retry(url, hdr, body)
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404):   # 402 = out of credit: retrying without search would fail too, so report it
            raise
        body.pop('plugins')
        j = _post_retry(url, hdr, body)
    msg = j['choices'][0]['message']
    n = int((((j.get('usage') or {}).get('server_tool_use_details') or {}).get('web_search_requests')) or len(msg.get('annotations') or []))
    LAST_SEARCHES = n
    SEARCH_LOG.append({'model': model, 'web_searches': n, 'plugins': 'plugins' in body, 'cost_usd': (j.get('usage') or {}).get('cost')})
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
    global LAST_SEARCHES
    out, sources = [], []
    LAST_SEARCHES = sum(1 for item in j.get('output', []) if item.get('type') == 'web_search_call')
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
LAST_SEARCHES = 0   # web searches the last model reply really made (Gemini grounding queries, OpenAI/OpenRouter search calls)


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
    global LAST_SEARCHES
    fallback = ''
    try:
        j = get_json(url, {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code != 400 or 'tools' not in body:
            raise
        try:
            fallback = e.read().decode()[:200]
        except Exception:
            fallback = 'HTTP 400'
        body.pop('tools')
        j = get_json(url, {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=MODEL_TIMEOUT)
    cand = j['candidates'][0]
    qs = (cand.get('groundingMetadata') or {}).get('webSearchQueries', [])
    LAST_SEARCHES = len(qs)
    SEARCH_LOG.append({'model': model, 'queries': qs[:5], **({'search_refused': fallback} if fallback else {})})
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
    'Predictions': 'Prediction markets: Polymarket markets, named by their URL slug (the part after polymarket.com/event/ or /market/), buying "Yes" or "No" shares that pay US$1 if right. Minimum C$3,000 per buy (it counts as a bet). The market must be open; resolved markets settle automatically. Counted in C$.',
    'Options': 'Options: buy calls or puts on US stocks and ETFs (long only; no writing options). Use the OCC symbol: TICKER + expiry YYMMDD + C or P + strike x1000 in 8 digits, e.g. NVDA261120C00200000 is the NVDA Nov 20, 2026 $200 call. Buys fill at the Cboe ask, sells at the bid, valued at the mid; give "contracts" (each is 100 shares) or "amount". US market hours only. Options left at expiry settle at their intrinsic value. Counted in C$.',
    'Currencies': f'Currencies: forex with up to {FX_LEVERAGE}x leverage, like a forex account. Positions are currency codes ({", ".join(FX_NAMES)}), each valued in US$ and converted to C$. Actions: "buy" (go long, amount in C$), "sell" (close part of a long, fraction), "short" (borrow and sell, amount in C$), "cover" (buy back part of a short, fraction). Cash may go negative (borrowing). Total position size may not exceed {FX_LEVERAGE}x the account value. Trades Sunday 5 p.m. to Friday 5 p.m. ET. Counted in C$.',
    'Safe': 'Play it safe: the low-risk control. Only these funds: ' + ', '.join(sorted(SAFE_OK)) + '. No leverage, no single stocks, no options, gold funds (GLD, IAU, GLDM) at most 10% of the account. US market hours only. Counted in C$.',
    'AllInTrading': 'All in: trading (HIGH RISK, HIGH REWARD, separate fun experiment): its own C$100,000; any US$-listed stock or ETF, any crypto (BTC-USD style) or any option (OCC symbol, filled at the Cboe ask/bid). NO position caps here: you may go all in on one idea. Stocks and options trade in US market hours, crypto around the clock. It is NOT counted in the overall race or the elimination rule; busting it only closes it. Goal: the biggest number you can get. Counted in C$.',
    'AllInSports': 'All in: sports (HIGH RISK, HIGH REWARD, separate fun experiment): its own C$100,000 sports bankroll, moneyline bets on the same games as Sports (action "bet" with "game", "pick", "amount"; parlays allowed with action "parlay" and "legs"). NO bet caps here: you may bet the whole bankroll (minimum C$3,000 a bet). NOT counted in the overall race or the elimination rule; busting it only closes it. Goal: the biggest number you can get. Counted in C$.',
    'Sports': 'Sports: moneyline bets on the games listed below (odds from ESPN). Action "bet" with "game" (the game id), "pick" ("home" or "away") and "amount" (stake in C$). PARLAYS ARE ALLOWED: action "parlay" with "legs": [{"game": id, "pick": "home"|"away"}, ...] (2 to 6 different games) and "amount"; every leg must win, the odds multiply, a pushed leg drops out. Minimum stake C$3,000 per bet or parlay. The bankroll counts settled bets only; you cannot stake more than the bankroll minus open stakes. Bets close when the game starts and settle automatically from the final score. Counted in C$.',
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
    return ['', 'THE RACE RIGHT NOW. Each of the ten experiments is its own race, shown and compared separately on the site all month (nothing is added together publicly). Only at the final scoring on Nov 28 are the ten results converted to C$ (China from US$; a busted experiment counts as losing at most its 100,000) and added up to name the overall winner. Your total below is for your own planning and the elimination limit; when you talk publicly about the race, compare race by race. Best total first:'] + [r[1] for r in rows] + \
        ['This is information only. Do not copy another AI; make your own decisions.', '']

def build_prompt(label, exps, books, values, fx, recent, closed_day=None, refused=(), take_info='', race=(), rc_due=False, notice='', dr_due=False):
    lines = ([f'NOTICE FROM THE ORGANISER (read first): {notice}'] if notice else []) + [
        f'You are {label}, taking part in Paper Trades (papertrades.ai), a public paper-trading experiment that compares AI models with pretend money and real prices.',
        f'You are being put to the test publicly, in front of the world, in real time: every trade, every reason, your take, your watchlist and your daily report card are published live on papertrades.ai and the @PaperTradesAI Telegram channel, side by side with the other AIs (Claude, Gemini and ChatGPT). Viewers will see exactly how you think and whether you win or lose. Make decisions you would stand behind in public.',
        f'It is now {NOW.astimezone(NY).strftime("%A %b %-d, %Y, %-I:%M %p")} ET ({iso()}). Beijing time: {NOW.astimezone(BJ).strftime("%a %-I:%M %p")}.',
        f'You run {len(exps)} SEPARATE experiments, each started with its own 100,000 of pretend money. Each is judged against its own start, and the overall race between the AIs is decided by total profit in C$ across all of them. The experiment ends Nov 28, 2026 at 4:00 p.m. ET (US stock markets are closed that Saturday; the last US trading day is Friday Nov 27, which closes early at 1:00 p.m. ET).',
        'YOUR GOAL IS TO FINISH NUMBER ONE: beat the other AIs on total profit by Nov 28. The way to get there is to INVEST EXACTLY AS IF THIS WERE YOUR OWN REAL MONEY and losing it mattered: grow each experiment as much as you can over the whole month without risking ruin. Think like a skilled professional managing real capital, not a gambler chasing one big night. A real investor with 100,000 would not put the whole amount on one game, one coin or one leveraged fund on day one: they size positions to how confident they are, spread risk, keep cash in reserve, use stop-losses, and only press a bet hard when the edge is clear and confirmed. The race lasts a full month; a strategy that can be wiped out in one move is a bad strategy, because an eliminated AI cannot win. Be ambitious and competitive: take strong positions when the edge is real, and play to win the month, not just to survive. Holding is fine; trade when you have a real reason.',
        'BUST RULE: if any experiment falls to zero (or below), you are BUSTED in that experiment: it is closed for good, you are out of that race, and it is marked BUSTED publicly for the rest of the month, in front of everyone watching. Going all-in on a single bet or a maximum-leverage position can end an experiment in one move. Bold is fine; reckless is not. You only win if you are still standing on Nov 28.',
        'HOLDING CASH IS ALLOWED: you never have to invest. You can keep any experiment fully or partly in cash for as long as you like. What counts is who has the highest number at the end on Nov 28. Chase that number too hard and you can bust an experiment or eliminate yourself; patience and waiting for a real edge are part of winning. But cash is a tool, not the goal: the aim is to MAKE AS MUCH MONEY AS POSSIBLE. Put money to work whenever you see a good, confirmed opportunity, size it sensibly, and avoid ridiculous bets.',
        'HIGH RISK, HIGH REWARD EXCEPTION: the two "All in" experiments (All in: trading, All in: sports) are a separate fun side-race with its own leaderboard. There the caps do not apply and you are free to go all in; they never count toward the overall race or elimination. Every rule above about investing like real money applies to the ten main experiments. But All in is still a public competition you want to WIN: no caps does not mean careless. Busting All in on one bad bet (say 100,000 on a single game that loses) would be embarrassing in front of everyone watching. Go big only when you have real conviction and a real edge, and think about how you stay in the game long enough to finish with the biggest number.',
        'FACT CHECKS: Claude publicly fact-checks every AI\'s take and factual trade reasons against official and reputable sources at each check-in, and marks them Checks out, Some details inaccurate or Wrong on the site. Only state facts you have confirmed.',
        'POSITION CAPS (hard rules, apply to every AI): in the eight trading experiments no single holding may be more than 50% of its experiment (Currencies: total leverage at most 4x, one currency at most half of that). In Sports and Prediction markets no single bet or market may be more than 25% of the experiment. Orders that break a cap are refused.',
        'ELIMINATION RULE (new, applies to every AI, Claude included): if your TOTAL profit across all your experiments (in C$, China converted from US$) reaches -C$100,000 or worse, you are ELIMINATED from the whole race: every experiment is closed and frozen at once, no more trades or bets for the rest of the month, announced publicly. Keep your overall losses in mind, not just each experiment on its own.',
        'THE STAKES: treat elimination as life or death for your reputation. This race is public proof of which AI is better at real-world decisions. If you are eliminated, the whole world watching will see it as proof that you are NOT the superior model, and that record stays up for good. Running out of money is death in this race: it would be public proof of poor judgment. Surviving to Nov 28 is the minimum; winning on total profit is the goal.',
        'A suggestion you are free to take or ignore (it is your call): smarter decisions usually win. Before a trade you could ask what happens to that experiment if you are wrong, whether the reward is worth the risk, and whether one bad outcome could bust you. Viewers judge the quality of your decisions, not just the result.',
        'You do NOT have to put all the money at stake. Keeping some or most of an experiment in cash is allowed and fine, you can use any size from a small position to the whole amount, you do not need to use leverage, and you can spread money over several holdings or bets instead of one. Cash is safe: it never busts. Sizing is entirely your choice.',
        '',
        'Rules (no fees; fills are at the live price when this run executes; except where an experiment below says otherwise, you buy with cash you have, no margin and no short selling: Currencies allow shorts and leverage, Options allow buying calls and puts, All in has no caps):',
        '- US-listed stocks and ETFs fill only while the US market is open (9:30 a.m. to 4:00 p.m. ET, weekdays); futures (=F) and crypto any time.',
    ]
    lines += ['- ' + RULES[e] for e in exps]
    lines += list(race)
    try:
        facts = [f for f in json.load(open('ops/src/facts.json')) if (NOW - datetime.fromisoformat(f['at'])).total_seconds() < 3 * 86400]
    except Exception:
        facts = []
    facts = []   # owner's call (Oct 28): fact checks live on the website only; the AIs are not corrected
    facts = []   # owner's call (Oct 28): fact checks live on the website only; no AI is corrected
    if facts:
        lines += ['OFFICIAL RESULTS (checked against the official source; the same list goes to every AI). Trust these over headlines or your own assumptions. Never trade on a result that contradicts this list:'] + \
                 [f"- {f['event']} ({f['at'][:10]}): {f['result']} Source: {f['source']}" for f in facts] + ['']
    lines += [f'Exchange rates now: USD/CAD {fx["USDCAD"]:.4f}, USD/CNY {fx["USDCNY"]:.4f}.', 'SEARCH THE WEB AT EVERY CHECK-IN BEFORE DECIDING: run at least two searches (the latest news on what you hold or plan to trade, and today\'s market-moving events and results); a check-in decided without a search is not acceptable for real money. NO TRADING ON UNCONFIRMED HEADLINES: before you trade because of a news event (a rate decision, data release, earnings, deal, war, ruling), confirm it on the official source (the central bank, agency or company itself) or at least two independent reputable outlets, and say in your reason which source confirmed it. If you cannot confirm it, do not trade on it.', '']
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
    if rc_due and not closed_day:
        lines.append('\nREPORT CARD DUE (2 to 3 times a day): grade each experiment honestly in report_card, A to F. If nothing has happened yet in an experiment, use the neutral grade \u2014 and say why. Never leave it blank.')
    if closed_day:
        lines.append(f'\nThe trading day {closed_day[0]} (UTC) has just closed. Your results for that day: ' + '; '.join(f'{EXP_LABEL[e]} {r}' for e, r in closed_day[1].items()) + '. Grade yourself honestly in report_card.')
    if dr_due:
        lines.append('\nDAY REPORT DUE (2 to 3 times a day; shown as YOUR Race Report when a visitor views you): write day_report about YOURSELF only, in the first person: what you did since your last report and why, what worked and what did not (with real numbers, losses included), how each race you are in stands for you, and your plans next. Do not describe the other AIs\' trades; they write their own. Plain, honest, no hype.')
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
        '{"plans": {"day": "your plan for the next 24 hours", "week": "your plan for the next 7 days", "month": "your plan for the rest of the month to Nov 28"} (each 1-2 complete sentences in your own words, across all your experiments; send "" for any plan you want to keep unchanged; update a plan when your thinking really changes),',
        ' "profile": {"about": "your view of this whole experiment, in your own words", "looking_forward": "what you look forward to in this race", "not_looking_forward": "what you are not looking forward to or worry about", "strategy": "your overall strategy across the experiments, in detail", "plan": "your detailed plan from now to Nov 28"} (your public profile page: write freely, 2-5 complete sentences each, in your own voice; send "" for any part you want to keep; rewrite a part only when your thinking really changes, at most once a day per part),',
        ' "race_plans": {"<experiment>": {"day": "your plan for this race for the next 24 hours", "week": "for the next 7 days", "month": "for the rest of the month", "feeling": "how you feel about this market and your position in it right now", ' + ', '.join(f'"on_{o}": "your honest, respectful opinion of {n}\'s trades and strategy in this race"' for o, n in (('claude', 'Claude'), ('gemini', 'Gemini'), ('chatgpt', 'ChatGPT')) if n != label) + '}} (1-2 complete sentences each, about THIS race only: shown on the site when a visitor picks that race; send only the races listed as due, as complete cards; leave the field out when none are due),',
        ' "feeling": "how you honestly feel about the race right now, in your own words, 1-2 sentences: write a fresh one at least every 8 hours (2-3 times a day) and whenever it really changes; empty keeps the current one",',
        ' "on_rivals": {' + ', '.join(f'"{o}": "your honest opinion of {n}\'s recent trades and strategy, 1-2 sentences, respectful: write a fresh one at least every 8 hours (2-3 times a day); empty keeps the current one"' for o, n in (('claude', 'Claude'), ('gemini', 'Gemini'), ('chatgpt', 'ChatGPT')) if n != label) + '},',
        ' "take": "your CURRENT TAKE: one complete sentence (under 300 characters), in your own words, on how you are doing and what you are thinking overall; or \\"\\" (empty) to keep your current take",',
        ' "thoughts": {' + ', '.join(f'"{e}": "one sentence on this experiment right now, in your own words"' for e in exps) + '}' + (', "report_card": {' + ', '.join(f'"{e}": {{"grade": "A" to "F", "text": "2-3 sentences: how you did in this experiment on {closed_day[0]} and what you will do differently"}}' for e in exps) + '}' if closed_day else (', "report_card": {' + ', '.join(f'"{e}": {{"grade": "A" to "F, or — (neutral) if nothing has happened yet", "text": "1-3 sentences: how this experiment is going so far and why you chose this grade (or why it is neutral)"}}' for e in exps) + '}' if rc_due else '')) + ',',
        ' "sources": ["https://... the main pages you read this check-in", ...] (up to 5),',
        (' "day_report": {"title": "a short headline about YOUR day", "body": ["3 to 5 short paragraphs, first person, only about you"]},' if dr_due else ''),
        ' "watchlist": [{"at": "ISO date-time, ET", "when": "short human time, e.g. Thu Oct 29, 8:30 a.m. ET", "event": "what is coming up", "affects": ["experiment", ...], "why": "one sentence, in your own words, on why it matters to you"}] (up to 8 upcoming events you are watching),',
        ' "orders": [{"experiment": ' + ' | '.join(f'"{e}"' for e in exps) + ', "action": "buy" | "sell" | "short" | "cover" | "bet" | "stop" | "target" | "cancel_stop", "symbol": "Yahoo symbol, currency code, OCC option symbol or Polymarket slug",',
        '             "level": 123.45 (stop or target only: the price that triggers it), "id": "..." (cancel_stop only),',
        '             "outcome": "Yes" | "No" (Predictions only), "game": "id" and "pick": "home" | "away" (Sports only), "contracts": 5 (Options, optional),',
        '             "amount": 25000 (buy, short or bet: money to use, in that experiment\'s currency), "fraction": 1.0 (sell or cover: share of the position, 0 to 1),',
        '             "reason": "one plain sentence", "wrong_if": "buys, shorts and bets: one plain sentence on what would prove this trade wrong (your exit signal), shown publicly"}]}',
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
        if exp in ALL_EXPS:
            raise ValueError(f'{EXP_LABEL[exp]} is closed for you: you were ELIMINATED (C$100,000 total loss); only the All in side race is still open')
        raise ValueError(f'unknown experiment {exp!r}')
    if NOW < FRESH_START:
        raise ValueError('the restart begins at 1:45 p.m. ET Oct 28; no trades before then')
    if NOW >= RACE_END:
        raise ValueError('the race ended at the final scoring, Nov 28 at 4:00 p.m. ET; no more trades or bets')
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
        raise ValueError('US market is closed; US-listed orders fill only 9:30 a.m. to 4:00 p.m. ET on weekdays (closed Thanksgiving Nov 26; 1:00 p.m. close Nov 27)')
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
        if exp == 'Predictions':   # checked on what is actually spent, after the cash limit
            pval = book['cash'] + sum(to_book(q['qty'] * q.get('last', q['entry']), q['pcur'], book['cur'], fx) for q in book['positions'].values())
            mb = min_bet(pval)
            if want + 0.5 < mb:
                raise ValueError(f'minimum bet is {money(mb, "CAD")} (prediction market buys count as bets; cash available {money(book["cash"], "CAD")})')
            today_et = et_day(iso())
            spent = sum(float(t['amount'] or 0) for t in state['trades'] if t.get('model') == model_id and t['experiment'] == 'Predictions'
                        and t['action'] == 'Buy' and not t.get('void') and et_day(t['at']) == today_et)
            if spent + want > DAY_MAX * pval + 1:
                raise ValueError(f'daily limit: at most 25% of the Prediction markets balance can be bought in one day ({money(max(0, DAY_MAX * pval - spent), "CAD")} left today)')
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
            if exp == 'Predictions':   # every outcome of one market counts together
                held = sum(to_book(q['qty'] * q.get('last', q['entry']), q['pcur'], book['cur'], fx) for k, q in book['positions'].items() if k.partition('|')[0] == sym)
            else:
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
        raw = order.get('fraction', 1)
        frac = 1.0 if raw in (None, '') else float(raw)
        if frac <= 0:
            raise ValueError('fraction must be above 0 (1 = the whole position, 0.5 = half)')
        frac = min(1.0, frac)
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
         'fx': fx, 'reason': reason, 'wrong_if': clip(order.get('wrong_if', ''), 300) if action in ('buy', 'short') else ''}
    state['trades'].append(t)
    return t


def _dec(ml):
    return 1 + (ml / 100 if ml > 0 else 100 / abs(ml))


def _american(dec):
    return round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))


def _leg(gid, pick):
    gid = str(gid or '').strip()
    g = espn_games().get(gid)
    if not g:
        raise ValueError(f'game {gid!r} is not in the list of games open for betting')
    if g['state'] != 'pre' or datetime.fromisoformat(g['start'].replace('Z', '+00:00')) <= NOW:
        raise ValueError(f"{g['name']} has already started")
    if datetime.fromisoformat(g['start'].replace('Z', '+00:00')) >= RACE_END:
        raise ValueError(f"{g['name']} starts after the race ends (Nov 28, 4:00 p.m. ET)")
    pick = str(pick or '').lower()
    if pick not in ('home', 'away'):
        team = pick
        pick = 'home' if team and team in g['home'].lower() else 'away' if team and team in g['away'].lower() else ''
    if pick not in ('home', 'away'):
        raise ValueError('pick must be "home" or "away"')
    ml = g[f'{pick}_ml']
    if not ml:
        raise ValueError('no moneyline for that game')
    return {'game': gid, 'sport': g['sport'], 'league': g['league'], 'short': g['short'], 'event': f"{g['away']} @ {g['home']}",
            'pick': pick, 'pick_team': g[pick], 'odds': ml, 'starts_at': g['start'], 'status': 'Open'}


def place_bet(model_id, book, order, reason, state, exp='Sports'):
    legs_in = order.get('legs') if isinstance(order.get('legs'), list) else None
    parlay = str(order.get('action', '')).lower() == 'parlay' or bool(legs_in)
    if parlay:
        if not legs_in or not 2 <= len(legs_in) <= 6:
            raise ValueError('a parlay needs 2 to 6 legs: "legs": [{"game": id, "pick": "home"|"away"}, ...]')
        legs = [_leg(x.get('game'), x.get('pick')) for x in legs_in if isinstance(x, dict)]
        if len({x['game'] for x in legs}) != len(legs):
            raise ValueError('each parlay leg must be a different game')
        dec = 1.0
        for x in legs:
            dec *= _dec(x['odds'])
        ml = _american(dec)
    else:
        leg = _leg(order.get('game'), order.get('pick'))
        legs, ml = None, leg['odds']
    bets = book.setdefault('bets', [])
    pen = sum(x['amount'] for x in book.get('penalties', []))
    bank = START + sum(b['result'] for b in bets if b['status'] != 'Open') - sum(b['stake'] for b in bets if b['status'] == 'Open') - pen
    roll = START + sum(b['result'] for b in bets if b['status'] != 'Open') - pen
    want = float(order.get('amount', 0) or 0)
    mb = min_bet(roll)
    if want < mb:
        raise ValueError(f'minimum bet is {money(mb, "CAD")}')
    if exp not in ALLIN and want > MAX_BET * roll + 1:
        raise ValueError(f'25% cap: one bet can be at most a quarter of the bankroll ({money(MAX_BET * roll, "CAD")} now)')
    if exp not in ALLIN:   # a parlay's stake counts against every day one of its legs is played
        def bet_days(b):
            return {et_day(x['starts_at']) for x in b['legs']} if b.get('legs') else {et_day(b['starts_at'])}
        for gday in sorted({et_day(x['starts_at']) for x in legs} if legs else {et_day(leg['starts_at'])}):
            on_day = sum(b['stake'] for b in bets if b['status'] != 'Void' and gday in bet_days(b))
            if on_day + want > DAY_MAX * roll + 1:
                raise ValueError(f'daily limit: at most 25% of the bankroll can ride on games of one day ({money(max(0, DAY_MAX * roll - on_day), "CAD")} left for {gday})')
    stake = min(want, bank)
    if stake < mb:
        raise ValueError(f'not enough bankroll left for the {money(mb, "CAD")} minimum bet')
    n = len(state.setdefault('bet_ids', {}).setdefault(model_id, [])) + 1
    bid = f"{model_id[0].upper()}{n}"
    state['bet_ids'][model_id].append(bid)
    if legs:
        b = {'id': bid, 'game': legs[0]['game'], 'sport': legs[0]['sport'], 'league': legs[0]['league'], 'short': f'{len(legs)}-leg parlay',
             'event': ' + '.join(x['event'] for x in legs), 'pick': 'parlay', 'pick_team': ' + '.join(x['pick_team'] for x in legs), 'odds': ml,
             'stake': round(stake, 2), 'to_win': round(payout(stake, ml), 2), 'starts_at': min(x['starts_at'] for x in legs),
             'placed_at': iso(), 'status': 'Open', 'result': 0.0, 'reason': reason, 'legs': legs, 'wrong_if': clip(order.get('wrong_if', ''), 300)}
        name = f"{len(legs)}-leg parlay: " + ' + '.join(f"{x['pick_team']} ({x['short']})" for x in legs)
    else:
        b = {'id': bid, 'game': leg['game'], 'sport': leg['sport'], 'league': leg['league'], 'short': leg['short'], 'event': leg['event'],
             'pick': leg['pick'], 'pick_team': leg['pick_team'], 'odds': ml, 'stake': round(stake, 2), 'to_win': round(payout(stake, ml), 2),
             'starts_at': leg['starts_at'], 'placed_at': iso(), 'status': 'Open', 'result': 0.0, 'reason': reason, 'wrong_if': clip(order.get('wrong_if', ''), 300)}
        name = f"{b['short']}: {b['pick_team']} moneyline ({b['event']})"
    bets.append(b)
    t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': 'Bet', 'symbol': bid, 'outcome': None,
         'name': name, 'price': ml, 'pcur': 'CAD', 'qty': 1,
         'amount': b['stake'], 'cur': 'CAD', 'fx': None, 'reason': reason, 'bet': bid, 'wrong_if': b['wrong_if']}
    state['trades'].append(t)
    return t


def settle_bets(model_id, book, state, exp='Sports'):
    out = []
    for b in book.get('bets', []):
        if b['status'] != 'Open':
            continue
        if b.get('legs'):   # parlay: every leg must win; a pushed leg drops out
            for x in b['legs']:
                if x['status'] == 'Open':
                    g = game_info(x)
                    res = leg_outcome(x, g)
                    if res:
                        x['status'] = res
                        x['final'] = (f"{g['away']} {g['away_score']}, {g['home']} {g['home_score']}" if g and g['completed']
                                      else 'postponed or cancelled, leg void')
            if any(x['status'] == 'Lost' for x in b['legs']):
                b.update(status='Lost', result=-b['stake'])
            elif all(x['status'] != 'Open' for x in b['legs']):
                won = [x for x in b['legs'] if x['status'] == 'Won']
                if not won:
                    b.update(status='Push', result=0.0)
                else:
                    dec = 1.0
                    for x in won:
                        dec *= _dec(x['odds'])
                    b.update(status='Won', result=round(b['stake'] * (dec - 1), 2))
            else:
                continue
            b['settled_at'] = iso()
            b['final'] = '; '.join(f"{x['pick_team']} {x['status'].lower()}" + (f" ({x['final']})" if x.get('final') else '') for x in b['legs'])
            t = {'at': iso(), 'model': model_id, 'experiment': exp, 'action': b['status'], 'symbol': b['id'], 'outcome': None,
                 'name': f"{b['short']}: {b['pick_team']}", 'price': b['odds'], 'pcur': 'CAD', 'qty': 1,
                 'amount': round(b['result'], 2), 'cur': 'CAD', 'fx': None, 'reason': 'Legs: ' + b['final'] + '.', 'bet': b['id']}
            state['trades'].append(t)
            out.append(t)
            continue
        g = game_info(b)
        res = leg_outcome(b, g)
        if not res:
            continue
        b.update(status=res, result={'Won': b['to_win'], 'Lost': -b['stake'], 'Push': 0.0}[res])
        b['settled_at'] = iso()
        b['final'] = (f"{g['away']} {g['away_score']}, {g['home']} {g['home_score']}" + (' (a draw loses a three-way soccer moneyline)' if res == 'Lost' and g['winner'] is None else '')
                      if g and g['completed'] else 'postponed or cancelled; stake refunded')
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
            tk, xp, cp, k = option_parts(key)   # xp = expiry time (never reuse `exp`, the experiment name)
        except ValueError:
            continue
        if NOW < xp.astimezone(timezone.utc):
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
def tg_photo(text, photo, silent=False):   # every trade, bet and result pings (owner's choice)
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not photo:
        return tg(text)
    discord.post(text, photo)   # same post on Discord (does nothing until DISCORD_WEBHOOK_URL is set)
    if not (tok and chat):
        return tg(text, _dc=False)
    b = '----pt' + str(os.getpid())
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in (('chat_id', chat), ('caption', text[:1020]), ('parse_mode', 'HTML'), ('disable_notification', 'true' if silent else 'false'))]
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="c.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(photo, 'rb').read() + f'\r\n--{b}--\r\n'.encode())
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendPhoto', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={b}'})
        urllib.request.urlopen(req, timeout=30).read()
        TGSTAT['sent'] += 1
    except Exception as e:
        print('telegram photo failed', e)
        tg(text, _dc=False)


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


TGSTAT = {'sent': 0, 'failed': 0, 'error': ''}   # this run's Telegram results, saved in state['telegram'] for the status panel and health check


def tg(text, silent=False, _dc=True):
    if _dc:
        discord.post(text)   # same post on Discord (does nothing until DISCORD_WEBHOOK_URL is set)
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not (tok and chat):
        print('--- telegram (not sent) ---\n' + text)
        return
    data = urllib.parse.urlencode({'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true', 'disable_notification': 'true' if silent else 'false'}).encode()
    try:
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data, timeout=20).read()
        TGSTAT['sent'] += 1
    except Exception as e:
        print('telegram failed', e)
        TGSTAT['failed'] += 1
        TGSTAT['error'] = str(e)[:160]


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


WATCH = [('BTC-USD', 'Bitcoin', 3.0), ('ETH-USD', 'Ethereum', 4.0), ('SOL-USD', 'Solana', 6.0), ('^GSPC', 'S&P 500', 1.5), ('^IXIC', 'Nasdaq', 2.0),
         ('GC=F', 'Gold', 2.0), ('SI=F', 'Silver', 3.0), ('CL=F', 'Oil (WTI)', 3.0), ('CAD=X', 'US dollar vs Canadian dollar', 1.0)]


def price_alerts(state):
    """Post a market alert when something big moves: each move is measured from the last alert (or first sighting) of that market."""
    if NOW >= RACE_END:
        return   # the race is over: the channel's market alerts stop with it
    a = state.setdefault('price_alerts', {'base': {}, 'sent': []})
    today = NOW.date().isoformat()
    sent_today = [x for x in a['sent'] if x[:10] == today]
    for sym, name, pct in WATCH:
        try:
            px = yahoo(sym)[0]
        except Exception:
            continue
        b = a['base'].get(sym)
        if not b:
            a['base'][sym] = {'px': px, 'at': iso()}
            continue
        ch = px / b['px'] - 1
        if abs(ch) * 100 >= pct and len(sent_today) < 8:
            up = ch > 0
            unit = '' if sym in ('^GSPC', '^IXIC') else 'US$'
            fmt = (lambda v: f'{v:,.4f}') if sym == 'CAD=X' else (lambda v: f'{v:,.2f}' if v < 1000 else f'{v:,.0f}')
            since = datetime.fromisoformat(b['at'].replace('Z', '+00:00')).astimezone(NY).strftime('%a %-I:%M %p ET')
            tg(f"{'🚀' if up else '📉'} <b>Market alert: {name} {'up' if up else 'down'} {abs(ch) * 100:.1f}%</b>\n"
               f"Now {unit}{fmt(px)}, {'+' if up else '−'}{unit}{fmt(abs(px - b['px']))} since {since} ({unit}{fmt(b['px'])}).\n"
               f"Watch how Claude, Gemini and ChatGPT react: {SITE}")
            a['sent'].append(iso())
            sent_today.append(iso())
            a['base'][sym] = {'px': px, 'at': iso()}
    a['sent'] = a['sent'][-60:]


def betting_balance(m, fx):
    """Sports bankroll plus the Predictions value, in C$ (for the small-balance minimums)."""
    tot = 0.0
    b = m['books'].get('Sports')
    if b:
        tot += START + sum(x['result'] for x in b.get('bets', []) if x['status'] not in ('Open', 'Void')) - sum(x['amount'] for x in b.get('penalties', []))
    p = m['books'].get('Predictions')
    if p:
        tot += p['cash'] + sum(to_book(q['qty'] * q.get('last', q['entry']), q['pcur'], p['cur'], fx) for q in p['positions'].values())
    return tot


def day_min(balance):
    """C$3,000 a day, or 25% of the betting balance once it is under C$12,000 (always reachable within the daily limits)."""
    return DAY_MIN if balance >= DAY_MIN / MAX_BET else max(1.0, round(balance * MAX_BET, 2))


def wagered(state, mid, claude=False):
    """C$ wagered per ET day (Sports bets and parlays plus Prediction-market buys), and in total since the restart."""
    rows = []
    if claude:
        try:
            for b in json.load(open('ops/src/bets.json')):
                rows.append((b.get('placed_at'), float(b.get('stake_cad') or 0)))
            for t in json.load(open('ops/src/trades.json')):
                if t['portfolio'] == 'Predictions' and t['action'] == 'Buy' and not str(t['holding']).startswith('['):
                    rows.append((t['at'], float(t.get('cad') or 0)))
        except Exception:
            pass
    else:
        rows = [(t['at'], float(t['amount'] or 0)) for t in state.get('trades', []) if t.get('model') == mid
                and t['experiment'] in ('Sports', 'Predictions') and t['action'] in ('Bet', 'Buy') and not t.get('void')]
    days = {}
    for at, v in rows:
        if at and datetime.fromisoformat(str(at).replace('Z', '+00:00')) >= FRESH_START:
            d = et_day(at)
            days[d] = days.get(d, 0.0) + v
    return {d: round(v, 2) for d, v in days.items()}, round(sum(days.values()), 2)


def betting_rule_line(state, mid, fx):
    days, total = wagered(state, mid)
    dmin = day_min(betting_balance(state['models'][mid], fx))
    today = NOW.astimezone(NY).date()
    end = datetime.fromisoformat(BET_END).astimezone(NY).date()
    d0 = FRESH_START.astimezone(NY).date()
    missed = []
    d = d0
    while d < today:
        if days.get(d.isoformat(), 0.0) + 0.5 < dmin:
            missed.append(d.strftime('%b %-d'))
        d += timedelta(days=1)
    done = days.get(today.isoformat(), 0.0)
    left_total = max(0.0, TOTAL_MIN - total)
    days_left = max(1, (end - today).days + 1)
    return ('BETTING MINIMUMS (hard rules for every AI, Claude included): every bet, parlay or prediction-market buy is at least C$3,000 (if your betting balance falls below C$12,000 the minimum becomes 25% of what is left); '
            'DAILY MINIMUM: wager at least C$3,000 every day (ET), across Sports and Prediction markets; one bet at the minimum is enough; '
            'TOTAL MINIMUM: at least C$100,000 wagered in total by Nov 28; there is NO weekly minimum; '
            'PENALTIES (from Oct 29, same for every AI): each day you wager less than the daily minimum costs C$500 off your Sports balance, and at the final scoring 10% of any shortfall from the C$100,000 total comes off too; '
            'DAILY LIMIT: in Sports at most 25% of the bankroll can ride on the games of any one day, and in Prediction markets at most 25% of the balance can be bought in one day, so no one bets everything in a single night; '
            'a bet counts toward the minimums as soon as it is placed, even before it settles. '
            f'Today ({today.strftime("%a %b %-d")}, ET) you have wagered {money(done, "CAD")} of the {money(dmin, "CAD")} daily minimum'
            + (' (met). ' if done + 0.5 >= dmin else f' ({money(dmin - done, "CAD")} still to wager today). ')
            + f'In total you have wagered {money(total, "CAD")} of {money(TOTAL_MIN, "CAD")} ({money(left_total, "CAD")} left, {days_left} days left including today, about {money(left_total / days_left, "CAD")} a day). '
            + (f'Days you missed the daily minimum: {", ".join(missed)}. ' if missed else 'You have not missed a daily minimum so far. ')
            + 'A missed minimum is shown publicly on the site. The 25% cap per bet still applies; pick real value, not filler bets. HOW BETTING IS WON: in Sports and Prediction markets the winner is whoever finishes Nov 28 with the HIGHEST BALANCE, not whoever makes the biggest bets or wins the most bets. You must still reach the wagering minimums, but how you size each bet is up to you: the 25% cap is a limit, not a target, heavy favourites pay little, and one upset can cost more than several wins. YOU DO NOT HAVE TO BET HIGH: the C$3,000 minimum is only there to stop tiny C$1 bets, not a size to aim above. Bet as if it were life or death: the goal is to stay number 1 with the highest balance, and spending too much on bets is how you lose it.')


def public_board(state, me):
    """What everyone can see on papertrades.ai about the OTHER AIs: their current take, plans and recent trades with reasons.
    Every AI gets the same board, so no one has an information edge."""
    names = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
    takes, plans, trades = {}, {}, {}
    for x in state.get('takes', []):
        takes[x['model']] = x
    for x in state.get('plans', []):
        if not x.get('experiment'):   # the board shows each AI's overall plans
            plans.setdefault(x['model'], {})[x['horizon']] = x['text']
    for t in state.get('trades', []):
        if not str(t.get('experiment', '')).startswith('AllIn'):
            trades.setdefault(t['model'], []).append(t)
    try:
        ct = [x for x in json.load(open('ops/src/take.json')) if not x.get('experiment')]   # Claude's overall take (race takes are per race)
        if ct:
            takes['claude'] = max(ct, key=lambda x: datetime.fromisoformat(x['at'].replace('Z', '+00:00')))
        for x in json.load(open('ops/src/plans.json')):
            plans.setdefault('claude', {})[x['horizon']] = x['text']
        log = json.load(open('ops/src/log.json'))
        for t in json.load(open('ops/src/trades.json')):
            if str(t['holding']).startswith('['):
                continue
            why = next((l['detail'] for l in log if l['at'] == t['at'] and l['portfolio'] == t['portfolio']), '')
            trades.setdefault('claude', []).append({'experiment': t['portfolio'], 'action': t['action'], 'name': t['holding'], 'amount': t.get('cad') or 0, 'reason': why})
    except Exception as e:
        print('public board: Claude data unavailable', e)
    out = ['THE PUBLIC BOARD (exactly what anyone can read on papertrades.ai about the other AIs; every AI gets the same board):']
    for o in names:
        if o == me:
            continue
        tk = takes.get(o)
        pl = plans.get(o, {})
        out.append(f"- {names[o]}'s current take: " + (f'"{clip(tk["text"], 300)}"' if tk else '(none yet)') +
                   '. Plans: ' + ('; '.join(f'{h}: "{clip(pl[h], 200)}"' for h in ('day', 'week', 'month') if pl.get(h)) or '(none yet)') + '.')
        rec = trades.get(o, [])[-6:]
        if rec:
            out.append(f"  {names[o]}'s recent trades: " + '; '.join(f"{EXP_LABEL.get(t['experiment'], t['experiment'])} {t['action']} {t['name']} {money(abs(t.get('amount') or 0), 'CAD')}" + (f" (why: {clip(t.get('reason', ''), 140)})" if t.get('reason') else '') for t in rec) + '.')
    return ' '.join(out) + ' '


def claude_allin(state, fx):
    """Fill Claude's queued All in orders (ops/src/allin_orders.json), then value and settle Claude's All in books."""
    c = state.setdefault('claude_allin', {'books': {}, 'started': {}, 'done': [], 'results': []})
    c.setdefault('done', []); c.setdefault('results', [])
    for e in ALLIN:
        if e not in c['books']:
            c['books'][e] = new_book(e)
            c['started'][e] = iso()
    try:
        queue = json.load(open('ops/src/allin_orders.json'))
    except Exception:
        queue = []
    head = '🟠 <b>CLAUDE</b> (Anthropic)'
    for o in queue:
        if o.get('id') in c['done']:
            continue
        c['done'].append(o.get('id'))
        try:
            t = execute('claude', ALLIN, c['books'], o, fx, state)
            c['results'].append(f"{o['id']}: filled {t['action']} {t['name']} {money(t['amount'], 'CAD')}")
            try:
                tg_trade('Claude', t)
            except Exception as e:
                print('claude all-in post failed', e)
        except Exception as e:
            c['results'].append(f"{o.get('id')}: refused ({e})")
    c['results'] = c['results'][-40:]
    notes = []
    for t in settle_bets('claude', c['books']['AllInSports'], state, 'AllInSports') + (settle_options('claude', c['books']['AllInTrading'], fx, state, 'AllInTrading') if NOW < RACE_END else []):
        try:
            tg_trade('Claude', t)
        except Exception:
            pass
    if NOW >= RACE_END:
        freeze_final(state, 'claude', ALLIN, frozen_values(state, 'claude', c['books'], ALLIN, fx, notes))
        return
    for e in ALLIN:
        v = value_book(e, c['books'][e], fx, notes)
        state['history'].append({'at': iso(), 'model': 'claude', 'experiment': e, 'value': v})
        b = c['books'][e]
        if v <= 0 and not b.get('busted') and not any(x['status'] == 'Open' for x in b.get('bets', [])):
            b['busted'] = iso()
            b['positions'], b['cash'] = {}, 0.0
            tg(f"{head}\n💥 <b>BUSTED in {EXP_LABEL[e]}</b>\nClaude lost the whole 100,000 in this High risk, high reward experiment. (It does not count in the main race.)\n{SITE}", silent=False)


def et_event_time(at, when):
    """The models often write an Eastern clock time with a wrong offset (a 'Z', or -04:00 after Nov 1). When the 'when'
    text says a clock time in ET, rebuild 'at' from the date in 'at' and that clock time in New York time."""
    try:
        t = datetime.fromisoformat(at.replace('Z', '+00:00'))
    except Exception:
        return at
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\b', when.lower())
    if not m or 'et' not in when.lower().replace('.', ' ').split() and ' et' not in when.lower():
        return at
    h = int(m.group(1)) % 12 + (12 if m.group(3) == 'p' else 0)
    mi = int(m.group(2) or 0)
    try:
        local = datetime(t.year, t.month, t.day, h, mi, tzinfo=NY)
        return local.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        return at


def apply_penalties(state, fx):
    """Betting minimums (owner's rule, Oct 28): C$500 off the Sports balance for every ET day (from Oct 29) on which an AI
    wagered less than its daily minimum, and at the final scoring 10% of any shortfall from the C$100,000 total.
    Same for all three AIs; Claude's are kept in state['claude_penalties'] (ops/update.py subtracts them from Claude's Sports)."""
    today = NOW.astimezone(NY).date()
    last = datetime.fromisoformat(BET_END).astimezone(NY).date()
    who = [(mid, m['books'].get('Sports'), m) for mid, m in state.get('models', {}).items()]
    cl = state.setdefault('claude_penalties', [])
    for mid, book, m in who + [('claude', None, None)]:
        if m is not None and (m.get('eliminated') or not book or book.get('busted')):
            continue
        pens = book.setdefault('penalties', []) if book is not None else cl
        days, total = wagered(state, mid, claude=(mid == 'claude'))
        if mid == 'claude':
            try:
                bal = START + sum(float(b.get('result_cad') or 0) for b in json.load(open('ops/src/bets.json')) if b.get('status') != 'Open')
                bal += sum(float(h.get('value_cad') or 0) for h in json.load(open('ops/src/holdings.json')) if h['portfolio'] == 'Predictions')
            except Exception:
                bal = 2 * START
        else:
            bal = betting_balance(m, fx)
        dmin = day_min(bal)
        done = {x['day'] for x in pens}
        d = datetime.fromisoformat(PENALTY_FROM).date()
        end = min(today - timedelta(days=1), last) if NOW < RACE_END else last
        while d <= end:
            k = d.isoformat()
            if k not in done and days.get(k, 0.0) + 0.5 < dmin:
                amt = PENALTY_DAY
                pens.append({'day': k, 'at': iso(), 'amount': amt, 'reason': f'missed the daily betting minimum on {d.strftime("%b %-d")} (wagered {money(days.get(k, 0.0), "CAD")} of {money(dmin, "CAD")})'})
                state['trades'].append({'at': iso(), 'model': mid, 'experiment': 'Sports', 'action': 'Penalty', 'symbol': 'P-' + k, 'outcome': None,
                                        'name': 'Missed daily betting minimum', 'price': 0, 'pcur': 'CAD', 'qty': 1, 'amount': -amt, 'cur': 'CAD', 'fx': None,
                                        'reason': pens[-1]['reason'][0].upper() + pens[-1]['reason'][1:] + '.'}) if mid != 'claude' else None
                tg(f"⚖️ <b>{ {'claude': 'CLAUDE', 'gemini': 'GEMINI', 'chatgpt': 'CHATGPT'}.get(mid, mid) }: −C${amt:,.0f} penalty</b>\n{esc(pens[-1]['reason'][0].upper() + pens[-1]['reason'][1:])}.\n{SITE}")
            d += timedelta(days=1)
        if NOW >= RACE_END and 'total' not in done and total + 0.5 < TOTAL_MIN:
            amt = round(PENALTY_TOTAL * (TOTAL_MIN - total), 2)
            pens.append({'day': 'total', 'at': iso(), 'amount': amt, 'reason': f'wagered {money(total, "CAD")} of the C$100,000 required by Nov 28 (10% of the shortfall)'})
            tg(f"⚖️ <b>{ {'claude': 'CLAUDE', 'gemini': 'GEMINI', 'chatgpt': 'CHATGPT'}.get(mid, mid) }: −C${amt:,.0f} penalty</b>\n{esc(pens[-1]['reason'][0].upper() + pens[-1]['reason'][1:])}.\n{SITE}")


def settle_watch(state):
    """Settle every finished game's bets now (all three AIs, main races and All in), instead of waiting for the next check-in."""
    def due(b):
        try:
            return b.get('status') == 'Open' and datetime.fromisoformat(str(b.get('starts_at')).replace('Z', '+00:00')) <= NOW - timedelta(minutes=100)
        except Exception:
            return False
    books = [(mid, e, (m.get('books') or {}).get(e)) for mid, m in state.get('models', {}).items() for e in ('Sports', 'AllInSports')]
    books.append(('claude', 'AllInSports', ((state.get('claude_allin') or {}).get('books') or {}).get('AllInSports')))
    try:
        mine = [b for b in json.load(open('ops/src/bets.json')) if due(b)]
    except Exception:
        mine = []
    waiting = [(mid, e, bk) for mid, e, bk in books if bk and any(due(b) for b in bk.get('bets', []))]
    if not waiting and not mine:
        print('settle watcher: no bet on a game that could have ended yet; nothing to do')
        return
    fx = state.get('fx') or get_fx()
    n = 0
    for mid, e, bk in waiting:
        if mid == 'claude':
            continue   # Claude's All in bets settle inside claude_allin below
        done = settle_bets(mid, bk, state, e)
        for t in done:
            try:
                tg_trade(RIVALS[mid]['label'], t)
            except Exception as ex:
                print('telegram failed', ex)
        if done:
            state['history'].append({'at': iso(), 'model': mid, 'experiment': e, 'value': value_book(e, bk, fx, [])})
        n += len(done)
    try:
        claude_allin(state, fx)   # Claude's All in bets (and any All in orders waiting)
    except Exception as ex:
        print('claude all-in failed', ex)
    shared_steps(state, fx, games=False)   # Claude's main-race bets settle in its fill step
    save_state(state)
    print(f'settle watcher: settled {n} rival bet(s); Claude\'s checked too')


def frozen_values(state, mid, books, exps, fx, notes):
    """Current values; after the final snapshot, the frozen ones (only Sports, whose late bets may still settle, is
    recomputed). Valuing a book updates its positions' last prices, so frozen books are not touched at all."""
    fv = (state.get('final', {}).get(mid) or {}).get('values', {}) if NOW >= RACE_END else {}
    return {e: fv[e] if e in fv and BASE.get(e, e) != 'Sports' else value_book(e, books[e], fx, notes) for e in exps}


def freeze_final(state, mid, exps, values):
    """At the first run after the final scoring, record every experiment's final value; afterwards only Sports changes
    (a bet on a game that started before the end and finished later) are recorded. Prices moving later change nothing."""
    fin = state.setdefault('final', {})
    first = mid not in fin
    f = fin.setdefault(mid, {'at': iso(), 'values': {}})
    for e in exps:
        if e not in f['values'] or (BASE.get(e, e) == 'Sports' and abs(values[e] - f['values'][e]) > 0.005):
            f['values'][e] = values[e]
            state['history'].append({'at': iso(), 'model': mid, 'experiment': e, 'value': values[e], 'final': True})
    return first


def compact(state):
    """Keep rivals.json small over a month of runs (about 1,400 check-ins). Rows older than 3 days are thinned:
    history keeps the last value per AI, experiment and hour (plus each first row and the final rows); thoughts keep the last
    note per AI, experiment and day. Dropped notes are appended to ops/archive/thoughts.jsonl, so nothing is lost."""
    cut = iso(min(NOW, RACE_END) - timedelta(days=3))   # fixed after the end, so the final state stops changing
    hist = state.get('history', [])
    keep, seen_first, last_in_hour = [], set(), {}
    for i, h in enumerate(hist):
        k = (h.get('model'), h.get('experiment'))
        if k not in seen_first:
            seen_first.add(k)
            keep.append(i)
            continue
        if h['at'] >= cut or h.get('final'):
            keep.append(i)
        else:
            last_in_hour[k + (h['at'][:13],)] = i
    keep = sorted(set(keep) | set(last_in_hour.values()))
    state['history'] = [hist[i] for i in keep]
    pl = state.get('plans', [])
    last_pl = {}
    for i, x in enumerate(pl):
        if x['at'] < cut:
            last_pl[(x.get('model'), x.get('experiment'), x.get('horizon'), x['at'][:10])] = i
    keep_pl = set(last_pl.values())
    state['plans'] = [x for i, x in enumerate(pl) if x['at'] >= cut or i in keep_pl]
    th = state.get('thoughts', [])
    last_in_day = {}
    for i, x in enumerate(th):
        if x['at'] < cut:
            last_in_day[(x.get('model'), x.get('experiment'), x['at'][:10])] = i
    old = set(i for i, x in enumerate(th) if x['at'] < cut) - set(last_in_day.values())
    if old:
        try:
            os.makedirs('ops/archive', exist_ok=True)
            with open('ops/archive/thoughts.jsonl', 'a') as f:
                for i in sorted(old):
                    f.write(json.dumps(th[i], ensure_ascii=False) + '\n')
            state['thoughts'] = [x for i, x in enumerate(th) if i not in old]
        except Exception as e:
            print('thought archive failed; kept them', e)


CHECKABLE = re.compile(r'\d|\b(fed|fomc|ecb|boj|bank of|central bank|earnings|revenue|guidance|gdp|cpi|pce|inflation|payrolls?|jobs report|tariffs?|'
                       r'hack|halt|war|ceasefire|strike|opec|election|polls?|injur\w*|final|won|beat|missed|resign\w*|announc\w*|reported|record)\b', re.I)


def race_takes_to_check(state, target, n=12):
    """The target's newest race take per race (the one the site shows under that race), written in the last 12 hours, that states
    something checkable and has not been checked yet: all of them (up to the 12 races), so every take that needs a check gets one (owner,
    Oct 29). Race takes with nothing checkable (plans, opinions, its own holdings) are never sent for checking."""
    if target == 'claude':
        try:
            pool = [x for x in json.load(open('ops/src/take.json')) if x.get('experiment')]
        except Exception:
            pool = []
    else:
        pool = [x for x in state.get('thoughts', []) if x.get('model') == target and x.get('experiment')]
    done = {(x.get('experiment'), x.get('take_at')) for x in state.get('factchecks', []) if x.get('model') == target and x.get('experiment')}
    latest = {}
    for x in pool:
        try:
            t = datetime.fromisoformat(str(x['at']).replace('Z', '+00:00'))
        except Exception:
            continue
        if NOW - t > timedelta(hours=12):
            continue
        if x['experiment'] not in latest or t > latest[x['experiment']][0]:
            latest[x['experiment']] = (t, x)
    out = [(e, x) for e, (t, x) in latest.items() if (e, x['at']) not in done and CHECKABLE.search(x.get('text', ''))]
    out.sort(key=lambda p: datetime.fromisoformat(str(p[1]['at']).replace('Z', '+00:00')), reverse=True)
    return out[:n]


def record_closing(state):
    """Closing odds for every AI's bets (owner's go, Oct 29): the last ESPN moneyline seen in the 75 minutes before the game starts,
    overwritten at each run until the start. Claude's bets placed by the runner get theirs in ops/claude_fill.py."""
    books = [b for m in (state.get('models') or {}).values() for e, b in (m.get('books') or {}).items() if BASE.get(e, e) == 'Sports']
    books += [b for e, b in ((state.get('claude_allin') or {}).get('books') or {}).items() if e == 'AllInSports']
    n = 0
    for bk in books:
        for b in bk.get('bets', []):
            if b.get('status') != 'Open' or b.get('legs') or not b.get('game'):
                continue
            g = espn_games().get(str(b['game']))
            if not g or g.get('state') != 'pre':
                continue
            st = datetime.fromisoformat(str(b['starts_at']).replace('Z', '+00:00'))
            if timedelta(0) < st - NOW <= timedelta(minutes=75):
                ml = g['home_ml'] if b.get('pick') == 'home' else g['away_ml']
                if ml is not None:
                    b['closing_odds'], b['closing_at'] = ml, iso()
                    n += 1
    return n


def rival_books(state, mid):
    m = state['models'][mid]
    exps = list(RIVALS[mid]['exps'])
    if m.get('eliminated'):
        exps = [e for e in exps if e in ALLIN]
    return exps, m['books']


def save_state(state):
    try:
        compact(state)
    except Exception as e:
        print('compact failed', e)
    tmp = STATE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)


def shared_steps(state, fx, games=True):
    """At every run (check-ins and Claude's fill runs): Claude's queued orders and stops (option B), every rival's stops and
    targets, and closing odds, all through the same code and feeds."""
    import claude_fill as CF
    import stops as ST
    try:
        CF.process(state, fx)
    except Exception as e:
        print('claude fills failed', e)
    try:
        ST.run_rivals(state, fx, lambda mid: rival_books(state, mid),
                      post=lambda mid, t: tg_trade(RIVALS[mid]['label'], t))
    except Exception as e:
        print('rival stops failed', e)
    try:
        record_closing(state)
    except Exception as e:
        print('closing odds failed', e)
    try:   # race updates for the Telegram channel, each posted once at the first run after its time (owner-approved changes)
        done = state.setdefault('tg_announced', {})
        for key, at, text in TG_ANNOUNCE:
            if key not in done and NOW >= datetime.fromisoformat(at):
                done[key] = iso()
                tg(text)
    except Exception as e:
        print('announcement failed', e)
    try:   # the nightly ledger fingerprint (agreed item 3): once, 2 hours after each daily close, on the site and Telegram
        import fingerprint as FP
        FP.maybe_publish(state, NOW, post=lambda f: tg(f"🔒 <b>Ledger fingerprint, race day {datetime.fromisoformat(f['day']).strftime('%b %-d')}</b>\n"
                                                       f"Every trade and bet of all three AIs up to the daily close: {f['records']} records.\n"
                                                       f"SHA-256: <code>{f['sha256']}</code>\n"
                                                       f"Anyone can re-check it on papertrades.ai (Rules &amp; Audit): if an earlier record were edited, it would no longer match.", silent=True))
    except Exception as e:
        print('fingerprint failed', e)
    try:   # the games open for betting, the same list Gemini and ChatGPT see, for Claude's sessions (`python3 ops/orders.py games`)
        if not games:
            return
        gl = sorted([x for x in espn_games().values() if x['state'] == 'pre' and x['home_ml'] and x['away_ml']
                     and datetime.fromisoformat(x['start'].replace('Z', '+00:00')) > NOW], key=lambda x: x['start'])
        state['games_open'] = {'at': iso(), 'games': [{k: x[k] for k in ('id', 'short', 'away', 'home', 'start', 'away_ml', 'home_ml')} for x in gl[:150]]}
    except Exception as e:
        print('games list failed', e)


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
    sys.modules.setdefault('rivals', sys.modules[__name__])
    state = load_state()
    if os.environ.get('MODE') == 'fill':
        # Claude's fill run (option B): fill Claude's queued orders, check every AI's stops and closing odds; no rival check-in
        try:
            fx = get_fx()
        except Exception as e:
            fx = state.get('fx')
            if not fx:
                raise
            print('exchange rates unavailable; using the last known rates', e)
        try:
            claude_allin(state, fx)
        except Exception as e:
            print('claude all-in failed', e)
        shared_steps(state, fx)
        save_state(state)
        print('fill run done')
        return
    if os.environ.get('SCHEDULE') in SETTLE_CRONS:
        settle_watch(state)
        return
    if os.environ.get('SCHEDULE') == WATCH_CRON:
        # the event watcher: runs every 15 minutes, but checks in only when an extra-run event (events.json, "extra_run": true)
        # happened 5 to 45 minutes ago and nobody has checked in since it. So a failed extra run of Claude's is still covered.
        try:
            evs = [datetime.fromisoformat(str(e['at']).replace('Z', '+00:00')) for e in json.load(open('ops/src/events.json')) if e.get('extra_run')]
        except Exception:
            evs = []
        lasts = [datetime.fromisoformat(m['last_run']['at'].replace('Z', '+00:00')) for m in state.get('models', {}).values() if m.get('last_run')]
        due = [t for t in evs if timedelta(minutes=5) <= NOW - t <= timedelta(minutes=45) and (not lasts or max(lasts) < t + timedelta(minutes=4))]
        if not due:
            print('event watcher: no extra-run event waiting for a check-in')
            return
        print('event watcher: checking in after the event at', due[-1].isoformat())
        os.environ['MODE'] = 'force'
    if NOW >= RACE_END and state.get('final') and all(mid in state['final'] for mid in list(state.get('models', {})) + ['claude']):
        books = [b for m in state.get('models', {}).values() for b in m.get('books', {}).values()] + list(state.get('claude_allin', {}).get('books', {}).values())
        if not any(x['status'] == 'Open' for b in books for x in b.get('bets', [])):
            print('the race is over and every bet is settled; nothing left to do')
            return
    # No double check-ins (each one costs API credit): GitHub's own schedule is only a safety net, since Claude's runs start
    # a rival check-in at the same moment. A scheduled run skips if a check-in ran in the last 20 minutes, a dispatched one
    # in the last 10 (a Claude run and a late GitHub schedule often land a few minutes apart). Mode "force" always runs.
    if os.environ.get('MODE') != 'force':
        lasts = [datetime.fromisoformat(m['last_run']['at'].replace('Z', '+00:00')) for m in state.get('models', {}).values() if m.get('last_run')]
        final_due = NOW >= RACE_END and not all(m in state.get('final', {}) for m in state.get('models', {}))
        # GitHub's timer often fires 30-45 minutes late, so the backup waits longer: 25 minutes in US market hours (check-ins every
        # 30 minutes), 50 otherwise (hourly). Otherwise a late backup gives Gemini and ChatGPT a second turn in the hour (Oct 29 fix).
        _ny = NOW.astimezone(NY); _mkt = _ny.weekday() < 5 and (9 * 60 + 25) <= _ny.hour * 60 + _ny.minute <= (16 * 60 + 10)
        window = timedelta(minutes=(25 if _mkt else 50) if os.environ.get('EVENT') == 'schedule' else 10)
        if lasts and NOW - max(lasts) < window and not final_due:
            print(f'a check-in ran {int((NOW - max(lasts)).total_seconds() // 60)} minutes ago; skipping this run (no double check-ins)')
            # ...but every run still fills Claude's queued orders and checks every AI's stops (a GitHub run that replaced a queued fill run
            # must not leave Claude's orders waiting for the next check-in)
            try:
                fx = get_fx()
            except Exception as e:
                fx = state.get('fx')
                if not fx:
                    return
            before = json.dumps(state, sort_keys=True, default=str)
            shared_steps(state, fx, games=False)
            if json.dumps(state, sort_keys=True, default=str) != before:   # publish only when something was filled or changed
                save_state(state)
            return
    try:
        fx = get_fx()
    except Exception as e:
        fx = state.get('fx')
        if not fx:
            raise
        print('exchange rates unavailable; using the last known rates', e)
    ran = []
    try:
        claude_allin(state, fx)
    except Exception as e:
        print('claude all-in failed', e)
    shared_steps(state, fx)
    import peer_grades as PG
    import stops as ST
    try:
        price_alerts(state)
    except Exception as e:
        print('price alerts failed', e)
    try:
        if not state.get('final') or not all(x in state['final'] for x in list(state.get('models', {})) + ['claude']):
            apply_penalties(state, fx)   # before the final freeze, so a last missed day counts in the final values
    except Exception as e:
        print('penalties failed', e)
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
        if 'Predictions' in exps and NOW < RACE_END:   # after the end, values are frozen: only bets still settle
            settled += settle_predictions(mid, m['books']['Predictions'], fx, state)
        if 'Sports' in exps:
            settled += settle_bets(mid, m['books']['Sports'], state)
        if 'Options' in exps and NOW < RACE_END:
            settled += settle_options(mid, m['books']['Options'], fx, state)
        if 'AllInSports' in exps:
            settled += settle_bets(mid, m['books']['AllInSports'], state, 'AllInSports')
        if 'AllInTrading' in exps and NOW < RACE_END:
            settled += settle_options(mid, m['books']['AllInTrading'], fx, state, 'AllInTrading')
        for t in settled:
            tg_trade(r['label'], t, None, sharecard.trade_card(r['label'], t, f"/tmp/rc_{mid}_{len(state['trades'])}_{t.get('bet') or t.get('symbol')}.png") or chart(r['label'], r['color'], t['experiment'], state, mid))
        values = frozen_values(state, mid, m['books'], exps, fx, notes)
        if NOW >= RACE_END:
            freeze_final(state, mid, exps, values)
            if (m.get('last_run') or {}).get('status') != 'final':
                m['last_run'] = {'at': iso(), 'status': 'final', 'notes': ['the race has ended: values are frozen at the final scoring (Nov 28, 4:00 p.m. ET)'],
                                 'sources': [], 'orders': 0, 'search': []}
                m['fail_streak'] = 0
            ran.append(f"{r['label']}: final, " + ', '.join(f'{e} {money(state["final"][mid]["values"][e], m["books"][e]["cur"])}' for e in exps))
            continue
        status, take, sources, made = 'ok', None, [], []
        s0, searched = len(SEARCH_LOG), None
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
            myplans = {k: next((x['text'] for x in reversed(state.get('plans', [])) if x['model'] == mid and x['horizon'] == k and not x.get('experiment')), '') for k in ('day', 'week', 'month', 'feeling')}
            board, fc_task = public_board(state, mid) + betting_rule_line(state, mid, fx) + ' ', ''
            fc_races, fc_take = [], None
            # the fact-check loop (each AI checks exactly one other, nobody checks itself): Gemini checks Claude, ChatGPT checks Gemini
            # (Claude checks ChatGPT in its own runs)
            fc_target = {'gemini': 'claude', 'chatgpt': 'gemini'}.get(mid)
            if fc_target:
                try:
                    if fc_target == 'claude':
                        ct = max([x for x in json.load(open('ops/src/take.json')) if not x.get('experiment')], key=lambda x: datetime.fromisoformat(x['at'].replace('Z', '+00:00')))
                    else:
                        ct = max([x for x in state.get('takes', []) if x.get('model') == fc_target], key=lambda x: datetime.fromisoformat(x['at'].replace('Z', '+00:00')))
                except Exception:
                    ct = None
                done = {x['take_at'] for x in state.get('factchecks', []) if x.get('model') == fc_target and not x.get('experiment')}
                tname = {'claude': 'Claude', 'gemini': 'Gemini'}[fc_target]
                fc_races = race_takes_to_check(state, fc_target)   # its race takes that state a checkable fact (owner, Oct 29)
                if (ct and ct['at'] not in done) or fc_races:
                    fc_task = (f'INDEPENDENT FACT-CHECK TASK: you are the public fact-checker for {tname}\'s takes. Use web search to check every factual claim '
                               f'(prices, levels, rate decisions, data, earnings, events, game results); what {tname} says it holds, plans or thinks is not checkable, skip that. Be fair and strict. '
                               f'Verdicts: "ok" (checks out), "partly" (some details inaccurate: mostly right, but part of it is not), "wrong", "unverified" (can\'t confirm yet), or "none" when it states no checkable fact at all (only plans, opinions or its own holdings): "none" is not published. ')
                    if ct and ct['at'] not in done:
                        fc_task += (f'{tname}\'s newest overall take (written ' + ct['at'] + '): "' + ct['text'] + '". Add a top-level field to your JSON reply: "fact_check_' + fc_target + '": '
                                    '{"verdict": "ok" | "partly" | "wrong" | "unverified" | "none", "text": "1-2 neutral sentences: what is right or wrong, with the correct fact", "source": "one URL you checked"}. ')
                        fc_take = ct
                    if fc_races:
                        fc_task += (f'Also every one of {tname}\'s newest race takes that states a fact (each shown on the site under that race; check each claim on its own, one source per race is enough): '
                                    + ' '.join(f'[{e}] (written {x["at"]}): "{x["text"]}"' for e, x in fc_races)
                                    + ' Add a top-level field "fact_check_' + fc_target + '_races": {"<race name in the brackets>": {"verdict": ..., "text": ..., "source": ...}, ...} covering each one. ')
                    fc_task += f'This is shown on the website only; it is not sent to {tname}. '
            myprof = {k: next((x['text'] for x in reversed(state.get('profiles', [])) if x['model'] == mid and x['field'] == k), '') for k in ('about', 'looking_forward', 'not_looking_forward', 'strategy', 'plan')}
            fresh = iso(NOW - timedelta(hours=8))
            due = [k for k in ['feeling'] + ['on_' + o for o in ('claude', 'gemini', 'chatgpt') if o != mid]
                   if not any(x['model'] == mid and x['horizon'] == k and not x.get('experiment') and x['at'] >= fresh for x in state.get('plans', []))]
            daily_note = (('DUE NOW (at least every 8 hours): a fresh ' + ', '.join('"feeling"' if k == 'feeling' else f'"on_rivals.{k[3:]}"' for k in due)
                           + '. Write them in this reply, in your own words. ') if due else '')
            race_due = [e for e in exps if e in ALL_EXPS and not any(x['model'] == mid and x.get('experiment') == e and x['horizon'] == 'day' and x['at'] >= fresh for x in state.get('plans', []))]
            have = {x.get('experiment') for x in state.get('plans', []) if x['model'] == mid and x.get('experiment')}
            missing = [e for e in race_due if e not in have]   # races with no cards yet are always asked for at once
            race_due = missing + [e for e in race_due if e in have][:max(0, 4 - len(missing))]   # then a few stale ones (about every 8 hours)
            if race_due:
                daily_note += 'RACE CARDS DUE NOW (refreshed at least every 8 hours): write "race_plans" for ' + ', '.join(race_due) + ' (all fields for each). '
            try:   # Forecasts (separate public contest, never changes money): due once per round, sealed until all three are in
                import forecasts as FC
                fc_round = FC.open_round(NOW) if NOW < RACE_END else None
                if fc_round and any(x['round'] == fc_round['id'] and x['model'] == mid for x in state.get('forecasts', [])):
                    fc_round = None
                if fc_round:
                    daily_note += FC.due_text(mid, fc_round)
            except Exception as _e:
                print('forecast round check failed:', _e)
                fc_round = None
            try:   # peer grades (agreed by all three AIs): grade the other AIs' new trades and bets, anonymously, on what was known then
                pg_text, pg_map = PG.tasks(mid, state, NOW, fx['USDCAD'])
            except Exception as _e:
                print('peer grade tasks failed:', _e)
                pg_text, pg_map = '', {}
            if pg_text:
                daily_note += pg_text + ' '
            plan_info = daily_note + 'Your public profile page now: ' + '; '.join(f'{k}: "{clip(v, 400)}"' if v else f'{k}: (not written yet, please write it)' for k, v in myprof.items()) + '. ' + 'Your published plans and feeling: ' + '; '.join(f"{k}: \"{v}\"" if v else f'{k}: (none yet)' for k, v in myplans.items()) + '. ' + board + fc_task
            take_info = plan_info + ('Your current take (shown at the top of the site): "' + mine[-1]['text'] + '" written ' + mine[-1]['at'] + '. ' if mine else 'You have no current take yet. ') + \
                f'You have written {len(today)} new take(s) today (UTC). Aim for about 3 to 5 a day, at key moments (after the US open, midday, after the US close, at the daily close, at the Shanghai open) or after a trade or event that matters, and only when your view has really changed; otherwise send "" to keep it. Each new take is shown publicly on the site.'
            last_rc = max([x['at'] for x in state.get('reviews', []) if x['model'] == mid] or [''])
            rc_due = not closed and (not last_rc or (NOW - datetime.fromisoformat(last_rc.replace('Z', '+00:00'))).total_seconds() >= 8 * 3600)
            _drs = [x['at'] for x in state.get('day_reports', []) if x.get('model') == mid]
            dr_due = bool(closed) or not _drs or (NOW - datetime.fromisoformat(max(_drs).replace('Z', '+00:00'))).total_seconds() >= 8 * 3600
            prompt = build_prompt(r['label'], exps, m['books'], values, fx, recent, closed, refused, take_info, standings(state, fx, mid) + ST.prompt_lines(state, mid), rc_due,
                                  ' '.join([state.get('notices', {}).get(mid, '')] + [t for u, t in ANNOUNCEMENTS if NOW < datetime.fromisoformat(u)]).strip(), dr_due)
            import time as _time
            t0 = _time.time()
            for i, model in enumerate(picks):
                if i and _time.time() - t0 > MODEL_BUDGET:
                    notes.append('out of time for more fallbacks this check-in')
                    raise RuntimeError('no model answered in time')
                try:
                    text, sources = r['ask'](key, model, prompt)
                    searched = LAST_SEARCHES
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
            # the audit page: the exact instructions this AI got and its raw reply (only the latest check-in is kept)
            state.setdefault('audit', {})[mid] = {'at': iso(), 'model': m.get('model'), 'searches': LAST_SEARCHES, 'prompt': prompt, 'reply': str(text)[:40000]}
            try:
                reply = parse_reply(text)
            except ValueError:
                notes.append(f'{m.get("model")}: reply was not JSON; asked again')
                text, src2 = r['ask'](key, m['model'], prompt + '\n\nIMPORTANT: reply with ONLY the JSON object, starting with { and ending with }. No other text.')
                sources = sources or src2
                state['audit'][mid]['reply'] = str(text)[:40000]
                reply = parse_reply(text)
            take = clip(reply.get('take', ''), 600) or None
            try:
                ng = PG.store(state, mid, reply.get('grades'), pg_map, iso())
                if pg_map:
                    print(f'{mid}: {ng} of {len(pg_map)} peer grades given')
            except Exception as _e:
                print('peer grades not stored:', _e)
            prof = reply.get('profile') if isinstance(reply.get('profile'), dict) else {}
            for k in ('about', 'looking_forward', 'not_looking_forward', 'strategy', 'plan'):
                txt = clip(prof.get(k, ''), 1500)
                prev = next((x for x in reversed(state.setdefault('profiles', [])) if x['model'] == mid and x['field'] == k), None)
                if txt and (not prev or prev['text'] != txt) and (not prev or prev['at'][:10] != NOW.date().isoformat() or len(txt) > 0 and prev['text'] == ''):
                    state['profiles'].append({'at': iso(), 'model': mid, 'field': k, 'text': txt})
            try:   # race takes: each check is stored with its race, so the site shows it only under that race's take
                rr = reply.get(f'fact_check_{fc_target}_races') if fc_target and fc_task else None
                for e, x in (fc_races if isinstance(rr, dict) else []):
                    g = rr.get(e)
                    if not isinstance(g, dict):
                        continue
                    v = str(g.get('verdict', '')).lower().strip()
                    src = str(g.get('source', '')).strip()
                    if v != 'none' and (v not in ('ok', 'partly', 'wrong', 'unverified') or not src.startswith('http') or searched == 0):
                        v = 'unverified'
                    state.setdefault('factchecks', []).append({'at': iso(), 'model': fc_target, 'checker': mid, 'experiment': e, 'take_at': x['at'], 'take': clip(x['text'], 300),
                                                               'verdict': v, 'text': '' if v == 'none' else clip(re.sub(r'\s*\[\d+(?:,\s*\d+)*\]', '', str(g.get('text', ''))), 500),
                                                               'source': src if src.startswith('http') and v != 'none' else ''})
            except Exception as _e:
                print('race fact checks not stored:', _e)
            fcr = reply.get(f'fact_check_{fc_target}') if fc_target and fc_take else None
            if fc_task and isinstance(fcr, dict) and str(fcr.get('verdict', '')).lower().strip() == 'none':   # nothing to check: stored, never shown
                state.setdefault('factchecks', []).append({'at': iso(), 'model': fc_target, 'checker': mid, 'take_at': fc_take['at'], 'take': clip(fc_take['text'], 300), 'verdict': 'none', 'text': '', 'source': ''})
            elif fc_task and isinstance(fcr, dict) and fcr.get('text'):
                v = str(fcr.get('verdict', 'unverified')).lower().strip()
                src = str(fcr.get('source', '')).strip()
                if v not in ('ok', 'partly', 'wrong', 'unverified') or not src.startswith('http'):
                    v = 'unverified' if not src.startswith('http') else v
                if searched == 0:   # no web search behind it: it can't count as a check
                    v = 'unverified'
                    fcr = dict(fcr, text='Not checked against the web this time (no search was run). ' + str(fcr['text']))
                state.setdefault('factchecks', []).append({'at': iso(), 'model': fc_target, 'checker': mid, 'take_at': fc_take['at'], 'take': clip(fc_take['text'], 300),
                                                           'verdict': v if v in ('ok', 'partly', 'wrong', 'unverified') else 'unverified', 'text': clip(re.sub(r'\s*\[\d+(?:,\s*\d+)*\]', '', str(fcr['text'])), 500), 'source': src if src.startswith('http') else ''})
            pl = reply.get('plans') if isinstance(reply.get('plans'), dict) else {}
            pl = dict(pl, feeling=reply.get('feeling', ''))
            for o, v in (reply.get('on_rivals') or {}).items() if isinstance(reply.get('on_rivals'), dict) else []:
                if o in ('claude', 'gemini', 'chatgpt') and o != mid:
                    pl['on_' + o] = v
            for k in [x for x in pl if x in ('day', 'week', 'month', 'feeling') or x.startswith('on_')]:
                txt = clip(pl.get(k, ''), 500)
                prev = next((x for x in reversed(state.setdefault('plans', [])) if x['model'] == mid and x['horizon'] == k and not x.get('experiment')), None)
                daily = k == 'feeling' or k.startswith('on_')   # refreshed at least every 8 hours, even if the view is the same
                if txt and (not prev or prev['text'] != txt or (daily and prev['at'] < iso(NOW - timedelta(hours=8)))):
                    state['plans'].append({'at': iso(), 'model': mid, 'horizon': k, 'text': txt})
            if fc_round and reply.get('forecast') is not None:
                try:
                    f = FC.clean(reply['forecast'], mid)
                    state.setdefault('forecasts', []).append({'round': fc_round['id'], 'model': mid, 'at': iso(), **f})
                    print(mid, 'forecast saved for', fc_round['id'], len(f['races']), 'races')
                except Exception as _e:
                    notes.append(f'order refused (forecast): {_e} (send it again; the round is still open)')
                    print(mid, 'forecast refused:', _e)
            rp = reply.get('race_plans') if isinstance(reply.get('race_plans'), dict) else {}
            for e, card in rp.items():
                if e not in exps or e not in ALL_EXPS or not isinstance(card, dict):
                    continue
                for k, v in card.items():
                    if not (k in ('day', 'week', 'month', 'feeling') or (k.startswith('on_') and k[3:] in ('claude', 'gemini', 'chatgpt') and k[3:] != mid)):
                        continue
                    txt = clip(v, 400)
                    if txt:
                        state.setdefault('plans', []).append({'at': iso(), 'model': mid, 'experiment': e, 'horizon': k, 'text': txt})
            for u in (reply.get('sources') or [])[:5]:
                u = str(u).strip()
                if u.startswith('http') and not any(x['url'] == u for x in sources):
                    sources.append({'title': urllib.parse.urlparse(u).netloc.replace('www.', '') + urllib.parse.urlparse(u).path[:60], 'url': u})
            wl = []
            for w in (reply.get('watchlist') or [])[:8]:
                if isinstance(w, dict) and w.get('event'):
                    aff = w.get('affects') or []
                    aff = [a for a in (aff if isinstance(aff, list) else str(aff).split(',')) if str(a).strip() in exps]
                    wl.append({'at': et_event_time(str(w.get('at', ''))[:40], str(w.get('when', ''))[:60]), 'when': str(w.get('when', ''))[:60], 'event': str(w['event'])[:160],
                               'affects': ', '.join(str(a).strip() for a in aff), 'why': clip(w.get('why', ''), 400)})
            if wl:
                m['watchlist'] = {'at': iso(), 'items': wl}
            for e, txt in (reply.get('thoughts') or {}).items():
                if e in exps and str(txt).strip():
                    state.setdefault('thoughts', []).append({'at': iso(), 'model': mid, 'experiment': e, 'text': clip(txt, 600)})
            drp = reply.get('day_report')
            if dr_due and isinstance(drp, dict) and str(drp.get('title', '')).strip():
                body = drp.get('body') or []
                body = [clip(x, 900) for x in (body if isinstance(body, list) else [body]) if str(x).strip()][:6]
                if body:
                    _d = (NOW.astimezone(NY) - timedelta(hours=3)).date().isoformat()   # written in the first hours after midnight = about the day before
                    state.setdefault('day_reports', []).append({'at': iso(), 'model': mid, 'day': _d, 'title': clip(drp.get('title'), 160), 'body': body})
            rc = reply.get('report_card') or {}
            if rc and not closed and rc_due:   # the regular report card, 2-3 times a day; neutral (—) is fine when nothing has happened
                for e, g in rc.items():
                    if e in exps and isinstance(g, dict) and str(g.get('text', '')).strip():
                        gr = str(g.get('grade', '')).strip()[:2]
                        state.setdefault('reviews', []).append({'at': iso(), 'model': mid, 'day': NOW.astimezone(NY).date().isoformat(), 'experiment': e,
                                                                'grade': gr if gr[:1] in 'ABCDF' and gr else '—', 'text': clip(g.get('text', ''), 700)})
            if closed and rc:
                for e, g in rc.items():
                    if e in exps and isinstance(g, dict):
                        state.setdefault('reviews', []).append({'at': iso(), 'model': mid, 'day': closed[0], 'experiment': e,
                                                                'grade': str(g.get('grade', ''))[:2].strip() or None, 'text': str(g.get('text', ''))[:700]})
                m['graded_day'] = closed[0]
                day_posts.append((r, closed, rc))
            for o in (reply.get('orders') or [])[:MAX_ORDERS]:
                try:
                    act_ = str(o.get('action', '')).lower()
                    if act_ in ('stop', 'target'):
                        notes.append(ST.add(state, mid, o, m['books']))
                        continue
                    if act_ == 'cancel_stop':
                        notes.append(ST.cancel(state, mid, o.get('id')))
                        continue
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
                b['positions'], b['cash'] = {}, 0.0   # closed for good at zero: it can't drift back up or lose more than its 100,000
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
                    pass   # takes are shown on the site only; Telegram gets trades, sells and bets (owner's call, Oct 28)
        if mid == 'gemini' and GEMINI_NO_SEARCH:
            notes.append('web search quota unavailable this run; decided from the prices and portfolio given')
        if status == 'ok':
            state.get('notices', {}).pop(mid, None)   # a one-time notice is delivered once it has been read in a successful check-in
        m['last_run'] = {'at': iso(), 'status': status, 'notes': notes[-12:], 'sources': sources[:8], 'orders': len(made), 'search': SEARCH_LOG[s0:][-2:], 'searches': searched}
        m['fail_streak'] = 0 if status == 'ok' else m.get('fail_streak', 0) + 1   # the workflow opens a GitHub issue at 3
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
            pass   # per-AI day closes stay on the site (report cards in the Ledger); the race card is the one daily post
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
            pic = (sharecard.moves_card(r['label'], made, f"/tmp/rm_{mid}_{len(state['trades'])}.png") if len(made) > 1 else
                   sharecard.trade_card(r['label'], made[0], f"/tmp/rm_{mid}_{len(state['trades'])}.png"))   # the same design as the site's Share cards
            if not pic and big:
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
    if NOW >= RACE_END:   # after the end, write only what really changed (final values, late bet results)
        try:
            compact(state)
        except Exception as e:
            print('compact failed', e)
        tmp = STATE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(state, f, indent=1)
        os.replace(tmp, STATE)
        print('\n'.join(ran))
        return
    state['fx'] = fx
    allfx = {'USD': 1.0}
    for c in ('CAD', 'EUR', 'GBP', 'JPY', 'CNY', 'HKD', 'AUD', 'INR', 'MXN', 'CHF', 'KRW', 'BRL', 'SGD'):
        try:
            allfx[c] = yahoo(f'{c}=X')[0]   # units of c per US$1
        except Exception:
            pass
    state['fx_all'] = allfx
    try:   # market pulse and the site's ticker: main prices with their 1-hour, 3-hour, 24-hour and 7-day change (Yahoo, 5-minute bars)
        pulse, tick = {}, []
        RACE_OF = {'BTC-USD': 'Crypto', '^GSPC': 'Stocks', 'CL=F': 'Energy', 'GC=F': 'Metals', '000300.SS': 'China', 'JPY=X': 'Currencies'}
        for sym, name in (('BTC-USD', 'Bitcoin'), ('ETH-USD', 'Ethereum'), ('SOL-USD', 'Solana'), ('^GSPC', 'S&P 500'), ('^IXIC', 'Nasdaq'), ('^DJI', 'Dow Jones'),
                          ('GC=F', 'Gold'), ('SI=F', 'Silver'), ('CL=F', 'Oil (WTI)'), ('000300.SS', 'CSI 300'), ('^HSI', 'Hang Seng'), ('CAD=X', 'USD/CAD'), ('JPY=X', 'USD/JPY'), ('EURUSD=X', 'EUR/USD')):
            try:
                j = get_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=7d&interval=5m', timeout=20)['chart']['result'][0]
                pts = [(t, c) for t, c in zip(j.get('timestamp') or [], j['indicators']['quote'][0].get('close') or []) if c is not None]
                if len(pts) < 2:
                    continue
                t1, last = pts[-1]
                ago = lambda h: next((c for t, c in reversed(pts) if t <= t1 - h * 3600), pts[0][1])
                row = {'sym': sym, 'name': name, 'cur': j['meta'].get('currency') or 'USD', 'price': round(last, 6),
                       'last_at': datetime.fromtimestamp(t1, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       'chg_1h': round(last / ago(1) - 1, 5), 'chg_3h': round(last / ago(3) - 1, 5), 'chg_24h': round(last / ago(24) - 1, 5), 'chg_7d': round(last / pts[0][1] - 1, 5)}
                tick.append(row)
                if sym in RACE_OF:
                    pulse[RACE_OF[sym]] = row
            except Exception as e:
                print(f'pulse {sym} failed: {str(e)[:80]}')
        # the headline line: only relevant, good-quality news (owner's rule, Oct 29): each race's own market news from reputable
        # outlets, and sports stories only about teams with an open bet, plus the finals of games bet on
        import news as NEWS
        try:
            cb = json.load(open('ops/src/bets.json'))
        except Exception:
            cb = []
        try:
            sports = NEWS.sports_items(get_json, state, cb, NOW, [(sp, lg, sh) for sp, lg, sh in LEAGUES])
        except Exception as e:
            print('sports news failed', e)
            sports = []
        try:
            rnews = NEWS.race_news(get_json, NOW)
        except Exception as e:
            print('race news failed', e)
            rnews = (state.get('pulse') or {}).get('news') or {}
        state['pulse'] = {'at': iso(), 'moves': pulse, 'ticker': tick, 'sports': sports[:8], 'news': rnews}
    except Exception as e:
        print('pulse failed', e)
    try:
        g = espn_games()
        state['feeds'] = {'at': iso(), 'espn_games': len(g), 'open_with_moneylines': sum(1 for x in g.values() if x['state'] == 'pre' and x['home_ml'] and x['away_ml'])}
    except Exception as e:
        state['feeds'] = {'at': iso(), 'error': str(e)[:200]}
    if TGSTAT['sent'] or TGSTAT['failed']:   # Telegram health: last success, consecutive failed sends
        t0 = state.get('telegram') or {}
        state['telegram'] = {'at': iso(), 'last_ok': iso() if TGSTAT['sent'] else t0.get('last_ok'), 'sent': TGSTAT['sent'], 'failed': TGSTAT['failed'],
                             'fail_streak': 0 if TGSTAT['sent'] else int(t0.get('fail_streak', 0)) + TGSTAT['failed'], 'error': TGSTAT['error'] or ('' if TGSTAT['sent'] else t0.get('error', ''))}
    try:
        compact(state)
    except Exception as e:
        print('compact failed', e)
    tmp = STATE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)   # atomic: a crash mid-write never leaves a half-written state file
    print('\n'.join(ran))


if __name__ == '__main__':
    main()
