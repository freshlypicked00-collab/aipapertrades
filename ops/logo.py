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


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'ops/logo'
    os.makedirs(out, exist_ok=True)
    for n, f in (('a', concept_a), ('b', concept_b), ('c', concept_c)):
        open(os.path.join(out, f'concept-{n}.svg'), 'w').write(f())
        print(os.path.join(out, f'concept-{n}.svg'))
