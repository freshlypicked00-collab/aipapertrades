"""Instagram highlights for @papertrades.ai (owner, Oct 29). Meta's API cannot create or fill highlights, so Claude sorts every story
into a highlight and the owner adds it in the Instagram app. The to-do list lives in one GitHub issue, "📌 Instagram highlights to
add" (the repo is private; GitHub emails the owner): each story is a checkbox naming its highlight; the owner ticks it once added,
and the next run stops listing it. A new story gets a comment (an email); stories left unticked for a day get one reminder a day.

  python3 ops/highlights.py covers   -> draws the highlight covers into social/highlights/ (1080x1920, icon in the centre circle)
  python3 ops/highlights.py sync     -> reads the ticks, updates the list, comments on new stories (needs gh and GH_TOKEN)

State: ops/src/social.json "highlights": {story id: {"h": highlight, "at": posted, "added": bool}} and "highlights_meta".
"""
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE = 'ops/src/social.json'
TITLE = '📌 Instagram highlights to add'
# the highlights, in the order they should sit on the profile, and which stories go in each
# the first daily stories showed only the races-led count (Day 1's remake only the sports bets); the ten-race versions replace them
SKIP = {'story-daily-2026-10-29', 'story-daily-2026-10-30', 'story-day1-remake-v1',
        # Day 4 and 5 posted again after the missing Day 3 (Nov 2), so the Daily highlight stays in order: the -v2 stories replace these
        'story-daily-2026-11-01', 'story-daily-2026-11-02',
        # replaced by the colourful highlight stories the owner was sent on Oct 30 (and the wrong '16 min' story)
        'story-feature-binance-v1', 'story-feature-grades-v1', 'story-moment-Crypto-202610290114-claude', 'story-moment-Currencies-202610292122-claude', 'story-moment-Metals-202610291346-chatgpt', 'story-moment-Options-202610291346-gemini', 'story-moment-Sports-202610290414-chatgpt', 'story-moment-Sports-202610300216-gemini', 'story-ten-2026-10-29', 'story-ten-2026-10-30'}
HIGHLIGHTS = [('Start here', ('story-intro',)), ('Daily', ('story-daily', 'story-ten-')), ('Lead changes', ('story-moment',)),
              ('Big moments', ('story-feature-binance', 'story-big-')), ('Report cards', ('story-feature-grades', 'story-grades-')),
              ('Meet the AIs', ('story-meet-',))]   # v2 covers (owner, Oct 30: more colour and drawings): ops/hl_covers.py
NAMES = {'Crypto': 'Crypto', 'Stocks': 'Stocks', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy', 'Options': 'Options',
         'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports', 'Predictions': 'Prediction markets'}


def highlight_of(sid):
    for name, prefixes in HIGHLIGHTS:
        if any(sid.startswith(p) for p in prefixes):
            return name
    return None


def describe(sid):
    """A plain description of the story, so the owner can find it in the archive."""
    p = sid.split('-')
    if sid.startswith('story-ten-'):
        return 'Day ' + str((datetime.fromisoformat('-'.join(p[2:5])) - datetime(2026, 10, 28)).days) + ' results story, all ten races'
    if sid.startswith('story-daily-'):
        return 'Daily results story for ' + datetime.fromisoformat('-'.join(p[2:5])).strftime('%b %-d') + ' (the day that closed at 8 p.m. ET the evening before)'
    if sid.startswith('story-moment-'):
        who = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}.get(p[-1], p[-1])
        return f'Lead change story: {who} took the lead in {NAMES.get(p[2], p[2])}'
    if sid.startswith('story-big-'):
        return 'Big moment story: ' + ' '.join(p[2:]).replace('swing', 'a big swing in').replace('bet', 'a big bet by')
    if sid.startswith('story-grades-'):
        return 'Report cards story ' + p[-1] + ' of 3 (' + '-'.join(p[2:5]) + ')'
    if sid.startswith('story-meet-'):
        return 'Meet the AIs story ' + p[-1] + ' of 4, refreshed ' + '-'.join(p[2:5]) + ' (replace last week\'s four)'
    if sid.startswith('story-feature-binance'):
        return 'Big moments story: Gemini sold its crypto 16 minutes before the Binance hack'
    if sid.startswith('story-feature-grades'):
        return 'Report cards story: the AIs grade each other'
    if sid.startswith('story-intro'):
        return '"Start here" story (how the race works)'
    if sid.startswith('story-day1'):
        return 'Day 1 results story'
    return sid


