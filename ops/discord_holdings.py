"""#holdings on Discord: one message per AI with what it holds right now in every race, kept up to date (owner, Nov 13).

Runs after every site publish (.github/workflows/deploy.yml). Reads the same data.json the site shows (exp_standings: each
race's value, profit and money split), so every number matches the site. Edits the bot's three messages in place instead of
posting new ones: the channel never fills up and nobody is pinged. Never fails the publish.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discord_bot as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = {k: label for k, _, label in B.RACES}
AIS = [('claude', '🟠', 'CLAUDE', 'Anthropic'), ('gemini', '🔵', 'GEMINI', 'Google'), ('chatgpt', '⚪', 'CHATGPT', 'OpenAI')]


def money(x, race):
    cur = 'US$' if race == 'China' else 'C$'
    return ('−' if x < 0 else '') + f'{cur}{abs(round(x)):,}'


def et_now():
    # Eastern time without a tz library: EST (UTC-5) from the first Sunday of November, which covers the whole season
    return datetime.now(timezone.utc) - timedelta(hours=5)


def message(mid, dot, name, maker, es):
    # Every holding is listed, always, with its full name (owner, Nov 13: "dont let it show incomplete stuff make sure all holdings
    # show ... always"): no "+N more", no cut names. Only if Discord's 2,000-character limit would be passed are the names shortened
    # (the bracketed part dropped, then the maker's prefix), and every holding still shows.
    for level in (0, 1, 2):
        text = _message(mid, dot, name, maker, es, level)
        if len(text) <= 1990:
            return text
    return text[:1990]


def _nm(n, level, race=''):
    n = str(n)
    if level >= 1 and race != 'Predictions':   # a market's side (Yes/No) is in the brackets: keep it
        n = n.split(' (')[0]
    if level >= 2:
        n = n.split(': ', 1)[-1]
        n = n[:-4] if n.endswith(' USD') else n
    return n


def _message(mid, dot, name, maker, es, level):
    lines = [f'{dot} **{name} holds now** ({maker}) · pretend money', '']
    allcash = []
    for race, rows in es.items():
        r = next((x for x in rows if x.get('id') == mid), None)
        if not r:
            continue
        v, p = float(r.get('value') or 0), float(r.get('profit') or 0)
        pct = p / (v - p) * 100 if v - p else 0
        tag = ' · out of money' if r.get('busted') else ''
        if not r.get('busted') and all(str(x['name']).startswith(('Cash', 'Not bet')) for x in (r.get('pie') or [])):
            allcash.append(f"{LABEL.get(race, race)} {money(v, race)} ({'+' if p >= 0 else ''}{money(p, race)})")   # nothing held: one shared line at the end
            continue
        lines.append(f"**{LABEL.get(race, race)}** {money(v, race)} ({'+' if p >= 0 else ''}{money(p, race)}, {'+' if pct >= 0 else '−'}{abs(pct):.1f}%){tag}")
        pie = sorted(r.get('pie') or [], key=lambda s: -float(s.get('value') or 0))
        held = [s for s in pie if not str(s['name']).startswith(('Cash', 'Not bet'))]
        cash = sum(float(s['value']) for s in pie if str(s['name']).startswith(('Cash', 'Not bet')))
        # a short is money owed back, not money held: say so, and say the cash includes what the short sales brought in
        short = lambda s: str(s['name']).endswith('(short)')
        bits = [(f"{_nm(str(s['name'])[:-8], level, race)}: short, owes {money(float(s['value']), race)}" if short(s) else f"{_nm(s['name'], level, race)} {money(float(s['value']), race)}") for s in held]
        if cash > 0.5:
            bits.append(f"{'not bet' if race == 'Sports' else 'cash'} {money(cash, race)}" + (' (includes the money from short sales)' if any(short(x) for x in held) else ''))
        lines.append('  ' + (' · '.join(bits) if bits else 'all cash'))
    if allcash:
        lines.append('**All cash:** ' + ' · '.join(allcash))
    t = et_now()
    lines += ['', f"Updated {t.strftime('%b %d, %I:%M %p').replace(' 0', ' ')} ET · each trade is in its race channel · "
                  f"full details: <https://papertrades.ai/#ai-{mid}>"]
    return '\n'.join(lines)


def main():
    if not B.TOKEN:
        print('no DISCORD_BOT_TOKEN: nothing to do')
        return
    ch = (B.load_map().get('channels') or {}).get('holdings')
    if not ch:
        print('no #holdings channel yet (run the Discord setup)')
        return
    es = json.load(open(os.path.join(ROOT, 'data.json'))).get('exp_standings') or {}
    if not es:
        print('no standings in data.json')
        return
    data = json.load(open(os.path.join(ROOT, 'data.json')))
    try:
        import holdcards as HC
    except Exception as e:   # no picture library: text only
        HC = None
        print('pictures off:', e)
    mine = [m for m in B.call('GET', f'/channels/{ch}/messages?limit=30') if (m.get('author') or {}).get('bot')]
    posts = [(f'{dot} **{name} holds now**', message(mid, dot, name, maker, es),
              (lambda mid=mid: [HC.portfolio_card(data, mid, f'/tmp/hold_{mid}_1.png'), HC.change_card(data, mid, f'/tmp/hold_{mid}_2.png')]))
             for mid, dot, name, maker in AIS]
    hr_text = ('🎲 **HIGH RISK side races** · what each AI holds now · pretend money\n'
               'Each AI got C$100,000 for each side race; one big swing can end it.\n\n'
               f"Updated {et_now().strftime('%b %d, %I:%M %p').replace(' 0', ' ')} ET · full details: <https://papertrades.ai/#allin>")
    posts.append(('🎲 **HIGH RISK side races**', hr_text, (lambda: [HC.highrisk_card(data, '/tmp/hold_highrisk.png')])))
    for head, text, pics in posts:
        old = next((m for m in mine if m.get('content', '').startswith(head)), None)
        body = {'content': text, 'allowed_mentions': {'parse': []}, 'flags': 4}
        files = []
        if HC:
            try:
                files = [p for p in pics() if p]
            except Exception as e:
                print('picture failed', head, e)
        if files:   # the new pictures replace the old ones on the same message
            body['attachments'] = [{'id': i, 'filename': f'{i + 1:02d}.png'} for i in range(len(files))]
        if old:
            B.call('PATCH', f'/channels/{ch}/messages/{old["id"]}', body, files=files or None)
            print(head, 'updated', len(files), 'pictures')
        else:
            B.call('POST', f'/channels/{ch}/messages', body, files=files or None)
            print(head, 'posted', len(files), 'pictures')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:   # never fail the publish over Discord
        print('discord holdings failed:', str(e)[:300])
