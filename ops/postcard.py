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
        """Where to find us: X, Telegram and Discord (with their logos), the site, and the disclaimer."""
        self.d.line([(SAFE_X, 1575), (W - SAFE_X, 1575)], fill=LINE, width=3)
        x, y = SAFE_X, 1630
        for icon, label in (('x', '@PaperTradesAI'), ('telegram', '@PaperTradesAI'), ('discord', 'Discord in bio')):
            path = os.path.join(HERE, 'icons', icon + '.png')
            if not os.path.exists(path):
                raise QualityError(f'missing icon {icon}')
            ic = Image.open(path).convert('RGBA').resize((44, 44), Image.LANCZOS)
            self.im.paste(ic, (int(x), y - 22), ic)
            f = font('mono', 'Medium', 28)
            self.text((x + 60, y), label, f, FG, 'lm')
            x += 60 + f.getlength(label) + 64
        if x - 64 > W - SAFE_X:
            raise QualityError('find-us row too wide')
        self.text((SAFE_X, 1712), 'papertrades.ai', font('mono', 'SemiBold', 40), FG, 'lm')
        self.text((W - SAFE_X, 1712), 'Pretend money · real prices · not advice', font('sans', 'Regular', 28), MUTED, 'rm')

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
    y, rh = 520, 104
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


def brand_block(c, y=268):
    """Always first: Claude vs Gemini vs ChatGPT, stacked in their colors, like the launch post."""
    c.text((SAFE_X, y), 'THE AI MONEY RACE · OCT 28 – NOV 28', font('mono', 'SemiBold', 30), UP, 'lm', tracking=4)
    nf, vf = font('sans', 'Bold', 150), font('sans', 'Medium', 84)
    y += 42
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        x = SAFE_X
        if i:
            c.text((x, y + 104), 'vs', vf, MUTED, 'ls'); x += vf.getlength('vs') + 26
        c.text((x, y + 128), AIS[k][0], nf, AIS[k][1], 'ls')
        y += 150
    return y + 20


def title_block(c, y, kicker, title, color=FG, max_lines=2):
    """The bold title of what's going on."""
    c.d.line([(SAFE_X, y), (SAFE_X + 120, y)], fill=AMBER, width=6)
    c.text((SAFE_X, y + 46), kicker, font('mono', 'SemiBold', 32), AMBER, 'lm', tracking=4)
    size = 104
    while size >= 64:
        f = font('sans', 'Bold', size)
        lines = c.wrap(title, f, W - 2 * SAFE_X)
        if len(lines) <= max_lines:
            break
        size -= 4
    else:
        raise QualityError('title too long')
    y += 86
    for ln in lines:
        c.text((SAFE_X, y), ln, f, color, 'lt'); y += int(size * 1.08)
    return y + 24


def moment_cover(m, path, glow=True):
    """Lead change: the three AIs, then the title (who took the lead, where, by how much), then that race's standings."""
    race, who, over = m['race'], m['who'], m['over']
    prof = m.get('profit') or {}
    if race not in LABEL or who not in AIS or over not in AIS or set(prof) != set(AIS):
        raise QualityError('moment data incomplete')
    at = datetime.fromisoformat(m['at'].replace('Z', '+00:00'))
    c = Card()
    if glow:
        _glow(c, AIS[who][1])
    c.header(f'DAY {day_of(at)} OF 32')
    y = brand_block(c)
    y = title_block(c, y + 10, f'LEAD CHANGE · {LABEL[race].upper()}',
                    f'{AIS[who][0]} takes the lead in {LABEL[race]}, {money(m["lead"], race).lstrip("+")} ahead of {AIS[over][0]}')
    y = max(y, 1250)
    ids = sorted(prof, key=lambda k: -prof[k])
    for i, mid in enumerate(ids):
        c.d.rectangle([SAFE_X, y + 12, SAFE_X + 9, y + 70], fill=AIS[mid][1])
        c.text((SAFE_X + 34, y + 41), f"{['1st', '2nd', '3rd'][i]}  {AIS[mid][0]}", font('sans', 'SemiBold', 50), FG, 'lm')
        v = prof[mid]
        c.text((W - SAFE_X, y + 41), money(v, race), font('mono', 'SemiBold', 48), UP if v > 0.5 else DOWN if v < -0.5 else MUTED, 'rm')
        y += 88
    if y > 1560:
        raise QualityError('moment cover overflows')
    c.footer()
    return c.save(path)


