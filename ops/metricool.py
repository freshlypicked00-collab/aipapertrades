"""YouTube Shorts through Metricool (owner, Oct 31). Metricool's YouTube connection is already approved by Google, so its uploads are
public (our own unaudited API project would be locked private; all three AIs flagged that, Oct 30).

  python3 ops/metricool.py probe   -> checks the token and the YouTube connection, saves the API's own YouTube fields (posts nothing)
  python3 ops/metricool.py test    -> the safety test (owner approved, Oct 31): uploads an existing Short as UNLISTED (not on the
                                      channel, no notification) and waits for YouTube to confirm, so we know uploads are not locked private
  python3 ops/metricool.py daily   -> the daily Short, posted on its own like Discord (owner, Oct 31: "upload shorts on your own"):
                                      race replays, PUBLIC, three a day at most (never two within 3 hours), a different race each time; recorded in
                                      ops/src/youtube.json so a rerun never posts twice

The token comes only from the METRICOOL_TOKEN secret and is never printed or written anywhere. The account and brand numbers are not
secret (they are in the address bar of every Metricool page)."""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = 'https://app.metricool.com/api'
USER_ID = '6076994'
BLOG_ID = '7772098'          # the "Paper Trades" brand
TOKEN = os.environ.get('METRICOOL_TOKEN', '').strip()
HERE = os.path.dirname(os.path.abspath(__file__))


def call(path, method='GET', body=None, blog=True, raw=False, accept='application/json'):
    """One API call. Never prints the address (it carries the token)."""
    q = {'userId': USER_ID, 'userToken': TOKEN}
    if blog:
        q['blogId'] = BLOG_ID
    url = BASE + path + ('&' if '?' in path else '?') + urllib.parse.urlencode(q)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={'X-Mc-Auth': TOKEN, 'Content-Type': 'application/json', 'Accept': accept})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            txt = r.read().decode('utf-8', 'replace')
            return r.status, (txt if raw else _json(txt))
    except urllib.error.HTTPError as e:
        return e.code, _json(e.read().decode('utf-8', 'replace'))
    except Exception as e:
        return 0, str(e)[:300]


def _json(t):
    try:
        return json.loads(t)
    except Exception:
        return t[:2000]


def _scrub(x):
    """Drop anything token-like before saving."""
    s = json.dumps(x)
    if TOKEN:
        s = s.replace(TOKEN, '[token]')
    return json.loads(s)


def probe():
    out = {}
    if not TOKEN:
        print('METRICOOL_TOKEN secret is missing'); sys.exit(1)
    st, prof = call('/admin/simpleProfiles', blog=False)
    out['profiles_status'] = st
    if st == 200 and isinstance(prof, list):
        out['brands'] = [{k: p.get(k) for k in ('id', 'label', 'title', 'youtube', 'youtubeName', 'youtubeChannelName', 'timezone') if k in p} | {'networks': sorted(k for k, v in p.items() if v and isinstance(v, str) and k in ('youtube', 'instagram', 'facebook', 'twitter', 'tiktok', 'linkedin', 'threads', 'bluesky', 'pinterest'))} for p in prof]
        out['brand_keys'] = sorted(prof[0].keys()) if prof else []
    else:
        out['profiles'] = prof if isinstance(prof, (dict, str)) else str(prof)[:500]
    st2, conn = call(f'/v2/settings/brands/{BLOG_ID}/connections')
    out['connections_status'] = st2; out['connections'] = conn if isinstance(conn, (dict, list)) else str(conn)[:800]
    # the API's own description of a scheduled post, to read YouTube's fields from Metricool itself
    for p in ('/v3/api-docs', '/v2/api-docs', '/swagger.json', '/openapi.json', '/v3/api-docs/scheduler'):
        s, doc = call(p, blog=False)
        if s == 200 and isinstance(doc, dict):
            schemas = (doc.get('components') or {}).get('schemas') or doc.get('definitions') or {}
            keep = {k: v for k, v in schemas.items() if 'youtube' in k.lower() or k.lower() in ('schedulerpost', 'postrequest', 'scheduledpost', 'providerstatus', 'publicationdate')}
            if not keep:
                keep = {k: v for k, v in schemas.items() if 'youtube' in json.dumps(v).lower()}
            out['schema_from'] = p; out['schemas'] = keep
            out['youtube_paths'] = [k for k in (doc.get('paths') or {}) if 'youtube' in k.lower() or 'normalize' in k.lower() or 'scheduler/posts' in k.lower()]
            break
        out.setdefault('schema_tries', []).append([p, s])
    path = os.path.join(HERE, 'review', 'metricool-probe.json')
    json.dump(_scrub(out), open(path, 'w'), indent=1)
    print(json.dumps({k: v for k, v in _scrub(out).items() if k not in ('schemas',)}, indent=1)[:4000])
    print('schemas saved:', list((out.get('schemas') or {}).keys())[:40])


