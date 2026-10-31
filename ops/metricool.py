"""YouTube Shorts through Metricool (owner, Oct 31). Metricool's YouTube connection is already approved by Google, so its uploads are
public (our own unaudited API project would be locked private; all three AIs flagged that, Oct 30).

  python3 ops/metricool.py probe   -> checks the token and the YouTube connection, saves the API's own YouTube fields (posts nothing)
  python3 ops/metricool.py test    -> the safety test (owner approved, Oct 31): uploads an existing Short as UNLISTED (not on the
                                      channel, no notification) and waits for YouTube to confirm, so we know uploads are not locked private

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


def call(path, method='GET', body=None, blog=True, raw=False):
    """One API call. Never prints the address (it carries the token)."""
    q = {'userId': USER_ID, 'userToken': TOKEN}
    if blog:
        q['blogId'] = BLOG_ID
    url = BASE + path + ('&' if '?' in path else '?') + urllib.parse.urlencode(q)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={'X-Mc-Auth': TOKEN, 'Content-Type': 'application/json', 'Accept': 'application/json'})
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
    st, r = call('/actions/normalize/image/url?' + urllib.parse.urlencode({'url': url}), raw=True)
    if st != 200:
        return None, f'normalize {st}: {str(r)[:300]}'
    r = r.strip()
    try:
        j = json.loads(r)
        r = j if isinstance(j, str) else (j.get('url') or (j.get('data') or {}).get('url') or j.get('mediaId') or j.get('id') or '')
    except Exception:
        r = r.strip('"')
    return (r or None), ('' if r else 'normalize returned nothing')


def schedule_short(video_url, title, text, privacy, when=None):
    """Schedule one YouTube Short. Returns (status, response)."""
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
        'youtubeData': {'title': title[:100], 'type': 'short', 'privacy': privacy, 'madeForKids': False, 'category': '28',
                        'notifySubscribers': privacy == 'public', 'tags': ['AI', 'Claude', 'Gemini', 'ChatGPT', 'paper trading']},
    }
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


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'probe'
    {'probe': probe, 'test': test}[cmd]()
