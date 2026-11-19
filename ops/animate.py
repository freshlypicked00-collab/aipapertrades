"""Animated GIF versions of the post cards (owner, Oct 31: "instead of still images gifs will be used going forward").

How it works: the normal card function (sharecard / racecard) draws the still card exactly as today. It is then run a second time with
every drawing step recorded as the pixels it changed, and the steps are replayed over time: the colour bar sweeps in, the robot pops in, lines slide up in reading order,
amounts count up, the AI's own words type themselves out, and a win ends with a burst (a loss with a short shake). Nothing new is
written or looked up: the GIF shows the same words and numbers as the still card, so it passes the same fact checks. The last frame IS
the still card, and three checks stand between a wrong animation and a post (any failure = the still card goes out): the recorded run
must give exactly the still on disk; the recorded steps must rebuild it pixel for pixel; the finished file's last frame is read back
and compared with it. Made by Pillow alone (no ffmpeg needed), within a time limit per card and per run.

  python3 ops/animate.py samples   -> social/gif-samples/*.gif from real recent posts
"""
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time as _time

from PIL import Image, ImageChops, ImageDraw

FPS = 20
INTRO = 0.75   # the '> ' terminal prompt before the card builds (ChatGPT, Oct 31)
MONEY = re.compile(r'^([+−\-]?)(C\$|US\$|¥)([\d,]+(?:\.\d+)?)(.*)$')


# ---------------------------------------------------------------- recording
# Rewritten Nov 19 (owner: "repair the animated cards"; Claude and Gemini agreed, ops/review/followups-nov19.json, F3 a to e).
# The first recorder told pictures apart by Python's id(), a number Python hands out again once a picture is freed; a link could then
# point back at itself and the run never ended (the stall of Nov 18 to 19). It also rebuilt each drawing step from its arguments, which
# came out almost empty on a newer Pillow. This one does neither:
#   * every picture the card touches gets its own running number and is kept alive until the recording ends, so no number is ever reused,
#     and a picture made from another one (trimmed, converted, copied) always has a HIGHER number than its parent: no loop can exist;
#   * a drawing step is recorded as what it CHANGED on the picture (the pixels before and after), not as its arguments. Replaying the
#     changes in order therefore rebuilds the still card exactly, whatever Pillow does inside, and anything drawn in a way this file does
#     not know about is simply picked up with the next step.
class _Rec:
    def __init__(self, want=None):
        self.n = 0            # running number for pictures and events
        self.tags = {}        # id(picture) -> its number (safe: every picture in here is held in self.imgs, so its id cannot be reused)
        self.imgs = {}        # number -> {'im', 'snap', 'base', 'parent', 'born'}
        self.events = []      # (seq, tag, kind, info, box, sprite)
        self.saves = []       # (seq, tag, copy, path)
        self.depth = 0        # > 0 while one of our hooks (or Pillow inside it) is running: nothing nested is recorded
        self.want = want

    def tick(self):
        self.n += 1
        return self.n

    def tag(self, im, parent=None):
        t = self.tags.get(id(im))
        if t is None or self.imgs[t]['im'] is not im:
            t = self.tick()
            snap = im.copy()
            self.tags[id(im)] = t
            self.imgs[t] = {'im': im, 'snap': snap, 'base': snap, 'parent': parent, 'born': t}
        return t

    def changed(self, im, kind, info=None):
        """Record what changed on this picture since it was last looked at."""
        t = self.tag(im)
        e = self.imgs[t]
        cur = im.copy()
        box, sprite = _patch(e['snap'], cur)
        e['snap'] = cur
        if box:
            self.events.append((self.tick(), t, kind, info or {}, box, sprite))

    def derive(self, parent, child):
        """child was made from parent at the same corner (trimmed, converted, copied, or two layers put together)."""
        if child is parent or not isinstance(child, Image.Image) or id(child) in self.tags:
            return
        self.changed(parent, 'other')   # anything drawn on the parent that we did not see goes in first
        pt = self.tags[id(parent)]
        ps = self.imgs[pt]['snap']
        if child.size[0] > ps.size[0] or child.size[1] > ps.size[1]:
            return
        t = self.tag(child, parent=pt)
        fit = ps.crop((0, 0) + child.size)
        if fit.mode != child.mode:
            fit = fit.convert(child.mode)
        box, sprite = _patch(fit, self.imgs[t]['snap'])
        if box:
            self.events.append((self.tick(), t, 'paste', {}, box, sprite))


