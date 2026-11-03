"""Short covers (owner, Nov 2: "do we need better thumbnails" -> yes; agreed with the owner, Claude's design):
one bold first frame per Short, readable at the size of a YouTube grid tile: the AI's robot, its name, ONE big number,
and a few huge words. Everything is read from the Short's own story (the public ledger); nothing typed by hand.

  python3 ops/cover.py social/stories/story-G-AIS-030.json   -> social/stories/story-G-AIS-030-cover.png
Used by ops/story_short.py: the cover is the first 0.7 s of every new Short, and its -thumb.png.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc  # noqa: E402
from hl_stories import robot  # noqa: E402

W, H = 1080, 1920
BG = (11, 11, 10)
FG = (242, 233, 216)
MUTED = (155, 146, 127)
UP, DOWN, AMBER = (61, 220, 132), (255, 90, 78), (255, 176, 0)
AIC = {'claude': (217, 119, 87), 'gemini': (79, 143, 247), 'chatgpt': (242, 242, 242)}
NAME = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
F = pc.font


def short_money(v):
    v = abs(v)
    if v >= 10000:
        return f'C${v / 1000:,.0f}K' if v % 1000 < 50 or v >= 100000 else f'C${v / 1000:,.1f}K'
    return f'C${v:,.0f}'


def fit(d, text, kind, weight, size, width):
    while size > 40 and d.textlength(text, font=F(kind, weight, size)) > width:
        size -= 4
    return F(kind, weight, size)


def cover(s, path):
    """s = a story from ops/story_short.bet_story (model, odds, stake, pnl, won, league, race, parts)."""
    col = AIC[s['model']]
    win = bool(s['won'])
    res = UP if win else DOWN
    g = Image.new('RGB', (W, H), BG); gd = ImageDraw.Draw(g)
    gd.ellipse([-250, 150, W + 250, 1250], fill=tuple(int(v * .38) for v in col))       # the AI's colour glow behind the robot
    gd.ellipse([-300, 1250, W + 300, 2300], fill=tuple(int(v * .22) for v in res))      # the result's colour at the bottom
    im = g.filter(ImageFilter.GaussianBlur(110)); d = ImageDraw.Draw(im)
    d.text((W // 2, 262), 'PAPERTRADES.AI', font=F('mono', 'SemiBold', 44), fill=MUTED, anchor='mm')
    robot(d, W // 2, 730, col, 1.9, 3)
    d.text((W // 2, 1030), NAME[s['model']].upper(), font=fit(d, NAME[s['model']].upper(), 'sans', 'Bold', 150, 900), fill=col, anchor='mm')
    word = 'WON' if win else 'LOST'
    num = ('+' if win else '−') + short_money(s['pnl'])
    d.text((W // 2, 1190), word, font=F('sans', 'Bold', 110), fill=FG, anchor='mm')
    d.text((W // 2, 1340), num, font=fit(d, num, 'sans', 'Bold', 230, 960), fill=res, anchor='mm')
    kind = 'UNDERDOG' if s['odds'] > 0 else 'FAVOURITE'
    o = f'+{s["odds"]}' if s['odds'] > 0 else f'−{abs(s["odds"])}'
    tag = f'{o} {kind}'
    d.text((W // 2, 1495), tag, font=fit(d, tag, 'sans', 'Bold', 92, 940), fill=AMBER, anchor='mm')
    d.text((W // 2, 1600), 'PRETEND MONEY · REAL ODDS', font=F('mono', 'SemiBold', 36), fill=MUTED, anchor='mm')
    im.save(path)
    return path


if __name__ == '__main__':
    for p in sys.argv[1:]:
        st = json.load(open(p))['story']
        print(cover(st, p[:-5] + '-cover.png'))
