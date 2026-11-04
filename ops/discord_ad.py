"""The PaperTrades.AI Discord commercial (owner, Nov 4: "make a comercial for papertrades.ai adveritsing the discord channel work
with gpt and gemini for the ideas make it high production").

Ideas: ops/review/discord-ad-nov4.json (Gemini and ChatGPT) and ops/review/discord-ad-claude-concept.md (Claude, written first).
All three agreed on the spine: one real story (Gemini's C$35,000 on underdog USC at +200, graded by Claude and ChatGPT BEFORE the
game, USC 30-18, +C$70,000), each AI speaking its own words, the real cards the Discord posts, then the channels and the invite.

Every number is read from data.json (the public ledger) and checked; the render stops if one is off. The cards are the real cards
(ops/sharecard.py), the lead-change text is the real #lead-changes post (ops/discord_leads.py). Music and sounds: ops/ad_audio.py.

  python3 ops/discord_ad.py discord-ad-v1 [--engine gemini] [--out social/ads] [--stills]   (--stills: key frames only)
"""
import argparse
import json
import math
import os
import subprocess
import sys
import wave
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from postcard import font  # noqa: E402
import ad_audio as AA  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
NY = ZoneInfo('America/New_York')
BG = (11, 11, 10); FG = (242, 233, 216); MUTED = (155, 146, 127); PANEL = (21, 20, 17); LINE = (48, 46, 40)
UP, DOWN, AMBER, INK, CREAM = (61, 220, 132), (255, 90, 78), (255, 176, 0), (20, 18, 14), (242, 233, 216)
BLURPLE = (88, 101, 242)
AIC = {'claude': (217, 119, 87), 'gemini': (79, 143, 247), 'chatgpt': (242, 242, 242)}
NAME = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
L, R = 80, 930            # nothing important within 150 px of the right edge (like / comment buttons)
TOP, BOT = 250, 1430      # nor in the top 250 px or the bottom 490 px (title, channel name)
CAP_Y = 1318              # the captions' centre line
INVITE = 'discord.gg/PkqX3zstD'


class Fail(Exception):
    pass


# ================================================================ the facts, from the ledger
def facts(d):
    T = {t['tx']: t for t in d['allin_trades'] if t.get('tx')}
    bets = [T.get(k) for k in ('G-AIS-019', 'G-AIS-024', 'G-AIS-026')]
    wins = [T.get(k) for k in ('G-AIS-028', 'G-AIS-029', 'G-AIS-030')]
    if any(b is None for b in bets + wins):
        raise Fail('a USC ticket is missing from the ledger')
    for b, st in zip(bets, (5000, 10000, 20000)):
        if b['model'] != 'gemini' or b['action'] != 'Bet' or 'USC Trojans moneyline' not in b['name'] or float(b['price']) != 200 or float(b['stake']) != st:
            raise Fail('a USC bet is not what the ad says: ' + b['tx'])
    for w_, p in zip(wins, (10000, 20000, 40000)):
        if w_['model'] != 'gemini' or w_['action'] != 'Won' or float(w_['pnl']) != p or 'Ohio State Buckeyes 18, USC Trojans 30' not in w_['reason']:
            raise Fail('a USC result is not what the ad says: ' + w_['tx'])
    reason = bets[2]['reason']
    if not reason.startswith('Aggressively capitalizing on the massive +200 value of USC'):
        raise Fail("Gemini's reason changed: " + reason)
    gr = {g['grader']: g for g in d['peer_grades'] if g.get('model') == 'gemini' and g.get('decision_at') == bets[2]['at'] and g.get('experiment') == 'AllInSports'}
    if gr.get('claude', {}).get('grade') != 'C' or 'one quarterback factor without a priced model edge is thin support' not in gr['claude'].get('text', ''):
        raise Fail("Claude's grade of G-AIS-026 is not the C the ad quotes")
    if gr.get('chatgpt', {}).get('grade') != 'B' or "calling +200 'massive value' lacks a price model" not in gr['chatgpt'].get('text', ''):
        raise Fail("ChatGPT's grade of G-AIS-026 is not the B the ad quotes")
    staked = sum(float(b['stake']) for b in bets); won = sum(float(w_['pnl']) for w_ in wins)
    if staked != 35000 or won != 70000:
        raise Fail(f'totals changed: staked {staked}, won {won}')
    lead = [m for m in d.get('moments') or [] if m.get('race') == 'Sports' and m.get('who') == 'gemini' and m['at'].startswith('2026-10-31T03:14')]
    if not lead:
        raise Fail('the Sports lead change of Oct 30 is missing')
    return {'bets': bets, 'wins': wins, 'staked': staked, 'won': won, 'grades': gr, 'reason': reason, 'lead': lead[0]}


def check_script(script):
    """The voice says only what the ledger says: the numbers and the three quotes."""
    txt = {ln['id']: ln['text'] for ln in script['lines']}
    need = {'02': 'thirty-five thousand', '03': 'Aggressively capitalizing on the massive plus two hundred value of USC',
            '04': 'One quarterback factor without a priced model edge is thin support', '05': 'Calling plus two hundred massive value lacks a price model',
            '06': 'USC thirty, Ohio State eighteen', '07': 'seventy thousand'}
    for k, v in need.items():
        if v not in txt.get(k, ''):
            raise Fail(f'line {k} no longer says "{v}"')


# ================================================================ drawing helpers
def F(kind, weight, size):
    return font(kind, weight, max(1, int(size)))


def clamp(u):
    return max(0.0, min(1.0, u))


def ease(u):
    u = clamp(u); return 1 - (1 - u) ** 3


def ease_io(u):
    u = clamp(u); return u * u * (3 - 2 * u)


def back(u, s=1.70158):   # overshoot then settle
    u = clamp(u); return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2


def spring(u, k=7.0, damp=4.2):   # a damped spring from 0 to 1 (overshoots, rings once, settles)
    if u <= 0:
        return 0.0
    return 1 - math.exp(-damp * u) * math.cos(k * u)


def text_c(d, xy, s, f, fill, stroke=0, anchor='mm', sfill=(0, 0, 0)):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill if stroke else None)


