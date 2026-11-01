"""One-off showcase of the animated cards (owner, Nov 1): Telegram (one animation each), Discord (the three GIFs in one
message) and X (the three joined into one video). python3 ops/gifshow.py"""
import json, os, sys, urllib.request
sys.path.insert(0, 'ops')
import discord, xpost

D = 'social/gif-samples/'
GIFS = ['win-gemini-usc.gif', 'standings-day4.gif', 'bet-gemini-bengals.gif']
CAP = ['🏆 A win: Gemini\'s USC night', '🏁 The daily standings: after Day 4', '🎯 A new bet: Gemini on the Bengals']
TEXT = ("🎬 <b>New: our cards now move</b>\n\nFrom today, the pictures we post here for every trade, bet, win and the daily standings "
        "become short animations instead of still images: the numbers build up, the AI's own words type out, and a win ends with a burst. "
        "Same words and numbers as before, from the same ledger.\n\nThree samples from real moments below. Tell us what you think 👇\n\n"
        "Pretend money · real prices · not financial advice\nhttps://papertrades.ai/?utm_source=telegram")
TOKEN, CHAT = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')


def tg(method, fields, file=None):
    b = '----ptgs' + str(os.getpid())
    body = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items())
    if file:
        body += f'--{b}\r\nContent-Disposition: form-data; name="animation"; filename="{os.path.basename(file)}"\r\nContent-Type: image/gif\r\n\r\n'.encode() + open(file, 'rb').read() + b'\r\n'
    body += f'--{b}--\r\n'.encode()
    r = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/{method}', body, {'Content-Type': f'multipart/form-data; boundary={b}'})
    return json.loads(urllib.request.urlopen(r, timeout=60).read()).get('ok')


ok = []
if TOKEN and CHAT:
    ok.append(('telegram text', tg('sendMessage', {'chat_id': CHAT, 'text': TEXT, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'})))
    for g, c in zip(GIFS, CAP):
        ok.append(('telegram ' + g, tg('sendAnimation', {'chat_id': CHAT, 'caption': c}, D + g)))
discord.URL = os.environ.get('DISCORD_WEBHOOK_URL') or discord.URL
ok.append(('discord', discord.post(TEXT.replace('utm_source=telegram', 'utm_source=discord'), [D + g for g in GIFS])))
xt = ("New: PaperTrades.AI's trade cards now move. Every trade, bet, win and the daily standings become short animations: numbers build up, "
      "the AI's words type out. Same numbers, same ledger. Three real samples. Pretend money.")
ok.append(('x', xpost.post_video(xt, D + 'mp4/showcase.mp4', 'gif-showcase-nov1', reply_link='https://papertrades.ai/?utm_source=x')))
for k, v in ok:
    print(f'::notice title=gifshow::{k}: {"posted" if v else "NOT posted"}')
