"""'Grades of the day' picture: the harshest grade and the best grade the AIs gave each other (all three AIs agreed, Oct 30:
ops/review/social-r2-oct30.json, R4). Both together, never a roast on its own. Quotes are word for word; a long quote is cut at a
word with "…". Same data as the site's "Today's grades" card (data.json "callout" and "praise", the last 24 hours, else 72).

  python3 ops/grades_card.py   -> social/grades-<date>.jpg (feed, 1440x1800) and social/story-grades-<date>.jpg (1440x2560)
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc
from postcard import AIS, AMBER, FG, LABEL, LINE, MUTED, PANEL, SAFE_X, UP, W, Card, font

NY = ZoneInfo('America/New_York')
BAD, GOOD = '#ff5a4e', '#3ddc84'
RACE = dict(LABEL, AllInTrading='High risk: trading', AllInSports='High risk: sports')


def clip(c, s, f, max_w, max_lines):
    """Word-for-word, wrapped; if it runs past max_lines, cut at a word and end with '…'."""
    lines = c.wrap(s, f, max_w)
    if len(lines) <= max_lines:
        return lines
    keep = lines[:max_lines]
    last = keep[-1]
    while last and f.getlength(last + '…') > max_w:
        last = last.rsplit(' ', 1)[0] if ' ' in last else last[:-1]
    keep[-1] = last.rstrip(',;:') + '…'
    return keep


def badge(c, x, y, letter, color, size=84):
    c.d.rounded_rectangle([x, y, x + size, y + size], radius=16, fill=color)
    c.text((x + size // 2, y + size // 2), letter, font('sans', 'Bold', int(size * 0.72)), '#0b0b0a' if color == GOOD else '#ffffff', 'mm')


def card(bad, good, day, path, glow=True):
    c = Card()
    if glow:
        pc._glow(c, AMBER, xy=(1220, 360), r=440)
    c.header(f'GRADES OF THE DAY · DAY {day}')
    y = 268
    c.text((SAFE_X, y), 'THE AIs GRADE EACH OTHER · A TO F', font('mono', 'SemiBold', 30), UP, 'lm', tracking=4)
    y += 40
    c.text((SAFE_X, y), 'Grades of the day', font('sans', 'Bold', 112), FG, 'lt'); y += 150
    inner = W - 2 * SAFE_X - 60
    qf = font('sans', 'Medium', 52)
    small = font('sans', 'Regular', 40)
    # the harshest grade
    if bad:
        top = y
        lines = clip(c, '“' + bad['text'] + '”', qf, inner - 10, 3)
        said = clip(c, AIS[bad['about']][0] + '’s move: ' + bad['said'], small, inner - 10, 1)
        h = 150 + 64 * len(lines) + 56
        c.d.rounded_rectangle([SAFE_X, top, W - SAFE_X, top + h], radius=26, fill=PANEL, outline=LINE, width=3)
        badge(c, SAFE_X + 30, top + 30, bad['grade'], BAD)
        c.text((SAFE_X + 140, top + 52), 'HARSHEST', font('mono', 'SemiBold', 28), BAD, 'lm', tracking=4)
        who = AIS[bad['by']][0] + ' on ' + AIS[bad['about']][0] + (' · ' + RACE.get(bad.get('race'), bad.get('race')) if bad.get('race') else '')
        c.text((SAFE_X + 140, top + 94), who, font('sans', 'Bold', 44), FG, 'lm')
        yy = top + 140
        for ln in said:
            c.text((SAFE_X + 30, yy), ln, small, MUTED, 'lt'); yy += 56
        for ln in lines:
            c.text((SAFE_X + 30, yy), ln, qf, FG, 'lt'); yy += 64
        y = top + h + 34
    # the best grade: a decision both rivals graded A
    if good:
        top = y
        g1, g2 = good['grades'][0], good['grades'][1]
        q1 = clip(c, AIS[g1['by']][0] + ': “' + g1['text'] + '”', small, inner - 10, 2)
        q2 = clip(c, AIS[g2['by']][0] + ': “' + g2['text'] + '”', small, inner - 10, 2)
        h = 150 + 52 * (len(q1) + len(q2)) + 80
        c.d.rounded_rectangle([SAFE_X, top, W - SAFE_X, top + h], radius=26, fill=PANEL, outline=LINE, width=3)
        badge(c, SAFE_X + 30, top + 30, 'A', GOOD)
        c.text((SAFE_X + 140, top + 52), 'BEST · BOTH RIVALS GAVE ' + ' & '.join(g['grade'] for g in good['grades']), font('mono', 'SemiBold', 28), GOOD, 'lm', tracking=4)
        who = AIS[good['about']][0] + (' · ' + RACE.get(good.get('race'), good.get('race')) if good.get('race') else '') + ' · ' + good['said']
        who = clip(c, who, font('sans', 'Bold', 44), inner - 120, 1)[0]
        c.text((SAFE_X + 140, top + 94), who, font('sans', 'Bold', 44), FG, 'lm')
        yy = top + 150
        for ln in q1:
            c.text((SAFE_X + 30, yy), ln, small, FG, 'lt'); yy += 52
        yy += 26
        for ln in q2:
            c.text((SAFE_X + 30, yy), ln, small, FG, 'lt'); yy += 52
        y = top + h + 20
    if y > 1560:
        raise pc.QualityError('grades card runs into the footer')
    c.text((SAFE_X, min(y + 10, 1530)), 'Graded anonymously, before the result. Opinions only: they never change a score.', font('sans', 'Regular', 30), MUTED, 'lt')
    c.footer()
    return c.save(path)


if __name__ == '__main__':
    d = json.load(open('data.json'))
    bad = (d.get('callout') or [None])[0]
    good = (d.get('praise') or [None])[0]
    if bad and bad.get('kind') != 'grade':
        bad = None
    if not bad and not good:
        sys.exit('no grades to show')
    now = datetime.now(NY)
    day = pc.day_of(now)
    stem = now.strftime('%Y-%m-%d')
    os.makedirs('social', exist_ok=True)
    feed = card(bad, good, day, f'social/grades-{stem}.jpg')
    plain = card(bad, good, day, '/tmp/grades-plain.jpg', glow=False)
    pc.story(plain, f'social/story-grades-{stem}.jpg', top='GRADES OF THE DAY', bottom='Every grade, live: papertrades.ai', glow_color=AMBER)
    print(feed)
