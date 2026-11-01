"""Daily appointment posts (owner, Oct 30; Claude, Gemini and ChatGPT all agreed: W11 and W12 in ops/review/WATCH_DECISIONS.md).

    python3 ops/daycards.py slate     # 6:30 p.m. ET: "Tonight's slate": every open Sports bet of all three AIs on tonight's games
    python3 ops/daycards.py preview   # 9:05 a.m. ET, weekdays: "Day N preview": today's scheduled events and each AI's published plan
    python3 ops/daycards.py weekly    # 5:05 p.m. ET, Sundays: "Week N recap": who leads each race, races led, biggest win, worst loss
    python3 ops/daycards.py stash     # after posting: keep what was sent (ops/src/daycards_sent.json, ops/src/x_sent.json) in /tmp
    python3 ops/daycards.py merge     # on the latest main: merge the stashed records back in (other runs push these files too)

Posts go to Telegram, Discord and X; not Instagram while Meta's request limit is pausing posts (Gemini's change, Claude agreed).
Skipped when there is nothing to show (ChatGPT's change: an empty or already settled slate is not posted). Each card is sent at most
once per Eastern day. Never invents anything: odds, stakes, events and plans are exactly what was recorded; a missing plan says
"no plan posted yet" (ChatGPT's change). Posts never add the races together (owner's rule before Nov 28).
Times: GitHub's schedule runs this at both possible UTC times (Eastern daylight time ends Nov 1); the script only acts inside the
Eastern window, so it posts once. FORCE=1 skips the window check (manual runs), DRY=1 builds the card and prints without posting.
"""
import html as _html
import json
import os
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharecard as C  # noqa: E402

ET = ZoneInfo('America/New_York')
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
SENT = os.path.join(SRC, 'daycards_sent.json')
XSENT = os.path.join(SRC, 'x_sent.json')
SITE = 'https://papertrades.ai'
START_DAY, DAYS = datetime(2026, 10, 28).date(), 32
RACE_END = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)
NOW = datetime.fromisoformat(os.environ['PT_NOW']) if os.environ.get('PT_NOW') else datetime.now(timezone.utc)
FORCE, DRY = bool(os.environ.get('FORCE')), bool(os.environ.get('DRY'))
AIS = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
ORDER = ['claude', 'gemini', 'chatgpt']


def load(name, default):
    try:
        return json.load(open(os.path.join(SRC, name)))
    except Exception:
        return default


def at(s):
    try:
        d = datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def hm(d):
    return d.astimezone(ET).strftime('%-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.').replace(':00 ', ' ')


def odds_txt(o):
    try:
        o = int(round(float(o)))
        return ('+' if o > 0 else '−') + str(abs(o))
    except Exception:
        return ''


def cad(v):
    return 'C$' + f'{abs(float(v)):,.0f}'


def short_team(name):
    """'New York Knicks' -> 'Knicks' for compact lines (the last word, two for names like 'Trail Blazers' / 'Red Sox')."""
    w = str(name or '').split()
    if len(w) >= 3 and w[-2] in ('Trail', 'Red', 'White', 'Blue', 'Maple', 'Golden', 'Green', 'Fighting', 'Crimson', 'Sun', 'Tar', 'Blue'):
        return ' '.join(w[-2:])
    return w[-1] if w else ''


def short_event(ev):
    if ' @ ' in str(ev):
        a, h = str(ev).split(' @ ', 1)
        return f'{short_team(a)} @ {short_team(h)}'
    return str(ev)


