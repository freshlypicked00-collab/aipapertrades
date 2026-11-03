"""Nicole's task bot on Telegram (owner, Nov 2): a private bot, separate from the channel bot, that sends Nicole each
manual-post job with a ✅ Done button, tells the owner when she finishes, and reminds her once if a job waits too long.

Secrets: NICOLE_BOT_TOKEN (from @BotFather). Nobody else can use the bot: it only answers the two chats linked with the
one-time /start codes whose SHA-256 is in ops/nicole/bot.json ("nicole" and "owner"). Everyone else is ignored.

There is no server, so the bot reads Telegram's queue when a GitHub run happens (each send, and the hourly check).
Telegram keeps unread updates for 24 hours, so nothing is lost; a Done tap shows its ✅ within the hour.

Usage:
  python3 ops/nicole_bot.py send ops/nicole/<task>.md   one message per "### " job (or one message), each with ✅ Done
  python3 ops/nicole_bot.py poll                        read taps and messages, link chats, remind, tell the owner
  python3 ops/nicole_bot.py codes                       print two fresh link codes (and save their hashes)
  python3 ops/nicole_bot.py save "message"              commit the state files, merging with any run that saved meanwhile
State: ops/nicole/bot.json (linked chat ids, code hashes, update offset), ops/nicole/tasks.json (every job and when done).
"""
import hashlib, html, json, os, re, secrets, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

TOKEN = os.environ.get('NICOLE_BOT_TOKEN', '').strip()
BOT, TASKS = 'ops/nicole/bot.json', 'ops/nicole/tasks.json'
REMIND_AFTER_H = 4
COPY_LABELS = ('title', 'text', 'caption', 'post', 'comment', 'first comment', 'reply', 'bio', 'description', 'link')
MEDIA = re.compile(r'https://[^\s)<>"]+\.(?:jpg|jpeg|png|gif|mp4)\b', re.I)


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def save(p, x):
    json.dump(x, open(p, 'w'), indent=1, ensure_ascii=False)


def api(method, **params):
    data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}).encode()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/{method}', data=data), timeout=40) as r:
                return json.load(r).get('result')
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors='replace')
            if e.code == 429:
                time.sleep(min(30, int((json.loads(body).get('parameters') or {}).get('retry_after', 3)) + 1)); continue
            print(f'::warning title=Nicole bot::{method} failed: {e.code} {body[:200]}'); return None
        except Exception as e:
            print(f'::warning title=Nicole bot::{method} failed: {e}'); time.sleep(2)
    return None


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


# ---------- markdown task file -> Telegram HTML, one message per job
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)', r'<i>\1</i>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return s


def to_html(md):
    """Headings and **bold** become bold; the text to paste (after a line like "**Title:**" or "**Text:**") goes in a
    copy box so one tap copies it exactly."""
    out, copy = [], None
    def flush():
        nonlocal copy
        if copy is not None:
            body = '\n'.join(copy).strip('\n')
            if body: out.append('<pre>' + html.escape(body, quote=False) + '</pre>')
            copy = None
    for line in md.split('\n'):
        m = re.match(r'^\s*\*\*([^*]+?):\*\*\s*$', line)
        if m and m.group(1).strip().lower() in COPY_LABELS:
            flush(); out.append('<b>' + html.escape(m.group(1).strip()) + '</b> (tap to copy):'); copy = []; continue
        if copy is not None:
            if re.match(r'^\s*(#{1,6}\s|\*\*[^*]+:\*\*|When done\b|---\s*$)', line): flush()
            else: copy.append(line); continue
        mh = re.match(r'^\s*#{1,6}\s+(.*)$', line)
        if mh: out.append('<b>' + inline(mh.group(1)) + '</b>'); continue
        out.append(re.sub(r'^(\s*)[-*]\s+', r'\1• ', inline(line)))
    flush()
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()


def split_jobs(md):
    """(title, intro, [(job title, job markdown)], outro). Jobs are the "### " sections; a file with none is one job."""
    lines = md.strip().split('\n')
    title = re.sub(r'^#+\s*', '', lines[0]).strip() if lines and lines[0].startswith('#') else ''
    body = '\n'.join(lines[1:] if title else lines)
    parts = re.split(r'(?m)^###\s+', body)
    intro, jobs = parts[0].strip(), []
    for p in parts[1:]:
        head, _, rest = p.partition('\n'); jobs.append((head.strip(), rest.strip()))
    outro = ''
    if jobs:   # a closing line after the last job ("When done, send the owner a screenshot...") belongs to every job
        m = re.search(r'(?ms)^\s*(When done\b.*)$', jobs[-1][1])
        if m: outro = m.group(1).strip(); jobs[-1] = (jobs[-1][0], jobs[-1][1][:m.start()].strip())
    else:
        jobs = [(title or 'New task', body.strip())]
    return title, intro, jobs, outro


