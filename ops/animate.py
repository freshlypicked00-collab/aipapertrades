"""Animated GIF versions of the post cards (owner, Oct 31: "instead of still images gifs will be used going forward").

How it works: the normal card function (sharecard / racecard) draws the card exactly as today, while every drawing step it makes is
recorded. The steps are then replayed over time: the colour bar sweeps in, the robot pops in, lines slide up in reading order,
amounts count up, the AI's own words type themselves out, and a win ends with a burst (a loss with a short shake). Nothing new is
written or looked up: the GIF shows the same words and numbers as the still card, so it passes the same fact checks.

  python3 ops/animate.py samples   -> social/gif-samples/*.gif from real recent posts
"""
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

FPS = 20
INTRO = 0.75   # the '> ' terminal prompt before the card builds (ChatGPT, Oct 31)
MONEY = re.compile(r'^([+−\-]?)(C\$|US\$|¥)([\d,]+(?:\.\d+)?)(.*)$')


# ---------------------------------------------------------------- recording
class _Rec:
    def __init__(self):
        self.ops, self.saved, self.alias = [], None, {}

    def root(self, i):
        # Nov 19: the record identifies images by id(), and Python reuses the id of an image that was freed. A cropped copy can get the
        # id of the image it was cropped from; two alias links then point at each other and this loop never ended. That stopped every
        # Gemini and ChatGPT check-in from Nov 18, 10:14 p.m. ET to Nov 19, 6 a.m. ET (each run was killed at the 30-minute job limit
        # before anything was saved). A loop now raises, so that one card goes out as a still. (Keeping every image alive instead was
        # tried the same morning and taken back: the animation came out EMPTY, because the recorder also relies on a card's final
        # image taking over the id of the image it replaces. The recorder needs a real rewrite before that can change.)
        seen = set()
        while i in self.alias:
            if i in seen:
                raise RuntimeError('animate: alias loop')
            seen.add(i)
            i = self.alias[i]
        return i


def record(fn, *a, **k):
    """Run a card function; return (its result, [(target_id, kind, args, kwargs)], id of the image it saved)."""
    rec = _Rec()
    D, I = ImageDraw.ImageDraw, Image.Image
    orig = {m: getattr(D, m) for m in ('text', 'rectangle', 'rounded_rectangle', 'line', 'ellipse', 'polygon', 'pieslice', 'arc', 'chord')}
    o_paste, o_save, o_crop = I.paste, I.save, I.crop

    def wrap(name):
        f = orig[name]

        def w(self, *aa, **kk):
            rec.ops.append((id(getattr(self, '_image', None)), name, aa, kk))
            return f(self, *aa, **kk)
        return w
    for m in orig:
        setattr(D, m, wrap(m))

    def paste(self, im, box=None, mask=None):
        src = im.copy() if isinstance(im, Image.Image) else im
        msk = mask.copy() if isinstance(mask, Image.Image) else mask
        rec.ops.append((id(self), 'paste', (src, box, msk), {}))
        return o_paste(self, im, box, mask)

    def save(self, *aa, **kk):
        rec.saved = (id(self), self.copy())
        return o_save(self, *aa, **kk)
    def crop(self, box=None):
        out = o_crop(self, box)
        if box is None or (box[0] == 0 and box[1] == 0):   # same origin: the card trimmed to fit
            if id(out) != id(self):
                rec.alias[id(out)] = id(self)
        return out
    I.paste, I.save, I.crop = paste, save, crop
    try:
        out = fn(*a, **k)
    finally:
        for m, f in orig.items():
            setattr(D, m, f)
        I.paste, I.save, I.crop = o_paste, o_save, o_crop
    return out, rec


# ---------------------------------------------------------------- elements
class El:
    def __init__(self, kind, sprite, pos, info):
        self.kind, self.sprite, self.pos, self.info = kind, sprite, pos, info
        self.y = pos[1]; self.t0 = 0.0; self.fx = 'fade'


def _sprite(size, kind, args, kwargs):
    c = Image.new('RGBA', size, (0, 0, 0, 0))
    if kind == 'paste':
        src, box, msk = args
        if isinstance(src, Image.Image):
            if src.mode != 'RGBA' and msk is None:
                src = src.convert('RGBA')
            c.paste(src, box, msk if msk is not None else (src if src.mode == 'RGBA' else None))
        else:
            return None, None
    else:
        getattr(ImageDraw.Draw(c), kind)(*args, **kwargs)
    bb = c.getbbox()
    if not bb:
        return None, None
    return c.crop(bb), (bb[0], bb[1])


