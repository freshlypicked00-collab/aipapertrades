"""Post new Paper Trades activity to a Telegram channel.

Run by GitHub Actions after each push (see .github/workflows/telegram.yml). Compares the data
files in this commit with the previous commit and posts: new trades, new bets, settled bets,
a new "AI's take", and each newly closed ledger day (results, scoreboard, report card grades).
Needs the secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID; does nothing without them.
"""
import json, os, subprocess, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgcharts  # noqa: E402
import sharecard  # noqa: E402
import discord  # noqa: E402
from datetime import datetime, timezone, timedelta

TOKEN, CHAT = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
BEFORE = os.environ.get('BEFORE_SHA') or 'HEAD^'
SITE = 'https://papertrades.ai'
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports', 'Predictions': 'Prediction markets'}
ICON = {'Buy': '🟢', 'Sell': '🔴', 'Short': '🔻', 'Cover': '🔺'}
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo('America/New_York')   # EDT until Nov 1, EST after
except Exception:
    ET = timezone(timedelta(hours=-5))


def load(path, ref=None):
    try:
        raw = subprocess.check_output(['git', 'show', f'{ref}:{path}'], stderr=subprocess.DEVNULL) if ref else open(path, 'rb').read()
        return json.loads(raw)
    except Exception:
        return []