def _mask(d):
    """One band that is non-zero wherever any band of the difference d is."""
    bands = d.split()
    m = bands[0]
    for x in bands[1:]:
        m = ImageChops.lighter(m, x)
    return m


def _patch(a, b):
    """(box, sprite): the smallest box holding every pixel that differs between a and b, and b's pixels there (only the changed ones show)."""
    if a.size != b.size or a.mode != b.mode:
        return (0, 0) + b.size, b.convert('RGBA')
    d = ImageChops.difference(a, b)
    if 'A' in d.mode or d.mode not in ('RGB', 'L'):
        d = _mask(d)   # Pillow looks only at the alpha band of an RGBA picture when asked for its box
    box = d.getbbox()
    if not box:
        return None, None
    sp = b.crop(box).convert('RGBA')
    sp.putalpha(_mask(d.crop(box)).point(_ON))
    return box, sp


_ON = [0] + [255] * 255
_DRAWS = ('text', 'multiline_text', 'rectangle', 'rounded_rectangle', 'line', 'ellipse', 'circle', 'polygon', 'regular_polygon', 'pieslice', 'arc', 'chord', 'point', 'bitmap')


def record(fn, *a, **k):
    """Run a card function with every drawing step recorded. Returns (its result, the record). Nothing is written to disk:
    the still card on disk stays exactly as the first, unrecorded run left it."""
    want = k.pop('_want', None)
    rec = _Rec(want)
    D, I = ImageDraw.ImageDraw, Image.Image
    orig = {m: getattr(D, m) for m in _DRAWS if hasattr(D, m)}
    o_init, o_paste, o_ac, o_save, o_crop, o_convert, o_copy, o_mac = D.__init__, I.paste, I.alpha_composite, I.save, I.crop, I.convert, I.copy, Image.alpha_composite

    def init(self, im, *aa, **kk):
        o_init(self, im, *aa, **kk)
        self._pt_img = im

    def wrap(name, f):
        def w(self, *aa, **kk):
            im = getattr(self, '_pt_img', None)
            if rec.depth or im is None:
                return f(self, *aa, **kk)
            rec.depth += 1
            try:
                rec.tag(im)
                out = f(self, *aa, **kk)
                info = {}
                if name in ('text', 'multiline_text'):
                    txt = aa[1] if len(aa) > 1 else kk.get('text', '')
                    ft = kk.get('font') if 'font' in kk else (aa[3] if len(aa) > 3 else None)
                    info = {'text': str(txt), 'size': getattr(ft, 'size', 20), 'font': ft, 'fill': kk.get('fill') if 'fill' in kk else (aa[2] if len(aa) > 2 else None),
                            'xy': aa[0] if aa else kk.get('xy'), 'anchor': kk.get('anchor')}
                rec.changed(im, 'text' if name == 'multiline_text' else name, info)
                return out
            finally:
                rec.depth -= 1
        return w

    def inplace(f):
        def w(self, *aa, **kk):
            if rec.depth:
                return f(self, *aa, **kk)
            rec.depth += 1
            try:
                rec.tag(self)
                out = f(self, *aa, **kk)
                rec.changed(self, 'paste')
                return out
            finally:
                rec.depth -= 1
        return w

    def derived(f, same_corner=lambda aa, kk: True):
        def w(self, *aa, **kk):
            if rec.depth:
                return f(self, *aa, **kk)
            rec.depth += 1
            try:
                out = f(self, *aa, **kk)
                if same_corner(aa, kk):
                    rec.derive(self, out)
                return out
            finally:
                rec.depth -= 1
        return w

    def corner(aa, kk):
        box = aa[0] if aa else kk.get('box')
        return box is None or (box[0] == 0 and box[1] == 0)

    def mac(im1, im2):
        if rec.depth:
            return o_mac(im1, im2)
        rec.depth += 1
        try:
            out = o_mac(im1, im2)
            rec.derive(im1, out)
            return out
        finally:
            rec.depth -= 1

    def save(self, fp=None, *aa, **kk):
        if rec.depth:
            return o_save(self, fp, *aa, **kk)
        rec.depth += 1
        try:
            rec.changed(self, 'other')
            rec.saves.append((rec.tick(), rec.tags[id(self)], self.copy(), fp if isinstance(fp, str) else None))
        finally:
            rec.depth -= 1

    D.__init__ = init
    for m, f in orig.items():
        setattr(D, m, wrap(m, f))
    I.paste, I.alpha_composite, I.save = inplace(o_paste), inplace(o_ac), save
    I.crop, I.convert, I.copy, Image.alpha_composite = derived(o_crop, corner), derived(o_convert), derived(o_copy), mac
    try:
        out = fn(*a, **k)
    finally:
        D.__init__ = o_init
        for m, f in orig.items():
            setattr(D, m, f)
        I.paste, I.alpha_composite, I.save, I.crop, I.convert, I.copy, Image.alpha_composite = o_paste, o_ac, o_save, o_crop, o_convert, o_copy, o_mac
    return out, rec


