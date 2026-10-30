"""Discord #lead-changes: one post each time an AI takes the lead in a race (owner, Oct 30).

Lead changes come from data.json "moments" (built by ops/build_site.py from every AI's value history).
  python3 ops/discord_leads.py pick   -> after the site is built: lists the new ones in /tmp/discord_leads.json and
                                         records them in ops/src/discord_sent.json (committed with the build)
  python3 ops/discord_leads.py post   -> after the push succeeded: posts what pick listed
Only lead changes from the last 12 hours are posted; older ones are recorded silently (no flood on the first run).
Does nothing without DISCORD_WEBHOOK_LEADS.
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discord  # noqa: E402

SENT, TMP = 'ops/src/discord_sent.json', '/tmp/discord_leads.json'
AIS = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets',
         'AllInTrading': 'All in: trading (side race)', 'AllInSports': 'All in: sports (side race)'}
SITE = 'https://papertrades.ai'


def money(v, cur):
    sym = 'US$' if cur == 'USD' else 'C$'
    return ('+' if v >= 0 else '−') + sym + f'{abs(v):,.0f}'


def text(m):
    who, race, cur = AIS.get(m['who'], m['who']), LABEL.get(m['race'], m['race']), m.get('cur', 'CAD')
    prof = m.get('profit') or {}
    order = sorted(prof, key=lambda k: -prof[k])
    medal = ['🥇', '🥈', '🥉']
    at = datetime.fromisoformat(m['at'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/New_York'))   # EDT, then EST from Nov 1
    lines = [f"👑 <b>{who} takes the lead in {race}</b>"]
    if m.get('over'):
        lines.append(f"Passed {AIS.get(m['over'], m['over'])}" + (f", now ahead by {money(m['lead'], cur)[1:]}" if m.get('lead') is not None else '') + '.')
    if order:
        lines.append(' · '.join(f"{medal[i]} {AIS.get(k, k)} {money(prof[k], cur)}" for i, k in enumerate(order[:3])))
    lines.append(f"{at.strftime('%b %-d, %-I:%M %p')} ET · profit since the Oct 28 restart · {SITE}")
    return '\n'.join(lines)


def pick():
    try:
        moments = json.load(open('data.json')).get('moments') or []
    except Exception:
        moments = []
    sent = json.load(open(SENT)) if os.path.exists(SENT) else {}
    now = datetime.now(timezone.utc)
    new = []
    for m in sorted(moments, key=lambda m: m['at']):
        if m['id'] in sent:
            continue
        sent[m['id']] = now.isoformat(timespec='seconds')
        if now - datetime.fromisoformat(m['at'].replace('Z', '+00:00')) <= timedelta(hours=12):
            new.append(m)
    json.dump(sent, open(SENT, 'w'), indent=1)
    json.dump(new, open(TMP, 'w'))
    print(f'lead changes to post: {len(new)}')


def post():
    if not os.path.exists(TMP):
        return
    for m in json.load(open(TMP)):
        discord.post(text(m), url=discord.LEADS)


if __name__ == '__main__':
    {'pick': pick, 'post': post}[sys.argv[1] if len(sys.argv) > 1 else 'pick']()
