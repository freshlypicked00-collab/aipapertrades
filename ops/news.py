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
}
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
}
GOOD = {'reuters', 'bloomberg', 'cnbc', 'associated press', 'ap', 'the wall street journal', 'wall street journal', 'financial times',
        'marketwatch', "barron's", 'barrons.com', 'coindesk', 'the block', 'decrypt', 'yahoo finance', 'kitco', 'investing.com', 'fortune',
        'axios', 'the economist', 'bbc', 'cnn business', 'cointelegraph', 'south china morning post', 'nikkei asia', 'fxstreet',
        'oilprice.com', 'politico', 'the hill', 'the new york times', 'the washington post', 'bloomberg law', 'fox business'}
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
                if now - at > timedelta(hours=24) or at > now + timedelta(minutes=5):
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


def sports_items(get_json, state, claude_bets, now, leagues):
    """ESPN stories that involve a team with an open bet (any AI), newest first, plus the final score of every game bet on that
    settled in the last 12 hours."""
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
            if not hit or k in seen:   # the same story often runs in several leagues' feeds
                continue
            seen.add(k)
            out.append({'league': name, 'headline': h[:150], 'at': at.strftime('%Y-%m-%dT%H:%M:%SZ'), 'link': ((a.get('links') or {}).get('web') or {}).get('href', ''),
                        'why': f'{hit}: open bet'})
    # finals of games bet on (the race's own sports results)
    finals = {}
    for mid, m in (state.get('models') or {}).items():
        for e in ('Sports', 'AllInSports'):
            for b in ((m.get('books') or {}).get(e) or {}).get('bets', []):
                if b.get('status') in ('Won', 'Lost', 'Push') and b.get('final') and b.get('settled_at'):
                    if now - datetime.fromisoformat(b['settled_at'].replace('Z', '+00:00')) <= timedelta(hours=12):
                        finals.setdefault(b['final'], (b.get('short', ''), b['settled_at'], set()))[2].add(mid)
    for f, (lg, at, who) in finals.items():
        out.append({'league': lg or 'FINAL', 'headline': 'Final: ' + f, 'at': at, 'link': '', 'why': 'bet on by ' + ', '.join(sorted(who)), 'final': True})
    out.sort(key=lambda x: x['at'], reverse=True)
    return out[:8]
