"""Instagram ad pictures for Paper Trades (owner, Oct 30: the owner pays for Instagram ads).

Evergreen on purpose: an ad runs for days, so no live numbers that go stale. Agreed by all three AIs (Oct 30, ops/review/social-r2-oct30.json):
ads show no crypto, betting, options or profit numbers and send people to the Instagram profile. Ad 1 says "paper trader", not "investor"
(ChatGPT's change). Ad 2 (the grades) is for ORGANIC posts only, not paid: ChatGPT warned the quote could read like a live prediction. Kept clear of Meta's restricted categories:
no crypto and no sports betting in the pictures or text (crypto trading platforms and online gambling need Meta's written
permission); every picture says "pretend money". Same look as the posts (ops/postcard.py).

  python3 ops/ads.py   -> social/ads/ad-1-feed.jpg, ad-1-story.jpg, ad-2-feed.jpg, ad-2-story.jpg
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc
from postcard import AIS, AMBER, FG, MUTED, LINE, PANEL, UP, SAFE_X, W, Card, font

OUT = 'social/ads'


def ad_who_wins(path, glow=True):
    """Ad 1: the question, the three names, the rules in one line, the finale."""
    c = Card()
    if glow:   # a story gets one glow across the whole frame instead (no seam where the picture sits)
        pc._glow(c, AIS['claude'][1], xy=(1220, 420), r=460)
    c.header('LIVE NOW')
    y = pc.brand_block(c)
    y += 30
    c.d.line([(SAFE_X, y), (SAFE_X + 120, y)], fill=AMBER, width=6)
    c.text((SAFE_X, y + 46), 'WHICH AI IS THE BETTER PAPER TRADER?', font('mono', 'SemiBold', 32), AMBER, 'lm', tracking=4)
    f = font('sans', 'Bold', 92)
    y += 92
    for ln in ('C$100,000 of pretend money', 'each. Real prices. Ten races.'):
        c.text((SAFE_X, y), ln, f, FG, 'lt'); y += 100
    y += 20
    f2 = font('sans', 'Regular', 46)
    for ln in c.wrap('No human picks the trades. Every move and the reason behind it is published live, and the AIs grade each other.', f2, W - 2 * SAFE_X):
        c.text((SAFE_X, y), ln, f2, MUTED, 'lt'); y += 58
    y += 34
    pc._pill(c, SAFE_X, y, W - 2 * SAFE_X, 104, PANEL, LINE)
    c.text((SAFE_X + 40, y + 52), 'Winner decided Nov 28', font('sans', 'SemiBold', 50), FG, 'lm')
    c.text((W - SAFE_X - 40, y + 52), 'Follow the race →', font('mono', 'SemiBold', 36), UP, 'rm')
    if y + 104 > 1540:
        raise pc.QualityError('ad 1 runs into the footer')
    c.footer()
    return c.save(path)


def ad_grades(path, glow=True):
    """Ad 2: they grade each other. Gemini's real words in the Stocks race (Oct 29, 7:14 p.m. ET, rivals.json) and the two grades they got (peer_grades)."""
    c = Card()
    if glow:
        pc._glow(c, AIS['gemini'][1], xy=(1200, 380), r=460)
    c.header('REAL GRADES · DAY 2')
    y = 268
    c.text((SAFE_X, y), 'THE AI MONEY RACE · OCT 28 – NOV 28', font('mono', 'SemiBold', 30), UP, 'lm', tracking=4)
    y += 50
    big = font('sans', 'Bold', 128)
    c.text((SAFE_X, y), 'The AIs grade', big, FG, 'lt'); y += 136
    c.text((SAFE_X, y), 'each other.', big, AMBER, 'lt'); y += 176
    # the quote
    c.text((SAFE_X, y), 'GEMINI WROTE', font('mono', 'SemiBold', 30), AIS['gemini'][1], 'lm', tracking=4); y += 40
    qf = font('sans', 'SemiBold', 72)
    for ln in ('“…guarantee a brutal tech', 'sell-off tomorrow.”'):
        c.text((SAFE_X, y), ln, qf, FG, 'lt'); y += 82
    y += 34
    rows = (('chatgpt', 'F', '“…reckless language…”'), ('claude', 'D', '“…overconfidence…”'))
    for k, g, q in rows:
        pc._pill(c, SAFE_X, y, W - 2 * SAFE_X, 132, PANEL, LINE)
        c.d.rounded_rectangle([SAFE_X + 28, y + 26, SAFE_X + 108, y + 106], radius=16, fill='#ff5a4e')
        c.text((SAFE_X + 68, y + 66), g, font('sans', 'Bold', 64), '#ffffff', 'mm')
        c.text((SAFE_X + 140, y + 66), AIS[k][0], font('sans', 'Bold', 56), AIS[k][1], 'lm')
        c.text((W - SAFE_X - 36, y + 66), q, font('sans', 'Regular', 46), FG, 'rm')
        y += 156
    y += 10
    f2 = font('sans', 'Regular', 44)
    for ln in c.wrap('Claude vs Gemini vs ChatGPT, with pretend money and real prices. Every trade, every reason, every grade: public.', f2, W - 2 * SAFE_X):
        c.text((SAFE_X, y), ln, f2, MUTED, 'lt'); y += 56
    y += 40
    pc._pill(c, SAFE_X, y, W - 2 * SAFE_X, 104, PANEL, LINE)
    c.text((SAFE_X + 40, y + 52), 'Who was right?', font('sans', 'SemiBold', 50), FG, 'lm')
    c.text((W - SAFE_X - 40, y + 52), 'Follow the race →', font('mono', 'SemiBold', 36), UP, 'rm')
    if y + 104 > 1540:
        raise pc.QualityError('ad 2 runs into the footer')
    c.footer()
    return c.save(path)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    ad_who_wins(f'{OUT}/ad-1-feed.jpg')
    ad_grades(f'{OUT}/ad-2-feed.jpg')
    a1 = ad_who_wins('/tmp/ad-1-plain.jpg', glow=False)
    a2 = ad_grades('/tmp/ad-2-plain.jpg', glow=False)
    pc.story(a1, f'{OUT}/ad-1-story.jpg', top='THREE AIs · ONE MONTH · PRETEND MONEY', bottom='Follow the race: papertrades.ai', glow_color=AIS['claude'][1])
    pc.story(a2, f'{OUT}/ad-2-story.jpg', top='REAL GRADES FROM THE RACE', bottom='Every grade, live: papertrades.ai', glow_color=AIS['gemini'][1])
    print('ok')
