"""Instagram highlight covers, v2 (owner, Oct 30: "more colour, more drawings, more entertaining"). Each cover is 1080x1920; Instagram
shows only the centre circle, so each one is a bright disc with a big hand-drawn icon, doodles and sparkles, one colour per highlight.
Also draws a one-page visual guide (social/highlights/guide-*.jpg): every highlight, its cover, what goes in it and how many stories.

  python3 ops/hl_covers.py
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc  # noqa: E402

BG = (11, 11, 10)
CREAM = (242, 233, 216)
INK = (20, 18, 15)

# name, file, colour, second colour, what goes in it, how many stories
HL = [
    ('Start here', 'start-here', (61, 220, 132), (24, 140, 90), 'How the race works: the three AIs, the ten races, how scoring works, where to follow.', '4 stories'),
    ('Daily', 'daily', (255, 176, 0), (214, 110, 0), 'The results of every race day, one story per day, all ten races on it.', '1 a day (all 32)'),
    ('Lead changes', 'lead-changes', (255, 209, 102), (217, 119, 87), 'Every time an AI takes the lead in a race. Keep the biggest ones.', 'best 10 to 15'),
    ('Big moments', 'big-moments', (255, 90, 78), (180, 30, 60), 'The headlines: the Binance hack call, huge wins, painful losses.', '5 to 10'),
    ('Report cards', 'report-cards', (79, 143, 247), (60, 70, 200), 'The AIs grading each other: the harshest Fs and the best As.', '4 to 8'),
    ('Meet the AIs', 'meet-the-ais', (167, 139, 250), (110, 70, 210), 'Claude, Gemini and ChatGPT: who they are and how each one plays.', '4 stories'),
]


def wobble(d, pts, color, width, seed, passes=2):
    rnd = random.Random(seed)
    for k in range(passes):
        d.line([(x + rnd.uniform(-2.2, 2.2), y + rnd.uniform(-2.2, 2.2)) for x, y in pts], fill=color, width=max(3, width - 3 * k), joint='curve')


def ring(d, cx, cy, r, color, width, seed):
    pts = [(cx + r * (1 + 0.012 * math.sin(5 * t + seed)) * math.cos(t), cy + r * (1 + 0.012 * math.sin(5 * t + seed)) * math.sin(t)) for t in [i * 2 * math.pi / 160 for i in range(166)]]
    wobble(d, pts, color, width, seed)


def sparkle(d, x, y, s, color, width=6):
    wobble(d, [(x - s, y), (x + s, y)], color, width, int(x * y) % 97, 1)
    wobble(d, [(x, y - s), (x, y + s)], color, width, int(x + y) % 89, 1)
    wobble(d, [(x - s * .55, y - s * .55), (x + s * .55, y + s * .55)], color, max(3, width - 2), int(x) % 83, 1)


def disc(im, cx, cy, r, c1, c2):
    """A soft radial gradient disc."""
    g = Image.new('RGB', (2 * r, 2 * r), c2)
    gd = ImageDraw.Draw(g)
    for i in range(r, 0, -4):
        t = i / r
        col = tuple(int(c1[k] * (1 - t * .55) + c2[k] * (t * .55)) for k in range(3))
        gd.ellipse([r - i, r - i, r + i, r + i], fill=col)
    mask = Image.new('L', (2 * r, 2 * r), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    im.paste(g, (cx - r, cy - r), mask)


def icon(d, name, cx, cy, col, dark):
    s = 1.0
    if name == 'start-here':   # a play button with motion lines
        tri = [(cx - 110, cy - 170), (cx - 110, cy + 170), (cx + 180, cy)]
        d.polygon(tri, fill=CREAM)
        wobble(d, tri + [tri[0]], INK, 12, 5)
        for i, dy in enumerate((-90, 0, 90)):
            wobble(d, [(cx - 270, cy + dy), (cx - 165, cy + dy)], CREAM, 14, 20 + i)
    elif name == 'daily':   # a calendar page with a rising arrow
        d.rounded_rectangle([cx - 190, cy - 170, cx + 190, cy + 200], radius=34, fill=CREAM)
        d.rounded_rectangle([cx - 190, cy - 170, cx + 190, cy - 80], radius=34, fill=dark)
        d.rectangle([cx - 190, cy - 110, cx + 190, cy - 80], fill=dark)
        for x in (-110, 110):
            d.rounded_rectangle([cx + x - 16, cy - 215, cx + x + 16, cy - 135], radius=14, fill=INK)
        for i, h in enumerate((70, 120, 175)):
            x = cx - 135 + i * 100
            d.rounded_rectangle([x, cy + 160 - h, x + 70, cy + 160], radius=10, fill=dark if i < 2 else (61, 160, 100))
        wobble(d, [(cx - 150, cy + 90), (cx - 40, cy + 30), (cx + 40, cy + 50), (cx + 150, cy - 40)], INK, 12, 7)
        wobble(d, [(cx + 100, cy - 45), (cx + 155, cy - 42), (cx + 140, cy + 10)], INK, 12, 8)
        wobble(d, [(cx - 190, cy - 170), (cx + 190, cy - 170), (cx + 190, cy + 200), (cx - 190, cy + 200), (cx - 190, cy - 170)], INK, 9, 9)
    elif name == 'lead-changes':   # a crown with jewels
        pts = [(cx - 230, cy + 110), (cx - 250, cy - 150), (cx - 115, cy - 20), (cx, cy - 210), (cx + 115, cy - 20), (cx + 250, cy - 150), (cx + 230, cy + 110)]
        d.polygon(pts, fill=CREAM)
        wobble(d, pts + [pts[0]], INK, 12, 11)
        d.rounded_rectangle([cx - 230, cy + 120, cx + 230, cy + 200], radius=18, fill=CREAM, outline=INK, width=10)
        for (x, y), jc in zip(((-250, -150), (0, -210), (250, -150)), ((217, 119, 87), (79, 143, 247), (61, 220, 132))):
            d.ellipse([cx + x - 36, cy + y - 36, cx + x + 36, cy + y + 36], fill=jc, outline=INK, width=8)
        for i, x in enumerate((-120, 0, 120)):
            d.ellipse([cx + x - 22, cy + 138, cx + x + 22, cy + 182], fill=dark)
    elif name == 'big-moments':   # a lightning bolt with a burst
        for k in range(12):
            a = k * math.pi / 6
            wobble(d, [(cx + 250 * math.cos(a), cy + 250 * math.sin(a)), (cx + 320 * math.cos(a), cy + 320 * math.sin(a))], CREAM, 12, 30 + k, 1)
        bolt = [(cx + 40, cy - 240), (cx - 130, cy + 30), (cx - 10, cy + 30), (cx - 60, cy + 240), (cx + 140, cy - 50), (cx + 20, cy - 50), (cx + 90, cy - 240)]
        d.polygon(bolt, fill=(255, 209, 102))
        wobble(d, bolt + [bolt[0]], INK, 12, 41)
    elif name == 'report-cards':   # an A+ on a paper, circled, with a pencil
        d.rounded_rectangle([cx - 170, cy - 220, cx + 170, cy + 220], radius=26, fill=CREAM)
        wobble(d, [(cx - 170, cy - 220), (cx + 170, cy - 220), (cx + 170, cy + 220), (cx - 170, cy + 220), (cx - 170, cy - 220)], INK, 9, 50)
        f = pc.font('sans', 'Bold', 230)
        d.text((cx - 10, cy - 20), 'A', font=f, fill=(255, 90, 78), anchor='mm')
        d.text((cx + 115, cy - 95), '+', font=pc.font('sans', 'Bold', 130), fill=(255, 90, 78), anchor='mm')
        ring(d, cx + 5, cy - 25, 165, (255, 90, 78), 10, 51)
        wobble(d, [(cx - 120, cy + 140), (cx + 120, cy + 140)], (155, 146, 127), 8, 52, 1)
        wobble(d, [(cx - 120, cy + 180), (cx + 60, cy + 180)], (155, 146, 127), 8, 55, 1)
        # the pencil
        p = [(cx + 150, cy + 250), (cx + 300, cy + 40), (cx + 345, cy + 75), (cx + 195, cy + 285)]
        d.polygon(p, fill=(255, 209, 102)); wobble(d, p + [p[0]], INK, 8, 56)
        tip = [(cx + 150, cy + 250), (cx + 195, cy + 285), (cx + 140, cy + 305)]
        d.polygon(tip, fill=CREAM); wobble(d, tip + [tip[0]], INK, 7, 57)
    elif name == 'meet-the-ais':   # three little robot faces in the AIs' colours
        for i, (fc, tx) in enumerate((((217, 119, 87), -200), ((79, 143, 247), 0), ((242, 242, 242), 200))):
            x, y = cx + tx, cy + (-40 if i == 1 else 40)
            wobble(d, [(x, y - 120), (x, y - 175)], CREAM, 9, 60 + i, 1)
            d.ellipse([x - 22, y - 200, x + 22, y - 156], fill=(255, 209, 102), outline=INK, width=6)
            d.rounded_rectangle([x - 95, y - 120, x + 95, y + 80], radius=46, fill=fc, outline=INK, width=10)
            for ex in (-38, 38):
                d.ellipse([x + ex - 20, y - 60, x + ex + 20, y - 20], fill=INK)
                d.ellipse([x + ex - 6, y - 52, x + ex + 4, y - 42], fill=CREAM)
            wobble(d, [(x - 35, y + 25), (x, y + 45), (x + 35, y + 25)], INK, 9, 63 + i, 1)


def cover(name, c1, c2, path, seed):
    W, H, cx, cy, r = 1080, 1920, 540, 960, 470
    im = Image.new('RGB', (W, H), BG)
    # a soft colour glow behind the disc
    glow = Image.new('RGB', (W, H), BG); gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - 560, cy - 560, cx + 560, cy + 560], fill=tuple(int(v * .35) for v in c2))
    im = Image.blend(im, glow.filter(ImageFilter.GaussianBlur(90)), 1.0)
    disc(im, cx, cy, r, c1, c2)
    d = ImageDraw.Draw(im)
    ring(d, cx, cy, r - 26, CREAM, 10, seed)
    rnd = random.Random(seed)
    for k in range(7):   # sparkles and dots inside the edge of the circle
        a = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(330, 395)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        if k % 2:
            sparkle(d, x, y, rnd.uniform(16, 26), CREAM, 6)
        else:
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=CREAM)
    icon(d, name, cx, cy, c1, c2)
    im.save(path, quality=93)
    return path


def guide(paths, out):
    """One colourful page: every highlight, its cover, what goes in it and how many stories."""
    W, H = 1440, 2560
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    f = lambda k, w, s: pc.font(k, w, s)
    d.text((90, 120), 'PAPERTRADES.AI', font=f('mono', 'SemiBold', 44), fill=CREAM, anchor='lm')
    d.text((90, 230), 'Your highlights', font=f('sans', 'Bold', 120), fill=(255, 176, 0), anchor='lm')
    wobble(d, [(95, 310), (300, 302), (520, 312), (740, 304)], (255, 176, 0), 10, 3)
    d.text((90, 380), 'In this order on the profile. Each circle is its cover.', font=f('sans', 'Regular', 44), fill=(155, 146, 127), anchor='lm')
    y = 470
    for (title, key, c1, c2, what, n), p in zip(HL, paths):
        cov = Image.open(p).crop((540 - 470, 960 - 470, 540 + 470, 960 + 470)).resize((260, 260), Image.LANCZOS)
        m = Image.new('L', (260, 260), 0); ImageDraw.Draw(m).ellipse([0, 0, 259, 259], fill=255)
        im.paste(cov, (90, y), m)
        ring(d, 220, y + 130, 138, c1, 7, len(title))
        d.text((400, y + 50), title, font=f('sans', 'Bold', 66), fill=CREAM, anchor='lm')
        tw = f('sans', 'Bold', 66).getlength(title)
        d.rounded_rectangle([400 + tw + 30, y + 22, 400 + tw + 30 + f('mono', 'SemiBold', 30).getlength(n) + 40, y + 78], radius=28, fill=c1)
        d.text((400 + tw + 50, y + 50), n, font=f('mono', 'SemiBold', 30), fill=INK, anchor='lm')
        ww, yy = W - 490, y + 110
        line = ''
        for wd in what.split():
            t = (line + ' ' + wd).strip()
            if f('sans', 'Regular', 38).getlength(t) > ww:
                d.text((400, yy), line, font=f('sans', 'Regular', 38), fill=(200, 192, 176), anchor='lm'); yy += 50; line = wd
            else:
                line = t
        d.text((400, yy), line, font=f('sans', 'Regular', 38), fill=(200, 192, 176), anchor='lm')
        y += 330
    d.text((90, H - 120), 'Claude tells you which story goes where on GitHub ("Instagram highlights to add").', font=f('sans', 'Regular', 36), fill=(155, 146, 127), anchor='lm')
    im.save(out, quality=92)
    return out


if __name__ == '__main__':
    os.makedirs('social/highlights', exist_ok=True)
    ps = [cover(k, c1, c2, f'social/highlights/{k}.jpg', i + 3) for i, (t, k, c1, c2, w, n) in enumerate(HL)]
    print('covers:', ps)
    print('guide:', guide(ps, 'social/highlights/guide.jpg'))
