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

URL = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()                # #live-trades: everything Telegram gets
DAILY = os.environ.get('DISCORD_WEBHOOK_DAILY', '').strip()           # #daily-results: the race card after each daily close
LEADS = os.environ.get('DISCORD_WEBHOOK_LEADS', '').strip()           # #lead-changes: each time an AI takes the lead in a race
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


STAT = {'sent': 0, 'failed': 0, 'error': ''}   # this run's Discord results (rivals.py saves them in rivals.json 'discord', so a failure is visible)


def post(text, photo=None, url=None):
    """Send one message (with an optional PNG, or a list of PNGs sent together as one gallery, up to 10) to #live-trades,
    or to the webhook given. Returns True when Discord accepted it.
    An album (cover + one card per move) must be passed as the whole list: the cover says "Swipe for each move", so it is
    never posted alone (owner, Oct 30, after a cover went out on its own)."""
    URL = (url if url is not None else globals()['URL']) or ''
    if not URL:
        return False
    try:
        content = to_md(text)
        if len(content) > 1990:
            content = content[:1985].rstrip() + ' …'
        payload = json.dumps({'content': content, 'allowed_mentions': {'parse': []}, 'flags': 4})   # 4 = no link previews
        photos = [p for p in (photo if isinstance(photo, (list, tuple)) else [photo]) if p and os.path.exists(p)][:10]
        if photos:
            b = '----ptdc' + str(os.getpid())
            body = f'--{b}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n{payload}\r\n'.encode()
            for i, p in enumerate(photos):
                body += (f'--{b}\r\nContent-Disposition: form-data; name="files[{i}]"; filename="{i + 1:02d}.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                         + open(p, 'rb').read() + b'\r\n')
            body += f'--{b}--\r\n'.encode()
            req = urllib.request.Request(URL + '?wait=true', body, {'Content-Type': f'multipart/form-data; boundary={b}', 'User-Agent': UA})
        else:
            req = urllib.request.Request(URL + '?wait=true', payload.encode(), {'Content-Type': 'application/json', 'User-Agent': UA})
        for attempt in (1, 2):
            try:
                urllib.request.urlopen(req, timeout=20).read()
                time.sleep(0.5)   # stay under Discord's webhook limit (5 posts per 2 seconds)
                STAT['sent'] += 1
                return True
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 1:   # rate limited: wait as asked, then try once more
                    try:
                        wait = float(json.loads(e.read()).get('retry_after', 2))
                    except Exception:
                        wait = 2
                    time.sleep(min(wait, 10) + 0.2)
                    continue
                try:   # keep Discord's own reason (e.g. 'Unknown Webhook', 'Request entity too large')
                    detail = e.read().decode('utf-8', 'replace')[:200]
                except Exception:
                    detail = ''
                raise RuntimeError(f'HTTP {e.code} {detail}'.strip())
        return False
    except Exception as e:
        STAT['failed'] += 1
        STAT['error'] = str(e)[:200]
        print('discord failed', str(e)[:200])
        return False