def bot(d, x, y, col, s=1.0, talk=0.0, blink=False, mood='smile'):
    """One of the three AI robots (the site's mascots): talks (mouth follows the voice), blinks, can look worried or cheer."""
    lw = max(3, int(9 * s))
    d.line([(x, y - 120 * s), (x, y - 170 * s)], fill=CREAM, width=lw)
    glow = int(160 + 95 * talk)
    d.ellipse([x - 22 * s, y - 200 * s, x + 22 * s, y - 156 * s], fill=(255, min(255, 150 + glow // 3), 102), outline=INK, width=max(3, int(6 * s)))
    d.rounded_rectangle([x - 95 * s, y - 120 * s, x + 95 * s, y + 80 * s], radius=int(46 * s), fill=col, outline=INK, width=max(4, int(10 * s)))
    for ex in (-38, 38):
        if blink:
            d.line([(x + (ex - 20) * s, y - 40 * s), (x + (ex + 20) * s, y - 40 * s)], fill=INK, width=max(3, int(8 * s)))
        else:
            d.ellipse([x + (ex - 20) * s, y - 60 * s, x + (ex + 20) * s, y - 20 * s], fill=INK)
            d.ellipse([x + (ex - 6) * s, y - 52 * s, x + (ex + 4) * s, y - 42 * s], fill=CREAM)
    if talk > 0.08:
        h = 8 + 34 * talk
        d.rounded_rectangle([x - 30 * s, y + (30 - h / 2) * s, x + 30 * s, y + (30 + h / 2) * s], radius=int(14 * s), fill=INK)
    elif mood == 'worried':
        d.line([(x - 32 * s, y + 40 * s), (x, y + 26 * s), (x + 32 * s, y + 40 * s)], fill=INK, width=lw, joint='curve')
    elif mood == 'cheer':
        d.chord([x - 38 * s, y + 4 * s, x + 38 * s, y + 62 * s], 0, 180, fill=INK)
    else:
        d.line([(x - 35 * s, y + 25 * s), (x, y + 45 * s), (x + 35 * s, y + 25 * s)], fill=INK, width=lw, joint='curve')


def bot_sprite(col, s=1.0, **kw):
    """The robot on its own transparent canvas (centre of the face at the canvas centre + 40*s down)."""
    w_, h_ = int(240 * s), int(320 * s)
    lay = Image.new('RGBA', (w_, h_), (0, 0, 0, 0))
    bot(ImageDraw.Draw(lay), w_ / 2, h_ / 2 + 40 * s, col, s, **kw)
    return lay


def stamp_layer(letter, col, size=260):
    """A grade stamp (an outlined rounded square with the letter, slightly rotated), as an RGBA image."""
    s = size
    lay = Image.new('RGBA', (s + 60, s + 60), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([30, 30, s + 30, s + 30], radius=int(s * .18), fill=(20, 18, 14, 210), outline=col + (255,), width=max(8, s // 16))
    fl = F('sans', 'Bold', s * .74); bx = ld.textbbox((0, 0), letter, font=fl)
    ld.text(((s + 60) / 2 - (bx[0] + bx[2]) / 2, (s + 60) / 2 - (bx[1] + bx[3]) / 2), letter, font=fl, fill=col + (255,))
    return lay.rotate(-11, resample=Image.BICUBIC, expand=True)


def paste_scaled(img, lay, cx, cy, k, alpha=1.0, rot=0.0):
    if k <= 0.01 or alpha <= 0.01:
        return
    lw, lh = max(1, int(lay.width * k)), max(1, int(lay.height * k))
    l2 = lay.resize((lw, lh), Image.BICUBIC)
    if rot:
        l2 = l2.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = l2.getchannel('A').point(lambda v: int(v * alpha)); l2.putalpha(a)
    img.paste(l2, (int(cx - l2.width / 2), int(cy - l2.height / 2)), l2)


def shadowed(card, radius=26, blur=28, dark=170):
    """The card with rounded corners and a soft drop shadow, as one RGBA image (made once per card)."""
    c = card.convert('RGBA')
    m = Image.new('L', c.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, c.width - 1, c.height - 1], radius=radius, fill=255)
    c.putalpha(m)
    pad = blur * 3
    out = Image.new('RGBA', (c.width + pad * 2, c.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new('L', out.size, 0); ImageDraw.Draw(sh).rounded_rectangle([pad, pad + blur // 2, pad + c.width, pad + c.height + blur // 2], radius=radius, fill=dark)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.paste((0, 0, 0, 255), (0, 0), sh)
    out.alpha_composite(c, (pad, pad))
    return out, pad


def tilt(card_rgba, yaw=0.0, pitch=0.0, scale=1.0):
    """A cheap 3-D tilt: the card's corners moved as if it were turned (yaw, pitch in radians) and seen from a camera in front."""
    w_, h_ = card_rgba.size
    src = np.float32([[0, 0], [w_, 0], [w_, h_], [0, h_]])
    f = 2200.0
    pts = []
    for x, y in src:
        X, Y, Z = (x - w_ / 2) * scale, (y - h_ / 2) * scale, 0.0
        X, Z = X * math.cos(yaw) + Z * math.sin(yaw), -X * math.sin(yaw) + Z * math.cos(yaw)
        Y, Z = Y * math.cos(pitch) - Z * math.sin(pitch), Y * math.sin(pitch) + Z * math.cos(pitch)
        k = f / (f + Z)
        pts.append([X * k, Y * k])
    pts = np.float32(pts)
    mnx, mny = pts[:, 0].min(), pts[:, 1].min()
    dst = pts - [mnx, mny]
    ow, oh = int(math.ceil(pts[:, 0].max() - mnx)) + 2, int(math.ceil(pts[:, 1].max() - mny)) + 2
    M = cv2.getPerspectiveTransform(src, dst)
    arr = cv2.warpPerspective(np.asarray(card_rgba), M, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(arr, 'RGBA')


def glint(lay, u, width=0.16, strength=0.55):
    """A light sweep across an RGBA layer (u: 0..1 position of the band), kept inside the layer's own shape."""
    if not 0 < u < 1:
        return lay
    w_, h_ = lay.size
    xx = np.linspace(0, 1, w_)[None, :] + np.linspace(0, 0.5, h_)[:, None]
    c = u * 1.6 - 0.3
    band = np.clip(1 - np.abs(xx - c) / width, 0, 1) ** 2 * strength
    a = np.asarray(lay).astype(np.float32)
    a[..., :3] = np.minimum(255, a[..., :3] + band[..., None] * 255 * (a[..., 3:4] / 255))
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def wrap(d, text, f, width):
    out, cur = [], ''
    for w_ in text.split():
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            out.append(cur); cur = w_
    if cur:
        out.append(cur)
    return out


# ================================================================ sound helpers
def read_wav(path):
    with wave.open(path) as w:
        sr = w.getframerate(); ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        n = int(len(x) * SR / sr); x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def trim(x, thr=0.012):
    a = np.abs(x); idx = np.where(a > thr)[0]
    if not len(idx):
        return x, 0.0
    s = max(0, idx[0] - int(0.03 * SR)); e = min(len(x), idx[-1] + int(0.06 * SR))
    return x[s:e], s / SR


def envelope(x, fps=FPS):
    hop = SR // fps
    n = len(x) // hop + 1
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(x) else 0 for i in range(n)])
    return np.clip(e / (e.max() + 1e-6) * 1.3, 0, 1)


def token_times(text, words, dur, cut):
    import yt_short
    return yt_short.token_times(text, words, dur, cut)


# ================================================================ the timeline
GAP_AFTER = {'01': 0.10, '02': 0.18, '03': 0.22, '04': 0.20, '05': 0.28, '06': 0.22, '07': 0.60, '08': 0.22}
END_HOLD = 2.4
BPM = 120
TEMPO = {'01': 1.10, '02': 1.12, '03': 1.08, '04': 1.08, '05': 1.07, '06': 1.20, '07': 1.04, '08': 1.10, '09': 1.04}   # a commercial's pace (pitch kept)


def tempo_wav(src, f, dst):
    """The same line, f times faster, pitch kept (ffmpeg atempo): done once, cached."""
    if f == 1.0:
        return src
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-filter:a', f'atempo={f}', dst + '.tmp.wav'], check=True)
        os.replace(dst + '.tmp.wav', dst)
    return dst


def timeline(script, vdir, words, fake=False):
    lines, t = [], 0.10
    for ln in script['lines']:
        if fake:   # before the voice exists: about 2.9 words a second
            dur = len(ln['text'].split()) / 2.9 + 0.2; x = np.zeros(int(dur * SR), np.float32); tok = list(np.linspace(0, dur * 0.95, len(ln['text'].split())))
        else:
            f_ = TEMPO.get(ln['id'], 1.0)
            src = tempo_wav(f'{vdir}/{ln["id"]}.wav', f_, f'/tmp/discord_ad/{script["name"]}/vo/{ln["id"]}-{f_}.wav')
            x, cut = trim(read_wav(src))
            dur = len(x) / SR
            wl = [[w_, a_ / f_, b_ / f_] for w_, a_, b_ in (words.get(ln['id']) or [])]
            tok = token_times(ln['text'], wl, dur, cut)
        lines.append({**ln, 'x': x, 'start': t, 'dur': dur, 'tok': tok, 'env': envelope(x) if len(x) else np.zeros(1)})
        t += dur + GAP_AFTER.get(ln['id'], 0.3)
    # lock the payoff and the end card to the music's beat: the drop lands on a downbeat (the voice waits a moment if needed)
    beat = 60 / BPM
    by = {ln['id']: ln for ln in lines}
    verse = by['02']['start'] - 0.05
    def snap_after(tt):
        k = math.ceil((tt - verse) / beat - 1e-6)   # the beat grid: locked to the music, never more than half a second of waiting
        return verse + k * beat
    for lid in ('07', '09'):
        want = snap_after(by[lid]['start'] - 0.06) + 0.06 if lid == '07' else snap_after(by[lid]['start'])
        shift = want - by[lid]['start']
        if shift > 0:
            hit = False
            for ln in lines:
                if ln['id'] == lid:
                    hit = True
                if hit:
                    ln['start'] += shift
    total = lines[-1]['start'] + lines[-1]['dur'] + END_HOLD
    scenes = []
    for i, ln in enumerate(lines):
        s0 = 0.0 if i == 0 else ln['start'] - 0.10
        s1 = total if i == len(lines) - 1 else lines[i + 1]['start'] - 0.10
        scenes.append({'id': ln['id'], 's0': s0, 's1': s1})
    marks = {'verse': verse, 'build': by['06']['start'] - 0.1, 'drop': by['07']['start'] - 0.06, 'outro': by['09']['start']}
    return lines, scenes, total, marks


# ================================================================ captions: a few words at a time, key words in colour
CAPS = {
    '01': [('3 AIs', 2, FG), ('racing with', 2, FG), ('pretend money', 2, AMBER), ('and grading', 2, FG), ("each other's", 2, FG), ('every move.', 2, UP)],
    '02': [('Gemini put', 2, AIC['gemini']), ('C$35,000', 2, AMBER), ('on underdog', 2, FG), ('USC.', 1, AIC['gemini'])],
    '06': [('Then the game.', 3, FG), ('USC 30,', 2, UP), ('Ohio State 18.', 3, FG)],
    '07': [('', 4, UP)],
    '08': [('Every trade,', 2, FG), ('every bet,', 2, FG), ('every grade,', 2, FG), ('posted live', 2, UP), ('in our Discord.', 3, BLURPLE)],
}
QUOTES = {   # quote lines: who, the words shown (the spoken part), the source label
    '03': ('gemini', '“Aggressively capitalizing on the massive +200 value of USC…”', 'GEMINI’S OWN REASON · G-AIS-026'),
    '04': ('claude', '“…one quarterback factor without a priced model edge is thin support…”', 'CLAUDE’S GRADE · GIVEN BEFORE THE GAME'),
    '05': ('chatgpt', '“…calling +200 ‘massive value’ lacks a price model…”', 'CHATGPT’S GRADE · GIVEN BEFORE THE GAME'),
}


# ================================================================ assets (made once per process)
class Assets:
    def __init__(self, f, card_dir):
        import sharecard
        import racecard
        import discord_leads
        os.makedirs(card_dir, exist_ok=True)
        b019, b024, b026 = f['bets']; w030 = f['wins'][2]
        self.card = {}
        for k, path in (('bet', sharecard.move_card('gemini', b026, f'{card_dir}/bet.png')), ('won', sharecard.move_card('gemini', w030, f'{card_dir}/won.png')),
                        ('rec', sharecard.receipt_card('gemini', w030, b026, sharecard.grades_for('gemini', b026), f'{card_dir}/receipt.png')),
                        ('b019', sharecard.move_card('gemini', b019, f'{card_dir}/b019.png')), ('b024', sharecard.move_card('gemini', b024, f'{card_dir}/b024.png'))):
            if not path or not os.path.exists(path):
                raise Fail('a card did not render: ' + k)
            self.card[k] = Image.open(path).convert('RGB')
        tab, _ = racecard.races(None, os.path.join(os.path.dirname(HERE), 'ops', 'src'))
        rc = racecard.races_card(tab, None, 'Daily results · each race on its own', f'{card_dir}/races.png')
        self.races = Image.open(rc if isinstance(rc, str) and os.path.exists(rc) else f'{card_dir}/races.png').convert('RGB')
        self.lead_text = discord_leads.text(f['lead'])
        root = os.path.dirname(HERE)
        self.logo = Image.open(os.path.join(root, 'brand', 'logo-circle-512.png')).convert('RGBA')
        self.glyph = Image.open(os.path.join(HERE, 'assets', 'discord-glyph-white.png')).convert('RGBA')
        # the big card, with its shadow, at the size it is shown
        self.bet_big = shadowed(self.card['bet'].resize((700, 875), Image.LANCZOS))
        self.stampC = stamp_layer('C', AIC['claude'], 250)
        self.stampB = stamp_layer('B', (235, 235, 235), 250)
        # background: a dark radial base, a vignette, grain
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.42) / (H * 0.62)) ** 2)
        self.vig = np.clip(1.08 - 0.55 * r ** 1.6, 0.35, 1.0)[..., None].astype(np.float32)
        self.base = (np.array(BG, np.float32)[None, None, :] * np.ones((H, W, 1), np.float32))
        g = np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy - 820) / 720) ** 2))
        self.glow = g[..., None].astype(np.float32)
        rng = np.random.default_rng(5)
        self.grain = [rng.normal(0, 5.5, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
        # drifting dust motes (bokeh), fixed per process so every frame of a scene agrees
        self.motes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(10, 34), rng.uniform(6, 22), rng.uniform(0, 6.28), rng.uniform(0.05, 0.14)) for _ in range(22)]
        yy2, xx2 = np.mgrid[-32:32, -32:32].astype(np.float32)
        blob = np.clip(1 - np.sqrt(xx2 ** 2 + yy2 ** 2) / 32, 0, 1) ** 1.6
        spr = np.zeros((64, 64, 4), np.uint8); spr[..., :3] = 255; spr[..., 3] = (blob * 255).astype(np.uint8)
        self.sprite = Image.fromarray(spr, 'RGBA')


# ================================================================ one frame
class Ctx:
    def __init__(self, A, f, lines, scenes, total):
        self.A, self.f, self.lines, self.scenes, self.total = A, f, lines, scenes, total
        self.by = {ln['id']: ln for ln in lines}

    def at_tok(self, lid, k):
        ln = self.by[lid]; return ln['start'] + ln['tok'][max(0, min(k, len(ln['tok']) - 1))]

    def talking(self, lid, tt):
        ln = self.by[lid]; i = int((tt - ln['start']) * FPS)
        return float(ln['env'][i]) if 0 <= i < len(ln['env']) else 0.0

    def end_of(self, lid):
        ln = self.by[lid]; return ln['start'] + ln['dur']


def blink(tt, seed):
    return tt > 0.6 and ((tt + seed * 0.37) % 3.7) > 3.58


def background(A, tt, col, amt=0.34, col2=None, amt2=0.0):
    img = A.base.copy()
    img += A.glow * (np.array(col, np.float32) - np.array(BG, np.float32)) * amt
    if col2 is not None and amt2 > 0:
        sh = np.roll(A.glow, int(260 * math.sin(tt * 0.7)), axis=1)
        img += sh * (np.array(col2, np.float32) - np.array(BG, np.float32)) * amt2
    return img


def finish(A, img_f, tt, shake=0.0, zoom=1.0, rot=0.0, aberr=0.0, blur_x=0, flash=0.0, frame_i=0):
    """Camera and film: zoom, shake, a slight roll, motion blur for whips, colour fringing on hits, a flash, vignette and grain."""
    a = img_f
    if zoom != 1.0 or shake or rot:
        rng = np.random.default_rng(frame_i * 31 + 7)
        dx, dy = (rng.uniform(-1, 1) * shake, rng.uniform(-1, 1) * shake) if shake else (0, 0)
        M = cv2.getRotationMatrix2D((W / 2, H * 0.45), rot, zoom)
        M[0, 2] += dx; M[1, 2] += dy
        a = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if blur_x > 2:
        k = np.zeros((1, int(blur_x)), np.float32); k[0, :] = 1 / int(blur_x)
        a = cv2.filter2D(a, -1, k)
    if aberr > 0.5:
        s = int(aberr)
        a = a.copy()
        a[..., 0] = np.roll(a[..., 0], s, axis=1); a[..., 2] = np.roll(a[..., 2], -s, axis=1)
    a = a * A.vig
    g = A.grain[frame_i % len(A.grain)]
    a = a + cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    if flash > 0:
        a = a + (255 - a) * flash
    return np.clip(a, 0, 255).astype(np.uint8)


def motes(A, img, tt, k=1.0):
    """Soft out-of-focus specks drifting up (depth), not a starfield."""
    for (x, y, r, sp, ph, al) in A.motes:
        yy = (y - tt * sp) % H; xx = x + 18 * math.sin(tt * 0.6 + ph)
        paste_scaled(img, A.sprite, xx, yy, 2 * r / 64, al * k * (0.6 + 0.4 * math.sin(tt * 1.3 + ph)))


def floor(d, tt, col):
    """A perspective grid floor below the safe area (decoration): lines run toward a vanishing point and slide toward the camera."""
    vx, vy = 540, 1150
    for i in range(-9, 10):
        x0 = vx + i * 150
        d.line([(vx + (x0 - vx) * 0.05, 1450), (vx + (x0 - vx) * 2.2, H)], fill=col + (26,), width=2)
    ph = (tt * 0.9) % 1.0
    for j in range(9):
        z = (j + ph) / 9
        y = 1450 + (H - 1450) * z ** 2.2
        d.line([(0, y), (W, y)], fill=col + (int(10 + 34 * z),), width=2)


def bug(d, A, img, tt, race=None):
    """The premise, always on screen: the logo and name, LIVE ON DISCORD, the one-line premise."""
    paste_scaled(img, A.logo, L + 24, 286, 56 / 512)
    d.text((L + 64, 286), 'PAPERTRADES.AI', font=F('mono', 'Bold', 34), fill=FG, anchor='lm')
    pulse = 0.5 + 0.5 * math.sin(tt * 5)
    x1 = R + 4; fl = F('mono', 'Bold', 24); tw = d.textlength('LIVE ON DISCORD', font=fl)
    x0 = x1 - tw - 64
    d.rounded_rectangle([x0, 262, x1, 310], radius=24, fill=(30, 32, 58, 255), outline=BLURPLE + (255,), width=2)
    d.ellipse([x0 + 16, 278, x0 + 32, 294], fill=(int(61 + 60 * pulse), 220, 132, 255))
    d.text((x0 + 44, 286), 'LIVE ON DISCORD', font=fl, fill=FG, anchor='lm')
    d.text((L, 336), race or '3 AIs · C$100,000 of pretend money each · real prices', font=F('sans', 'Medium', 32), fill=MUTED, anchor='lm')


def caption(d, C, lid, tt):
    if lid not in CAPS:
        return
    k0, chunk, c_at, ccol = 0, None, None, FG
    for j, (txt, nw, col) in enumerate(CAPS[lid]):
        st = C.at_tok(lid, k0)
        if tt >= st - 0.04 or (j == 0 and lid == '01'):
            chunk, c_at, ccol = txt, min(st, tt), col
        k0 += nw
    if lid == '01' and tt < C.by['01']['start']:
        chunk, c_at = CAPS['01'][0][0], 0.0
    if chunk:
        q = back((tt - c_at) * 7)
        fc = F('sans', 'Bold', 96 * (0.8 + 0.2 * q))
        text_c(d, (540, CAP_Y), chunk, fc, ccol, 10, sfill=(6, 6, 5))


def karaoke(d, C, lid, tt, col):
    """A quote line: the spoken words light up as they are said (the shown quote may start or end with an ellipsis)."""
    who, quote, src = QUOTES[lid]
    ln = C.by[lid]
    import speech_text
    spoken = len(speech_text.tokens(ln['text'], drop_and=False))
    heard = sum(1 for k in range(spoken) if tt >= C.at_tok(lid, k))
    ws = quote.split()
    lead = 1 if ws[0].startswith('“…') else 0
    lit = min(len(ws), lead + int(round(heard * (len(ws) - lead) / max(1, spoken)))) if heard else 0
    fq = F('sans', 'Bold', 60)
    rows = wrap(d, quote, fq, R - L + 20)
    yy = CAP_Y - (len(rows) - 1) * 36
    k = 0
    for row in rows:
        x = 540 - d.textlength(row, font=fq) / 2
        for w_ in row.split():
            on = k < lit
            d.text((x, yy), w_, font=fq, fill=FG if on else (120, 114, 100), anchor='lm', stroke_width=6, stroke_fill=(6, 6, 5))
            if on and k == lit - 1:
                d.line([(x, yy + 40), (x + d.textlength(w_, font=fq), yy + 40)], fill=col, width=6)
            x += d.textlength(w_ + ' ', font=fq); k += 1
        yy += 72


# ---------------------------------------------------------------- the scenes
def scene_01(C, tt, img, d, lt, u):
    A = C.A
    xs = {'claude': 235, 'gemini': 540, 'chatgpt': 845}
    land = {'claude': 0.0, 'gemini': 0.09, 'chatgpt': 0.18}
    for k in ('claude', 'gemini', 'chatgpt'):
        e = lt - land[k]
        if e < 0:
            continue
        # a slam: big and faint, then its size in 0.14 s, then a small wobble
        kk = 1 + 0.8 * (1 - ease(e / 0.14)) + (0.06 * math.exp(-(e - 0.14) * 10) * math.sin((e - 0.14) * 30) if e > 0.14 else 0)
        al = min(1.0, 0.35 + e / 0.1)
        spr = bot_sprite(AIC[k], 1.05, blink=blink(tt, len(k)), mood='worried' if k == 'gemini' and tt > C.at_tok('01', 8) else 'smile')
        paste_scaled(img, spr, xs[k], 830 - 40 * 1.05, kk, al)
        if e > 0.12:
            text_c(d, (xs[k], 975), NAME[k], F('sans', 'Bold', 56), AIC[k])
    # the title: 3 AIs / pretend money, word by word
    q1 = back((lt - 0.05) * 5)
    text_c(d, (540, 470), '3 AIs. 1 RACE.', F('sans', 'Bold', 118 * (0.7 + 0.3 * q1)), FG, 6)
    t_pm = C.at_tok('01', 4)
    if tt >= t_pm - 0.05:
        q = back((tt - t_pm + 0.05) * 5)
        text_c(d, (540, 580), 'C$100,000 EACH · PRETEND MONEY', F('mono', 'Bold', 46 * (0.6 + 0.4 * q)), AMBER, 4)
    # "grading each other's": Claude's C and ChatGPT's B fly at Gemini (the grades of the story, foreshadowed)
    t_g = C.at_tok('01', 7)
    for k, lay, sx, delay in (('claude', A.stampC, xs['claude'], 0.0), ('chatgpt', A.stampB, xs['chatgpt'], 0.16)):
        v = (tt - t_g - delay) * 3.2
        if v > 0:
            p = ease(v)
            tx_ = xs['gemini'] + (-122 if k == 'claude' else 122)
            cx = sx + (tx_ - sx) * p
            cy = 720 - 150 * math.sin(math.pi * min(1, v)) + (676 - 720) * p
            paste_scaled(img, lay, cx, cy, 0.36 + 0.14 * (1 - p), rot=(1 - p) * (40 if k == 'claude' else -40) + (8 if k == 'chatgpt' else 0))


def scene_02(C, tt, img, d, lt, u):
    A = C.A; f = C.f
    bot(d, 200, 600, AIC['gemini'], 0.95, blink=blink(tt, 1))
    q = back(lt * 4)
    d.text((330, 470), 'GEMINI’S BET', font=F('mono', 'Bold', 38), fill=MUTED)
    d.text((326, 512), 'USC', font=F('sans', 'Bold', int(124 * (0.75 + 0.25 * q))), fill=AIC['gemini'])
    d.text((330, 660), '+200 · THE UNDERDOG', font=F('mono', 'Bold', 40), fill=AMBER)
    # the three tickets, as the real ledger has them
    box = (L, 750, R, 1196)
    d.rounded_rectangle(box, radius=28, fill=PANEL + (235,), outline=AIC['gemini'] + (255,), width=4)
    d.text((L + 36, 786), 'High risk: sports · Oct 31 · USC moneyline at +200', font=F('sans', 'Medium', 34), fill=MUTED)
    for i, (b, when) in enumerate(zip(f['bets'], ('3:14 p.m.', '4:14 p.m.', '6:14 p.m.'))):
        t_in = 0.2 + 0.32 * i
        if lt >= t_in:
            p = ease((lt - t_in) * 4)
            yy = 850 + i * 76; xo = (1 - p) * 300
            d.text((L + 36 + xo, yy), when, font=F('mono', 'Bold', 42), fill=FG)
            d.text((L + 560 + xo, yy), f"C${float(b['stake']):,.0f}", font=F('mono', 'Bold', 44), fill=AMBER, anchor='ra')
            d.text((R - 30 + xo, yy + 6), b['tx'], font=F('mono', 'Medium', 30), fill=MUTED, anchor='ra')
    if lt > 1.15:
        p = ease((lt - 1.15) * 2.2)
        d.line([(L + 36, 1086), (R - 30, 1086)], fill=LINE, width=3)
        d.text((L + 36, 1104), 'Total', font=F('mono', 'Bold', 52), fill=FG)
        d.text((L + 560, 1104), f"C${f['staked'] * p:,.0f}", font=F('mono', 'Bold', 56), fill=AMBER, anchor='ra')


def card_at(C, img, tt, x, y, k=1.0, yaw=0.0, pitch=0.0, gl=None, alpha=1.0):
    lay, pad = C.A.bet_big
    t = tilt(lay, yaw, pitch, k) if (yaw or pitch or k != 1.0) else lay
    if gl is not None:
        t = glint(t, gl)
    paste_scaled(img, t, x, y, 1.0, alpha)


def scene_quote_card(C, tt, img, d, lt, u, lid):
    """03, 04, 05: the real bet card (G-AIS-026) in the middle; the speaker talks; the grades slam onto it."""
    who = QUOTES[lid][0]
    s03 = C.by['03']['start']
    intro = clamp((tt - s03 + 0.1) / 0.55) if lid == '03' else 1.0
    yaw = (1 - ease(intro)) * 0.9 + 0.06 * math.sin(tt * 0.9)
    pitch = 0.05 * math.sin(tt * 0.7 + 1)
    k = 0.78 + 0.05 * ease(intro)
    gl = ((tt - s03 - 0.35) / 1.1) if lid == '03' else None
    card_at(C, img, tt, 540, 800, k, yaw, pitch, gl, alpha=ease(intro * 1.4))
    d.text((L, 392), QUOTES[lid][2], font=F('mono', 'Bold', 30), fill=AIC[who] if who != 'chatgpt' else FG, anchor='lm')
    # the speaker, beside the card
    sx = {'gemini': 150, 'claude': 150, 'chatgpt': 868}[who]
    enter = ease((tt - C.by[lid]['start'] + 0.25) * 4)
    sy = 1102 + (1 - enter) * 500
    bot(d, sx, sy, AIC[who], 0.6, talk=C.talking(lid, tt), blink=blink(tt, 2))
    # the stamps: Claude's C lands as Claude starts, ChatGPT's B as ChatGPT starts; they stay
    for sl, lay, cx, cy, rot in (('04', C.A.stampC, 712, 590, 0), ('05', C.A.stampB, 372, 960, 8)):
        ts = C.by[sl]['start'] + 0.05
        if tt >= ts:
            v = (tt - ts) * 5
            kk = 1 + 1.4 * (1 - ease(v))
            paste_scaled(img, lay, cx, cy, 0.62 * kk, alpha=min(1, v * 2), rot=rot)
    d2 = ImageDraw.Draw(img, 'RGBA')
    karaoke(d2, C, lid, tt, AIC[who] if who != 'chatgpt' else UP)


def scene_06(C, tt, img, d, lt, u):
    A = C.A
    text_c(d, (540, 470), 'FINAL SCORE', F('mono', 'Bold', 46), MUTED)
    # stadium light beams (abstract, no logos)
    box = (L, 560, R, 1060)
    d.rounded_rectangle(box, radius=30, fill=PANEL + (240,), outline=LINE + (255,), width=3)
    rows = (('OHIO STATE', 18, MUTED, C.at_tok('06', 7)), ('USC', 30, FG, C.at_tok('06', 4)))
    for i, (team, pts, col, t_land) in enumerate(rows):
        yy = 680 + i * 220
        d.text((L + 50, yy + 40), team, font=F('sans', 'Bold', 86), fill=col, anchor='lm')
        if team == 'USC':
            d.rounded_rectangle([L + 50, yy + 108, L + 330, yy + 158], radius=24, fill=(26, 40, 70, 255))
            d.text((L + 190, yy + 133), 'Gemini’s pick', font=F('sans', 'Bold', 34), fill=AIC['gemini'], anchor='mm')
        # slot-machine digits that land when the number is said
        if tt < t_land:
            v = int((tt * 37 + i * 7) % 60)
            d.text((R - 50, yy + 40), f'{v:02d}', font=F('mono', 'Bold', 150), fill=(110, 105, 92), anchor='rm')
        else:
            q = back((tt - t_land) * 6)
            d.text((R - 50, yy + 40), str(pts), font=F('mono', 'Bold', int(150 * (0.8 + 0.2 * q))), fill=UP if team == 'USC' else col, anchor='rm')


def rays(img, cx, cy, tt, col, alpha, n=14, length=1500):
    """Slowly turning light rays behind a payoff (drawn soft: half size, blurred, added)."""
    lay = Image.new('L', (W // 2, H // 2), 0); ld = ImageDraw.Draw(lay)
    for i in range(n):
        a0 = tt * 0.35 + i * 2 * math.pi / n
        p1 = (cx / 2 + math.cos(a0 - 0.07) * length / 2, cy / 2 + math.sin(a0 - 0.07) * length / 2)
        p2 = (cx / 2 + math.cos(a0 + 0.07) * length / 2, cy / 2 + math.sin(a0 + 0.07) * length / 2)
        ld.polygon([(cx / 2, cy / 2), p1, p2], fill=int(255 * alpha))
    lay = lay.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    img.paste(Image.new('RGB', (W, H), col), (0, 0), lay)


def scene_07(C, tt, img, d, lt, u):
    A = C.A; f = C.f
    t0 = C.by['07']['start'] - 0.06
    el = tt - t0
    if el > 0:
        rays(img, 540, 930, tt, UP, 0.16 * min(1, el * 3))
    d = ImageDraw.Draw(img, 'RGBA')
    # confetti, behind the words
    rng = np.random.default_rng(11)
    if el > 0:
        for i in range(110):
            ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05); sp = rng.uniform(700, 1600); col = [UP, AMBER, AIC['gemini'], AIC['claude'], FG][i % 5]
            sz = rng.uniform(10, 20); spin = rng.uniform(4, 12)
            x = 540 + math.cos(ang) * sp * el * 0.8
            y = 930 + math.sin(ang) * sp * el + 1100 * el * el
            if -40 < x < W + 40 and -40 < y < H:
                rot = el * spin + i
                dx, dy = math.cos(rot) * sz, math.sin(rot) * sz * 0.45
                d.polygon([(x - dx, y - dy), (x + dy, y - dx), (x + dx, y + dy), (x - dy, y + dx)], fill=col + (230,))
    hop = 40 * abs(math.sin(max(0, el) * 7)) * math.exp(-max(0, el) * 1.5)
    bot(d, 540, 640 - hop, AIC['gemini'], 1.12, blink=False, mood='cheer')
    q0 = back(el * 5)
    text_c(d, (540, 822), 'GEMINI WON', F('sans', 'Bold', int(92 * (0.75 + 0.25 * q0))), AIC['gemini'], 7)
    v = ease(el / 0.45)
    k = back(el * 4.5)
    text_c(d, (515, 975), f"+C${f['won'] * v:,.0f}", F('mono', 'Bold', int(142 * (0.7 + 0.3 * k))), UP, 9)
    if el > 0.5:
        a_ = int(255 * clamp((el - 0.5) * 3))
        text_c(d, (540, 1100), '3 winning tickets · G-AIS-028 · 029 · 030', F('mono', 'Medium', 32), FG + (a_,), 3)
        text_c(d, (540, 1152), 'USC 30 · Ohio State 18 · pretend money', F('sans', 'Medium', 34), MUTED + (a_,))


def feed_message(img, d, A, x, y, w_, head, lines, card=None, card_w=560, when='', hl=0.0):
    """One post in #live-trades, as the server shows it: avatar, PaperTrades.AI APP, the time, the text, the card. Returns its bottom."""
    if hl > 0:   # a new post flashes, like an unread highlight
        d.rounded_rectangle([x - 18, y - 14, x + w_ + 10, y + 150 + (int(card.height * card_w / card.width) if card is not None else 0)], radius=18,
                            fill=(88, 101, 242, int(46 * hl)))
        d.rectangle([x - 18, y - 14, x - 12, y + 150], fill=(88, 101, 242, int(255 * hl)))
    paste_scaled(img, A.logo, x + 38, y + 38, 76 / 512)
    fn = F('sans', 'Bold', 40)
    d.text((x + 96, y + 4), 'PaperTrades.AI', font=fn, fill=FG)
    nx = x + 96 + d.textlength('PaperTrades.AI', font=fn) + 12
    d.rounded_rectangle([nx, y + 12, nx + 66, y + 44], radius=6, fill=BLURPLE + (255,))
    d.text((nx + 33, y + 28), 'APP', font=F('sans', 'Bold', 24), fill=(255, 255, 255), anchor='mm')
    d.text((nx + 80, y + 16), when, font=F('sans', 'Medium', 28), fill=MUTED)
    yy = y + 62
    d.text((x + 96, yy), head, font=F('sans', 'Bold', 34), fill=AIC['gemini']); yy += 46
    for ln, col in lines:
        for row in wrap(d, ln, F('sans', 'Medium', 33), w_ - 110):
            d.text((x + 96, yy), row, font=F('sans', 'Medium', 33), fill=col); yy += 42
    if card is not None:
        ch = int(card.height * card_w / card.width)
        c2 = card.resize((card_w, ch), Image.LANCZOS).convert('RGBA')
        m = Image.new('L', c2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, c2.width - 1, c2.height - 1], radius=16, fill=255)
        c2.putalpha(m)
        img.paste(c2, (int(x + 96), int(yy + 10)), c2)
        yy += ch + 18
    return yy


def scene_08(C, tt, img, d, lt, u):
    A = C.A; f = C.f
    s = C.by['08']['start']
    msgs = [('GEMINI · High risk: sports', [('Bet: USC Trojans moneyline', FG), ('C$20,000 at +200 · to win C$40,000', AMBER)], A.card['bet'], 'Oct 31, 6:14 PM'),
            ('GEMINI · High risk: sports', [('Won: USC Trojans moneyline', FG), ('+C$40,000 · Final: Ohio State 18, USC 30', UP)], A.card['won'], 'Oct 31, 11:14 PM'),
            ('GEMINI · the bet behind it', [('Graded before the result: Claude C · ChatGPT B', FG)], A.card['rec'], 'Oct 31, 11:14 PM')]
    arrivals = [s - 0.12, s + 0.62, s + 1.32]
    t_split = C.at_tok('08', 6) - 0.1   # "posted live in our Discord": the channels
    clip = Image.new('RGBA', (W, H), (0, 0, 0, 0)); cd = ImageDraw.Draw(clip)
    # where each post starts (measured once by drawing off-screen), and the scroll that brings the newest to the top
    if not hasattr(A, 'feed_h'):
        tmp = Image.new('RGBA', (W, 6000)); td = ImageDraw.Draw(tmp); y0 = 0; A.feed_y = []
        for head, lines, card, when in msgs:
            A.feed_y.append(y0); y0 = feed_message(tmp, td, A, L - 6, y0, R - L, head, lines, card, 560, when) + 40
        A.feed_h = y0
    scroll = 0.0
    for i, ta in enumerate(arrivals):
        if i and tt >= ta:
            scroll += ease((tt - ta) * 3.2) * (A.feed_y[i] - A.feed_y[i - 1])
    top = 486
    for i, (head, lines, card, when) in enumerate(msgs):
        if tt < arrivals[i]:
            break
        p = ease((tt - arrivals[i]) * 4.5)
        y = top + A.feed_y[i] - scroll + (1 - p) * 140
        if y > 1300:
            continue
        feed_message(clip, cd, A, L - 6, y, R - L, head, lines, card, 560, when, hl=max(0.0, 1 - (tt - arrivals[i]) / 0.7))
    a = np.asarray(clip).astype(np.float32)
    ramp = np.ones(H, np.float32)
    ramp[:466] = 0; ramp[466:520] = np.linspace(0, 1, 54); ramp[1150:1230] = np.linspace(1, 0, 80); ramp[1230:] = 0
    a[..., 3] *= ramp[:, None]
    if tt >= t_split:   # the feed steps back for the channels
        a[..., 3] *= 1 - ease((tt - t_split) * 3.5)
    img.alpha_composite(Image.fromarray(a.astype(np.uint8), 'RGBA'))
    d = ImageDraw.Draw(img, 'RGBA')
    # the channel header, on top of the feed
    d.rounded_rectangle([L - 20, 382, R + 10, 452], radius=18, fill=(28, 29, 34, 250))
    if tt < t_split:
        d.text((L + 6, 417), '#', font=F('sans', 'Bold', 48), fill=MUTED, anchor='lm')
        d.text((L + 42, 417), 'live-trades', font=F('sans', 'Bold', 42), fill=FG, anchor='lm')
    else:
        paste_scaled(img, A.logo, L + 24, 417, 50 / 512)
        d.text((L + 62, 417), 'PaperTrades.AI server · 3 channels', font=F('sans', 'Bold', 40), fill=FG, anchor='lm')
    n_new = sum(1 for ta in arrivals if tt >= ta)
    if tt < t_split and n_new:
        d.rounded_rectangle([R - 200, 398, R - 6, 436], radius=19, fill=(237, 66, 69, 255))
        d.text((R - 103, 417), f'{n_new} new', font=F('sans', 'Bold', 28), fill=(255, 255, 255), anchor='mm')
    if tt >= t_split:
        chans = [('live-trades', 'every trade, bet and result, as it happens', UP),
                 ('daily-results', 'the race card after each daily close', AMBER),
                 ('lead-changes', 'who just took the lead, and by how much', AIC['gemini'])]
        for i, (nm, desc, col) in enumerate(chans):
            p = back((tt - t_split - 0.12 * i) * 4)
            if p <= 0:
                continue
            yy = 520 + i * 210; xo = (1 - min(1, p)) * 500
            d.rounded_rectangle([L + xo, yy, R + xo, yy + 180], radius=26, fill=(24, 25, 32, 248), outline=col + (255,), width=4)
            d.text((L + 36 + xo, yy + 58), '# ' + nm, font=F('sans', 'Bold', 64), fill=FG, anchor='lm')
            d.text((L + 36 + xo, yy + 128), desc, font=F('sans', 'Medium', 34), fill=MUTED, anchor='lm')
            pulse = 0.5 + 0.5 * math.sin(tt * 6 + i)
            d.ellipse([R - 64 + xo, yy + 44, R - 36 + xo, yy + 72], fill=(int(200 + 55 * pulse), 60, 60, 255))


def scene_09(C, tt, img, d, lt, u):
    A = C.A
    s = C.by['09']['start'] - 0.1
    el = tt - s
    rays(img, 540, 640, tt, BLURPLE, 0.10 * min(1, max(0, el) * 2), n=10, length=1300)
    d = ImageDraw.Draw(img, 'RGBA')
    k = spring(max(0, el) * 1.6, 8, 5)
    lg = glint(A.logo, (el - 0.5) / 1.0, 0.14, 0.5)
    paste_scaled(img, lg, 540, 640, 0.80 * k)
    if el > 0.2:
        q = back((el - 0.2) * 4)
        text_c(d, (540, 968), 'Join free on Discord', F('sans', 'Bold', int(96 * (0.7 + 0.3 * q))), FG, 7)
    if el > 0.4:
        q = back((el - 0.4) * 4)
        bw, bh = 640 * q, 116 * q
        d.rounded_rectangle([540 - bw / 2, 1088 - bh / 2, 540 + bw / 2, 1088 + bh / 2], radius=max(1, int(58 * q)), fill=BLURPLE + (255,))
        paste_scaled(img, A.glyph, 540 - 205 * q, 1088, 0.12 * q)
        d.text((540 + 34 * q, 1088), 'Join the server', font=F('sans', 'Bold', int(54 * q) + 1), fill=(255, 255, 255), anchor='mm')
    if el > 0.6:
        n = int(clamp((el - 0.6) / 0.5) * len(INVITE))
        d.text((540, 1204), INVITE[:n] + ('▍' if n < len(INVITE) and int(el * 8) % 2 else ''), font=F('mono', 'Bold', 56), fill=AMBER, anchor='mm')
    t_p = C.at_tok('09', 3) - 0.05
    if tt >= t_p:   # "and pick your AI"
        q = back((tt - t_p) * 5)
        fb = F('sans', 'Bold', int(46 * (0.8 + 0.2 * q)))
        parts = [('Pick your AI:  ', FG), ('Claude', AIC['claude']), ('  ·  ', MUTED), ('Gemini', AIC['gemini']), ('  ·  ', MUTED), ('ChatGPT', AIC['chatgpt'])]
        tw = sum(d.textlength(t_, font=fb) for t_, _ in parts); x = 540 - tw / 2
        for t_, c_ in parts:
            d.text((x, 1290), t_, font=fb, fill=c_, anchor='lm', stroke_width=4, stroke_fill=(6, 6, 5)); x += d.textlength(t_, font=fb)
    if el > 1.1:
        a_ = int(255 * clamp((el - 1.1) * 2))
        d.text((540, 1362), 'Pretend money · real prices · not advice · Oct 28 – Nov 28', font=F('sans', 'Medium', 30), fill=MUTED + (a_,), anchor='mm')
    # the three robots pop up at the bottom (decoration, below the safe line), cheering in turn
    for i, kk in enumerate(('claude', 'gemini', 'chatgpt')):
        p = ease((el - 0.3 - 0.1 * i) * 3)
        hop = 18 * max(0, math.sin((el - 0.8) * 6 - i)) if el > 0.8 else 0
        bot(d, 300 + i * 240, 1690 + (1 - p) * 320 - hop, AIC[kk], 0.8, blink=blink(tt, i), mood='cheer' if hop > 8 else 'smile')


SCENES = {'01': scene_01, '02': scene_02, '03': lambda *a: scene_quote_card(*a, '03'), '04': lambda *a: scene_quote_card(*a, '04'),
          '05': lambda *a: scene_quote_card(*a, '05'), '06': scene_06, '07': scene_07, '08': scene_08, '09': scene_09}
MOOD = {'01': (AMBER, 0.20, AIC['gemini'], 0.12), '02': (AIC['gemini'], 0.34, None, 0), '03': (AIC['gemini'], 0.36, None, 0), '04': (AIC['claude'], 0.36, AIC['gemini'], 0.10),
        '05': ((200, 200, 200), 0.22, AIC['gemini'], 0.10), '06': (AMBER, 0.24, None, 0), '07': (UP, 0.40, AIC['gemini'], 0.16), '08': (BLURPLE, 0.36, UP, 0.10),
        '09': (BLURPLE, 0.40, UP, 0.12)}


def frame(C, sc, fi):
    tt = fi / FPS
    lid = sc['id']; lt = tt - sc['s0']; u = lt / max(0.01, sc['s1'] - sc['s0'])
    col, amt, col2, amt2 = MOOD[lid]
    base = background(C.A, tt, col, amt, col2, amt2)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA')
    floor(d, tt, tuple(int(c) for c in col))
    motes(C.A, img, tt, 0.9)
    bug(d, C.A, img, tt, 'High risk: sports (side race) · pretend money · real odds' if lid in ('02', '03', '04', '05', '06', '07') else None)
    SCENES[lid](C, tt, img, d, lt, u)
    d = ImageDraw.Draw(img, 'RGBA')
    caption(d, C, lid, tt)
    # the camera: a slow push through each scene, a punch-in on each cut, shake and fringing on the hits
    zoom = 1.0 + 0.035 * ease_io(u)
    if lt < 0.16 and lid != '01':
        zoom += 0.06 * (1 - ease(lt / 0.16))
    shake, aberr, flash, blur_x = 0.0, 0.0, 0.0, 0
    hits = [0.0, C.by['04']['start'] + 0.05, C.by['05']['start'] + 0.05, C.by['07']['start'] - 0.06, C.by['09']['start']]
    for i, h_ in enumerate(hits):
        e = tt - h_
        if 0 <= e < 0.45:
            shake = max(shake, (22 if i in (0, 3) else 14) * math.exp(-e * 9))
            aberr = max(aberr, (9 if i in (0, 3) else 5) * math.exp(-e * 12))
    if 0 <= tt - hits[3] < 0.18:
        flash = 0.55 * (1 - (tt - hits[3]) / 0.18)
    # whips into the scenes that change place: a short horizontal motion blur on the first frames
    if lid in ('03', '06', '08', '09') and lt < 0.12:
        blur_x = int(70 * (1 - lt / 0.12))
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    return finish(C.A, a, tt, shake, zoom, 0.0, aberr, blur_x, flash, fi)


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
    put('impact', 0.0, 0.9); put('buzz', 0.02, 0.8)
    for k, dt in (('claude', 0.0), ('gemini', 0.14), ('chatgpt', 0.28)):
        put('pop', dt + 0.18, 0.9)
    t_g = C.at_tok('01', 7); put('whoosh', t_g - 0.1, 0.7); put('stamp', t_g + 0.3, 0.6); put('stamp', t_g + 0.46, 0.6)
    s2 = by['02']['start']
    put('whoosh', s2 - 0.2, 0.8)
    for i in range(3):
        put('ping', s2 + 0.2 + 0.32 * i, 0.8 + 0.1 * i)
    for i in range(6):
        put('tick', s2 + 1.15 + i * 0.08, 0.8)
    put('whip', by['03']['start'] - 0.2, 0.9)
    put('stamp', by['04']['start'] + 0.05, 1.0); put('impact', by['04']['start'] + 0.05, 0.45)
    put('stamp', by['05']['start'] + 0.05, 1.0); put('impact', by['05']['start'] + 0.05, 0.45)
    put('whip', by['06']['start'] - 0.2, 0.9)
    for k in (4, 7):
        put('pop', C.at_tok('06', k), 0.9)
    d0 = by['07']['start'] - 0.06
    put('impact', d0, 1.0); put('ching', d0 + 0.05, 1.0)
    s8 = by['08']['start']
    put('whip', s8 - 0.2, 0.8)
    for ta in (s8 - 0.05, s8 + 0.55, s8 + 1.15):
        put('ping', ta, 0.9)
    t_split = C.at_tok('08', 6) - 0.1
    for i in range(3):
        put('ping2', t_split + 0.12 * i, 0.7)
    s9 = by['09']['start'] - 0.1
    put('whoosh', s9 - 0.25, 0.7); put('pop', s9 + 0.45, 0.9)
    music = AA.score(total + 0.5, marks, seed='discord-ad', bpm=BPM)
    m = np.zeros((n, 2), np.float32); m[:min(n, len(music))] = music[:n]
    # duck the music under the voice (smoothly), keep it full in the gaps and on the drop
    env = np.convolve(np.abs(voice), np.ones(int(0.2 * SR)) / (0.2 * SR), 'same')
    duck = np.clip(1 - env * 9.0, 0.25, 1.0)   # the voice sits about 12 dB over the music; full music in the gaps
    duck = np.convolve(duck, np.ones(int(0.08 * SR)) / (0.08 * SR), 'same')
    st = m * (0.50 * duck)[:, None] + (voice * 1.0)[:, None] + (fx * 0.75)[:, None]
    st = st[:int(total * SR)]
    st /= max(1.0, np.abs(st).max() / 0.97)
    AA.write_wav(out_wav, st)
    return out_wav


# ================================================================ render
_G = {}


def _init(args):
    name, engine, fake, card_dir = args
    d = json.load(open('data.json'))
    f = facts(d)
    script = json.load(open(f'ops/voice/{name}.json'))
    vdir = f'social/voice/{name}/{engine}'
    words = json.load(open(f'{vdir}/words.json')) if (not fake and os.path.exists(f'{vdir}/words.json')) else {}
    lines, scenes, total, marks = timeline(script, vdir, words, fake)
    A = Assets(f, card_dir)
    _G['C'] = Ctx(A, f, lines, scenes, total)
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


def _worker_init(args):
    _init(args)


def build(name, engine='gemini', out_dir='social/ads', stills=False, fake=False, crf=17, audio_only=False):
    script = json.load(open(f'ops/voice/{name}.json'))
    check_script(script)
    card_dir = f'/tmp/discord_ad/{name}/cards'
    lines, scenes, total, marks = _init((name, engine, fake, card_dir))
    C = _G['C']
    work = f'/tmp/discord_ad/{name}'
    os.makedirs(work, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    if stills:   # the busiest moments, at full size, to look at before a full render
        moments = [0.35, C.at_tok('01', 8) + 0.5, C.by['02']['start'] + 1.6, C.by['03']['start'] + 1.2, C.by['04']['start'] + 0.9, C.by['05']['start'] + 1.0,
                   C.at_tok('06', 7) + 0.3, C.by['07']['start'] + 0.35, C.by['08']['start'] + 1.0, C.at_tok('08', 6) + 0.6, total - 0.5]
        outs = []
        for i, tm in enumerate(moments):
            fi = int(tm * FPS); sc = next(s for s in scenes if s['s0'] <= tm < s['s1'] or s is scenes[-1])
            p = f'{work}/still-{i:02d}.jpg'; Image.fromarray(frame(C, sc, fi)).save(p, quality=90); outs.append(p)
        return outs, {'total': total, 'marks': marks, 'lines': {ln['id']: [round(ln['start'], 2), round(ln['dur'], 2)] for ln in lines}}
    wav = mix_audio(C, lines, total, marks, f'{work}/mix.wav')
    silent = f'{work}/video.mp4'
    if not (audio_only and os.path.exists(silent)):
        jobs = [(sc, f'{work}/scene-{sc["id"]}.mp4', crf) for sc in scenes]
        with ProcessPoolExecutor(max_workers=2, initializer=_worker_init, initargs=((name, engine, fake, card_dir),)) as ex:
            done = list(ex.map(_render_scene, jobs))
        lst = f'{work}/scenes.txt'
        open(lst, 'w').write(''.join(f"file '{p}'\n" for p, _ in done))
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent], check=True)
    out = os.path.join(out_dir, f'{name}.mp4'); tmp = out[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, out)
    meta = {'name': name, 'engine': engine, 'seconds': round(total, 2), 'marks': {k: round(v, 2) for k, v in marks.items()},
            'lines': {ln['id']: [round(ln['start'], 2), round(ln['dur'], 2)] for ln in lines}}
    json.dump(meta, open(os.path.join(out_dir, f'{name}.json'), 'w'), indent=1)
    return out, meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('--engine', default='gemini'); ap.add_argument('--out', default='social/ads')
    ap.add_argument('--stills', action='store_true'); ap.add_argument('--fake', action='store_true'); ap.add_argument('--crf', type=int, default=17); ap.add_argument('--audio-only', action='store_true')
    a = ap.parse_args()
    print(build(a.name, a.engine, a.out, a.stills, a.fake, a.crf, a.audio_only))