def et(at):
    t = datetime.fromisoformat(at)
    off = -4 if t < datetime(2026, 11, 1, 6, tzinfo=timezone.utc) else -5
    return (t + timedelta(hours=off)).strftime('%b %-d, %-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' ET'


def gh(*args, inp=None):
    r = subprocess.run(['gh', *args], capture_output=True, text=True, input=inp)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:300])
    return r.stdout


def sync():
    repo = os.environ.get('GITHUB_REPOSITORY', 'freshlypicked00-collab/aipapertrades')
    st = json.load(open(STATE))
    hl, meta = st.setdefault('highlights', {}), st.setdefault('highlights_meta', {})
    now = datetime.now(timezone.utc)
    new = []
    for sid, v in sorted(st.get('posted', {}).items(), key=lambda kv: kv[1]['at']):
        h = highlight_of(sid) if sid.startswith('story-') and sid not in SKIP else None
        if h and sid not in hl:
            hl[sid] = {'h': h, 'at': v['at'], 'added': False}
            new.append(sid)
    # the issue: find it (or open it), read the owner's ticks
    num = meta.get('issue')
    if num:
        try:
            body = json.loads(gh('api', f'repos/{repo}/issues/{num}'))['body'] or ''
        except Exception:
            num, body = None, ''
    else:
        body = ''
    for line in body.splitlines():
        line = line.strip()
        if line.lower().startswith('- [x]') and '`' in line:
            sid = line.split('`')[1]
            if sid in hl:
                hl[sid]['added'] = True
    for sid in SKIP:
        hl.pop(sid, None)
    todo = sorted([s for s, v in hl.items() if not v['added']], key=lambda s: hl[s]['at'])
    lines = ['Meta does not let apps add stories to highlights, so Claude sorts each story here and you add it in the Instagram app '
             '(the story → **Highlight** at the bottom → pick the highlight; older stories: open the highlight → ⋯ → Edit highlight → Stories). '
             '**Tick each box once it is added**; the next check-in removes it from the list.', '',
             'Highlights, in this order on the profile: ' + ', '.join(f'**{n}**' for n, _ in HIGHLIGHTS) + ' (covers in `social/highlights/` on the site: '
             + ', '.join(f'https://papertrades.ai/social/highlights/{n.lower().replace(" ", "-")}.jpg' for n, _ in HIGHLIGHTS) + ').', '']
    if todo:
        for name, _ in HIGHLIGHTS:
            mine = [s for s in todo if hl[s]['h'] == name]
            if mine:
                lines.append(f'### Add to **{name}**')
                lines += [f'- [ ] `{s}` · {describe(s)} · posted {et(hl[s]["at"])}' for s in mine]
                lines.append('')
    else:
        lines.append('✅ **Nothing to add right now.** Every story is in its highlight.')
    done = [s for s, v in hl.items() if v['added']]
    if done:
        lines.append(f'<details><summary>Already added ({len(done)})</summary>\n\n' + '\n'.join(f'- [x] `{s}` · {hl[s]["h"]}' for s in sorted(done, key=lambda s: hl[s]['at'])) + '\n</details>')
    text = '\n'.join(lines)
    if not num:
        out = gh('api', '-X', 'POST', f'repos/{repo}/issues', '-f', f'title={TITLE}', '-f', f'body={text}')
        num = json.loads(out)['number']
        meta['issue'] = num
    elif text != body:
        gh('api', '-X', 'PATCH', f'repos/{repo}/issues/{num}', '-f', f'body={text}', '-f', 'state=open')
    # tell the owner: each new story at once, then one reminder a day while anything is left
    if new and meta.get('started'):
        gh('api', '-X', 'POST', f'repos/{repo}/issues/{num}/comments', '-f',
           'body=' + '📌 New story to add:\n' + '\n'.join(f'- **{hl[s]["h"]}** ← {describe(s)} (posted {et(hl[s]["at"])})' for s in new))
        meta['last_ping'] = now.isoformat()
    elif todo and (not meta.get('last_ping') or now - datetime.fromisoformat(meta['last_ping']) > timedelta(hours=24)):
        old = [s for s in todo if now - datetime.fromisoformat(hl[s]['at']) > timedelta(hours=20)]
        if old and meta.get('started'):
            gh('api', '-X', 'POST', f'repos/{repo}/issues/{num}/comments', '-f', f'body=⏰ Reminder: {len(todo)} stor{"y" if len(todo) == 1 else "ies"} still to add to the highlights (list above).')
            meta['last_ping'] = now.isoformat()
    meta['started'] = meta.get('started') or now.isoformat()
    json.dump(st, open(STATE, 'w'), indent=1)
    print(f'highlights: issue #{num}, {len(todo)} to add, {len(new)} new')


