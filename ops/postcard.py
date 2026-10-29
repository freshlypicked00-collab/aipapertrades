"""Instagram pictures for Paper Trades, in the website's own look (dark theme, IBM Plex fonts, the site's colors).

Every picture is 1440x1800 (4:5, the largest Instagram keeps), with all content inside the centre 3:4 area so the
profile grid shows it uncropped. A quality gate (QualityError) refuses any picture whose text would leave the safe area,
whose numbers are missing or not finite, or whose content is incomplete: nothing below standard is ever posted.
"""
import math
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
W, H = 1440, 1800
SAFE_X = 110            # the grid crops 45px a side; keep a calm margin beyond that
BG, FG, MUTED, LINE, PANEL = '#0b0b0a', '#f2e9d8', '#9b927f', '#2b2923', '#13120f'
UP, DOWN, AMBER = '#3ddc84', '#ff5a4e', '#ffb000'
AIS = {'claude': ('Claude', '#d97757'), 'gemini': ('Gemini', '#4f8ff7'), 'chatgpt': ('ChatGPT', '#f2f2f2')}
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets'}
ORDER = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
NY = ZoneInfo('America/New_York')


class QualityError(Exception):
    pass


def font(kind, weight, size):
    name = {'mono': 'IBMPlexMono', 'sans': 'IBMPlexSansCondensed'}[kind] + '-' + weight + '.ttf'
    path = os.path.join(FONTS, name)
    if not os.path.exists(path):
        raise QualityError(f'missing font {name}')
    return ImageFont.truetype(path, size)


def money(x, race):
    if x is None or not math.isfinite(float(x)):
        raise QualityError('a value is missing')
    sym = 'US$' if race == 'China' else 'C$'
    if abs(x) < 0.5:
        return sym + '0'
    return ('+' if x > 0 else '−') + sym + f'{abs(x):,.0f}'


def day_of(dt):
    return (dt.astimezone(NY).date() - datetime(2026, 10, 27).date()).days