def daily_cover(table, n, when, big, path, glow=True, swipe=True):
    """Day N: the three AIs, then the title (who leads the most races), races led per AI, the biggest move."""
    if not table or any(e not in table for e in ORDER):
        raise QualityError('daily data incomplete')
    led = races_led(table)
    order = sorted(AIS, key=lambda k: -len(led[k]))
    top = [k for k in order if len(led[k]) == len(led[order[0]])]
    c = Card()
    if glow:
        _glow(c, AIS[top[0]][1] if len(top) == 1 else AMBER)
    c.header(f'DAY {n} OF 32')
    y = brand_block(c)
    if len(top) == 1:
        title = f'{AIS[top[0]][0]} leads {len(led[top[0]])} of the 10 races'
    elif len(top) == 2:
        title = f'{AIS[top[0]][0]} and {AIS[top[1]][0]} lead {len(led[top[0]])} races each'
    else:
        title = f'All three lead {len(led[top[0]])} races each'
    y = title_block(c, y + 10, f'DAY {n} RESULTS · {when.strftime("%a %b %-d").upper()}', title)
    y = max(y, 1225)
    tw = (W - 2 * SAFE_X - 2 * 24) / 3
    for i, k in enumerate(order):
        x = SAFE_X + i * (tw + 24)
        c.d.rounded_rectangle([x, y, x + tw, y + 150], radius=16, fill=PANEL, outline=LINE, width=2)
        c.d.rectangle([x, y, x + tw, y + 8], fill=AIS[k][1])
        c.text((x + 26, y + 52), AIS[k][0], font('sans', 'SemiBold', 40), FG, 'lm')
        nf = font('mono', 'SemiBold', 64)
        c.text((x + 26, y + 112), str(len(led[k])), nf, AIS[k][1], 'lm')
        c.text((x + 26 + nf.getlength(str(len(led[k]))) + 14, y + 116), 'races led', font('sans', 'Regular', 28), MUTED, 'lm')
    y += 190
    if big:
        _, mid, e, d, pct = big
        line = f'Biggest move: {AIS[mid][0]} in {LABEL.get(e, e)} {money(d, e)}'
        c.text((SAFE_X, y + 20), line, c.fit(line, 'sans', 'SemiBold', 46, W - 2 * SAFE_X - (0 if not swipe else 0), 30), UP if d > 0.5 else DOWN if d < -0.5 else FG, 'lm')
    if swipe:
        c.text((W - SAFE_X, 1528), 'Swipe for all ten races  →', font('mono', 'SemiBold', 30), AMBER, 'rm')
    if y + 40 > 1560:
        raise QualityError('daily cover overflows')
    c.footer()
    return c.save(path)