def normalize(url):
    """Metricool copies the file to its own storage; the post must use the address it returns."""
    st, r = call('/actions/normalize/image/url?' + urllib.parse.urlencode({'url': url}), raw=True, accept='*/*')   # it answers in plain text
    if st != 200:
        return None, f'normalize {st}: {str(r)[:300]}'
    r = r.strip()
    try:
        j = json.loads(r)
        r = j if isinstance(j, str) else (j.get('url') or (j.get('data') or {}).get('url') or j.get('mediaId') or j.get('id') or '')
    except Exception:
        r = r.strip('"')
    return (r or None), ('' if r else 'normalize returned nothing')


def schedule_short(video_url, title, text, privacy, when=None, thumb=None, cover_ms=None, yt_type='short'):
    """Schedule one YouTube Short (or, with yt_type='video', a regular video). Returns (status, response)."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    tz = 'America/Toronto'
    at = when or (datetime.now(ZoneInfo(tz)) + timedelta(minutes=3))
    media, err = normalize(video_url)
    if not media:
        return 0, err
    body = {
        'text': text, 'providers': [{'network': 'youtube'}],
        'publicationDate': {'dateTime': at.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': tz},
        'draft': False, 'autoPublish': True, 'media': [media],
        'youtubeData': {'title': title[:100], 'type': yt_type, 'privacy': privacy, 'madeForKids': False, 'category': 'SCIENCE_TECHNOLOGY',
                        'notifySubscribers': privacy == 'public', 'tags': ['AI', 'Claude', 'Gemini', 'ChatGPT', 'paper trading']},
    }
    if thumb:   # the bold cover as the Short's thumbnail (owner, Nov 3: "make sure u add the right thumbnail EVERYTIME")
        # Nov 3: the raw papertrades.ai address was accepted but not used, so the picture goes through Metricool's own storage
        # first (like the video), as a JPEG; cover_ms also points YouTube's frame picker at the cover when the video starts with it
        tn, terr = normalize(thumb)
        print('thumbnail for Metricool:', tn or terr)
        extra = {'videoThumbnailUrl': tn or thumb}
        if cover_ms is not None:
            extra['videoCoverMilliseconds'] = int(cover_ms)
        st, r = call('/v2/scheduler/posts', 'POST', {**body, **extra})
        if st in (200, 201):
            d = r.get('data', r) if isinstance(r, dict) else {}
            print('Metricool kept the thumbnail:', bool(d.get('videoThumbnailUrl')), str(d.get('videoThumbnailUrl'))[:120], 'cover ms', d.get('videoCoverMilliseconds'))
            return st, r
        print('thumbnail refused, posting without it:', str(_scrub(r))[:200])
    return call('/v2/scheduler/posts', 'POST', body)


def wait_for(post_id, minutes=20):
    """Poll until YouTube's answer comes back: PUBLISHED (with its link) or ERROR."""
    import time
    last = None
    for _ in range(minutes * 2):
        st, r = call(f'/v2/scheduler/posts/{post_id}')
        d = r.get('data', r) if isinstance(r, dict) else {}
        prov = [p for p in (d.get('providers') or []) if p.get('network') == 'youtube']
        last = prov[0] if prov else {'status': f'http {st}'}
        print('  status:', last.get('status'), (last.get('detailedStatus') or '')[:160])
        if last.get('status') in ('PUBLISHED', 'ERROR'):
            break
        time.sleep(30)
    return last