# ------------------------------------------------------------------ the open bets of all three AIs (main Sports race)
def open_bets():
    out = []
    for b in (load('bets.json', []) if isinstance(load('bets.json', []), list) else load('bets.json', {}).get('bets', [])):
        if b.get('status') != 'Open':
            continue
        legs = b.get('legs') or []
        out.append({'ai': 'claude', 'id': b.get('bet'), 'league': b.get('sport') or '', 'event': b.get('event') or '',
                    'start': at(b.get('starts_at') or (legs[0].get('starts_at') if legs else None)),
                    'pick': str(b.get('pick') or '').replace(' moneyline', ''), 'odds': b.get('odds'), 'stake': b.get('stake_cad'),
                    'legs': [{'event': x.get('event'), 'pick': str(x.get('pick') or '').replace(' moneyline', ''), 'start': at(x.get('starts_at'))} for x in legs]})
    r = load('rivals.json', {})
    for mid in ('gemini', 'chatgpt'):
        bk = (((r.get('models') or {}).get(mid) or {}).get('books') or {}).get('Sports') or {}
        for b in bk.get('bets', []):
            if b.get('status') != 'Open':
                continue
            legs = b.get('legs') or []
            out.append({'ai': mid, 'id': b.get('id'), 'league': b.get('short') or '', 'event': b.get('event') or '',
                        'start': at(b.get('starts_at') or (legs[0].get('starts_at') if legs else None)),
                        'pick': b.get('pick_team') or b.get('pick') or '', 'odds': b.get('odds'), 'stake': b.get('stake'),
                        'legs': [{'event': x.get('event'), 'pick': x.get('pick_team') or x.get('pick'), 'start': at(x.get('starts_at'))} for x in legs]})
    return [b for b in out if b['start']]


def combine(bets):
    """Several bets by the same AI on the same pick at the same odds (placed on different days) shown as one line with the count and total."""
    out, idx = [], {}
    for b in sorted(bets, key=lambda b: (b['start'], ORDER.index(b['ai']))):
        k = (b['ai'], b['event'], b['start'], str(b['pick']), str(b['odds']), bool(b['legs']), b['id'] if b['legs'] else '')
        if k in idx:
            c = idx[k]; c['n'] += 1; c['stake'] = (c.get('stake') or 0) + (b.get('stake') or 0)
        else:
            c = dict(b, n=1); idx[k] = c; out.append(c)
    return out


def stake_txt(b):
    return (f"{b['n']} bets · {cad(b['stake'])} total" if b.get('n', 1) > 1 else cad(b['stake'])) if b.get('stake') else ''