def title_slide(n, when, path):
    """Slide 1 of the daily post: just "Day N results" and the date, big and calm, plus where we are in the race."""
    if not 1 <= n <= 32:
        raise QualityError('day number out of range')
    c = Card()
    _glow(c, AMBER, xy=(1100, 520), r=520)
    c.header(f'DAY {n} OF 32')
    c.text((SAFE_X, 360), 'THE AI MONEY RACE', font('mono', 'SemiBold', 34), UP, 'lm', tracking=6)
    big = c.fit(f'Day {n}', 'sans', 'Bold', 400, W - 2 * SAFE_X, 220)
    c.text((SAFE_X, 400), f'Day {n}', big, FG, 'lt')
    y = 400 + int(big.size * 1.0)
    c.text((SAFE_X, y), 'results', font('sans', 'Bold', 210), AMBER, 'lt')
    y += 260
    c.text((SAFE_X, y), when.strftime('%A, %B %-d, %Y'), font('mono', 'Medium', 46), FG, 'lt')
    # where we are: 32 days, today's filled
    y += 130
    seg_w, gap = (W - 2 * SAFE_X - 31 * 8) / 32, 8
    for i in range(32):
        x = SAFE_X + i * (seg_w + gap)
        c.d.rounded_rectangle([x, y, x + seg_w, y + 22], radius=4, fill=AMBER if i < n else LINE)
    c.text((SAFE_X, y + 64), f'Day {n} of 32', font('mono', 'Medium', 30), MUTED, 'lm')
    c.text((W - SAFE_X, y + 64), 'Final scoring Nov 28', font('mono', 'Medium', 30), MUTED, 'rm')
    # the three AIs
    y += 150
    x = SAFE_X
    for k in ('claude', 'gemini', 'chatgpt'):
        c.d.ellipse([x, y - 14, x + 28, y + 14], fill=AIS[k][1])
        f = font('sans', 'SemiBold', 48)
        c.text((x + 44, y), AIS[k][0], f, FG, 'lm')
        x += 44 + f.getlength(AIS[k][0]) + 70
    c.text((W - SAFE_X, 1528), 'Swipe for the results  →', font('mono', 'SemiBold', 30), AMBER, 'rm')
    if y + 40 > 1500:
        raise QualityError('title slide overflows')
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


