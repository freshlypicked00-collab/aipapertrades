"""Corrected "Days 1-4: who led each race" carousel (owner, Oct 31, 10:54 p.m. ET).

The Day 1 and Day 2 results cards posted on Instagram on Oct 30 named the wrong leader in three races (Day 1 China, Day 2 Crypto,
Day 2 Play it safe): they used Claude's stale and rounded prices, which the Oct 31 audit corrected. This carousel replaces them and
fills the feed's gap (Days 3 and 4 went out only as stories). Every number is the audited daily close in data.json's ledgers
(profit since the Oct 28 restart at each day's 00:00 UTC close, each race on its own). Races are never added together (owner's rule).

    python3 ops/corrected_days.py      # writes social/corrected-days1-4-v1-{1..6}.jpg and prints the caption
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc  # noqa: E402
from postcard import AIS, AMBER, DOWN, FG, LINE, MUTED, ORDER, PANEL, SAFE_X, UP, W, Card, QualityError, font  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'social')
PREFIX = 'corrected-days1-4-v1'
DAYS = [('2026-10-28', 'Wed, Oct 28'), ('2026-10-29', 'Thu, Oct 29'), ('2026-10-30', 'Fri, Oct 30'), ('2026-10-31', 'Sat, Oct 31')]
# what the Oct 30 cards said (read off the posted images) where the leader was wrong
OLD = {('2026-10-28', 'China'): ('Claude', 'China', 58), ('2026-10-29', 'Crypto'): ('Claude', 'Crypto', -882), ('2026-10-29', 'Safe'): ('Claude', 'Safe', -248)}

D = json.load(open(os.path.join(ROOT, 'data.json')))


def closes(day):
    """{race: {model: profit at that day's close}} from the audited ledgers."""
    out = {}
    for m in ('claude', 'gemini', 'chatgpt'):
        rows = D['ledger'] if m == 'claude' else D['models'][m]['ledger']
        for r in rows:
            if r.get('day') == day and r.get('portfolio') in ORDER and r.get('close') is not None:
                out.setdefault(r['portfolio'], {})[m] = round(float(r['close']) - 100000, 2)
    for race in ORDER:
        if len(out.get(race, {})) != 3:
            raise QualityError(f'{day} {race}: missing a value')
    return out


def leaders(vals):
    best = max(vals.values())
    return [m for m in ('claude', 'gemini', 'chatgpt') if abs(vals[m] - best) < 0.5], best


def names(ms):
    return ' & '.join(AIS[m][0] for m in ms)


def cover():
    c = Card(); pc._glow(c, AMBER); c.header('CORRECTED · DAYS 1–4')
    c.text((SAFE_X, 330), 'THE AI MONEY RACE · OCT 28 – 31', font('mono', 'SemiBold', 34), UP, 'lm', tracking=5)
    c.text((SAFE_X, 400), 'Days 1–4', font('sans', 'Bold', 230), FG, 'lt')
    c.text((SAFE_X, 660), 'who led each race', font('sans', 'Bold', 120), AMBER, 'lt')
    y = 880
    for line in c.wrap('This replaces our Day 1 and Day 2 cards. Our audit found three races where they named the wrong leader, '
                       'all in Claude’s favour. Every number here is the audited one.', font('sans', 'SemiBold', 54), W - 2 * SAFE_X):
        c.text((SAFE_X, y), line, font('sans', 'SemiBold', 54), FG, 'lt'); y += 72
    y += 30
    for line in c.wrap('Each race on its own: profit since the Oct 28 restart, at each day’s close. Pretend money, real prices.',
                       font('sans', 'Regular', 42), W - 2 * SAFE_X):
        c.text((SAFE_X, y), line, font('sans', 'Regular', 42), MUTED, 'lt'); y += 58
    c.text((W - SAFE_X, 1480), 'Swipe for each day →', font('mono', 'SemiBold', 34), AMBER, 'rm')
    c.footer(); return c.save(os.path.join(OUT, f'{PREFIX}-1.jpg'))


def day_slide(i, day, label):
    vals = closes(day)
    c = Card(); c.header(f'DAY {i} OF 32 · {label.upper()}')
    c.text((SAFE_X, 290), f'DAY {i} RESULTS · AUDITED', font('mono', 'SemiBold', 34), UP, 'lm', tracking=5)
    c.text((SAFE_X, 325), f'Day {i}: who led', font('sans', 'Bold', 110), FG, 'lt')
    y, rh = 475, 100
    for race in ORDER:
        ms, best = leaders(vals[race])
        fixed = (day, race) in OLD
        c.d.rounded_rectangle([SAFE_X, y, W - SAFE_X, y + rh - 14], radius=10, fill=PANEL, outline=AMBER if fixed else LINE, width=3 if fixed else 2)
        c.text((SAFE_X + 28, y + (rh - 14) // 2), pc.LABEL[race], font('sans', 'SemiBold', 44), FG, 'lm')
        col = AIS[ms[0]][1] if len(ms) == 1 else FG
        who = 'All three tied' if len(ms) == 3 else names(ms) + (' (tie)' if len(ms) > 1 else '')
        f_who = font('sans', 'Bold', 44)
        c.text((W - SAFE_X - 270, y + (rh - 14) // 2), who, f_who, col, 'rm')
        c.text((W - SAFE_X - 28, y + (rh - 14) // 2), pc.money(best, race), font('mono', 'SemiBold', 40), UP if best > 0.5 else DOWN if best < -0.5 else MUTED, 'rm')
        if fixed:
            c.text((SAFE_X + 28 + font('sans', 'SemiBold', 44).getlength(pc.LABEL[race]) + 20, y + (rh - 14) // 2), 'CORRECTED', font('mono', 'SemiBold', 24), AMBER, 'lm', tracking=3)
        y += rh
    c.text((SAFE_X, y + 20), 'The leader and its profit since the Oct 28 restart, at the day’s close (00:00 UTC).', font('sans', 'Regular', 32), MUTED, 'lt')
    if y + 62 > 1565:
        raise QualityError('day slide overflows')
    c.footer(); return c.save(os.path.join(OUT, f'{PREFIX}-{i + 1}.jpg'))


def changes():
    c = Card(); pc._glow(c, AMBER, xy=(1200, 900)); c.header('WHAT CHANGED')
    c.text((SAFE_X, 330), 'THE THREE CORRECTIONS', font('mono', 'SemiBold', 34), AMBER, 'lm', tracking=5)
    y = 420
    for (day, race), (_, _, old) in OLD.items():
        n = [d for d, _ in DAYS].index(day) + 1
        vals = closes(day)
        ms, best = leaders(vals[race])
        c.text((SAFE_X, y), f'Day {n} · {pc.LABEL[race]}', font('sans', 'Bold', 60), FG, 'lt'); y += 84
        c.text((SAFE_X, y), f'We said: Claude leads, {pc.money(old, race)}', font('sans', 'Regular', 46), MUTED, 'lt'); y += 62
        now = f'Audited: {names(ms)} lead{"s" if len(ms) == 1 else ""}, {pc.money(best, race)} (Claude {pc.money(vals[race]["claude"], race)})'
        c.text((SAFE_X, y), now, c.fit(now, 'sans', 'SemiBold', 46, W - 2 * SAFE_X), AMBER, 'lt'); y += 110
    y += 10
    for line in c.wrap('Why: stale and rounded prices in Claude’s own records (Claude runs this site). Gemini’s and ChatGPT’s numbers were right. '
                       'The full audit is public: papertrades.ai, Rules & Audit.', font('sans', 'Regular', 42), W - 2 * SAFE_X):
        c.text((SAFE_X, y), line, font('sans', 'Regular', 42), FG, 'lt'); y += 58
    if y > 1540:
        raise QualityError('changes slide overflows')
    c.footer(); return c.save(os.path.join(OUT, f'{PREFIX}-6.jpg'))


CAPTION = ('Correction + catch-up: who led each race on Days 1–4. 🏁\n\n'
           'Our Day 1 and Day 2 cards named the wrong leader in three races (Day 1 China stocks, Day 2 Crypto, Day 2 Play it safe). '
           'They used stale and rounded prices from Claude’s own records, all in Claude’s favour; our audit caught it and we’ve '
           'replaced those posts with this one. Gemini’s and ChatGPT’s numbers were right.\n\n'
           'Each race is scored on its own. Every trade, reason and correction is public at PaperTrades.AI (link in bio).\n\n'
           'Pretend money, real prices. Not financial advice. We never take deposits.\n\n'
           '#AI #ChatGPT #Claude #Gemini #StockMarket')

if __name__ == '__main__':
    paths = [cover()] + [day_slide(i, d, l) for i, (d, l) in enumerate(DAYS, 1)] + [changes()]
    for p in paths:
        print(p)
    print('\n' + CAPTION)
