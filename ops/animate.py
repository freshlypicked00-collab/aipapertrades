"""Animated GIF versions of the post cards (owner, Oct 31: "instead of still images gifs will be used going forward").

How it works: the normal card function (sharecard / racecard) draws the card exactly as today, while every drawing step it makes is
recorded. The steps are then replayed over time: the colour bar sweeps in, the robot pops in, lines slide up in reading order,
amounts count up, the AI's own words type themselves out, and a win ends with a burst (a loss with a short shake). Nothing new is
written or looked up: the GIF shows the same words and numbers as the still card, so it passes the same fact checks.

  python3 ops/animate.py samples   -> social/gif-samples/*.gif from real recent posts
"""
import itertools
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time as _time

from PIL import Image, ImageChops, ImageDraw

FPS = 20
INTRO = 0.75   # the '> ' terminal prompt before the card builds (ChatGPT, Oct 31)
MONEY = re.compile(r'^([+−\-]?)(C\$|US\$|¥)([\d,]+(?:\.\d+)?)(.*)$')


# ---------------------------------------------------------------- recording
# Nov 19 repair (owner: "ask Gemini and do whatever you guys agree on"; Claude and Gemini agreed, ops/review/followups-nov19.json, F3):
# the old recorder told pictures apart by id(), a number Python hands out again once a picture is freed. A cropped copy could get the
# number of the picture it came from (an endless loop that stalled the check-ins on Nov 18-19), and the recording depended on a card's
# final picture happening to reuse the number of the one it replaced (so with other memory timing the animation came out nearly empty).
# Now every picture gets its own tag that is never reused, a drawing step is tied to its picture through ImageDraw.Draw (not Pillow's
# private _image field), and every animation is checked against the still card before it can be used (elements and check below).
_TOKS = itertools.count(1)


def _tok(im):
    """The picture's own tag, given the first time it is seen and never reused (None for anything that is not a picture)."""
    if not isinstance(im, Image.Image):
        return None
    t = getattr(im, '_pt_tok', None)
    if t is None:
        t = next(_TOKS)
        try:
            im._pt_tok = t
        except Exception:
            return None
    return t


class _Rec:
    def __init__(self):
        self.ops, self.saved, self.alias, self.made = [], None, {}, {}

    def root(self, i):
        """The picture a tag stands for: a same-origin crop (a card trimmed to fit) counts as the picture it was cut from. Tags are never
        reused, so this always ends; the guard stays anyway."""
        seen = set()
        while i in self.alias:
            if i in seen:
                raise RuntimeError('animate: alias loop')
            seen.add(i)
            i = self.alias[i]
        return i


DRAW_OPS = ('text', 'rectangle', 'rounded_rectangle', 'line', 'ellipse', 'polygon', 'pieslice', 'arc', 'chord', 'point', 'bitmap', 'regular_polygon')


