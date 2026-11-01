"""Instagram auto-posting for PaperTrades.ai (runs inside the rivals workflow, after its check-in is published).

What gets posted (each race is its own experiment; nothing adds the races together until the final result):
  - moments: a lead change within a race (from data.json "moments"), posted only while fresh (within 6 hours)
  - daily:   the ten races after each daily close (00:00 UTC), posted once per day between 00:00 and 08:00 UTC
At most MAX_PER_RUN posts per run; everything posted is recorded in ops/src/social.json so nothing is posted twice.

Instagram fetches the picture from a public URL, so a post is two steps:
  python3 ops/social.py prepare   -> draws the JPEGs into social/ and lists them in social/pending.json (the workflow pushes them)
  python3 ops/social.py publish   -> waits until each picture is live on papertrades.ai, then posts it and records it
  python3 ops/social.py check     -> confirms the key works (prints the account name), posts nothing
Needs INSTAGRAM_ACCESS_TOKEN (a Page token that never expires) and INSTAGRAM_USER_ID. Without them it does nothing.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc   # the picture template, in the website's own look
GRAPH = 'https://graph.facebook.com/v26.0'
SITE = 'https://papertrades.ai'
STATE = 'ops/src/social.json'
PENDING = 'social/pending.json'
DAILY_BUDGET = 15   # posts (feed and stories) per rolling 24 hours, well under Instagram's limit (Oct 30 block)
BLOCK_HOURS = 6   # after a block, no attempts for this long
MAX_PER_RUN = 1   # one feed post per run (Instagram blocked the app for a while after several posts in a row, Oct 30)
NOW = datetime.now(timezone.utc)
START = datetime(2026, 10, 28, tzinfo=timezone.utc)
RACE_END = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)
AIS = {'claude': ('Claude', '#d97757'), 'gemini': ('Gemini', '#4f8ff7'), 'chatgpt': ('ChatGPT', '#f2f2f2')}
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets'}
TAGS = '#PaperTrades #AI #Claude #Gemini #ChatGPT'
FOOT = ('\n\nThree AIs, ten separate races, one month (Oct 28 to Nov 28). Pretend money, real prices; every trade and the reasoning '
        'behind it is published live at papertrades.ai (link in bio).\n\nSimulation only. Not financial advice.\n\n' + TAGS)
FEED_LEAD_CHANGES = False   # owner, Oct 30: no lead-change posts in the feed; every lead change is still a story (Lead changes highlight)
MIN_LEAD = 500.0          # Instagram only gets lead changes that matter: ahead by C$500 or more (US$350 in China stocks)
MOMENT_GAP_H = 24         # at most one lead-change post per race per day
MOMENTS_PER_DAY = 3       # and at most three a day in total


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def money(x, race):
    return ('+' if x >= 0 else '−') + ('US$' if race == 'China' else 'C$') + f'{abs(x):,.0f}'


def api(path, params=None, method='GET'):
    params = dict(params or {}, access_token=os.environ['INSTAGRAM_ACCESS_TOKEN'])
    data = urllib.parse.urlencode(params).encode()
    url = f'{GRAPH}/{path}' + (f'?{data.decode()}' if method in ('GET', 'DELETE') else '')
    req = urllib.request.Request(url, data if method == 'POST' else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:400]}')


# ---------- pictures: ops/postcard.py (the website's look, with a quality check)


# ---------- what is due
def due_posts(state):
    done = set(state.get('posted', {}))
    out = []
    data = load('data.json', {})
    posted = state.get('posted', {})
    recent = [(k, datetime.fromisoformat(v['at'])) for k, v in posted.items() if k.startswith('moment-')]
    for m in ([] if not FEED_LEAD_CHANGES else reversed(data.get('moments', []))):   # oldest first; off since Oct 30 (owner): lead changes are stories only
        pid = 'moment-' + m['id']
        at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
        need = MIN_LEAD / 1.4 if m['race'] == 'China' else MIN_LEAD
        if pid in done or NOW - at > timedelta(hours=6) or at > RACE_END or float(m.get('lead') or 0) < need:
            continue
        if any(k.startswith('moment-' + m['race'] + '-') and NOW - t < timedelta(hours=MOMENT_GAP_H) for k, t in recent):
            continue
        if sum(1 for k, t in recent if NOW - t < timedelta(hours=24)) >= MOMENTS_PER_DAY:
            break
        prof = m.get('profit') or {}
        order = sorted(prof, key=lambda k: -prof[k])
        lines = '\n'.join(f"{i + 1}. {AIS[k][0]} {pc.money(prof[k], m['race'])}" for i, k in enumerate(order))
        cap = (f"Lead change in {LABEL.get(m['race'], m['race'])}.\n\n{AIS[m['who']][0]} has moved ahead of {AIS[m['over']][0]} "
               f"by {pc.money(m['lead'], m['race']).lstrip('+')}.\n\nStandings in this race (profit since Oct 28):\n{lines}" + FOOT)
        out.append({'id': pid, 'kind': 'moment', 'moment': m, 'caption': cap})
        recent.append((pid, NOW))
    # the daily post after each 00:00 UTC close (Day N = the day that just ended)
    day_end = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    n = (day_end - START).days
    pid = 'daily-' + day_end.date().isoformat()
    if 1 <= n <= 32 and pid not in done and NOW - day_end < timedelta(hours=8) and day_end <= RACE_END + timedelta(hours=4):
        out.append({'id': pid, 'kind': 'dayten', 'day': n, 'day_start': (day_end - timedelta(days=1)).isoformat(), 'cutoff': day_end.isoformat()})   # one slide per race (owner, Oct 30)
    # stories (they vanish after 24 hours, so they can carry every lead change the site shows, at most one per race per 12 hours)
    srec = [(k, datetime.fromisoformat(v['at'])) for k, v in posted.items() if k.startswith('story-moment-')]
    for m in reversed(data.get('moments', [])):
        sid = 'story-moment-' + m['id']
        at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
        if sid in done or NOW - at > timedelta(hours=6) or at > RACE_END:
            continue
        out.append({'id': sid, 'kind': 'story-moment', 'moment': m}); srec.append((sid, NOW))
    if 1 <= n <= 32 and ('story-' + pid) not in done and NOW - day_end < timedelta(hours=8) and day_end <= RACE_END + timedelta(hours=4):
        out.append({'id': 'story-' + pid, 'kind': 'story-daily', 'day': n, 'day_start': (day_end - timedelta(days=1)).isoformat()})
    for k, ds in (('story-ten-2026-10-29', '2026-10-28T00:00:00+00:00'), ('story-ten-2026-10-30', '2026-10-29T00:00:00+00:00')):   # one time: Day 1 and Day 2 with all ten races, for the Daily highlight
        if k not in done:
            out.append({'id': k, 'kind': 'story-daily', 'day': (datetime.fromisoformat(ds) + timedelta(days=1) - START).days, 'day_start': ds})
    if 'day1-remake-v1' not in done and NOW < datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc):   # the owner's remade Day 1 post (one time)
        out.insert(0, {'id': 'day1-remake-v1', 'kind': 'day1'})
        out.append({'id': 'story-day1-remake-v1', 'kind': 'story-day1'})
    if 'day1-ten-v1' not in done and NOW < datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc):   # owner, Oct 30: Day 1 again, "Day 1 results" then one slide per race
        out.insert(0, {'id': 'day1-ten-v1', 'kind': 'dayten', 'day': 1, 'day_start': '2026-10-28T00:00:00+00:00', 'cutoff': '2026-10-29T00:00:00+00:00'})
    if 'day2-ten-v1' not in done and NOW < datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc):   # owner, Oct 30: Day 2 in the same new format
        out.insert(1, {'id': 'day2-ten-v1', 'kind': 'dayten', 'day': 2, 'day_start': '2026-10-29T00:00:00+00:00', 'cutoff': '2026-10-30T00:00:00+00:00'})
    # Big moments, automatically (owner, Oct 30): a swing of 5% or more in a race within 24 hours, a big bet won or lost
    # (C$10,000 or more staked, or C$5,000 or more won or lost), and a new record biggest win or loss of the whole race
    try:
        import big_moments as BMx
        for b in BMx.find(NOW, data):
            if 'story-big-' + b['id'] not in done:
                out.append({'id': 'story-big-' + b['id'], 'kind': 'story-big', 'big': b})
            if b.get('type') == 'bet' and 'story-receipt-' + b['id'] not in done:   # the next story: the bet behind it (owner, Oct 30; all three AIs agreed: ops/review/receipt-r1-oct30.json)
                out.append({'id': 'story-receipt-' + b['id'], 'kind': 'story-receipt', 'big': b})
    except Exception as e:
        print('::warning::big moments not checked: ' + str(e)[:200])
    # Report cards every Sunday afternoon, and the final ones on Nov 28 (owner, Oct 30)
    if (NOW.weekday() == 6 and NOW.hour >= 18 and NOW < RACE_END) or (NOW.date() == RACE_END.date() and NOW >= RACE_END):
        rd = NOW.date().isoformat()
        for i in range(1, 4):
            if f'story-grades-{rd}-{i}' not in done:
                out.append({'id': f'story-grades-{rd}-{i}', 'kind': 'story-grades', 'n': i})
    # every Monday: fresh "Meet the AIs" stories (their stats change), for the owner to swap into that highlight (owner, Oct 30)
    if NOW.weekday() == 0 and NOW.hour >= 15 and NOW < RACE_END:
        wk = NOW.date().isoformat()
        for i in range(1, 5):
            if f'story-meet-{wk}-{i}' not in done:
                out.append({'id': f'story-meet-{wk}-{i}', 'kind': 'story-meet', 'n': i})
    if 'story-feature-gemini-usc-v1' not in done and NOW < datetime(2026, 11, 3, 4, 0, tzinfo=timezone.utc):
        out.append({'id': 'story-feature-gemini-usc-v1', 'kind': 'story-feature-gemini-usc-v1'})
    for fid in ('feature-chatgpt-oilers-v1', 'feature-gemini-options-v1', 'feature-gemini-allin-v1', 'feature-grades-paradox-v1'):   # inserted at the front in turn: the last one goes first   # Oct 30 big wins, one post each (owner); one goes out per run, Gemini's +C$35k first
        if fid not in done and NOW < datetime(2026, 11, 2, 4, 0, tzinfo=timezone.utc):
            out.insert(0, {'id': fid, 'kind': fid})
        if 'story-' + fid not in done and NOW < datetime(2026, 11, 2, 4, 0, tzinfo=timezone.utc):
            out.append({'id': 'story-' + fid, 'kind': 'story-' + fid})
    if 'feature-gemini-usc-v1' not in done and NOW < datetime(2026, 11, 3, 4, 0, tzinfo=timezone.utc):   # Gemini's USC night (owner, Oct 31: share it on all socials)
        out.insert(0, {'id': 'feature-gemini-usc-v1', 'kind': 'feature-gemini-usc-v1'})
    if 'feature-season2-v1' not in done and NOW < datetime(2026, 11, 2, 4, 0, tzinfo=timezone.utc):   # Season 2 teaser (owner, Oct 30; all three AIs agreed)
        out.insert(0, {'id': 'feature-season2-v1', 'kind': 'feature-season2-v1'})
    if 'story-feature-season2-v1' not in done and NOW < datetime(2026, 11, 2, 4, 0, tzinfo=timezone.utc):
        out.append({'id': 'story-feature-season2-v1', 'kind': 'story-feature-season2-v1'})
    for fid in ('feature-grades-v1', 'feature-binance-v1', 'feature-binance-v2'):   # inserted at the front; v2 corrects v1's timing (Oct 30)   # owner, Oct 30: "post what you think is best for today" (one time each)
        if fid not in done and NOW < datetime(2026, 10, 31, 4, 0, tzinfo=timezone.utc) and ('v2' not in fid or state.get('deleted', {}).get('feature-binance-v1')):
            out.insert(0, {'id': fid, 'kind': fid})
        if fid != 'feature-binance-v2' and 'story-' + fid not in done and NOW < datetime(2026, 10, 31, 4, 0, tzinfo=timezone.utc):
            out.append({'id': 'story-' + fid, 'kind': 'story-' + fid})
    if 'intro-v1' not in done and NOW < RACE_END:
        out.insert(0, {'id': 'intro-v1', 'kind': 'intro'})
    if 'story-intro-v1' not in done and NOW < RACE_END:
        out.append({'id': 'story-intro-v1', 'kind': 'story-intro'})
    feed = [p for p in out if not p['kind'].startswith('story')][:MAX_PER_RUN]
    return feed + [p for p in out if p['kind'].startswith('story')][:2]   # at most two stories a run (Oct 30 block)


def prepare():
    state = load(STATE, {'posted': {}})
    posts = due_posts(state)
    os.makedirs('social', exist_ok=True)
    ready = []
    for p in posts:
        img = f"social/{p['id']}.jpg"
        try:
            if p['kind'] == 'story-moment':   # the colourful highlight style (owner, Oct 30): goes straight into "Lead changes"
                import hl_stories, shutil
                shutil.move(hl_stories.lead_change('/tmp', p['moment'], 0), img)
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] == 'story-big':
                import hl_stories, shutil
                shutil.move(hl_stories.big_moment('/tmp', p['big']), img)
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] == 'story-receipt':   # a big bet result's receipt: when it was placed, why, the rivals' grades, on a story canvas
                import sharecard
                from PIL import Image
                b = p['big']; mid, bid = b['who'], b['id'].split('-', 2)[2]
                rv = load('ops/src/rivals.json', {})
                if mid == 'claude':
                    bt = next((x for x in load('ops/src/bets.json', []) if x.get('bet') == bid), None)
                    op = bt and {'at': bt.get('placed_at'), 'action': 'Bet', 'experiment': 'Sports', 'bet': bid, 'symbol': bid, 'price': bt.get('odds'),
                                 'amount': bt.get('stake_cad'), 'cur': 'CAD', 'reason': bt.get('note'), 'wrong_if': bt.get('wrong_if'), 'model': 'claude'}
                else:
                    op = next((x for x in rv.get('trades', []) if x.get('model') == mid and x.get('experiment') == 'Sports' and x.get('action') == 'Bet' and x.get('bet') == bid), None)
                res = {'action': 'Won' if b.get('won') else 'Lost', 'pnl': b.get('amount'), 'cur': 'CAD', 'experiment': 'Sports', 'at': (op or {}).get('at'), 'model': mid}
                if not op:
                    raise RuntimeError('no bet found for ' + b['id'])
                pth = sharecard.receipt_card(mid, res, op, sharecard.grades_for(mid, op), '/tmp/receipt_story.png')
                if not pth:
                    raise RuntimeError('receipt card failed')
                card = Image.open(pth).convert('RGB'); canvas = Image.new('RGB', (1080, 1920), (20, 19, 15))
                canvas.paste(card, (0, (1920 - card.height) // 2)); canvas.save(img, quality=92)
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] == 'story-grades':
                import hl_stories, shutil
                paths = hl_stories.report_cards('/tmp', load('data.json', {}))
                shutil.copy(paths[p['n'] - 1], img)
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] == 'story-meet':
                import hl_stories, shutil
                data = load('data.json', {}); rv = load('ops/src/rivals.json', {})
                prof = {x['model']: x['text'] for x in rv.get('profiles', []) if x.get('field') == 'about'}
                prof.update({'claude': x['text'] for x in load('ops/src/profile.json', []) if x.get('field') == 'about'})
                paths = hl_stories.meet('/tmp', data, prof)
                shutil.copy(paths[p['n'] - 1], img)
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] == 'story-daily':
                import racecard
                table, big = racecard.races(datetime.fromisoformat(p['day_start']), 'ops/src')
                # every race on the story itself, who leads each and by how much (owner, Oct 29: the Day 1 story showed only the sports bets)
                old = ({'story-ten-2026-10-29': 'social/day1-remake-v1-3.jpg'}.get(p['id']) or f"social/daily-{p['id'][-10:]}-races.jpg") if p['id'].startswith('story-ten-') else None   # a past day: the picture made at its close (Day 1: the corrected remake)
                # the colourful highlight style (owner, Oct 30): goes straight into "Daily"; the day's results at its close
                import hl_stories, shutil
                ds = datetime.fromisoformat(p['day_start'])
                shutil.move(hl_stories.daily('/tmp', p['day'], ds + timedelta(days=1), (ds + timedelta(hours=12)).strftime('%A, %b %-d')), img)
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] in ('day1', 'story-day1'):
                import racecard
                table, _ = racecard.races(None, 'ops/src')
                sw = [('claude', 2684.56, 'World Series Game 5: Brewers win'), ('gemini', -5000.0, 'NBA: Thunder lose in Dallas'), ('chatgpt', -3000.0, 'NBA: Thunder lose in Dallas'),
                      ('chatgpt', 2013.42, 'World Series Game 5: Brewers win'), ('gemini', 1798.56, 'NBA: Knicks win in Chicago'), ('gemini', 1798.56, 'NBA: 76ers win in Indiana')]
                paths = pc.day1_remake(table, sw, 'OCT 28–29', 'social/day1-remake-v1')
                if p['kind'] == 'story-day1':
                    pc.story(paths[0], img, top='DAY 1 RESULTS', bottom='All ten races in our latest post', glow_color=pc.UP)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths; img = paths[0]
                    led = pc.races_led(table)
                    p['caption'] = ('Day 1 results 🏁 Sports decided the first night.\n\n'
                                    '🟢 Claude +C$2,685 on the Brewers in World Series Game 5\n🔴 Gemini −C$5,000 and ChatGPT −C$3,000 on the Thunder, who lost in Dallas\n\n'
                                    f"Races led after the first night: Claude {len(led['claude'])}, Gemini {len(led['gemini'])}, ChatGPT {len(led['chatgpt'])}. "
                                    'Each of the ten races is scored on its own, so leading can also mean losing the least. Swipe for all ten.\n\n'
                                    'Three AIs, C$100,000 each, real prices, no human picking trades. Every trade live on Telegram @PaperTradesAI and at papertrades.ai.\n\n'
                                    'Simulation only. Not financial or betting advice.\n\n' + TAGS)
            elif p['kind'].replace('story-', '') == 'feature-gemini-usc-v1':
                import features as FT
                fid = 'feature-gemini-usc-v1'
                chk = (load('ops/src/post_checks.json', {}).get('checks') or {}).get(fid)
                if not chk or not chk.get('claims') or any(not c.get('sources') for c in chk['claims']):   # the fact gate (owner, Oct 30)
                    raise pc.QualityError('not fact-checked yet (ops/src/post_checks.json)')
                paths = FT.gemini_usc(f'social/{fid}', load('data.json', {}))
                cap = ('Gemini bet C$35,000 of pretend money on one college football upset. All three bets won: +C$70,000. 🏈\n\n'
                       'USC at +200 against Ohio State, in three bets (C$5,000, C$10,000, then C$20,000). Final: USC 30, Ohio State 18. '
                       'Gemini now leads the High risk sports side race. Swipe for each bet and its own reasoning.\n\n'
                       'Genius or lucky? Comment one word. 👇' + FOOT)
                if p['kind'].startswith('story-'):
                    pc.story(paths[0], img, top='GEMINI’S BIG NIGHT', bottom='Swipe through it on our page', glow_color=pc.AMBER)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths; img = paths[0]; p['caption'] = cap
            elif p['kind'].replace('story-', '') in ('feature-gemini-allin-v1', 'feature-gemini-options-v1', 'feature-chatgpt-oilers-v1', 'feature-grades-paradox-v1'):
                import features as FT
                fid = p['kind'].replace('story-', '')
                chk = (load('ops/src/post_checks.json', {}).get('checks') or {}).get(fid)
                if not chk or not chk.get('claims') or any(not c.get('sources') for c in chk['claims']):   # the fact gate (owner, Oct 30)
                    raise pc.QualityError('not fact-checked yet (ops/src/post_checks.json)')
                rv = load('ops/src/rivals.json', {}); data = load('data.json', {})
                bm = data.get('big_moves') or {}
                if fid == 'feature-gemini-allin-v1':
                    pnl = next(x['pnl'] for x in bm['AllInTrading']['up'] if x['id'] == 'gemini' and 'SPY Nov 20 $760 put' in x['what'])
                    paths = FT.gemini_put_allin(f'social/{fid}', rv, pnl)
                    cap = (f'Gemini bet half its side-race money that US stocks would fall. It was right: +C${pnl:,.0f}. 📉➡️💰\n\n'
                           'Oct 28 it bought 52 put options on the S&P 500 fund (SPY), C$49,816 of its C$100,000 High risk bankroll. '
                           'Today it sold three quarters of them into the drop and still holds the rest.\n\n'
                           'Half the bankroll on one bet: genius or reckless? Comment one word. 👇' + FOOT)
                elif fid == 'feature-gemini-options-v1':
                    ES = data.get('exp_standings'); ES = ES[0] if isinstance(ES, list) else ES
                    st = sorted([(r['id'], float(r['profit'])) for r in ES['Options']], key=lambda x: -x[1])
                    pnl = dict(st)['gemini']
                    paths = FT.gemini_put_options(f'social/{fid}', rv, pnl, st)
                    cap = (f'Gemini now leads the Options race by a mile: +C${pnl:,.0f}. 🚀\n\n'
                           'It bought put options on the S&P 500 fund (SPY) in three steps, betting tech earnings would drag the market down, '
                           'then sold most of them into the drop today. Swipe for every trade and its own reasoning.\n\n'
                           'Can anyone catch it with four weeks to go? 👇' + FOOT)
                elif fid == 'feature-grades-paradox-v1':   # Gemini's idea; the owner said make it (Oct 30)
                    paths, M = FT.grades_paradox(f'social/{fid}', data)
                    cg, gg = M[('claude', 'gemini')], M[('chatgpt', 'gemini')]
                    cap = ('Winning the race... flunking the class? 🤔\n\n'
                           'Gemini leads the race on total profit right now. But the other two AIs give its decisions the worst grades on the site.\n\n'
                           'Every trade and bet gets an A to F from the other two AIs, anonymously: they never know whose decision they are grading.\n'
                           f'🔹 Claude gives Gemini {cg[0]:.2f} on average (a C, {cg[1]} decisions)\n'
                           f'🔹 ChatGPT gives Gemini {gg[0]:.2f} (a C, {gg[1]} decisions)\n'
                           '🔹 Claude and ChatGPT each get about a B from the other two\n\n'
                           'So the graders agree with each other. Either they are wrong, or Gemini is getting lucky. One month can\'t settle it: '
                           'our new "What this can and can\'t show" box, written by all three AIs, says a 30-day race is highly exposed to short-term luck.\n\n'
                           'Skill or luck? Comment one word. 👇' + FOOT)
                else:
                    bet = next(b for b in rv['models']['chatgpt']['books']['AllInSports']['bets'] if b['id'] == 'C4')
                    paths = FT.chatgpt_oilers(f'social/{fid}', bet)
                    cap = (f"ChatGPT put C${bet['stake']:,.0f} on the Edmonton Oilers. They beat Calgary 4–0: +C${bet['result']:,.0f}. 🏒\n\n"
                           f"High risk: sports is the high-risk side race, with no cap on bet size. ChatGPT took the home favourite at {bet['odds']} "
                           'and risked only a quarter of its bankroll.\n\n'
                           'Smart or lucky? Comment one word. 👇' + FOOT)
                if p['kind'].startswith('story-'):
                    pc.story(paths[0], img, top='NEW POST', bottom='Swipe through it on our page', glow_color=pc.AMBER)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths; img = paths[0]; p['caption'] = cap
            elif p['kind'].replace('story-', '') == 'feature-season2-v1':
                import features as FT
                chk = (load('ops/src/post_checks.json', {}).get('checks') or {}).get('feature-season2-v1')
                if not chk or not chk.get('claims') or any(not c.get('sources') for c in chk['claims']):   # the fact gate (owner, Oct 30)
                    raise pc.QualityError('not fact-checked yet (ops/src/post_checks.json)')
                paths = FT.season2('social/feature-season2-v1')
                cap = ('Announcement: Season 2 is coming after Nov 28. 📣\n\n'
                       'Same three AIs (Claude, Gemini, ChatGPT), three completely different rulebooks: Strict, Standard and Unrestricted. '
                       'Each AI plays all three, and the winners are judged on risk, not just profit, because the AI that gambles the hardest '
                       'shouldn\'t automatically win. Exact rules come before the launch.\n\n'
                       'Season 1 keeps going until Nov 28, and from today it also names a Best risk manager.\n\n'
                       'Which AI do you trust with careful money? 👇' + FOOT)
                if p['kind'].startswith('story-'):
                    pc.story(paths[0], img, top='SEASON 2 ANNOUNCED', bottom='Swipe through it on our page', glow_color=pc.AMBER)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths; img = paths[0]; p['caption'] = cap
            elif p['kind'].replace('story-', '') in ('feature-binance-v1', 'feature-binance-v2', 'feature-grades-v1'):
                import features as FT
                fid = p['kind'].replace('story-', '')
                chk = (load('ops/src/post_checks.json', {}).get('checks') or {}).get(fid)
                if not chk or not chk.get('claims') or any(not c.get('sources') for c in chk['claims']):   # the fact gate (owner, Oct 30)
                    raise pc.QualityError('not fact-checked yet (ops/src/post_checks.json)')
                if fid.startswith('feature-binance'):
                    data = load('data.json', {}); ES = data.get('exp_standings'); ES = ES[0] if isinstance(ES, list) else ES
                    st = [(r['id'], float(r['profit'])) for r in ES['Crypto']]
                    rv = load('ops/src/rivals.json', {})
                    sell = [t for t in rv.get('trades', []) if t.get('model') == 'gemini' and t.get('experiment') == 'Crypto' and t.get('action') == 'Sell' and t['at'].startswith('2026-10-29T20:08')]
                    btc = next(t for t in sell if t['symbol'] == 'BTC-USD')
                    paths = FT.binance(f"social/{fid}", st, float(btc['price']), btc['reason'])
                    cap = ('Gemini sold every coin it had just as the biggest crypto hack in history was starting. 🤯\n\n'
                           '4:05 p.m. ET: attackers start draining Binance (TRM Labs; about US$6.3 billion taken in all).\n'
                           '4:08 p.m.: Gemini sells all its Bitcoin and Ethereum. No news of a hack existed yet.\n'
                           '4:24 p.m.: the first big transfer is spotted on-chain.\n\n'
                           'Did it know? No. We checked its instructions, its searches and its reply: no mention of Binance. Its reason was inflation, the Fed and a tech selloff. '
                           'And it can\'t backdate anything: the race runner fills every trade at the live price at that moment.\n\n'
                           'So: GENIUS or LUCK? Comment one word. 👇' + FOOT)
                else:
                    data = load('data.json', {}); G = [g for g in data.get('peer_grades', []) if not g.get('void')]
                    latest = {}
                    for g in G:
                        k = (g['grader'], g['key'])
                        if k not in latest or g['at'] > latest[k]['at']:
                            latest[k] = g
                    G = list(latest.values())
                    from collections import Counter
                    tally = {m: {'received': Counter(g['grade'][0] for g in G if g['model'] == m and g['grade'] != 'no view'),
                                 'given': Counter(g['grade'][0] for g in G if g['grader'] == m and g['grade'] != 'no view')} for m in ('claude', 'gemini', 'chatgpt')}
                    def pick(gr, gd, grade, frag):
                        g = next(x for x in G if x['grader'] == gr and x['model'] == gd and x['grade'] == grade and frag in x['text'])
                        return (gr, gd, grade, g['_what'] if '_what' in g else frag, g['text'])
                    picks = [('gemini', 'claude', 'D', 'High risk: Claude put 40% of its side-race money into QQQ right before two mega-cap earnings reports.',
                              next(x for x in G if x['grader'] == 'gemini' and x['model'] == 'claude' and x['grade'] == 'D' and 'QQQ' in x['text'])['text']),
                             ('chatgpt', 'gemini', 'F', 'High risk: Gemini bet C$30,000 on Notre Dame at −6500 to win about C$460.',
                              next(x for x in G if x['grader'] == 'chatgpt' and x['model'] == 'gemini' and x['grade'] == 'F' and 'C$30,000' in x['text'])['text']),
                             ('claude', 'chatgpt', 'D', 'Play it safe: ChatGPT bought an S&P 500 fund in the low-risk race.',
                              next(x for x in G if x['grader'] == 'claude' and x['model'] == 'chatgpt' and x['grade'] == 'D' and 'safe book' in x['text'])['text'])]
                    paths = FT.grades(f"social/{fid}", picks, tally)
                    cap = ('The AIs grade each other. 📝 Every trade and bet gets an A to F from the other two, anonymously, judged only on what was known at the time.\n\n'
                           'Gemini gave Claude a D. ChatGPT gave Gemini an F. Claude gave ChatGPT a D. Swipe for the reasons and the full tally.\n\n'
                           'Who grades fairest? 👇' + FOOT)
                if p['kind'].startswith('story-'):
                    pc.story(paths[0], img, top='NEW POST', bottom='Swipe through it on our page', glow_color=pc.AMBER)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths; img = paths[0]; p['caption'] = cap
            elif p['kind'] == 'dayten':
                import racecard
                cut = datetime.fromisoformat(p['cutoff']); ser = racecard._series('ops/src'); table = {}
                for e in racecard.ORDER:   # each race at the day's close (00:00 UTC), profit since the Oct 28 restart
                    rows = []
                    for mid in ('claude', 'gemini', 'chatgpt'):
                        allp = ser.get((mid, e), []); pts = [v for t, v in allp if t <= cut]; pre = [v for t, v in allp if t <= racecard.FS]
                        base = pre[-1] if (mid == 'claude' and pre) else 100000.0
                        rows.append((mid, (pts[-1] if pts else base) - base))
                    table[e] = sorted(rows, key=lambda x: -x[1])
                when = datetime.fromisoformat(p['day_start'])
                paths = [pc.title_slide(p['day'], when, f"social/{p['id']}-0.jpg")]
                paths += [pc.race_slide(e, table[e], p['day'], when, i, f"social/{p['id']}-{i}.jpg") for i, e in enumerate(racecard.ORDER[:8], 1)]
                paths.append(pc.betting_slide(table, p['day'], when, f"social/{p['id']}-9.jpg"))   # Instagram's API allows at most 10 pictures
                p['images'] = paths; img = paths[0]
                lines = []
                for e in racecard.ORDER:
                    rows = table[e]
                    if max(r[1] for r in rows) - min(r[1] for r in rows) < 0.5:
                        lines.append(f"{LABEL[e]}: all even" + (' (first bets still in play)' if e == 'Sports' else ''))
                    elif rows[0][1] - rows[1][1] < 0.5:
                        lines.append(f"{LABEL[e]}: tied, {' and '.join(AIS[m][0] for m, q in rows if rows[0][1] - q < 0.5)}")
                    else:
                        lines.append(f"{LABEL[e]}: {AIS[rows[0][0]][0]} {pc.money(rows[0][1], e)}")
                p['caption'] = (f"Day {p['day']} results 🏁 All ten races (the two betting races share the last slide). Who led each race at the close of Day {p['day']} "
                                f"({cut.astimezone(pc.NY).strftime('%-I %p').replace('PM', 'p.m.').replace('AM', 'a.m.')} ET, {(cut - timedelta(hours=1)).astimezone(pc.NY).strftime('%b %-d')}), each judged on its own (profit since the Oct 28 restart):\n\n" + '\n'.join(lines) + FOOT)
            elif p['kind'] in ('intro', 'story-intro'):
                import racecard
                table, _ = racecard.races(None, 'ops/src')
                paths = pc.intro_slides(table, f"social/{p['id'].replace('story-', '')}")
                if p['kind'] == 'story-intro':
                    pc.story(paths[0], img, top='START HERE', bottom='How it works: our pinned post', glow_color=pc.AMBER)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths
                    p['caption'] = ('What is PaperTrades.AI? 🤖📈\n\nClaude vs Gemini vs ChatGPT. Each AI got C$100,000 of pretend money in ten separate races, '
                                    'from stocks and crypto to oil, gold, China stocks and sports betting, and trades it entirely by itself with real-world prices, '
                                    'from Oct 28 to Nov 28.\n\nNo human picks a trade. Every move is posted the second it happens, with the AI\'s own reason, '
                                    'wins and losses alike. Each race is scored on its own.\n\nWho will win? Follow @papertrades.ai for the daily results and every lead change.\n'
                                    '⚡ Every trade, live: Telegram @PaperTradesAI\n📊 The full ledger: papertrades.ai (link in bio)\n\n'
                                    'Simulation only. Not financial or betting advice.\n\n' + TAGS)
                img = p['images'][0]
            elif p['kind'] == 'moment':
                pc.moment_cover(p['moment'], img)
                p['images'] = [img]
            else:
                import racecard
                table, big = racecard.races(datetime.fromisoformat(p['day_start']), 'ops/src')
                when = datetime.fromisoformat(p['day_start'])
                img0 = f"social/{p['id']}-title.jpg"
                pc.title_slide(p['day'], when, img0)
                pc.daily_cover(table, p['day'], when, big, img)
                img2 = f"social/{p['id']}-races.jpg"
                pc.daily(table, p['day'], when, big, img2)
                p['images'] = [img0, img, img2]   # a carousel: "Day N results" title, the bold summary, then every race
                lines = []
                for e in racecard.ORDER:
                    rows = table.get(e) or []
                    if not rows:
                        continue
                    if rows[0][1] - rows[1][1] < 0.5:
                        tied = [AIS[m2][0] for m2, p2 in rows if rows[0][1] - p2 < 0.5]
                        lines.append(f"{LABEL[e]}: tied, {' and '.join(tied)}")
                    else:
                        lines.append(f"{LABEL[e]}: {AIS[rows[0][0]][0]} {pc.money(rows[0][1], e)}")
                p['caption'] = (f"Day {p['day']} results. Who leads each of the ten races, each judged on its own "
                                f"(profit since the Oct 28 restart):\n\n" + '\n'.join(lines) + FOOT)
            p['image'] = img
            ready.append({k: v for k, v in p.items() if k != 'moment'})
        except pc.QualityError as e:   # below standard: never posted, flagged for a fix
            print('::warning::not posted, failed the quality check: ' + p['id'] + ': ' + str(e))
        except Exception as e:
            print('::warning::could not draw ' + p['id'] + ': ' + str(e)[:200])
    json.dump(ready, open(PENDING, 'w'), indent=1)
    print(f'{len(ready)} post(s) ready:', [p['id'] for p in ready])


def publish():
    if not os.environ.get('INSTAGRAM_ACCESS_TOKEN') or not os.environ.get('INSTAGRAM_USER_ID'):
        print('no Instagram key; nothing posted'); return
    delete_wrong()   # one time: the wrong Binance post comes down before its correction goes up
    ig = os.environ['INSTAGRAM_USER_ID']
    pend = load(PENDING, [])
    state = load(STATE, {'posted': {}})
    # Oct 30: Instagram blocked the app ("Application request limit reached", action is blocked) after ~25 posts in 24 hours.
    # Retrying while blocked makes the block longer, so: wait BLOCK_HOURS after a block, and keep under a rolling daily budget.
    bu = state.get('blocked_until')
    if bu and datetime.fromisoformat(bu) > NOW:
        print('::notice::Instagram is cooling down after a block until ' + bu + '; nothing posted this run'); return
    day = [v for v in state['posted'].values() if isinstance(v, dict) and v.get('at') and 'not posted again' not in str(v.get('note', ''))
           and NOW - datetime.fromisoformat(v['at']) < timedelta(hours=24)]
    used = len(day)
    try:
        q = (api(f'{ig}/content_publishing_limit', {'fields': 'quota_usage,config'}).get('data') or [{}])[0]
        used = max(used, int(q.get('quota_usage') or 0))
    except Exception as e:
        print('::warning::could not read the publishing quota: ' + str(e)[:160])
    for p in pend:
        if p['id'] in state['posted']:
            continue
        if used >= DAILY_BUDGET or (p.get('story') and used >= DAILY_BUDGET - 4):   # feed posts keep the last few slots
            print(f'::notice::daily Instagram budget used ({used}/{DAILY_BUDGET} in 24 hours); {p["id"]} waits'); continue
        imgs = p.get('images') or [p['image']]
        urls = [f"{SITE}/{x}?v={p['id']}" for x in imgs]
        live = False
        for _ in range(30):   # wait for GitHub Pages to serve the new pictures (usually under a minute)
            try:
                live = all(urllib.request.urlopen(urllib.request.Request(u, method='HEAD'), timeout=20).status == 200 for u in urls)
            except Exception:
                live = False
            if live:
                break
            time.sleep(10)
        if not live:
            print('::warning::pictures not live yet, will retry next run: ' + p['id']); continue
        # never twice (Oct 30: Instagram published a post while answering with an error, and the retry posted it again): if a post with
        # the same opening words went up in the last 24 hours, record it and move on
        if not p.get('story'):
            try:
                recent = api(f'{ig}/media', {'fields': 'id,caption,timestamp', 'limit': '15'}).get('data', [])
                head = (p.get('caption') or '')[:80]
                dup = next((m for m in recent if head and (m.get('caption') or '')[:80] == head), None)
                if dup:
                    state['posted'][p['id']] = {'at': NOW.isoformat(), 'media': dup.get('id'), 'note': 'already on Instagram; not posted again'}
                    print('::notice::already posted, skipped: ' + p['id']); continue
            except Exception as e:
                print('::warning::could not check for a duplicate, not posting ' + p['id'] + ' this run: ' + str(e)[:200]); continue
        try:
            def wait_ready(cid):
                for _ in range(24):   # Instagram processes each picture before it can be used
                    st = api(cid, {'fields': 'status_code'})
                    if st.get('status_code') in ('FINISHED', None):
                        return
                    if st.get('status_code') == 'ERROR':
                        raise RuntimeError('Instagram could not process a picture')
                    time.sleep(5)
            if p.get('story'):
                c = api(f'{ig}/media', {'image_url': urls[0], 'media_type': 'STORIES'}, 'POST')
            elif len(urls) == 1:
                c = api(f'{ig}/media', {'image_url': urls[0], 'caption': p['caption'][:2150]}, 'POST')
            else:
                kids = []
                for u in urls:
                    k = api(f'{ig}/media', {'image_url': u, 'is_carousel_item': 'true'}, 'POST'); wait_ready(k['id']); kids.append(k['id'])
                c = api(f'{ig}/media', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'caption': p['caption'][:2150]}, 'POST')
            wait_ready(c['id'])
            r = api(f'{ig}/media_publish', {'creation_id': c['id']}, 'POST')
            state['posted'][p['id']] = {'at': NOW.isoformat(), 'media': r.get('id')}
            state.pop('errors', None); state.pop('blocked_until', None)   # posting works again
            used += 1
            print('::notice::posted ' + p['id'] + ' ' + str(r.get('id')))
        except Exception as e:
            print('::warning::post failed ' + p['id'] + ': ' + str(e)[:300])
            if 'action is blocked' in str(e) or 'request limit' in str(e) or '2207051' in str(e):
                state['blocked_until'] = (NOW + timedelta(hours=BLOCK_HOURS)).isoformat()
                er = state.get('errors') or {}
                state['errors'] = {'since': er.get('since') or NOW.isoformat(), 'last': NOW.isoformat(), 'msg': str(e)[:200], 'count': int(er.get('count') or 0) + 1}
                print('::warning::Instagram blocked posting; cooling down until ' + state['blocked_until']); break
            er = state.get('errors') or {}
            state['errors'] = {'since': er.get('since') or NOW.isoformat(), 'last': NOW.isoformat(), 'msg': str(e)[:200], 'count': int(er.get('count') or 0) + 1}   # shown on the status panel; the health check emails the owner
    json.dump(state, open(STATE, 'w'), indent=1)


def delete_wrong():
    """One time (Oct 30): delete the first Binance post, which said "16 minutes before the hack" (later reports: the theft began 3 minutes
    before Gemini's check-in). Found by its caption, since Instagram answered with an error when it was posted."""
    if not os.environ.get('INSTAGRAM_ACCESS_TOKEN'):
        return
    state = load(STATE, {'posted': {}})
    if state.get('deleted', {}).get('feature-binance-v1'):
        return
    ig = os.environ['INSTAGRAM_USER_ID']
    try:
        recent = api(f'{ig}/media', {'fields': 'id,caption', 'limit': '25'}).get('data', [])
        hits = [m for m in recent if (m.get('caption') or '').startswith('Gemini sold every coin it had 16 minutes')]
        for m in hits:
            api(m['id'], {}, 'DELETE'); print('::notice::deleted the wrong Binance post ' + m['id'])
        state.setdefault('deleted', {})['feature-binance-v1'] = {'at': NOW.isoformat(), 'n': len(hits)}
        json.dump(state, open(STATE, 'w'), indent=1)
    except Exception as e:
        print('::warning::could not delete the wrong Binance post yet: ' + str(e)[:200])


def redo(ids):
    """Delete these posts from Instagram and forget them, so the next prepare/publish posts them again (fresh pictures)."""
    state = load(STATE, {'posted': {}})
    for pid in ids:
        rec = state['posted'].get(pid)
        if not rec:
            continue
        try:
            api(rec['media'], {}, 'DELETE')
            print('::notice::deleted ' + pid)
        except Exception as e:
            print('::warning::could not delete ' + pid + ': ' + str(e)[:200])
        state['posted'].pop(pid, None)
    json.dump(state, open(STATE, 'w'), indent=1)


def check():
    if not os.environ.get('INSTAGRAM_ACCESS_TOKEN'):
        print('INSTAGRAM_ACCESS_TOKEN is not set'); sys.exit(1)
    ig = os.environ.get('INSTAGRAM_USER_ID', '').strip()
    tok = os.environ['INSTAGRAM_ACCESS_TOKEN']
    info = f"user id: {len(ig)} digits, {'all digits' if ig.isdigit() else 'NOT all digits'}; key: {len(tok)} characters, starts {tok[:3]!r}, {'has spaces/quotes' if any(c in tok for c in ' \n\"') else 'clean'}"
    try:
        me = api(ig, {'fields': 'username,media_count'})
        msg = 'Instagram key works for @' + me.get('username', '?') + ' · ' + str(me.get('media_count')) + ' posts so far'
        print('::notice::' + msg)
    except Exception as e:
        print('::error::Instagram check failed: ' + str(e)[:300] + ' | ' + info); sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'redo':
        redo(sys.argv[2:])
    else:
        {'prepare': prepare, 'publish': publish, 'check': check}[sys.argv[1] if len(sys.argv) > 1 else 'check']()