# ---------------------------------------------------------------- elements
class El:
    def __init__(self, kind, sprite, pos, info):
        self.kind, self.sprite, self.pos, self.info = kind, sprite, pos, info
        self.y = pos[1]; self.t0 = 0.0; self.fx = 'fade'


def elements(rec):
    """(elements in drawing order, the finished card, the empty card they are drawn on). Putting every element on the empty card,
    in order, gives the finished card pixel for pixel."""
    if not rec.saves:
        raise RuntimeError('animate: the card was never saved')
    hit = [s for s in rec.saves if rec.want and s[3] == rec.want] or rec.saves
    seq, target, final, _ = hit[-1]
    chain = [target]
    while rec.imgs[chain[0]]['parent'] is not None:
        nxt = rec.imgs[chain[0]]['parent']
        if nxt >= chain[0]:   # cannot happen (a picture made from another always has the higher number); kept as a guard, never a loop
            raise RuntimeError('animate: alias loop')
        chain.insert(0, nxt)
    W, H = final.size
    base = rec.imgs[chain[0]]['base']
    if base.size[0] < W or base.size[1] < H:
        raise RuntimeError('animate: the card grew while it was drawn')
    base = base.crop((0, 0, W, H)).convert('RGBA')
    until = {t: (rec.imgs[chain[i + 1]]['born'] if i + 1 < len(chain) else seq) for i, t in enumerate(chain)}
    els = []
    for s, t, kind, info, box, sprite in rec.events:
        if t not in until or s > until[t]:
            continue
        x0, y0, x1, y1 = box
        if x0 >= W or y0 >= H:
            continue
        if x1 > W or y1 > H:
            sprite = sprite.crop((0, 0, min(x1, W) - x0, min(y1, H) - y0))
        if not els and x0 <= 0 and y0 <= 0 and x1 >= W and y1 >= H and kind != 'text':
            base.alpha_composite(sprite)   # the background fill: part of the empty card
            continue
        els.append(El(kind, sprite, (x0, y0), dict(info)))
    return els, final.convert('RGB'), base


