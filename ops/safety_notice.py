"""Safety notice on Telegram and Discord (B4 of the safety banner; all three AIs agreed Nov 1; owner said yes Nov 2).
Telegram: post it, pin it (quietly, no second alert) and put the short version at the top of the channel description.
Discord: post it to #live-trades (a webhook can't pin or edit the channel topic: the owner does those by hand).
Runs once: the log in ops/notices/sent.json keeps it from posting twice."""
import json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discord  # noqa: E402

NAME = 'safety-notice-b4'
TEXT = ('🔒 <b>Safety notice</b>\n'
        'PaperTrades.AI never takes deposits and will never message you asking for money, your password or personal information '
        '(optional tips are only on our Support page). We are not associated with any similarly named site or app.\n\n'
        'Official accounts: https://papertrades.ai/#official')
SHORT = '🔒 We never take deposits or ask for money, passwords or personal info. Not associated with any similarly named site or app.'
tok, chat = os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']


def tg(method, **p):
    try:
        r = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/{method}', urllib.parse.urlencode(p).encode(), timeout=30))
    except urllib.error.HTTPError as e:
        r = json.loads(e.read().decode() or '{}')
    if not r.get('ok'): print(f'::warning title={method}::{str(r)[:300]}')
    return r.get('result') if r.get('ok') else None


log = 'ops/notices/sent.json'; sent = json.load(open(log)) if os.path.exists(log) else []
if NAME in sent: print('already posted'); sys.exit(0)
m = tg('sendMessage', chat_id=chat, text=TEXT, parse_mode='HTML', disable_web_page_preview='true')
if not m: sys.exit(1)
pinned = tg('pinChatMessage', chat_id=chat, message_id=m['message_id'], disable_notification='true')
info = tg('getChat', chat_id=chat) or {}
old = (info.get('description') or '').strip()
print('Old description:', repr(old))
if '🔒' not in old:
    new = SHORT + ('\n\n' + old if old else '')
    if len(new) > 255: new = SHORT + '\n\n' + old[:255 - len(SHORT) - 3].rsplit(' ', 1)[0] + '…'
    ok = tg('setChatDescription', chat_id=chat, description=new)
    print('New description:', repr(new), 'set' if ok is not None else 'NOT set')
print('pinned' if pinned else 'NOT pinned (the bot needs the "Pin messages" admin right)')
d = discord.post(TEXT)
print('Discord posted' if d else 'Discord not posted')
sent.append(NAME); json.dump(sent, open(log, 'w'), indent=1)