def chunks(text, n=3900):
    """Telegram allows 4,096 characters per message: split on blank lines, never inside a copy box."""
    if len(text) <= n: return [text]
    out, cur = [], ''
    for para in re.split(r'\n\n(?![^<]*</pre>)', text):
        if cur and len(cur) + 2 + len(para) > n: out.append(cur); cur = para
        else: cur = (cur + '\n\n' + para) if cur else para
    if cur: out.append(cur)
    return out


DONE_KB = lambda tid: {'inline_keyboard': [[{'text': '✅ Done', 'callback_data': 'done:' + tid}]]}


def send_file(path):
    B, T = load(BOT, {}), load(TASKS, [])
    chat = (B.get('chats') or {}).get('nicole')
    if not TOKEN or not chat:
        print('::notice title=Nicole bot::not set up yet (no token or Nicole has not linked); the email copy still goes out'); return 0
    md = open(path).read()
    title, intro, jobs, outro = split_jobs(md)
    if title or intro:
        api('sendMessage', chat_id=chat, parse_mode='HTML', disable_web_page_preview=True,
            text=(('' if re.match(r'^[^\w\s]', title) else '📬 ') + '<b>' + inline(title) + '</b>' if title else '📬 <b>New tasks</b>') + ('\n\n' + to_html(intro) if intro else '')
                 + (f'\n\n{len(jobs)} jobs below. Tap ✅ Done under each one when it’s finished.' if len(jobs) > 1 else ''))
    base = os.path.basename(path).rsplit('.', 1)[0]
    for i, (jt, jm) in enumerate(jobs, 1):
        tid = f'{base[:40]}#{i}'
        if any(t['id'] == tid for t in T): continue   # already sent once
        text = '<b>' + inline(jt) + '</b>\n\n' + to_html(jm) + ('\n\n<i>' + inline(outro) + '</i>' if outro else '')
        parts = chunks(text); mid = None
        for k, part in enumerate(parts):
            r = api('sendMessage', chat_id=chat, parse_mode='HTML', disable_web_page_preview=True, text=part,
                    reply_markup=DONE_KB(tid) if k == len(parts) - 1 else None)
            if r: mid = r['message_id']
        for url in dict.fromkeys(MEDIA.findall(jm)):
            api('sendVideo' if url.lower().endswith('.mp4') else 'sendPhoto', chat_id=chat, **{'video' if url.lower().endswith('.mp4') else 'photo': url})
        T.append({'id': tid, 'file': os.path.basename(path), 'title': re.sub(r'^\d+\.\s*', '', jt)[:120], 'sent_at': now(), 'msg': mid, 'done_at': None, 'reminded': False})
    save(TASKS, T)
    return len(jobs)


def tell_owner(text):
    o = (load(BOT, {}).get('chats') or {}).get('owner')
    if o: api('sendMessage', chat_id=o, parse_mode='HTML', disable_web_page_preview=True, text=text)


def mark_done(T, tid, B):
    t = next((x for x in T if x['id'] == tid), None)
    if not t or t.get('done_at'): return t
    t['done_at'] = now()
    if t.get('msg'):
        api('editMessageReplyMarkup', chat_id=B['chats']['nicole'], message_id=t['msg'],
            reply_markup={'inline_keyboard': [[{'text': '✅ Done, thanks!', 'callback_data': 'noop'}]]})
    left = sum(1 for x in T if not x.get('done_at'))
    tell_owner(f'✅ Nicole finished: <b>{html.escape(t["title"])}</b>' + (f'\n{left} job{"s" if left != 1 else ""} still open.' if left else '\nAll jobs done.'))
    return t


def open_list(T):
    o = [x for x in T if not x.get('done_at')]
    return '\n'.join(f'• {html.escape(x["title"])} (sent {x["sent_at"][5:10]})' for x in o) or 'Nothing open. 🎉'