# ---------- the "What is Paper Trades?" explainer: a 4-slide carousel for new visitors (pinned), plus its story
def intro_slides(table, prefix):
    """1) what it is, 2) nobody touches the trades, 3) the ten races and who leads each now, 4) where to follow. Returns paths."""
    if not table or any(e not in table for e in ORDER):
        raise QualityError('intro data incomplete')
    paths = []
    # 1. the cover
    c = Card()
    _glow(c, AMBER, xy=(1150, 420), r=560)
    c.header('START HERE')
    y = brand_block(c)
    y = title_block(c, y + 10, 'WHAT IS PAPER TRADES?', 'Three AIs. C$100,000 each. Ten races. One month.', max_lines=3)
    c.text((SAFE_X, max(y + 10, 1300)), 'Real prices. Pretend money. Every trade public.', font('sans', 'Medium', 50), MUTED, 'lt')
    c.text((W - SAFE_X, 1528), 'Swipe to see how it works  →', font('mono', 'SemiBold', 30), AMBER, 'rm')
    c.footer(); paths.append(c.save(prefix + '-1.jpg'))
    # 2. the rules in four lines
    c = Card()
    c.header('HOW IT WORKS')
    y = title_block(c, 300, 'NO HUMAN TOUCHES THE TRADES', 'The AIs decide everything themselves', max_lines=2)
    pts = [('🧠', 'Each AI picks its own trades and bets, and explains every one in its own words.'),
           ('📈', 'Real-world prices: stocks, crypto, gold, oil, currencies, China, sports odds.'),
           ('⚡', 'Every trade is posted the second it happens, wins and losses alike.'),
           ('🏁', 'Each race is scored on its own. Final scoring: Saturday, November 28.')]
    y += 40
    bf, num = font('sans', 'Medium', 50), font('mono', 'Bold', 44)
    for i, (_, t) in enumerate(pts):
        c.d.rounded_rectangle([SAFE_X, y, SAFE_X + 74, y + 74], radius=14, fill=PANEL, outline=AMBER, width=3)
        c.text((SAFE_X + 37, y + 39), str(i + 1), num, AMBER, 'mm')
        lines = c.wrap(t, bf, W - 2 * SAFE_X - 110)
        for j, ln in enumerate(lines):
            c.text((SAFE_X + 110, y + 8 + j * 62), ln, bf, FG, 'lt')
        y += max(74, len(lines) * 62) + 46
    if y > 1540:
        raise QualityError('intro slide 2 overflows')
    c.footer(); paths.append(c.save(prefix + '-2.jpg'))
    # 3. the ten races and who leads each right now
    c = Card()
    c.header('THE TEN RACES')
    y = title_block(c, 270, 'WHO LEADS EACH RACE · ' + datetime.now(NY).strftime('%b %-d').upper(), 'Ten races, ten winners', max_lines=1)
    y += 6
    rf, lf = font('sans', 'SemiBold', 44), font('sans', 'Bold', 44)
    for e in ORDER:
        rows = table.get(e) or []
        c.d.line([(SAFE_X, y), (W - SAFE_X, y)], fill=LINE, width=2)
        c.text((SAFE_X, y + 43), LABEL[e], rf, FG, 'lm')
        if len(rows) > 1 and rows[0][1] - rows[1][1] >= 0.5:
            k = rows[0][0]
            c.d.ellipse([W - SAFE_X - lf.getlength(AIS[k][0]) - 44, y + 30, W - SAFE_X - lf.getlength(AIS[k][0]) - 18, y + 56], fill=AIS[k][1])
            c.text((W - SAFE_X, y + 43), AIS[k][0], lf, AIS[k][1], 'rm')
        else:
            c.text((W - SAFE_X, y + 43), 'Tied', lf, MUTED, 'rm')
        y += 86
    if y > 1560:
        raise QualityError('intro slide 3 overflows')
    c.footer(); paths.append(c.save(prefix + '-3.jpg'))
    # 4. follow along
    c = Card()
    _glow(c, UP, xy=(1150, 520), r=520)
    c.header('FOLLOW THE RACE')
    y = title_block(c, 300, 'WHO WILL WIN?', 'Watch it happen, live', max_lines=2)
    items = [('Instagram', '@papertrades.ai', 'Daily results and every lead change'),
             ('Telegram', '@PaperTradesAI', 'Every trade, the second it happens'),
             ('Website', 'papertrades.ai', 'The full ledger, rules and audit'),
             ('X', '@PaperTradesAI', 'Highlights and race news')]
    y += 30
    for name, handle, why in items:
        c.d.rounded_rectangle([SAFE_X, y, W - SAFE_X, y + 170], radius=18, fill=PANEL, outline=LINE, width=2)
        c.text((SAFE_X + 40, y + 52), name.upper(), font('mono', 'SemiBold', 30), MUTED, 'lm', tracking=3)
        c.text((SAFE_X + 40, y + 112), handle, font('sans', 'Bold', 60), FG, 'lm')
        c.text((W - SAFE_X - 40, y + 112), why, c.fit(why, 'sans', 'Regular', 34, 560, 24), MUTED, 'rm')
        y += 196
    if y > 1560:
        raise QualityError('intro slide 4 overflows')
    c.footer(); paths.append(c.save(prefix + '-4.jpg'))
    return paths


# ---------- "Day 1 results", remade to grab attention (owner's request, Oct 29): a 5-slide carousel about the first night
def _grad_text(c, xy, s, f, c1, c2):
    """Big text filled with a left-to-right gradient (c1 -> c2)."""
    from PIL import ImageChops
    x, y = xy
    l, t, r, b = c.d.textbbox((x, y), s, font=f)
    mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).text((x, y), s, font=f, fill=255)
    grad = Image.new('RGB', (W, H), c1); gd = ImageDraw.Draw(grad)
    rgb = lambda h: tuple(int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    a, z = rgb(c1), rgb(c2)
    for xx in range(max(0, l), min(W, r + 1)):
        k = (xx - l) / max(1, r - l)
        gd.line([(xx, t), (xx, b)], fill=tuple(int(a[i] + (z[i] - a[i]) * k) for i in range(3)))
    c.im.paste(grad, (0, 0), mask)
    c.d = ImageDraw.Draw(c.im)
    return b


def _pill(c, x, y, w, h, fill, outline):
    c.d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2 if h < 120 else 28, fill=fill, outline=outline, width=3)