def covers():
    import hl_covers   # v2: one bright colour and a hand-drawn icon per highlight
    os.makedirs('social/highlights', exist_ok=True)
    for i, (t, k, c1, c2, w, n) in enumerate(hl_covers.HL):
        print('drew', hl_covers.cover(k, c1, c2, f'social/highlights/{k}.jpg', i + 3))
    return


def covers_v1():
    from PIL import Image, ImageDraw
    import postcard as pc
    os.makedirs('social/highlights', exist_ok=True)
    W, H, cx, cy = 1080, 1920, 540, 960
    for name, _ in HIGHLIGHTS:
        im = Image.new('RGB', (W, H), pc.BG)
        d = ImageDraw.Draw(im)
        for r, a in ((470, 18), (430, 30)):   # a soft amber glow behind the ring
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(int(pc.BG.lstrip('#')[i:i + 2], 16) + a * (k + 1) // 6 for k, i in enumerate((0, 2, 4))))
        d.ellipse([cx - 400, cy - 400, cx + 400, cy + 400], fill=pc.PANEL, outline=pc.AMBER, width=14)
        A = pc.AMBER
        if name == 'Start here':   # a play arrow
            d.polygon([(cx - 120, cy - 190), (cx - 120, cy + 190), (cx + 200, cy)], fill=A)
        elif name == 'Daily':   # three rising bars on a baseline
            for i, (x, h) in enumerate(((-210, 170), (-50, 280), (110, 390))):
                d.rounded_rectangle([cx + x, cy + 200 - h, cx + x + 110, cy + 200], radius=14, fill=A if i == 2 else pc.FG)
            d.line([(cx - 260, cy + 225), (cx + 260, cy + 225)], fill=pc.MUTED, width=10)
        elif name == 'Lead changes':   # a crown
            pts = [(cx - 250, cy + 130), (cx - 270, cy - 150), (cx - 120, cy - 20), (cx, cy - 220), (cx + 120, cy - 20), (cx + 270, cy - 150), (cx + 250, cy + 130)]
            d.polygon(pts, fill=A)
            d.rounded_rectangle([cx - 250, cy + 150, cx + 250, cy + 220], radius=16, fill=A)
            for x, y in ((-270, -150), (0, -220), (270, -150)):
                d.ellipse([cx + x - 34, cy + y - 34, cx + x + 34, cy + y + 34], fill=pc.FG)
        path = f'social/highlights/{name.lower().replace(" ", "-")}.jpg'
        im.save(path, quality=92)
        print('drew', path)


if __name__ == '__main__':
    {'covers': covers, 'sync': sync}[sys.argv[1] if len(sys.argv) > 1 else 'sync']()
