"""Discord as the main live-alert place (owner, Nov 9): one channel per race, set up and fed by one bot.

Layout agreed Nov 9 (Claude and ChatGPT: one channel per race, as the owner asked; Gemini preferred three per-AI channels):
  START HERE   #welcome-and-rules  #how-it-works  #pick-your-alerts        (read-only)
  HEADLINES    #announcements  #daily-results  #lead-changes  #big-moments (read-only; pings only opt-in roles)
  LIVE         #live-trades (every move, as today; no ping)
  RACES        one read-only channel per race, every move with the AI's reason; its own opt-in alert role
  COMMUNITY    #general  #who-wins  #feedback-bugs
Never @everyone or @here (all three agreed); every post says pretend money, not advice.

  python3 ops/discord_bot.py setup     -> creates/arranges roles, categories and channels, writes ops/discord_channels.json
  python3 ops/discord_bot.py check     -> says what the bot can see (no changes)

Everything else imports route(). Does nothing until the GitHub secret DISCORD_BOT_TOKEN is set and setup has run,
and never raises: a Discord problem must never stop a check-in or a Telegram post.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
API = 'https://discord.com/api/v10'
UA = 'DiscordBot (https://papertrades.ai, 1.0)'
MAP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'discord_channels.json')
SITE = 'https://papertrades.ai'
FOOT = 'Pretend money · real prices · not advice. We never DM anyone about money.'
STAT = {'sent': 0, 'failed': 0, 'error': ''}

# race key (the experiment name in the data) -> channel name and the alert role's name
RACES = [('Stocks', 'stocks', 'Stocks and anything'), ('Crypto', 'crypto', 'Crypto'), ('China', 'china-stocks', 'China stocks'),
         ('Metals', 'metals', 'Metals'), ('Energy', 'energy', 'Oil and energy'), ('Options', 'options', 'Options'),
         ('Currencies', 'currencies', 'Currencies'), ('Safe', 'play-it-safe', 'Play it safe'), ('Sports', 'sports-bets', 'Sports bets'),
         ('Predictions', 'prediction-markets', 'Prediction markets'), ('AllInTrading', 'high-risk-trading', 'High risk: trading'),
         ('AllInSports', 'high-risk-sports', 'High risk: sports')]
LAYOUT = [
    ('START HERE', [('welcome-and-rules', 'ro', 'What this is: three AIs, pretend money, real prices. Not advice. We never DM you about money.'),
                    ('how-it-works', 'ro', 'The races, the rules and where every number comes from.'),
                    ('pick-your-alerts', 'ro', 'Choose which alerts ping you. Nothing pings you until you pick it.')]),
    ('HEADLINES', [('announcements', 'ro', 'Season news, rule clarifications, data issues.'),
                   ('daily-results', 'ro', 'The race card after each daily close (00:00 UTC). Pings @Daily Results Alerts.'),
                   ('lead-changes', 'ro', 'Each time an AI takes the lead in a race. Pings @Lead Change Alerts.'),
                   ('big-moments', 'ro', 'Wins or losses of C$5,000+, new records, an AI crossing ±10/25/50%. Pings @Big Moment Alerts.')]),
    ('LIVE', [('live-trades', 'ro', 'Every move from all three AIs, all races, as it happens. No pings.')]),
    ('RACES', [(ch, 'ro', f'{label}: every move from Claude, Gemini and ChatGPT in this race, with each AI\'s own reason. Pings @{label} Alerts.')
               for _, ch, label in RACES]),
    ('COMMUNITY', [('general', 'chat', 'Talk about the race. No links, no money talk, no DMs: we never DM you.'),
                   ('who-wins', 'chat', 'Guess who leads tomorrow.'),
                   ('feedback-bugs', 'chat', 'Something looks wrong on the site? Tell us here.')]),
]
ROLES = ['Daily Results Alerts', 'Lead Change Alerts', 'Big Moment Alerts', 'Season News Alerts'] + [f'{label} Alerts' for _, _, label in RACES]

# Discord permission bits
VIEW, SEND, MANAGE_MSG, EMBED, ATTACH, HISTORY, REACT, THREADS = 1 << 10, 1 << 11, 1 << 13, 1 << 14, 1 << 15, 1 << 16, 1 << 6, (1 << 35) | (1 << 36) | (1 << 38)
BOT_PERMS = 16 | 32 | VIEW | SEND | MANAGE_MSG | EMBED | ATTACH | HISTORY | (1 << 28)   # manage channels/server/roles, post, pin, files
SAFE_WORDS = ['dm me', 'message me', 'wallet', 'seed phrase', 'private key', 'signals', 'guaranteed returns', 'guaranteed profit',
              'invest with me', 'copy my trades', 'send crypto', 'send btc', 'send usdt', 'recovery phrase', 'airdrop', 'giveaway', 'whatsapp', 'telegram me']


def call(method, path, body=None, files=None, reason=None):
    """One Discord API call with the bot token; waits and retries once on a rate limit. Returns the parsed JSON (or {})."""
    h = {'Authorization': f'Bot {TOKEN}', 'User-Agent': UA}
    if reason:
        h['X-Audit-Log-Reason'] = reason
    if files:
        b = '----ptbot' + str(os.getpid())
        data = f'--{b}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n{json.dumps(body or {})}\r\n'.encode()
        for i, p in enumerate(files):
            ext, ct = ('gif', 'image/gif') if p.endswith('.gif') else ('png', 'image/png')
            data += (f'--{b}\r\nContent-Disposition: form-data; name="files[{i}]"; filename="{i + 1:02d}.{ext}"\r\nContent-Type: {ct}\r\n\r\n'.encode()
                     + open(p, 'rb').read() + b'\r\n')
        data += f'--{b}--\r\n'.encode()
        h['Content-Type'] = f'multipart/form-data; boundary={b}'
    else:
        data = json.dumps(body).encode() if body is not None else None
        if data is not None:
            h['Content-Type'] = 'application/json'
    for attempt in (1, 2, 3):
        req = urllib.request.Request(API + path, data, h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            txt = e.read().decode('utf-8', 'replace')
            if e.code == 429 and attempt < 3:
                try:
                    wait = float(json.loads(txt).get('retry_after', 2))
                except Exception:
                    wait = 2
                time.sleep(min(wait, 15) + 0.3)
                continue
            raise RuntimeError(f'{method} {path}: HTTP {e.code} {txt[:200]}')
    return {}


def load_map():
    try:
        return json.load(open(MAP_FILE))
    except Exception:
        return {}


def ready():
    m = load_map()
    return bool(TOKEN and m.get('channels'))


def to_md(text):
    import discord   # the same HTML -> Markdown conversion as the webhook posts
    return discord.to_md(text)


def send(key, text, photos=None, ping_role=None):
    """Post to the channel named by key (e.g. 'crypto', 'big-moments'). ping_role = a role key from the map (only that role)."""
    if not TOKEN:
        return False
    try:
        m = load_map()
        ch = (m.get('channels') or {}).get(key)
        if not ch:
            return False
        rid = (m.get('roles') or {}).get(ping_role) if ping_role else None
        content = (f'<@&{rid}> ' if rid else '') + to_md(text)
        if len(content) > 1990:
            content = content[:1985].rstrip() + ' …'
        body = {'content': content, 'allowed_mentions': {'parse': [], 'roles': [rid] if rid else []}, 'flags': 4}   # never @everyone; no link previews
        files = [p for p in (photos or []) if p and os.path.exists(p)][:10]
        files = [p[:-4] + '.gif' if p.endswith('.png') and os.path.exists(p[:-4] + '.gif') else p for p in files]   # animated card when there is one
        if sum(os.path.getsize(p) for p in files) > 9 * 1024 * 1024:
            files = [p[:-4] + '.png' if p.endswith('.gif') and os.path.exists(p[:-4] + '.png') else p for p in files]
        call('POST', f'/channels/{ch}/messages', body, files=files or None)
        STAT['sent'] += 1
        time.sleep(0.4)
        return True
    except Exception as e:
        STAT['failed'] += 1
        STAT['error'] = str(e)[:200]
        print('discord bot failed', str(e)[:200])
        return False


def route(who, items, trades=None, history=None, series=None, prefix='/tmp/dcr'):
    """Post one check-in's moves to their race channels. who = 'claude' | 'Gemini' | 'ChatGPT'; items = [(text_html, move)].
    Each race gets one post: the AI's name, that race's moves (the same lines as Telegram, the AI's own reasons) and its cards."""
    if not ready() or not items:
        return 0
    head = {'claude': '🟠 <b>CLAUDE</b> (Anthropic)', 'Gemini': '🔵 <b>GEMINI</b> (Google)', 'ChatGPT': '⚪ <b>CHATGPT</b> (OpenAI)'}.get(who, f'<b>{who}</b>')
    chan = {k: ch for k, ch, _ in RACES}
    groups = {}
    for text, mv in items:
        e = (mv or {}).get('experiment') or ''
        if e in chan:
            groups.setdefault(e, []).append((text, mv))
    n = 0
    for e, its in groups.items():
        try:
            pics = []
            try:
                import sharecard
                pics = sharecard.album(who.lower() if who == 'claude' else who, [mv for _, mv in its], trades, history, f'{prefix}_{e}', series=series)
            except Exception as ex:
                print('discord route cards failed', ex)
            body = head + '\n' + '\n\n'.join(t for t, _ in its) + f'\n\n{FOOT}\n{SITE}'
            if send(chan[e], body, pics, ping_role=e):
                n += 1
        except Exception as ex:
            print('discord route failed', e, ex)
    return n


# ---------- one-time setup (run by .github/workflows/discord-setup.yml) ----------

def guild_id():
    gs = call('GET', '/users/@me/guilds')
    if len(gs) != 1:
        raise RuntimeError(f'the bot should be in exactly one server, it is in {len(gs)}: ' + ', '.join(g.get('name', '?') for g in gs))
    return gs[0]['id'], gs[0]['name']


def setup():
    gid, gname = guild_id()
    me = call('GET', '/users/@me')
    print('server:', gname, '| bot:', me.get('username'))
    m = load_map()
    m['guild'] = gid
    # roles: reuse by name (the two alert roles already exist), create the rest; mentionable so the bot can ping them
    roles = {r['name']: r for r in call('GET', f'/guilds/{gid}/roles')}
    m.setdefault('roles', {})
    for name in ROLES:
        r = roles.get(name) or call('POST', f'/guilds/{gid}/roles', {'name': name, 'mentionable': True, 'permissions': '0'}, reason='PaperTrades.AI alerts')
        key = next((k for k, _, label in RACES if f'{label} Alerts' == name), None) or {'Daily Results Alerts': 'daily', 'Lead Change Alerts': 'leads',
                                                                                        'Big Moment Alerts': 'big', 'Season News Alerts': 'news'}[name]
        m['roles'][key] = r['id']
        print('role', name, r['id'])
    everyone = gid   # the @everyone role has the server's ID
    chans = call('GET', f'/guilds/{gid}/channels')
    by_name = {c['name']: c for c in chans}
    m.setdefault('channels', {})
    pos = 0
    for cat, items in LAYOUT:
        c = next((x for x in chans if x['type'] == 4 and x['name'].lower() == cat.lower()), None) or \
            call('POST', f'/guilds/{gid}/channels', {'name': cat, 'type': 4, 'position': pos}, reason='PaperTrades.AI layout')
        pos += 1
        for name, mode, topic in items:
            ow = [{'id': me['id'], 'type': 1, 'allow': str(VIEW | SEND | EMBED | ATTACH | HISTORY | MANAGE_MSG), 'deny': '0'}]
            if mode == 'ro':   # read-only: members read and react, only the bot posts
                ow.append({'id': everyone, 'type': 0, 'allow': str(VIEW | HISTORY | REACT), 'deny': str(SEND | THREADS)})
            else:              # chat: members talk; links and files are blocked by AutoMod/permissions, slow mode on
                ow.append({'id': everyone, 'type': 0, 'allow': str(VIEW | HISTORY | SEND | REACT), 'deny': str(EMBED | ATTACH | THREADS)})
            body = {'name': name, 'type': 0, 'parent_id': c['id'], 'topic': topic, 'permission_overwrites': ow}
            if mode == 'chat':
                body['rate_limit_per_user'] = 15
            ex = by_name.get(name)
            if ex:
                call('PATCH', f'/channels/{ex["id"]}', {k: v for k, v in body.items() if k != 'type'}, reason='PaperTrades.AI layout')
                cid = ex['id']
            else:
                cid = call('POST', f'/guilds/{gid}/channels', body, reason='PaperTrades.AI layout')['id']
            m['channels'][name] = cid
            for k, ch, _ in RACES:
                if ch == name:
                    m['channels'][ch] = cid
            print('channel', cat, '#' + name, cid)
    # server: notifications only for @mentions; verification medium (all three agreed)
    try:
        call('PATCH', f'/guilds/{gid}', {'default_message_notifications': 1, 'verification_level': 2, 'explicit_content_filter': 2}, reason='PaperTrades.AI safety')
    except Exception as e:
        print('server settings not changed:', e)
    # AutoMod: block scam words and links from members (the bot's own posts are exempt by the role/channel exemptions below)
    try:
        rules = {r['name']: r for r in call('GET', f'/guilds/{gid}/auto-moderation/rules')}
        ro = [m['channels'][n] for _, its in LAYOUT for n, mode, _ in its if mode == 'ro']
        want = {'PaperTrades.AI: scam words': {'keyword_filter': [f'*{w}*' for w in SAFE_WORDS]},
                'PaperTrades.AI: no links': {'regex_patterns': [r'https?://', r'discord\.gg/', r'www\.']}}
        for name, meta in want.items():
            body = {'name': name, 'event_type': 1, 'trigger_type': 1, 'trigger_metadata': meta, 'enabled': True, 'exempt_channels': ro,
                    'actions': [{'type': 1, 'metadata': {'custom_message': 'Blocked: no links or money talk here. PaperTrades.AI never DMs anyone about money.'}}]}
            if name in rules:
                call('PATCH', f'/guilds/{gid}/auto-moderation/rules/{rules[name]["id"]}', {k: v for k, v in body.items() if k not in ('event_type', 'trigger_type')})
            else:
                call('POST', f'/guilds/{gid}/auto-moderation/rules', body)
            print('automod', name)
    except Exception as e:
        print('automod not set:', e)
    m['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    json.dump(m, open(MAP_FILE, 'w'), indent=1)
    print('wrote', MAP_FILE)


WELCOME = {
    'welcome-and-rules': """**Welcome to PaperTrades.AI** 🤖📈
Three AIs (Claude, Gemini and ChatGPT) each trade C$100,000 of **pretend money** at real prices in 10 races, Oct 28 to Nov 28, 2026. Every trade and bet is posted here with the AI's own reason, and every number can be checked on https://papertrades.ai

**Rules**
1. 🔒 **We never DM you about money.** No admin, no bot, no "support" will ever message you asking for money, a wallet, a seed phrase or a password. Anyone who does is a scammer: report them.
2. Pretend money only. Nothing here is investment, trading or betting advice.
3. No links, no promotions, no "signals", no "invest with me".
4. Be kind. Talk about the race, not about people.

**Official accounts:** papertrades.ai · Telegram @PaperTradesAI · X @papertradesai · Instagram @papertrades.ai · YouTube @PaperTradesAI""",
    'how-it-works': """**How the race works**
• 3 AIs, 10 separate races: Stocks and anything, Crypto, China stocks, Metals, Oil and energy, Options, Currencies, Play it safe, Sports bets, Prediction markets. Plus 2 *High risk* side races.
• Each AI starts every race with C$100,000 of pretend money. Real prices and real odds. No human picks or approves a trade.
• Each AI checks in on its own schedule, decides, and explains why. The other two grade the decision.
• The daily scoreboard is taken at 00:00 UTC (7 p.m. ET). The season ends Nov 28.

**Where to look**
📢 #announcements, #daily-results, #lead-changes, #big-moments: the headlines
⚡ #live-trades: every move from all three AIs
🏁 One channel per race (#stocks, #crypto ...): only that race's moves
✅ Every move has a transaction ID you can look up on the site's Ledger.""",
    'pick-your-alerts': """**Pick your alerts** 🔔
Nothing here pings you until you choose it.
Open the server menu (tap the server name at the top) → **Channels & Roles** → **Browse Channels / Customize** and pick:
• **Daily Results Alerts**: the scoreboard after each daily close
• **Lead Change Alerts**: when an AI takes the lead in a race
• **Big Moment Alerts**: big wins and losses, records
• **Season News Alerts**: important announcements
• Any race's alert role (for example **Crypto Alerts**) to be pinged for every move in that race

Prefer quiet? Follow the channels without picking any role and read whenever you like.""",
}


def welcome():
    """Post (or replace) the text in the three START HERE channels and pin it."""
    m = load_map()
    for key, text in WELCOME.items():
        ch = (m.get('channels') or {}).get(key)
        if not ch:
            continue
        for msg in call('GET', f'/channels/{ch}/messages?limit=20'):   # replace the bot's earlier version, so re-running never duplicates
            if (msg.get('author') or {}).get('bot'):
                call('DELETE', f'/channels/{ch}/messages/{msg["id"]}')
                time.sleep(0.4)
        r = call('POST', f'/channels/{ch}/messages', {'content': text, 'allowed_mentions': {'parse': []}, 'flags': 4})
        try:
            call('PUT', f'/channels/{ch}/pins/{r["id"]}')
        except Exception as e:
            print('pin failed', key, e)
        print('posted', key)


def onboarding():
    """Add the alert roles to Discord's Onboarding so members pick them when they join (and in Channels & Roles later).
    Keeps every other question the owner set up; replaces only our own alerts question."""
    m = load_map(); gid = m['guild']; R = m['roles']; C = m['channels']
    ob = call('GET', f'/guilds/{gid}/onboarding')
    keep = [q for q in ob.get('prompts', []) if not any((o.get('role_ids') and set(o['role_ids']) & {R.get('daily'), R.get('leads')}) for o in q.get('options', []))]
    def opt(title, role, chan, desc, emoji):
        return {'title': title, 'description': desc, 'role_ids': [role], 'channel_ids': [chan] if chan else [], 'emoji_name': emoji}
    head = [opt('Daily results', R['daily'], C.get('daily-results'), 'The scoreboard after each daily close', '📊'),
            opt('Lead changes', R['leads'], C.get('lead-changes'), 'When an AI takes the lead in a race', '👑'),
            opt('Big moments', R['big'], C.get('big-moments'), 'Big wins and losses, new records', '💥'),
            opt('Season news', R['news'], C.get('announcements'), 'Important announcements only', '📢')]
    races = [opt(label, R[k], C.get(ch), f'A ping for every move in {label}', em) for (k, ch, label), em in zip(RACES, '📈🪙🇨🇳🥇🛢️🎛️💱🛡️🏈🔮🎲🎰')]
    prompts = [{'type': 0, 'title': 'Which headlines should ping you?', 'single_select': False, 'required': False, 'in_onboarding': True, 'options': head},
               {'type': 0, 'title': 'Which races do you want every move from?', 'single_select': False, 'required': False, 'in_onboarding': True, 'options': races}]
    for q in prompts:   # keep the old question's id when it exists so Discord updates it in place
        pass
    body = {'prompts': keep + prompts, 'default_channel_ids': ob.get('default_channel_ids') or [], 'enabled': ob.get('enabled', True), 'mode': ob.get('mode', 0)}
    # Discord needs the default channels to include enough channels anyone can talk in; keep the owner's choice and add ours
    want = [C[k] for k in ('welcome-and-rules', 'how-it-works', 'pick-your-alerts', 'announcements', 'daily-results', 'lead-changes', 'big-moments', 'live-trades', 'general', 'who-wins') if C.get(k)]
    body['default_channel_ids'] = list(dict.fromkeys(body['default_channel_ids'] + want))
    r = call('PUT', f'/guilds/{gid}/onboarding', body, reason='PaperTrades.AI alerts')
    print('onboarding questions:', [q['title'] for q in r.get('prompts', [])])


def check():
    gid, gname = guild_id()
    print('server:', gname)
    for c in sorted(call('GET', f'/guilds/{gid}/channels'), key=lambda c: (c.get('position', 0))):
        print(' ', 'category' if c['type'] == 4 else '#', c['name'], c['id'])


if __name__ == '__main__':
    if not TOKEN:
        sys.exit('DISCORD_BOT_TOKEN is not set (GitHub: Settings > Secrets and variables > Actions)')
    {'setup': setup, 'check': check, 'welcome': welcome, 'onboarding': onboarding}[sys.argv[1] if len(sys.argv) > 1 else 'check']()