def record(fn, *a, **k):
    """Run a card function; return (its result, the record: every drawing step and paste on each picture, and the picture it saved)."""
    rec = _Rec()
    D, I = ImageDraw.ImageDraw, Image.Image
    orig = {m: getattr(D, m) for m in DRAW_OPS if hasattr(D, m)}
    o_draw, o_new = ImageDraw.Draw, Image.new
    o_paste, o_save, o_crop = I.paste, I.save, I.crop
    depth = [0]   # a step Pillow builds out of other steps (a rounded rectangle, a polygon's outline) is recorded once, as itself

    def wrap(name):
        f = orig[name]

        def w(self, *aa, **kk):
            if depth[0] == 0:
                tgt = getattr(self, '_pt_tok', None) or _tok(getattr(self, '_image', None))
                rec.ops.append((tgt, name, aa, kk, getattr(self, '_pt_mode', None)))
            depth[0] += 1
            try:
                return f(self, *aa, **kk)
            finally:
                depth[0] -= 1
        return w

    def draw(im, mode=None):
        d = o_draw(im, mode)
        try:
            d._pt_tok, d._pt_mode = _tok(im), mode
        except Exception:
            pass
        return d

    def new(*aa, **kk):
        im = o_new(*aa, **kk)
        args = dict(zip(('mode', 'size', 'color'), aa)); args.update(kk)
        rec.made[_tok(im)] = (args.get('mode'), tuple(args.get('size') or im.size), args.get('color', 0))
        return im

    def paste(self, im, box=None, mask=None):
        src = im.copy() if isinstance(im, Image.Image) else im
        msk = mask.copy() if isinstance(mask, Image.Image) else mask
        rec.ops.append((_tok(self), 'paste', (src, box, msk), {}, None))
        return o_paste(self, im, box, mask)

    def save(self, *aa, **kk):
        rec.saved = (_tok(self), self.copy())
        return o_save(self, *aa, **kk)

    def crop(self, box=None):
        out = o_crop(self, box)
        if box is None or (box[0] == 0 and box[1] == 0):   # same origin: the card trimmed to fit
            ti, to = _tok(self), _tok(out)
            if ti is not None and to is not None and ti != to:
                rec.alias[to] = ti
        return out
    for m in orig:
        setattr(D, m, wrap(m))
    ImageDraw.Draw, Image.new = draw, new
    I.paste, I.save, I.crop = paste, save, crop
    try:
        out = fn(*a, **k)
    finally:
        for m, f in orig.items():
            setattr(D, m, f)
        ImageDraw.Draw, Image.new = o_draw, o_new
        I.paste, I.save, I.crop = o_paste, o_save, o_crop
    return out, rec


# ---------------------------------------------------------------- elements
class El:
    def __init__(self, kind, sprite, pos, info):
        self.kind, self.sprite, self.pos, self.info = kind, sprite, pos, info
        self.y = pos[1]; self.t0 = 0.0; self.fx = 'fade'


