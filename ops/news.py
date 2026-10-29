"""Headlines for the site's news line, per race, kept relevant and of good quality (owner's rule, Oct 29, 2026):
  - each race gets headlines about its own market (Crypto: crypto news, Oil and energy: oil news, ...), only from reputable
    outlets, from the last 24 hours, never clickbait or "should you buy" pieces;
  - sports stories only when they involve a team someone has an open bet on, plus the final score of every game bet on;
  - nothing random: a headline must name the race's market in its title.
Run from ops/rivals.py at each check-in; stored in rivals.json pulse.news / pulse.sports and shown by the site.
"""
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

QUERIES = {
    'Crypto': ['bitcoin', 'ethereum', 'crypto market'],
    'Stocks': ['stock market today', 'S&P 500', 'Wall Street stocks'],
    'Energy': ['oil prices', 'crude oil', 'OPEC'],
    'Metals': ['gold price', 'silver price'],
    'China': ['China stocks', 'Shanghai stocks', 'Chinese economy'],
    'Currencies': ['dollar yen', 'forex dollar', 'Bank of Japan'],
    'Options': ['stock market volatility VIX', 'options traders'],
    'Safe': ['Treasury yields', 'Treasury bills'],
    'Predictions': ['Polymarket', 'Senate race polls', 'prediction markets'],
    # the three AIs' own companies, for each AI's page (owner, Oct 29): Anthropic for Claude, Google for Gemini, OpenAI for ChatGPT
    'Claude': ['Anthropic', 'Anthropic Claude AI'],
    'Gemini': ['Google Gemini AI', 'Google DeepMind'],
    'ChatGPT': ['OpenAI', 'ChatGPT OpenAI'],
}
WINDOW = {'Claude': 48, 'Gemini': 48, 'ChatGPT': 48}   # hours; company news is slower than market news (24 h)
TOPIC = {
    'Crypto': r'bitcoin|ether(eum)?\b|crypto|solana|\bbtc\b|stablecoin|coinbase|blockchain|\bxrp\b',
    'Stocks': r'stocks?\b|s&p|nasdaq|\bdow\b|wall street|equities|earnings|shares',
    'Energy': r'\boil\b|crude|opec|brent|\bwti\b|natural gas|energy|hormuz|refin',
    'Metals': r'\bgold\b|silver|bullion|precious metal|platinum|copper',
    'China': r'china|chinese|shanghai|shenzhen|\bcsi\b|yuan|beijing|hang seng|\bpboc\b',
    'Currencies': r'dollar|\byen\b|\beuro\b|currenc|forex|\bboj\b|bank of japan|bank of canada|loonie|sterling|\bfx\b',
    'Options': r'volatility|\bvix\b|options|s&p|stock market',
    'Safe': r'treasur|yield|bonds?\b|t-bill|federal reserve|\bfed\b',
    'Predictions': r'polymarket|kalshi|prediction market|election|senate|midterm|odds',
    'Claude': r'anthropic|\bclaude\b',
    'Gemini': r'deepmind|google.{0,40}\b(gemini|ai)\b|\bgemini\b.{0,40}\b(ai|model|app|chatbot|google)\b',
    'ChatGPT': r'openai|chatgpt|\bgpt-?\d|sam altman',
}
GOOD = {'reuters', 'bloomberg', 'cnbc', 'associated press', 'ap', 'the wall street journal', 'wall street journal', 'financial times',
        'marketwatch', "barron's", 'barrons.com', 'coindesk', 'the block', 'decrypt', 'yahoo finance', 'kitco', 'investing.com', 'fortune',
        'axios', 'the economist', 'bbc', 'cnn business', 'cointelegraph', 'south china morning post', 'nikkei asia', 'fxstreet',
        'oilprice.com', 'politico', 'the hill', 'the new york times', 'the washington post', 'bloomberg law', 'fox business',
        'techcrunch', 'the verge', 'wired', 'ars technica', 'venturebeat', 'engadget', 'zdnet', 'the information', 'semafor', 'business insider',
        'cnet', 'the guardian', 'associated press finance', 'investopedia'}
BAD = re.compile(r'\?$|^(should you|is it time|is now|could|will .* (soar|crash)|here\'s why|this (stock|is why)|\d+ (stocks?|reasons))'
                 r'|prediction:|buy now|millionaire|billionaire|forever|dividend stocks?|best stocks?|top stocks?|i\'d buy|no-brainer|'
                 r'motley|zacks|price prediction|to the moon|you won\'t believe|smart money|bull run incoming', re.I)


