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


def send(text, photo=None):
    if not (TOKEN and CHAT):
        print('--- (no Telegram secrets; would send' + (f' with {photo}' if photo else '') + ') ---\n' + text)
        return
    if photo and len(text) <= 1000:
        b = '----pt' + str(os.getpid())
        parts = []
        for k, v in (('chat_id', CHAT), ('caption', text), ('parse_mode', 'HTML')):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="c.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(photo, 'rb').read() + f'\r\n--{b}--\r\n'.encode())
        req = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/sendPhoto', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={b}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        return
    if photo:
        send('📊', photo)
    data = urllib.parse.urlencode({'chat_id': CHAT, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data, timeout=20) as r:
        r.read()


HIST = load('ops/src/history.json')
BG, FG, MUTED, LINE, UP, DOWN, AMBER = '#0b0b0a', '#f2e9d8', '#9b927f', '#2b2923', '#3ddc84', '#ff5a4e', '#ffb000'


def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'text.parse_math': False, 'font.size': 11, 'text.color': FG, 'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED})
    return plt


def chart_section(pf, n):
    """One image, three panels: last 24 hours, last 7 days, since start, for one experiment."""
    try:
        plt = _plt()
        import matplotlib.dates as md
        pts = sorted((datetime.fromisoformat(h['at']), h['value']) for h in HIST if h['portfolio'] == pf)
        if len(pts) < 2:
            return None
        now, start = pts[-1][0], 100000
        sym = 'US$' if pf == 'China' else 'C$'
        fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), facecolor=BG)
        for ax, (title, span) in zip(axes, (('24 hours', timedelta(hours=24)), ('7 days', timedelta(days=7)), ('Since start', None))):
            sel = [p for p in pts if span is None or p[0] >= now - span]
            before = [p for p in pts if span is not None and p[0] < now - span]
            if before:
                sel = [before[-1]] + sel
            if len(sel) < 2:
                sel = pts
            xs, ys = [p[0] for p in sel], [p[1] for p in sel]
            col = UP if ys[-1] >= ys[0] else DOWN
            ax.set_facecolor(BG)
            ax.plot(xs, ys, color=col, lw=2.2)
            ax.fill_between(xs, ys, min(ys + [start]) , color=col, alpha=.12)
            ax.axhline(start, color=MUTED, lw=.8, ls='--')
            ch = ys[-1] - ys[0]
            ax.set_title(f"{title}   {'+' if ch >= 0 else '−'}{sym}{abs(ch):,.0f}", color=col, fontsize=12, loc='left')
            rng = max(ys + [start]) - min(ys + [start])
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _, r=rng: f'{v/1000:,.1f}k' if r < 5000 else f'{v/1000:,.0f}k'))
            ax.yaxis.set_major_locator(plt.MaxNLocator(5))
            loc = md.AutoDateLocator(maxticks=5)
            ax.xaxis.set_major_locator(loc)
            ax.xaxis.set_major_formatter(md.ConciseDateFormatter(loc))
            for sp in ax.spines.values():
                sp.set_color(LINE)
            ax.grid(color=LINE, lw=.6)
        fig.suptitle(f"PAPER TRADES · {LABEL.get(pf, pf)} · value {sym}{pts[-1][1]:,.0f} (started {sym}100,000)", color=AMBER, fontsize=13, x=.01, ha='left', fontweight='bold')
        fig.text(.99, .01, 'Simulation only · papertrades.ai', color=MUTED, ha='right', fontsize=9)
        fig.tight_layout(rect=(0, .03, 1, .94))
        path = f'/tmp/pt_{pf}_{n}.png'
        fig.savefig(path, dpi=110, facecolor=BG)
        plt.close(fig)
        return path
    except Exception as e:
        print('chart failed', e)
        return None