def test():
    if not TOKEN:
        print('METRICOOL_TOKEN secret is missing'); sys.exit(1)
    name = 'replay-Options-2026-10-30.mp4'
    tries = ['https://papertrades.ai/social/reels/' + name, 'https://raw.githubusercontent.com/freshlypicked00-collab/aipapertrades/main/social/reels/' + name]
    out = {'video': name, 'privacy': 'unlisted'}
    for u in tries:
        st, r = schedule_short(u, 'Paper Trades test upload (unlisted)', 'Test upload from Paper Trades. https://papertrades.ai', 'unlisted')
        out.setdefault('attempts', []).append({'source': u.split('/')[2], 'status': st, 'answer': _scrub(r) if isinstance(r, (dict, list)) else str(r)[:400]})
        if st in (200, 201) and isinstance(r, dict):
            d = r.get('data', r); pid = d.get('id')
            out['post_id'] = pid
            if pid:
                out['result'] = _scrub(wait_for(pid))
            break
    json.dump(_scrub(out), open(os.path.join(HERE, 'review', 'metricool-test.json'), 'w'), indent=1)
    print(json.dumps(_scrub(out), indent=1)[:3000])


LOG = os.path.join(HERE, 'src', 'youtube.json')
PER_DAY = 3
RACE_START = '2026-10-28'


def _log():
    try:
        return json.load(open(LOG))
    except Exception:
        return {'posts': []}


def _git(*a):
    import subprocess
    return subprocess.run(['git', *a], capture_output=True, text=True)


def _push(msg, paths):
    _git('config', 'user.name', 'paper-trades-bot'); _git('config', 'user.email', 'paper-trades-bot@users.noreply.github.com')
    _git('add', *paths)
    if _git('commit', '-qm', msg).returncode != 0:
        return True
    for _ in range(4):
        _git('pull', '-q', '--rebase', 'origin', 'main')
        if _git('push', '-q', 'origin', 'HEAD:main').returncode == 0:
            return True
    return False


