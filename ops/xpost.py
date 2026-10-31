"""Post to X (@papertradesai) through the official X API (owner, Oct 30: "I can pay, I can afford funding to grow the project").

Pay-per-use API (docs.x.com pricing, Oct 2026): about US$0.015 a post, but US$0.20 for a post that contains a link, so
posts here NEVER contain a link (papertrades.ai is in the bio and printed on every picture). Pictures are uploaded first.

Does nothing until these four GitHub secrets are set (keys from the X Developer Console, app permission "Read and write"):
  X_API_KEY, X_API_SECRET (consumer keys) and X_ACCESS_TOKEN, X_ACCESS_SECRET (the @papertradesai user's access token).
Never raises: an X problem must never stop a check-in. Guards: no links in the main post (a page link goes in the first reply), at most 280 characters, at most DAILY_CAP posts
per rolling 24 hours (recorded in ops/src/x_sent.json, committed with each run), the same text never twice.
"""
import base64, hashlib, hmac, html, json, os, re, secrets, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

KEYS = [os.environ.get(k, '').strip() for k in ('X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_SECRET')]
ON = all(KEYS)
API = 'https://api.x.com'
SENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'x_sent.json')
DAILY_CAP = 24      # posts per rolling 24 hours, link replies included (owner, Oct 30: funding is not an issue, post links until we grow)
LIMIT = 270   # X counts an emoji as two characters: a little room to spare


def _q(s):
    return urllib.parse.quote(str(s), safe='~')


def _auth(method, url, params=None):
    """OAuth 1.0a (HMAC-SHA1) header for the @papertradesai user. params: query or form fields that are part of the signature
    (JSON and multipart bodies are not)."""
    ck, cs, tk, ts = KEYS
    oa = {'oauth_consumer_key': ck, 'oauth_nonce': secrets.token_hex(16), 'oauth_signature_method': 'HMAC-SHA1',
          'oauth_timestamp': str(int(time.time())), 'oauth_token': tk, 'oauth_version': '1.0'}
    allp = {**(params or {}), **oa}
    base = '&'.join([method.upper(), _q(url), _q('&'.join(f'{_q(k)}={_q(v)}' for k, v in sorted(allp.items())))])
    sig = base64.b64encode(hmac.new(f'{_q(cs)}&{_q(ts)}'.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oa['oauth_signature'] = sig
    return 'OAuth ' + ', '.join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(oa.items()))


def _req(method, url, body=None, ctype=None):
    base, _, qs = url.partition('?')   # query parameters are part of the OAuth signature
    h = {'Authorization': _auth(method, base, dict(urllib.parse.parse_qsl(qs)) if qs else None), 'User-Agent': 'PaperTradesBot/1.0'}
    if ctype:
        h['Content-Type'] = ctype
    with urllib.request.urlopen(urllib.request.Request(url, body, h, method=method), timeout=60) as r:
        t = r.read()
        return json.loads(t) if t else {}


def plain(text):
    """Telegram-style HTML or Markdown to plain text for X, with every link removed (a link makes a post cost 13x)."""
    t = re.sub(r'<a\s+href="[^"]+"\s*>(.*?)</a>', r'\1', text or '', flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)                     # markdown links
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'\b(www\.)?papertrades\.ai\b', 'PaperTrades', t, flags=re.I)  # a bare domain is turned into a link by X
    t = re.sub(r'[ \t]+\n', '\n', t).replace('**', '').strip()
    t = '\n'.join(re.sub(r'[\s·|,-]+$', '', ln) for ln in t.split('\n'))   # no dangling separators where a link was
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


def fit(text, tail=''):
    """At most 280 characters: whole lines first, then a clean cut."""
    t = plain(text)
    room = LIMIT - len(tail)
    if len(t) > room:
        lines, out = t.split('\n'), ''
        for ln in lines:
            if len(out) + len(ln) + 1 > room - 1:
                break
            out += ('\n' if out else '') + ln
        t = (out or t[:room - 1]).rstrip() + ('…' if not out else '')
    return t + tail


def _load():
    try:
        return json.load(open(SENT))
    except Exception:
        return {'posts': []}


def upload(photo):
    """Upload a PNG or JPEG; returns its media id (X API v2 media upload, one request for an image)."""
    data = open(photo, 'rb').read()
    b = '----ptx' + secrets.token_hex(8)
    mt = 'image/png' if photo.lower().endswith('.png') else 'image/jpeg'
    body = (f'--{b}\r\nContent-Disposition: form-data; name="media_category"\r\n\r\ntweet_image\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="media_type"\r\n\r\n{mt}\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="media"; filename="card"\r\nContent-Type: {mt}\r\n\r\n').encode() + data + f'\r\n--{b}--\r\n'.encode()
    j = _req('POST', API + '/2/media/upload', body, f'multipart/form-data; boundary={b}')
    return str((j.get('data') or {}).get('id') or j.get('media_id_string') or '')


