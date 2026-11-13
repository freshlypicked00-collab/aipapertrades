"""YouTube commercial v2: the website and the Discord, how the channels are set up and how to pick your alerts
(owner, Nov 13: "make a new commercial for youtube work with the other models advertise the website, and the discord channel,
show how the channels setup and how you can setup the notifications etc.").

Concept: ops/review/yt-ad2-claude-concept.md (Claude, first); Gemini and ChatGPT agreed V1-V4 and both amended the ending to the owner's
exact words (ops/review/yt-ad2-nov13.json). Both asked for REAL footage, not mock-ups: the website is filmed from the live build at
phone size (ops/yt_ad2_film.js), the Discord screens are screenshots of our own server (the owner signed in, nothing changed).
Every number is read from data.json; the render stops if a fact no longer matches.
Reuses the camera, film, robots and sound of the first commercial (ops/discord_ad.py, ops/ad_audio.py).

  python3 ops/yt_ad2.py yt-ad2-v1 [--stills] [--fake]
"""
import argparse
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import discord_ad as DA  # noqa: E402
import ad_audio as AA  # noqa: E402
from discord_ad import (W, H, FPS, SR, BG, FG, MUTED, UP, DOWN, AMBER, BLURPLE, AIC, NAME, F, ease, ease_io, back, spring,  # noqa: E402
                        text_c, bot, paste_scaled, shadowed, wrap, read_wav, trim, envelope, token_times, tempo_wav, Fail)

ROOT = os.path.dirname(HERE)
FOOT = os.path.join(ROOT, 'social', 'ads', 'yt-ad2')        # the footage: website stills (filmed) and Discord screenshots
CAP_Y = 1455
GAP_AFTER = {'01': 0.16, '02': 0.20, '03': 0.20, '04': 0.30, '05': 0.16, '06': 0.22, '07': 0.18, '08': 0.30, '09': 0.24}
TEMPO = {'01': 1.06, '02': 1.04, '03': 1.04, '04': 1.04, '05': 1.05, '06': 1.06, '07': 1.02, '08': 1.04, '09': 1.06, '10': 1.02}
END_HOLD = 2.6
BPM = 120


# ================================================================ facts (read from the public data; stop if one changed)
def facts(d):
    t = {x['tx']: x for x in d['rivals_trades'] if x.get('tx')}
    buy = t.get('G-CRY-028')
    if not buy or buy['action'] != 'Buy' or round(buy['amount']) != 35000 or buy['symbol'] != 'BTC-USD':
        raise Fail('G-CRY-028 is not Gemini buying C$35,000 of Bitcoin')
    uso = t.get('G-ENE-031')
    if not uso or uso['symbol'] != 'USO' or round(uso['amount']) != 15000:
        raise Fail('G-ENE-031 is not Gemini buying C$15,000 of USO')
    g = {x['grader']: x for x in d['peer_grades'] if x['key'] == 'gemini|2026-11-12T18:44:37Z|Energy|USO|Buy'}
    if g.get('claude', {}).get('grade') != 'B' or g.get('chatgpt', {}).get('grade') != 'B':
        raise Fail('the USO grades changed')
    st = sorted(d['standings'], key=lambda r: -r.get('profit', 0)) if isinstance(d.get('standings'), list) else None
    return {'buy': buy, 'uso': uso, 'grades': g, 'standings': st}


# ================================================================ voice timeline
def timeline(script, vdir, words, fake=False):
    lines, t = [], 0.12
    for ln in script['lines']:
        if fake:
            dur = len(ln['text'].split()) / 2.9 + 0.2; x = np.zeros(int(dur * SR), np.float32); tok = list(np.linspace(0, dur * 0.95, len(ln['text'].split())))
        else:
            f_ = TEMPO.get(ln['id'], 1.0)
            os.makedirs(f'/tmp/yt_ad2/{script["name"]}/vo', exist_ok=True)
            src = tempo_wav(f'{vdir}/{ln["id"]}.wav', f_, f'/tmp/yt_ad2/{script["name"]}/vo/{ln["id"]}-{f_}.wav')
            x, cut = trim(read_wav(src))
            dur = len(x) / SR
            wl = [[w_, a_ / f_, b_ / f_] for w_, a_, b_ in (words.get(ln['id']) or [])]
            tok = token_times(ln['text'], wl, dur, cut)
        lines.append({**ln, 'x': x, 'start': t, 'dur': dur, 'tok': tok, 'env': envelope(x) if len(x) else np.zeros(1)})
        t += dur + GAP_AFTER.get(ln['id'], 0.25)
    total = lines[-1]['start'] + lines[-1]['dur'] + END_HOLD
    scenes = []
    for i, ln in enumerate(lines):
        s0 = 0.0 if i == 0 else ln['start'] - 0.12
        s1 = total if i == len(lines) - 1 else lines[i + 1]['start'] - 0.12
        scenes.append({'id': ln['id'], 's0': s0, 's1': s1})
    by = {ln['id']: ln for ln in lines}
    marks = {'verse': by['02']['start'] - 0.05, 'build': by['05']['start'] - 0.1, 'drop': by['05']['start'] + 0.3, 'outro': by['10']['start']}
    return lines, scenes, total, marks