def when(s):
    t = datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(ET)   # always shown in New York time, whatever offset it was written with
    u = t.astimezone(timezone.utc)
    hk = t.astimezone(timezone(timedelta(hours=8)))
    return (t.strftime('%b %-d, %-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' ET (' + u.strftime('%H:%M UTC') + ' · '
            + (hk.strftime('%b %-d, ') if hk.date() != t.date() else '') + hk.strftime('%-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' HKT)')


def money(v, pf):
    sym = 'US$' if pf == 'China' else 'C$'
    return ('+' if v >= 0 else '−') + sym + f'{abs(v):,.0f}'


def send(text, photo=None, silent=False, _dc=True):
    if _dc:
        discord.post(text, photo)   # same post on Discord (does nothing until DISCORD_WEBHOOK_URL is set)
    if not (TOKEN and CHAT):
        print('--- (no Telegram secrets; would send' + (f' with {photo}' if photo else '') + ') ---\n' + text)
        return
    if photo and len(text) <= 1000:
        b = '----pt' + str(os.getpid())
        parts = []
        for k, v in (('chat_id', CHAT), ('caption', text), ('parse_mode', 'HTML'), ('disable_notification', 'true' if silent else 'false')):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="c.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(photo, 'rb').read() + f'\r\n--{b}--\r\n'.encode())
        req = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/sendPhoto', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={b}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())['result']['message_id']
    if photo:
        send(f'<b>PAPER TRADES</b> · {SITE}', photo, silent, _dc=False)
    data = urllib.parse.urlencode({'chat_id': CHAT, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true', 'disable_notification': 'true' if silent else 'false'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data, timeout=20) as r:
        return json.loads(r.read())['result']['message_id']


HIST = load('ops/src/history.json')
# Claude's trades in the shape sharecard.buy_in() reads (for the average entry on sells): China counts shares; elsewhere each buy is
# weighted by its C$ cost / price (proportional to the quantity bought; Claude's trades.json has no quantity field)
CLAUDE_TRADES = [{'at': x['at'], 'model': 'claude', 'experiment': x['portfolio'], 'action': x['action'], 'symbol': tgcharts.symbol_for(x['portfolio'], x['holding'], x.get('code')),
                  'price': x.get('price_local') or x.get('price_usd'), 'qty': x.get('shares') or ((x.get('cad') or 0) / (x.get('price_usd') or 1) if x.get('price_usd') else None)}
                 for x in load('ops/src/trades.json')]
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


def chart_scoreboard(rows, title, single=None):
    """Daily close image: each experiment's % since start, and % for the day."""
    try:
        plt = _plt()
        fig, axes = plt.subplots(1, 1 if single else 2, figsize=(9 if single else 12, 5.2), facecolor=BG)
        panels = [(axes, 'total', single)] if single else [(axes[0], 'day', 'Last 24 hours' if WELCOME else 'Today'), (axes[1], 'total', 'Since start')]
        for ax, key, head in panels:
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
        fig.text(.99, .01, ('Archived first run · ' if single else 'Ten separate experiments · ') + 'Simulation only · papertrades.ai', color=MUTED, ha='right', fontsize=9)
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
TEST = os.environ.get('TEST') == '1'
WELCOME = os.environ.get('MODE') == 'welcome'
ANNOUNCE = os.environ.get('MODE') == 'announce'
NOTE = os.environ.get('MODE') == 'note'
SOURCES = load(S + 'sources.json')


def source_for(pf, holding):
    tagged = [x for x in SOURCES if pf in x.get('portfolios', [])]
    words = [w.lower() for w in holding.split() if len(w) > 2]
    best = next((x for x in tagged if any(w in x['title'].lower() for w in words)), tagged[0] if tagged else None)
    return f"\nSource: <a href=\"{esc(best['url'])}\">{esc(best['title'])}</a>" if best else ''


if os.environ.get('MODE') == 'poll':
    # A native, anonymous Telegram poll pinned at the top: who wins on Nov 28? The welcome stays pinned underneath.
    api = lambda method, **kw: json.loads(urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/{method}', urllib.parse.urlencode(kw).encode(), timeout=20).read())['result']
    chat = api('getChat', chat_id=CHAT)
    welcome = (chat.get('pinned_message') or {}).get('message_id')
    print(f'::notice title=welcome::{welcome}')
    poll = api('sendPoll', chat_id=CHAT, question='🏁 Who wins Paper Trades on Nov 28?',
               options=json.dumps(['🟠 Claude (Anthropic)', '🔵 Gemini (Google)', '⚪ ChatGPT (OpenAI)']), is_anonymous='true', disable_notification='true')
    api('pinChatMessage', chat_id=CHAT, message_id=poll['message_id'], disable_notification='true')
    print(f"::notice title=poll::{poll['message_id']}")
    sys.exit(0)

if os.environ.get('MODE') == 'cleanup':
    # Remove chatter from the channel (takes, per-AI daily closes, catch-ups). Trades, sells, bets, results,
    # the pinned welcome and rule notices stay. Reads the public web view of the channel; bots can delete posts under 48 hours old.
    import re as _re
    DROP = ("current take", "Day 1 closed", "Day 0 closed", "closed: ", "catch-up", "Catch-up")
    posts, before = {}, ''
    for _ in range(10):
        req = urllib.request.Request('https://t.me/s/' + CHAT.lstrip('@') + (f'?before={before}' if before else ''), headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36', 'Accept-Language': 'en'})
        page = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
        found = _re.findall(r'data-post="[^"/]+/(\d+)"(.*?)(?=data-post="[^"/]+/|$)', page, _re.S | _re.I)
        if not found:
            print(f'::notice title=reader::page {len(page)} chars, {page.count("data-post")} data-post, title ' + (_re.search(r'<title>(.*?)</title>', page, _re.S).group(1)[:80] if '<title>' in page else '-'))
        if not found:
            break
        for pid, body in found:
            txt = _re.sub(r'<[^>]+>', ' ', body)
            posts[int(pid)] = ' '.join(txt.split())[:400]
        lo = min(int(p) for p, _ in found)
        if str(lo) == before:
            break
        before = str(lo)
    gone = 0
    kept_ids = []
    for pid in sorted(posts):
        t = posts[pid]
        if any(k in t for k in DROP) and 'NEW RULE' not in t and 'RESET' not in t.upper()[:40]:
            try:
                r = urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/deleteMessage', urllib.parse.urlencode({'chat_id': CHAT, 'message_id': pid}).encode(), timeout=20).read()
                gone += 1
                print('deleted', pid, t[:90])
            except Exception as e:
                print('could not delete', pid, e)
        else:
            print('kept', pid, t[:90])
            kept_ids.append(f'{pid}: {t[:60]}')
    print(gone, 'deleted of', len(posts))
    print(f'::notice title=cleanup::{gone} deleted of {len(posts)} posts read')
    for k in range(0, len(kept_ids), 12):
        print('::notice title=kept::' + ' | '.join(kept_ids[k:k + 12]).replace('%', '%25'))
    sys.exit(0)

if NOTE:
    send(open('ops/note.txt').read().strip())
    sys.exit(0)

if ANNOUNCE:
    rows = [{'pf': p, 'day': v, 'total': v} for p, v in (('Stocks', .0641), ('Crypto', .0136), ('China', .0055), ('Currencies', -.0004), ('Metals', -.0051))]
    send(open('ops/announce.txt').read().strip() + f'\n{SITE}', chart_scoreboard(rows, "Claude's first run, final (Oct 26-28)", single='Return since start'))
    sys.exit(0)

EDIT_PIN = os.environ.get('MODE') == 'editwelcome'
if WELCOME or EDIT_PIN:
    pass
if EDIT_PIN:
    WELCOME = True
if WELCOME:
    last = {}
    for h in HIST:
        last[h['portfolio']] = h['value']
    order = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
    board = sorted(((pf, last.get(pf, 100000)) for pf in order), key=lambda x: -x[1])
    day = (datetime.now(timezone.utc) - datetime(2026, 10, 28, tzinfo=timezone.utc)).days + 1
    intro = ("👋 <b>Welcome to Paper Trades: AI vs AI</b>\n\n"
             "Three AI models trade <b>head to head</b>, tested <b>publicly, in front of the world, in real time</b>, with pretend money and real-world prices from Oct 28 to Nov 28, 2026. "
             "Each model runs its <b>own separate copy</b> of each experiment, starting from the same 100,000 at the same moment, "
             "and they are scored against each other. The overall winner is the AI with the most total profit on Nov 28.\n\n"
             "🟠 <b>Claude</b> (Anthropic): all ten experiments\n"
             "🔵 <b>Gemini</b> (Google): all ten experiments\n"
             "⚪ <b>ChatGPT</b> (OpenAI): all ten experiments\n\n"
             "<b>Trading:</b> Stocks and anything · Crypto · China stocks · Metals · Oil and energy · Options · Currencies · Play it safe\n"
             "<b>Betting:</b> Sports · Prediction markets\n\n"
             "🔁 <b>Restart:</b> after a morning tuning run, every experiment of every AI restarted at 100,000 on Oct 28, 1:45 p.m. ET (China stocks at the Shanghai open), so all three start level.\n\n"
             "📏 <b>Rules:</b> invest as if it were real money and play to finish #1 · at most 50% in one holding, 25% on one bet, 4× currency leverage · lose a whole experiment: BUSTED · lose C$100,000 in total: ELIMINATED\n\n"
             "<b>How it works</b>\n"
             "• All three AIs check in at the same times (hourly, every 30 minutes in US market hours, and at the US and Shanghai opens and closes), search the news themselves, and explain every trade in their own words\n"
             "• Every model writes its own daily report card and grades itself\n"
             "• Every post here starts with who made it: 🟠 CLAUDE, 🔵 GEMINI or ⚪ CHATGPT\n\n"
             "<b>What you'll see here</b>\n"
             "🟢🔴 every buy and sell, live, with a price chart · 🎯 every bet and result · 🚀📉 market alerts when Bitcoin, stocks, gold, oil or the dollar make a big move · "
             "🏁 one race update a day at 00:00 UTC (8 p.m. ET until Nov 1, 7 p.m. ET after). Takes, plans and report cards are on the website.\n\n"
             "🔴 Simulation only. No real money. Not investment or betting advice.\n\n"
             f"Compare them live on the AI vs AI tab, and switch models on the site: {SITE}")
    if EDIT_PIN and TOKEN and CHAT:
        try:
            chat = json.loads(urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/getChat?chat_id={urllib.parse.quote(CHAT)}', timeout=20).read())['result']
            pin = chat.get('pinned_message') or {}
            try:   # the welcome's id is saved once a poll is pinned above it
                pin = {'message_id': json.load(open('ops/tg_ids.json'))['welcome']}
            except Exception:
                pass
            data = urllib.parse.urlencode({'chat_id': CHAT, 'message_id': pin['message_id'], 'text': intro, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'}).encode()
            urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/editMessageText', data, timeout=20).read()
            print('edited pinned message', pin['message_id'])
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as e:
            print('could not edit the pinned message, posting a new one:', e)
    mid = send(intro, 'og.png' if os.path.exists('og.png') else None)
    lines = [f"🏁 <b>Where things stand: day {day} of 32</b> (Claude's experiments)\n"]
    for i, (pf, v) in enumerate(board, 1):
        sym = 'US$' if pf == 'China' else 'C$'
        ch = v - 100000
        lines.append(f"{i}. {'🟩' if ch > 0.5 else '🟥' if ch < -0.5 else '⬜'} {esc(LABEL[pf])}: {sym}{v:,.0f} ({'+' if ch >= 0 else '−'}{abs(ch) / 1000:.1f}%)")
    lines.append(f"\nEach started at 100,000. {SITE}")
    now = datetime.now(timezone.utc)
    def ago(pf):
        pts = [h for h in HIST if h['portfolio'] == pf and datetime.fromisoformat(h['at']) <= now - timedelta(hours=24)]
        return pts[-1]['value'] if pts else 100000
    rows = [{'pf': pf, 'day': v / ago(pf) - 1, 'total': v / 100000 - 1} for pf, v in board]
    send('\n'.join(lines), chart_scoreboard(rows, f'Day {day} standings'))
    tk = [x for x in load(S + 'take.json') if not x.get('experiment')]
    if tk:
        send(f"🟠 <b>CLAUDE</b> (Anthropic)\n💬 <b>Claude's take</b>\n“{esc(tk[-1]['text'])}”\n{SITE}")
    if TOKEN and CHAT and mid:
        try:
            urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/pinChatMessage', urllib.parse.urlencode({'chat_id': CHAT, 'message_id': mid, 'disable_notification': 'true'}).encode(), timeout=20).read()
        except Exception as e:
            print('pin failed (give the bot "Pin messages" permission):', e)
    sys.exit(0)

# trades
old = {json.dumps(t, sort_keys=True) for t in load(S + 'trades.json', BEFORE)}
if TEST:
    old = {json.dumps(t, sort_keys=True) for t in load(S + 'trades.json')[:-1]}
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
    why = next((e['detail'] for e in reversed(log) if e['portfolio'] == pf and e['at'][:16] == t['at'][:16]), '') or t.get('note', '')
    msgs.append((f"{ICON.get(a, '•')} <b>{esc(LABEL.get(pf, pf))}: {a} {esc(h)}</b>\n{price}\n{when(t['at'])}" + (f"\n<i>{esc(why[:400])}</i>" if why else '') + source_for(pf, h),
                 ('trade', pf, tgcharts.symbol_for(pf, h, t.get('code')), t.get('price_local') or t.get('price_usd'), a,
                  {'experiment': pf, 'action': a, 'name': h, 'symbol': tgcharts.symbol_for(pf, h, t.get('code')), 'amount': (t.get('usd') if pf == 'China' else t.get('cad')) or 0,
                   'cur': 'USD' if pf == 'China' else 'CAD', 'price': t.get('price_local') or t.get('price_usd'), 'pcur': 'CNY' if pf == 'China' else 'USD', 'pnl': t.get('pnl', t.get('pnl_cad', t.get('pnl_usd'))), 'at': t['at'],
                   'model': 'claude', 'qty': t.get('qty') or t.get('shares'), 'held_before': t.get('held_before'), 'held_after': t.get('held_after'),
                   'entry': t.get('entry_usd') if pf != 'China' else t.get('entry_local'), 'reason': sharecard.just_reason(why.split('What would prove it wrong:')[0]),
                   'wrong_if': why.split('What would prove it wrong:', 1)[1].strip() if 'What would prove it wrong:' in why else ''})))
if TEST:
    msgs = [('🧪 <b>TEST POST</b> (a replay of the latest trade, not a new one)\n\n' + m, p) for m, p in msgs[-1:]]

# bets placed and settled
oldb = {b['bet']: b for b in load(S + 'bets.json', BEFORE if not TEST else None)}
for b in load(S + 'bets.json'):
    o = oldb.get(b['bet'])
    odds = ('+' if float(b['odds']) > 0 else '') + str(b['odds'])
    if o is None:
        msgs.append((f"🎯 <b>Sports: new bet {b['bet']}</b>\n{esc(b['pick'])} ({esc(b['event'])}) at {odds}, stake C${b['stake_cad']:,.0f} to win C${b['to_win_cad']:,.0f}",
                     ('trade', 'Sports', None, None, 'Bet', {'experiment': 'Sports', 'action': 'Bet', 'name': f"{b['pick']} ({b['event']})", 'amount': float(b['stake_cad']), 'price': float(b['odds']), 'to_win': float(b['to_win_cad']), 'cur': 'CAD', 'at': b.get('placed_at')})))
    elif o['status'] == 'Open' and b['status'] != 'Open':
        icon = {'Won': '✅', 'Lost': '❌', 'Push': '➖'}.get(b['status'], '🏁')
        msgs.append((f"{icon} <b>Sports: {b['bet']} {b['status'].lower()}</b>\n{esc(b['pick'])} ({esc(b['event'])}): {money(b['result_cad'] or 0, 'Sports')}",
                     ('trade', 'Sports', None, None, b['status'], {'experiment': 'Sports', 'action': b['status'], 'name': f"{b['pick']} ({b['event']})", 'stake': float(b['stake_cad']),
                                                                  'pnl': float(b['result_cad'] or 0) if b['status'] == 'Won' else -float(b['stake_cad']) if b['status'] == 'Lost' else 0.0, 'cur': 'CAD', 'at': b.get('settled_at')})))

# prediction markets settled (a sale at 1.00 or 0.00)
for t in load(S + 'trades.json'):
    if not TEST and t['portfolio'] == 'Predictions' and t['action'] == 'Sell' and t['price_usd'] in (0, 1) and json.dumps(t, sort_keys=True) not in old:
        msgs.append((f"🏁 <b>Prediction market settled: {esc(t['holding'])}</b>\n{'Won, paid US$1 a share' if t['price_usd'] == 1 else 'Lost, shares expired worthless'}", 'Predictions'))

# the AI's take
oldt = {x['at'] for x in load(S + 'take.json', BEFORE if not TEST else None)}
for x in load(S + 'take.json'):
    if x['at'] not in oldt:
        pass   # takes are shown on the site only; Telegram gets trades, sells and bets

# closed ledger days
oldd = {r['day'] for r in load(S + 'ledger.json', BEFORE if not TEST else None)}
ledger = load(S + 'ledger.json')
review = load(S + 'review.json')
race_days = []
for day in sorted({r['day'] for r in ledger} - oldd):
    rows = [r for r in ledger if r['day'] == day and r['portfolio'] != 'All']
    n = (datetime.fromisoformat(day) - datetime(2026, 10, 28)).days + 1
    lines = [f"📒 <b>Day {n} closed: {datetime.fromisoformat(day).strftime('%a %b %-d')}</b> (00:00 UTC · 8 a.m. HKT)"]
    for r in sorted(rows, key=lambda r: -(r['pct'] or 0)):
        lines.append(f"{'🟩' if r['pnl'] > 0.5 else '🟥' if r['pnl'] < -0.5 else '⬜'} {esc(LABEL.get(r['portfolio'], r['portfolio']))}: {money(r['pnl'], r['portfolio'])} ({r['pct'] * 100:+.1f}%)")
    if review:
        latest = max(x['at'] for x in review)
        grades = [f"{LABEL.get(x['portfolio'], x['portfolio'])} {x['grade']}" for x in review if x['at'] == latest and x['portfolio'] != 'All' and x.get('grade') not in (None, '—')]
        if grades:
            lines.append('\n<b>Report card:</b> ' + esc(', '.join(grades)))
    lines.append(f"\nEach experiment is scored on its own; the overall race is decided by total profit. Simulation only, not investment or betting advice.\n{SITE}")
    srows = []
    for r in rows:
        vals = [h['value'] for h in HIST if h['portfolio'] == r['portfolio']]
        srows.append({'pf': r['portfolio'], 'day': r['pct'] or 0, 'total': (vals[-1] / 100000 - 1) if vals else 0})
    # the shared race card below is the one daily post; per-AI day closes live on the site (Ledger)
    race_days.append((day, n))

# Bundle every trade, bet and settlement from this update into ONE post (with one chart), so the channel isn't flooded.
activity = [(m, p) for m, p in msgs if (isinstance(p, tuple) and p[0] == 'trade') or isinstance(p, str)]
others = [(m, p) for m, p in msgs if not ((isinstance(p, tuple) and p[0] == 'trade') or isinstance(p, str))]
if len(activity) > 1:
    cards = [p[5] for m, p in activity if isinstance(p, tuple) and len(p) > 5]
    first_chart = ('moves', cards) if cards else next((p for m, p in activity if isinstance(p, tuple)), activity[0][1])
    body = f"🧾 <b>{len(activity)} moves this check-in</b>\n\n" + '\n\n'.join(m for m, p in activity)
    if len(body) > 3500:
        body = body[:3450].rsplit('\n\n', 1)[0] + f"\n\n…and more on {SITE}"
    activity = [(body, first_chart)]
msgs = activity + others
for i, (m, pic) in enumerate(msgs):
    if isinstance(pic, tuple) and pic[0] == 'moves':   # several moves: a cover and one picture per move, as one album (agreed by all three AIs, Oct 30)
        pics = sharecard.album('claude', pic[1], CLAUDE_TRADES, HIST, f'/tmp/pt_album_{i}', series=lambda s, _m={c.get('symbol'): c['experiment'] for c in pic[1]}: sharecard.chart_points(s, _m.get(s)))
        if len(pics) >= 2:
            mm = '🟠 <b>CLAUDE</b> (Anthropic)\n' + m + ('' if SITE in m else f'\n{SITE}')
            discord.post(mm, pics)   # the whole album, never the cover alone: the cover says "Swipe for each move" (owner, Oct 30)
            if sharecard.tg_album(TOKEN, CHAT, pics, mm):
                continue
            send(mm, sharecard.moves_card('claude', pic[1], f'/tmp/pt_moves_{i}.png') or pics[1], silent=False, _dc=False)   # album failed: a summary with no swipe line
            continue
        photo = (pics[0] if len(pics) == 1 else None) or sharecard.moves_card('claude', pic[1], f'/tmp/pt_moves_{i}.png') or chart_section(pic[1][0]['experiment'], i)
    elif isinstance(pic, tuple) and pic[0] == 'trade':
        _, pf_, sym_, px_, act_ = pic[:5]
        photo = ((sharecard.album('claude', [pic[5]], CLAUDE_TRADES, HIST, f'/tmp/pt_one_{i}', series=lambda s, _e=pf_: sharecard.chart_points(s, _e)) or [None])[0] if len(pic) > 5 else None) or \
                (sharecard.trade_card('claude', pic[5], f'/tmp/pt_card_{i}.png', symbol=sym_) if len(pic) > 5 else None) or \
                (tgcharts.price_chart(sym_, 'Claude · ' + LABEL.get(pf_, pf_), '#d97757', px_, act_, f'/tmp/pt_trade_{i}.png') if sym_ else None) or chart_section(pf_, i)
    elif isinstance(pic, tuple):
        photo = chart_scoreboard(pic[1], pic[2])
    else:
        photo = chart_section(pic, i) if pic else None
    m = '🟠 <b>CLAUDE</b> (Anthropic)\n' + m
    send(m + ('' if SITE in m else f'\n{SITE}'), photo, silent=False)   # every trade, bet and result pings (owner's choice)
# the race card: one shareable picture of the overall standings after each daily close
for day, n in race_days[-1:]:
    try:
        import racecard
        fxr = load(S + 'fx.json') or {}
        usdcad = float(fxr.get('usdcad') or 1.38) if isinstance(fxr, dict) else 1.38
        start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        table, big = racecard.races(start)
        if table:
            pic = racecard.races_card(table, big, f"After Day {n} · {datetime.fromisoformat(day).strftime('%a %b %-d')}")
            medal = ['🥇', '🥈', '🥉']
            txt = [f"🏁 <b>THE RACES after Day {n}</b>", 'Ten separate races, each on its own (profit since the Oct 28 restart):', '']
            for e in racecard.ORDER:
                rows = table.get(e) or []
                if not rows:
                    continue
                lab = racecard.LABEL.get(e, e) + (' (US$)' if e == 'China' else '')
                if max(x[1] for x in rows) - min(x[1] for x in rows) < 0.5:
                    txt.append(f"<b>{lab}</b>: all even so far")
                    continue
                txt.append(f"<b>{lab}</b>: " + ' · '.join(f"{medal[i]} {racecard.AIS[mid][0]} {racecard.money(p, e)}" for i, (mid, p) in enumerate(rows[:3])))
            if big:
                _, mid, e, d, pct = big
                txt.append(f"\nBiggest move today: {racecard.AIS[mid][0]} in {racecard.LABEL.get(e, e)}, {racecard.money(d, e)} ({pct * 100:+.1f}%)")
            try:   # Call-out of the day (owner and Gemini, Oct 30): the sharpest thing one AI said about another
                co = (json.load(open('data.json')).get('callout') or [None])[0]
                if co:
                    nm = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
                    tag = ('found it wrong' if co.get('verdict') == 'wrong' else 'found it partly wrong') if co['kind'] == 'fact' else f"gave it an {co.get('grade')}" if co.get('grade') == 'F' else f"gave it a {co.get('grade')}"
                    txt.append(f"\n🎯 <b>Call-out of the day</b>: {nm.get(co['by'], co['by'])} on {nm.get(co['about'], co['about'])}" + (f" ({esc({'AllInTrading': 'All in: trading', 'AllInSports': 'All in: sports'}.get(co['race']) or LABEL.get(co['race'], co['race']))})" if co.get('race') else '') + f", {tag}:\n“{esc(co['text'])}”")
            except Exception as e:
                print('call-out failed', e)
            txt.append(f"\nThe races are only added together at the final scoring on Nov 28.\nShare it 👉 {SITE}")
            send('\n'.join(txt), pic, silent=False)
            discord.post('\n'.join(txt), pic, url=discord.DAILY)   # also in #daily-results (owner, Oct 30)
    except Exception as e:
        print('race card failed', e)
print(f'{len(msgs)} message(s)')
