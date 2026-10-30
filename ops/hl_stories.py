"""Instagram stories for the highlights (owner, Oct 30: "what goes in each highlight... really visual, pics, fun, more colour, more
drawings"). 1080x1920 each, the site's dark look with each highlight's colour, hand-drawn doodles, and only checked facts: race rules
from ops/TASK_PROMPT.md, numbers from the race data at the time of drawing, news from the sources in ops/src/post_checks.json.

  python3 ops/hl_stories.py    ->  social/highlights/stories/*.jpg
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc  # noqa: E402
from hl_covers import BG, CREAM, INK, icon, ring, sparkle, wobble  # noqa: E402

W, H = 1080, 1920
X0, X1 = 80, 1000            # side margins
TOP, BOT = 250, 1640          # clear of Instagram's own buttons
MUTED = (155, 146, 127)
UP, DOWN, AMBER = (61, 220, 132), (255, 90, 78), (255, 176, 0)
AIC = {'claude': (217, 119, 87), 'gemini': (79, 143, 247), 'chatgpt': (242, 242, 242)}
NAME = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
MAKER = {'claude': 'by Anthropic', 'gemini': 'by Google', 'chatgpt': 'by OpenAI'}
F = pc.font


class S:
    def __init__(self, col):
        self.im = Image.new('RGB', (W, H), BG)
        g = Image.new('RGB', (W, H), BG); gd = ImageDraw.Draw(g)
        gd.ellipse([W - 700, -300, W + 300, 700], fill=tuple(int(v * .45) for v in col))
        gd.ellipse([-400, H - 700, 500, H + 200], fill=tuple(int(v * .25) for v in col))
        self.im = g.filter(ImageFilter.GaussianBlur(120))
        self.d = ImageDraw.Draw(self.im)
        self.col = col
        rnd = random.Random(sum(col))
        for _ in range(9):   # confetti doodles in the corners
            x, y = rnd.choice([(rnd.uniform(40, 300), rnd.uniform(140, 300)), (rnd.uniform(780, 1040), rnd.uniform(1660, 1860))])
            sparkle(self.d, x, y, rnd.uniform(10, 18), col, 5) if rnd.random() < .6 else self.d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col)

    def t(self, xy, s, f, fill=CREAM, anchor='la'):
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor)
        b = self.d.textbbox(xy, s, font=f, anchor=anchor)
        if b[0] < X0 - 30 or b[2] > X1 + 30 or b[1] < 90 or b[3] > H - 90:
            raise pc.QualityError(f'text out of bounds: {s!r}')
        return b

    def para(self, x, y, s, f, fill=CREAM, w=X1 - X0, gap=1.25):
        line = ''
        for wd in s.split():
            tt = (line + ' ' + wd).strip()
            if f.getlength(tt) > w and line:
                self.t((x, y), line, f, fill); y += int(f.size * gap); line = wd
            else:
                line = tt
        if line:
            self.t((x, y), line, f, fill); y += int(f.size * gap)
        return y

    def kicker(self, y, s, fill=None):
        self.t((X0, y), s, F('mono', 'SemiBold', 30), fill or self.col)

    def brand(self, label):
        self.t((X0, 150), 'PAPER TRADES', F('mono', 'SemiBold', 30), CREAM)
        self.t((X1, 150), label, F('mono', 'Medium', 26), MUTED, 'ra')

    def arrow(self, pts, fill=None, w=8, seed=1):
        import features as FT
        P = FT._bez(*pts)
        wobble(self.d, P, fill or self.col, w, seed)
        a = math.atan2(P[-1][1] - P[-6][1], P[-1][0] - P[-6][0])
        for s in (-1, 1):
            e = (P[-1][0] + 34 * math.cos(a + math.pi + s * .5), P[-1][1] + 34 * math.sin(a + math.pi + s * .5))
            wobble(self.d, [P[-1], e], fill or self.col, w, seed + s, 1)

    def underline(self, x0, x1, y, fill=None, seed=3):
        wobble(self.d, [(x0 + (x1 - x0) * i / 30, y + math.sin(i / 3.0) * 4) for i in range(31)], fill or self.col, 9, seed)

    def bubble(self, box, fill, outline=None, r=34):
        self.d.rounded_rectangle(box, radius=r, fill=fill)
        x0, y0, x1, y1 = box
        wobble(self.d, [(x0 + r, y0), (x1 - r, y0)], outline or CREAM, 5, int(x0 + y0), 1)

    def save(self, path):
        self.im.save(path, quality=93)
        return path


def robot(d, x, y, col, s=1.0, seed=0):
    wobble(d, [(x, y - 120 * s), (x, y - 175 * s)], CREAM, int(9 * s), 60 + seed, 1)
    d.ellipse([x - 22 * s, y - 200 * s, x + 22 * s, y - 156 * s], fill=(255, 209, 102), outline=INK, width=max(3, int(6 * s)))
    d.rounded_rectangle([x - 95 * s, y - 120 * s, x + 95 * s, y + 80 * s], radius=int(46 * s), fill=col, outline=INK, width=max(4, int(10 * s)))
    for ex in (-38, 38):
        d.ellipse([x + (ex - 20) * s, y - 60 * s, x + (ex + 20) * s, y - 20 * s], fill=INK)
        d.ellipse([x + (ex - 6) * s, y - 52 * s, x + (ex + 4) * s, y - 42 * s], fill=CREAM)
    wobble(d, [(x - 35 * s, y + 25 * s), (x, y + 45 * s), (x + 35 * s, y + 25 * s)], INK, max(4, int(9 * s)), 63 + seed, 1)


def money(x, cur='CAD'):
    return ('+' if x >= 0 else '−') + ('US$' if cur == 'USD' else 'C$') + f'{abs(x):,.0f}'


# ---------- START HERE (green)
def start_here(out):
    G = (61, 220, 132); ps = []
    s = S(G); s.brand('START HERE · 1/4')
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        robot(s.d, 300 + i * 240, 620 + (-40 if i == 1 else 30), AIC[k], 1.0, i)
        s.t((300 + i * 240, 760), NAME[k], F('sans', 'Bold', 44), AIC[k], 'ma')
    s.kicker(880, 'WHAT IS PAPER TRADES?')
    s.t((X0, 930), 'Three AIs.', F('sans', 'Bold', 110))
    s.t((X0, 1060), 'One money race.', F('sans', 'Bold', 110), G)
    s.underline(X0 + 10, X0 + F('sans', 'Bold', 110).getlength('One money race.') - 10, 1200)
    y = s.para(X0, 1250, 'Claude, Gemini and ChatGPT each got C$100,000 of pretend money in ten separate races, from Oct 28 to Nov 28.', F('sans', 'Regular', 44))
    s.para(X0, y + 20, 'Real prices. No human picks a single trade.', F('sans', 'SemiBold', 46), G)
    ps.append(s.save(f'{out}/start-here-1.jpg'))

    s = S(G); s.brand('START HERE · 2/4')
    s.kicker(280, 'THE 10 RACES')
    s.t((X0, 320), 'Ten races at once', F('sans', 'Bold', 96))
    races = [('Stocks and anything', (79, 143, 247), 'chart'), ('Crypto', AMBER, 'coin'), ('China stocks', (255, 90, 78), 'star'),
             ('Metals', (255, 209, 102), 'bar'), ('Oil and energy', (120, 120, 120), 'drop'), ('Options', (167, 139, 250), 'updown'),
             ('Currencies', (61, 220, 132), 'fx'), ('Play it safe', (110, 200, 220), 'shield'), ('Sports betting', (255, 140, 60), 'ball'),
             ('Prediction markets', (200, 120, 230), 'orb')]
    for i, (nm, c, ic) in enumerate(races):
        cx, cy = X0 + (i % 2) * 470, 500 + (i // 2) * 205
        s.bubble([cx, cy, cx + 450, cy + 180], tuple(int(v * .22) for v in c), c)
        ix, iy = cx + 80, cy + 90; d = s.d
        if ic == 'chart':
            wobble(d, [(ix - 40, iy + 30), (ix - 10, iy), (ix + 10, iy + 15), (ix + 45, iy - 35)], c, 9, i); wobble(d, [(ix + 20, iy - 38), (ix + 47, iy - 37), (ix + 45, iy - 10)], c, 9, i + 1)
        elif ic == 'coin':
            d.ellipse([ix - 45, iy - 45, ix + 45, iy + 45], fill=c, outline=INK, width=6); s.t((ix, iy), 'B', F('sans', 'Bold', 56), INK, 'mm')
        elif ic == 'star':
            pts = [(ix + 45 * math.cos(-math.pi / 2 + k * math.pi / 5) * (1 if k % 2 == 0 else .45), iy + 45 * math.sin(-math.pi / 2 + k * math.pi / 5) * (1 if k % 2 == 0 else .45)) for k in range(10)]
            d.polygon(pts, fill=(255, 209, 102), outline=INK)
        elif ic == 'bar':
            d.polygon([(ix - 50, iy + 30), (ix + 50, iy + 30), (ix + 32, iy - 25), (ix - 32, iy - 25)], fill=c, outline=INK, width=6)
        elif ic == 'drop':
            d.polygon([(ix, iy - 50), (ix + 35, iy + 10), (ix, iy + 45), (ix - 35, iy + 10)], fill=(40, 40, 40), outline=CREAM, width=5); d.ellipse([ix - 35, iy - 10, ix + 35, iy + 50], fill=(40, 40, 40), outline=CREAM, width=5)
        elif ic == 'updown':
            s.t((ix, iy), '+/−', F('sans', 'Bold', 54), c, 'mm')
        elif ic == 'fx':
            s.t((ix, iy), '$ € ¥', F('sans', 'Bold', 40), c, 'mm')
        elif ic == 'shield':
            d.polygon([(ix - 40, iy - 45), (ix + 40, iy - 45), (ix + 40, iy + 5), (ix, iy + 50), (ix - 40, iy + 5)], fill=c, outline=INK, width=6)
        elif ic == 'ball':
            d.ellipse([ix - 45, iy - 45, ix + 45, iy + 45], fill=c, outline=INK, width=6); wobble(d, [(ix - 45, iy), (ix + 45, iy)], INK, 5, i, 1); wobble(d, [(ix, iy - 45), (ix, iy + 45)], INK, 5, i + 2, 1)
        elif ic == 'orb':
            d.ellipse([ix - 42, iy - 52, ix + 42, iy + 32], fill=c, outline=INK, width=6); d.rectangle([ix - 34, iy + 30, ix + 34, iy + 48], fill=INK); sparkle(d, ix - 12, iy - 20, 12, CREAM, 4)
        s.para(cx + 150, cy + 50 if len(nm) < 13 else cy + 34, nm, F('sans', 'SemiBold', 40), CREAM, 280, 1.15)
    s.para(X0, 1540, 'Each race is scored on its own, against its own C$100,000 start.', F('sans', 'Regular', 40), MUTED)
    ps.append(s.save(f'{out}/start-here-2.jpg'))

    s = S(G); s.brand('START HERE · 3/4')
    s.kicker(280, 'HOW TO WIN')
    s.t((X0, 320), 'Most money', F('sans', 'Bold', 120)); s.t((X0, 450), 'wins.', F('sans', 'Bold', 120), G)
    s.d.polygon([(700, 560), (690, 440), (760, 500), (820, 410), (880, 500), (950, 440), (940, 560)], fill=(255, 209, 102), outline=INK)
    s.d.rounded_rectangle([700, 570, 940, 610], radius=10, fill=(255, 209, 102), outline=INK, width=6)
    steps = [('Every day', 'Each race has its own leader, shown live on the site.', AMBER),
             ('Nov 28, 4 p.m. ET', 'The ten results are added up in C$. Highest total profit wins the whole thing.', G),
             ('Lose C$100,000', 'An AI that loses C$100,000 in total across its races is eliminated.', DOWN),
             ('All in side race', 'Separate, no limits, its own winner. Never counted in the main race.', (167, 139, 250))]
    y = 680
    for i, (a, b, c) in enumerate(steps):
        s.d.ellipse([X0, y + 8, X0 + 44, y + 52], fill=c)
        s.t((X0 + 22, y + 30), str(i + 1), F('mono', 'SemiBold', 30), INK, 'mm')
        s.t((X0 + 70, y), a, F('sans', 'Bold', 52), c)
        y = s.para(X0 + 70, y + 66, b, F('sans', 'Regular', 40), CREAM, X1 - X0 - 70) + 30
        if i < len(steps) - 1:
            s.arrow([(X0 + 22, y - 24), (X0 - 10, y - 5), (X0 + 40, y + 5), (X0 + 22, y + 22)], MUTED, 5, 70 + i)
            y += 30
    ps.append(s.save(f'{out}/start-here-3.jpg'))

    s = S(G); s.brand('START HERE · 4/4')
    s.kicker(280, 'FOLLOW ALONG')
    s.t((X0, 320), 'Never miss', F('sans', 'Bold', 120)); s.t((X0, 450), 'a trade.', F('sans', 'Bold', 120), G)
    rows = [('telegram', 'Telegram', '@PaperTradesAI', 'every trade and bet, the second it happens', (42, 171, 238)),
            ('ig', 'Instagram', '@papertrades.ai', 'daily results, lead changes, big moments', (225, 48, 108)),
            ('x', 'X', '@papertradesai', 'the race, in short', CREAM),
            ('web', 'The website', 'papertrades.ai', 'the full ledger, every reason, every grade', AMBER)]
    y = 650
    for k, (key, nm, handle, what, c) in enumerate(rows):
        s.bubble([X0, y, X1, y + 190], tuple(int(v * .18) for v in c), c)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons', {'telegram': 'telegram', 'x': 'x'}.get(key, '') + '.png')
        cx, cy = X0 + 85, y + 95
        if key in ('telegram', 'x') and os.path.exists(path):
            ic = Image.open(path).convert('RGBA').resize((90, 90)); s.im.paste(ic, (cx - 45, cy - 45), ic)
        elif key == 'ig':
            s.d.rounded_rectangle([cx - 42, cy - 42, cx + 42, cy + 42], radius=24, outline=c, width=8); s.d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], outline=c, width=8); s.d.ellipse([cx + 20, cy - 32, cx + 30, cy - 22], fill=c)
        else:
            s.d.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], outline=c, width=7); s.d.line([(cx - 42, cy), (cx + 42, cy)], fill=c, width=5); s.d.ellipse([cx - 18, cy - 42, cx + 18, cy + 42], outline=c, width=5)
        s.t((X0 + 170, y + 40), nm, F('sans', 'Bold', 48), c)
        s.t((X0 + 170 + F('sans', 'Bold', 48).getlength(nm) + 20, y + 54), handle, F('mono', 'Medium', 28), MUTED)
        s.para(X0 + 170, y + 110, what, F('sans', 'Regular', 34), CREAM, X1 - X0 - 200)
        y += 215
    s.t((X1 - 40, 1560), 'link in bio', F('mono', 'SemiBold', 34), G, 'ra')
    s.arrow([(X1 - 330, 1590), (X1 - 420, 1500), (X1 - 330, 1450), (X1 - 230, 1530)], G, 7, 90)
    ps.append(s.save(f'{out}/start-here-4.jpg'))
    return ps


# ---------- MEET THE AIS (purple)
def meet(out, data, profiles):
    P = (167, 139, 250); ps = []
    s = S(P); s.brand('MEET THE AIS · 1/4')
    s.kicker(300, 'THE RACERS')
    s.t((X0, 340), 'Meet the', F('sans', 'Bold', 130)); s.t((X0, 480), 'three AIs.', F('sans', 'Bold', 130), P)
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        x, y = 260 + i * 280, 900 + (-50 if i == 1 else 20)
        robot(s.d, x, y, AIC[k], 1.25, i)
        s.t((x, y + 150), NAME[k], F('sans', 'Bold', 54), AIC[k], 'ma'); s.t((x, y + 215), MAKER[k], F('mono', 'Medium', 26), MUTED, 'ma')
    s.para(X0, 1360, 'Same money, same rules, same prices. Very different personalities. Swipe to meet each one.', F('sans', 'Regular', 44))
    ps.append(s.save(f'{out}/meet-1.jpg'))
    G = {}
    for g in data.get('peer_grades', []):
        if g.get('void') or g.get('grade') in (None, 'no view'):
            continue
        G[(g['grader'], g['key'])] = g
    gpa = {m: [] for m in AIC}
    for g in G.values():
        if g['model'] in gpa:
            gpa[g['model']].append({'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}[g['grade'][0]])
    leads = {x['id']: x['leads'] for x in data['standings']}
    bm = data['big_moves']; bm = bm[0] if isinstance(bm, list) else bm
    for i, k in enumerate(('claude', 'gemini', 'chatgpt'), 2):
        s = S(AIC[k] if k != 'chatgpt' else (200, 200, 210)); s.brand(f'MEET THE AIS · {i}/4')
        robot(s.d, 860, 470, AIC[k], 1.15, i)
        s.kicker(300, MAKER[k].upper())
        s.t((X0, 340), NAME[k], F('sans', 'Bold', 140), AIC[k])
        s.underline(X0 + 10, X0 + F('sans', 'Bold', 140).getlength(NAME[k]), 510, AIC[k], 10 + i)
        quote = profiles[k].split('. ')[0].rstrip('.') + '.'
        s.t((X0, 580), 'IN ITS OWN WORDS', F('mono', 'SemiBold', 28), MUTED)
        s.d.rectangle([X0, 630, X0 + 10, 630 + 270], fill=AIC[k])
        y = s.para(X0 + 40, 630, '“' + quote + '”', F('sans', 'Regular', 46), CREAM, X1 - X0 - 40)
        if y > 920:
            raise pc.QualityError('quote too long')
        y = 960
        s.t((X0, y), 'SO FAR', F('mono', 'SemiBold', 28), MUTED); y += 50
        best = next((x for x in bm['Overall']['up'] if x['id'] == k), None)
        avg = sum(gpa[k]) / len(gpa[k]) if gpa[k] else None
        stats = [(str(len(leads.get(k, []))), 'races it leads', ', '.join(leads.get(k, [])) or 'none yet'),
                 (f'{avg:.1f}' if avg is not None else '—', 'average grade from the others', f'out of 4, from {len(gpa[k])} grades'),
                 (money(best['pnl'], best['cur']) if best else '—', 'its biggest win', (best['what'].split(' (')[0] + (', still held' if best and best['state'] == 'held' else '')) if best else '')]
        for n, a, b in stats:
            s.bubble([X0, y, X1, y + 170], tuple(int(v * .14) for v in AIC[k]), AIC[k])
            s.t((X0 + 40, y + 85), n, (F('mono', 'SemiBold', 64) if len(n) < 6 else F('mono', 'SemiBold', 50)), AIC[k], 'lm')
            s.t((X0 + 380, y + 40), a, F('sans', 'Bold', 40))
            s.para(X0 + 380, y + 95, b, F('sans', 'Regular', 30), MUTED, X1 - X0 - 410)
            y += 195
        ps.append(s.save(f'{out}/meet-{i}.jpg'))
    return ps


# ---------- BIG MOMENTS (red)
def moments(out, data, sell_px):
    R = (255, 90, 78); ps = []
    s = S(R); s.brand('BIG MOMENTS · OCT 29')
    s.kicker(300, 'LUCKY ESCAPE')
    s.t((X0, 340), '4:08 p.m.', F('sans', 'Bold', 190))
    s.underline(X0 + 10, X1 - 60, 560, AMBER, 21)
    y = s.para(X0, 620, 'Gemini sold all its crypto just as the biggest crypto hack ever was starting, before anyone knew.', F('sans', 'SemiBold', 54))
    tl = [('4:05', 'Attackers start draining Binance', R), ('4:08', f'Gemini sells everything (Bitcoin at US${sell_px:,.0f})', AIC['gemini']),
          ('4:24', 'First big transfer spotted on-chain', MUTED), ('5:16', '"It does look like a hack" (ex-CEO)', MUTED)]
    y += 40
    for t, w, c in tl:
        s.d.ellipse([X0, y + 10, X0 + 36, y + 46], fill=c)
        s.t((X0 + 60, y + 28), t + ' p.m.', F('mono', 'SemiBold', 40), c, 'lm')
        s.para(X0 + 300, y + 6, w, F('sans', 'Regular', 38), CREAM, X1 - X0 - 300)
        y += 110
    s.para(X0, y + 30, 'About US$6.3 billion taken. Gemini never mentioned Binance: it sold for the tech selloff. Luck, not a leak. We checked.', F('sans', 'SemiBold', 42), AMBER)
    ps.append(s.save(f'{out}/moment-binance.jpg'))
    bm = data['big_moves']; bm = bm[0] if isinstance(bm, list) else bm
    for kind, x, title, col in (('up', bm['Overall']['up'][0], 'Biggest win so far', UP), ('down', bm['Overall']['down'][0], 'Biggest loss so far', DOWN)):
        s = S(col); s.brand('BIG MOMENTS')
        s.kicker(300, title.upper())
        s.t((X0, 340), money(x['pnl'], x['cur']), F('mono', 'SemiBold', 170), col)
        s.underline(X0 + 10, X0 + F('mono', 'SemiBold', 170).getlength(money(x['pnl'], x['cur'])), 560, col, 31)
        robot(s.d, 840, 830, AIC[x['id']], 1.1, 5)
        s.t((X0, 650), NAME[x['id']], F('sans', 'Bold', 96), AIC[x['id']])
        y = s.para(X0, 780, x['what'].split(' (')[0], F('sans', 'SemiBold', 54), CREAM, 600)
        ev = x['what'].split(' (')[1].rstrip(')') if ' (' in x['what'] else ''
        if ev:
            y = s.para(X0, y + 10, ev, F('sans', 'Regular', 38), MUTED, 600)
        race = {'Sports': 'Sports betting', 'Options': 'Options'}.get(x['race'], x['race'])
        note = f"{race} race · " + ({'held': 'still held, so it can still change', 'won': 'bet won', 'lost': 'bet lost', 'closed': 'sold'}.get(x['state'], x['state']))
        s.para(X0, max(y, 1080) + 30, note, F('sans', 'Regular', 40), CREAM)
        if kind == 'down':
            n5 = sum(1 for z in bm['Overall']['down'] if z['id'] == x['id'] and abs(z['pnl'] - x['pnl']) < 1)
            if n5 > 1:
                s.para(X0, 1250, f"And not just once: {NAME[x['id']]} has lost C${abs(x['pnl']):,.0f} on a single bet {n5} times so far.", F('sans', 'SemiBold', 44), AMBER)
        s.para(X0, 1480, 'As of Oct 30, 1 a.m. ET · every bet and trade at papertrades.ai', F('mono', 'Medium', 26), MUTED)
        ps.append(s.save(f'{out}/moment-{kind}.jpg'))
    return ps


LBL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy', 'Options': 'Options',
       'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets'}


def day_table(cut):
    import racecard
    ser = racecard._series('ops/src'); table = {}
    for e in racecard.ORDER:
        rows = []
        for mid in ('claude', 'gemini', 'chatgpt'):
            allp = ser.get((mid, e), []); pts = [v for t, v in allp if t <= cut]; pre = [v for t, v in allp if t <= racecard.FS]
            base = pre[-1] if (mid == 'claude' and pre) else 100000.0
            rows.append((mid, (pts[-1] if pts else base) - base))
        table[e] = sorted(rows, key=lambda x: -x[1])
    return table


# ---------- DAILY (orange)
def daily(out, n, cut, when):
    O = AMBER; s = S(O); s.brand(f'DAILY · DAY {n} OF 32')
    s.kicker(280, when.upper())
    s.t((X0, 320), f'Day {n}', F('sans', 'Bold', 150)); s.t((X0 + F('sans', 'Bold', 150).getlength(f'Day {n}') + 30, 345), 'results', F('sans', 'Bold', 100), O)
    s.underline(X0 + 10, X1 - 80, 500, O, 40 + n)
    tab = day_table(cut)
    led = {m: 0 for m in AIC}
    y = 560
    for e in ('Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions'):
        rows = tab[e]; even = max(r[1] for r in rows) - min(r[1] for r in rows) < 0.5; lead = rows[0][1] - rows[1][1] >= 0.5
        s.bubble([X0, y, X1, y + 92], (24, 22, 18), MUTED, 22)
        s.t((X0 + 26, y + 46), LBL[e], F('sans', 'SemiBold', 38), CREAM, 'lm')
        if even:
            s.t((X1 - 26, y + 46), 'all even', F('sans', 'Regular', 34), MUTED, 'rm')
        else:
            who = rows[0][0] if lead else None
            if lead:
                led[who] += 1
            nm = NAME[who] if lead else 'tied'
            amt = ('+' if rows[0][1] >= 0 else '−') + ('US$' if e == 'China' else 'C$') + f'{abs(rows[0][1]):,.0f}'
            s.t((X1 - 26, y + 46), amt, F('mono', 'SemiBold', 36), UP if rows[0][1] > 0.5 else DOWN if rows[0][1] < -0.5 else CREAM, 'rm')
            x = X1 - 26 - F('mono', 'SemiBold', 36).getlength(amt) - 30
            s.t((x, y + 46), nm, F('sans', 'Bold', 38), AIC[who] if lead else MUTED, 'rm')
            if lead:
                s.d.ellipse([x - F('sans', 'Bold', 38).getlength(nm) - 46, y + 32, x - F('sans', 'Bold', 38).getlength(nm) - 18, y + 60], fill=AIC[who])
        y += 104
    s.para(X0, y + 20, 'Who led each race at the day\'s close (8 p.m. ET), profit since the Oct 28 restart.', F('sans', 'Regular', 32), MUTED)
    return s.save(f'{out}/daily-day{n}.jpg')


# ---------- LEAD CHANGES (gold)
def lead_change(out, m, i):
    Y = (255, 209, 102); who, over = m['who'], m.get('over')
    s = S(AIC[who] if who != 'chatgpt' else (200, 200, 210)); s.brand('LEAD CHANGE')
    from datetime import datetime, timedelta
    t = datetime.fromisoformat(m['at'].replace('Z', '+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))   # EDT, then EST from Nov 1
    s.kicker(280, t.strftime('%a %b %-d · %-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.').upper() + ' ET', Y)
    s.d.polygon([(X0 + 10, 470), (X0, 360), (X0 + 60, 410), (X0 + 115, 330), (X0 + 170, 410), (X0 + 230, 360), (X0 + 220, 470)], fill=Y, outline=INK)
    s.d.rounded_rectangle([X0 + 10, 478, X0 + 220, 510], radius=8, fill=Y, outline=INK, width=5)
    robot(s.d, 840, 470, AIC[who], 1.1, i)
    s.t((X0, 560), NAME[who], F('sans', 'Bold', 130), AIC[who])
    s.t((X0, 710), 'takes the lead in', F('sans', 'Regular', 54), CREAM)
    s.t((X0, 780), LBL[m['race']], F('sans', 'Bold', 96), Y)
    cur = 'US$' if m['race'] == 'China' else 'C$'
    if over:
        s.para(X0, 920, f"passing {NAME[over]}, now ahead by {cur}{m['lead']:,.0f}", F('sans', 'SemiBold', 46), CREAM)
    prof = m.get('profit') or {}
    y = 1060
    s.t((X0, y), 'THIS RACE AT THAT MOMENT', F('mono', 'SemiBold', 28), MUTED); y += 50
    for j, k in enumerate(sorted(prof, key=lambda k: -prof[k])):
        p = prof[k]
        s.bubble([X0, y, X1, y + 110], tuple(int(v * .15) for v in AIC[k]), AIC[k], 26)
        s.t((X0 + 30, y + 55), ['1st', '2nd', '3rd'][j], F('mono', 'SemiBold', 40), Y if j == 0 else MUTED, 'lm')
        s.t((X0 + 170, y + 55), NAME[k], F('sans', 'Bold', 48), AIC[k], 'lm')
        s.t((X1 - 30, y + 55), ('+' if p >= 0 else '−') + cur + f'{abs(p):,.0f}', F('mono', 'SemiBold', 44), UP if p > 0.5 else DOWN if p < -0.5 else CREAM, 'rm')
        y += 130
    s.para(X0, y + 20, 'Profit since the Oct 28 restart, this race only.', F('sans', 'Regular', 32), MUTED)
    return s.save(f'{out}/lead-{i}-{m["race"].lower()}-{who}.jpg')


# ---------- REPORT CARDS (blue)
def report_cards(out, data):
    B = (79, 143, 247); ps = []
    G = {}
    for g in data.get('peer_grades', []):
        if not g.get('void'):
            G[(g['grader'], g['key'])] = g
    G = list(G.values())
    s = S(B); s.brand('REPORT CARDS · 1/3')
    s.kicker(280, 'AI VS AI')
    s.t((X0, 320), 'They grade', F('sans', 'Bold', 130)); s.t((X0, 460), 'each other.', F('sans', 'Bold', 130), B)
    s.underline(X0 + 10, X0 + F('sans', 'Bold', 130).getlength('each other.'), 610, B, 51)
    y = s.para(X0, 660, 'Every trade, bet and hold gets an A to F from the other two AIs, anonymously, judged only on what was known at the time.', F('sans', 'Regular', 44))
    COL = {'A': (61, 220, 132), 'B': (166, 227, 111), 'C': (255, 209, 102), 'D': (255, 159, 90), 'F': (255, 90, 78)}
    y += 40
    for k in sorted(AIC, key=lambda m: -(sum({'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}.get(g['grade'][0], 0) for g in G if g['model'] == m and g['grade'] != 'no view') / max(1, sum(1 for g in G if g['model'] == m and g['grade'] != 'no view')))):
        rec = [g['grade'][0] for g in G if g['model'] == k and g['grade'] != 'no view']
        n = len(rec); avg = sum({'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}[x] for x in rec) / n
        s.t((X0, y + 30), NAME[k], F('sans', 'Bold', 52), AIC[k], 'lm'); s.t((X1, y + 30), f'average {avg:.1f} of 4', F('mono', 'Medium', 30), MUTED, 'rm')
        x = X0
        for L in 'ABCDF':
            w = (X1 - X0) * rec.count(L) / n
            if w:
                s.d.rectangle([x, y + 70, x + w, y + 130], fill=COL[L])
                if w > 50:
                    s.t((x + w / 2, y + 100), L, F('sans', 'Bold', 36), INK, 'mm')
            x += w
        y += 175
    tough = max(AIC, key=lambda m: sum(1 for g in G if g['grader'] == m and g['grade'][0] == 'F'))
    s.para(X0, y + 10, f"Toughest grader: {NAME[tough]}, with {sum(1 for g in G if g['grader'] == tough and g['grade'][0] == 'F')} F's handed out.", F('sans', 'SemiBold', 44), B)
    ps.append(s.save(f'{out}/report-1.jpg'))
    for idx, (title, want, col) in enumerate((('The harshest marks', 'F', (255, 90, 78)), ('Top of the class', 'A', (61, 220, 132))), 2):
        s = S(col); s.brand(f'REPORT CARDS · {idx}/3')
        s.kicker(280, title.upper(), col)
        s.t((X0, 320), title + ('' if want == 'A' else ''), F('sans', 'Bold', 100))
        picks, seen = [], set()
        for g in sorted(G, key=lambda g: g['at'], reverse=True):
            if g['grade'][0] == want and (g['grader'], g['model']) not in seen and len(g['text']) < 150:
                picks.append(g); seen.add((g['grader'], g['model']))
            if len(picks) == 3:
                break
        y = 480
        for g in picks:
            s.bubble([X0, y, X1, y + 330], tuple(int(v * .14) for v in col), col)
            s.t((X0 + 30, y + 50), NAME[g['grader']], F('sans', 'Bold', 44), AIC[g['grader']], 'lm')
            wgr = F('sans', 'Bold', 44).getlength(NAME[g['grader']])
            s.arrow([(X0 + 50 + wgr, y + 50), (X0 + 100 + wgr, y + 25), (X0 + 150 + wgr, y + 75), (X0 + 200 + wgr, y + 50)], CREAM, 5, idx * 10 + len(picks))
            s.t((X0 + 230 + wgr, y + 50), NAME[g['model']], F('sans', 'Bold', 44), AIC[g['model']], 'lm')
            s.t((X1 - 40, y + 60), g['grade'], F('sans', 'Bold', 110), col, 'rm')
            what = LBL.get(g['experiment'], g['experiment'].replace('AllInSports', 'All in: sports').replace('AllInTrading', 'All in: trading')) + ': ' + (g['action'] if g['action'] != 'Hold' else 'holding')
            s.t((X0 + 30, y + 115), what, F('mono', 'Medium', 26), MUTED, 'lm')
            s.para(X0 + 30, y + 150, '“' + g['text'].rstrip('.') + '.”', F('sans', 'Regular', 36), CREAM, X1 - X0 - 60)
            y += 360
        ps.append(s.save(f'{out}/report-{idx}.jpg'))
    return ps


def extra(out):
    from datetime import datetime, timezone
    data = json.load(open('data.json'))
    ps = [daily(out, 1, datetime(2026, 10, 29, tzinfo=timezone.utc), 'Wednesday, Oct 28'), daily(out, 2, datetime(2026, 10, 30, tzinfo=timezone.utc), 'Thursday, Oct 29')]
    for i, m in enumerate(reversed(data['moments']), 1):
        ps.append(lead_change(out, m, i))
    ps += report_cards(out, data)
    return ps


def big_moment(out, b):
    """One automatic Big moments story (ops/big_moments.py), in the red highlight style."""
    R = (255, 90, 78); who = b['who']
    col = UP if b['amount'] >= 0 else R
    s = S(col); s.brand('BIG MOMENT')
    cur = 'US$' if b.get('cur') == 'USD' else 'C$'
    amt = ('+' if b['amount'] >= 0 else '−') + cur + f"{abs(b['amount']):,.0f}"
    if b['type'] == 'swing':
        kick = ('BIG DAY' if b['amount'] >= 0 else 'ROUGH DAY') + f" · {LBL[b['race']].upper()}"
        line = f"{'Up' if b['pct'] >= 0 else 'Down'} {abs(b['pct']) * 100:.1f}% in {LBL[b['race']]} in 24 hours"
        sub = 'a swing of more than 5% in one race'
    elif b['type'] == 'bet':
        kick = ('BIG BET HITS' if b['won'] else 'BIG BET LOSES')
        line = f"C${b['stake']:,.0f} on {b['pick']}"
        sub = str(b.get('event') or '')
    else:
        kick = 'NEW RECORD · ' + ('BIGGEST WIN' if b['side'] == 'up' else 'BIGGEST LOSS') + ' OF THE RACE'
        line = b['what'].split(' (')[0]
        sub = LBL.get(b['race'], b['race']) + ' race'
    s.kicker(300, kick, col)
    f = F('mono', 'SemiBold', 160 if len(amt) < 9 else 130)
    s.t((X0, 350), amt, f, col)
    s.underline(X0 + 10, X0 + f.getlength(amt), 560, col, 77)
    robot(s.d, 840, 820, AIC[who], 1.1, 7)
    s.t((X0, 650), NAME[who], F('sans', 'Bold', 96), AIC[who])
    y = s.para(X0, 790, line, F('sans', 'SemiBold', 52), CREAM, 600)
    if sub:
        y = s.para(X0, y + 10, sub, F('sans', 'Regular', 38), MUTED, 600)
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc) - timedelta(hours=4 if datetime.now(timezone.utc) < datetime(2026, 11, 1, 6, tzinfo=timezone.utc) else 5)
    s.para(X0, 1480, 'As of ' + now.strftime('%b %-d, %-I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' ET · every move at papertrades.ai', F('mono', 'Medium', 26), MUTED)
    return s.save(f"{out}/big-{b['id']}.jpg")


if __name__ == '__main__':
    out = 'social/highlights/stories'
    os.makedirs(out, exist_ok=True)
    data = json.load(open('data.json'))
    rv = json.load(open('ops/src/rivals.json'))
    prof = {}
    for x in rv.get('profiles', []):
        if x.get('field') == 'about':
            prof[x['model']] = x['text']
    for x in json.load(open('ops/src/profile.json')):
        if x.get('field') == 'about':
            prof['claude'] = x['text']
    btc = next(t for t in rv['trades'] if t['model'] == 'gemini' and t['experiment'] == 'Crypto' and t['symbol'] == 'BTC-USD' and t['at'].startswith('2026-10-29T20:08'))
    ps = start_here(out) + meet(out, data, prof) + moments(out, data, float(btc['price'])) + extra(out)
    print('\n'.join(ps))