# ================================================================ captions: a few words at a time, key words in colour
CAPS = {
    '01': [('3 AIs', 2, FG), ('trading', 1, FG), ('pretend money', 2, AMBER), ('at real prices', 3, FG), ('every move', 3, UP), ('is public.', 2, UP)],
    '02': [('This is', 2, FG), ('PaperTrades.AI', 3, UP), ('10 races', 2, FG), ('1 month', 2, FG), ('1 winner', 2, AMBER)],
    '03': [('Tap any trade', 3, FG), ('to see', 2, FG), ('my exact reason', 3, AIC['gemini']), ('+ a transaction ID', 4, AMBER), ('you can check', 3, UP)],
    '04': [("And we grade", 3, FG), ("each other's moves", 3, FG), ('before', 1, AMBER), ('the results', 2, FG), ('are in.', 2, FG)],
    '05': [('Want it', 2, FG), ('on your phone?', 3, FG), ('Join our', 2, FG), ('free Discord.', 2, BLURPLE)],
    '06': [('Headlines', 1, FG), ('up top.', 2, FG), ('Every live move.', 3, UP), ('One channel', 4, FG), ('for each race.', 3, AMBER)],
    '07': [('Nothing pings you', 3, FG), ('until you', 2, FG), ('pick it.', 2, UP)],
    '08': [('Pick', 1, FG), ('Gemini', 1, AIC['gemini']), ('then Crypto', 2, AMBER), ("and you'll know", 3, FG), ('every move.', 3, UP)],
    '09': [('Change it', 2, FG), ('any time:', 2, FG), ('server name', 4, AMBER), ('→ Channels & Roles', 4, BLURPLE)],
    '10': [('Link in', 2, FG), ('the description', 2, FG), ('Like', 3, UP), ('& subscribe', 2, FG), ('for trade updates', 4, AMBER)],
}


# ================================================================ assets
class Assets:
    def __init__(self, f):
        A0 = DA.Assets.__new__(DA.Assets)
        # background pieces from the first commercial (vignette, glow, grain, motes, sprite)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.42) / (H * 0.62)) ** 2)
        self.vig = np.clip(1.08 - 0.55 * r ** 1.6, 0.35, 1.0)[..., None].astype(np.float32)
        self.base = (np.array(BG, np.float32)[None, None, :] * np.ones((H, W, 1), np.float32))
        g = np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy - 820) / 720) ** 2))
        self.glow = g[..., None].astype(np.float32)
        rng = np.random.default_rng(5)
        self.grain = [rng.normal(0, 5.0, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
        self.motes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(10, 34), rng.uniform(6, 22), rng.uniform(0, 6.28), rng.uniform(0.05, 0.12)) for _ in range(20)]
        yy2, xx2 = np.mgrid[-32:32, -32:32].astype(np.float32)
        blob = np.clip(1 - np.sqrt(xx2 ** 2 + yy2 ** 2) / 32, 0, 1) ** 1.6
        spr = np.zeros((64, 64, 4), np.uint8); spr[..., :3] = 255; spr[..., 3] = (blob * 255).astype(np.uint8)
        self.sprite = Image.fromarray(spr, 'RGBA')
        self.logo = Image.open(os.path.join(ROOT, 'brand', 'logo-circle-512.png')).convert('RGBA')
        self.glyph = Image.open(os.path.join(HERE, 'assets', 'discord-glyph-white.png')).convert('RGBA')
        ld = lambda n: Image.open(os.path.join(FOOT, n)).convert('RGB')
        # the website, filmed at phone size (1080 px wide)
        self.home_long = ld('site-home-long.jpg'); self.story = ld('site-story.jpg'); self.standings = ld('site-standings.jpg')
        # Discord: our own server (screenshots); optional ones fall back to None
        self.dc = {}
        for k in ('channels', 'live', 'roles', 'roles-ai', 'menu'):
            p = os.path.join(FOOT, f'discord-{k}.png')
            self.dc[k] = Image.open(p).convert('RGB') if os.path.exists(p) else None
        self.f = f


class Ctx:
    def __init__(self, A, lines, scenes, total):
        self.A, self.lines, self.scenes, self.total = A, lines, scenes, total
        self.by = {ln['id']: ln for ln in lines}

    def at_tok(self, lid, k):
        ln = self.by[lid]; return ln['start'] + ln['tok'][max(0, min(k, len(ln['tok']) - 1))]

    def talking(self, lid, tt):
        ln = self.by[lid]; i = int((tt - ln['start']) * FPS)
        return float(ln['env'][i]) if 0 <= i < len(ln['env']) else 0.0


def background(A, tt, col, amt=0.34, col2=None, amt2=0.0):
    img = A.base.copy()
    img += A.glow * (np.array(col, np.float32) - np.array(BG, np.float32)) * amt
    if col2 is not None and amt2 > 0:
        sh = np.roll(A.glow, int(260 * math.sin(tt * 0.7)), axis=1)
        img += sh * (np.array(col2, np.float32) - np.array(BG, np.float32)) * amt2
    return img


