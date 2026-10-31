"""Post to X (@papertradesai) through the official X API (owner, Oct 30: "I can pay, I can afford funding to grow the project").

Pay-per-use API (docs.x.com pricing, Oct 2026): about US$0.015 a post, but US$0.20 for a post that contains a link, so
posts here NEVER contain a link (papertrades.ai is in the bio and printed on every picture). Pictures are uploaded first.

Does nothing until these four GitHub secrets are set (keys from the X Developer Console, app permission "Read and write"):
  X_API_KEY, X_API_SECRET (consumer keys) and X_ACCESS_TOKEN, X_ACCESS_SECRET (the @papertradesai user's access token).
Never raises: an X problem must never stop a check-in. Guards: no links, at most 280 characters, at most DAILY_CAP posts
per rolling 24 hours (recorded in ops/src/x_sent.json, committed with each run), the same text never twice.
"""
import base64, hashlib, hmac, html, json, os, re, secrets, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

KEYS = [os.environ.get(k, '').strip() for k in ('X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_SECRET')]
ON = all(KEYS)
API = 'https://api.x.com'
SENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'x_sent.json')
DAILY_CAP = 12      # posts per rolling 24 hours (about US$0.18 a day at the plain-post price)
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
    h = {'Authorization': _auth(method, url), 'User-Agent': 'PaperTradesBot/1.0'}
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


def post(text, photo=None, key=None):
    """One post (with an optional picture). key: a stable id so the same thing is never posted twice. True when posted."""
    if not ON:
        return False
    try:
        st = _load()
        now = datetime.now(timezone.utc)
        recent = [p for p in st['posts'] if now - datetime.fromisoformat(p['at']) < timedelta(hours=24)]
        body = fit(text)
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
        except Exception as e:
            print('X check failed:', str(e)[:300])