def tonight(bets):
    """Bets on games from 4 hours ago (still live, not settled) to 6 a.m. Eastern tomorrow."""
    et = NOW.astimezone(ET)
    end = (et + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    lo = NOW - timedelta(hours=4)
    return [b for b in bets if lo <= b['start'] <= end.astimezone(timezone.utc)]


# ------------------------------------------------------------------ sending
def tg_send(text, photo):
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_CHAT_ID', '')
    if not (tok and chat):
        print('(no Telegram secrets)')
        return False
    try:
        if photo and len(text) <= 1000:
            b = '----ptdc' + str(os.getpid())
            parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in
                     (('chat_id', chat), ('caption', text), ('parse_mode', 'HTML'), ('disable_notification', 'false'))]
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="c.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(photo, 'rb').read() + f'\r\n--{b}--\r\n'.encode())
            req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendPhoto', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={b}'})
            urllib.request.urlopen(req, timeout=30).read()
            return True
        if photo:
            tg_send('<b>PAPERTRADES.AI</b>', photo)
        data = urllib.parse.urlencode({'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}).encode()
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data, timeout=20).read()
        return True
    except Exception as e:
        print('::warning::Telegram failed:', str(e)[:200])
        return False


def publish(kind, tg_text, x_text, photo, tab):
    day = NOW.astimezone(ET).date().isoformat()
    key = f'{kind}-{day}'
    sent = load('daycards_sent.json', {})
    if key in sent and not FORCE:
        print('already sent today:', key)
        return
    if DRY:
        print('--- DRY RUN ---\n' + tg_text + '\n--- X ---\n' + x_text + '\n--- picture:', photo)
        return
    ok_tg = tg_send(tg_text, photo)
    ok_dc = False
    try:
        import discord
        ok_dc = discord.post(tg_text, photo, url=discord.DAILY or discord.URL, ping=discord.ROLE_DAILY if kind == 'weekly' else None)
    except Exception as e:
        print('::warning::Discord failed:', str(e)[:200])
    ok_x = False
    try:
        import xpost
        ok_x = xpost.post(x_text, photo, key=key, reply_link=f'{SITE}/?utm_source=x' + ('#' + tab if tab else ''))
    except Exception as e:
        print('::warning::X failed:', str(e)[:200])
    sent[key] = {'at': NOW.isoformat(timespec='seconds'), 'telegram': ok_tg, 'discord': ok_dc, 'x': ok_x}
    json.dump(sent, open(SENT, 'w'), indent=1)
    print(f'::notice::{key}: Telegram {ok_tg}, Discord {ok_dc}, X {ok_x}')


# ------------------------------------------------------------------ W11: Tonight's slate
def slate_card(rows, path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (C.S, C.H2), C.BG)
    g = ImageDraw.Draw(im)
    g.rectangle([0, 0, C.S, 14], fill=C.ORANGE)
    g.text((80, 70), 'PAPER TRADES · AI VS AI', font=C._font('bold', 30), fill=C.ORANGE)
    g.text((80, 116), 'SPORTS BETTING · ' + NOW.astimezone(ET).strftime('%a %b %-d').upper(), font=C._font('med', 30), fill=C.MUTED)
    y = C._wrap(g, "Tonight's slate", C._font('bold', 86), 80, 170, C.S - 160, 96, C.FG, max_lines=1)
    games = {}
    for b in rows:
        games.setdefault((b['start'], b['event'] if not b['legs'] else 'Parlays'), []).append(b)
    n_g = len({k[1] for k in games if k[1] != 'Parlays'})
    nb = sum(b.get('n', 1) for b in rows)
    y = C._wrap(g, f"{nb} open bet{'s' if nb != 1 else ''} from the three AIs on {n_g} game{'s' if n_g != 1 else ''}", C._font('med', 36), 80, y + 6, C.S - 160, 46, C.MUTED, max_lines=2) + 18
    shown = 0
    keys = sorted(games, key=lambda k: (k[1] == 'Parlays', k[0]))
    for k in keys:
        if y > C.H2 - 330:
            break
        start, ev = k
        live = start <= NOW
        lab = 'LIVE NOW' if live else hm(start)
        lg = games[k][0]['league']
        g.text((80, y), lab, font=C._font('bold', 32), fill=C.DOWN if live else C.FG)
        x2 = 80 + g.textlength(lab, font=C._font('bold', 32))
        sub = '  ·  ' + (f'{lg} · ' if lg and ev != 'Parlays' else '') + (short_event(ev) if ev != 'Parlays' else 'Parlays')
        g.text((x2, y + 3), sub, font=C._font('med', 30), fill=C.MUTED)
        y += 50
        for b in sorted(games[k], key=lambda b: ORDER.index(b['ai'])):
            if y > C.H2 - 270:
                break
            C._robot(im, b['ai'], 80, y - 2, 42)
            g = ImageDraw.Draw(im)
            g.text((134, y), AIS[b['ai']], font=C._font('semi', 34), fill=C.AIS[b['ai']][1])
            pick = (' + '.join(short_team(x['pick']) or x['pick'] for x in b['legs'][:4]) if b['legs'] else short_team(b['pick']) or b['pick'])
            right = ' · '.join(x for x in (odds_txt(b['odds']), stake_txt(b)) if x)
            fr = C._font('semi', 32)
            wr = g.textlength(right, font=fr)
            px = 134 + g.textlength(AIS[b['ai']], font=C._font('semi', 34)) + 18
            ptxt = pick
            while g.textlength(ptxt, font=C._font('med', 34)) > C.S - 80 - wr - 30 - px and len(ptxt) > 4:
                ptxt = ptxt[:-2].rstrip() + '…'
            g.text((px, y), ptxt, font=C._font('med', 34), fill=C.FG)
            g.text((C.S - 80 - wr, y + 2), right, font=fr, fill=C.FG)
            y += 52
            shown += 1
        y += 18
    if shown < len(rows):
        g.text((80, y), f'+{len(rows) - shown} more on papertrades.ai', font=C._font('med', 30), fill=C.MUTED)
        y += 48
    return C._finish(im, g, y + 20, path, 'Pretend money, real odds · results post as each game ends')


def slate():
    et = NOW.astimezone(ET)
    if not FORCE and not (18 * 60 + 15 <= et.hour * 60 + et.minute <= 20 * 60 + 30):
        print('outside the 6:15-8:30 p.m. ET window:', et.strftime('%H:%M'))
        return
    if NOW >= RACE_END:
        print('the race is over')
        return
    raw = tonight(open_bets())
    rows = combine(raw)
    if not rows:
        print('no open bets on tonight\'s games: nothing to post')   # ChatGPT's change: skip an empty slate
        return
    photo = slate_card(rows, '/tmp/slate.png')
    day = et.strftime('%a %b %-d')
    games = {}
    for b in sorted(rows, key=lambda b: (bool(b['legs']), b['start'], ORDER.index(b['ai']))):
        games.setdefault((b['start'], b['event'] if not b['legs'] else 'Parlays'), []).append(b)
    tg = [f"🏟 <b>Tonight's slate</b> · {day}", 'Every open Sports bet of the three AIs on tonight\'s games:', '']
    xl = [f"🏟 Tonight's slate · {day}: {len(raw)} open bets from Claude, Gemini and ChatGPT"]
    for (start, ev), bs in games.items():
        lab = 'LIVE NOW' if start <= NOW else hm(start) + ' ET'
        tg.append(f"<b>{lab}</b> · " + (f"{_html.escape(bs[0]['league'])} · " if bs[0]['league'] and ev != 'Parlays' else '') + _html.escape(short_event(ev) if ev != 'Parlays' else 'Parlays'))
        for b in bs:
            pick = ' + '.join(x['pick'] for x in b['legs']) if b['legs'] else b['pick']
            tg.append(f"• {AIS[b['ai']]}: {_html.escape(str(pick))} {odds_txt(b['odds'])}" + (f" · {stake_txt(b)}" if b.get('stake') else ''))
        if ev != 'Parlays':
            xl.append(f"{hm(start) if start > NOW else 'Live'} {short_event(ev)}: " + ', '.join(f"{AIS[b['ai']]} {short_team(b['pick'])}" + (f" ×{b['n']}" if b.get('n', 1) > 1 else '') for b in bs))
        tg.append('')
    tg.append('Results, with the final score, post as each game ends.')
    tg.append(f'{SITE} · Pretend money, not advice.')
    import xpost
    x_text = xpost.fit('\n'.join(xl) + '\nResults with final scores as each game ends.') if hasattr(xpost, 'fit') else '\n'.join(xl)[:260]
    publish('slate', '\n'.join(tg), x_text, photo, 'sports')


# ------------------------------------------------------------------ W12: Day N preview
def plan_of(mid):
    """The AI's latest published plan for the next 24 hours (overall, not a race card), if written in the last 36 hours."""
    if mid == 'claude':
        ps = [p for p in load('plans.json', []) if p.get('model') == 'claude' and p.get('horizon') == 'day' and not p.get('experiment')]
    else:
        ps = [p for p in load('rivals.json', {}).get('plans', []) if p.get('model') == mid and p.get('horizon') == 'day' and not p.get('experiment')]
    ps = [p for p in ps if at(p.get('at')) and NOW - at(p['at']) <= timedelta(hours=36)]
    return max(ps, key=lambda p: at(p['at']))['text'] if ps else None


def today_events():
    et = NOW.astimezone(ET).date()
    ev = load('events.json', [])
    ev = ev if isinstance(ev, list) else ev.get('events', [])
    out = [e for e in ev if at(e.get('at')) and at(e['at']).astimezone(ET).date() == et]
    return sorted(out, key=lambda e: at(e['at']))


def preview_card(n, evs, games_n, bets_n, plans, path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (C.S, C.H2), C.BG)
    g = ImageDraw.Draw(im)
    g.rectangle([0, 0, C.S, 14], fill=C.ORANGE)
    g.text((80, 70), 'PAPER TRADES · AI VS AI', font=C._font('bold', 30), fill=C.ORANGE)
    g.text((80, 116), 'SEASON 1 · ' + NOW.astimezone(ET).strftime('%a %b %-d').upper(), font=C._font('med', 30), fill=C.MUTED)
    y = C._wrap(g, f'Day {n} of {DAYS} preview', C._font('bold', 80), 80, 170, C.S - 160, 90, C.FG, max_lines=1) + 14
    g.text((80, y), "WHAT'S ON TODAY (ET)", font=C._font('semi', 26), fill=C.MUTED)
    y += 40
    if evs:
        for e in evs[:5]:
            t = at(e['at'])
            line = f"{hm(t)}  {e['event']}"
            y = C._wrap(g, line, C._font('med', 32), 80, y, C.S - 160, 40, C.FG, max_lines=1) + 4
    else:
        y = C._wrap(g, 'No scheduled releases on our calendar today.', C._font('med', 32), 80, y, C.S - 160, 40, C.MUTED, max_lines=1) + 4
    if bets_n:
        y = C._wrap(g, f"Tonight: {bets_n} open bet{'s' if bets_n != 1 else ''} on {games_n} game{'s' if games_n != 1 else ''} · slate at 6:30 p.m.", C._font('med', 32), 80, y, C.S - 160, 40, C.FG, max_lines=1) + 4
    y += 22
    g.text((80, y), "EACH AI'S PLAN FOR TODAY · IN ITS OWN WORDS", font=C._font('semi', 26), fill=C.MUTED)
    y += 44
    for mid in ORDER:
        C._robot(im, mid, 80, y, 48)
        g = ImageDraw.Draw(im)
        g.text((140, y + 4), AIS[mid], font=C._font('semi', 36), fill=C.AIS[mid][1])
        y += 58
        txt = plans.get(mid)
        y = C._wrap(g, ('“' + C._clip(txt, 230) + '”') if txt else 'No plan posted yet.', C._font('med' if txt else 'reg', 31), 80, y, C.S - 160, 40, C.FG if txt else C.MUTED, max_lines=5) + 16
    return C._finish(im, g, y + 10, path, 'Pretend money, real prices · every move live on papertrades.ai')


def preview():
    et = NOW.astimezone(ET)
    if not FORCE and (et.weekday() >= 5 or not (8 * 60 + 55 <= et.hour * 60 + et.minute <= 10 * 60 + 45)):
        print('outside the weekday 8:55-10:45 a.m. ET window:', et.strftime('%a %H:%M'))
        return
    if NOW >= RACE_END:
        print('the race is over')
        return
    n = (et.date() - START_DAY).days + 1
    if not 1 <= n <= DAYS:
        return
    evs = today_events()
    bets = tonight(open_bets())
    games_n = len({b['event'] for b in bets if not b['legs']})
    plans = {mid: plan_of(mid) for mid in ORDER}
    photo = preview_card(n, evs, games_n, len(bets), plans, '/tmp/preview.png')
    tg = [f"☀️ <b>Day {n} of {DAYS} preview</b> · {et.strftime('%a %b %-d')}", '']
    if evs:
        tg.append('<b>What\'s on today (ET)</b>')
        tg += [f"• {hm(at(e['at']))}: {_html.escape(e['event'])}" for e in evs[:6]]
        tg.append('')
    if bets:
        tg += [f"Tonight: {len(bets)} open bets on {games_n} games · slate at 6:30 p.m. ET", '']
    tg.append("<b>Each AI's plan for today, in its own words</b>")
    for mid in ORDER:
        tg.append(f"• <b>{AIS[mid]}</b>: " + (_html.escape(C._clip(plans[mid], 300)) if plans[mid] else 'no plan posted yet'))
    tg += ['', f'{SITE} · Pretend money, not advice.']
    xl = [f"☀️ Day {n} of {DAYS} · {et.strftime('%a %b %-d')}: what's on today and each AI's plan, in its own words"]
    if evs:
        xl.append('Today: ' + ' · '.join(f"{hm(at(e['at']))} {C._clip(e['event'], 40)}" for e in evs[:3]))
    import xpost
    x_text = xpost.fit('\n'.join(xl)) if hasattr(xpost, 'fit') else '\n'.join(xl)[:260]
    publish('preview', '\n'.join(tg), x_text, photo, '')


# ------------------------------------------------------------------ Weekly recap, Sundays 5:05 p.m. ET (Gemini's idea; Claude agreed, 2 of 3)
RACES = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
RLABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
          'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets'}


