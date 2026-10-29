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
    return ('+' if x >= 0 else '−') + ('US$' if race == 'China' else 'C$') + f'{abs(x):,.0f}'


def day_of(dt):
    return (dt.astimezone(NY).date() - datetime(2026, 10, 27).date()).days


class Card:
    def __init__(self):
        self.im = Image.new('RGB', (W, H), BG)
        self.d = ImageDraw.Draw(self.im)

    def text(self, xy, s, f, fill, anchor='la', tracking=0):
        x, y = xy
        if tracking:   # letter-spaced labels, like the site's small uppercase headings
            if anchor[0] == 'r':
                x -= self.width(s, f, tracking)
            for ch in s:
                self.d.text((x, y), ch, font=f, fill=fill, anchor='l' + anchor[1])
                x += f.getlength(ch) + tracking
            box = (xy[0] - (self.width(s, f, tracking) if anchor[0] == 'r' else 0), y - f.size, x, y + f.size)
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
    lines = c.wrap(f'{AIS[who][0]} takes the lead', hf, W - 2 * SAFE_X)
    if len(lines) > 2:
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
        c.text((W - SAFE_X - 40, y + 75), money(v, race), font('mono', 'SemiBold', 60), UP if v >= 0 else DOWN, 'rm')
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
        else:
            mid, p = rows[0]
            c.d.rectangle([SAFE_X, y + 52, SAFE_X + 8, y + 88], fill=AIS[mid][1])
            c.text((SAFE_X + 24, y + 70), AIS[mid][0], font('sans', 'SemiBold', 44), FG, 'lm')
            c.text((SAFE_X + 300, y + 70), money(p, e), font('mono', 'SemiBold', 40), UP if p >= 0 else DOWN, 'lm')
            rest = '   '.join(f'{k}  {AIS[m2][0]} {money(p2, e)}' for k, (m2, p2) in zip(('2nd', '3rd'), rows[1:3]))
            c.text((W - SAFE_X, y + 70), rest, c.fit(rest, 'mono', 'Regular', 26, 560, 20), MUTED, 'rm')
        y += rh
    c.footer()
    return c.save(path)
