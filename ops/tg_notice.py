"""Post a correction or notice to the Telegram channel, loud (with a push notification), from a text file in ops/notices.

Usage (in a workflow, with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID): python3 ops/tg_notice.py ops/notices/<file>.txt
A file is posted once: its name is recorded in ops/notices/sent.json, and a second run does nothing.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discord  # noqa: E402

path = sys.argv[1]
name = os.path.basename(path)
log = os.path.join(os.path.dirname(os.path.abspath(path)), 'sent.json')
sent = json.load(open(log)) if os.path.exists(log) else []
if name in sent:
    print('already posted:', name); sys.exit(0)
text = open(path).read().strip()
tok, chat = os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
data = urllib.parse.urlencode({'chat_id': chat, 'text': text[:4000], 'parse_mode': 'HTML', 'disable_web_page_preview': 'true', 'disable_notification': 'false'}).encode()
r = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data, timeout=30))
if not r.get('ok'):
    print('::error::Telegram refused the notice:', str(r)[:300]); sys.exit(1)
discord.post(text)   # the same notice on Discord (does nothing until DISCORD_WEBHOOK_URL is set)
sent.append(name)
json.dump(sent, open(log, 'w'), indent=1)
print('::notice::posted ' + name)
