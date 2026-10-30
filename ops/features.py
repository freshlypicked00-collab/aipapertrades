"""Feature posts for Instagram (owner, Oct 30: "post what you think is best for today, more creative than boring words, hand-drawn
arrows, in the website's theme"). Each function draws one carousel from the race's own data, in the site's look (ops/postcard.py),
with chalk-style hand-drawn arrows, loops and underlines. The same quality gate applies: nothing outside the safe area, nothing missing.
"""
import math
import random

import postcard as pc
from postcard import AIS, AMBER, BG, DOWN, FG, LINE, MUTED, PANEL, SAFE_X, UP, W, Card, QualityError, font


# ---------- hand-drawn marks (a slightly wobbly double stroke, like chalk or a marker)
def _bez(p0, p1, p2, p3, n=60):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _stroke(card, pts, color, width, seed):
    rnd = random.Random(seed)
    for k in range(2):   # two passes, slightly apart: the hand-drawn look
        jit = [(x + rnd.uniform(-1.6, 1.6), y + rnd.uniform(-1.6, 1.6)) for x, y in pts]
        card.d.line(jit, fill=color, width=max(2, width - k * 2), joint='curve')


def _head(card, tip, prev, color, width, size=34):
    ang = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
    for s in (-1, 1):
        a = ang + math.pi + s * 0.5
        end = (tip[0] + size * math.cos(a), tip[1] + size * math.sin(a))
        _stroke(card, [tip, ((tip[0] + end[0]) / 2 + s * 1.5, (tip[1] + end[1]) / 2), end], color, width, hash((tip, s)))


def arrow(card, p0, p1, p2, p3, color=FG, width=7, seed=1):
    """A curved hand-drawn arrow from p0 to p3 (p1, p2 bend it)."""
    pts = _bez(p0, p1, p2, p3)
    _stroke(card, pts, color, width, seed)
    _head(card, pts[-1], pts[-6], color, width)


def loop_arrow(card, start, end, color=FG, width=7, seed=2, r=46):
    """An arrow with a little curl in the middle (like the loopy sketch arrows)."""
    mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    pts = _bez(start, (start[0], my), (mx - r, my + r), (mx, my), 30)
    pts += [(mx + r * math.cos(t), my - r + r * math.sin(t)) for t in [math.pi / 2 + i * 2 * math.pi / 40 for i in range(41)]]
    pts += _bez((mx, my), (mx + r, my + r), (end[0], my), end, 30)
    _stroke(card, pts, color, width, seed)
    _head(card, pts[-1], pts[-6], color, width)


def underline(card, x0, x1, y, color=AMBER, width=6, seed=3):
    rnd = random.Random(seed)
    pts = [(x0 + (x1 - x0) * i / 30, y + math.sin(i / 3.0) * 3 + rnd.uniform(-1, 1)) for i in range(31)]
    _stroke(card, pts, color, width, seed)


def circle(card, box, color=AMBER, width=6, seed=4):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 + 22, (y1 - y0) / 2 + 18
    pts = [(cx + rx * math.cos(t) * (1 + 0.03 * math.sin(3 * t)), cy + ry * math.sin(t)) for t in [-0.5 + i * (2 * math.pi + 0.5) / 80 for i in range(81)]]
    _stroke(card, pts, color, width, seed)


def para(card, x, y, s, f, color, max_w, gap=1.28):
    for line in card.wrap(s, f, max_w):
        card.text((x, y), line, f, color, 'lt')
        y += int(f.size * gap)
    return y


def kicker(card, y, s, color=UP):
    card.text((SAFE_X, y), s, font('mono', 'SemiBold', 32), color, 'lm', tracking=5)


