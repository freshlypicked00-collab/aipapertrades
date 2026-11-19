"""The share picture of the final result (full pass, Nov 20). HELD for the owner's OK: nothing calls this yet and it posts nothing.

It is the daily standings picture (ops/racecard.py, the same numbers as the site) with the final title and one more line under the
ten races: the three overall totals, which are named in a picture for the first time at the finish.

  python3 ops/final_card.py out.png            the final picture, from the site's data as it is now
  python3 ops/final_card.py out.png --preview  the same, marked PREVIEW (for looking at before Nov 28)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
NAMES = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
COL = {'claude': (217, 119, 87), 'gemini': (66, 133, 244), 'chatgpt': (242, 233, 216)}
UP, DOWN, MUTED = (61, 220, 132), (255, 95, 86), (155, 146, 127)


def money(v):
    return ('+' if v >= 0 else '−') + 'C$' + f'{abs(v):,.0f}'


def make(out, preview=False):
    import racecard, sharecard
    from PIL import Image, ImageDraw
    os.chdir(ROOT)
    table, _ = racecard.races(None, 'ops/src')
    title = ('PREVIEW · ' if preview else '') + 'Final result · Season 1 · Oct 28 to Nov 28, 2026'
    racecard.races_card(table, None, title, out)
    rows = sorted(json.load(open('data.json'))['standings'], key=lambda r: -r['profit'])
    im = Image.open(out).convert('RGB')
    g = ImageDraw.Draw(im)
    W, H = im.size
    f, fb = sharecard._font('med', 22), sharecard._font('bold', 24)
    x, y = 60, H - 62
    g.rectangle([0, y - 8, W, H], fill=im.getpixel((5, H - 5)))   # the old small-print line makes room
    g.text((x, y), 'OVERALL, the ten races added up:', font=f, fill=MUTED)
    x += g.textlength('OVERALL, the ten races added up:', font=f) + 18
    for i, r in enumerate(rows):
        lab = ['1st', '2nd', '3rd'][i] + ' ' + NAMES.get(r['id'], r['id'])
        g.text((x, y - 1), lab, font=fb, fill=COL.get(r['id'], (242, 233, 216)))
        x += g.textlength(lab, font=fb) + 8
        g.text((x, y - 1), money(r['profit']), font=fb, fill=UP if r['profit'] >= 0 else DOWN)
        x += g.textlength(money(r['profit']), font=fb) + 26
    g.text((60, H - 28), 'papertrades.ai/#final · pretend money, real prices · not advice', font=sharecard._font('med', 17), fill=MUTED)
    im.save(out)
    return out


if __name__ == '__main__':
    print(make(sys.argv[1] if len(sys.argv) > 1 else '/tmp/final_result.png', '--preview' in sys.argv))