def chart_scoreboard(rows, title):
    """Daily close image: each experiment's % since start, and % for the day."""
    try:
        plt = _plt()
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), facecolor=BG)
        for ax, key, head in ((axes[0], 'day', 'Today'), (axes[1], 'total', 'Since start')):
            rs = sorted(rows, key=lambda r: r[key])
            ax.set_facecolor(BG)
            vals = [r[key] * 100 for r in rs]
            ax.barh([LABEL.get(r['pf'], r['pf']) for r in rs], vals, color=[UP if v >= 0 else DOWN for v in vals])
            for i, v in enumerate(vals):
                ax.text(v, i, f' {v:+.1f}% ' , va='center', ha='left' if v >= 0 else 'right', color=FG, fontsize=10)
            ax.axvline(0, color=MUTED, lw=.8)
            ax.set_title(head, color=AMBER, loc='left', fontsize=13)
            lim = max(1, max(abs(v) for v in vals)) * 1.35
            ax.set_xlim(-lim, lim)
            ax.set_xticks([])
            for sp in ax.spines.values():
                sp.set_visible(False)
        fig.suptitle('PAPER TRADES · ' + title, color=AMBER, fontsize=14, x=.01, ha='left', fontweight='bold')
        fig.text(.99, .01, 'Ten separate experiments, never added together · Simulation only · papertrades.ai', color=MUTED, ha='right', fontsize=9)
        fig.tight_layout(rect=(0, .03, 1, .93))
        path = '/tmp/pt_close.png'
        fig.savefig(path, dpi=110, facecolor=BG)
        plt.close(fig)
        return path
    except Exception as e:
        print('chart failed', e)
        return None


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
    msgs.append((f"{ICON.get(a, '•')} <b>{esc(LABEL.get(pf, pf))}: {a} {esc(h)}</b>\n{price}\n{when(t['at'])}" + (f"\n<i>{esc(why[:400])}</i>" if why else ''), pf))

# bets placed and settled
oldb = {b['bet']: b for b in load(S + 'bets.json', BEFORE)}
for b in load(S + 'bets.json'):
    o = oldb.get(b['bet'])
    odds = ('+' if float(b['odds']) > 0 else '') + str(b['odds'])
    if o is None:
        msgs.append((f"🎯 <b>Sports: new bet {b['bet']}</b>\n{esc(b['pick'])} ({esc(b['event'])}) at {odds}, stake C${b['stake_cad']:,.0f} to win C${b['to_win_cad']:,.0f}", 'Sports'))
    elif o['status'] == 'Open' and b['status'] != 'Open':
        icon = {'Won': '✅', 'Lost': '❌', 'Push': '➖'}.get(b['status'], '🏁')
        msgs.append((f"{icon} <b>Sports: {b['bet']} {b['status'].lower()}</b>\n{esc(b['pick'])} ({esc(b['event'])}): {money(b['result_cad'] or 0, 'Sports')}", 'Sports'))

# prediction markets settled (a sale at 1.00 or 0.00)
for t in load(S + 'trades.json'):
    if t['portfolio'] == 'Predictions' and t['action'] == 'Sell' and t['price_usd'] in (0, 1) and json.dumps(t, sort_keys=True) not in old:
        msgs.append((f"🏁 <b>Prediction market settled: {esc(t['holding'])}</b>\n{'Won, paid US$1 a share' if t['price_usd'] == 1 else 'Lost, shares expired worthless'}", 'Predictions'))

# the AI's take
oldt = {x['at'] for x in load(S + 'take.json', BEFORE)}
for x in load(S + 'take.json'):
    if x['at'] not in oldt:
        msgs.append((f"💬 <b>The AI's take</b>\n“{esc(x['text'])}”", None))

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
    srows = []
    for r in rows:
        vals = [h['value'] for h in HIST if h['portfolio'] == r['portfolio']]
        srows.append({'pf': r['portfolio'], 'day': r['pct'] or 0, 'total': (vals[-1] / 100000 - 1) if vals else 0})
    msgs.append(('\n'.join(lines), ('close', srows, f"Day {n} close")))

for i, (m, pic) in enumerate(msgs):
    photo = chart_scoreboard(pic[1], pic[2]) if isinstance(pic, tuple) else chart_section(pic, i) if pic else None
    send(m + ('' if SITE in m else f'\n{SITE}'), photo)
print(f'{len(msgs)} message(s)')