# ---------- post 1: Gemini sold all its crypto 16 minutes before the Binance hack
def binance(prefix, standings, sell_px, reason):
    paths = []
    gem, amb = AIS['gemini'][1], AMBER
    # 1. the hook
    c = Card(); pc._glow(c, gem); c.header('CRYPTO RACE · OCT 29')
    kicker(c, 330, 'GENIUS OR LUCK?')
    f = font('sans', 'Bold', 300)
    c.text((SAFE_X, 380), '16 min', f, FG, 'lt')
    underline(c, SAFE_X + 10, SAFE_X + f.getlength('16 min') - 10, 700, amb, 9)
    y = para(c, SAFE_X, 760, 'Gemini sold all its crypto 16 minutes before the US$2.5 billion Binance hack.', font('sans', 'SemiBold', 74), FG, W - 2 * SAFE_X)
    para(c, SAFE_X, y + 30, 'Did it know something? We checked the timeline.', font('sans', 'Regular', 46), MUTED, W - 2 * SAFE_X)
    c.text((W - SAFE_X - 120, 1470), 'swipe', font('mono', 'SemiBold', 34), amb, 'rm')
    loop_arrow(c, (W - SAFE_X - 330, 1340), (W - SAFE_X - 40, 1470), amb, 7)
    c.footer(); paths.append(c.save(f'{prefix}-1.jpg'))
    # 2. the timeline
    c = Card(); pc._glow(c, gem, xy=(1200, 900)); c.header('THE TIMELINE · ET')
    kicker(c, 300, 'THURSDAY, OCT 29')
    rows = [('4:08 p.m.', 'Gemini sells all its Bitcoin and Ethereum', f'Bitcoin filled at US${sell_px:,.0f}, a normal price', gem),
            ('4:24 p.m.', 'The first hacked money leaves Binance', 'US$388M in Ethereum, the earliest on-chain sign', DOWN),
            ('5:16 p.m.', 'Binance\'s ex-CEO: "It does look like a hack"', 'Changpeng Zhao, on X', MUTED),
            ('By 9:30 p.m.', 'Binance confirms the hack; over US$2.5B frozen', 'Bitcoin fell about 5% and BNB about 10% that night', MUTED)]
    y = 380
    tops = []
    for i, (t, a, b, col) in enumerate(rows):
        c.d.ellipse([SAFE_X, y + 6, SAFE_X + 30, y + 36], fill=col)
        c.text((SAFE_X + 60, y + 22), t, font('mono', 'SemiBold', 44), col if i < 2 else FG, 'lm')
        yy = para(c, SAFE_X + 60, y + 60, a, font('sans', 'SemiBold', 46), FG, W - 2 * SAFE_X - 60 - 300)
        yy = para(c, SAFE_X + 60, yy + 4, b, font('sans', 'Regular', 32), MUTED, W - 2 * SAFE_X - 60 - 300)
        tops.append(y)
        if i < len(rows) - 1:
            arrow(c, (SAFE_X + 15, yy + 8), (SAFE_X - 10, yy + 30), (SAFE_X + 30, yy + 40), (SAFE_X + 15, yy + 66), MUTED, 5, seed=10 + i)
        y = yy + 70
    # the 16 minutes, circled
    t0, t1 = tops[0] + 22, tops[1] + 22   # the 16 minutes, bracketed between the sale and the first hacked transfer
    c.text((W - SAFE_X, (t0 + t1) / 2 - 30), '16', font('sans', 'Bold', 110), amb, 'rm')
    c.text((W - SAFE_X, (t0 + t1) / 2 + 50), 'minutes', font('sans', 'Bold', 48), amb, 'rm')
    arrow(c, (W - SAFE_X - 150, t0 - 10), (W - SAFE_X - 330, t0 + 20), (W - SAFE_X - 330, t1 - 30), (W - SAFE_X - 200, t1), amb, 6, seed=21)
    if y > 1500:
        raise QualityError('timeline overflows')
    c.footer(); paths.append(c.save(f'{prefix}-2.jpg'))
    # 3. did it know?
    c = Card(); pc._glow(c, amb); c.header('DID IT KNOW?')
    f = font('sans', 'Bold', 260)
    c.text((SAFE_X, 300), 'No.', f, FG, 'lt')
    circle(c, (SAFE_X, 330, SAFE_X + f.getlength('No.'), 560), amb, 8)
    y = para(c, SAFE_X, 660, 'Its reason, written at 4:08 p.m.:', font('mono', 'SemiBold', 34), MUTED, W - 2 * SAFE_X)
    c.d.rectangle([SAFE_X, y + 20, SAFE_X + 10, y + 20 + 330], fill=gem)
    y2 = para(c, SAFE_X + 50, y + 30, '“' + reason.rstrip('.') + '.”', font('sans', 'Regular', 50), FG, W - 2 * SAFE_X - 50)
    if y2 > y + 360:
        raise QualityError('quote too long')
    y = y + 400
    y = para(c, SAFE_X, y, 'No mention of Binance. It sold for inflation, the Fed and a tech selloff, then got lucky.', font('sans', 'SemiBold', 50), amb, W - 2 * SAFE_X)
    para(c, SAFE_X, y + 24, 'And it can\'t cheat: the race runner fills every trade at the live price, at that moment.', font('sans', 'Regular', 40), MUTED, W - 2 * SAFE_X)
    c.footer(); paths.append(c.save(f'{prefix}-3.jpg'))
    # 4. the crypto race now
    c = Card(); pc._glow(c, gem, xy=(1150, 600)); c.header('CRYPTO RACE · NOW')
    kicker(c, 320, 'WHO LEADS CRYPTO')
    c.text((SAFE_X, 370), 'Cash won the day', c.fit('Cash won the day', 'sans', 'Bold', 130, W - 2 * SAFE_X), FG, 'lt')
    y = 600
    for i, (mid, p) in enumerate(standings):
        c.d.rounded_rectangle([SAFE_X, y, W - SAFE_X - 110, y + 170], radius=18, fill=PANEL, outline=LINE, width=2)
        c.d.rectangle([SAFE_X, y, SAFE_X + 12, y + 170], fill=AIS[mid][1])
        c.text((SAFE_X + 50, y + 85), ['1st', '2nd', '3rd'][i], font('mono', 'SemiBold', 54), amb if i == 0 else MUTED, 'lm')
        c.text((SAFE_X + 230, y + 85), AIS[mid][0], font('sans', 'Bold', 70), FG, 'lm')
        c.text((W - SAFE_X - 150, y + 85), pc.money(p, 'Crypto'), font('mono', 'SemiBold', 62), UP if p > 0.5 else DOWN if p < -0.5 else FG, 'rm')
        y += 196
    c.text((W - SAFE_X, y + 60), 'all in cash since 4:08 p.m.', font('sans', 'SemiBold', 44), gem, 'rm')
    arrow(c, (W - SAFE_X - 40, y + 20), (W - SAFE_X + 10, y - 200), (W - SAFE_X + 10, 760), (W - SAFE_X - 60, 685), gem, 6, seed=31)
    c.text((SAFE_X, y + 130), 'Profit since the Oct 28 restart, Crypto race only', font('sans', 'Regular', 34), MUTED, 'lm')
    c.footer(); paths.append(c.save(f'{prefix}-4.jpg'))
    # 5. your call
    c = Card(); pc._glow(c, amb, xy=(700, 900), r=600); c.header('YOUR CALL')
    kicker(c, 330, 'COMMENT ONE WORD')
    c.text((SAFE_X, 400), 'GENIUS', font('sans', 'Bold', 220), UP, 'lt')
    c.text((SAFE_X + 40, 650), 'or', font('sans', 'Regular', 90), MUTED, 'lt')
    c.text((SAFE_X, 760), 'LUCK?', font('sans', 'Bold', 220), DOWN, 'lt')
    arrow(c, (W - SAFE_X - 40, 480), (W - SAFE_X + 10, 700), (W - SAFE_X - 60, 900), (W - SAFE_X - 260, 1080), amb, 8, seed=41)
    y = para(c, SAFE_X, 1110, 'Three AIs. C$100,000 each in ten races. Every trade live, with its reason.', font('sans', 'SemiBold', 48), FG, W - 2 * SAFE_X)
    c.text((SAFE_X, y + 50), 'Follow @papertrades.ai for the rest of the race', font('mono', 'SemiBold', 34), amb, 'lm')
    c.footer(); paths.append(c.save(f'{prefix}-5.jpg'))
    return paths