def daily():
    import time
    from datetime import datetime, date
    from zoneinfo import ZoneInfo
    if not TOKEN:
        print('METRICOOL_TOKEN secret is missing'); sys.exit(1)
    NY = ZoneInfo('America/New_York')
    today = datetime.now(NY).date()
    if today > date(2026, 11, 28):
        print('Season 1 is over; nothing to post'); return
    log = _log()
    # three a day (owner: "post more than every day"; all three AIs agreed, Oct 31), never two within three hours, so a rerun or a
    # late schedule never doubles up
    done = [p for p in log['posts'] if p.get('day') == today.isoformat() and p.get('status') != 'ERROR']
    if len(done) >= PER_DAY:
        print(f'already {len(done)} Shorts today'); return
    if log['posts'] and log['posts'][-1].get('at') and log['posts'][-1].get('status') != 'ERROR':
        gap_h = (datetime.now(NY) - datetime.fromisoformat(log['posts'][-1]['at'])).total_seconds() / 3600
        if gap_h < 3:
            print(f'last Short was {gap_h:.1f} h ago; waiting'); return
    sys.path.insert(0, HERE)
    import reel
    d = json.load(open(os.path.join(os.path.dirname(HERE), 'data.json')))
    recent = [p.get('race') for p in log['posts'][-6:]]   # not a race shown in the last six Shorts (two days)
    best, gap = None, -1
    for r in reel.ORDER:   # the race with the widest gap between first and last, not one shown in the last six Shorts
        if r == 'China' or r in recent:
            continue
        sr = reel.series(d, r); last = [x[-1][1] for x in sr.values() if x]
        if len(last) == 3 and max(last) - min(last) > gap:
            best, gap = r, max(last) - min(last)
    race = best or reel.pick_race(d)
    mp4, finals = reel.render(race, os.path.join(os.path.dirname(HERE), 'social', 'reels'), sound=True)
    rel = os.path.relpath(mp4, os.path.dirname(HERE))
    stem = rel[:-4]
    if not _push(f'YouTube Short: {race} race replay ({today})', [rel, stem + '-cover.jpg', stem + '-thumb.jpg']):
        print('could not push the video'); sys.exit(1)
    fin = sorted(finals.items(), key=lambda kv: -kv[1]) if isinstance(finals, dict) else finals
    name = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
    lab = reel.LABEL[race]
    day = (today - date(2026, 10, 28)).days + 1
    money = lambda v: ('+' if v > 0.5 else '−' if v < -0.5 else '') + 'C$' + f'{abs(v):,.0f}'
    title = f'Which AI is winning {lab}? Day {day} | Claude vs Gemini vs ChatGPT'
    tag = {'Stocks': 'Stocks', 'Crypto': 'Crypto', 'China': 'ChinaStocks', 'Metals': 'Gold', 'Energy': 'Oil', 'Options': 'Options', 'Currencies': 'Forex',
           'Safe': 'Investing', 'Sports': 'SportsBetting', 'Predictions': 'PredictionMarkets'}.get(race, 'Trading')   # searchable title hashtag (owner, Nov 1)
    for tags in (f' #AI #{tag}', ' #AI', ''):
        if len(title + tags) <= 100:
            title += tags
            break
    lines = [f'{i + 1}. {name.get(k, k)}: {money(v)}' for i, (k, v) in enumerate(fin)]
    text = (f'Day {day} of 32 in the {lab} race. Three AIs, C$100,000 of pretend money each, real prices, no humans picking trades.\n\n'
            + '\n'.join(lines) + ' (profit in this race so far)\n\n'
            'Every trade and the reason behind it, live and free: papertrades.ai\n'
            'Pretend money only. Not investment or betting advice.\n\n#AI #Claude #ChatGPT #Gemini #Shorts')
    out = {'day': today.isoformat(), 'at': datetime.now(NY).isoformat(timespec='seconds'), 'race': race, 'video': rel, 'title': title, 'standings': {k: v for k, v in fin}}
    # Metricool fetches the video itself, and only papertrades.ai serves it as a video (GitHub's raw files failed, Oct 31): publish
    # the site, wait until the file is really there, then hand it over
    import subprocess
    subprocess.run(['gh', 'workflow', 'run', 'deploy.yml', '--ref', 'main'], capture_output=True)
    url = 'https://papertrades.ai/' + rel
    live = False
    for _ in range(40):   # up to 10 minutes
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=20) as h:
                if h.status == 200 and 'video' in (h.headers.get('Content-Type') or ''):
                    live = True; break
        except Exception:
            pass
        time.sleep(15)
    print('video live on the site:', live)
    st, r = schedule_short(url, title, text, 'public') if live else (0, 'the video never appeared on papertrades.ai')
    if not (st in (200, 201) and isinstance(r, dict)):
        out['status'] = 'ERROR'; out['error'] = str(_scrub(r))[:400]
    else:
        pid = (r.get('data') or r).get('id'); out['post_id'] = pid
        res = wait_for(pid) if pid else {}
        out['status'] = res.get('status'); out['url'] = res.get('publicUrl'); out['detail'] = res.get('detailedStatus')
    log['posts'].append(_scrub(out))
    json.dump(log, open(LOG, 'w'), indent=1)
    _push(f'YouTube Short {out.get("status")}: {race} ({today})', [os.path.relpath(LOG, os.path.dirname(HERE))])
    print(json.dumps(_scrub(out), indent=1))
    if out.get('status') != 'PUBLISHED':
        sys.exit(1)