def upload_video(path, chunk=4 * 1024 * 1024):
    """Chunked video upload (X API v2: initialize, append, finalize, then wait for processing). Returns the media id."""
    size = os.path.getsize(path)
    j = _req('POST', API + '/2/media/upload/initialize', json.dumps({'media_type': 'video/mp4', 'total_bytes': size, 'media_category': 'tweet_video'}).encode(), 'application/json')
    mid = str((j.get('data') or {}).get('id') or '')
    if not mid:
        raise RuntimeError('no media id: ' + json.dumps(j)[:200])
    with open(path, 'rb') as f:
        i = 0
        while True:
            part = f.read(chunk)
            if not part:
                break
            b = '----ptx' + secrets.token_hex(8)
            body = (f'--{b}\r\nContent-Disposition: form-data; name="segment_index"\r\n\r\n{i}\r\n'
                    f'--{b}\r\nContent-Disposition: form-data; name="media"; filename="part"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + part + f'\r\n--{b}--\r\n'.encode()
            _req('POST', f'{API}/2/media/upload/{mid}/append', body, f'multipart/form-data; boundary={b}')
            i += 1
    j = _req('POST', f'{API}/2/media/upload/{mid}/finalize')
    info = (j.get('data') or {}).get('processing_info') or {}
    for _ in range(60):   # X processes the video before it can be posted
        if not info or info.get('state') == 'succeeded':
            return mid
        if info.get('state') == 'failed':
            raise RuntimeError('X could not process the video: ' + json.dumps(info)[:200])
        time.sleep(max(2, int(info.get('check_after_secs') or 5)))
        j = _req('GET', f'{API}/2/media/upload?command=STATUS&media_id={mid}')
        info = (j.get('data') or {}).get('processing_info') or {}
    raise RuntimeError('video still processing after several minutes')


def post_video(text, path, key, reply_link=None):
    """One post with a video (owner, Oct 30: the Season 1 trailer). reply_link: a first reply carrying the link, so the
    main post has none (posts with links get less reach; the one reply with a link costs about US$0.20)."""
    if not ON:
        print('X keys not set'); return False
    st = _load()
    if any(p.get('key') == key for p in st['posts']):
        print('already posted:', key); return False
    try:
        mid = upload_video(path)
        body = fit(text)
        j = _req('POST', API + '/2/tweets', json.dumps({'text': body, 'media': {'media_ids': [mid]}}).encode(), 'application/json')
        pid = (j.get('data') or {}).get('id')
        now = datetime.now(timezone.utc)
        st['posts'].append({'at': now.isoformat(timespec='seconds'), 'id': pid, 'key': key, 'text': body})
        if reply_link and pid:
            r = _req('POST', API + '/2/tweets', json.dumps({'text': reply_link, 'reply': {'in_reply_to_tweet_id': pid}}).encode(), 'application/json')
            st['posts'].append({'at': now.isoformat(timespec='seconds'), 'id': (r.get('data') or {}).get('id'), 'key': key + '-link', 'text': reply_link})
        json.dump(st, open(SENT, 'w'), indent=1)
        print('::notice::posted the video to X', pid)
        return True
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode()[:400]
        except Exception:
            msg = ''
        print(f'::error::X video post failed: HTTP {e.code} {msg}')
        return False


def post(text, photo=None, key=None, reply_link=None):
    """One post (with an optional picture). key: a stable id so the same thing is never posted twice. True when posted.
    reply_link: the page it points to, posted as the first reply (the main post stays link-free for reach and says 'Link in reply';
    owner, Oct 30, and all three AIs agreed: ops/review/growth-r1-oct30.json). Plain papertrades.ai links with ?utm_source=x, no shorteners."""
    if not ON:
        return False
    try:
        st = _load()
        now = datetime.now(timezone.utc)
        recent = [p for p in st['posts'] if now - datetime.fromisoformat(p['at']) < timedelta(hours=24)]
        body = fit(text, '\n👇 Link in reply' if reply_link else '')
        if not body:
            return False
        if key and any(p.get('key') == key for p in st['posts']):
            return False
        if any(p.get('text') == body for p in recent):
            return False
        if len(recent) >= DAILY_CAP:
            print(f'::notice::X: daily cap reached ({DAILY_CAP} in 24 hours); not posted')
            return False
        payload = {'text': body}
        if photo and os.path.exists(photo):
            try:
                mid = upload(photo)
                if mid:
                    payload['media'] = {'media_ids': [mid]}
            except Exception as e:
                print('::warning::X picture upload failed, posting the text alone:', str(e)[:200])
        j = _req('POST', API + '/2/tweets', json.dumps(payload).encode(), 'application/json')
        pid = (j.get('data') or {}).get('id')
        st['posts'] = [p for p in st['posts'] if now - datetime.fromisoformat(p['at']) < timedelta(days=7)]
        st['posts'].append({'at': now.isoformat(timespec='seconds'), 'id': pid, 'key': key, 'text': body})
        if reply_link and pid:   # the link in the first reply (about US$0.20); a failed reply never undoes the post
            try:
                r = _req('POST', API + '/2/tweets', json.dumps({'text': reply_link, 'reply': {'in_reply_to_tweet_id': pid}}).encode(), 'application/json')
                st['posts'].append({'at': now.isoformat(timespec='seconds'), 'id': (r.get('data') or {}).get('id'), 'key': (key or '') + '-link', 'text': reply_link})
            except Exception as e:
                print('::warning::X link reply failed:', str(e)[:200])
        json.dump(st, open(SENT, 'w'), indent=1)
        print('::notice::posted to X', pid)
        return True
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode()[:300]
        except Exception:
            msg = ''
        print(f'::warning::X post failed: HTTP {e.code} {msg}')
        return False
    except Exception as e:
        print('::warning::X post failed:', str(e)[:200])
        return False


if __name__ == '__main__':   # python3 ops/xpost.py check  -> who the keys belong to (reads 1 user: about US$0.01)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        if not ON:
            print('X keys not set'); sys.exit(0)
        try:
            print(json.dumps(_req('GET', API + '/2/users/me'))[:300])
        except urllib.error.HTTPError as e:
            body = ''
            try:
                body = e.read().decode('utf-8', 'replace')[:300]
            except Exception:
                pass
            k = KEYS
            # key shapes only (lengths and the access token's user-id prefix), never the keys themselves
            print('X check failed:', e.code, body, '| key lengths:', [len(x) for x in k], '| token user id:', k[2].split('-')[0] if '-' in k[2] else 'no dash')
        except Exception as e:
            print('X check failed:', str(e)[:300])