def yahoo_news(get_json, q, n=10):
    u = f'https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(q)}&quotesCount=0&newsCount={n}&enableFuzzyQuery=false'
    try:
        return get_json(u, timeout=15).get('news') or []
    except Exception as e:
        print(f'news {q!r} failed: {str(e)[:80]}')
        return []


def race_news(get_json, now):
    """{race: [{t, src, link, at}]}: up to 4 good, on-topic headlines from the last 24 hours, newest first."""
    out = {}
    for race, qs in QUERIES.items():
        seen, items = set(), []
        for q in qs:
            for a in yahoo_news(get_json, q):
                t = ' '.join(str(a.get('title', '')).split())
                pub = str(a.get('publisher', '')).strip()
                ts = a.get('providerPublishTime')
                if not t or not ts or not a.get('link'):
                    continue
                at = datetime.fromtimestamp(int(ts), timezone.utc)
                if now - at > timedelta(hours=WINDOW.get(race, 24)) or at > now + timedelta(minutes=5):
                    continue
                if pub.lower() not in GOOD or BAD.search(t) or not re.search(TOPIC[race], t, re.I):
                    continue
                k = re.sub(r'[^a-z0-9 ]', '', t.lower())[:60]
                if k in seen:
                    continue
                seen.add(k)
                items.append({'t': t[:180], 'src': pub, 'link': a['link'], 'at': at.strftime('%Y-%m-%dT%H:%M:%SZ')})
        items.sort(key=lambda x: x['at'], reverse=True)
        if items:
            out[race] = items[:4]
    return out


def _team_words(name):
    """'Boston Celtics' -> {'celtics', 'boston'}; colleges keep their full name too."""
    ws = [w for w in re.findall(r"[A-Za-z][A-Za-z.'&-]+", str(name)) if len(w) > 2]
    out = {name.lower()}
    if ws:
        out.add(ws[-1].lower())
    return out


def open_bet_teams(state, claude_bets):
    teams = {}
    for mid, m in (state.get('models') or {}).items():
        for e in ('Sports', 'AllInSports'):
            for b in ((m.get('books') or {}).get(e) or {}).get('bets', []):
                if b.get('status') == 'Open':
                    for side in str(b.get('event', '')).split(' @ '):
                        teams.setdefault(side.strip(), set()).add(mid)
    for e in ('AllInSports',):
        for b in (((state.get('claude_allin') or {}).get('books') or {}).get(e) or {}).get('bets', []):
            if b.get('status') == 'Open':
                for side in str(b.get('event', '')).split(' @ '):
                    teams.setdefault(side.strip(), set()).add('claude')
    for b in claude_bets or []:
        if b.get('status') == 'Open':
            for side in re.split(r' @ | vs\.? ', re.sub(r'\s*\(.*\)$', '', str(b.get('event', '')))):
                teams.setdefault(side.strip(), set()).add('claude')
    return {k: v for k, v in teams.items() if k}


# general sports news worth a headline (owner, Oct 29: "how the MLB just finished and who won"): results and big stories, never filler
MAJOR = re.compile(r"\b(wins?|won|beats?|title|champions?(hip)?|clinch(es|ed)?|sweeps?|swept|series|walk-?off|no-hitter|perfect game|record|traded?|"
                   r"signs?|signed|fired|hires?|hired|retires?|retiring|suspended|mvp|world series|super bowl|stanley cup|finals?|playoffs?)\b", re.I)
NOISE = re.compile(r"practice|questionable|doubtful|day-to-day|fantasy|betting|\bodds\b|\bpicks?\b|\bprops?\b|best bets|power rankings|"
                   r"mock draft|uniforms?|podcast|^watch|video|takeaways|grades?\b|how to watch|what we learned|overreactions?", re.I)
BIG = (('baseball', 'mlb', 'MLB'), ('football', 'nfl', 'NFL'), ('basketball', 'nba', 'NBA'), ('hockey', 'nhl', 'NHL'))