def story():
    """The daily story Short (owner, Oct 31; standard S1-S10 agreed by all three AIs: ops/review/SOCIAL_STANDARD.md): the day's biggest
    settled bet told for a stranger (ops/story_short.py). One a day (S8). Owner, Oct 31: "approved" - Claude's checks replace the
    owner's preview: every fact comes from the ledger and the render fails if one is missing; frames are kept in the safe zone.
    python3 ops/metricool.py story [RESULT_TX]   (no ID: the biggest result of the last 36 hours not yet posted)"""
    import time
    from datetime import datetime, date, timedelta, timezone
    from zoneinfo import ZoneInfo
    if not TOKEN:
        print('METRICOOL_TOKEN secret is missing'); sys.exit(1)
    NY = ZoneInfo('America/New_York')
    today = datetime.now(NY).date()
    if today > date(2026, 11, 28):
        print('Season 1 is over; nothing to post'); return
    sys.path.insert(0, HERE)
    import story_short as SS
    log = _log()
    want = (sys.argv[2].strip().upper() if len(sys.argv) > 2 and sys.argv[2].strip() else None)
    # two a day (owner, Oct 31: "as many as you and ChatGPT and Gemini feel is good"; Claude and ChatGPT voted 2, Gemini 1:
    # ops/review/shorts-freq-oct31.json), at least 4 hours apart; the variety rule all three agreed on is applied below
    mine = [p for p in log['posts'] if p.get('kind') == 'story' and p.get('status') != 'ERROR']
    if not want and sum(1 for p in mine if p.get('day') == today.isoformat()) >= 2:
        print('already two story Shorts today'); return
    if not want and mine and mine[-1].get('at') and (datetime.now(NY) - datetime.fromisoformat(mine[-1]['at'])).total_seconds() < 4 * 3600:
        print('last story Short was under 4 hours ago; waiting'); return
    root = os.path.dirname(HERE)
    d = json.load(open(os.path.join(root, 'data.json')))
    posted = {t for p in log['posts'] if p.get('status') != 'ERROR' for t in ([p.get('tx')] + list(p.get('txs') or []))}   # a game told once covers all its bets
    since = (datetime.now(timezone.utc) - timedelta(hours=36)).strftime('%Y-%m-%dT%H:%M:%SZ')
    picks = [want] if want else [tx for _, tx in SS.candidates(d, since) if tx not in posted]
    if not want and mine:   # variety (all three AIs): never the same AI, then never the same race, as the last Short when another story exists
        import txids as _TX
        last_ai, last_race = (mine[-1].get('tx') or '?')[:1], _TX.RACE.get(mine[-1].get('race') or '', '?')
        picks = sorted(picks, key=lambda tx: (tx[:1] == last_ai, tx.split('-')[1] == last_race))   # stable: biggest first within each group
    st_, alt = None, None
    game = lambda x: '|'.join(sorted([str(x.get('away')), str(x.get('home'))])) + '|' + str(x.get('day'))
    last_game = mine[-1].get('game') if mine else None   # full pass, Nov 20: two Shorts in a row told the same game with only the AI's
    for tx in picks:                                      # name changed (Nov 17). Another game goes first when there is one.
        try:
            cand = SS.bet_story(tx, d)
        except SS.StoryError as e:
            print('skipped', tx, e); continue
        if not want and last_game and game(cand) == last_game and alt is None:
            alt = cand; print('same game as the last Short; another story goes first if there is one:', tx); continue
        st_ = cand; break
    st_ = st_ or alt
    if not st_:
        print('no story today: no settled bet with a full ledger record'); return
    mp4, title, desc = SS.render(st_, os.path.join(root, 'social', 'stories'))
    rel = os.path.relpath(mp4, root); stem = rel[:-4]
    try:   # the thumbnail as a JPEG too (Metricool and YouTube take JPEGs)
        from PIL import Image
        Image.open(os.path.join(root, stem + '-thumb.png')).convert('RGB').save(os.path.join(root, stem + '-thumb.jpg'), quality=92)
    except Exception as e:
        print('no JPEG thumbnail:', e)
    if not _push(f'YouTube story Short: {st_["res_tx"]} ({today})', [rel, stem + '.json', stem + '-thumb.png', stem + '-thumb.jpg']):
        print('could not push the video'); sys.exit(1)
    out = {'kind': 'story', 'tx': st_['res_tx'], 'txs': st_.get('res_txs') or [st_['res_tx']], 'day': today.isoformat(), 'at': datetime.now(NY).isoformat(timespec='seconds'),
           'race': st_['race'], 'video': rel, 'title': title, 'game': game(st_)}
    import subprocess
    subprocess.run(['gh', 'workflow', 'run', 'deploy.yml', '--ref', 'main'], capture_output=True)
    url = 'https://papertrades.ai/' + rel
    live = False
    for _ in range(40):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=20) as h:
                if h.status == 200 and 'video' in (h.headers.get('Content-Type') or ''):
                    live = True; break
        except Exception:
            pass
        time.sleep(15)
    print('video live on the site:', live)
    st, r = schedule_short(url, title, desc, 'public', thumb='https://papertrades.ai/' + stem + '-thumb.jpg', cover_ms=300) if live else (0, 'the video never appeared on papertrades.ai')
    if not (st in (200, 201) and isinstance(r, dict)):
        out['status'] = 'ERROR'; out['error'] = str(_scrub(r))[:400]
    else:
        pid = (r.get('data') or r).get('id'); out['post_id'] = pid
        res = wait_for(pid) if pid else {}
        out['status'] = res.get('status'); out['url'] = res.get('publicUrl'); out['detail'] = res.get('detailedStatus')
    log['posts'].append(_scrub(out))
    json.dump(log, open(LOG, 'w'), indent=1)
    _push(f'YouTube story Short {out.get("status")}: {st_["res_tx"]} ({today})', [os.path.relpath(LOG, root)])
    if out.get('status') == 'PUBLISHED':
        nini_thumbnail(rel, title, out.get('url'))
    print(json.dumps(_scrub(out), indent=1))
    if out.get('status') != 'PUBLISHED':
        sys.exit(1)


