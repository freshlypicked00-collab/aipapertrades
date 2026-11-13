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
    lines = [f'{dot} **{name} holds now** ({maker}) · pretend money', '']
    for race, rows in es.items():
        r = next((x for x in rows if x.get('id') == mid), None)
        if not r:
            continue
        v, p = float(r.get('value') or 0), float(r.get('profit') or 0)
        pct = p / (v - p) * 100 if v - p else 0
        tag = ' · out of money' if r.get('busted') else ''
        lines.append(f"**{LABEL.get(race, race)}** {money(v, race)} ({'+' if p >= 0 else ''}{money(p, race)}, {'+' if pct >= 0 else '−'}{abs(pct):.1f}%){tag}")
        pie = sorted(r.get('pie') or [], key=lambda s: -float(s.get('value') or 0))
        held = [s for s in pie if not str(s['name']).startswith(('Cash', 'Not bet'))]
        cash = sum(float(s['value']) for s in pie if str(s['name']).startswith(('Cash', 'Not bet')))
        nm = lambda n: (n.split(' (')[0] if len(n) > 40 and ' (' in n else n)[:40] + ('…' if len(n.split(' (')[0] if len(n) > 40 and ' (' in n else n) > 40 else '')
        # a short is money owed back, not money held: say so, and say the cash includes what the short sales brought in
        short = lambda s: str(s['name']).endswith('(short)')
        bits = [(f"{nm(str(s['name'])[:-8])}: short, owes {money(float(s['value']), race)}" if short(s) else f"{nm(str(s['name']))} {money(float(s['value']), race)}") for s in held[:4]]
        if len(held) > 4:
            bits.append(f'+{len(held) - 4} more')
        if cash > 0.5:
            bits.append(f"{'not bet' if race == 'Sports' else 'cash'} {money(cash, race)}" + (' (includes the money from short sales)' if any(short(x) for x in held) else ''))
        lines.append('  ' + (' · '.join(bits) if bits else 'all cash'))
    t = et_now()
    lines += ['', f"Updated {t.strftime('%b %d, %I:%M %p').replace(' 0', ' ')} ET · each trade is in its race channel · "
                  f"full details: <https://papertrades.ai/#ai-{mid}>"]
    text = '\n'.join(lines)
    return text if len(text) <= 1990 else text[:1980].rsplit('\n', 1)[0] + '\n…'


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
    mine = [m for m in B.call('GET', f'/channels/{ch}/messages?limit=30') if (m.get('author') or {}).get('bot')]
    for mid, dot, name, maker in AIS:
        text = message(mid, dot, name, maker, es)
        old = next((m for m in mine if m.get('content', '').startswith(f'{dot} **{name} holds now**')), None)
        body = {'content': text, 'allowed_mentions': {'parse': []}, 'flags': 4}
        if old and old['content'].split('\nUpdated ')[0] == text.split('\nUpdated ')[0]:
            print(name, 'unchanged')
            continue
        if old:
            B.call('PATCH', f'/channels/{ch}/messages/{old["id"]}', body)
            print(name, 'updated')
        else:
            B.call('POST', f'/channels/{ch}/messages', body)
            print(name, 'posted')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:   # never fail the publish over Discord
        print('discord holdings failed:', str(e)[:300])