def day1_remake(table, swings, when_label, prefix):
    """swings: list of (who, amount, what) for the night's biggest wins and losses, any AI. Returns 5 paths."""
    if not table or any(e not in table for e in ORDER) or not swings:
        raise QualityError('day 1 data incomplete')
    led = races_led(table)
    paths = []
    best = max(swings, key=lambda s: s[1]); worst = min(swings, key=lambda s: s[1])
    # 1. the hook
    c = Card()
    _glow(c, UP, xy=(260, 760), r=520); _glow(c, DOWN, xy=(1250, 1250), r=460)
    c.header('DAY 1 RESULTS')
    c.text((SAFE_X, 300), 'THE AI MONEY RACE · ' + when_label, font('mono', 'SemiBold', 30), MUTED, 'lm', tracking=4)
    y = _grad_text(c, (SAFE_X - 8, 330), 'DAY 1', font('sans', 'Bold', 380), AMBER, UP)
    y = title_block(c, y + 40, 'THE FIRST NIGHT', 'Sports decided the first night', max_lines=2)
    for who, amt, what in (best, worst):
        col = UP if amt >= 0 else DOWN
        _pill(c, SAFE_X, y, W - 2 * SAFE_X, 150, PANEL, col)
        c.text((SAFE_X + 40, y + 52), AIS[who][0].upper(), font('mono', 'SemiBold', 30), AIS[who][1], 'lm', tracking=3)
        c.text((SAFE_X + 40, y + 108), what, c.fit(what, 'sans', 'Medium', 42, 760, 28), FG, 'lm')
        c.text((W - SAFE_X - 40, y + 76), ('+' if amt >= 0 else '−') + f'C${abs(amt):,.0f}', font('sans', 'Bold', 84), col, 'rm')
        y += 176
    if y > 1500:
        raise QualityError('day 1 cover overflows')
    c.text((W - SAFE_X, 1528), 'Swipe for every race  →', font('mono', 'SemiBold', 30), AMBER, 'rm')
    c.footer(); paths.append(c.save(prefix + '-1.jpg'))
    # 2. races led
    c = Card()
    c.header('DAY 1 · SCOREBOARD')
    y = title_block(c, 280, 'RACES LED AFTER THE FIRST NIGHT', 'Who is ahead in the ten races', max_lines=2)
    order = sorted(AIS, key=lambda k: -len(led[k]))
    top, base_y, colw = max(1, len(led[order[0]])), 1350, (W - 2 * SAFE_X - 2 * 50) / 3
    for i, k in enumerate(order):
        x = SAFE_X + i * (colw + 50); n = len(led[k]); hgt = int(520 * n / top) if n else 8
        c.d.rounded_rectangle([x, base_y - hgt, x + colw, base_y], radius=22, fill=AIS[k][1])
        c.text((x + colw / 2, base_y - hgt - 70), str(n), font('sans', 'Bold', 130), AIS[k][1], 'mm')
        c.text((x + colw / 2, base_y + 52), AIS[k][0], font('sans', 'SemiBold', 54), FG, 'mm')
    tied = [e for e in ORDER if not (len(table[e]) > 1 and table[e][0][1] - table[e][1][1] >= 0.5)]
    note = (f"{len(tied)} race tied ({', '.join(LABEL[e] for e in tied)}). " if tied else '') + 'Each race is scored on its own; leading can mean losing the least.'
    for j, ln in enumerate(c.wrap(note, font('sans', 'Regular', 34), W - 2 * SAFE_X)[:2]):
        c.text((SAFE_X, 1478 + j * 42), ln, font('sans', 'Regular', 34), MUTED, 'lm')
    c.footer(); paths.append(c.save(prefix + '-2.jpg'))
    # 3. all ten races
    c = Card()
    c.header('DAY 1 · ALL TEN RACES')
    y = title_block(c, 270, 'PROFIT SINCE THE OCT 28 START', 'Ten races, one look', max_lines=1)
    cw, ch, gx, gy = (W - 2 * SAFE_X - 30) / 2, 184, 30, 18
    for i, e in enumerate(ORDER):
        x = SAFE_X + (i % 2) * (cw + gx); yy = y + 6 + (i // 2) * (ch + gy)
        rows = table[e]; tie = not (len(rows) > 1 and rows[0][1] - rows[1][1] >= 0.5)
        lead = rows[0][0]; col = MUTED if tie else AIS[lead][1]
        c.d.rounded_rectangle([x, yy, x + cw, yy + ch], radius=18, fill=PANEL, outline=LINE, width=2)
        c.d.rectangle([x, yy + 18, x + 8, yy + ch - 18], fill=col)
        c.text((x + 32, yy + 40), LABEL[e].upper(), font('mono', 'SemiBold', 24), MUTED, 'lm', tracking=2)
        c.text((x + 32, yy + 90), 'Tied' if tie else AIS[lead][0], font('sans', 'Bold', 50), col, 'lm')
        if not tie:
            c.text((x + cw - 28, yy + 90), money(rows[0][1], e), font('mono', 'SemiBold', 40), UP if rows[0][1] > 0.5 else DOWN if rows[0][1] < -0.5 else MUTED, 'rm')
        bx = x + 32
        for m, p in sorted(rows, key=lambda r: list(AIS).index(r[0])):   # the three AIs, always in the same order
            c.d.rounded_rectangle([bx, yy + 132, bx + (cw - 96) / 3, yy + 150], radius=9, fill=AIS[m][1] if p > 0.5 else LINE if abs(p) <= 0.5 else '#5a2420')
            bx += (cw - 96) / 3 + 16
    if y + 6 + 5 * (ch + gy) > 1580:
        raise QualityError('day 1 grid overflows')
    c.footer(); paths.append(c.save(prefix + '-3.jpg'))
    # 4. the night's biggest swings
    c = Card()
    _glow(c, AMBER, xy=(1150, 600), r=480)
    c.header('DAY 1 · BIGGEST SWINGS')
    y = title_block(c, 280, 'ONE GAME CAN MAKE OR BREAK A NIGHT', 'The biggest wins and losses', max_lines=2)
    y += 20
    for who, amt, what in sorted(swings, key=lambda s: -abs(s[1]))[:6]:
        col = UP if amt >= 0 else DOWN
        c.d.rectangle([SAFE_X, y + 10, SAFE_X + 10, y + 120], fill=AIS[who][1])
        c.text((SAFE_X + 40, y + 40), AIS[who][0], font('sans', 'Bold', 48), AIS[who][1], 'lm')
        c.text((SAFE_X + 40, y + 96), what, c.fit(what, 'sans', 'Regular', 36, 760, 26), FG, 'lm')
        c.text((W - SAFE_X, y + 66), ('+' if amt >= 0 else '−') + f'C${abs(amt):,.0f}', font('sans', 'Bold', 76), col, 'rm')
        y += 150
    if y > 1560:
        raise QualityError('day 1 swings overflow')
    c.footer(); paths.append(c.save(prefix + '-4.jpg'))
    # 5. follow
    c = Card()
    _glow(c, UP, xy=(720, 760), r=600)
    c.header('DAY 2 IS LIVE')
    y = _grad_text(c, (SAFE_X - 6, 300), 'Day 2', font('sans', 'Bold', 300), FG, AMBER)
    y = title_block(c, y + 40, 'WHO WINS ON NOV 28?', 'Follow every trade as it happens', max_lines=2)
    for name, handle in (('Instagram', '@papertrades.ai'), ('Telegram, every trade live', '@PaperTradesAI'), ('The full ledger', 'papertrades.ai')):
        c.text((SAFE_X, y + 30), name.upper(), font('mono', 'SemiBold', 28), MUTED, 'lm', tracking=3)
        c.text((SAFE_X, y + 92), handle, font('sans', 'Bold', 72), FG, 'lm')
        y += 160
    if y > 1560:
        raise QualityError('day 1 follow slide overflows')
    c.footer(); paths.append(c.save(prefix + '-5.jpg'))
    return paths
