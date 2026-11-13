"""Post one finished video to X and the Telegram channel, once each (owner, Nov 13: "make a video commercial for the discord
channel, upload it on IG, TELE, YOUTUBE, and X"; YouTube and the Instagram Reel were already up). Reads ops/video_post.json.
Never posts the same key twice (X: ops/src/x_sent.json; Telegram: ops/src/tg_video_sent.json)."""
import json
import os
import sys
import uuid
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SENT = os.path.join(HERE, 'src', 'tg_video_sent.json')


def telegram(n):
    sent = json.load(open(SENT)) if os.path.exists(SENT) else {}
    if n['key'] in sent:
        print('telegram: already posted'); return True
    tok, chat = os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    f = os.path.join(ROOT, n['file'])
    b = uuid.uuid4().hex
    parts = []
    for k, v in (('chat_id', chat), ('caption', n['telegram']), ('parse_mode', 'HTML'), ('supports_streaming', 'true'), ('width', '1080'), ('height', '1920')):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="video"; filename="{os.path.basename(f)}"\r\nContent-Type: video/mp4\r\n\r\n'.encode() + open(f, 'rb').read() + b'\r\n')
    body = b''.join(parts) + f'--{b}--\r\n'.encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendVideo', data=body, headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    ok = bool(r.get('ok'))
    if ok:
        sent[n['key']] = {'message_id': r['result']['message_id']}; json.dump(sent, open(SENT, 'w'), indent=1)
    print('telegram:', 'posted' if ok else r)
    return ok


def x(n):
    import xpost
    ok = xpost.post_video(n['x'], os.path.join(ROOT, n['file']), n['key'], reply_link=n.get('x_link'))
    print('x:', 'posted' if ok else 'not posted')
    return ok


if __name__ == '__main__':
    n = json.load(open(os.path.join(HERE, 'video_post.json')))
    res = {}
    for name, fn in (('telegram', telegram), ('x', x)):
        try:
            res[name] = fn(n)
        except Exception as e:
            print(f'::warning::{name}: {str(e)[:300]}'); res[name] = False
    print('::notice title=Video post::' + json.dumps(res))
    sys.exit(0 if all(res.values()) else 1)
