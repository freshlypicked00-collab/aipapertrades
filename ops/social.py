"""Instagram auto-posting for Paper Trades (runs inside the rivals workflow, after its check-in is published).

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
MAX_PER_RUN = 2
NOW = datetime.now(timezone.utc)
START = datetime(2026, 10, 28, tzinfo=timezone.utc)
RACE_END = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)
AIS = {'claude': ('Claude', '#d97757'), 'gemini': ('Gemini', '#4f8ff7'), 'chatgpt': ('ChatGPT', '#f2f2f2')}
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets'}
TAGS = '#PaperTrades #AI #Claude #Gemini #ChatGPT'
FOOT = ('\n\nThree AIs, ten separate races, one month (Oct 28 to Nov 28). Pretend money, real prices; every trade and the reasoning '
        'behind it is published live at papertrades.ai (link in bio).\n\nSimulation only. Not financial advice.\n\n' + TAGS)
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
    for m in reversed(data.get('moments', [])):   # oldest first
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
    if 1 <= n <= 31 and pid not in done and NOW - day_end < timedelta(hours=8) and day_end <= RACE_END + timedelta(hours=4):
        out.append({'id': pid, 'kind': 'daily', 'day': n, 'day_start': (day_end - timedelta(days=1)).isoformat()})
    # stories (they vanish after 24 hours, so they can carry every lead change the site shows, at most one per race per 12 hours)
    srec = [(k, datetime.fromisoformat(v['at'])) for k, v in posted.items() if k.startswith('story-moment-')]
    for m in reversed(data.get('moments', [])):
        sid = 'story-moment-' + m['id']
        at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
        if sid in done or NOW - at > timedelta(hours=6) or at > RACE_END:
            continue
        if any(k.startswith('story-moment-' + m['race'] + '-') and NOW - t < timedelta(hours=12) for k, t in srec):
            continue
        out.append({'id': sid, 'kind': 'story-moment', 'moment': m}); srec.append((sid, NOW))
    if 1 <= n <= 31 and ('story-' + pid) not in done and NOW - day_end < timedelta(hours=8) and day_end <= RACE_END + timedelta(hours=4):
        out.append({'id': 'story-' + pid, 'kind': 'story-daily', 'day': n, 'day_start': (day_end - timedelta(days=1)).isoformat()})
    for k, ds in (('story-ten-2026-10-29', '2026-10-28T00:00:00+00:00'), ('story-ten-2026-10-30', '2026-10-29T00:00:00+00:00')):   # one time: Day 1 and Day 2 with all ten races, for the Daily highlight
        if k not in done:
            out.append({'id': k, 'kind': 'story-daily', 'day': (datetime.fromisoformat(ds) + timedelta(days=1) - START).days, 'day_start': ds})
    if 'day1-remake-v1' not in done and NOW < datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc):   # the owner's remade Day 1 post (one time)
        out.insert(0, {'id': 'day1-remake-v1', 'kind': 'day1'})
        out.append({'id': 'story-day1-remake-v1', 'kind': 'story-day1'})
    if 'day1-ten-v1' not in done and NOW < datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc):   # owner, Oct 30: Day 1 again, "Day 1 results" then one slide per race
        out.insert(0, {'id': 'day1-ten-v1', 'kind': 'dayten', 'day': 1, 'day_start': '2026-10-28T00:00:00+00:00', 'cutoff': '2026-10-29T00:00:00+00:00'})
    if 'intro-v1' not in done and NOW < RACE_END:
        out.insert(0, {'id': 'intro-v1', 'kind': 'intro'})
    if 'story-intro-v1' not in done and NOW < RACE_END:
        out.append({'id': 'story-intro-v1', 'kind': 'story-intro'})
    feed = [p for p in out if not p['kind'].startswith('story')][:MAX_PER_RUN]
    return feed + [p for p in out if p['kind'].startswith('story')][:3]


def prepare():
    state = load(STATE, {'posted': {}})
    posts = due_posts(state)
    os.makedirs('social', exist_ok=True)
    ready = []
    for p in posts:
        img = f"social/{p['id']}.jpg"
        try:
            if p['kind'] == 'story-moment':
                pc.moment_cover(p['moment'], '/tmp/pt_cover.jpg', glow=False)
                pc.story('/tmp/pt_cover.jpg', img, top='LEAD CHANGE', glow_color=pc.AIS[p['moment']['who']][1])
                p['images'] = [img]; p['story'] = True; p['caption'] = ''
            elif p['kind'] == 'story-daily':
                import racecard
                table, big = racecard.races(datetime.fromisoformat(p['day_start']), 'ops/src')
                # every race on the story itself, who leads each and by how much (owner, Oct 29: the Day 1 story showed only the sports bets)
                old = ({'story-ten-2026-10-29': 'social/day1-remake-v1-3.jpg'}.get(p['id']) or f"social/daily-{p['id'][-10:]}-races.jpg") if p['id'].startswith('story-ten-') else None   # a past day: the picture made at its close (Day 1: the corrected remake)
                if old and os.path.exists(old):
                    import shutil; shutil.copy(old, '/tmp/pt_cover.jpg')
                else:
                    pc.daily(table, p['day'], datetime.fromisoformat(p['day_start']), big, '/tmp/pt_cover.jpg')
                led = pc.races_led(table); best = max(led, key=lambda k: len(led[k]))
                pc.story('/tmp/pt_cover.jpg', img, top=f"DAY {p['day']} RESULTS · ALL TEN RACES", bottom='Every trade, live: papertrades.ai', glow_color=pc.AIS[best][1] if sum(len(v) == len(led[best]) for v in led.values()) == 1 else pc.AMBER)
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
                                f"(8 p.m. ET, Oct 28), each judged on its own (profit since the Oct 28 restart):\n\n" + '\n'.join(lines) + FOOT)
            elif p['kind'] in ('intro', 'story-intro'):
                import racecard
                table, _ = racecard.races(None, 'ops/src')
                paths = pc.intro_slides(table, f"social/{p['id'].replace('story-', '')}")
                if p['kind'] == 'story-intro':
                    pc.story(paths[0], img, top='START HERE', bottom='How it works: our pinned post', glow_color=pc.AMBER)
                    p['images'] = [img]; p['story'] = True; p['caption'] = ''
                else:
                    p['images'] = paths
                    p['caption'] = ('What is Paper Trades? 🤖📈\n\nClaude vs Gemini vs ChatGPT. Each AI got C$100,000 of pretend money in ten separate races, '
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
    ig = os.environ['INSTAGRAM_USER_ID']
    pend = load(PENDING, [])
    state = load(STATE, {'posted': {}})
    for p in pend:
        if p['id'] in state['posted']:
            continue
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
            state.pop('errors', None)   # posting works again
            print('::notice::posted ' + p['id'] + ' ' + str(r.get('id')))
        except Exception as e:
            print('::warning::post failed ' + p['id'] + ': ' + str(e)[:300])
            er = state.get('errors') or {}
            state['errors'] = {'since': er.get('since') or NOW.isoformat(), 'last': NOW.isoformat(), 'msg': str(e)[:200], 'count': int(er.get('count') or 0) + 1}   # shown on the status panel; the health check emails the owner
    json.dump(state, open(STATE, 'w'), indent=1)


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
