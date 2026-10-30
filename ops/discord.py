"""Mirror every Telegram post to a Discord channel through a webhook (owner's choice, Oct 30).

Does nothing until the GitHub secret DISCORD_WEBHOOK_URL is set, and never raises: a Discord problem
must never stop a check-in or a Telegram post. The Telegram text is HTML; Discord wants Markdown, so
it is converted here.
"""
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

URL = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
UA = 'PaperTradesBot (https://papertrades.ai, 1.0)'   # Discord rejects requests with no User-Agent


def to_md(text):
    t = text or ''
    t = re.sub(r'<a\s+href="([^"]+)"\s*>(.*?)</a>', lambda m: m.group(2) if m.group(2).strip() == m.group(1).strip() else f'[{m.group(2)}]({m.group(1)})', t, flags=re.S | re.I)
    for tag, md in (('b', '**'), ('strong', '**'), ('i', '*'), ('em', '*'), ('u', '__'), ('s', '~~'), ('code', '`')):
        t = re.sub(rf'</?{tag}>', md, t, flags=re.I)
    t = re.sub(r'<pre>(.*?)</pre>', lambda m: '```\n' + m.group(1) + '\n```', t, flags=re.S | re.I)
    t = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: '\n'.join('> ' + x for x in m.group(1).split('\n')), t, flags=re.S | re.I)
    t = re.sub(r'<tg-spoiler>(.*?)</tg-spoiler>', r'||\1||', t, flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', '', t)
    return html.unescape(t).strip()


def post(text, photo=None):
    """Send one message (with an optional PNG). Returns True when Discord accepted it."""
    if not URL:
        return False
    try:
        content = to_md(text)
        if len(content) > 1990:
            content = content[:1985].rstrip() + ' …'
        payload = json.dumps({'content': content, 'allowed_mentions': {'parse': []}, 'flags': 4})   # 4 = no link previews
        if photo and os.path.exists(photo):
            b = '----ptdc' + str(os.getpid())
            body = (f'--{b}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n{payload}\r\n'.encode()
                    + f'--{b}\r\nContent-Disposition: form-data; name="files[0]"; filename="chart.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                    + open(photo, 'rb').read() + f'\r\n--{b}--\r\n'.encode())
            req = urllib.request.Request(URL + '?wait=true', body, {'Content-Type': f'multipart/form-data; boundary={b}', 'User-Agent': UA})
        else:
            req = urllib.request.Request(URL + '?wait=true', payload.encode(), {'Content-Type': 'application/json', 'User-Agent': UA})
        for attempt in (1, 2):
            try:
                urllib.request.urlopen(req, timeout=20).read()
                time.sleep(0.5)   # stay under Discord's webhook limit (5 posts per 2 seconds)
                return True
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 1:   # rate limited: wait as asked, then try once more
                    try:
                        wait = float(json.loads(e.read()).get('retry_after', 2))
                    except Exception:
                        wait = 2
                    time.sleep(min(wait, 10) + 0.2)
                    continue
                raise
        return False
    except Exception as e:
        print('discord failed', str(e)[:160])
        return False