def elements(rec):
    """Replay the recorded steps on a fresh canvas, in order. Each step's element is exactly the pixels it changed, so the elements put
    together give back the still card pixel for pixel (check() makes sure). Returns (elements, the background, the still card)."""
    target, final = rec.saved
    W, H = final.size
    root = rec.root(target)
    mode, _, color = rec.made.get(root, (final.mode, None, None))
    if color is None or mode is None:
        mode, color = final.mode, final.getpixel((3, H // 2))
    canvas = Image.new(mode, (W, H), color)
    base, els = None, []
    for tgt, kind, a, k, dmode in rec.ops:
        if tgt is None or rec.root(tgt) != root:
            continue
        before = canvas.copy()
        try:
            if kind == 'paste':
                src, box, msk = a
                canvas.paste(src, box, msk)
            else:
                getattr(ImageDraw.Draw(canvas, dmode), kind)(*a, **k)
        except Exception:
            canvas = before
            continue
        ch = ImageChops.difference(before.convert('RGB'), canvas.convert('RGB')).convert('L').point(lambda v: 255 if v else 0)
        bb = ch.getbbox()
        if not bb:
            continue
        if not els and kind == 'rectangle' and bb == (0, 0, W, H):
            base = canvas.copy(); continue   # a background fill: part of the background, not an element
        sp = canvas.convert('RGBA').crop(bb); sp.putalpha(ch.crop(bb))
        info = {}
        if kind == 'text':
            txt = a[1] if len(a) > 1 else k.get('text', '')
            f = k.get('font'); info = {'text': str(txt), 'size': getattr(f, 'size', 20), 'font': f, 'fill': k.get('fill'), 'xy': a[0], 'anchor': k.get('anchor')}
        els.append(El(kind, sp, (bb[0], bb[1]), info))
    base = (base or Image.new(mode, (W, H), color)).convert('RGB')
    return els, base, final.convert('RGB')


def _covers(box, W, H):
    try:
        x0, y0, x1, y1 = [float(v) for v in (box if len(box) == 4 else (*box[0], *box[1]))]
        return x0 <= 0 and y0 <= 0 and x1 >= W - 1 and y1 >= H - 1
    except Exception:
        return False


def check(els, base, final):
    """The built-in proof (F3 b): the animation's last frame (every element in place, no passing effect) must be the still card. Raises
    if not, so that card goes out as the still."""
    im = base.convert('RGBA')
    for e in els:
        im.alpha_composite(e.sprite, (int(e.pos[0]), int(e.pos[1])))
    d = ImageChops.difference(im.convert('RGB'), final).convert('L')
    hist = d.histogram(); n = final.size[0] * final.size[1]
    mean = sum(i * c for i, c in enumerate(hist)) / n
    off = sum(hist[25:]) / n
    if not els or mean > 0.3 or off > 0.0005:
        raise RuntimeError(f'animate: the animation does not end on the still card ({len(els)} elements, mean difference {mean:.2f}, {off:.3%} of pixels off)')
    return mean, off


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


def frame(els, base, W, H, t, total, win=None, hero=None):
    im = base.convert('RGBA')
    last_typed = None
    for e in els:
        u = (t - e.t0) / max(0.01, getattr(e, 'dur', 0.35))
        if u <= 0:
            continue
        sp, (x, y) = e.sprite, e.pos
        a = 1.0
        done = u >= 1   # once an element has arrived it is its exact pixels, so the card ends exactly on the still (check)
        if e.fx in ('wipe', 'draw') and not done:
            w = int(sp.width * ease(u))
            if w <= 0:
                continue
            sp = sp.crop((0, 0, w, sp.height))
        elif e.fx == 'pop':
            if not done:
                s = back(u)
                if s <= 0.02:
                    continue
                sp2 = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.BILINEAR)
                x += (sp.width - sp2.width) / 2; y += (sp.height - sp2.height) / 2; sp = sp2
            else:
                y += 4 * math.sin((t - e.t0) * 3.2)   # the robot keeps a gentle bob while the card is read
        elif e.fx == 'rise' and not done:
            a = ease(u); y += (1 - ease(u)) * 26
        elif e.fx == 'fade' and not done:
            a = ease(u)
        elif e.fx == 'type':
            if not done:
                n = int(len(e.info['text']) * u)
                if n <= 0:
                    continue
                sp, pos = _text_sprite(e, e.info['text'][:n], W, H)
                if sp is None:
                    continue
                x, y = pos
                last_typed = (e, x + sp.width, y, sp.height, True)
            else:
                last_typed = (e, x + sp.width, y, sp.height, False)
        elif e.fx == 'count' and not done:
            sp, pos = _text_sprite(e, _fmt_money(e.info['m'], ease(u)), W, H)
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
            im = im.transform(im.size, Image.AFFINE, (1, 0, 9 * math.sin(hu * 60), 0, 1, 0), fillcolor=tuple(base.getpixel((3, H // 2))[:3]) + (255,))
    return im.convert('RGB')


def _ffmpeg():
    """ffmpeg from the system, else from the imageio-ffmpeg pip package (F3 c: the new runner image no longer ships one)."""
    p = shutil.which('ffmpeg')
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


PER_CARD = float(os.environ.get('PT_GIF_CARD', '30'))   # F3 d: seconds one animation may take, at most; past that, the still


def _encode(frames, size, out, width, limit, t_start):
    """Pipe the frames straight into ffmpeg (no picture files) and make the GIF. None if it runs out of time or fails."""
    ff = _ffmpeg()
    if not ff:
        print('animated card skipped: no ffmpeg')
        return None
    W, H = size
    h = int(H * width / W) // 2 * 2
    vf = f'fps={FPS},scale={width}:{h}:flags=lanczos,split[a][b];[a]palettegen=max_colors=200:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle'
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    tmp = out[:-4] + '.part.gif'
    p = subprocess.Popen([ff, '-nostdin', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-framerate', str(FPS), '-i', '-',
                          '-vf', vf, '-loop', '0', '-f', 'gif', tmp], stdin=subprocess.PIPE)
    ok = False
    try:
        for fr in frames:
            if _time.time() - t_start > limit:
                print(f'animated card skipped: it would take more than {limit:.0f} s')
                break
            p.stdin.write(fr.tobytes())
        else:
            ok = True
        p.stdin.close()
        p.wait(timeout=max(1.0, limit - (_time.time() - t_start)))
    except Exception as e:
        print('animated card skipped:', e); ok = False
    finally:
        if p.poll() is None:
            p.kill(); p.wait()
    if ok and p.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
        os.replace(tmp, out)
        return out
    if os.path.exists(tmp):
        os.remove(tmp)
    return None


def make_gif(card_fn, args, kwargs, out, width=720, hold=None, rec=None, limit=None):
    """The GIF of a card, from its recording (rec) or by drawing the card now (which also saves the still). Returns the GIF path, or None
    when it can't be made in time. Raises when the animation would not end exactly on the still card (check): the still goes out."""
    t_start = _time.time()
    limit = PER_CARD if limit is None else min(PER_CARD, limit)
    if rec is None:
        _, rec = record(card_fn, *args, **kwargs)
    if not rec.saved:
        return None
    els, base, final = elements(rec)
    check(els, base, final)
    W, H = final.size
    if hold is None:   # time to read before it loops: longer when there is a quote to read (Gemini and ChatGPT)
        hold = 9.0 if any(e.fx == 'type' for e in els) else 6.5   # owner, Nov 1: more time to read everything (was 4.5 / 3.0)
    total = plan(els, W, H) + hold
    heroes = [e for e in els if e.fx == 'count' and e.info.get('hero')]
    hero = heroes[0] if heroes else None
    win = None
    if hero:
        sign = hero.info['m'].group(1)
        win = True if sign == '+' else False if sign in ('−', '-') else None
    n = int(total * FPS)
    return _encode((frame(els, base, W, H, i / FPS, total, win, hero) for i in range(n)), (W, H), out, width, limit, t_start)


def make_gif_mpl(card_fn, args, kwargs, out, width=960, hold=9.0, still=None, limit=None):   # owner, Nov 1: more time to read (was 4.5)
    """For cards drawn with matplotlib: rows light up from the top one after another, amounts count up. The last frame must be the still
    card (F3 b), and it must be done within the time limit (F3 d)."""
    import io
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    t_start = _time.time()
    limit = PER_CARD if limit is None else min(PER_CARD, limit)
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
    try:
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
        n = int(total * FPS)

        def render(t):
            for r in rows:
                u = (t - r['t0']) / r['dur']; a = max(0.0, min(1.0, u))
                r['a'].set_alpha(r['alpha'] * ease(a) if a < 1 else r['alpha'])
            buf = io.BytesIO(); o_save(fig, buf, format='png', **cap['kw']); buf.seek(0)
            return Image.open(buf).convert('RGBA')
        last = render(total).convert('RGB')
        if still and os.path.exists(still):
            ref = Image.open(still).convert('RGB')
            if ref.size != last.size:
                raise RuntimeError(f'animate: the animation is {last.size}, the still card {ref.size}')
            d = ImageChops.difference(last, ref).convert('L').histogram(); px = ref.size[0] * ref.size[1]
            if sum(i * c for i, c in enumerate(d)) / px > 0.3 or sum(d[25:]) / px > 0.0005:
                raise RuntimeError('animate: the animation does not end on the still card')

        still_from = max(max(r['t0'] + r['dur'] for r in rows), total - (hold - 0.5))   # from here on every frame is the same picture

        def frames():
            prev = None
            for i in range(n):
                t = i / FPS
                if t >= still_from:
                    yield last   # drawn once, not once a frame (a matplotlib frame takes up to 0.4 s on GitHub's runner)
                    continue
                if prev is not None and i % 2:
                    yield prev   # rows fade in at 10 drawings a second: half the time, the same look
                    continue
                fr = render(t)
                if t < total - (hold - 0.5):
                    _scanline(fr, t, fr.width, fr.height)
                prev = fr.convert('RGB')
                yield prev
        return _encode(frames(), last.size, out, width, limit, t_start)
    finally:
        o_close(fig)


def samples(out_dir=None):
    """Animations of real recent posts, made exactly as the live posts make them (F3 e): a sale, a bet, a win, several moves, the standings.
    Writes social/gif-samples/*.gif, a strip of frames from each (*-frames.jpg) and summary.json."""
    import json
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    os.chdir(root); sys.path.insert(0, here)
    import sharecard, racecard
    d = json.load(open('data.json'))
    out = out_dir or os.path.join(root, 'social', 'gif-samples'); os.makedirs(out, exist_ok=True)
    rt = d.get('rivals_trades', []) + d.get('allin_trades', [])
    last = lambda f: next((t for t in reversed(rt) if f(t)), None)
    jobs = []
    sale = last(lambda t: t.get('action') == 'Sell' and t.get('model') in ('gemini', 'chatgpt'))
    if sale:
        jobs.append(('sale-card', sharecard.move_card, (sale['model'], sale), {'path': '/tmp/gif_sale.png'}))
        jobs.append(('sale-trade', sharecard._trade_card, (sale['model'], sale), {'path': '/tmp/gif_sale_t.png'}))
    bet = last(lambda t: t.get('action') == 'Bet')
    if bet:
        jobs.append(('bet', sharecard.move_card, (bet['model'], bet), {'path': '/tmp/gif_bet.png', 'idx': 1, 'total': 2}))
    won = last(lambda t: t.get('action') == 'Won')
    if won:
        jobs.append(('win', sharecard._trade_card, (won['model'], won), {'path': '/tmp/gif_win.png'}))
    mv = [t for t in rt if t.get('model') == 'gemini'][-4:]
    if mv:
        jobs.append(('moves', sharecard.moves_card, ('gemini', mv), {'path': '/tmp/gif_moves.png'}))
    summary = []
    for name, fn, a, k in jobs:
        t0 = _time.time()
        try:
            _, rec = record(fn, *a, **k)
            g = make_gif(fn, a, k, os.path.join(out, name + '.gif'), rec=rec, limit=PER_CARD)
            els, base, final = elements(rec)
            mean, off = check(els, base, final)
            summary.append({'card': name, 'gif': bool(g), 'elements': len(els), 'mean_diff': round(mean, 3), 'off': off, 'seconds': round(_time.time() - t0, 1),
                            'kb': os.path.getsize(g) // 1024 if g else None})
            if g:
                _strip(g, os.path.join(out, name + '-frames.jpg'))
        except Exception as e:
            summary.append({'card': name, 'gif': False, 'error': str(e)[:300], 'seconds': round(_time.time() - t0, 1)})
    try:
        t0 = _time.time()
        table, big = racecard.races()
        racecard.races_card(table, big, 'Standings sample', '/tmp/gif_races.png')
        g = make_gif_mpl(racecard.races_card, (table, big, 'Standings sample', '/tmp/gif_races.png'), {}, os.path.join(out, 'standings.gif'), still='/tmp/gif_races.png', limit=PER_CARD)
        summary.append({'card': 'standings', 'gif': bool(g), 'seconds': round(_time.time() - t0, 1), 'kb': os.path.getsize(g) // 1024 if g else None})
        if g:
            _strip(g, os.path.join(out, 'standings-frames.jpg'))
    except Exception as e:
        summary.append({'card': 'standings', 'gif': False, 'error': str(e)[:300]})
    json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    print(json.dumps(summary, indent=1))
    return summary


def _strip(gif, path, n=8):
    """Eight frames of a GIF side by side, to look at it frame by frame (F3 e)."""
    im = Image.open(gif); k = getattr(im, 'n_frames', 1); pics = []
    for i in range(n):
        im.seek(min(k - 1, int(i * (k - 1) / max(1, n - 1)))); pics.append(im.convert('RGB').copy())
    w, h = pics[0].size; sc = 300 / w
    sheet = Image.new('RGB', (int(w * sc) * n, int(h * sc)), (40, 40, 40))
    for i, p in enumerate(pics):
        sheet.paste(p.resize((int(w * sc), int(h * sc))), (i * int(w * sc), 0))
    sheet.save(path, quality=85)


# ---------------------------------------------------------------- live posts (owner, Nov 1: "i dont think we should use still images there anymore")
# install() wraps the card functions so every still card the posters draw also gets an animated twin next to it (same name, .gif).
# Telegram (sendAnimation; albums as short videos) and Discord send the GIF when it exists, else the still card. A stale GIF from an
# earlier post is always deleted first, so a still is never paired with the wrong animation. Each card is drawn once: the same drawing
# saves the still and records the animation. Limits (F3 d): one animation at most PT_GIF_CARD seconds (30), all of a run's animations
# together at most PT_GIF_BUDGET seconds (90); past that, stills. A card drawn inside another card's drawing never makes its own GIF.
_BUDGET = float(os.environ.get('PT_GIF_BUDGET', '90'))   # seconds of GIF making per run
_MAX = int(os.environ.get('PT_GIF_MAX', '14'))
_SPENT, _MADE, _ACTIVE = [0.0], [0], [False]


def _wrap(orig, mpl=False):
    def w(*a, **k):
        if _ACTIVE[0]:
            return orig(*a, **k)   # inside another card's drawing: that card makes the animation
        path = k.get('path') or next((x for x in a if isinstance(x, str) and x.endswith('.png')), None)
        if path and os.path.exists(path[:-4] + '.gif'):
            os.remove(path[:-4] + '.gif')
        left = _BUDGET - _SPENT[0]
        want = _MADE[0] < _MAX and left > 5 and _ffmpeg() is not None   # no ffmpeg on this run (a settle run skips the pip step): no recording either
        t0 = _time.time()
        _ACTIVE[0] = True
        try:
            rec = None
            if want and not mpl:
                res, rec = record(orig, *a, **k)   # one drawing: the still is saved and the animation recorded
            else:
                res = orig(*a, **k)
            out = res if isinstance(res, str) and res.endswith('.png') else path
            if out and os.path.exists(out[:-4] + '.gif'):
                os.remove(out[:-4] + '.gif')
            if want and out and os.path.exists(out):
                try:
                    rest = left - (_time.time() - t0)
                    g = (make_gif_mpl(orig, a, k, out[:-4] + '.gif', still=out, limit=rest) if mpl else
                         make_gif(orig, a, k, out[:-4] + '.gif', rec=rec, limit=rest))
                    if g and os.path.getsize(g) > 8 * 1024 * 1024:   # too big to send everywhere: keep the still
                        os.remove(g)
                    _MADE[0] += 1
                except Exception as e:
                    print('animated card skipped:', e)
                    if os.path.exists(out[:-4] + '.gif'):
                        os.remove(out[:-4] + '.gif')
        finally:
            _ACTIVE[0] = False
            _SPENT[0] += _time.time() - t0
        return res
    w._animated = True
    return w


def install():
    """Call once in a poster (telegram.py, rivals.py). Safe to call twice."""
    # Animated cards are on only when PT_GIFS=1. The workflows set it from the repository variable PT_GIFS (Settings > Secrets and
    # variables > Actions > Variables): on unless that variable is 0, so they can be turned off in one step without touching the code
    # (Claude and Gemini, F3). History: off on Nov 19 after the stall; repaired the same day (recorder, check, limits, ffmpeg from pip).
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
    ff = _ffmpeg()
    if not ff:
        return None
    out = gif[:-4] + '.mp4'
    try:
        r = subprocess.run([ff, '-nostdin', '-y', '-v', 'error', '-i', gif, '-movflags', '+faststart', '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', out],
                           stdin=subprocess.DEVNULL, timeout=60)   # one encode can never hold a check-in
    except Exception as e:
        print('mp4 skipped:', e)
        return None
    return out if r.returncode == 0 else None


if __name__ == '__main__':
    {'samples': samples}[sys.argv[1] if len(sys.argv) > 1 else 'samples']()