class Card:
    def __init__(self):
        self.im = Image.new('RGB', (W, H), BG)
        self.d = ImageDraw.Draw(self.im)

    def text(self, xy, s, f, fill, anchor='la', tracking=0):
        x, y = xy
        if tracking:   # letter-spaced labels, like the site's small uppercase headings
            w = self.width(s, f, tracking)
            if anchor[0] == 'r':
                x -= w
            start = x
            for ch in s:
                self.d.text((x, y), ch, font=f, fill=fill, anchor='l' + anchor[1])
                x += f.getlength(ch) + tracking
            box = (start, y - f.size // 2, start + w, y + f.size // 2)
        else:
            self.d.text((x, y), s, font=f, fill=fill, anchor=anchor)
            box = self.d.textbbox((x, y), s, font=f, anchor=anchor)
        if box[0] < SAFE_X - 2 or box[2] > W - SAFE_X + 2 or box[1] < 40 or box[3] > H - 40:
            raise QualityError(f'text out of bounds: {s!r}')
        return box

    def width(self, s, f, tracking=0):
        return sum(f.getlength(ch) + tracking for ch in s) - (tracking if s else 0) if tracking else f.getlength(s)

    def fit(self, s, kind, weight, size, max_w, min_size=28):
        """The largest font size up to `size` at which s fits max_w."""
        while size >= min_size:
            f = font(kind, weight, size)
            if f.getlength(s) <= max_w:
                return f
            size -= 2
        raise QualityError(f'text too long: {s!r}')

    def wrap(self, s, f, max_w):
        words, lines, cur = s.split(), [], ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if f.getlength(t) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        if cur:
            lines.append(cur)
        return lines

    def header(self, right):
        icon = os.path.join(os.path.dirname(HERE), 'icon-512.png')
        x = SAFE_X
        if os.path.exists(icon):
            ic = Image.open(icon).convert('RGBA').resize((76, 76), Image.LANCZOS)
            self.im.paste(ic, (x, 92), ic)
            x += 100
        self.text((x, 130), 'PAPER TRADES', font('mono', 'SemiBold', 44), FG, 'lm', tracking=6)
        self.text((W - SAFE_X, 130), right, font('mono', 'Medium', 28), MUTED, 'rm', tracking=3)
        self.d.line([(SAFE_X, 210), (W - SAFE_X, 210)], fill=LINE, width=3)

    def footer(self):
        self.d.line([(SAFE_X, 1610), (W - SAFE_X, 1610)], fill=LINE, width=3)
        self.text((SAFE_X, 1672), 'papertrades.ai', font('mono', 'SemiBold', 40), FG, 'lm')
        self.text((W - SAFE_X, 1672), '@PaperTradesAI', font('mono', 'Medium', 30), MUTED, 'rm')
        self.text((SAFE_X, 1730), 'Simulation with pretend money and real prices. Not financial advice.', font('sans', 'Regular', 28), MUTED, 'lm')

    def save(self, path):
        self.im.save(path, 'JPEG', quality=95, subsampling=0, optimize=True)
        return path


def moment(m, path):
    """A lead change within one race."""
    race, who, over = m['race'], m['who'], m['over']
    prof = m.get('profit') or {}
    if race not in LABEL or who not in AIS or over not in AIS or set(prof) != set(AIS):
        raise QualityError('moment data incomplete')
    at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
    c = Card()
    c.header(f'DAY {day_of(at)} OF 32')
    c.text((SAFE_X, 300), f'LEAD CHANGE · {LABEL[race].upper()}', font('mono', 'SemiBold', 34), AMBER, 'lm', tracking=4)
    hf = font('sans', 'Bold', 150)
    head = f'{AIS[who][0]} takes the lead'
    words = head.split()
    if hf.getlength(head) <= W - 2 * SAFE_X:
        lines = [head]
    else:   # two balanced lines, never a single word left dangling
        best = min(range(1, len(words)), key=lambda k: max(hf.getlength(' '.join(words[:k])), hf.getlength(' '.join(words[k:]))))
        lines = [' '.join(words[:best]), ' '.join(words[best:])]
        if max(hf.getlength(x) for x in lines) > W - 2 * SAFE_X:
            raise QualityError('headline too long')
    y = 360
    for ln in lines:
        c.text((SAFE_X, y), ln, hf, AIS[who][1], 'lt'); y += 160
    sub = f'Ahead of {AIS[over][0]} by {money(m["lead"], race).lstrip("+")}.'
    c.text((SAFE_X, y + 40), sub, font('sans', 'Medium', 60), FG, 'lt')
    when = at.astimezone(NY)
    c.text((SAFE_X, y + 130), when.strftime('%a %b %-d, %-I:%M %p ET').replace('AM', 'a.m.').replace('PM', 'p.m.'), font('mono', 'Regular', 30), MUTED, 'lt')
    # standings in this race
    top = 1010
    c.text((SAFE_X, top), f'{LABEL[race].upper()} · PROFIT SINCE OCT 28', font('mono', 'Medium', 28), MUTED, 'lm', tracking=3)
    ids = sorted(prof, key=lambda k: -prof[k])
    y = top + 50
    for i, mid in enumerate(ids):
        c.d.rounded_rectangle([SAFE_X, y, W - SAFE_X, y + 150], radius=14, fill=PANEL, outline=LINE, width=2)
        c.d.rectangle([SAFE_X, y, SAFE_X + 10, y + 150], fill=AIS[mid][1])
        c.text((SAFE_X + 50, y + 75), ['1ST', '2ND', '3RD'][i], font('mono', 'SemiBold', 34), AMBER if i == 0 else MUTED, 'lm', tracking=2)
        c.text((SAFE_X + 190, y + 75), AIS[mid][0], font('sans', 'SemiBold', 68), FG, 'lm')
        v = prof[mid]
        c.text((W - SAFE_X - 40, y + 75), money(v, race), font('mono', 'SemiBold', 60), UP if v > 0.5 else DOWN if v < -0.5 else MUTED, 'rm')
        y += 172
    c.footer()
    return c.save(path)


def daily(table, n, when, big, path):
    """Day N results: who leads each of the ten races (each race on its own)."""
    if not table or any(e not in table for e in ORDER):
        raise QualityError('daily data incomplete: not every race has results')
    c = Card()
    c.header(f'DAY {n} OF 32')
    c.text((SAFE_X, 290), f'DAY {n} RESULTS · {when.strftime("%a %b %-d").upper()}', font('mono', 'SemiBold', 34), AMBER, 'lm', tracking=4)
    c.text((SAFE_X, 330), 'Who leads each race', font('sans', 'Bold', 104), FG, 'lt')
    c.text((SAFE_X, 455), 'Ten separate races · profit since the Oct 28 restart', font('sans', 'Regular', 34), MUTED, 'lt')
    y, rh = 528, 106
    for i, e in enumerate(ORDER):
        rows = table[e]
        if i % 2 == 0:
            c.d.rectangle([SAFE_X - 20, y, W - SAFE_X + 20, y + rh - 6], fill=PANEL)
        c.text((SAFE_X, y + 30), (LABEL[e] + (' (US$)' if e == 'China' else '')).upper(), font('mono', 'Medium', 24), MUTED, 'lm', tracking=2)
        even = max(r[1] for r in rows) - min(r[1] for r in rows) < 0.5
        if even:
            c.text((SAFE_X, y + 70), 'All even so far', font('sans', 'Medium', 40), MUTED, 'lm')
        elif rows[0][1] - rows[1][1] < 0.5:   # a tie at the top is shown as a tie, never as a lead
            tied = [m2 for m2, p2 in rows if rows[0][1] - p2 < 0.5]
            c.text((SAFE_X, y + 70), 'Tied: ' + ' and '.join(AIS[m2][0] for m2 in tied), font('sans', 'SemiBold', 44), FG, 'lm')
            c.text((SAFE_X + 520, y + 70), money(rows[0][1], e), font('mono', 'SemiBold', 40), UP if rows[0][1] > 0.5 else DOWN if rows[0][1] < -0.5 else MUTED, 'lm')
            rest = '   '.join(f'{AIS[m2][0]} {money(p2, e)}' for m2, p2 in rows if m2 not in tied)
            if rest:
                c.text((W - SAFE_X, y + 70), rest, c.fit(rest, 'mono', 'Regular', 26, 380, 20), MUTED, 'rm')
        else:
            mid, p = rows[0]
            c.d.rectangle([SAFE_X, y + 52, SAFE_X + 8, y + 88], fill=AIS[mid][1])
            c.text((SAFE_X + 24, y + 70), AIS[mid][0], font('sans', 'SemiBold', 44), FG, 'lm')
            c.text((SAFE_X + 300, y + 70), money(p, e), font('mono', 'SemiBold', 40), UP if p > 0.5 else DOWN if p < -0.5 else MUTED, 'lm')
            rest = '   '.join(f'{k}  {AIS[m2][0]} {money(p2, e)}' for k, (m2, p2) in zip(('2nd', '3rd'), rows[1:3]))
            c.text((W - SAFE_X, y + 70), rest, c.fit(rest, 'mono', 'Regular', 26, 560, 20), MUTED, 'rm')
        y += rh
    c.footer()
    return c.save(path)


# ---------- covers: the first slide, built to read at thumbnail size (huge type, few elements)
def _glow(c, color, xy=(1180, 330), r=420):
    from PIL import ImageFilter
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(layer)
    rgb = tuple(int(color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    g.ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=rgb + (46,))
    layer = layer.filter(ImageFilter.GaussianBlur(140))
    c.im = Image.alpha_composite(c.im.convert('RGBA'), layer).convert('RGB')
    c.d = ImageDraw.Draw(c.im)


def races_led(table):
    led = {k: [] for k in AIS}
    for e in ORDER:
        rows = table.get(e) or []
        if len(rows) > 1 and rows[0][1] - rows[1][1] >= 0.5:
            led[rows[0][0]].append(e)
    return led


def moment_cover(m, path, glow=True):
    """Lead change: the new leader's name huge, the margin huge, the three in this race below."""
    race, who, over = m['race'], m['who'], m['over']
    prof = m.get('profit') or {}
    if race not in LABEL or who not in AIS or over not in AIS or set(prof) != set(AIS):
        raise QualityError('moment data incomplete')
    at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
    c = Card()
    if glow:
        _glow(c, AIS[who][1])
    c.header(f'DAY {day_of(at)} OF 32')
    c.text((SAFE_X, 300), f'LEAD CHANGE · {LABEL[race].upper()}', font('mono', 'SemiBold', 36), AMBER, 'lm', tracking=4)
    name_f = c.fit(AIS[who][0], 'sans', 'Bold', 330, W - 2 * SAFE_X, 200)
    c.text((SAFE_X, 345), AIS[who][0], name_f, AIS[who][1], 'lt')
    y = 345 + int(name_f.size * 1.02)
    c.text((SAFE_X, y), 'takes the lead', font('sans', 'Bold', 150), FG, 'lt')
    y += 190
    c.text((SAFE_X, y), f'in {LABEL[race]}', font('sans', 'Medium', 70), MUTED, 'lt')
    y += 130
    amt = money(m['lead'], race).lstrip('+')
    af = font('mono', 'SemiBold', 150)
    c.text((SAFE_X, y), amt, af, FG, 'lt')
    c.text((SAFE_X + af.getlength(amt) + 30, y + 95), f'ahead of {AIS[over][0]}', font('sans', 'Medium', 52), MUTED, 'lm')
    y = 1270
    ids = sorted(prof, key=lambda k: -prof[k])
    for i, mid in enumerate(ids):
        c.d.rectangle([SAFE_X, y + 14, SAFE_X + 10, y + 82], fill=AIS[mid][1])
        c.text((SAFE_X + 40, y + 48), AIS[mid][0], font('sans', 'SemiBold', 58), FG, 'lm')
        v = prof[mid]
        c.text((W - SAFE_X, y + 48), money(v, race), font('mono', 'SemiBold', 54), UP if v > 0.5 else DOWN if v < -0.5 else MUTED, 'rm')
        y += 104
    c.footer()
    return c.save(path)


def daily_cover(table, n, when, big, path, glow=True, swipe=True):
    """Day N: who leads the most races (names huge), races led per AI, and the biggest move. Slide 2 has every race."""
    if not table or any(e not in table for e in ORDER):
        raise QualityError('daily data incomplete')
    led = races_led(table)
    order = sorted(AIS, key=lambda k: -len(led[k]))
    top = [k for k in order if len(led[k]) == len(led[order[0]])]
    c = Card()
    if glow:
        _glow(c, AIS[top[0]][1] if len(top) == 1 else AMBER)
    c.header(f'DAY {n} OF 32')
    c.text((SAFE_X, 300), f'DAY {n} RESULTS · {when.strftime("%a %b %-d").upper()}', font('mono', 'SemiBold', 36), AMBER, 'lm', tracking=4)
    if len(top) == 1:
        nf = c.fit(AIS[top[0]][0], 'sans', 'Bold', 300, W - 2 * SAFE_X, 180)
        c.text((SAFE_X, 345), AIS[top[0]][0], nf, AIS[top[0]][1], 'lt')
        y = 345 + int(nf.size * 1.02)
        c.text((SAFE_X, y), f'leads {len(led[top[0]])} of 10 races', font('sans', 'Bold', 128), FG, 'lt')
        y += 170
    else:
        nf = font('sans', 'Bold', 150)
        y = 360
        for k in top:
            c.text((SAFE_X, y), AIS[k][0], nf, AIS[k][1], 'lt'); y += 160
        c.text((SAFE_X, y), f'tied at {len(led[top[0]])} races each', font('sans', 'Bold', 100), FG, 'lt')
        y += 140
    # races led, per AI: three big tiles
    y = max(y + 40, 900)
    tw = (W - 2 * SAFE_X - 2 * 30) / 3
    for i, k in enumerate(order):
        x = SAFE_X + i * (tw + 30)
        c.d.rounded_rectangle([x, y, x + tw, y + 250], radius=18, fill=PANEL, outline=LINE, width=2)
        c.d.rectangle([x, y, x + tw, y + 10], fill=AIS[k][1])
        c.text((x + 30, y + 70), AIS[k][0], font('sans', 'SemiBold', 48), FG, 'lm')
        c.text((x + 30, y + 165), str(len(led[k])), font('mono', 'SemiBold', 110), AIS[k][1], 'lm')
        c.text((x + 30 + font('mono', 'SemiBold', 110).getlength(str(len(led[k]))) + 18, y + 185), 'races led', font('sans', 'Regular', 32), MUTED, 'lm')
    y += 310
    if big:
        _, mid, e, d, pct = big
        c.text((SAFE_X, y), 'BIGGEST MOVE TODAY', font('mono', 'Medium', 28), MUTED, 'lm', tracking=3)
        line = f'{AIS[mid][0]} in {LABEL.get(e, e)}  {money(d, e)}'
        c.text((SAFE_X, y + 66), line, c.fit(line, 'sans', 'SemiBold', 64, W - 2 * SAFE_X, 36), UP if d > 0.5 else DOWN if d < -0.5 else FG, 'lm')
    c.text((SAFE_X, 1470), 'Ten separate races, each judged on its own. Final scoring Nov 28.', font('sans', 'Regular', 34), MUTED, 'lm')
    if swipe:
        c.text((W - SAFE_X, 1560), 'Swipe for all ten races  →', font('mono', 'SemiBold', 32), AMBER, 'rm')
    c.footer()
    return c.save(path)


# ---------- stories (9:16): the cover, framed for a phone screen, clear of Instagram's own buttons at the top and bottom
SW, SH = 1440, 2560


def story(cover_jpg, path, top='NEW ON PAPER TRADES', bottom='Every trade, live: papertrades.ai', glow_color=None):
    cov = Image.open(cover_jpg).convert('RGB')
    if cov.size != (W, H):
        raise QualityError('story cover has the wrong size')
    im = Image.new('RGB', (SW, SH), BG)
    im.paste(cov, (0, 380))
    if glow_color:   # one soft glow across the whole story, so there is no seam where the cover sits
        from PIL import ImageFilter
        layer = Image.new('RGBA', (SW, SH), (0, 0, 0, 0)); g = ImageDraw.Draw(layer)
        rgb = tuple(int(glow_color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        g.ellipse([1180 - 560, 760 - 560, 1180 + 560, 760 + 560], fill=rgb + (40,))
        layer = layer.filter(ImageFilter.GaussianBlur(180))
        im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    d = ImageDraw.Draw(im)
    f1, f2 = font('mono', 'SemiBold', 40), font('sans', 'SemiBold', 54)
    for s, f, y, col in ((top, f1, 300, AMBER), (bottom, f2, 2260, FG)):
        w = f.getlength(s)
        if w > SW - 2 * SAFE_X:
            raise QualityError('story text too long')
        d.text(((SW - w) / 2, y), s, font=f, fill=col, anchor='lm')
    im.save(path, 'JPEG', quality=95, subsampling=0, optimize=True)
    return path
