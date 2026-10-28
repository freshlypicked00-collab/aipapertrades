"""Post new Paper Trades activity to a Telegram channel.

Run by GitHub Actions after each push (see .github/workflows/telegram.yml). Compares the data
files in this commit with the previous commit and posts: new trades, new bets, settled bets,
a new "AI's take", and each newly closed ledger day (results, scoreboard, report card grades).
Needs the secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID; does nothing without them.
"""
import json, os, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

TOKEN, CHAT = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
BEFORE = os.environ.get('BEFORE_SHA') or 'HEAD^'
SITE = 'https://papertrades.ai'
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports', 'Predictions': 'Prediction markets'}
ICON = {'Buy': '🟢', 'Sell': '🔴', 'Short': '🔻', 'Cover': '🔺'}
ET = timezone(timedelta(hours=-4))  # good enough for labels; UTC is shown too


def load(path, ref=None):
    try:
        raw = subprocess.check_output(['git', 'show', f'{ref}:{path}'], stderr=subprocess.DEVNULL) if ref else open(path, 'rb').read()
        return json.loads(raw)
    except Exception:
        return []


def when(s):
    t = datetime.fromisoformat(s.replace('Z', '+00:00'))
    u = t.astimezone(timezone.utc)
    return t.strftime('%b %-d, %-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' ET (' + u.strftime('%H:%M UTC') + ')'


def money(v, pf):
    sym = 'US$' if pf == 'China' else 'C$'
    return ('+' if v >= 0 else '−') + sym + f'{abs(v):,.0f}'


def send(text):
    if not (TOKEN and CHAT):
        print('--- (no Telegram secrets; would send) ---\n' + text)
        return
    data = urllib.parse.urlencode({'chat_id': CHAT, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data, timeout=20) as r:
        r.read()


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


S = 'ops/src/'
msgs = []
if os.environ.get('TEST'):
    send('✅ Test: the Paper Trades bot is live. Every trade, bet and daily close will be posted here.\n' + SITE)
    sys.exit(0)

# trades
old = {json.dumps(t, sort_keys=True) for t in load(S + 'trades.json', BEFORE)}
log = load(S + 'log.json')
for t in load(S + 'trades.json'):
    if json.dumps(t, sort_keys=True) in old:
        continue
    pf, h, a = t['portfolio'], t['holding'], t['action']
    if pf == 'China':
        price = f"¥{t['price_local']:,.3f} per share, ¥{t['cny']:,.0f}"
    elif pf == 'Predictions':
        price = f"{t['price_usd'] * 100:.1f}¢ per share, C${t['cad']:,.0f}"
    elif h == 'Japanese yen':
        price = f"USD/JPY {1 / t['price_usd']:.2f}, C${t['cad']:,.0f}"
    else:
        price = f"US${t['price_usd']:,.2f}, C${t['cad']:,.0f}"
    why = next((e['detail'] for e in reversed(log) if e['portfolio'] == pf and e['at'][:16] == t['at'][:16]), '')
    msgs.append(f"{ICON.get(a, '•')} <b>{esc(LABEL.get(pf, pf))}: {a} {esc(h)}</b>\n{price}\n{when(t['at'])}" + (f"\n<i>{esc(why[:400])}</i>" if why else ''))

# bets placed and settled
oldb = {b['bet']: b for b in load(S + 'bets.json', BEFORE)}
for b in load(S + 'bets.json'):
    o = oldb.get(b['bet'])
    odds = ('+' if float(b['odds']) > 0 else '') + str(b['odds'])
    if o is None:
        msgs.append(f"🎯 <b>Sports: new bet {b['bet']}</b>\n{esc(b['pick'])} ({esc(b['event'])}) at {odds}, stake C${b['stake_cad']:,.0f} to win C${b['to_win_cad']:,.0f}")
    elif o['status'] == 'Open' and b['status'] != 'Open':
        icon = {'Won': '✅', 'Lost': '❌', 'Push': '➖'}.get(b['status'], '🏁')
        msgs.append(f"{icon} <b>Sports: {b['bet']} {b['status'].lower()}</b>\n{esc(b['pick'])} ({esc(b['event'])}): {money(b['result_cad'] or 0, 'Sports')}")

# prediction markets settled (a sale at 1.00 or 0.00)
for t in load(S + 'trades.json'):
    if t['portfolio'] == 'Predictions' and t['action'] == 'Sell' and t['price_usd'] in (0, 1) and json.dumps(t, sort_keys=True) not in old:
        msgs.append(f"🏁 <b>Prediction market settled: {esc(t['holding'])}</b>\n{'Won, paid US$1 a share' if t['price_usd'] == 1 else 'Lost, shares expired worthless'}")

# the AI's take
oldt = {x['at'] for x in load(S + 'take.json', BEFORE)}
for x in load(S + 'take.json'):
    if x['at'] not in oldt:
        msgs.append(f"💬 <b>The AI's take</b>\n“{esc(x['text'])}”")

# closed ledger days
oldd = {r['day'] for r in load(S + 'ledger.json', BEFORE)}
ledger = load(S + 'ledger.json')
review = load(S + 'review.json')
for day in sorted({r['day'] for r in ledger} - oldd):
    rows = [r for r in ledger if r['day'] == day and r['portfolio'] != 'All']
    n = (datetime.fromisoformat(day) - datetime(2026, 10, 26)).days + 1
    lines = [f"📒 <b>Day {n} closed: {datetime.fromisoformat(day).strftime('%a %b %-d')}</b> (00:00 UTC)"]
    for r in sorted(rows, key=lambda r: -(r['pct'] or 0)):
        lines.append(f"{'🟩' if r['pnl'] > 0.5 else '🟥' if r['pnl'] < -0.5 else '⬜'} {esc(LABEL.get(r['portfolio'], r['portfolio']))}: {money(r['pnl'], r['portfolio'])} ({r['pct'] * 100:+.1f}%)")
    if review:
        latest = max(x['at'] for x in review)
        grades = [f"{LABEL.get(x['portfolio'], x['portfolio'])} {x['grade']}" for x in review if x['at'] == latest and x['portfolio'] != 'All' and x.get('grade') not in (None, '—')]
        if grades:
            lines.append('\n<b>Report card:</b> ' + esc(', '.join(grades)))
    lines.append(f"\nEach experiment is separate and never added together. Simulation only, not investment or betting advice.\n{SITE}")
    msgs.append('\n'.join(lines))

for m in msgs:
    send(m + ('' if SITE in m else f'\n{SITE}'))
print(f'{len(msgs)} message(s)')
