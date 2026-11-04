"""PaperTrades.AI logo: the three AI robots and the green rising chart in one mark (owner, Nov 3: "combine both of the logos we
had so it's like a green stock going up in the background ... work with Gemini to create something magnificent").

  python3 ops/logo.py ops/logo      -> concept SVGs (drafts stay in ops/, never published) (rendered to PNG by ops/logo_render.js)
All three robots are the same size and on the same level: the logo never ranks the AIs.
"""
import os
import sys

INK, CREAM, BALL = '#14120e', '#f2e9d8', '#ffcb66'
AIC = {'claude': '#d97757', 'gemini': '#4f8ff7', 'chatgpt': '#f2f2f2'}
GREEN, GREEN2, DEEP = '#3ddc84', '#4cc283', '#17201c'


def robot(x, y, col, s=1.0):
    """The site's robot (same geometry as ops/yt_short.bot), centred at x, y (y = middle of the face)."""
    sw = lambda v: f'{v * s:.2f}'
    return (f'<g>'
            f'<line x1="{x}" y1="{y - 118 * s}" x2="{x}" y2="{y - 162 * s}" stroke="{CREAM}" stroke-width="{sw(10)}" stroke-linecap="round"/>'
            f'<circle cx="{x}" cy="{y - 178 * s}" r="{sw(22)}" fill="{BALL}" stroke="{INK}" stroke-width="{sw(7)}"/>'
            f'<rect x="{x - 95 * s}" y="{y - 120 * s}" width="{190 * s}" height="{200 * s}" rx="{46 * s}" fill="{col}" stroke="{INK}" stroke-width="{sw(11)}"/>'
            + ''.join(f'<circle cx="{x + ex * s}" cy="{y - 40 * s}" r="{sw(20)}" fill="{INK}"/><circle cx="{x + (ex - 1) * s}" cy="{y - 47 * s}" r="{sw(5.5)}" fill="{CREAM}"/>' for ex in (-38, 38))
            + f'<polyline points="{x - 35 * s},{y + 25 * s} {x},{y + 45 * s} {x + 35 * s},{y + 25 * s}" fill="none" stroke="{INK}" stroke-width="{sw(10)}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</g>')


def robots(y, s, gap):
    return ''.join(robot(512 + (i - 1) * gap, y, AIC[k], s) for i, k in enumerate(('claude', 'gemini', 'chatgpt')))


