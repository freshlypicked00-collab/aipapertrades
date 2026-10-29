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
TAGS = '#AI #Claude #Gemini #ChatGPT #PaperTrading #Investing #Crypto #Stocks'
FOOT = '\n\nTen separate live races, pretend money, real prices. Every trade and reason: papertrades.ai (link in bio). Not financial advice.\n\n' + TAGS


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


# ---------- pictures
def moment_card(m, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'text.parse_math': False})
    BG, FG, MUTED, UP, DOWN = '#14130f', '#f2f2f2', '#9b927f', '#3ddc84', '#ff6b6b'
    who, over, race = m['who'], m['over'], m['race']
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1080); ax.set_ylim(1080, 0); ax.axis('off')
    ax.add_patch(plt.Rectangle((0, 0), 1080, 14, color=AIS[who][1]))
    ax.text(80, 110, 'PAPER TRADES · AI VS AI', color='#d97757', fontsize=22, fontweight='bold')
    when = datetime.fromisoformat(m['at'].replace('Z', '+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
    ax.text(80, 160, f"{LABEL.get(race, race).upper()} · {when.strftime('%b %-d')}", color=MUTED, fontsize=22)
    ax.text(80, 290, f"{AIS[who][0]} takes", color=AIS[who][1], fontsize=66, fontweight='bold')
    ax.text(80, 385, 'the lead', color=AIS[who][1], fontsize=66, fontweight='bold')
    ax.text(80, 480, f"Overtook {AIS[over][0]} in {LABEL.get(race, race)},", color=FG, fontsize=32)
    ax.text(80, 535, f"ahead by {money(m['lead'], race).lstrip('+')}.", color=FG, fontsize=32)
    prof = m.get('profit') or {}
    ids = sorted(prof, key=lambda k: -prof[k])
    pos = max([v for v in prof.values() if v > 0] + [0]); neg = max([-v for v in prof.values() if v < 0] + [0])
    span = 440.0; tot = (pos + neg) or 1
    x0 = 300 + span * neg / tot   # the zero line: profits grow right of it, losses left of it
    ax.plot([x0, x0], [630, 640 + 76 * len(ids)], color=MUTED, lw=1.5)
    y = 650
    for i in ids:
        v = prof[i]; w = max(4, span * abs(v) / tot)
        ax.text(80, y + 26, AIS[i][0], color=FG, fontsize=26, fontweight='bold', va='center')
        ax.add_patch(plt.Rectangle((x0 if v >= 0 else x0 - w, y + 6), w, 40, color=AIS[i][1], alpha=1 if v >= 0 else 0.5))
        ax.text(max(x0 + (w if v >= 0 else 0), x0) + 16, y + 26, money(v, race), color=UP if v >= 0 else DOWN, fontsize=24, fontweight='bold', va='center')
        y += 76
    ax.text(80, 950, 'Profit in this race since Oct 28 · pretend money, real prices', color=MUTED, fontsize=19)
    ax.text(80, 1004, 'papertrades.ai', color=FG, fontsize=25, fontweight='bold')
    ax.text(1000, 1004, '@PaperTradesAI', color=MUTED, fontsize=20, ha='right')
    fig.savefig(path, dpi=1440 / 10.8, facecolor=BG, format='jpg', pil_kwargs={'quality': 95, 'subsampling': 0})   # 1440x1440, the largest Instagram keeps
    plt.close(fig)


def daily_card(table, big, n, when, path):
    """The ten races after a daily close, as a tall 4:5 picture (1440x1800) that fills a phone screen in the feed."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import racecard
    plt.rcParams.update({'text.parse_math': False})
    BG, FG, MUTED, UP, DOWN = '#0b0b0a', '#f2e9d8', '#9b927f', '#3ddc84', '#ff5a4e'
    fig = plt.figure(figsize=(10.8, 13.5), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1080); ax.set_ylim(1350, 0); ax.axis('off')
    ax.text(60, 80, 'PAPER TRADES', color='#ffb000', fontsize=30, fontweight='bold', family='monospace')
    ax.text(60, 132, f"After Day {n} · {when.strftime('%a %b %-d')}", color=FG, fontsize=24)
    ax.text(60, 174, 'Ten separate races · each on its own · profit since Oct 28', color=MUTED, fontsize=16)
    y = 205
    for i, e in enumerate(racecard.ORDER):
        rows = table.get(e) or []
        ax.add_patch(plt.Rectangle((40, y), 1000, 96, color='#16150f' if i % 2 == 0 else '#0f0e0b', zorder=0))
        ax.text(60, y + 30, (racecard.LABEL.get(e, e) + (' (US$)' if e == 'China' else '')).upper(), color=MUTED, fontsize=15, fontweight='bold', va='center')
        if not rows or max(r[1] for r in rows) - min(r[1] for r in rows) < 0.5:
            ax.text(60, y + 70, 'All even so far' if rows else 'No results yet', color=MUTED, fontsize=20, va='center')
        else:
            for j, (mid, p) in enumerate(rows[:3]):
                x = 60 + j * 335
                lead = j == 0 and len(rows) > 1 and p - rows[1][1] >= 0.5
                ax.add_patch(plt.Rectangle((x, y + 52), 7, 36, color=racecard.AIS[mid][2]))
                ax.text(x + 18, y + 70, ('👑 ' if False else '') + racecard.AIS[mid][0], color=FG, fontsize=20, fontweight='bold' if lead else 'normal', va='center')
                ax.text(x + 300, y + 70, racecard.money(p, e), color=UP if p >= 0 else DOWN, fontsize=19, ha='right', va='center', family='monospace', fontweight='bold')
        y += 101
    if big:
        _, mid, e, d, pct = big
        ax.text(60, 1262, f"Biggest move: {racecard.AIS[mid][0]} in {racecard.LABEL.get(e, e)}, {racecard.money(d, e)} ({pct * 100:+.1f}%)", color=UP if d >= 0 else DOWN, fontsize=19)
    ax.text(60, 1322, 'papertrades.ai · @PaperTradesAI · pretend money, real prices', color=MUTED, fontsize=15)
    fig.savefig(path, dpi=1440 / 10.8, facecolor=BG, format='jpg', pil_kwargs={'quality': 95, 'subsampling': 0})
    plt.close(fig)


def to_jpg(png, jpg):
    from PIL import Image
    Image.open(png).convert('RGB').save(jpg, 'JPEG', quality=90)


# ---------- what is due
def due_posts(state):
    done = set(state.get('posted', {}))
    out = []
    data = load('data.json', {})
    for m in reversed(data.get('moments', [])):   # oldest first
        pid = 'moment-' + m['id']
        at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
        if pid in done or NOW - at > timedelta(hours=6) or at > RACE_END:
            continue
        cap = (f"⚡ {AIS[m['who']][0]} just took the lead in {LABEL.get(m['race'], m['race'])} from {AIS[m['over']][0]}, "
               f"ahead by {money(m['lead'], m['race']).lstrip('+')}." + FOOT)
        out.append({'id': pid, 'kind': 'moment', 'moment': m, 'caption': cap})
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
                moment_card(p['moment'], img)
            else:
                import racecard
                table, big = racecard.races(datetime.fromisoformat(p['day_start']), 'ops/src')
                when = datetime.fromisoformat(p['day_start'])
                daily_card(table, big, p['day'], when, img)
                medal = ['🥇', '🥈', '🥉']
                lines = []
                for e in racecard.ORDER:
                    rows = table.get(e) or []
                    if not rows:
                        continue
                    if max(x[1] for x in rows) - min(x[1] for x in rows) < 0.5:
                        lines.append(f"{LABEL[e]}: all even so far")
                    else:
                        lines.append(f"{LABEL[e]}: {medal[0]} {AIS[rows[0][0]][0]} {money(rows[0][1], e)}")
                p['caption'] = f"🏁 After Day {p['day']}: who leads each of the ten races\n\n" + '\n'.join(lines) + FOOT
            p['image'] = img
            ready.append({k: v for k, v in p.items() if k != 'moment'})
        except Exception as e:
            print('could not draw', p['id'], e)
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
        url = f"{SITE}/{p['image']}?v={p['id']}"
        live = False
        for _ in range(30):   # wait for GitHub Pages to serve the new picture (usually under a minute)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=20) as r:
                    live = r.status == 200 and 'image' in (r.headers.get('Content-Type') or '')
            except Exception:
                live = False
            if live:
                break
            time.sleep(10)
        if not live:
            print('picture not live yet, will retry next run:', url); continue
        try:
            c = api(f'{ig}/media', {'image_url': url, 'caption': p['caption'][:2150]}, 'POST')
            for _ in range(12):   # Instagram processes the picture before it can be published
                st = api(c['id'], {'fields': 'status_code'})
                if st.get('status_code') in ('FINISHED', None):
                    break
                if st.get('status_code') == 'ERROR':
                    raise RuntimeError('Instagram could not process the picture')
                time.sleep(5)
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
