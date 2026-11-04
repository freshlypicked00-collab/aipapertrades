"""Put the PaperTrades.AI logo on the accounts the code can reach (owner, Nov 4: "use this logo everywhere going forward").
- Discord: each webhook (#live-trades, #daily-results, #lead-changes) gets the name PaperTrades.AI and the logo as its picture.
- Telegram: the channel photo (the channel bot is an admin).
Instagram, X, YouTube, TikTok, the Discord server icon and the bots' own pictures can only be changed by hand (Nini's task)."""
import base64, json, os, urllib.request, uuid

LOGO = 'brand/logo-512.png'
UA = 'PaperTradesBot (https://papertrades.ai, 1.0)'
png = open(LOGO, 'rb').read()

for name in ('DISCORD_WEBHOOK_URL', 'DISCORD_WEBHOOK_DAILY', 'DISCORD_WEBHOOK_LEADS'):
    url = os.environ.get(name, '').strip().split('?')[0]
    if not url: print(f'{name}: not set'); continue
    body = json.dumps({'name': 'PaperTrades.AI', 'avatar': 'data:image/png;base64,' + base64.b64encode(png).decode()}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=body, method='PATCH', headers={'Content-Type': 'application/json', 'User-Agent': UA}), timeout=30)
        print(f'::notice title=Discord {name}::picture and name updated ({r.status})')
    except urllib.error.HTTPError as e:
        print(f'::warning title=Discord {name}::{e.code} {e.read().decode(errors="replace")[:200]}')

tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip(), os.environ.get('TELEGRAM_CHAT_ID', '').strip()
if tok and chat:
    b = uuid.uuid4().hex
    data = (f'--{b}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat}\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="logo.png"\r\nContent-Type: image/png\r\n\r\n').encode() + png + f'\r\n--{b}--\r\n'.encode()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{tok}/setChatPhoto', data=data, headers={'Content-Type': f'multipart/form-data; boundary={b}'}), timeout=60))
        print(f'::notice title=Telegram channel photo::{r}')
    except urllib.error.HTTPError as e:
        print(f'::warning title=Telegram channel photo::{e.code} {e.read().decode(errors="replace")[:200]}')
