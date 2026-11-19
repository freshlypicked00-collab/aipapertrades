"""Find (and, only when told to, delete) exact repeats of an AI's result post on Telegram and in Discord #live-trades.

Why (Nov 19): from Nov 18, 10:14 p.m. ET to Nov 19, 5:14 a.m. ET each hourly Gemini-and-ChatGPT run posted the night's first two
results and was then stopped before saving. Claude first believed the same posts went out about ten times; the dry run of Nov 19 found one
repeat on Telegram (Gemini's Miami Heat win, twice) and none on Discord (ops/src/corrections.json).

DRY RUN by default: it only lists what it would remove. With CONFIRM=delete it keeps the FIRST copy of each repeated post and deletes
the later copies. Only posts from the last HOURS (default 30) that start with an AI's header are looked at. Deleting cannot be undone,
so the owner starts that run himself (.github/workflows/dedupe.yml). Telegram lets a bot delete posts under 48 hours old only.
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DELETE = os.environ.get('CONFIRM') == 'delete'
HOURS = float(os.environ.get('HOURS') or 30)
SINCE = datetime.now(timezone.utc) - timedelta(hours=HOURS)
HEAD = re.compile(r'(GEMINI|CHATGPT|CLAUDE)\W{0,6}\((Google|OpenAI|Anthropic)\)')


def norm(s):
    return ' '.join(re.sub(r'[*_`]', '', s).split())


def repeats(posts):
    """posts: [(id, time, text)] oldest first -> [(text, kept id, [ids to remove])] for texts posted more than once."""
    seen, out = {}, {}
    for pid, at, text in posts:
        if at < SINCE or not HEAD.search(text[:80]):
            continue
        k = norm(text)
        if k in seen:
            out.setdefault(k, (seen[k], []))[1].append(pid)
        else:
            seen[k] = pid
    return [(k, v[0], v[1]) for k, v in out.items()]


def telegram():
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID') or ''
    if not chat.startswith('@'):
        print('Telegram: no public channel name to read; skipped'); return
    posts, before = {}, ''
    for _ in range(12):
        req = urllib.request.Request('https://t.me/s/' + chat.lstrip('@') + (f'?before={before}' if before else ''), headers={'User-Agent': 'Mozilla/5.0'})
        page = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
        found = re.findall(r'data-post="[^"/]+/(\d+)"(.*?)(?=data-post="[^"/]+/|$)', page, re.S)
        if not found:
            break
        for pid, body in found:
            tm = re.search(r'<time[^>]*datetime="([^"]+)"', body)
            txt = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', body, re.S)
            if tm and txt:
                posts[int(pid)] = (datetime.fromisoformat(tm.group(1)), ' '.join(re.sub(r'<[^>]+>', ' ', txt.group(1)).split()))
        lo = min(int(p) for p, _ in found)
        if str(lo) == before or min(v[0] for v in posts.values()) < SINCE:
            break
        before = str(lo)
    rep = repeats([(p, posts[p][0], posts[p][1]) for p in sorted(posts)])
    n = 0
    for text, keep, drop in rep:
        print(f'Telegram: {len(drop) + 1} copies, keep #{keep}, remove {drop}: {text[:110]}')
        for pid in drop if DELETE and tok else []:
            try:
                urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/deleteMessage', urllib.parse.urlencode({'chat_id': chat, 'message_id': pid}).encode(), timeout=20).read(); n += 1
            except Exception as e:
                print('  could not delete', pid, str(e)[:120])
    print(f'::notice title=Telegram::{len(posts)} posts read; {sum(len(d) for _, _, d in rep)} repeats of {len(rep)} posts; {n} deleted' + ('' if DELETE else ' (dry run)'))


def discord():
    import discord_bot as B
    ch = (B.load_map().get('channels') or {}).get('live-trades')
    if not (B.TOKEN and ch):
        print('Discord: no bot token or #live-trades channel; skipped'); return
    msgs, before = [], ''
    for _ in range(6):
        page = B.call('GET', f'/channels/{ch}/messages?limit=100' + (f'&before={before}' if before else '')) or []
        if not page:
            break
        msgs += page; before = page[-1]['id']
        if datetime.fromisoformat(page[-1]['timestamp']) < SINCE:
            break
    rep = repeats([(m['id'], datetime.fromisoformat(m['timestamp']), m.get('content') or '') for m in sorted(msgs, key=lambda m: int(m['id']))])
    n = 0
    for text, keep, drop in rep:
        print(f'Discord: {len(drop) + 1} copies, keep {keep}, remove {len(drop)}: {text[:110]}')
        for mid in drop if DELETE else []:
            try:
                B.call('DELETE', f'/channels/{ch}/messages/{mid}'); n += 1
            except Exception as e:
                print('  could not delete', mid, str(e)[:120])
    print(f'::notice title=Discord::{len(msgs)} posts read; {sum(len(d) for _, _, d in rep)} repeats of {len(rep)} posts; {n} deleted' + ('' if DELETE else ' (dry run)'))


if __name__ == '__main__':
    for f in (telegram, discord):
        try:
            f()
        except Exception as e:
            print(f'{f.__name__} failed: {str(e)[:200]}')