def arrow(pts, width, col, head=1.0):
    """A thick rounded polyline ending in an arrowhead pointing along its last segment."""
    import math
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    a = math.atan2(y2 - y1, x2 - x1)
    L, Wd = 2.0 * width * head, 1.55 * width * head
    tip = (x2 + math.cos(a) * L * 0.55, y2 + math.sin(a) * L * 0.55)
    b1 = (x2 - math.cos(a) * L * 0.45 + math.cos(a + math.pi / 2) * Wd, y2 - math.sin(a) * L * 0.45 + math.sin(a + math.pi / 2) * Wd)
    b2 = (x2 - math.cos(a) * L * 0.45 - math.cos(a + math.pi / 2) * Wd, y2 - math.sin(a) * L * 0.45 - math.sin(a + math.pi / 2) * Wd)
    p = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    return (f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {b1[0]:.1f},{b1[1]:.1f} {b2[0]:.1f},{b2[1]:.1f}" fill="{col}" stroke="{col}" stroke-width="{width * 0.25:.1f}" stroke-linejoin="round"/>')


def svg(body, defs=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
            f'<defs>{defs}'
            f'<radialGradient id="bg" cx="50%" cy="42%" r="70%"><stop offset="0" stop-color="#16231c"/><stop offset=".62" stop-color="#0e120f"/><stop offset="1" stop-color="#0b0b0a"/></radialGradient>'
            f'<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>'
            f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity=".34"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>'
            f'</defs><rect width="1024" height="1024" fill="url(#bg)"/>{body}</svg>')


def grid():
    g = ''.join(f'<line x1="0" y1="{y}" x2="1024" y2="{y}" stroke="{GREEN}" stroke-opacity=".07" stroke-width="3"/>' for y in range(160, 900, 110))
    g += ''.join(f'<line x1="{x}" y1="0" x2="{x}" y2="1024" stroke="{GREEN}" stroke-opacity=".04" stroke-width="3"/>' for x in range(122, 1000, 130))
    return g


LINE = [(118, 640), (360, 392), (470, 480), (842, 168)]   # the site icon's zigzag (up, a small dip, up), scaled up


def concept_a():
    """A: the green chart rises behind the robots, glowing, with a soft area fill; the robots watch it go up."""
    pts = LINE
    area = ' '.join(f'{x},{y}' for x, y in pts) + f' {pts[-1][0]},1024 {pts[0][0]},1024'
    body = grid()
    body += f'<polygon points="{area}" fill="url(#area)"/>'
    body += f'<g filter="url(#glow)" opacity=".85">{arrow(pts, 64, GREEN)}</g>' + arrow(pts, 58, GREEN)
    body += robots(720, 1.18, 252)
    return svg(body)


def concept_b():
    """B: rising green candlesticks behind the robots, the zigzag on top."""
    body = grid()
    import random
    rnd = random.Random(7)
    x, base = 96, 860
    for i in range(9):
        h = 120 + i * 62 + rnd.randint(-30, 30)
        top = base - h
        body += f'<line x1="{x + 30}" y1="{top - 34}" x2="{x + 30}" y2="{base + 10}" stroke="{GREEN}" stroke-opacity=".35" stroke-width="8" stroke-linecap="round"/>'
        body += f'<rect x="{x}" y="{top}" width="60" height="{h - 40}" rx="10" fill="{GREEN}" fill-opacity="{.18 + i * .03:.2f}"/>'
        x += 96
    body += f'<g filter="url(#glow)" opacity=".8">{arrow(LINE, 60, GREEN)}</g>' + arrow(LINE, 54, GREEN)
    body += robots(720, 1.18, 252)
    return svg(body)


def concept_c():
    """C: the old app icon (green zigzag on a dark green tile) as a big screen, the three robots in front of it watching."""
    body = f'<rect x="172" y="96" width="680" height="560" rx="96" fill="{DEEP}" stroke="{GREEN}" stroke-opacity=".35" stroke-width="8"/>'
    pts = [(268, 520), (448, 350), (538, 430), (748, 210)]
    body += f'<g filter="url(#glow)" opacity=".7">{arrow(pts, 50, GREEN2)}</g>' + arrow(pts, 46, GREEN2)
    body += robots(760, 1.12, 240)
    return svg(body)


# ---------- round 2: concept A refined with Gemini's round-1 review (ops/review/logo-r1-nov3.json): no grid, no area fill,
# a bolder line that weaves behind the robots and soars above ChatGPT, a swept arrowhead, the whole mark centred in the circle
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'IBMPlexMono-Bold.ttf')   # the site's font (IBM Plex Mono)
MARK_LINE = [(118, 650), (390, 382), (522, 478), (826, 196)]


def swept(pts, w, col, extra=''):
    """The line and a swept arrowhead that grows out of it (the line stops at the arrow's notch, so no round cap shows)."""
    import math
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    a = math.atan2(y2 - y1, x2 - x1); ux, uy = math.cos(a), math.sin(a); px, py = -uy, ux
    tip = (x2 + ux * 1.55 * w, y2 + uy * 1.55 * w)
    w1 = (x2 - ux * 0.62 * w + px * 1.32 * w, y2 - uy * 0.62 * w + py * 1.32 * w)
    w2 = (x2 - ux * 0.62 * w - px * 1.32 * w, y2 - uy * 0.62 * w - py * 1.32 * w)
    p = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    head = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (tip, w1, (x2, y2), w2))
    return (f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
            f'<polygon points="{head}" fill="{col}" stroke="{col}" stroke-width="{w * 0.22:.1f}" stroke-linejoin="round" {extra}/>')


def mark_body(line_w=62, rs=1.12, gap=236, ry=700):
    body = f'<g filter="url(#glow2)" opacity=".9">{swept(MARK_LINE, line_w + 10, GREEN)}</g>'
    body += swept(MARK_LINE, line_w, GREEN)
    body += f'<g opacity=".55">{swept(MARK_LINE, line_w * 0.28, "#b8f5d0")}</g>'   # a thin bright core: the line looks lit, not flat
    body += robots(ry, rs, gap)
    return body