def nini_thumbnail(rel, title, url):
    """Owner, Nov 3: "make sure u add the right thumbnail EVERYTIME". YouTube takes the thumbnail sent with the upload for links and
    search, but the Shorts grid on the channel only shows one uploaded in YouTube Studio, so after every Short NINI gets a Telegram
    task with the picture and three steps (ops/nicole_bot.py sends the picture under the job)."""
    try:
        import subprocess
        from datetime import datetime
        stem = rel[:-4]; root = os.path.dirname(HERE)
        name = f"{datetime.now().strftime('%Y-%m-%d')}-thumb-{os.path.basename(stem)[:40]}.md"
        pic = 'https://papertrades.ai/' + stem + '-thumb.jpg'
        md = (f"## 🖼️ New YouTube Short: its thumbnail\n\n"
              f"### Put the thumbnail on the new Short (2 min)\n"
              f"1. Save the picture that comes after this message (press and hold it → Save).\n"
              f"2. YouTube Studio → **Content** → **Shorts** → open **{title[:70]}**.\n"
              f"3. **Thumbnail** → **Upload file** (or ⋮ → **Change**) → pick the picture → **Save**.\n"
              f"Short: {url or 'the newest Short'}\n"
              f"Picture: {pic}\n")
        open(os.path.join(HERE, 'nicole', name), 'w').write(md)
        if _push('NINI task: thumbnail for ' + os.path.basename(stem), [os.path.join('ops', 'nicole', name)]):
            subprocess.run(['gh', 'workflow', 'run', 'nicole.yml', '--ref', 'main', '-f', 'file=' + name], capture_output=True)
            print('NINI thumbnail task sent:', name)
    except Exception as e:
        print('::warning::NINI thumbnail task not sent:', e)