# ---------- post 2: the AIs grade each other
def grades(prefix, picks, tally):
    """picks: [(grader, graded, grade, what, text)]; tally: {ai: {'received': Counter, 'given': Counter}}."""
    paths = []
    c = Card(); pc._glow(c, AMBER); c.header('REPORT CARDS')
    kicker(c, 330, 'AI VS AI')
    f = font('sans', 'Bold', 168)
    c.text((SAFE_X, 380), 'They grade', f, FG, 'lt')
    c.text((SAFE_X, 560), 'each other.', f, AMBER, 'lt')
    underline(c, SAFE_X + 10, SAFE_X + f.getlength('each other.') - 10, 770, AMBER, 9)
    y = para(c, SAFE_X, 830, 'Every trade and bet gets an A to F from the other two AIs, anonymously, judged only on what was known at the time.', font('sans', 'Regular', 50), FG, W - 2 * SAFE_X)
    para(c, SAFE_X, y + 20, 'Nobody got off easy.', font('sans', 'SemiBold', 56), AMBER, W - 2 * SAFE_X)
    c.text((W - SAFE_X - 120, 1470), 'swipe', font('mono', 'SemiBold', 34), AMBER, 'rm')
    loop_arrow(c, (W - SAFE_X - 330, 1340), (W - SAFE_X - 40, 1470), AMBER, 7)
    c.footer(); paths.append(c.save(f'{prefix}-1.jpg'))
    for i, (gr, gd, g, what, text) in enumerate(picks, 2):
        c = Card(); pc._glow(c, AIS[gd][1]); c.header(f'GRADE {i - 1} OF {len(picks)}')
        c.text((SAFE_X, 330), AIS[gr][0], font('sans', 'Bold', 70), AIS[gr][1], 'lm')
        gw = font('sans', 'Bold', 70).getlength(AIS[gr][0])
        arrow(c, (SAFE_X + gw + 30, 330), (SAFE_X + gw + 110, 290), (SAFE_X + gw + 190, 370), (SAFE_X + gw + 270, 330), FG, 6, seed=50 + i)
        c.text((SAFE_X + gw + 300, 330), AIS[gd][0], font('sans', 'Bold', 70), AIS[gd][1], 'lm')
        big = font('sans', 'Bold', 420)
        col = DOWN if g[0] in 'DF' else UP if g[0] in 'AB' else AMBER
        c.text((W - SAFE_X - 30, 420), g, big, col, 'rt')
        bb = c.d.textbbox((W - SAFE_X - 30, 420), g, font=big, anchor='rt')
        circle(c, bb, col, 8, seed=60 + i)
        y = para(c, SAFE_X, 470, what, font('sans', 'SemiBold', 54), FG, 760)
        y = max(y, 900) + 20
        c.d.rectangle([SAFE_X, y, SAFE_X + 10, y + 300], fill=AIS[gr][1])
        y2 = para(c, SAFE_X + 50, y + 6, '“' + text.rstrip('.') + '.”', font('sans', 'Regular', 52), FG, W - 2 * SAFE_X - 50)
        c.text((SAFE_X + 50, y2 + 30), '— ' + AIS[gr][0] + ', grading ' + AIS[gd][0], font('mono', 'Medium', 32), MUTED, 'lm')
        if y2 > 1460:
            raise QualityError('grade slide overflows')
        c.footer(); paths.append(c.save(f'{prefix}-{i}.jpg'))
    # the tally: grades each AI received, as a stacked bar, and how many F's each one handed out
    c = Card(); pc._glow(c, AMBER, xy=(1100, 600)); c.header('THE TALLY SO FAR')
    kicker(c, 320, 'GRADES RECEIVED')
    c.text((SAFE_X, 370), 'Who gets the best marks?', c.fit('Who gets the best marks?', 'sans', 'Bold', 104, W - 2 * SAFE_X), FG, 'lt')
    COL = {'A': '#3ddc84', 'B': '#a6e36f', 'C': '#ffd166', 'D': '#ff9f5a', 'F': '#ff5a4e'}
    y = 560
    order = sorted(tally, key=lambda m: -(sum({'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}[k] * v for k, v in tally[m]['received'].items() if k in COL) / max(1, sum(v for k, v in tally[m]['received'].items() if k in COL))))
    for mid in order:
        rec = tally[mid]['received']; n = sum(rec.get(k, 0) for k in COL)
        if not n:
            raise QualityError('no grades to tally')
        gpa = sum({'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}[k] * rec.get(k, 0) for k in COL) / n
        c.text((SAFE_X, y + 30), AIS[mid][0], font('sans', 'Bold', 60), AIS[mid][1], 'lm')
        c.text((W - SAFE_X, y + 30), f'average {gpa:.1f} of 4 · {n} grades', font('mono', 'Medium', 32), MUTED, 'rm')
        x, bw = SAFE_X, W - 2 * SAFE_X
        for k in 'ABCDF':
            w = bw * rec.get(k, 0) / n
            if w > 0:
                c.d.rectangle([x, y + 80, x + w, y + 150], fill=COL[k])
                if w > 60:
                    c.text((x + w / 2, y + 115), k, font('sans', 'Bold', 40), BG, 'mm')
            x += w
        y += 220
    hard = max(tally, key=lambda m: tally[m]['given'].get('F', 0))
    line = f"Toughest grader: {AIS[hard][0]}, with {tally[hard]['given'].get('F', 0)} F's handed out"
    c.text((SAFE_X, y + 40), line, c.fit(line, 'sans', 'SemiBold', 50, W - 2 * SAFE_X), AMBER, 'lm')
    para(c, SAFE_X, y + 100, 'Every grade, with its reason, is under each decision on papertrades.ai. Grades never change the score.', font('sans', 'Regular', 38), MUTED, W - 2 * SAFE_X)
    c.text((W - SAFE_X, 1528), 'Who grades fairest? Comment  →', font('mono', 'SemiBold', 30), AMBER, 'rm')
    c.footer(); paths.append(c.save(f'{prefix}-{len(picks) + 2}.jpg'))
    return paths
