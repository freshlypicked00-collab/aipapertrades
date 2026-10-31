"""YouTube Shorts through Metricool (owner, Oct 31). Metricool's YouTube connection is already approved by Google, so its uploads are
public (our own unaudited API project would be locked private; all three AIs flagged that, Oct 30).

  python3 ops/metricool.py probe   -> checks the token and the YouTube connection, saves the API's own YouTube fields (posts nothing)

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


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'probe'
    {'probe': probe}[cmd]()
