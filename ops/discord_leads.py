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
         'AllInTrading': 'High risk: trading (side race)', 'AllInSports': 'High risk: sports (side race)'}
SITE = 'https://papertrades.ai'


def money(v, cur):
    sym = 'US$' if cur == 'USD' else 'C$'
    return ('+' if v >= 0 else '−') + sym + f'{abs(v):,.0f}'


def _dur(h):
    if h is None:
        return ''
    return 'under an hour' if h < 1 else f'{round(h)} h' if h < 48 else f'{round(h / 24)} days'


def rivalry(m):
    """'ChatGPT had led for 9 h · 4th lead change in this race' (numbers from the value history; nothing estimated)."""
    bits = []
    if m.get('over') and m.get('held_h') is not None:
        bits.append(f"{AIS.get(m['over'], m['over'])} had led for {_dur(m['held_h'])}")
    n = m.get('nth')
    if n:
        bits.append(f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')} lead change in this race")
    return ' · '.join(bits)


def text(m):
    who, race, cur = AIS.get(m['who'], m['who']), LABEL.get(m['race'], m['race']), m.get('cur', 'CAD')
    prof = m.get('profit') or {}
    order = sorted(prof, key=lambda k: -prof[k])
    medal = ['🥇', '🥈', '🥉']
    at = datetime.fromisoformat(m['at'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/New_York'))   # EDT, then EST from Nov 1
    lines = [f"👑 <b>{who} {'retakes' if m.get('again') else 'takes'} the lead in {race}</b>"]
    if m.get('over'):
        lines.append(f"Passed {AIS.get(m['over'], m['over'])}" + (f", now ahead by {money(m['lead'], cur)[1:]}" if m.get('lead') is not None else '') + '.')
    ctx = rivalry(m)   # W14 (owner, Oct 30; all three AIs agreed): how long the last lead lasted and how many times it has changed
    if ctx:
        lines.append(ctx)
    if order:
        lines.append(' · '.join(f"{medal[i]} {AIS.get(k, k)} {money(prof[k], cur)}" for i, k in enumerate(order[:3])))
        if prof[order[0]] < 0:   # leading while down reads oddly: say so (owner, Nov 2)
            lines[-1] += ' (all three are down; the leader has the smallest loss)'
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
    import xpost
    for m in json.load(open(TMP)):
        discord.post(text(m), url=discord.LEADS, ping=discord.ROLE_LEADS)
        tab = {'Stocks': 'stocks', 'Crypto': 'crypto', 'China': 'china', 'Metals': 'metals', 'Energy': 'energy', 'Options': 'options', 'Currencies': 'currencies',
               'Safe': 'safe', 'Sports': 'sports', 'Predictions': 'predictions', 'AllInTrading': 'allin', 'AllInSports': 'allin'}.get(m.get('race') or m.get('exp'), '')
        xpost.post(text(m), key='lead-' + m['id'], reply_link='https://papertrades.ai/?utm_source=x' + ('#' + tab if tab else ''))   # X too, the race's page in the first reply (owner, Oct 30)


if __name__ == '__main__':
    {'pick': pick, 'post': post}[sys.argv[1] if len(sys.argv) > 1 else 'pick']()