DEFS2 = ('<radialGradient id="bg2" cx="52%" cy="40%" r="62%"><stop offset="0" stop-color="#13201a"/><stop offset=".7" stop-color="#0c0f0d"/><stop offset="1" stop-color="#0b0b0a"/></radialGradient>'
         '<filter id="glow2" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="26"/></filter>')


def text_path(text, x, y, size, tracking=0.16, anchor='middle', col=None, parts=None):
    """Text as SVG paths in IBM Plex Mono Bold (no font needed to view the file). parts: [(text, colour)] to colour pieces."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    f = TTFont(FONT); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f['head'].unitsPerEm
    sc = size / upm; parts = parts or [(text, col or CREAM)]
    full = ''.join(t for t, _ in parts)
    adv = [gs[cmap[ord(ch)]].width * sc for ch in full]
    width = sum(adv) + tracking * size * (len(full) - 1)
    cx = x - width / 2 if anchor == 'middle' else x
    out, i = '', 0
    for t, c in parts:
        for ch in t:
            g = gs[cmap[ord(ch)]]; pen = SVGPathPen(gs); g.draw(pen)
            out += f'<path d="{pen.getCommands()}" fill="{c}" transform="translate({cx:.2f},{y:.2f}) scale({sc:.5f},{-sc:.5f})"/>'
            cx += adv[i] + tracking * size; i += 1
    return out, width


WORD = [('PAPERTRADES', CREAM), ('.AI', GREEN)]


def svg2(body, w=1024, h=1024, bg=True):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><defs>{DEFS2}</defs>'
            + (f'<rect width="{w}" height="{h}" fill="url(#bg2)"/>' if bg else '') + body + '</svg>')


def mark_v2():
    """The mark: robots + rising chart, for small circles (40-48 px), the favicon and the app icon."""
    return svg2(mark_body())


def stacked_v2():
    """The full logo, square: the mark with PAPERTRADES.AI under it, everything inside the profile circle."""
    t, _ = text_path('', 512, 0, 10, parts=WORD)
    words, wd = text_path('', 512, 868, 64, parts=WORD)
    body = f'<g transform="translate(512,430) scale(.74) translate(-512,-488)">{mark_body()}</g>' + words
    return svg2(body)


def wide_v2():
    """The full logo, wide: the mark on the left, PAPERTRADES.AI on the right (site header, banners, video end cards)."""
    words, wd = text_path('', 0, 0, 120, anchor='start', parts=WORD)
    W = int(1024 * 0.9 + 60 + wd + 80)
    body = f'<g transform="translate(20,40) scale(.9)">{mark_body()}</g><g transform="translate({int(1024 * .9 + 60)},560)">{words}</g>'
    return svg2(body, W, 1000)


def round_v2(scale=.6, my=410, ty=790, ts=50):
    """Profile-picture version (owner, Nov 3: the stacked logo "doesnt fit good on youtube"): the mark and the name kept well
    inside the circle YouTube, Instagram, X and Telegram cut out, with room to spare for each site's own crop."""
    words, wd = text_path('', 512, ty, ts, parts=WORD)
    body = f'<g transform="translate(512,{my}) scale({scale}) translate(-512,-470)">{mark_body()}</g>' + words
    return svg2(body)


if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[2] == 'v2':
    out = sys.argv[1]
    for n, f in (('mark', mark_v2), ('stacked', stacked_v2), ('wide', wide_v2), ('round', round_v2)):
        open(os.path.join(out, f'v2-{n}.svg'), 'w').write(f()); print(os.path.join(out, f'v2-{n}.svg'))
    sys.exit(0)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'ops/logo'
    os.makedirs(out, exist_ok=True)
    for n, f in (('a', concept_a), ('b', concept_b), ('c', concept_c)):
        open(os.path.join(out, f'concept-{n}.svg'), 'w').write(f())
        print(os.path.join(out, f'concept-{n}.svg'))