def poll():
    if not TOKEN: print('::notice title=Nicole bot::no NICOLE_BOT_TOKEN yet'); return
    B, T = load(BOT, {}), load(TASKS, [])
    B.setdefault('chats', {}); B.setdefault('codes', {})
    if not B.get('username'):   # the bot's public @name, for the link-up links (also proves the token works)
        me = api('getMe') or {}
        if me.get('username'): B['username'] = me['username']; print(f'::notice title=Nicole bot::token works: @{me["username"]}')
    # real time (Nov 2): with the Cloudflare webhook on, each update arrives in NICOLE_UPDATE from the Worker; getUpdates is then
    # refused by Telegram (a bot has either a webhook or a queue), so the hourly run only sends reminders
    one = os.environ.get('NICOLE_UPDATE', '').strip()
    if one and one != 'null':
        ups = [json.loads(one)]
    elif B.get('webhook'):
        ups = []
    else:
        ups = api('getUpdates', offset=B.get('offset', 0), timeout=0, allowed_updates=['message', 'callback_query']) or []
    for u in ups:
        if not one: B['offset'] = u['update_id'] + 1
        if 'callback_query' in u:
            q = u['callback_query']; cid = str(q['message']['chat']['id'])
            if cid not in B['chats'].values(): continue
            if q.get('data', '').startswith('done:') and cid == B['chats'].get('nicole'): mark_done(T, q['data'][5:], B)
            api('answerCallbackQuery', callback_query_id=q['id'])   # fails quietly if the tap is old
            continue
        m = u.get('message') or {}; cid = str((m.get('chat') or {}).get('id', '')); txt = (m.get('text') or '').strip()
        if m.get('chat', {}).get('type') != 'private' or not cid: continue
        if txt.startswith('/start'):
            code = txt.split(maxsplit=1)[1].strip() if ' ' in txt else ''
            who = next((k for k, v in B['codes'].items() if code and h(code) == v), None)
            if who:
                B['chats'][who] = cid; B['codes'].pop(who, None)
                api('sendMessage', chat_id=cid, text=('Hi Nicole! 👋 You’re linked. New PaperTrades.AI posting jobs will arrive here. '
                    'Do each one, then tap ✅ Done under it (the tick shows within the hour). Send /tasks any time to see what’s still open. '
                    'Anything you type here goes to the owner.') if who == 'nicole' else 'Linked ✅ You’ll get a message here whenever Nicole finishes a job, and anything she writes to the bot.')
                if who == 'nicole': tell_owner('🔗 Nicole linked the task bot.')
            continue
        if cid not in B['chats'].values(): continue   # strangers are ignored
        if txt.lower() in ('/tasks', 'tasks'):
            api('sendMessage', chat_id=cid, parse_mode='HTML', text='<b>Still open:</b>\n' + open_list(T)); continue
        if cid == B['chats'].get('nicole'):
            rep = (m.get('reply_to_message') or {}).get('message_id')
            t = next((x for x in T if rep and x.get('msg') == rep), None)
            if t and re.fullmatch(r'(?i)\W*(done|finished|posted|ok|✅)\W*', txt or ''): mark_done(T, t['id'], B); continue
            if txt: tell_owner('💬 <b>Nicole:</b> ' + html.escape(txt))
            elif m.get('photo') or m.get('document'):
                o = B['chats'].get('owner')
                if o: api('forwardMessage', chat_id=o, from_chat_id=cid, message_id=m['message_id'])
    # one reminder for a job left open too long
    nic = B['chats'].get('nicole')
    for t in T:
        if nic and not t.get('done_at') and not t.get('reminded'):
            age = (datetime.now(timezone.utc) - datetime.strptime(t['sent_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if age >= REMIND_AFTER_H:
                api('sendMessage', chat_id=nic, reply_to_message_id=t.get('msg'), allow_sending_without_reply=True,
                    text='⏰ Friendly reminder: this one is still open. Tap ✅ Done when it’s finished.'); t['reminded'] = True
    save(BOT, B); save(TASKS, T)


def webhook(url):
    """Turn real-time on (url = the Cloudflare Worker's address) or off (url = 'off'). The secret header is derived from the
    token the same way as in ops/nicole/worker.js, so no extra password is needed."""
    B = load(BOT, {})
    if url == 'off':
        api('deleteWebhook'); B.pop('webhook', None); save(BOT, B); print('webhook off: back to the hourly queue'); return
    sec = hashlib.sha256(('webhook:' + TOKEN).encode()).hexdigest()[:48]
    r = api('setWebhook', url=url, secret_token=sec, allowed_updates=['message', 'callback_query'], drop_pending_updates=False)
    info = api('getWebhookInfo') or {}
    print('setWebhook:', r, '| now:', info.get('url'), '| pending:', info.get('pending_update_count'), '| last error:', info.get('last_error_message'))
    if r: B['webhook'] = url; save(BOT, B); tell_owner('⚡ NINI\'s bot is now real time: her ✅ Done taps reach you within about a minute.')


def merge_save(msg):
    """Commit any code changes first: this resets the working copy to main. Save the bot's state to main without losing anything another run wrote at the same moment (Nov 2): two runs (a task
    send and the hourly check) can overlap, and a plain rebase either conflicts or drops one side. So: keep this run's files,
    reset to the newest main, merge the two versions field by field, commit, push; retry on a race."""
    import subprocess
    run = lambda *a: subprocess.run(list(a), capture_output=True, text=True)
    SENT = 'ops/nicole/sent.json'
    mine = {p: load(p, None) for p in (BOT, TASKS, SENT)}
    for attempt in range(6):
        run('git', 'fetch', '-q', 'origin', 'main'); run('git', 'reset', '-q', '--hard', 'origin/main')
        theirs = {p: load(p, None) for p in (BOT, TASKS, SENT)}
        # tasks: one record per id; a Done or a reminder on either side wins
        T = {t['id']: dict(t) for t in (theirs[TASKS] or [])}
        for t in mine[TASKS] or []:
            o = T.get(t['id'])
            if not o: T[t['id']] = dict(t); continue
            dn = [x for x in (o.get('done_at'), t.get('done_at')) if x]
            o['done_at'] = min(dn) if dn else None
            o['reminded'] = bool(o.get('reminded') or t.get('reminded'))
            o['msg'] = o.get('msg') or t.get('msg')
        order = [t['id'] for t in (theirs[TASKS] or [])] + [t['id'] for t in (mine[TASKS] or []) if t['id'] not in {x['id'] for x in (theirs[TASKS] or [])}]
        if mine[TASKS] is not None or theirs[TASKS] is not None: save(TASKS, [T[i] for i in order])
        # bot: linked chats from both; a code is dropped once its chat is linked or this run used it; the newest offset
        a, b = theirs[BOT] or {}, mine[BOT] or {}
        if a or b:
            chats = {**(a.get('chats') or {}), **(b.get('chats') or {})}
            chats = {k: v for k, v in chats.items() if not ((b.get('codes_at') or {}).get(k, '') > (a.get('codes_at') or {}).get(k, '') and k not in (b.get('chats') or {}))}
            # per role, the newest code wins (codes_at); a used code's role is linked, so it drops out
            ca, cb, ta, tb = a.get('codes') or {}, b.get('codes') or {}, a.get('codes_at') or {}, b.get('codes_at') or {}
            codes_ = {k: (cb[k] if k in cb and (k not in ca or tb.get(k, '') > ta.get(k, '')) else ca[k]) for k in set(ca) | set(cb)}
            codes_ = {k: v for k, v in codes_.items() if k not in chats}
            save(BOT, {**a, **b, 'chats': chats, 'codes': codes_, 'codes_at': {**ta, **{k: v for k, v in tb.items() if v > ta.get(k, '')}}, 'offset': max(a.get('offset', 0), b.get('offset', 0))})
        # sent log: every entry from both, in order, once
        if mine[SENT] is not None or theirs[SENT] is not None:
            seen, out = set(), []
            for e in (theirs[SENT] or []) + (mine[SENT] or []):
                k = json.dumps(e, sort_keys=True)
                if k not in seen: seen.add(k); out.append(e)
            save(SENT, out)
        run('git', 'add', BOT, TASKS, SENT)
        if run('git', 'diff', '--cached', '--quiet').returncode == 0: print('nothing to save'); return
        run('git', 'commit', '-qm', msg)
        if run('git', 'push', '-q', 'origin', 'HEAD:main').returncode == 0: print('saved'); return
        time.sleep(4 + 4 * attempt)
    print('::warning title=Nicole bot::could not save the bot state after 6 tries')


def codes():
    B = load(BOT, {}); B.setdefault('codes', {}); out = {}
    roles = [x for x in sys.argv[2:] if x in ('nicole', 'owner')] or ['nicole', 'owner']   # codes nicole: relink only her
    for who in roles:
        c = secrets.token_urlsafe(9).replace('-', 'x').replace('_', 'y'); B['codes'][who] = h(c); out[who] = c; B.setdefault('codes_at', {})[who] = now()
        (B.get('chats') or {}).pop(who, None)   # a new code unlinks the old chat at once; it links again when the code is used
    save(BOT, B); print(json.dumps(out))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'poll'
    if cmd == 'send': print(send_file(sys.argv[2]), 'jobs')
    elif cmd == 'codes': codes()
    elif cmd == 'webhook': webhook(sys.argv[2])
    elif cmd == 'save': merge_save(sys.argv[2] if len(sys.argv) > 2 else 'Nicole bot: state')
    else: poll()
