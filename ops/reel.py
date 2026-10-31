"""A 16-second vertical "race replay" video of one race (owner, Oct 30: grow the socials; Reels reach people who don't follow yet).

Draws the three AIs' profit in one race over time, from the same data as the site (data.json: Claude's "history",
Gemini's and ChatGPT's "rivals_history"), in the posts' look (ops/postcard.py colours and IBM Plex fonts). One race
only, never totals across races. No music: add a sound in the Instagram app when posting by hand.

  python3 ops/reel.py                 -> picks the race with the widest gap between first and last, writes social/reels/
  python3 ops/reel.py --race Options  -> that race
Output: social/reels/replay-<race>-<date>.mp4 (1080x1920, 30 fps, H.264, no audio) and a cover .jpg.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc
from postcard import AIS, AMBER, BG, FG, LINE, MUTED, PANEL, UP, DOWN, LABEL, ORDER, font

W, H, FPS = 1080, 1920, 30
X0, X1, Y0, Y1 = 90, 930, 540, 1150          # the chart box, inside Instagram's Reels safe area (top bar, right-hand buttons, caption)
INTRO, DRAW, HOLD, OUTRO = 2.2, 9.0, 1.3, 3.5   # seconds
NY = ZoneInfo('America/New_York')
START = datetime(2026, 10, 28, 17, 30, tzinfo=timezone.utc)   # the race started Oct 28 (fresh C$100,000)


def ts(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def series(d, race):
    base = 100000.0
    out = {'claude': [(ts(h['at']), h['value'] - base) for h in d.get('history', []) if h.get('portfolio') == race]}
    for m in ('gemini', 'chatgpt'):
        out[m] = [(ts(h['at']), h['value'] - base) for h in d.get('rivals_history', []) if h.get('model') == m and h.get('experiment') == race]
    for k in out:
        out[k] = sorted(p for p in out[k] if p[0] >= START)
        if not out[k] or out[k][0][0] > START:
            out[k].insert(0, (START, 0.0))
    return out


def value_at(s, t):
    """Step value: the last check-in at or before t."""
    v = s[0][1]
    for at, x in s:
        if at > t:
            break
        v = x
    return v


def pick_race(d):
    best, gap = None, -1
    for r in ORDER:
        if r == 'China':   # US$ race; keep the replay in one currency
            continue
        s = series(d, r)
        last = [x[-1][1] for x in s.values()]
        if max(last) - min(last) > gap:
            best, gap = r, max(last) - min(last)
    return best


def money(x):
    if abs(x) < 0.5:
        return 'C$0'
    return ('+' if x > 0 else '−') + 'C$' + f'{abs(x):,.0f}'


def ease(t):
    return 1 - (1 - t) ** 3


class Frame:
    def __init__(self, glow):
        self.im = glow.copy()
        self.d = ImageDraw.Draw(self.im)

    def text(self, xy, s, f, fill, anchor='la'):
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor)
        b = self.d.textbbox(xy, s, font=f, anchor=anchor)
        if b[0] < 40 or b[2] > W - 40:
            raise pc.QualityError(f'text out of frame: {s!r}')


def background(color):
    im = Image.new('RGBA', (W, H), BG)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rgb = tuple(int(color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    ImageDraw.Draw(layer).ellipse([W - 560, 380, W + 260, 1200], fill=rgb + (44,))
    return Image.alpha_composite(im, layer.filter(ImageFilter.GaussianBlur(150))).convert('RGB')


def header(f, race, day):
    icon = os.path.join(os.path.dirname(pc.HERE), 'icon-512.png')
    if os.path.exists(icon):
        ic = Image.open(icon).convert('RGBA').resize((64, 64), Image.LANCZOS)
        f.im.paste(ic, (X0, 200), ic)
    f.text((X0 + 84, 232), 'PAPERTRADES.AI', font('mono', 'SemiBold', 38), FG, 'lm')
    f.text((W - 150, 232), f'DAY {day} OF 32', font('mono', 'Medium', 28), MUTED, 'rm')
    f.d.line([(X0, 300), (W - 150, 300)], fill=LINE, width=3)
    f.text((X0, 360), 'RACE REPLAY · ' + LABEL[race].upper(), font('mono', 'SemiBold', 30), UP, 'lm')


def render(race, out_dir):
    d = json.load(open('data.json'))
    S = series(d, race)
    now = max(p[0] for s in S.values() for p in s)
    day = pc.day_of(now)
    finals = sorted(((k, S[k][-1][1]) for k in S), key=lambda x: -x[1])
    leader = finals[0][0] if finals[0][1] - finals[1][1] >= 0.5 else None
    lo = min(min(v for _, v in s) for s in S.values()); hi = max(max(v for _, v in s) for s in S.values())
    pad = max(150.0, (hi - lo) * 0.12); lo -= pad; hi += pad
    t0, t1 = START.timestamp(), now.timestamp()
    X = lambda t: X0 + (t.timestamp() - t0) / (t1 - t0) * (X1 - X0)
    Y = lambda v: Y1 - (v - lo) / (hi - lo) * (Y1 - Y0)
    glow = background(AIS[leader][1] if leader else AMBER)
    tmp = tempfile.mkdtemp()
    n = 0

    def save(fr):
        nonlocal n
        fr.im.save(os.path.join(tmp, f'{n:05d}.png')); n += 1

    big = font('sans', 'Bold', 128); mid = font('sans', 'Bold', 76); small = font('sans', 'Regular', 40)
    # 1. intro: the race, the three names
    for i in range(int(INTRO * FPS)):
        fr = Frame(glow); header(fr, race, day)
        a = min(1.0, i / (0.5 * FPS))
        y = 500
        fr.text((X0, y), 'Who is winning', mid, FG); y += 92
        fr.text((X0, y), LABEL[race] + '?', mid, AMBER); y += 170
        for k in ('claude', 'gemini', 'chatgpt'):
            if i >= (0.25 + 0.3 * list(AIS).index(k)) * FPS:
                fr.text((X0, y), AIS[k][0], big, AIS[k][1])
            y += 150
        fr.text((X0, 1420), 'C$100,000 of pretend money each.', small, MUTED)
        fr.text((X0, 1474), 'Real prices. Since Oct 28.', small, MUTED)
        if a < 1:
            fr.im = Image.blend(Image.new('RGB', (W, H), BG), fr.im, a)
        save(fr)
    # 2. the chart, drawn left to right
    lab = font('sans', 'Bold', 40); val = font('mono', 'SemiBold', 34); tick = font('mono', 'Medium', 24)
    total = int((DRAW + HOLD) * FPS)
    for i in range(total):
        p = min(1.0, ease(i / (DRAW * FPS)))
        t = datetime.fromtimestamp(t0 + p * (t1 - t0), tz=timezone.utc)
        fr = Frame(glow); header(fr, race, day)
        fr.text((X0, 450), t.astimezone(NY).strftime('%a %b %-d · %-I:%M %p ET'), font('sans', 'SemiBold', 54), FG, 'lm')
        # zero line and grid
        for gv in sorted({0.0, lo + pad, hi - pad}):
            gy = Y(gv)
            fr.d.line([(X0, gy), (X1, gy)], fill=('#5a5446' if gv == 0 else LINE), width=(3 if gv == 0 else 2))
            fr.text((X1, gy - 22), 'start' if gv == 0 else money(gv), tick, MUTED, 'rs')
        heads = []
        for k in ('chatgpt', 'gemini', 'claude'):   # Claude drawn last, on top
            pts, last = [], None
            for at, v in S[k]:
                if at > t:
                    break
                if last is not None:
                    pts.append((X(at), Y(last)))   # step: hold the value until the next check-in
                pts.append((X(at), Y(v))); last = v
            pts.append((X(t), Y(last)))
            col = AIS[k][1]
            if len(pts) > 1:
                fr.d.line(pts, fill=col, width=9, joint='curve')
            hx, hy = pts[-1]
            fr.d.ellipse([hx - 13, hy - 13, hx + 13, hy + 13], fill=col)
            heads.append((hy, k, last))
        # labels under the chart, ranked live
        rank = sorted(heads, key=lambda h: -h[2])
        y = Y1 + 50
        for pos, (_, k, v) in enumerate(rank):
            fr.d.rounded_rectangle([X0, y, W - 150, y + 96], radius=20, fill=PANEL, outline=LINE, width=2)
            fr.text((X0 + 30, y + 48), f'{pos + 1}', font('mono', 'Bold', 40), MUTED, 'lm')
            fr.text((X0 + 90, y + 48), AIS[k][0], lab, AIS[k][1], 'lm')
            fr.text((W - 180, y + 48), money(v), val, UP if v > 0.5 else DOWN if v < -0.5 else FG, 'rm')
            y += 112
        save(fr)
    # 3. outro: who leads this race, and where to follow
    for i in range(int(OUTRO * FPS)):
        fr = Frame(glow); header(fr, race, day)
        y = 470
        if leader:
            fr.text((X0, y), 'Leading ' + LABEL[race] + ' after day ' + str(day) + ':', font('sans', 'SemiBold', 52), MUTED); y += 90
            fr.text((X0, y), AIS[leader][0], font('sans', 'Bold', 170), AIS[leader][1]); y += 200
            fr.text((X0, y), money(finals[0][1]) + ' in this race', font('mono', 'SemiBold', 60), UP if finals[0][1] > 0 else DOWN); y += 150
        else:
            fr.text((X0, y), 'Still level in ' + LABEL[race], mid, FG); y += 240
        fr.text((X0, y), 'Ten races. One winner', mid, FG); y += 92
        fr.text((X0, y), 'on Nov 28.', mid, AMBER); y += 170
        fr.text((X0, y), 'Every trade and why, live:', small, MUTED); y += 70
        fr.text((X0, y), 'papertrades.ai', font('mono', 'SemiBold', 64), FG); y += 100
        fr.text((X0, y), '@PaperTradesAI on X and Telegram', small, MUTED)
        fr.text((X0, y + 70), 'Pretend money · real prices · not advice', font('sans', 'Regular', 34), MUTED)
        save(fr)
    os.makedirs(out_dir, exist_ok=True)
    stem = f'{out_dir}/replay-{race}-{now.astimezone(NY):%Y-%m-%d}'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%05d.png'),
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', stem + '.mp4']
    subprocess.run(cmd, check=True)
    shutil.copy(os.path.join(tmp, f'{int((INTRO + DRAW + HOLD) * FPS) - 1:05d}.png'), '/tmp/reel-cover.png')
    Image.open('/tmp/reel-cover.png').convert('RGB').save(stem + '-cover.jpg', 'JPEG', quality=92)
    shutil.rmtree(tmp)
    return stem + '.mp4', {k: round(v, 2) for k, v in finals}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--race')
    ap.add_argument('--out', default='social/reels')
    a = ap.parse_args()
    d = json.load(open('data.json'))
    race = a.race or pick_race(d)
    if race not in LABEL:
        sys.exit(f'unknown race {race}')
    path, finals = render(race, a.out)
    print(path, finals)