def scoreboard_finals(get_json, now, bet_teams):
    """Finished games from the last day and a half: every playoff or championship game (World Series, ...) and every NFL game,
    plus any game someone bet on. Each says who won, the score and the series."""
    from zoneinfo import ZoneInfo
    ny = ZoneInfo('America/New_York')
    out, seen = [], set()
    for sp, lg, short in BIG:
        for d in (1, 0):
            day = (now.astimezone(ny) - timedelta(days=d)).strftime('%Y%m%d')
            try:
                j = get_json(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/scoreboard?dates={day}', timeout=20)
            except Exception as e:
                print(f'finals {lg} {day} failed: {str(e)[:80]}')
                continue
            for ev in j.get('events', []):
                try:
                    c = ev['competitions'][0]
                    if not ev['status']['type'].get('completed') or str(ev['id']) in seen:
                        continue
                    start = datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
                    if now - start > timedelta(hours=36):
                        continue
                    teams = {t['homeAway']: t for t in c['competitors']}
                    w = next((t for t in teams.values() if t.get('winner')), None)
                    lo = next((t for t in teams.values() if t is not w), None)
                    if not w or not lo:
                        continue
                    note = (((c.get('notes') or [{}])[0]) or {}).get('headline', '')
                    series = (c.get('series') or {}).get('summary', '')
                    names = {teams['home']['team']['displayName'], teams['away']['team']['displayName']}
                    bet = any(n in bet_teams for n in names)
                    if not (note or lg == 'nfl' or bet):
                        continue
                    seen.add(str(ev['id']))
                    txt = (note + ': ' if note else '') + f"{w['team']['displayName']} {w.get('score')}, {lo['team']['displayName']} {lo.get('score')}" + (f' ({series})' if series else '')
                    out.append({'league': short, 'headline': txt, 'at': (start + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'), 'link': '',
                                'why': 'big game' if note else ('game bet on' if bet else 'result'), 'final': True, 'game': str(ev['id']), 'rank': 0 if note else 1 if bet else 2})
                except Exception:
                    continue
    return out


def sports_items(get_json, state, claude_bets, now, leagues):
    """The Sports headlines: finished games worth knowing (playoffs and championships, NFL, games bet on), big stories (results,
    titles, trades, signings; no filler), stories about teams with an open bet, and the finals of games bet on."""
    teams = open_bet_teams(state, claude_bets)
    words = {w: t for t in teams for w in _team_words(t)}
    out, seen = [], set()
    for sp, lg, name in leagues:
        try:
            arts = get_json(f'https://site.api.espn.com/apis/site/v2/sports/{sp}/{lg}/news?limit=25', timeout=15).get('articles') or []
        except Exception as e:
            print(f'sports news {lg} failed: {str(e)[:80]}')
            continue
        for a in arts:
            h, pub = str(a.get('headline', '')).strip(), a.get('published') or ''
            if not h or not pub:
                continue
            at = datetime.fromisoformat(pub.replace('Z', '+00:00'))
            if now - at > timedelta(hours=30):
                continue
            text = (h + ' ' + str(a.get('description', ''))).lower()
            hit = next((t for w, t in words.items() if re.search(r'\b' + re.escape(w) + r'\b', text)), None)
            k = re.sub(r'[^a-z0-9 ]', '', h.lower())[:60]
            big = (sp, lg, name) in BIG and MAJOR.search(h) and not NOISE.search(h)
            if not (hit or big) or k in seen:   # the same story often runs in several leagues' feeds
                continue
            seen.add(k)
            out.append({'league': name, 'headline': h[:150], 'at': at.strftime('%Y-%m-%dT%H:%M:%SZ'), 'link': ((a.get('links') or {}).get('web') or {}).get('href', ''),
                        'why': f'{hit}: open bet' if hit else 'big story', 'rank': 3 if hit else 4})
    # finals of games bet on (the race's own sports results)
    finals = {}
    for mid, m in (state.get('models') or {}).items():
        for e in ('Sports', 'AllInSports'):
            for b in ((m.get('books') or {}).get(e) or {}).get('bets', []):
                if b.get('status') in ('Won', 'Lost', 'Push') and b.get('final') and b.get('settled_at'):
                    if now - datetime.fromisoformat(b['settled_at'].replace('Z', '+00:00')) <= timedelta(hours=12):
                        finals.setdefault(b['final'], (b.get('short', ''), b['settled_at'], set()))[2].add(mid)
    for f, (lg, at, who) in finals.items():
        out.append({'league': lg or 'FINAL', 'headline': 'Final: ' + f, 'at': at, 'link': '', 'why': 'bet on by ' + ', '.join(sorted(who)), 'final': True, 'bet': True, 'rank': 1})
    try:
        out += scoreboard_finals(get_json, now, set(teams))
    except Exception as e:
        print('finals failed', e)
    # one line per game: a game bet on keeps the line that says who bet on it
    have = {re.sub(r'[^a-z ]', '', x['headline'].lower()) for x in out if x.get('bet')}
    out = [x for x in out if x.get('bet') or not x.get('final') or not any(all(w in h for w in re.findall(r'[a-z]{4,}', x['headline'].lower())[:2]) for h in have)]
    out.sort(key=lambda x: x['at'], reverse=True)
    out.sort(key=lambda x: x.get('rank', 5))   # big games first, then games bet on, NFL results, stories about open bets, big stories
    return out[:12]
