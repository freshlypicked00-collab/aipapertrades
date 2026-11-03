"""YouTube channel art (owner, Nov 3: the channel "looks like another AI slop project"; Gemini and Claude agreed on A7: the three AI
robots as the picture instead of a generic chart line, and a banner that says what the channel is and how often it posts).

  python3 ops/yt_channel_art.py social/yt/channel   -> avatar.png (800x800) and banner.png (2560x1440, text inside the 1546x423 safe area)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_short import AIC, AMBER, BG, F, FG, MUTED, UP, bot  # noqa: E402


def glow(size, spots):
    g = Image.new('RGB', size, BG); d = ImageDraw.Draw(g)
    for (x, y, r, col, a) in spots:
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(BG[i] + (col[i] - BG[i]) * a) for i in range(3)))
    return g.filter(ImageFilter.GaussianBlur(min(size) // 9))


def avatar(path):
    S = 800
    im = glow((S, S), [(170, 430, 230, AIC['claude'], .30), (400, 430, 230, AIC['gemini'], .30), (630, 430, 230, AIC['chatgpt'], .16)])
    d = ImageDraw.Draw(im)
    for x, k in ((172, 'claude'), (400, 'gemini'), (628, 'chatgpt')):   # all three the same size: the channel takes no side
        bot(d, x, 470, AIC[k], 1.12)
    im.save(path)
    return path


def banner(path):
    Wd, Hd = 2560, 1440
    im = glow((Wd, Hd), [(1280, 720, 700, AIC['gemini'], .22), (700, 760, 520, AIC['claude'], .20), (1860, 760, 520, AIC['chatgpt'], .10)])
    d = ImageDraw.Draw(im)
    # faint price lines across the whole banner (seen on TVs and desktop only)
    import math
    for k, (col, ph) in enumerate(((AIC['claude'], 0.0), (AIC['gemini'], 1.7), (AIC['chatgpt'], 3.1))):
        pts = [(x, 720 + 140 * math.sin(x / 260 + ph) + 60 * math.sin(x / 97 + ph * 2) + (k - 1) * 90) for x in range(0, Wd + 20, 20)]
        d.line(pts, fill=tuple(int(BG[i] + (col[i] - BG[i]) * .35) for i in range(3)), width=6, joint='curve')
    # the safe area: 1546 x 423, centred; the lines fade behind the words so they stay easy to read
    x0, y0 = (Wd - 1546) // 2, (Hd - 423) // 2
    shade = Image.new('L', (Wd, Hd), 0); ImageDraw.Draw(shade).rounded_rectangle([x0 - 60, y0 - 40, x0 + 1606, y0 + 463], radius=60, fill=200)
    shade = shade.filter(ImageFilter.GaussianBlur(50))
    im = Image.composite(Image.new('RGB', (Wd, Hd), BG), im, shade); d = ImageDraw.Draw(im)
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        bot(d, x0 + 95 + i * 150, y0 + 250 - (30 if k == 'gemini' else 0), AIC[k], 0.62 if k != 'gemini' else 0.72)
    tx = x0 + 470
    d.text((tx, y0 + 40), 'PAPERTRADES.AI', font=F('mono', 'Bold', 96), fill=FG)
    d.text((tx, y0 + 160), '3 AIs. C$100,000 of pretend money each. Real prices.', font=F('sans', 'Bold', 54), fill=FG)
    d.text((tx, y0 + 232), 'Claude', font=F('sans', 'Bold', 54), fill=AIC['claude'])
    xx = tx + d.textlength('Claude', font=F('sans', 'Bold', 54))
    d.text((xx, y0 + 232), ' vs ', font=F('sans', 'Bold', 54), fill=MUTED); xx += d.textlength(' vs ', font=F('sans', 'Bold', 54))
    d.text((xx, y0 + 232), 'Gemini', font=F('sans', 'Bold', 54), fill=AIC['gemini']); xx += d.textlength('Gemini', font=F('sans', 'Bold', 54))
    d.text((xx, y0 + 232), ' vs ', font=F('sans', 'Bold', 54), fill=MUTED); xx += d.textlength(' vs ', font=F('sans', 'Bold', 54))
    d.text((xx, y0 + 232), 'ChatGPT', font=F('sans', 'Bold', 54), fill=AIC['chatgpt'])
    d.text((tx, y0 + 318), 'Season 1 · Oct 28 – Nov 28, 2026 · New AI trade stories every day', font=F('mono', 'Bold', 36), fill=AMBER)
    im.save(path)
    return path


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'social/yt/channel'
    os.makedirs(out, exist_ok=True)
    print(avatar(os.path.join(out, 'avatar.png')), banner(os.path.join(out, 'banner.png')))