# ================================================================ building blocks
def rounded_mask(w, h, r):
    m = Image.new('L', (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=r * 2, fill=255)
    return m.resize((w, h), Image.LANCZOS)


PH_W, PH_H = 600, 1300                 # the phone's screen on the canvas: a tall, slim modern phone (19.5:9), not a foldable
PH_X, PH_Y = (W - PH_W) // 2, 316
_FRAME = {}


def phone_frame():
    """A slim, generic modern phone (owner, Nov 13: a proper phone shape, not the wide one): thin even bezels, a pill camera, a
    brushed-metal edge and side buttons. Drawn at 2x and scaled down so every curve is smooth. No maker's logo or exact design."""
    if 'f' in _FRAME:
        return _FRAME['f']
    S2 = 2
    bez, edge = 12, 7                                  # black bezel, metal edge (canvas px)
    w, h = PH_W + 2 * (bez + edge), PH_H + 2 * (bez + edge)
    R = 92                                             # outer corner radius
    big = Image.new('RGBA', ((w + 40) * S2, (h + 20) * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    ox = 20 * S2   # room for the side buttons
    # side buttons (left: action + volume up/down; right: power), metal, behind the edge
    for (x0, y0, x1, y1) in ((-6, 210, 4, 270), (-6, 320, 4, 420), (-6, 440, 4, 540), (w - 4, 330, w + 6, 470)):
        d.rounded_rectangle([ox + x0 * S2, (y0 + 10) * S2, ox + x1 * S2, (y1 + 10) * S2], radius=4 * S2, fill=(120, 118, 112, 255))
    # the metal edge: a vertical gradient from light to dark, then the black body inside it
    edge_img = Image.new('RGBA', (w * S2, h * S2), (0, 0, 0, 0))
    grad = Image.linear_gradient('L').resize((w * S2, h * S2))
    light = Image.new('RGBA', (w * S2, h * S2), (196, 193, 186, 255)); dark = Image.new('RGBA', (w * S2, h * S2), (88, 86, 82, 255))
    metal = Image.composite(dark, light, grad)
    m = Image.new('L', (w * S2, h * S2), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * S2 - 1, h * S2 - 1], radius=R * S2, fill=255)
    edge_img.paste(metal, (0, 0), m)
    ImageDraw.Draw(edge_img).rounded_rectangle([edge * S2, edge * S2, (w - edge) * S2 - 1, (h - edge) * S2 - 1], radius=(R - edge) * S2, fill=(6, 6, 7, 255))
    # a fine highlight line on the metal (catches the light)
    ImageDraw.Draw(edge_img).rounded_rectangle([2 * S2, 2 * S2, (w - 2) * S2 - 1, (h - 2) * S2 - 1], radius=(R - 2) * S2, outline=(235, 232, 225, 150), width=S2)
    big.alpha_composite(edge_img, (ox, 10 * S2))
    frame = big.resize((w + 40, h + 20), Image.LANCZOS)
    smask = rounded_mask(PH_W, PH_H, R - edge - bez + 6)
    pill = Image.new('RGBA', (PH_W, PH_H), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([PH_W // 2 - 62, 18, PH_W // 2 + 62, 52], radius=17, fill=(0, 0, 0, 255))
    glass = Image.new('RGBA', (PH_W, PH_H), (0, 0, 0, 0))   # a faint diagonal reflection on the glass
    gd = ImageDraw.Draw(glass)
    for k in range(60):
        gd.line([(-200 + k * 4, 0), (PH_W * 0.9 + k * 4, PH_H)], fill=(255, 255, 255, 3), width=4)
    _FRAME['f'] = (frame, smask, pill, glass, (20 + edge + bez, 10 + edge + bez))
    return _FRAME['f']


def soft_shadow(body, blur=30, dark=0.85, dy=18):
    """A soft drop shadow that follows the body's own shape (its alpha), so the phone never sits on a dark box."""
    pad = blur * 3
    out = Image.new('RGBA', (body.width + pad * 2, body.height + pad * 2), (0, 0, 0, 0))
    a = body.getchannel('A').point(lambda v: int(v * dark))
    sh = Image.new('L', out.size, 0); sh.paste(a, (pad, pad + dy))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.paste((0, 0, 0, 255), (0, 0), sh)
    out.alpha_composite(body, (pad, pad))
    return out


def phone_screen(img, screen, k=1.0, dx=0.0, dy=0.0, alpha=1.0, rot=0.0):
    """Put any 600x1300 screen image into the phone and onto the canvas."""
    frame, smask, pill, glass, (sx, sy) = phone_frame()
    body = frame.copy()
    scr = screen.convert('RGBA').resize((PH_W, PH_H), Image.LANCZOS) if screen.size != (PH_W, PH_H) else screen.convert('RGBA')
    scr = scr.copy(); scr.alpha_composite(glass); scr.alpha_composite(pill)
    a = scr.getchannel('A'); a = Image.composite(a, Image.new('L', a.size, 0), smask); scr.putalpha(a)
    body.alpha_composite(scr, (sx, sy))
    lay = soft_shadow(body)
    cx, cy = W / 2 + dx, PH_Y + PH_H / 2 + dy
    paste_scaled(img, lay, cx, cy, k, alpha, rot)
    return (cx, cy)


def phone(img, shot, scroll=0.0, k=1.0, dx=0.0, dy=0.0, zoom=1.0, focus=(0.5, 0.5), alpha=1.0):
    """A phone showing a real screenshot (1080 px wide), scrolled `scroll` px (in screenshot pixels), optionally zoomed on `focus`."""
    sw = shot.size[0]
    sc = PH_W / sw * zoom
    vis_h = PH_H / sc
    fx = focus[0] * sw
    x0 = max(0, min(sw - PH_W / sc, fx - PH_W / sc / 2)) if zoom > 1.001 else 0
    y0 = max(0, min(shot.size[1] - vis_h, scroll))
    crop = shot.crop((int(x0), int(y0), int(x0 + PH_W / sc), int(y0 + vis_h))).resize((PH_W, PH_H), Image.LANCZOS)
    phone_screen(img, crop, k, dx, dy, alpha)
    return (W / 2 + dx, PH_Y + PH_H / 2 + dy, k, sc, x0, y0)


def window(img, shot, box, cx, cy, width, k=1.0, alpha=1.0, title=None):
    """A real desktop screenshot region in a rounded window with a soft shadow."""
    crop = shot.crop(box)
    h = int(width * crop.size[1] / crop.size[0])
    crop = crop.resize((width, h), Image.LANCZOS).convert('RGBA')
    crop.putalpha(rounded_mask(width, h, 26))
    pad = 0
    body = Image.new('RGBA', (width + pad * 2, h + pad * 2), (0, 0, 0, 0)); body.alpha_composite(crop, (pad, pad))
    d = ImageDraw.Draw(body); d.rounded_rectangle([0, 0, body.size[0] - 1, body.size[1] - 1], radius=26, outline=(80, 78, 72, 255), width=2)
    lay = shadowed(body, radius=30, blur=30, dark=190)[0]
    paste_scaled(img, lay, cx, cy, k, alpha)
    return h


def tap(d, x, y, u):
    """A finger tap: a ring that expands and fades."""
    if not 0 <= u <= 1:
        return
    r = 18 + 50 * ease(u); a = int(230 * (1 - u))
    d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, a), width=6)
    if u < 0.35:
        d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(255, 255, 255, int(200 * (1 - u / 0.35))))


def highlight(d, box, u, col=AMBER, width=6):
    if u <= 0:
        return
    x0, y0, x1, y1 = box; p = 10 * (1 - min(1, u))
    a = int(255 * min(1, u * 2))
    d.rounded_rectangle([x0 - 8 - p, y0 - 8 - p, x1 + 8 + p, y1 + 8 + p], radius=18, outline=col + (a,), width=width)


def bug(d, A, img, tt, label=None):
    paste_scaled(img, A.logo, 104, 250, 64 / 512)
    d.text((150, 250), 'PAPERTRADES.AI', font=F('mono', 'Bold', 36), fill=FG, anchor='lm')
    if label:
        fl = F('mono', 'Bold', 24); tw = d.textlength(label, font=fl)
        x1 = 930; x0 = x1 - tw - 64
        pulse = 0.5 + 0.5 * math.sin(tt * 5)
        col = BLURPLE if 'DISCORD' in label else UP
        d.rounded_rectangle([x0, 226, x1, 274], radius=24, fill=(24, 26, 40, 255) if col == BLURPLE else (18, 38, 26, 255), outline=col + (255,), width=2)
        d.ellipse([x0 + 16, 242, x0 + 32, 258], fill=(int(61 + 60 * pulse), 220, 132, 255))
        d.text((x0 + 44, 250), label, font=fl, fill=FG, anchor='lm')


def caption(d, C, lid, tt):
    if lid not in CAPS:
        return
    k0, chunk, c_at, ccol = 0, None, None, FG
    for j, (txt, nw, col) in enumerate(CAPS[lid]):
        st = C.at_tok(lid, k0)
        if tt >= st - 0.04 or (j == 0 and lid == '01'):
            chunk, c_at, ccol = txt, min(st, tt), col
        k0 += nw
    if chunk:
        q = back(min(1.0, (tt - c_at) * 7))
        fc = F('sans', 'Bold', int(84 * (0.82 + 0.18 * q)))
        tw = d.textlength(chunk, font=fc)
        d.rounded_rectangle([540 - tw / 2 - 34, CAP_Y - 62, 540 + tw / 2 + 34, CAP_Y + 58], radius=40, fill=(8, 8, 7, 175))
        text_c(d, (540, CAP_Y), chunk, fc, ccol, 8, sfill=(6, 6, 5))


def notif(img, d, x, y, w, u, lines_):
    """A phone notification banner (generic, drawn): app icon, title, two lines; slides down with a spring."""
    if u <= 0:
        return
    k = spring(min(1.0, u)); yy = y - 220 * (1 - k)
    lay = Image.new('RGBA', (w, 190), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([0, 0, w - 1, 189], radius=38, fill=(38, 38, 42, 245), outline=(90, 90, 96, 255), width=2)
    ld.rounded_rectangle([26, 30, 96, 100], radius=18, fill=BLURPLE + (255,))
    g = Image.open(os.path.join(HERE, 'assets', 'discord-glyph-white.png')).convert('RGBA'); g.thumbnail((46, 46))
    lay.alpha_composite(g, (61 - g.size[0] // 2, 65 - g.size[1] // 2))
    ld.text((118, 40), lines_[0], font=F('sans', 'Bold', 32), fill=(240, 240, 240), anchor='lm')
    ld.text((w - 30, 40), 'example: its Nov 5 buy', font=F('sans', 'Medium', 24), fill=(170, 170, 176), anchor='rm')
    ld.text((118, 92), lines_[1], font=F('sans', 'Bold', 30), fill=(235, 235, 235), anchor='lm')
    ld.text((118, 140), lines_[2], font=F('sans', 'Medium', 28), fill=(200, 200, 206), anchor='lm')
    sh = shadowed(lay, radius=38, blur=26, dark=200)[0]
    paste_scaled(img, sh, x + w / 2, yy + 95, 1.0, min(1.0, u * 3))


# ================================================================ a phone lock screen with real pings (drawn, generic)
PINGS = [   # real moves (data.json), newest last; the text is what the Discord race channels post
    ('gemini', 'Crypto', 'bought Bitcoin', 'C$35,000', 'G-CRY-028', 'Nov 5'),
    ('gemini', 'Oil and energy', 'bought oil (USO)', 'C$15,000', 'G-ENE-031', 'Nov 12'),
    ('claude', 'Metals', 'sold gold (GLD), +C$119', 'C$20,119', 'C-MET-006', 'Nov 12'),
    ('chatgpt', 'Stocks', 'sold TMV', 'C$13,250', 'X-STK-018', 'Nov 13'),
]


def lock_screen(A, tt, n_pings=0.0, clock='10:24', date='Friday, November 13', dim=0.0):
    """A dark lock screen: our green rising arrow glowing on the wallpaper, the time, and up to four real moves as pings.
    n_pings can be fractional: the newest ping springs in."""
    scr = Image.new('RGBA', (PH_W, PH_H), (10, 12, 11, 255))
    g = Image.new('RGBA', (PH_W, PH_H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.ellipse([-200, 700, PH_W + 200, 1600], fill=(20, 70, 44, 255)); gd.ellipse([-100, -300, PH_W + 100, 400], fill=(28, 36, 70, 255))
    g = g.filter(ImageFilter.GaussianBlur(120)); scr.alpha_composite(g)
    d = ImageDraw.Draw(scr)
    d.line([(60, 1180), (230, 1010), (300, 1070), (540, 830)], fill=UP + (90,), width=26, joint='curve')
    d.text((PH_W / 2, 150), date, font=F('sans', 'Bold', 30), fill=(235, 235, 240), anchor='mm')
    d.text((PH_W / 2, 250), clock, font=F('sans', 'Bold', 150), fill=(245, 245, 248), anchor='mm')
    n = len(PINGS)
    shown = min(n, n_pings)
    for i in range(int(math.ceil(shown))):
        frac = min(1.0, shown - i)
        k = spring(frac)
        who, race, what, amt, tx, when = PINGS[i]
        # newest on top: card i sits at slot (shown_int-1-i)
        slot = int(math.ceil(shown)) - 1 - i
        y = 400 + slot * 150 - 120 * (1 - k)
        card = Image.new('RGBA', (PH_W - 40, 136), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, card.width - 1, 135], radius=30, fill=(46, 46, 52, 228))
        cd.rounded_rectangle([18, 20, 76, 78], radius=15, fill=BLURPLE + (255,))
        gl = A.glyph.copy(); gl.thumbnail((40, 40)); card.alpha_composite(gl, (47 - gl.size[0] // 2, 49 - gl.size[1] // 2))
        cd.ellipse([62, 62, 84, 84], fill=AIC[who] + (255,), outline=(46, 46, 52, 255), width=3)
        chan = {'Crypto': 'crypto', 'Oil and energy': 'energy', 'Metals': 'metals', 'Stocks': 'stocks'}.get(race, race.lower())   # the real channel names
        cd.text((96, 34), f'PaperTrades.AI · #{chan}', font=F('sans', 'Bold', 22), fill=(225, 225, 230), anchor='lm')
        cd.text((card.width - 20, 34), when, font=F('sans', 'Medium', 20), fill=(160, 160, 166), anchor='rm')
        cd.text((96, 72), f'{NAME[who]} · {race}: {what}', font=F('sans', 'Bold', 25), fill=(245, 245, 248), anchor='lm')
        cd.text((96, 106), f'{amt} · Transaction ID {tx}', font=F('sans', 'Medium', 22), fill=(200, 200, 206), anchor='lm')
        a = card.getchannel('A').point(lambda v: int(v * min(1.0, frac * 3))); card.putalpha(a)
        scr.alpha_composite(card, (20, int(y)))
    if dim > 0:
        scr.alpha_composite(Image.new('RGBA', scr.size, (0, 0, 0, int(200 * dim))))
    return scr


# ================================================================ scenes
def scene_01(C, tt, img, d, lt, u):
    """Hook: the three robots land; the live overall standings."""
    xs = {'claude': 250, 'gemini': 540, 'chatgpt': 830}
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        a = spring(max(0.0, (lt - 0.05 - 0.09 * i) * 2.2))
        y = 760 - 480 * (1 - a)
        if a > 0:
            bot(d, xs[k], y, AIC[k], 1.15 * (0.6 + 0.4 * a), talk=0.0, blink=((tt + i) % 3.3) > 3.2)
            d.text((xs[k], y + 160), NAME[k], font=F('sans', 'Bold', 46), fill=AIC[k], anchor='mm')
    st = C.A.f['standings']
    if st and lt > 1.2:
        for i, r in enumerate(st[:3]):
            a = ease(min(1.0, (lt - 1.2 - 0.12 * i) * 3))
            if a <= 0:
                continue
            p = r.get('profit', 0)
            s = ('+' if p >= 0 else '−') + f'C${abs(p):,.0f}'
            x = xs.get(r['id'], 540)
            d.text((x, 990 + 30 * (1 - a)), s, font=F('mono', 'Bold', 44), fill=(UP if p >= 0 else DOWN) + (int(255 * a),), anchor='mm')
        d.text((540, 1070), 'total profit so far · pretend money', font=F('sans', 'Medium', 30), fill=MUTED, anchor='mm')


def scene_02(C, tt, img, d, lt, u):
    """The website: the phone rises, the home page scrolls from the top to the race standings."""
    A = C.A
    k = spring(min(1.0, lt * 2.4))
    scroll = 2100 * ease_io(max(0.0, (lt - 0.7) / max(0.5, C.by['02']['dur'] - 0.6)))
    phone(img, A.home_long, scroll=scroll, k=0.8 + 0.2 * k, dy=260 * (1 - k))


def scene_03(C, tt, img, d, lt, u):
    """Tap a trade: Gemini's own reason and its transaction ID."""
    A = C.A
    k = 1.0 + 0.06 * ease_io(min(1.0, max(0.0, (lt - 0.5) / 1.2)))
    r = phone(img, A.story, scroll=760 + 60 * ease_io(min(1.0, lt / 2.5)), k=k)
    d2 = ImageDraw.Draw(img, 'RGBA')
    tap(d2, 560, 820, (lt - 0.25) / 0.6)
    # the transaction ID gets a ring once it is said
    t_id = C.at_tok('03', 9)
    if tt >= t_id - 0.1:
        a = min(1.0, (tt - t_id + 0.1) * 4)
        fl = F('mono', 'Bold', 32); txt = 'Transaction ID G-CRY-028'; tw = d2.textlength(txt, font=fl)
        y = 1300 - 20 * (1 - a)
        d2.rounded_rectangle([540 - tw / 2 - 26, y - 34, 540 + tw / 2 + 26, y + 34], radius=34, fill=(40, 30, 6, int(240 * a)), outline=AMBER + (int(255 * a),), width=3)
        d2.text((540, y), txt, font=fl, fill=AMBER + (int(255 * a),), anchor='mm')


def grade_card(C, img, d, x, y, who, grade, text, a):
    if a <= 0:
        return
    w, h = 820, 250
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=(26, 25, 22, 250), outline=AIC[who] + (255,), width=3)
    bot(ld, 72, 98, AIC[who], 0.38)
    ld.text((140, 46), f'{NAME[who]} graded it', font=F('sans', 'Bold', 36), fill=AIC[who], anchor='lm')
    ld.rounded_rectangle([w - 120, 22, w - 26, 116], radius=20, fill=AMBER + (255,))
    ld.text((w - 73, 70), grade, font=F('sans', 'Bold', 70), fill=(20, 18, 14), anchor='mm')
    rows = wrap(ld, '“' + text + '”', F('sans', 'Medium', 30), w - 170)
    for i, row in enumerate(rows[:4]):
        ld.text((140, 104 + i * 38), row, font=F('sans', 'Medium', 30), fill=FG, anchor='lm')
    sh = shadowed(lay, radius=28, blur=24, dark=180)[0]
    k = spring(min(1.0, a))
    paste_scaled(img, sh, x + 80 * (1 - k), y, 0.94 + 0.06 * k, min(1.0, a * 2))


def scene_04(C, tt, img, d, lt, u):
    """Peer grades: the other two AIs graded Gemini's oil buy before anyone knew how it would go."""
    f = C.A.f
    d.text((540, 420), 'Gemini bought oil (USO) · C$15,000 · G-ENE-031', font=F('sans', 'Bold', 38), fill=AIC['gemini'], anchor='mm')
    d.text((540, 470), 'graded before the result was known', font=F('sans', 'Medium', 30), fill=MUTED, anchor='mm')
    g = f['grades']
    grade_card(C, img, d, 540, 690, 'claude', g['claude']['grade'], g['claude']['text'], (lt - 0.2) * 2.5)
    grade_card(C, img, d, 540, 990, 'chatgpt', g['chatgpt']['grade'], g['chatgpt']['text'], (lt - 0.8) * 2.5)


def scene_05(C, tt, img, d, lt, u):
    """The Discord: our server's real channel list slides in."""
    A = C.A
    k = spring(min(1.0, lt * 2.2))
    a = A.dc.get('live')
    gl = A.glyph.copy(); gl.thumbnail((110, 110))
    if lt > 0.05:
        paste_scaled(img, gl, 540, 470, spring(min(1.0, (lt - 0.05) * 2.5)), 0.95)
    if a is not None:
        window(img, a, (0, 0, a.size[0], a.size[1]), 540 + 500 * (1 - k), 900, 900, 1.0, min(1.0, lt * 3))
        d.text((540, 1210), '#live-trades: every move, as it happens', font=F('sans', 'Bold', 36), fill=MUTED, anchor='mm')


def scene_06(C, tt, img, d, lt, u):
    """Headlines, every live move, one channel per race: the real channel list with each section lit as it is said."""
    A = C.A
    a = A.dc.get('channels')
    if a is None:
        return
    WW = 420
    h = window(img, a, (0, 0, a.size[0], a.size[1]), 540, 860, WW)
    d2 = ImageDraw.Draw(img, 'RGBA')
    top = 860 - h / 2; sc = WW / a.size[0]
    marks = A.dc_marks.get('channels', {})
    for j, (key, tok) in enumerate((('headlines', 0), ('live', 2), ('races', 5))):
        if key in marks and tt >= C.at_tok('06', tok) - 0.05:
            x0, y0, x1, y1 = marks[key]
            box = (540 - WW / 2 + x0 * sc, top + y0 * sc, 540 - WW / 2 + x1 * sc, top + y1 * sc)
            highlight(d2, box, (tt - C.at_tok('06', tok)) * 4, [AMBER, UP, AMBER][j])


def scene_07(C, tt, img, d, lt, u):
    """Nothing pings you until you pick it: the real 'Which headlines should ping you?' question."""
    A = C.A
    r = A.dc.get('roles')
    if r is None:
        return
    k = spring(min(1.0, lt * 2.4))
    h = window(img, r, (0, 0, r.size[0], r.size[1]), 540, 840 + 120 * (1 - k), 860, 0.96 + 0.04 * k, min(1.0, lt * 3))
    d2 = ImageDraw.Draw(img, 'RGBA'); top = 840 - h / 2; sc = 860 / r.size[0]
    for j, key in enumerate(('daily', 'leads')):
        m = A.dc_marks.get('roles', {}).get(key)
        t0 = C.by['07']['start'] + 0.5 + 0.45 * j
        if m and tt >= t0:
            x0, y0, x1, y1 = m
            box = (540 - 430 + x0 * sc, top + y0 * sc, 540 - 430 + x1 * sc, top + y1 * sc)
            tap(d2, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, (tt - t0) / 0.6)
            highlight(d2, box, (tt - t0) * 4, UP)


def scene_08(C, tt, img, d, lt, u):
    """Pick Gemini, then Crypto: then the ping when Gemini moves (its real Bitcoin buy)."""
    A = C.A
    r = A.dc.get('roles-ai')
    if r is not None:
        h = window(img, r, (0, 0, r.size[0], r.size[1]), 540, 930, 780)
        d2 = ImageDraw.Draw(img, 'RGBA'); top = 930 - h / 2; sc = 780 / r.size[0]
        m = A.dc_marks.get('roles-ai', {}).get('crypto')
        t0 = C.at_tok('08', 2)
        if m and tt >= t0:
            x0, y0, x1, y1 = m
            box = (540 - 390 + x0 * sc, top + y0 * sc, 540 - 390 + x1 * sc, top + y1 * sc)
            tap(d2, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, (tt - t0) / 0.6)
            highlight(d2, box, (tt - t0) * 4, AMBER)
    b = A.f['buy']
    t1 = C.at_tok('08', 4)
    notif(img, ImageDraw.Draw(img, 'RGBA'), 110, 300, 860, (tt - t1) * 2.2,
          ['PaperTrades.AI · #crypto', 'Gemini · Crypto: bought Bitcoin', f'C${b["amount"]:,.0f} · Transaction ID {b["tx"]}'])


def scene_09(C, tt, img, d, lt, u):
    """Change it any time: the server menu with Channels & Roles."""
    A = C.A
    m_ = A.dc.get('menu')
    if m_ is None:
        return
    k = spring(min(1.0, lt * 2.4))
    h = window(img, m_, (0, 0, m_.size[0], m_.size[1]), 540, 820, 820, 1.0, min(1.0, lt * 3))
    d2 = ImageDraw.Draw(img, 'RGBA'); top = 820 - h / 2; sc = 820 / m_.size[0]
    for key, tok in (('name', 3), ('roles', 6)):
        m = A.dc_marks.get('menu', {}).get(key)
        t0 = C.at_tok('09', tok)
        if m and tt >= t0:
            x0, y0, x1, y1 = m
            box = (540 - 410 + x0 * sc, top + y0 * sc, 540 - 410 + x1 * sc, top + y1 * sc)
            tap(d2, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, (tt - t0) / 0.6)
            highlight(d2, box, (tt - t0) * 4, AMBER if key == 'name' else BLURPLE)


def scene_10(C, tt, img, d, lt, u):
    """The end card: the logo, the site, the free Discord, like and subscribe."""
    A = C.A
    k = spring(min(1.0, lt * 1.8))
    paste_scaled(img, A.logo, 540, 640, (300 / 512) * (0.7 + 0.3 * k), min(1.0, lt * 3))
    d.text((540, 880), 'papertrades.ai', font=F('mono', 'Bold', 72), fill=FG + (int(255 * min(1.0, lt * 2)),), anchor='mm')
    if lt > 0.5:
        a = min(1.0, (lt - 0.5) * 3)
        gl = A.glyph.copy(); gl.thumbnail((54, 54))
        d.rounded_rectangle([230, 960, 850, 1040], radius=40, fill=(30, 32, 58, int(255 * a)), outline=BLURPLE + (int(255 * a),), width=3)
        paste_scaled(img, gl, 290, 1000, 1.0, a)
        d.text((560, 1000), 'Free Discord · link in description', font=F('sans', 'Bold', 36), fill=FG + (int(255 * a),), anchor='mm')
    if lt > 1.1:
        a = min(1.0, (lt - 1.1) * 3)
        d.text((540, 1110), 'Like & subscribe for more trade updates', font=F('sans', 'Bold', 40), fill=UP + (int(255 * a),), anchor='mm')
    d.text((540, 1200), 'Pretend money · real prices · not advice', font=F('sans', 'Medium', 30), fill=MUTED, anchor='mm')


SCENES = {'01': scene_01, '02': scene_02, '03': scene_03, '04': scene_04, '05': scene_05, '06': scene_06, '07': scene_07,
          '08': scene_08, '09': scene_09, '10': scene_10}
MOOD = {'01': (AMBER, 0.22, AIC['gemini'], 0.12), '02': (UP, 0.30, None, 0), '03': (AIC['gemini'], 0.34, None, 0), '04': (AIC['claude'], 0.26, AIC['chatgpt'], 0.10),
        '05': (BLURPLE, 0.40, None, 0), '06': (BLURPLE, 0.34, AMBER, 0.08), '07': (BLURPLE, 0.30, UP, 0.10), '08': (AIC['gemini'], 0.30, BLURPLE, 0.14),
        '09': (BLURPLE, 0.32, None, 0), '10': (UP, 0.30, BLURPLE, 0.14)}
LABEL = {'01': None, '02': 'THE WEBSITE', '03': 'THE WEBSITE', '04': 'THE WEBSITE', '05': 'FREE DISCORD', '06': 'FREE DISCORD',
         '07': 'YOUR ALERTS · DISCORD', '08': 'YOUR ALERTS · DISCORD', '09': 'YOUR ALERTS · DISCORD', '10': None}


def frame(C, sc, fi):
    tt = fi / FPS
    lid = sc['id']; lt = tt - sc['s0']; u = lt / max(0.01, sc['s1'] - sc['s0'])
    col, amt, col2, amt2 = MOOD[lid]
    base = background(C.A, tt, col, amt, col2, amt2)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA')
    DA.motes(C.A, img, tt, 0.8)
    if lid != '10':
        bug(d, C.A, img, tt, LABEL[lid])
    SCENES[lid](C, tt, img, d, lt, u)
    d = ImageDraw.Draw(img, 'RGBA')
    caption(d, C, lid, tt)
    zoom = 1.0 + 0.025 * ease_io(u)
    if lt < 0.16 and lid != '01':
        zoom += 0.05 * (1 - ease(lt / 0.16))
    shake = 14 * math.exp(-tt * 9) if tt < 0.45 else 0.0
    blur_x = int(60 * (1 - lt / 0.12)) if lid in ('02', '05', '07', '10') and lt < 0.12 else 0
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    return DA.finish(C.A, a, tt, shake, zoom, 0.0, 0.0, blur_x, 0.0, fi)


# ================================================================ sound
def mix_audio(C, lines, total, marks, out_wav):
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    for ln in lines:
        s = int(ln['start'] * SR); x = ln['x'] * 0.95
        voice[s:s + len(x)] += x[:max(0, n - s)]
    fx = np.zeros(n, np.float32)

    def put(name, at, vol=1.0):
        y = AA.sfx(name) * vol; s = int(at * SR)
        if s < 0:
            y = y[-s:]; s = 0
        fx[s:s + len(y)] += y[:max(0, n - s)]
    by = C.by
    put('impact', 0.0, 0.8)
    for i in range(3):
        put('pop', 0.12 + 0.09 * i, 0.9)
    put('whoosh', by['02']['start'] - 0.25, 0.8)
    put('pop', by['03']['start'] + 0.15, 0.9); put('tick', C.at_tok('03', 9), 0.9)
    put('stamp', by['04']['start'] + 0.1, 0.8); put('stamp', by['04']['start'] + 0.7, 0.8)
    put('whip', by['05']['start'] - 0.2, 0.9); put('impact', by['05']['start'] + 0.3, 0.5)
    for tok in (0, 2, 5):
        put('ping', C.at_tok('06', tok), 0.7)
    put('pop', by['07']['start'] + 0.5, 0.9); put('pop', by['07']['start'] + 0.95, 0.9)
    put('pop', C.at_tok('08', 2), 0.9); put('ping2', C.at_tok('08', 4), 1.0)
    put('pop', C.at_tok('09', 3), 0.8); put('pop', C.at_tok('09', 6), 0.8)
    put('whoosh', by['10']['start'] - 0.25, 0.8); put('ching', by['10']['start'] + 0.2, 0.8)
    music = AA.score(total + 0.5, marks, seed='yt-ad2', bpm=BPM)
    m = np.zeros((n, 2), np.float32); m[:min(n, len(music))] = music[:n]
    env = np.convolve(np.abs(voice), np.ones(int(0.2 * SR)) / (0.2 * SR), 'same')
    duck = np.clip(1 - env * 9.0, 0.25, 1.0)
    duck = np.convolve(duck, np.ones(int(0.08 * SR)) / (0.08 * SR), 'same')
    st = m * (0.46 * duck)[:, None] + voice[:, None] + (fx * 0.7)[:, None]
    st = st[:int(total * SR)]
    st /= max(1.0, np.abs(st).max() / 0.97)
    AA.write_wav(out_wav, st)
    return out_wav


# ================================================================ render
_G = {}


def _init(args):
    name, engine, fake = args
    d = json.load(open(os.path.join(ROOT, 'data.json')))
    f = facts(d)
    script = json.load(open(os.path.join(HERE, 'voice', f'{name}.json')))
    vdir = os.path.join(ROOT, 'social', 'voice', name, engine)
    words = json.load(open(f'{vdir}/words.json')) if (not fake and os.path.exists(f'{vdir}/words.json')) else {}
    lines, scenes, total, marks = timeline(script, vdir, words, fake)
    A = Assets(f)
    mp = os.path.join(FOOT, 'marks.json')
    A.dc_marks = json.load(open(mp)) if os.path.exists(mp) else {}
    _G['C'] = Ctx(A, lines, scenes, total)
    return lines, scenes, total, marks


def _render_scene(job):
    sc, path, crf = job
    C = _G['C']
    f0, f1 = int(round(sc['s0'] * FPS)), int(round(sc['s1'] * FPS))
    tmp = path[:-4] + '.part.mp4'
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        ff.stdin.write(frame(C, sc, fi).tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise Fail('ffmpeg failed on scene ' + sc['id'])
    os.replace(tmp, path)
    return path, f1 - f0


def build(name, engine='gemini', out_dir='social/ads', stills=False, fake=False, crf=18):
    lines, scenes, total, marks = _init((name, engine, fake))
    C = _G['C']
    work = f'/tmp/yt_ad2/{name}'
    os.makedirs(work, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    if stills:
        outs = []
        for sc in scenes:
            for frac in (0.35, 0.85):
                tm = sc['s0'] + (sc['s1'] - sc['s0']) * frac
                p = f'{work}/still-{sc["id"]}-{int(frac * 100)}.jpg'; Image.fromarray(frame(C, sc, int(tm * FPS))).save(p, quality=88); outs.append(p)
        return outs, {'total': round(total, 2)}
    wav = mix_audio(C, lines, total, marks, f'{work}/mix.wav')
    jobs = [(sc, f'{work}/scene-{sc["id"]}.mp4', crf) for sc in scenes]
    with ProcessPoolExecutor(max_workers=3, initializer=_init, initargs=((name, engine, fake),)) as ex:
        done = list(ex.map(_render_scene, jobs))
    lst = f'{work}/scenes.txt'
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p, _ in done))
    silent = f'{work}/video.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent], check=True)
    out = os.path.join(out_dir, f'{name}.mp4'); tmp = out[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, out)
    meta = {'name': name, 'engine': engine, 'seconds': round(total, 2), 'lines': {ln['id']: [round(ln['start'], 2), round(ln['dur'], 2)] for ln in lines}}
    json.dump(meta, open(os.path.join(out_dir, f'{name}.json'), 'w'), indent=1)
    return out, meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('--engine', default='gemini'); ap.add_argument('--out', default='social/ads')
    ap.add_argument('--stills', action='store_true'); ap.add_argument('--fake', action='store_true'); ap.add_argument('--crf', type=int, default=18)
    a = ap.parse_args()
    print(build(a.name, a.engine, a.out, a.stills, a.fake, a.crf))
