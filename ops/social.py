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
    return out[:MAX_PER_RUN]


def prepare():
    state = load(STATE, {'posted': {}})
    posts = due_posts(state)
    os.makedirs('social', exist_ok=True)
    ready = []
    for p in posts:
        img = f"social/{p['id']}.jpg"
        try:
            if p['kind'] == 'moment':
                pc.moment_cover(p['moment'], img)
                p['images'] = [img]
            else:
                import racecard
                table, big = racecard.races(datetime.fromisoformat(p['day_start']), 'ops/src')
                when = datetime.fromisoformat(p['day_start'])
                pc.daily_cover(table, p['day'], when, big, img)
                img2 = f"social/{p['id']}-races.jpg"
                pc.daily(table, p['day'], when, big, img2)
                p['images'] = [img, img2]   # a carousel: the bold cover, then every race
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
            if len(urls) == 1:
                c = api(f'{ig}/media', {'image_url': urls[0], 'caption': p['caption'][:2150]}, 'POST')
            else:
                kids = []
                for u in urls:
                    k = api(f'{ig}/media', {'image_url': u, 'is_carousel_item': 'true'}, 'POST'); wait_ready(k['id']); kids.append(k['id'])
                c = api(f'{ig}/media', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'caption': p['caption'][:2150]}, 'POST')
            wait_ready(c['id'])
            r = api(f'{ig}/media_publish', {'creation_id': c['id']}, 'POST')
            state['posted'][p['id']] = {'at': NOW.isoformat(), 'media': r.get('id')}
            print('::notice::posted ' + p['id'] + ' ' + str(r.get('id')))
        except Exception as e:
            print('::warning::post failed ' + p['id'] + ': ' + str(e)[:300])
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