def site_data():
    try:
        return json.load(open(os.path.join(os.path.dirname(SRC), '..', 'data.json')))
    except Exception:
        try:
            return json.load(open('data.json'))
        except Exception:
            return {}


def week_facts():
    d = site_data()
    es = d.get('exp_standings') or {}
    es = es[0] if isinstance(es, list) and es else es
    et = NOW.astimezone(ET)
    lo = max(NOW - timedelta(days=7), datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc))
    leaders, led = [], {k: 0 for k in ORDER}
    for race in RACES:
        rows = [r for r in (es.get(race) or []) if r.get('id') in AIS]
        rows.sort(key=lambda r: -float(r.get('profit') or 0))
        if len(rows) > 1 and float(rows[0]['profit']) - float(rows[1]['profit']) >= 0.5:
            leaders.append((race, rows[0]['id'], float(rows[0]['profit'])))
            led[rows[0]['id']] += 1
        else:
            leaders.append((race, None, None))
    ms = [m for m in (d.get('moments_all') or []) if at(m.get('at')) and at(m['at']) >= lo and m.get('who') in AIS]
    wins = [m for m in ms if m.get('type') == 'win']
    losses = [m for m in ms if m.get('type') == 'loss']
    leads = [m for m in ms if (m.get('type') or 'lead') == 'lead']
    best = max(wins, key=lambda m: float(m.get('amount') or 0), default=None)
    worst = min(losses, key=lambda m: float(m.get('amount') or 0), default=None)
    streaks = [s for s in (d.get('streaks') or []) if s.get('n', 0) >= 3 and s.get('id') in AIS]
    n = 1 + max(0, (et.date() - datetime(2026, 11, 1).date()).days // 7)
    return {'n': n, 'from': lo, 'leaders': leaders, 'led': led, 'best': best, 'worst': worst, 'leads': leads, 'streaks': streaks}


def money_r(v, race):
    return ('+' if v >= 0 else '−') + ('US$' if race == 'China' else 'C$') + f'{abs(v):,.0f}'


def what_of(m):
    return str(m.get('what') or '').split(' (')[0]


def weekly_card(f, path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (C.S, C.H2), C.BG)
    g = ImageDraw.Draw(im)
    g.rectangle([0, 0, C.S, 14], fill=C.ORANGE)
    g.text((80, 70), 'PAPER TRADES · AI VS AI', font=C._font('bold', 30), fill=C.ORANGE)
    span = f["from"].astimezone(ET).strftime('%b %-d') + ' – ' + NOW.astimezone(ET).strftime('%b %-d')
    g.text((80, 116), ('SEASON 1 · ' + span).upper(), font=C._font('med', 30), fill=C.MUTED)
    y = C._wrap(g, f'Week {f["n"]} recap', C._font('bold', 84), 80, 166, C.S - 160, 92, C.FG, max_lines=1) + 10
    g.text((80, y), 'WHO LEADS EACH RACE · EACH RACE ON ITS OWN', font=C._font('semi', 26), fill=C.MUTED)
    y += 40
    for race, who, prof in f['leaders']:
        g.text((80, y), RLABEL[race], font=C._font('med', 31), fill=C.FG)
        if who:
            C._robot(im, who, 520, y - 2, 36)
            g = ImageDraw.Draw(im)
            g.text((566, y), AIS[who], font=C._font('semi', 31), fill=C.AIS[who][1])
            amt = money_r(prof, race)
            g.text((C.S - 80 - g.textlength(amt, font=C._font('semi', 31)), y), amt, font=C._font('semi', 31), fill=C.UP if prof >= 0 else C.DOWN)
        else:
            g.text((520, y), 'no clear leader', font=C._font('reg', 31), fill=C.MUTED)
        y += 44
    y += 6
    led = f['led']
    g.text((80, y), 'Races led now: ' + ' · '.join(f"{AIS[k]} {led[k]}" for k in sorted(ORDER, key=lambda k: -led[k])), font=C._font('semi', 31), fill=C.FG)
    y += 56
    for lab, m, col in (('BIGGEST WIN THIS WEEK', f['best'], C.UP), ('WORST LOSS THIS WEEK', f['worst'], C.DOWN)):
        if not m:
            continue
        g.text((80, y), lab, font=C._font('semi', 26), fill=C.MUTED)
        y += 36
        line = f"{AIS[m['who']]}: {money_r(float(m['amount']), m.get('race'))} on {what_of(m)} ({RLABEL.get(m.get('race'), m.get('race'))})"
        y = C._wrap(g, line, C._font('med', 31), 80, y, C.S - 160, 40, col, max_lines=2) + 12
    extra = [f"{len(f['leads'])} lead change{'s' if len(f['leads']) != 1 else ''} this week"]
    extra += [f"{AIS[s['id']]}: {s.get('label') or (str(s['n']) + ' games ' + ('won' if s['k'] == 'W' else 'lost') + ' in a row')} in {RLABEL.get(s['race'], 'All in: sports')}" for s in f['streaks'][:2]]   # counted in games (owner, Oct 31)
    for e in extra:
        y = C._wrap(g, e, C._font('med', 30), 80, y, C.S - 160, 38, C.MUTED, max_lines=1) + 4
    return C._finish(im, g, y + 16, path, 'Pretend money, real prices · each race is scored on its own until Nov 28')


def weekly():
    et = NOW.astimezone(ET)
    if not FORCE and (et.weekday() != 6 or not (16 * 60 + 55 <= et.hour * 60 + et.minute <= 18 * 60 + 20)):
        print('outside the Sunday 4:55-6:20 p.m. ET window:', et.strftime('%a %H:%M'))
        return
    if NOW >= RACE_END:
        print('the race is over: the final result is posted instead')
        return
    f = week_facts()
    if not any(w for _, w, _ in f['leaders']):
        print('no standings to recap')
        return
    photo = weekly_card(f, '/tmp/weekly.png')
    span = f["from"].astimezone(ET).strftime('%b %-d') + ' – ' + et.strftime('%b %-d')
    tg = [f"📅 <b>Week {f['n']} recap</b> · {span}", '<i>Each race is scored on its own; nothing is added up until Nov 28.</i>', '', '<b>Who leads each race</b>']
    for race, who, prof in f['leaders']:
        tg.append(f"• {RLABEL[race]}: " + (f"{AIS[who]} {money_r(prof, race)}" if who else 'no clear leader'))
    tg += ['', 'Races led now: ' + ' · '.join(f"{AIS[k]} {f['led'][k]}" for k in sorted(ORDER, key=lambda k: -f['led'][k]))]
    if f['best']:
        m = f['best']; tg.append(f"🏆 Biggest win: {AIS[m['who']]} {money_r(float(m['amount']), m.get('race'))} on {_html.escape(what_of(m))}")
    if f['worst']:
        m = f['worst']; tg.append(f"📉 Worst loss: {AIS[m['who']]} {money_r(float(m['amount']), m.get('race'))} on {_html.escape(what_of(m))}")
    tg.append(f"🏁 {len(f['leads'])} lead changes this week")
    for s in f['streaks'][:3]:
        tg.append(f"{'🔥' if s['k'] == 'W' else '🧊'} {AIS[s['id']]}: {s.get('label') or (str(s['n']) + ' games ' + ('won' if s['k'] == 'W' else 'lost') + ' in a row')} ({RLABEL.get(s['race'], 'All in: sports')})")
    tg += ['', f'{SITE} · Pretend money, not advice.']
    led = f['led']
    xl = [f"📅 Week {f['n']} recap · {span}", 'Races led: ' + ' · '.join(f"{AIS[k]} {led[k]}" for k in sorted(ORDER, key=lambda k: -led[k]))]
    if f['best']:
        xl.append(f"Biggest win: {AIS[f['best']['who']]} {money_r(float(f['best']['amount']), f['best'].get('race'))}")
    if f['worst']:
        xl.append(f"Worst loss: {AIS[f['worst']['who']]} {money_r(float(f['worst']['amount']), f['worst'].get('race'))}")
    xl.append(f"{len(f['leads'])} lead changes")
    import xpost
    x_text = xpost.fit('\n'.join(xl)) if hasattr(xpost, 'fit') else '\n'.join(xl)[:260]
    publish('weekly', '\n'.join(tg), x_text, photo, 'h2h')


# ------------------------------------------------------------------ keeping the records when other runs push the same files
def stash():
    for f in (SENT, XSENT):
        if os.path.exists(f):
            shutil.copy(f, '/tmp/' + os.path.basename(f))


def merge():
    tmp = '/tmp/' + os.path.basename(SENT)
    if os.path.exists(tmp):
        cur = load('daycards_sent.json', {})
        cur.update(json.load(open(tmp)))
        json.dump(cur, open(SENT, 'w'), indent=1)
    tmp = '/tmp/' + os.path.basename(XSENT)
    if os.path.exists(tmp):
        mine = json.load(open(tmp)).get('posts', [])
        cur = load('x_sent.json', {'posts': []})
        have = {(p.get('id'), p.get('key'), p.get('at')) for p in cur.get('posts', [])}
        cur['posts'] = cur.get('posts', []) + [p for p in mine if (p.get('id'), p.get('key'), p.get('at')) not in have]
        cur['posts'].sort(key=lambda p: p.get('at', ''))
        json.dump(cur, open(XSENT, 'w'), indent=1)


if __name__ == '__main__':
    {'slate': slate, 'preview': preview, 'weekly': weekly, 'stash': stash, 'merge': merge}[sys.argv[1]]()