def custom():
    """Post one finished Short from the repo (owner, Nov 3: the new YouTube-first Shorts): VIDEO=social/yt/<name>.mp4, with its
    title and description from social/yt/<name>.txt and its thumbnail from social/yt/<name>-thumb.png (sent as a JPEG)."""
    import time
    if not TOKEN:
        print('METRICOOL_TOKEN secret is missing'); sys.exit(1)
    rel = os.environ['VIDEO']; stem = rel[:-4]; root = os.path.dirname(HERE)
    from datetime import datetime
    txt = open(os.path.join(root, stem + '.txt')).read()
    title = txt.split('TITLE', 1)[1].split('\n', 2)[1].strip()
    desc = txt.split('DESCRIPTION', 1)[1].split('PINNED COMMENT', 1)[0].strip()
    from PIL import Image
    Image.open(os.path.join(root, stem + '-thumb.png')).convert('RGB').save(os.path.join(root, stem + '-thumb.jpg'), quality=92)
    if not _push(f'YouTube Short thumbnail (JPEG): {os.path.basename(stem)}', [stem + '-thumb.jpg']):
        print('could not push the thumbnail')
    import subprocess
    subprocess.run(['gh', 'workflow', 'run', 'deploy.yml', '--ref', 'main'], capture_output=True)
    url = 'https://papertrades.ai/' + rel; th = 'https://papertrades.ai/' + stem + '-thumb.jpg'
    live = False
    for _ in range(40):
        try:
            ok = [urllib.request.urlopen(urllib.request.Request(u, method='HEAD'), timeout=20).status == 200 for u in (url, th)]
            if all(ok):
                live = True; break
        except Exception:
            pass
        time.sleep(15)
    print('video and thumbnail live on the site:', live)
    if not live:
        sys.exit('not live on papertrades.ai')
    log = json.load(open(LOG)) if os.path.exists(LOG) else {'posts': []}
    if any(p.get('video') == rel and p.get('status') == 'PUBLISHED' for p in log['posts']):
        sys.exit('already posted: ' + rel)
    out = {'kind': 'yt', 'video': rel, 'title': title, 'at': datetime.now().astimezone().isoformat(timespec='seconds'), 'day': datetime.now().date().isoformat()}
    title = title.replace('<', '').replace('>', ''); desc = desc.replace('<', '').replace('>', '→')   # YouTube refuses < and > (Nov 13)
    kind = 'video' if '-wide' in rel else 'short'   # a 16:9 '-wide' file goes up as a regular video (owner, Nov 13: "as a short and a video")
    st, r = schedule_short(url, title, desc, 'public', thumb=th, yt_type=kind)
    if not (st in (200, 201) and isinstance(r, dict)):
        out['status'] = 'ERROR'; out['error'] = str(_scrub(r))[:400]
    else:
        pid = (r.get('data') or r).get('id'); out['post_id'] = pid
        res = wait_for(pid) if pid else {}
        out['status'] = res.get('status'); out['url'] = res.get('publicUrl'); out['detail'] = res.get('detailedStatus')
    log['posts'].append(_scrub(out))
    json.dump(log, open(LOG, 'w'), indent=1)
    _push(f'YouTube Short {out.get("status")}: {os.path.basename(rel)}', [os.path.relpath(LOG, root)])
    if out.get('status') == 'PUBLISHED':
        nini_thumbnail(rel, title, out.get('url'))
    print(json.dumps(_scrub(out), indent=1))
    if out.get('status') != 'PUBLISHED':
        sys.exit(1)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'probe'
    {'probe': probe, 'test': test, 'daily': daily, 'story': story, 'custom': custom}[cmd]()