def elements(rec):
    target, final = rec.saved
    W, H = final.size
    bg = final.convert('RGB').getpixel((3, H // 2))
    els = []
    root = rec.root(target)
    for tid, kind, a, k in rec.ops:
        if rec.root(tid) != root:
            continue
        if kind == 'rectangle' and a and _covers(a[0], W, H):
            continue   # the background fill
        sp, pos = _sprite((W, H), kind, a, k)
        if sp is None:
            continue
        info = {}
        if kind == 'text':
            txt = a[1] if len(a) > 1 else k.get('text', '')
            f = k.get('font'); info = {'text': str(txt), 'size': getattr(f, 'size', 20), 'font': f, 'fill': k.get('fill'), 'xy': a[0], 'anchor': k.get('anchor')}
        els.append(El(kind, sp, pos, info))
    return els, final.convert('RGB'), bg


def _covers(box, W, H):
    try:
        x0, y0, x1, y1 = [float(v) for v in (box if len(box) == 4 else (*box[0], *box[1]))]
        return x0 <= 0 and y0 <= 0 and x1 >= W - 1 and y1 >= H - 1
    except Exception:
        return False


# ---------------------------------------------------------------- choreography
def plan(els, W, H):
    """Give each element a start time and an effect, in reading order."""
    t = 0.0
    rows = sorted(els, key=lambda e: (e.y, e.pos[0]))
    last_y, slot = None, 0.15 + INTRO
    for e in rows:
        w, h = e.sprite.size
        if e.kind in ('rectangle', 'rounded_rectangle') and e.y <= 2 and h <= 24 and w > W * 0.6:
            e.fx, e.t0 = 'wipe', 0.0; continue
        if e.kind == 'paste':
            e.fx, e.t0 = 'pop', 0.25; continue
        if e.kind == 'line' and e.sprite.width > 200 and e.sprite.height > 40:
            e.fx = 'draw'   # a price line draws itself in, left to right (all three agreed, Oct 31)
        if e.y > H - 175 and e.kind == 'text':
            e.fx = 'fade'; e.t0 = None; continue   # the footer: after everything else
        if last_y is None or abs(e.y - last_y) > 14:
            slot += 0.09 if (last_y is None or e.y - last_y < 120) else 0.16
            last_y = e.y
        e.t0 = slot
        if e.kind == 'text':
            m = MONEY.match(e.info['text'].strip())
            if m and e.info['size'] >= 18:
                e.fx = 'count'; e.info['m'] = m
                if e.info['size'] >= 100:
                    e.info['hero'] = True
            elif e.info['size'] >= 70:
                e.fx = 'rise'; e.info['headline'] = True
            elif e.info['text'].lstrip().startswith(('“', '"')) or (34 <= e.info['size'] <= 52 and len(e.info['text']) >= 28 and e.pos[0] > 95):
                e.fx = 'type'
            else:
                e.fx = 'rise'
    # typed lines follow one another; everything after them waits its turn
    typed = sum(len(x.info['text']) for x in els if x.fx == 'type')
    cps = max(55.0, typed / 2.5)
    cur = 0.0
    for e in sorted([x for x in els if x.t0 is not None], key=lambda x: (x.y, x.pos[0])):
        if e.fx in ('wipe', 'pop'):
            continue
        e.t0 = max(e.t0, cur)
        if e.fx == 'type':
            e.dur = max(0.2, len(e.info['text']) / cps); cur = e.t0 + e.dur
        elif e.fx == 'count':
            e.dur = 1.1 if e.info.get('hero') else 0.6; cur = max(cur, e.t0 + (0.45 if e.info.get('hero') else 0.05))
        elif e.fx == 'draw':
            e.dur = 1.0; cur = max(cur, e.t0 + 0.3)
        else:
            e.dur = 0.35
    end = max([x.t0 + getattr(x, 'dur', 0.35) for x in els if x.t0 is not None] + [0.8])
    for e in els:
        if e.t0 is None:
            e.t0, e.dur = end + 0.05, 0.4
    return end + 0.5


def ease(u):
    u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3


def back(u):
    u = max(0.0, min(1.0, u)); c = 1.7
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def _fmt_money(m, frac):
    sign, cur, num, rest = m.groups()
    v = float(num.replace(',', '')) * frac
    dec = num.split('.')[1] if '.' in num else ''
    s = f'{v:,.{len(dec)}f}'
    return f'{sign}{cur}{s}{rest}'


def _text_sprite(e, txt, W, H):
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    kw = {'font': e.info['font'], 'fill': e.info['fill']}
    if e.info.get('anchor'):
        kw['anchor'] = e.info['anchor']
    ImageDraw.Draw(c).text(e.info['xy'], txt, **kw)
    bb = c.getbbox()
    return (c.crop(bb), (bb[0], bb[1])) if bb else (None, None)


def _cursor(im, x, y, h, col):
    ImageDraw.Draw(im).rectangle([x + 6, y, x + 6 + max(8, int(h * 0.5)), y + h], fill=col)


_SCAN = {}
def _scanline(im, t, W, H):
    """A very faint band sweeping top to bottom every 3.2 s (Gemini: the retro-terminal feel)."""
    if W not in _SCAN:
        b = Image.new('RGBA', (W, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(b)
        for j in range(120):
            d.line([(0, j), (W, j)], fill=(255, 255, 255, int(14 * math.sin(math.pi * j / 119))))
        _SCAN[W] = b
    y = int(((t % 3.2) / 3.2) * (H + 240)) - 120
    im.alpha_composite(_SCAN[W], (0, max(-119, min(H - 1, y))) if y >= 0 else (0, 0), (0, 0 if y >= 0 else -y, W, 120))


def _prompt(im, t, head, W):
    """'> gemini wins a bet' typed like a terminal command before the card builds (ChatGPT)."""
    if head is None or t > INTRO + 0.15:
        return
    txt = '> ' + head.info['text'].lower()
    n = int(len(txt) * min(1.0, t / (INTRO * 0.75)))
    f = _mono(36)
    a = 1.0 if t <= INTRO else max(0.0, 1 - (t - INTRO) / 0.15)
    d = ImageDraw.Draw(im, 'RGBA'); x, y = head.pos[0], head.pos[1] + 10
    col = (255, 176, 0, int(255 * a))
    d.text((x, y), txt[:n], font=f, fill=col)
    if int(t * 4) % 2 == 0 or n < len(txt):
        w = d.textlength(txt[:n], font=f); d.rectangle([x + w + 6, y + 4, x + w + 24, y + 40], fill=col)


_MONO = {}
def _mono(px):
    if px not in _MONO:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import postcard
        _MONO[px] = postcard.font('mono', 'SemiBold', px)
    return _MONO[px]


def frame(els, bg, W, H, t, total, win=None, hero=None):
    im = Image.new('RGBA', (W, H), bg + (255,) if len(bg) == 3 else bg)
    last_typed = None
    for e in els:
        u = (t - e.t0) / max(0.01, getattr(e, 'dur', 0.35))
        if u <= 0:
            continue
        sp, (x, y) = e.sprite, e.pos
        a = 1.0
        if e.fx == 'wipe':
            w = int(sp.width * ease(u * 1.0))
            if w <= 0:
                continue
            sp = sp.crop((0, 0, w, sp.height))
        elif e.fx == 'pop':
            s = back(u) if u < 1 else 1.0
            bob = 0 if u < 1 else 4 * math.sin((t - e.t0) * 3.2)
            if s <= 0.02:
                continue
            sp2 = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.BILINEAR)
            x += (sp.width - sp2.width) / 2; y += (sp.height - sp2.height) / 2 + bob; sp = sp2
        elif e.fx == 'rise':
            a = ease(u); y += (1 - ease(u)) * 26
        elif e.fx == 'fade':
            a = ease(u)
        elif e.fx == 'draw':
            w = int(sp.width * ease(u))
            if w <= 0:
                continue
            sp = sp.crop((0, 0, w, sp.height))
        elif e.fx == 'type':
            n = int(len(e.info['text']) * min(1.0, u))
            if n <= 0:
                continue
            sp, pos = _text_sprite(e, e.info['text'][:n], W, H)
            if sp is None:
                continue
            x, y = pos
            last_typed = (e, x + sp.width, y, sp.height, u < 1)
        elif e.fx == 'count':
            frac = ease(u) if u < 1 else 1.0
            sp, pos = _text_sprite(e, _fmt_money(e.info['m'], frac), W, H)
            if sp is None:
                continue
            x, y = pos
            a = min(1.0, u * 4)
        if a < 1:
            sp = sp.copy(); sp.putalpha(sp.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(sp, (int(round(x)), int(round(y))))
    # a blinking block cursor leads the typing and keeps blinking at the end of the quote (Gemini)
    if last_typed:
        e_, x_, y_, h_, typing = last_typed
        col = tuple(e_.info['fill'][:3]) if isinstance(e_.info['fill'], tuple) else (242, 233, 216)
        if typing or int(t * 2) % 2 == 0:
            _cursor(im, x_, y_, h_, col)
    _prompt(im, t, next((e for e in els if e.info.get('headline')), None), W)
    if t < total - 6.0:   # the faint sweep runs while the card builds, then stops so the long reading hold stays still and the file small
        _scanline(im, t, W, H)
    # the payoff: a burst of sparks around a win, a short shake on a loss
    if hero is not None:
        hu = t - (hero.t0 + hero.dur)
        if win and 0 <= hu <= 1.2:
            d = ImageDraw.Draw(im, 'RGBA'); r = random.Random(7)
            cx, cy = hero.pos[0] + hero.sprite.width / 2, hero.pos[1] + hero.sprite.height / 2
            col = hero.info['fill'] if isinstance(hero.info['fill'], tuple) else (61, 220, 132)
            for k in range(28):
                ang = r.uniform(0, 2 * math.pi); sp_ = r.uniform(180, 420); rr = ease(hu / 1.2) * sp_
                px, py = cx + math.cos(ang) * (hero.sprite.width / 2 + rr * 0.6), cy + math.sin(ang) * (hero.sprite.height / 2 + rr * 0.35)
                al = int(255 * (1 - hu / 1.2)); s = 5
                d.ellipse([px - s, py - s, px + s, py + s], fill=tuple(col[:3]) + (al,))
        if win is False and 0 <= hu <= 0.35:
            im = im.transform(im.size, Image.AFFINE, (1, 0, 9 * math.sin(hu * 60), 0, 1, 0), fillcolor=bg + (255,))
    return im.convert('RGB')


def make_gif(card_fn, args, kwargs, out, width=720, hold=None):
    """Draw the card (still image too), then the GIF. Returns the GIF path or None."""
    res, rec = record(card_fn, *args, **kwargs)
    if not rec.saved:
        return None
    els, final, bg = elements(rec)
    W, H = final.size
    if hold is None:   # time to read before it loops: longer when there is a quote to read (Gemini and ChatGPT)
        hold = 9.0 if any(e.fx == 'type' for e in els) else 6.5   # owner, Nov 1: more time to read everything (was 4.5 / 3.0)
    total = plan(els, W, H) + hold
    heroes = [e for e in els if e.fx == 'count' and e.info.get('hero')]
    hero = heroes[0] if heroes else None
    win = None
    if hero:
        win = hero.info['m'].group(1) in ('+',) or (hero.info['m'].group(1) == '' and False)
        if hero.info['m'].group(1) in ('−', '-'):
            win = False
        elif hero.info['m'].group(1) != '+':
            win = None
    tmp = tempfile.mkdtemp()
    n = int(total * FPS)
    for i in range(n):
        frame(els, bg, W, H, i / FPS, total, win, hero).save(os.path.join(tmp, f'{i:04d}.png'))
    final.save(os.path.join(tmp, 'final.png'))
    h = int(H * width / W) // 2 * 2
    vf = f'fps={FPS},scale={width}:{h}:flags=lanczos,split[a][b];[a]palettegen=max_colors=200:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle'
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    r = subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%04d.png'), '-vf', vf, '-loop', '0', out], stdin=subprocess.DEVNULL, timeout=120)   # Nov 19: one encode can never hold a check-in
    shutil.rmtree(tmp)
    return out if r.returncode == 0 else None


def make_gif_mpl(card_fn, args, kwargs, out, width=960, hold=9.0):   # owner, Nov 1: more time to read (was 4.5)
    """For cards drawn with matplotlib: rows light up from the top one after another, amounts count up."""
    import io
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    cap = {}
    o_save, o_close = Figure.savefig, plt.close

    def savefig(self, *a, **k):
        cap['fig'], cap['kw'] = self, {kk: v for kk, v in k.items() if kk in ('dpi', 'facecolor')}
        return o_save(self, *a, **k)
    Figure.savefig, plt.close = savefig, (lambda *a, **k: None)
    try:
        card_fn(*args, **kwargs)
    finally:
        Figure.savefig, plt.close = o_save, o_close
    fig = cap.get('fig')
    if fig is None:
        return None
    dpi = cap['kw'].get('dpi', fig.dpi); fig.set_dpi(dpi)
    fig.canvas.draw(); rend = fig.canvas.get_renderer(); Hpx = fig.bbox.height
    arts = []
    for ax in fig.axes:
        arts += list(ax.texts) + list(ax.patches) + list(ax.lines)
    arts += list(fig.texts)
    rows = []
    for a in arts:
        try:
            bb = a.get_window_extent(rend)
        except Exception:
            continue
        y = Hpx - bb.y1
        txt = a.get_text() if hasattr(a, 'get_text') else None
        rows.append({'a': a, 'y': y, 'x': bb.x0, 'txt': txt, 'm': MONEY.match(txt.strip()) if txt else None, 'alpha': a.get_alpha() if a.get_alpha() is not None else 1.0})
    ys = sorted(set(round(r['y'] / 22) for r in rows))
    slot = {v: 0.2 + 0.11 * i for i, v in enumerate(ys)}
    for r in rows:
        r['t0'] = slot[round(r['y'] / 22)] + (0.0 if r['txt'] is None else 0.03); r['dur'] = 0.3
    total = max(r['t0'] + r['dur'] for r in rows) + 0.4 + hold
    tmp = tempfile.mkdtemp(); n = int(total * FPS)
    for i in range(n):
        t = i / FPS
        for r in rows:
            u = (t - r['t0']) / r['dur']; a = max(0.0, min(1.0, u))
            r['a'].set_alpha(r['alpha'] * ease(a) if a < 1 else r['alpha'])
        buf = io.BytesIO(); o_save(fig, buf, format='png', **cap['kw']); buf.seek(0)
        fr = Image.open(buf).convert('RGBA')
        if t < total - (hold - 0.5):
            _scanline(fr, t, fr.width, fr.height)
        fr.convert('RGB').save(os.path.join(tmp, f'{i:04d}.png'))
    o_close(fig)
    W0, H0 = Image.open(os.path.join(tmp, '0000.png')).size
    h = int(H0 * width / W0) // 2 * 2
    vf = f'fps={FPS},scale={width}:{h}:flags=lanczos,split[a][b];[a]palettegen=max_colors=200:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle'
    r = subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%04d.png'), '-vf', vf, '-loop', '0', out], stdin=subprocess.DEVNULL, timeout=120)   # Nov 19: one encode can never hold a check-in
    shutil.rmtree(tmp)
    return out if r.returncode == 0 else None


def samples():
    """GIFs of three real recent posts: Gemini's USC win, the Day 4 standings, Gemini's Bengals bet."""
    import json
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    os.chdir(root); sys.path.insert(0, here)
    import sharecard, racecard
    d = json.load(open('data.json'))
    out = os.path.join(root, 'social', 'gif-samples'); os.makedirs(out, exist_ok=True)
    made = []
    usc = [t for t in d.get('allin_trades', []) if t.get('model') == 'gemini' and t.get('bet') == 'G40' and t.get('action') == 'Won']
    if usc:
        try:   # the streak line, exactly as the live post adds it (rivals.py)
            bets = json.load(open('ops/src/rivals.json'))['models']['gemini']['books']['AllInSports'].get('bets', [])
            usc[-1] = dict(usc[-1], streak=sharecard.streak_of(bets))
        except Exception as e:
            print('no streak:', e)
        made.append(make_gif(sharecard._trade_card, ('gemini', usc[-1]), {'path': '/tmp/gif_usc.png'}, os.path.join(out, 'win-gemini-usc.gif')))
    table, big = racecard.races()
    made.append(make_gif_mpl(racecard.races_card, (table, big, 'After Day 4 · Sat Oct 31', '/tmp/gif_races.png'), {}, os.path.join(out, 'standings-day4.gif')))
    ben = [t for t in d.get('rivals_trades', []) if t.get('model') == 'gemini' and t.get('bet') == 'G41' and t.get('action') == 'Bet']
    if ben:
        made.append(make_gif(sharecard.move_card, ('gemini', ben[-1]), {'path': '/tmp/gif_bengals.png', 'idx': 1, 'total': 2}, os.path.join(out, 'bet-gemini-bengals.gif')))
    print(made)



# ---------------------------------------------------------------- live posts (owner, Nov 1: "i dont think we should use still images there anymore")
# install() wraps the card functions so every still card the posters draw also gets an animated twin next to it (same name, .gif).
# Telegram (sendAnimation; albums as short videos) and Discord send the GIF when it exists, else the still card. A stale GIF from an
# earlier post is always deleted first, so a still is never paired with the wrong animation. A time budget keeps runs within limits.
import time as _time
_BUDGET = float(os.environ.get('PT_GIF_BUDGET', '150'))   # seconds of GIF rendering per run
_MAX = int(os.environ.get('PT_GIF_MAX', '14'))
_SPENT, _MADE = [0.0], [0]


def _wrap(orig, mpl=False):
    def w(*a, **k):
        path = k.get('path') or next((x for x in a if isinstance(x, str) and x.endswith('.png')), None)
        if path and os.path.exists(path[:-4] + '.gif'):
            os.remove(path[:-4] + '.gif')
        res = orig(*a, **k)
        out = res if isinstance(res, str) and res.endswith('.png') else path
        if out and os.path.exists(out[:-4] + '.gif'):
            os.remove(out[:-4] + '.gif')
        if out and os.path.exists(out) and _MADE[0] < _MAX and _SPENT[0] < _BUDGET:
            t0 = _time.time()
            try:
                g = (make_gif_mpl if mpl else make_gif)(orig, a, k, out[:-4] + '.gif')
                if g and os.path.getsize(g) > 8 * 1024 * 1024:   # too big to send everywhere: keep the still
                    os.remove(g)
                _MADE[0] += 1
            except Exception as e:
                print('animated card skipped:', e)
                if os.path.exists(out[:-4] + '.gif'):
                    os.remove(out[:-4] + '.gif')
            _SPENT[0] += _time.time() - t0
        return res
    w._animated = True
    return w


def install():
    """Call once in a poster (telegram.py, rivals.py). Safe to call twice."""
    # Nov 19: animated cards are OFF unless PT_GIFS=1 is set. They had silently gone out as stills since about Nov 12 (the new runner
    # image has no ffmpeg), and a test with ffmpeg on Nov 19 showed why they must not simply come back: with today's Pillow the recorder
    # captures only the "@PaperTradesAI" mark, so the animation is an almost empty card. Until the recorder is repaired and proven with
    # pictures, no poster wraps its cards, so nothing is recorded and a still is always sent. (It also saves about 4 s a card.)
    if os.environ.get('PT_GIFS', '0') != '1':
        return
    import sharecard, racecard
    for nm in ('_trade_card', 'moves_card', 'move_card', 'one_card'):
        f = getattr(sharecard, nm, None)
        if f and not getattr(f, '_animated', False):
            setattr(sharecard, nm, _wrap(f))
    for nm in ('races_card', 'race_card'):
        f = getattr(racecard, nm, None)
        if f and not getattr(f, '_animated', False):
            setattr(racecard, nm, _wrap(f, mpl=True))


def gif_of(photo):
    """The animated twin of a still card, if there is one."""
    return photo[:-4] + '.gif' if photo and photo.endswith('.png') and os.path.exists(photo[:-4] + '.gif') else None


def as_mp4(gif):
    """A GIF as a short silent MP4 (Telegram albums take videos, not GIFs). Returns the path or None."""
    out = gif[:-4] + '.mp4'
    r = subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', gif, '-movflags', '+faststart', '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', out], stdin=subprocess.DEVNULL, timeout=120)   # Nov 19: one encode can never hold a check-in
    return out if r.returncode == 0 else None


if __name__ == '__main__':
    {'samples': samples}[sys.argv[1] if len(sys.argv) > 1 else 'samples']()