def proof(els, final, base):
    """Every element on the empty card must give the finished card exactly. Returns the number of pixels that differ (0 = proven)."""
    im = base.copy()
    for e in els:
        im.alpha_composite(e.sprite, e.pos)
    d = ImageChops.difference(im.convert('RGB'), final)
    return sum(_mask(d).point(_ON).histogram()[255:]) if d.getbbox() else 0


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
    im = base.copy()
    bg = base.getpixel((3, H // 2))[:3]
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
            bob = 0 if u < 1 else 4 * math.sin((t - e.t0) * 3.2) * max(0.0, min(1.0, (total - 0.35 - t) / 0.6))   # settles before the still card takes over
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
            if u < 1:
                sp, pos = _text_sprite(e, e.info['text'][:n], W, H)
                if sp is None:
                    continue
                x, y = pos
            last_typed = (e, x + sp.width, y, sp.height, u < 1)
        elif e.fx == 'count':
            if u < 1:
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
    _scanline(im, t, W, H)   # the faint sweep runs while the card builds; the reading hold is the still card itself
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
            im = im.transform(im.size, Image.AFFINE, (1, 0, 9 * math.sin(hu * 60), 0, 1, 0), fillcolor=tuple(bg) + (255,))
    return im.convert('RGB')


class TooSlow(Exception):
    pass


def _late(deadline):
    if deadline and _time.time() > deadline:
        raise TooSlow('animate: over the time limit for one card')


def _same(a, b, tol=0):
    """True when two pictures are the same size and no pixel differs by more than tol levels."""
    if a.size != b.size:
        return False
    d = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
    return not d.getbbox() if not tol else max(hi for lo, hi in d.getextrema()) <= tol


def write_gif(frames, durs, still, out, width, deadline=None):
    """Frames (same size as the still card) -> one GIF made by Pillow alone (no ffmpeg: the runner has none). The LAST frame is the still
    card itself, held for durs[-1] milliseconds. Proof built in (F3 b): the file is read back and its last frame must show the still
    card (within what 255 colours allow); if not, the file is deleted and None returned, so the still is what gets posted."""
    W, H = still.size
    size = (width, int(H * width / W) // 2 * 2)
    small = [f.resize(size, Image.LANCZOS) for f in frames] + [still.convert('RGB').resize(size, Image.LANCZOS)]
    _late(deadline)
    src = Image.new('RGB', (size[0] * 2, size[1]))   # the colours of the finished card and of the card half built
    src.paste(small[-1], (0, 0)); src.paste(small[len(small) // 3], (size[0], 0))
    pal = src.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    ps = []
    for f in small:
        ps.append(f.quantize(palette=pal, dither=Image.Dither.NONE))
        _late(deadline)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    ps[0].save(out, save_all=True, append_images=ps[1:], duration=list(durs), loop=0, optimize=False, disposal=1)
    try:
        g = Image.open(out)
        g.seek(g.n_frames - 1)
        last = g.convert('RGB')
        d = ImageChops.difference(last, small[-1]).convert('L')
        hist = d.histogram(); n = float(size[0] * size[1])
        mean = sum(i * c for i, c in enumerate(hist)) / n
        far = sum(hist[48:]) / n
        if g.n_frames < 2 or last.size != size or mean > 3.0 or far > 0.004:
            raise ValueError(f'last frame differs from the still card (mean {mean:.2f}, far {far:.4f}, frames {g.n_frames})')
    except Exception as e:
        print('animated card dropped:', e)
        if os.path.exists(out):
            os.remove(out)
        return None
    return out


def make_gif(card_fn, args, kwargs, out, width=720, hold=None, still=None, limit=None):
    """The card's drawing steps replayed over time, ending on the still card. Returns the GIF path, or None (then the still is posted).
    still: the card already on disk; the recorded run must give exactly that picture, or there is no animation."""
    deadline = _time.time() + limit if limit else None
    res, rec = record(card_fn, *args, **dict(kwargs, _want=still))
    if not rec.saves:
        return None
    els, final, base = elements(rec)
    W, H = final.size
    if still and os.path.exists(still) and not _same(Image.open(still), final):
        print('animated card dropped: the recorded card is not the still card')
        return None
    bad = proof(els, final, base)
    if bad:
        print(f'animated card dropped: the recorded steps do not rebuild the card ({bad} pixels differ)')
        return None
    if len(els) < 4:
        print('animated card dropped: too few drawing steps were recorded')
        return None
    if hold is None:   # time to read before it loops: longer when there is a quote to read (Gemini and ChatGPT)
        hold = 9.0 if any(e.fx == 'type' for e in els) else 6.5   # owner, Nov 1: more time to read everything (was 4.5 / 3.0)
    built = plan(els, W, H)
    hold = 9.0 if any(e.fx == 'type' for e in els) else hold
    heroes = [e for e in els if e.fx == 'count' and e.info.get('hero')]
    hero = heroes[0] if heroes else None
    win = None
    if hero:
        sign = hero.info['m'].group(1)
        win = True if sign == '+' else False if sign in ('−', '-') else None
        if win is not None:
            built = max(built, hero.t0 + hero.dur + (1.25 if win else 0.4))
    frames = []
    for i in range(int(built * FPS) + 1):
        frames.append(frame(els, base, W, H, i / FPS, built, win, hero))
        _late(deadline)
    durs = [int(1000 / FPS)] * len(frames) + [int(hold * 1000)]
    return write_gif(frames, durs, final, out, width, deadline)


def make_gif_mpl(card_fn, args, kwargs, out, width=960, hold=9.0, still=None, limit=None):   # owner, Nov 1: more time to read (was 4.5)
    """For cards drawn with matplotlib: rows light up from the top one after another, then the still card is held."""
    import io
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    deadline = _time.time() + limit if limit else None
    cap = {}
    o_save, o_close = Figure.savefig, plt.close

    def savefig(self, *a, **k):
        cap['fig'], cap['kw'] = self, {kk: v for kk, v in k.items() if kk in ('dpi', 'facecolor')}
        buf = io.BytesIO(); o_save(self, buf, format='png', **cap['kw']); buf.seek(0)
        cap['final'] = Image.open(buf).convert('RGB')   # nothing is written to disk: the still card stays as the first run left it
    Figure.savefig, plt.close = savefig, (lambda *a, **k: None)
    try:
        card_fn(*args, **kwargs)
    finally:
        Figure.savefig, plt.close = o_save, o_close
    fig = cap.get('fig')
    if fig is None:
        return None
    try:
        final = cap['final']
        if still and os.path.exists(still) and not _same(Image.open(still), final, tol=2):
            print('animated card dropped: the recorded card is not the still card')
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
            txt = a.get_text() if hasattr(a, 'get_text') else None
            rows.append({'a': a, 'y': Hpx - bb.y1, 'txt': txt, 'alpha': a.get_alpha() if a.get_alpha() is not None else 1.0})
        if len(rows) < 4:
            return None
        ys = sorted(set(round(r['y'] / 22) for r in rows))
        slot = {v: 0.2 + 0.11 * i for i, v in enumerate(ys)}
        for r in rows:
            r['t0'] = slot[round(r['y'] / 22)] + (0.0 if r['txt'] is None else 0.03); r['dur'] = 0.3
        built = max(r['t0'] + r['dur'] for r in rows) + 0.1
        fps = 10   # each frame is a full matplotlib drawing: fewer of them
        frames = []
        for i in range(int(built * fps) + 1):
            t = i / fps
            for r in rows:
                u = max(0.0, min(1.0, (t - r['t0']) / r['dur']))
                r['a'].set_alpha(r['alpha'] * ease(u) if u < 1 else r['alpha'])
            buf = io.BytesIO(); o_save(fig, buf, format='png', **cap['kw']); buf.seek(0)
            fr = Image.open(buf).convert('RGBA')
            if fr.size != final.size:
                return None
            _scanline(fr, t, fr.width, fr.height)
            frames.append(fr.convert('RGB'))
            _late(deadline)
        return write_gif(frames, [int(1000 / fps)] * len(frames) + [int(hold * 1000)], final, out, width, deadline)
    finally:
        o_close(fig)


def samples(out=None):
    """Animated cards of real recent posts, made exactly as a live post makes them (the wrapped card functions): a win, a loss, a buy,
    a sale with its receipt, and the daily standings. Prints each file with its time, size and frame count. Nothing is posted."""
    import json
    here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
    os.chdir(root); sys.path.insert(0, here)
    os.environ['PT_GIFS'] = '1'
    import sharecard, racecard
    install()
    out = out or os.path.join(root, 'social', 'gif-samples'); os.makedirs(out, exist_ok=True)
    st = json.load(open('ops/src/rivals.json'))
    tr = st['trades']
    label = {'gemini': 'Gemini', 'chatgpt': 'ChatGPT', 'claude': 'Claude'}

    def last(pred):
        return next((t for t in reversed(tr) if t.get('model') in ('gemini', 'chatgpt') and pred(t)), None)
    jobs = []
    for name, t in (('win', last(lambda t: t['action'] == 'Won')), ('loss', last(lambda t: t['action'] == 'Lost'))):
        if t:
            jobs.append((name, lambda t=t, name=name: [sharecard.trade_card(label[t['model']], t, os.path.join(out, name + '.png'))]))
    for name, t in (('buy', last(lambda t: t['action'] == 'Buy' and t['experiment'] in ('Stocks', 'Crypto', 'Metals', 'Energy'))),
                    ('sale', last(lambda t: t['action'] == 'Sell' and t['experiment'] in ('Stocks', 'Crypto', 'Metals', 'Energy'))),
                    ('bet', last(lambda t: t['action'] == 'Bet'))):
        if t:
            jobs.append((name, lambda t=t, name=name: sharecard.album(label[t['model']], [t], tr, st['history'], os.path.join(out, name), series=None)))
    table, big = racecard.races(None, 'ops/src')
    jobs.append(('day', lambda: [racecard.races_card(table, big, 'Live standings (sample)', os.path.join(out, 'day.png'))]))
    made = []
    for name, job in jobs:
        t0 = _time.time()
        try:
            pics = [p for p in (job() or []) if p]
        except Exception as e:
            print(name, 'FAILED', e); continue
        for p in pics:
            g = gif_of(p)
            if g:
                im = Image.open(g)
                print(f'{name}: {os.path.basename(g)} {os.path.getsize(g) / 1024:.0f} KB, {im.n_frames} frames, {im.size[0]}x{im.size[1]}')
                made.append(g)
            else:
                print(f'{name}: {os.path.basename(p)} STILL ONLY (no animation)')
        print(f'{name}: {_time.time() - t0:.1f} s for {len(pics)} card(s)')
    print(f'{len(made)} animated; {_SPENT[0]:.1f} s of the {_BUDGET:.0f} s budget used')
    return made



# ---------------------------------------------------------------- live posts (owner, Nov 1: "i dont think we should use still images there anymore")
# install() wraps the card functions so every still card the posters draw also gets an animated twin next to it (same name, .gif).
# Telegram (sendAnimation; albums as short videos) and Discord send the GIF when it exists, else the still card. A stale GIF from an
# earlier post is always deleted first, so a still is never paired with the wrong animation. A time budget keeps runs within limits.
_BUDGET = float(os.environ.get('PT_GIF_BUDGET', '90'))   # seconds of animation work per run (F3 d): past that, still cards
_CARD = float(os.environ.get('PT_GIF_CARD', '20'))       # seconds for one card: past that, that card goes out as the still
_MAX = int(os.environ.get('PT_GIF_MAX', '14'))
_SPENT, _MADE, _INSIDE = [0.0], [0], [0]


def _wrap(orig, mpl=False):
    def w(*a, **k):
        if _INSIDE[0]:   # a card function called by another card function (or by a recording): just draw; the outer card is the one animated
            return orig(*a, **k)
        _INSIDE[0] += 1
        try:
            return go(*a, **k)
        finally:
            _INSIDE[0] -= 1

    def go(*a, **k):
        path = k.get('path') or next((x for x in a if isinstance(x, str) and x.endswith('.png')), None)
        if path and os.path.exists(path[:-4] + '.gif'):
            os.remove(path[:-4] + '.gif')
        res = orig(*a, **k)
        out = res if isinstance(res, str) and res.endswith('.png') else path
        try:
            if out and os.path.exists(out[:-4] + '.gif'):
                os.remove(out[:-4] + '.gif')
            if out and os.path.exists(out) and _MADE[0] < _MAX and _SPENT[0] < _BUDGET:
                t0 = _time.time()
                try:
                    g = (make_gif_mpl if mpl else make_gif)(orig, a, k, out[:-4] + '.gif', still=out, limit=min(_CARD, _BUDGET - _SPENT[0]))
                    if g and os.path.getsize(g) > 8 * 1024 * 1024:   # too big to send everywhere: keep the still
                        os.remove(g)
                    _MADE[0] += 1
                except BaseException as e:   # whatever goes wrong with an animation, the still card is already made and is what goes out
                    print('animated card skipped:', e)
                    if os.path.exists(out[:-4] + '.gif'):
                        os.remove(out[:-4] + '.gif')
                    if isinstance(e, (KeyboardInterrupt, SystemExit)):
                        raise
                _SPENT[0] += _time.time() - t0
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print('animated card skipped:', e)
        return res
    w._animated = True
    return w


def install():
    """Call once in a poster (telegram.py, rivals.py). Safe to call twice."""
    # Animated cards are OFF unless PT_GIFS=1 is set (Nov 19). They had silently gone out as stills since about Nov 12 and the first
    # recorder was broken (see "recording" above). The recorder was rewritten the same day; the switch stays off until the owner has seen
    # sample cards and said yes, and it stays in place afterwards so animations can be turned off in one line (Claude and Gemini agreed).
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


def _ffmpeg():
    """ffmpeg if this machine has one: the system's, or the small pip package's (imageio-ffmpeg). None when there is none."""
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def as_mp4(gif):
    """A GIF as a short silent MP4 (Telegram albums take videos, not GIFs). Returns the path, or None (then the still goes in the album)."""
    exe = _ffmpeg()
    if not exe:
        return None
    out = gif[:-4] + '.mp4'
    try:
        r = subprocess.run([exe, '-nostdin', '-y', '-v', 'error', '-i', gif, '-movflags', '+faststart', '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', out], stdin=subprocess.DEVNULL, timeout=30)   # one encode can never hold a check-in
    except Exception as e:
        print('animated card kept as a still in the album:', e)
        return None
    return out if r.returncode == 0 and os.path.exists(out) else None


if __name__ == '__main__':
    samples(sys.argv[2] if len(sys.argv) > 2 else None)
