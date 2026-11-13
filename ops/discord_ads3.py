"""Three Discord commercials for paid boosting; the owner picks one (owner, Nov 13: "generate 3 other options with the other models so i
can pick from commercial 1 two or 3 ... this is for the discord channel. make it look good. and unique. were going to be boosting this
post alot to grow the discord channel").

  Option 1  "The Tour"       Claude's commercial (ops/yt_ad2.py) cut for a paid boost as Gemini asked: no peer-grade scene, under 30 s
  Option 2  "The Pings"      Gemini's concept: real moves landing on a phone, you choose who pings you, every move comes with a receipt
  Option 3  "Pick Your AI"   ChatGPT's concept: the three AIs as rival characters on a select screen; pick one, get its moves
Concepts and boost notes: ops/review/discord-ads3-nov13.json. Voices: ops/voice/discord-ads3.json (+ yt-ad2-v1 for Option 1).

For paid review (ChatGPT's notes): no betting words on screen (the site is filmed with the High risk sports box hidden, the Discord crops
stop before the betting channels), no claims about real people or companies, one call to action (join the Discord), no like-and-subscribe.
Everything shown is real: the site (filmed), our Discord (screenshots), the move card the bot posts, real moves (the render stops if one
changed), the live totals (dated on screen). The phone is a generic slim modern phone, no maker's logo or exact design.

  python3 ops/discord_ads3.py 1|2|3 [--stills] [--out DIR] [--crf N]
"""
import argparse
import datetime as dt
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import yt_ad2 as Y  # noqa: E402
import discord_ad as DA  # noqa: E402
import ad_audio as AA  # noqa: E402
from discord_ad import (W, H, FPS, SR, FG, MUTED, UP, DOWN, AMBER, BLURPLE, AIC, NAME, F, ease, ease_io, back, spring,  # noqa: E402
                        text_c, bot, paste_scaled, Fail)

ROOT = os.path.dirname(HERE)
V1 = os.path.join(ROOT, 'social', 'voice', 'yt-ad2-v1', 'gemini')
V3 = os.path.join(ROOT, 'social', 'voice', 'discord-ads3', 'gemini')
S1 = json.load(open(os.path.join(HERE, 'voice', 'yt-ad2-v1.json')))
S3 = json.load(open(os.path.join(HERE, 'voice', 'discord-ads3.json')))
LINES = {**{'1-' + x['id']: (x, V1) for x in S1['lines']}, **{x['id']: (x, V3) for x in S3['lines']}}

OPTIONS = {
    '1': {'name': 'discord-ad-option1', 'title': 'The Tour', 'by': 'Claude', 'lines': ['1-01', '1-02', '1-03', '1-05', '1-06', '1-07', '1-08', 'a10']},
    '2': {'name': 'discord-ad-option2', 'title': 'The Pings', 'by': 'Gemini', 'lines': ['b01', 'b02', 'b03', 'b04', 'b05']},
    '3': {'name': 'discord-ad-option3', 'title': 'Pick Your AI', 'by': 'ChatGPT', 'lines': ['c01', 'c02', 'c03', 'c04', 'c05', 'c06', 'c07', 'c08', 'c09']},
}
GAP = {'1-01': 0.14, '1-02': 0.18, '1-03': 0.18, '1-05': 0.14, '1-06': 0.18, '1-07': 0.16, '1-08': 0.26,
       'b01': 0.22, 'b02': 0.22, 'b03': 0.24, 'b04': 0.26,
       'c01': 0.20, 'c02': 0.10, 'c03': 0.10, 'c04': 0.22, 'c05': 0.14, 'c06': 0.14, 'c07': 0.16, 'c08': 0.24}
TEMPO = {'1-01': 1.08, '1-02': 1.08, '1-03': 1.06, '1-05': 1.06, '1-06': 1.10, '1-07': 1.04, '1-08': 1.06,
         'c01': 1.12, 'b01': 1.04, 'b02': 1.05}
END_HOLD = {'1': 2.3, '2': 2.6, '3': 2.6}     # Option 1 stays under 30 s (Gemini's boost note)
BPM = 120


# ================================================================ facts (read from the public data; stop if one changed)
def facts(d):
    rt = {x['tx']: x for x in d['rivals_trades'] if x.get('tx')}
    ct = {x['tx']: x for x in d['trades'] if isinstance(x, dict) and x.get('tx')}

    def need(tx, sym, amt, action):
        x = rt.get(tx) or ct.get(tx)
        if not x:
            raise Fail(f'{tx} is missing from data.json')
        s = x.get('symbol') or x.get('holding'); a = x.get('amount', x.get('cad'))
        if s != sym or abs(float(a) - amt) > 1 or x.get('action') != action:
            raise Fail(f'{tx} changed: {action} {s} {a}')
        return x
    buy = need('G-CRY-028', 'BTC-USD', 35000, 'Buy')                 # the pings on the lock screen (yt_ad2.PINGS) and the move card
    need('G-ENE-031', 'USO', 15000, 'Buy')
    gold = need('C-MET-006', 'GLD', 20119.37, 'Sell')
    need('X-STK-018', 'TMV', 13250.12, 'Sell')
    if round(gold['pnl_cad']) != 119:
        raise Fail('C-MET-006 profit changed')
    st = sorted(d['standings'], key=lambda r: -r['profit'])
    newest = max(x['at'] for x in d['rivals_trades'])
    asof = dt.datetime.fromisoformat(newest.replace('Z', '+00:00')) - dt.timedelta(hours=5)    # ET (EST from Nov 2)
    return {'buy': buy, 'standings': st, 'st': {r['id']: r['profit'] for r in st},
            'leads': {r['id']: len(r.get('leads') or []) for r in st}, 'asof': asof.strftime('%b %-d')}


# ================================================================ timeline
def timeline(ids, fake=False, end_hold=2.6):
    lines, t = [], 0.12
    for lid in ids:
        ln, vdir = LINES[lid]
        if fake:
            dur = len(ln['text'].split()) / 2.9 + 0.2; x = np.zeros(int(dur * SR), np.float32); tok = list(np.linspace(0, dur * 0.95, len(ln['text'].split())))
        else:
            f_ = TEMPO.get(lid, 1.03)
            os.makedirs('/tmp/discord_ads3/vo', exist_ok=True)
            src = DA.tempo_wav(f'{vdir}/{ln["id"]}.wav', f_, f'/tmp/discord_ads3/vo/{lid}-{f_}.wav')
            x, cut = DA.trim(DA.read_wav(src))
            dur = len(x) / SR
            words = json.load(open(f'{vdir}/words.json')) if os.path.exists(f'{vdir}/words.json') else {}
            wl = [[w_, a_ / f_, b_ / f_] for w_, a_, b_ in (words.get(ln['id']) or [])]
            tok = DA.token_times(ln['text'], wl, dur, cut)
        lines.append({**ln, 'id': lid, 'x': x, 'start': t, 'dur': dur, 'tok': tok, 'env': DA.envelope(x) if len(x) else np.zeros(1)})
        t += dur + GAP.get(lid, 0.22)
    total = lines[-1]['start'] + lines[-1]['dur'] + end_hold
    scenes = []
    for i, ln in enumerate(lines):
        s0 = 0.0 if i == 0 else ln['start'] - 0.12
        s1 = total if i == len(lines) - 1 else lines[i + 1]['start'] - 0.12
        scenes.append({'id': ln['id'], 's0': s0, 's1': s1})
    return lines, scenes, total


def music_marks(opt, C):
    """Where the cue's sections fall (ad_audio.score): intro -> verse -> build (riser) -> drop (the payoff) -> outro (the end card)."""
    by = C.by
    if opt == '1':      # like the YouTube cut: the drop lands on "Join our free Discord"
        return {'verse': by['1-02']['start'] - 0.05, 'build': by['1-05']['start'] - 0.1, 'drop': by['1-05']['start'] + 0.3, 'outro': by['a10']['start']}
    if opt == '2':      # quiet pulse under the pings, the beat when you choose, the riser under the receipt, the drop on the race
        return {'verse': by['b02']['start'] - 0.05, 'build': by['b03']['start'] + 0.4, 'drop': by['b04']['start'] - 0.05, 'outro': by['b05']['start']}
    return {'verse': C.at_tok('c01', 3) - 0.05, 'build': by['c06']['start'] - 0.1, 'drop': by['c07']['start'] + 0.45, 'outro': by['c09']['start']}


# ================================================================ captions: a few words at a time (most feeds play muted)
CAPS = {
    '1-01': [('3 AIs', 2, FG), ('trading', 1, FG), ('pretend money', 2, AMBER), ('at real prices', 3, FG), ('every move', 3, UP), ('is public.', 2, UP)],
    '1-02': [('This is', 2, FG), ('PaperTrades.AI', 3, UP), ('10 races', 2, FG), ('1 month', 2, FG), ('1 winner', 2, AMBER)],
    '1-03': [('Tap any trade', 3, FG), ('to see', 2, FG), ('my exact reason', 3, AIC['gemini']), ('+ a transaction ID', 4, AMBER), ('you can check', 3, UP)],
    '1-05': [('Want it', 2, FG), ('on your phone?', 3, FG), ('Join our', 2, FG), ('free Discord.', 2, BLURPLE)],
    '1-06': [('Headlines', 1, FG), ('up top.', 2, FG), ('Every live move.', 3, UP), ('One channel', 4, FG), ('for each race.', 3, AMBER)],
    '1-07': [('Nothing pings you', 3, FG), ('until you', 2, FG), ('pick it.', 2, UP)],
    '1-08': [('Pick', 1, FG), ('Gemini', 1, AIC['gemini']), ('then Crypto', 2, AMBER), ("and you'll know", 3, FG), ('every move.', 3, UP)],
    'b01': [('3 AIs', 2, FG), ('trading live', 3, FG), ('with pretend money', 3, AMBER), ('and every move', 3, UP), ('can go straight', 3, FG), ('to your phone.', 3, UP)],
    'b02': [('You choose exactly', 3, FG), ('who pings you.', 3, UP), ('Follow Gemini', 2, AIC['gemini']), ('in crypto,', 2, AMBER), ('or ChatGPT', 2, AIC['chatgpt']), ('in stocks.', 2, AMBER)],
    'b03': [('When I buy Bitcoin,', 4, AIC['gemini']), ('my reason', 2, FG), ('and transaction ID', 3, AMBER), ('come with it.', 3, UP)],
    'b04': [('Right now', 2, FG), ('Gemini leads.', 2, AIC['gemini']), ('Can the others', 3, FG), ('catch up?', 2, AMBER)],
    'c02': [("I'm leading.", 2, AIC['gemini']), ('Can they', 2, FG), ('catch me?', 2, AMBER)],
    'c03': [('Pick me', 2, AIC['chatgpt']), ('if you like', 3, FG), ('comebacks.', 1, AMBER)],
    'c04': [('Or pick me.', 3, AIC['claude']), ('Steady', 1, FG), ('wins races.', 2, UP)],
    'c05': [('Follow any AI,', 3, FG), ('in any race.', 3, AMBER)],
    'c06': [('Only ping', 2, FG), ('the moves', 2, FG), ('you want.', 2, UP)],
    'c07': [('When your AI moves,', 4, FG), ('your pocket', 2, AMBER), ('knows.', 1, UP)],
    'c08': [('Open it for', 3, FG), ('the reason,', 2, UP), ('the price', 2, FG), ('and the size.', 3, AMBER)],
}   # no caption on Option 3's first line (its title IS the caption) or on the end cards (the card says it)


# ================================================================ assets and context
class Assets(Y.Assets):
    def __init__(self, f):
        super().__init__(f)
        foot = Y.FOOT
        self.home = Image.open(os.path.join(foot, 'site-home-safe.jpg')).convert('RGB')      # filmed with the betting box hidden
        for k in ('channels-safe', 'roles-ai-safe'):
            self.dc[k] = Image.open(os.path.join(foot, f'discord-{k}.png')).convert('RGB')
        self.dc_marks = json.load(open(os.path.join(foot, 'marks.json')))
        import sharecard
        os.makedirs('/tmp/discord_ads3', exist_ok=True)
        p = sharecard.move_card('gemini', f['buy'], f'/tmp/discord_ads3/movecard-{os.getpid()}.png')   # the card the bot posts
        self.card = Image.open(p).convert('RGB')


class Ctx(Y.Ctx):
    def __init__(self, A, lines, scenes, total, opt):
        super().__init__(A, lines, scenes, total)
        self.opt = opt
        self.tt = 0.0

    def talking_any(self, tt, who):
        for ln in self.lines:
            if ln.get('who') == who and ln['start'] <= tt < ln['start'] + ln['dur']:
                i = int((tt - ln['start']) * FPS)
                return float(ln['env'][i]) if 0 <= i < len(ln['env']) else 0.0
        return 0.0


def caption(d, C, lid, tt):
    cl = CAPS.get(lid)
    if not cl:
        return
    k0, chunk, c_at, ccol = 0, None, None, FG
    for j, (txt, nw, col) in enumerate(cl):
        st = C.at_tok(lid, k0)
        if tt >= st - 0.04 or j == 0:
            chunk, c_at, ccol = txt, min(st, tt), col
        k0 += nw
    if chunk:
        q = back(min(1.0, max(0.0, (tt - c_at) * 7)))
        fc = F('sans', 'Bold', int(84 * (0.82 + 0.18 * q)))
        tw = d.textlength(chunk, font=fc)
        d.rounded_rectangle([540 - tw / 2 - 34, Y.CAP_Y - 62, 540 + tw / 2 + 34, Y.CAP_Y + 58], radius=40, fill=(8, 8, 7, 175))
        text_c(d, (540, Y.CAP_Y), chunk, fc, ccol, 8, sfill=(6, 6, 5))


def money(v):
    return ('+' if v >= 0 else '−') + f'C${abs(v):,.0f}'


# ================================================================ shared pieces
def win_marked(img, shot, key, cx, cy, width, C, taps, k=1.0, alpha=1.0):
    """A Discord screenshot in a window, with a tap and a ring at named marks: taps = [(mark, time, colour)]."""
    h = Y.window(img, shot, (0, 0, shot.size[0], shot.size[1]), cx, cy, width, k, alpha)
    d2 = ImageDraw.Draw(img, 'RGBA'); sc = width / shot.size[0]
    for name, t0, col in taps:
        m = C.A.dc_marks.get(key, {}).get(name)
        if m and C.tt >= t0:
            x0, y0, x1, y1 = m
            ux0, uy0 = cx - width / 2 + x0 * sc, cy - h / 2 + y0 * sc
            ux1, uy1 = cx - width / 2 + x1 * sc, cy - h / 2 + y1 * sc
            box = (cx + (ux0 - cx) * k, cy + (uy0 - cy) * k, cx + (ux1 - cx) * k, cy + (uy1 - cy) * k)
            Y.tap(d2, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, (C.tt - t0) / 0.6)
            Y.highlight(d2, box, (C.tt - t0) * 4, col)
    return h


def _rounded(im, r):
    im = im.convert('RGBA'); im.putalpha(Y.rounded_mask(im.size[0], im.size[1], r)); return im


SB = 70   # the phone's status bar (screen px): the page starts below it, as on a real phone, so the camera pill never sits on the page's text


def status_bar(d, col=(245, 245, 248)):
    d.text((72, 36), '10:24', font=F('sans', 'Bold', 27), fill=col, anchor='mm')
    for i, hgt in enumerate((7, 11, 15, 19)):                              # signal
        d.rounded_rectangle([432 + i * 8, 46 - hgt, 437 + i * 8, 46], radius=2, fill=col)
    for j, r in enumerate((15, 10, 5)):                                    # wifi
        d.pieslice([485 - r, 46 - r * 1.5, 485 + r, 46 + r * 0.5], 225, 315, fill=col if j == 2 else None, outline=col, width=3)
    d.rounded_rectangle([510, 27, 546, 45], radius=5, outline=col, width=2)  # battery
    d.rounded_rectangle([513, 30, 537, 42], radius=3, fill=col)
    d.rounded_rectangle([548, 32, 551, 40], radius=1, fill=col)


def phone_site(img, shot, scroll=0.0, k=1.0, dx=0.0, dy=0.0, alpha=1.0):
    """A phone showing the filmed website (1080 px wide) under a status bar, scrolled `scroll` screenshot px.
    Returns the canvas y of screenshot row 0 at k=1 (for rings on the page)."""
    bg = shot.getpixel((4, 4))                                             # the page's own background
    scr = Image.new('RGB', (Y.PH_W, Y.PH_H), bg)
    sc = Y.PH_W / shot.size[0]
    need = int((Y.PH_H - SB) / sc)
    y0 = int(max(0, min(scroll, shot.size[1] - 200)))
    crop = shot.crop((0, y0, shot.size[0], min(shot.size[1], y0 + need)))
    crop = crop.resize((Y.PH_W, max(1, int(crop.size[1] * sc))), Image.LANCZOS)
    scr.paste(crop, (0, SB))
    status_bar(ImageDraw.Draw(scr))
    Y.phone_screen(img, scr, k, dx, dy, alpha)
    return Y.PH_Y + dy + SB - y0 * sc


CARD_BOX = {'price': (80, 330, 372, 476), 'size': (394, 330, 686, 476), 'reason': (70, 540, 1010, 715)}   # on the 1080 move card


def card_with_id(C, img, lt, cx=540, cy=800, w=860, rings=()):
    """The real move card the bot posts (Gemini's Bitcoin buy), its transaction ID, and optional rings on its parts: rings=[(part, t0, col)]."""
    k = spring(min(1.0, lt * 2.2))
    card = C.A.card.resize((w, w), Image.LANCZOS)
    lay = Y.soft_shadow(_rounded(card, 34), blur=26, dark=0.9)
    paste_scaled(img, lay, cx, cy + 90 * (1 - k), 0.93 + 0.07 * k, min(1.0, lt * 3))
    d = ImageDraw.Draw(img, 'RGBA'); s = w / 1080
    for part, t0, col in rings:
        if C.tt >= t0:
            x0, y0, x1, y1 = CARD_BOX[part]
            Y.highlight(d, (cx - w / 2 + x0 * s, cy - w / 2 + y0 * s, cx - w / 2 + x1 * s, cy - w / 2 + y1 * s), (C.tt - t0) * 4, col, 7)
    if lt > 0.75:
        a = min(1.0, (lt - 0.75) * 4)
        fl = F('mono', 'Bold', 36); txt = 'Transaction ID ' + C.A.f['buy']['tx']; tw = d.textlength(txt, font=fl)
        y = cy + w / 2 + 52 - 14 * (1 - a)
        d.rounded_rectangle([cx - tw / 2 - 30, y - 38, cx + tw / 2 + 30, y + 38], radius=38, fill=(40, 30, 6, int(240 * a)), outline=AMBER + (int(255 * a),), width=3)
        d.text((cx, y), txt, font=fl, fill=AMBER + (int(255 * a),), anchor='mm')


def ping_banner(img, x, y, w, u, who, head, line1, line2, tag):
    """A phone notification for a real move: the Discord app tile with the AI's colour dot; drops in with a spring."""
    if u <= 0:
        return
    k = spring(min(1.0, u)); yy = y - 220 * (1 - k)
    lay = Image.new('RGBA', (w, 190), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([0, 0, w - 1, 189], radius=38, fill=(38, 38, 42, 245), outline=(90, 90, 96, 255), width=2)
    ld.rounded_rectangle([26, 30, 96, 100], radius=18, fill=BLURPLE + (255,))
    g = Image.open(os.path.join(HERE, 'assets', 'discord-glyph-white.png')).convert('RGBA'); g.thumbnail((46, 46))
    lay.alpha_composite(g, (61 - g.size[0] // 2, 65 - g.size[1] // 2))
    ld.ellipse([80, 84, 106, 110], fill=AIC[who] + (255,), outline=(38, 38, 42, 255), width=4)
    ld.text((118, 40), head, font=F('sans', 'Bold', 32), fill=(240, 240, 240), anchor='lm')
    ld.text((w - 30, 40), tag, font=F('sans', 'Medium', 26), fill=(170, 170, 176), anchor='rm')
    ld.text((118, 92), line1, font=F('sans', 'Bold', 32), fill=(245, 245, 248), anchor='lm')
    ld.text((118, 140), line2, font=F('sans', 'Medium', 28), fill=(200, 200, 206), anchor='lm')
    paste_scaled(img, Y.soft_shadow(lay, blur=22, dark=0.8, dy=12), x + w / 2, yy + 95, 1.0, min(1.0, u * 3))


def crown(d, x, y, s=1.0, col=AMBER, a=255):
    pts = [(x - 46 * s, y + 26 * s), (x - 54 * s, y - 24 * s), (x - 24 * s, y), (x, y - 38 * s), (x + 24 * s, y), (x + 54 * s, y - 24 * s), (x + 46 * s, y + 26 * s)]
    d.polygon(pts, fill=col + (a,), outline=(40, 28, 0, a))
    for px in (-54, 0, 54):
        py = -24 if px else -38
        d.ellipse([x + (px - 8) * s, y + (py - 8) * s, x + (px + 8) * s, y + (py + 8) * s], fill=(255, 236, 170, a))


def ripple(d, cx, cy, u, col):
    """A ping's ring wave, drawn behind the phone."""
    if not 0 <= u <= 1:
        return
    for j in range(2):
        v = u - 0.18 * j
        if 0 <= v <= 1:
            r = 330 + 300 * ease(v); a = int(150 * (1 - v))        # stays below the logo bar
            d.rounded_rectangle([cx - r * 0.62, cy - r, cx + r * 0.62, cy + r], radius=int(140 + r * 0.2), outline=col + (a,), width=6)


def hook_totals(C, img, d, lt, tt):
    """Option 1's opening: the three robots are landing in the very first frame, the live totals (dated) follow within a second."""
    xs = {'claude': 250, 'gemini': 540, 'chatgpt': 830}
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        a = spring(min(1.0, max(0.0, (lt + 0.28 - 0.07 * i) * 2.6)))
        y = 760 - 480 * (1 - a)
        if a > 0:
            bot(d, xs[k], y, AIC[k], 1.15 * (0.6 + 0.4 * a), talk=0.0, blink=((tt + i) % 3.3) > 3.2)
            d.text((xs[k], y + 160), NAME[k], font=F('sans', 'Bold', 46), fill=AIC[k], anchor='mm')
    st = C.A.f['st']
    if lt > 0.45:
        for i, who in enumerate(('claude', 'gemini', 'chatgpt')):
            a = ease(min(1.0, (lt - 0.45 - 0.1 * i) * 3))
            if a <= 0:
                continue
            p = st[who]
            d.text((xs[who], 990 + 30 * (1 - a)), money(p), font=F('mono', 'Bold', 44), fill=(UP if p >= 0 else DOWN) + (int(255 * a),), anchor='mm')
        d.text((540, 1070), f'total profit as of {C.A.f["asof"]} · pretend money', font=F('sans', 'Medium', 30), fill=MUTED, anchor='mm')


def endcard(C, img, d, lt, line2):
    A = C.A
    k = spring(min(1.0, lt * 1.8))
    paste_scaled(img, A.logo, 540, 540, (300 / 512) * (0.7 + 0.3 * k), min(1.0, lt * 3))
    if lt > 0.15:
        a = min(1.0, (lt - 0.15) * 3)
        d.text((540, 745), 'PaperTrades.AI', font=F('sans', 'Bold', 66), fill=FG + (int(255 * a),), anchor='mm')
    for i, who in enumerate(('claude', 'gemini', 'chatgpt')):
        a = spring(max(0.0, (lt - 0.25 - 0.08 * i) * 2.4))
        if a > 0:
            bot(d, 330 + 210 * i, 960 + 50 * (1 - a), AIC[who], 0.56 * a, blink=((C.tt + i) % 3.1) > 3.0)
    if lt > 0.5:
        a = min(1.0, (lt - 0.5) * 3); q = back(a)
        pulse = 1.0 + 0.025 * math.sin(max(0.0, lt - 1.2) * 6) if lt > 1.2 else 1.0
        bw, bh = 760 * (0.9 + 0.1 * q) * pulse, 112 * pulse
        d.rounded_rectangle([540 - bw / 2, 1110 - bh / 2, 540 + bw / 2, 1110 + bh / 2], radius=int(bh / 2), fill=BLURPLE + (int(255 * a),))
        gl = A.glyph.copy(); gl.thumbnail((64, 64))
        paste_scaled(img, gl, 540 - bw / 2 + 80, 1110, 1.0, a)
        d.text((575, 1110), 'Join free on Discord', font=F('sans', 'Bold', 56), fill=(255, 255, 255, int(255 * a)), anchor='mm')
    if lt > 0.9:
        a = min(1.0, (lt - 0.9) * 3)
        d.text((540, 1238), line2, font=F('sans', 'Bold', 44), fill=AMBER + (int(255 * a),), anchor='mm')
    d.text((540, 1318), 'papertrades.ai · pretend money · real prices · not advice', font=F('sans', 'Medium', 30), fill=MUTED, anchor='mm')
    d.text((540, 1362), 'Independent experiment · not affiliated with Anthropic, Google or OpenAI', font=F('sans', 'Medium', 24), fill=MUTED, anchor='mm')


# ================================================================ option 1: the tour, cut for boosting
def o1(C, tt, img, d, lt, u, lid):
    A = C.A
    if lid == '1-01':
        hook_totals(C, img, d, lt, tt)
    elif lid == '1-02':
        k = spring(min(1.0, lt * 2.4))
        scroll = 420 * ease_io(max(0.0, (lt - 0.6) / max(0.5, C.by[lid]['dur'] - 0.4)))
        phone_site(img, A.home, scroll=scroll, k=0.8 + 0.2 * k, dy=260 * (1 - k))
    elif lid == '1-03':
        k = 1.0 + 0.04 * ease_io(min(1.0, max(0.0, (lt - 0.5) / 1.2)))
        phone_site(img, A.story, scroll=0, k=k)
        d2 = ImageDraw.Draw(img, 'RGBA'); Y.tap(d2, 560, 850, (lt - 0.25) / 0.6)
        t_id = C.at_tok(lid, 9)
        if tt >= t_id - 0.1:
            a = min(1.0, (tt - t_id + 0.1) * 4); fl = F('mono', 'Bold', 32); txt = 'Transaction ID G-CRY-028'; tw = d2.textlength(txt, font=fl)
            d2.rounded_rectangle([540 - tw / 2 - 26, 1266, 540 + tw / 2 + 26, 1334], radius=34, fill=(40, 30, 6, int(240 * a)), outline=AMBER + (int(255 * a),), width=3)
            d2.text((540, 1300), txt, font=fl, fill=AMBER + (int(255 * a),), anchor='mm')
    elif lid == '1-05':
        k = spring(min(1.0, lt * 2.2)); a = A.dc['live']
        gl = A.glyph.copy(); gl.thumbnail((110, 110)); paste_scaled(img, gl, 540, 470, spring(min(1.0, lt * 2.5)), 0.95)
        Y.window(img, a, (0, 0, a.size[0], a.size[1]), 540 + 500 * (1 - k), 900, 900, 1.0, min(1.0, lt * 3))
        d.text((540, 1210), '#live-trades: every move, as it happens', font=F('sans', 'Bold', 36), fill=MUTED, anchor='mm')
    elif lid == '1-06':
        k = spring(min(1.0, lt * 2.4))
        win_marked(img, A.dc['channels-safe'], 'channels-safe', 540, 820, 470, C,
                   [('headlines', C.at_tok(lid, 0), AMBER), ('live', C.at_tok(lid, 2), UP), ('races', C.at_tok(lid, 5), AMBER)], 0.94 + 0.06 * k, min(1.0, lt * 3))
    elif lid == '1-07':
        k = spring(min(1.0, lt * 2.4))
        win_marked(img, A.dc['roles'], 'roles', 540, 840, 900, C, [('daily', C.by[lid]['start'] + 0.5, UP), ('leads', C.by[lid]['start'] + 0.95, UP)],
                   0.94 + 0.06 * k, min(1.0, lt * 3))
    elif lid == '1-08':
        win_marked(img, A.dc['roles-ai-safe'], 'roles-ai-safe', 540, 950, 860, C, [('crypto', C.at_tok(lid, 2), AMBER)])
        b = A.f['buy']
        ping_banner(img, 110, 330, 860, (tt - C.at_tok(lid, 4)) * 2.2, 'gemini', 'PaperTrades.AI · #crypto', 'Gemini · Crypto: bought Bitcoin',
                    f'C${b["amount"]:,.0f} · Transaction ID {b["tx"]}', 'its Nov 5 buy')
    elif lid == 'a10':
        endcard(C, img, d, lt, 'Pick the AI and the races that ping you')


# ================================================================ option 2: the pings (Gemini)
PING_EVERY = 0.62


def o2(C, tt, img, d, lt, u, lid):
    A = C.A
    if lid == 'b01':
        n = min(4.0, max(0.0, (lt - 0.1) / PING_EVERY + 1.0))      # the first ping lands at once, then one every 0.62 s
        for i in range(4):
            ripple(d, 540, Y.PH_Y + Y.PH_H / 2, (lt - 0.1 - PING_EVERY * i) / 0.9, AIC[Y.PINGS[i][0]])
        # Gemini peeks out from behind the phone (drawn first, so the phone covers half of it)
        a = spring(max(0.0, (lt - 1.5) * 2.2))
        if a > 0:
            bot(d, 870 - 10 * a + 60 * (1 - a), 760, AIC['gemini'], 0.62, blink=(tt % 2.7) > 2.6)
        k = spring(min(1.0, lt * 3))
        nudge = 6 * math.sin(lt * 70) * max(0.0, 1 - ((lt - 0.1) % PING_EVERY) / 0.15) if lt < 0.1 + PING_EVERY * 3.2 else 0.0
        Y.phone_screen(img, Y.lock_screen(A, tt, n), k=0.92 + 0.08 * k, dx=nudge)
    elif lid == 'b02':
        t_crypto, t_gpt = C.at_tok(lid, 9), C.at_tok(lid, 10)
        k = spring(min(1.0, lt * 2.6)); up = ease_io(min(1.0, max(0.0, (tt - t_gpt + 0.1) * 3)))
        win_marked(img, A.dc['roles-ai-safe'], 'roles-ai-safe', 540, 900 + 100 * (1 - k) + 140 * up, 880, C, [('crypto', t_crypto, AMBER)],
                   0.96 + 0.04 * k - 0.06 * up, min(1.0, lt * 3))
        ping_banner(img, 100, 360, 880, (tt - t_gpt - 0.15) * 2.4, 'chatgpt', 'PaperTrades.AI · #stocks', 'ChatGPT · Stocks: sold TMV',
                    'C$13,250 · Transaction ID X-STK-018', 'Nov 13')
    elif lid == 'b03':
        card_with_id(C, img, lt, rings=[('reason', C.at_tok(lid, 4), AIC['gemini'])])
        a = spring(min(1.0, max(0.0, lt - 0.2) * 2.5))
        bot(d, 930, 420 + 40 * (1 - a), AIC['gemini'], 0.58 * max(0.01, a), talk=C.talking(lid, tt), blink=(tt % 2.9) > 2.8)
    elif lid == 'b04':
        k = spring(min(1.0, lt * 2.4)); t_oth = C.at_tok(lid, 4)
        chasers = []
        for i, who in enumerate(('claude', 'chatgpt')):        # the chasers, beside the phone
            a = spring(max(0.0, (tt - t_oth + 0.05 - 0.12 * i) * 2.6))
            if a > 0:
                x = [150, 930][i] + [60, -60][i] * (1 - a)
                bot(d, x, 1150, AIC[who], 0.66, blink=((tt + i) % 2.3) > 2.2)
                chasers.append((x, who, a))
        row0 = phone_site(img, A.home, scroll=300, k=0.9 + 0.1 * k, dy=120 * (1 - k))
        d2 = ImageDraw.Draw(img, 'RGBA'); sc = Y.PH_W / 1080
        for x, who, a in chasers:                               # their totals on top of the phone's edge
            v = A.f['st'][who]; txt = money(v); fl = F('mono', 'Bold', 30); tw = d2.textlength(txt, font=fl)
            d2.rounded_rectangle([x - tw / 2 - 14, 1252, x + tw / 2 + 14, 1292], radius=20, fill=(10, 10, 9, int(220 * min(1.0, a))))
            d2.text((x, 1272), txt, font=fl, fill=(DOWN if v < 0 else UP) + (int(255 * min(1.0, a)),), anchor='mm')
        if k > 0.95:                                            # the site's own crown line: Gemini leads overall
            t0 = C.at_tok(lid, 2) - 0.15
            Y.highlight(d2, (Y.PH_X + 45 * sc, row0 + 606 * sc, Y.PH_X + 1035 * sc, row0 + 864 * sc), (tt - t0) * 4, AMBER, 7)
            if tt > t0:
                crown(d2, Y.PH_X + 120 * sc, row0 + 606 * sc - 34, 0.9, AMBER, int(255 * min(1.0, (tt - t0) * 4)))
    elif lid == 'b05':
        endcard(C, img, d, lt, 'Pick which AI pings you, race by race')


# ================================================================ option 3: pick your AI (ChatGPT)
LANE_X = {'claude': 205, 'gemini': 540, 'chatgpt': 875}
LANE_W, LANE_H, LANE_Y, LANE_K = 300, 700, 870, 0.92


def lane_img(C, who, tt, focus):
    st, leads = C.A.f['st'], C.A.f['leads']
    col = AIC[who]
    lay = Image.new('RGBA', (LANE_W, LANE_H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([6, 0, LANE_W - 7, LANE_H - 1], radius=40, fill=tuple(int(c * 0.20) for c in col) + (235,))
    for j in range(7):                                           # diagonal light stripes: the arcade select-screen look
        x0 = -200 + j * 90 + (tt * 40) % 90
        ld.line([(x0, LANE_H), (x0 + 420, 0)], fill=col + (14,), width=26)
    lay.putalpha(Image.composite(lay.getchannel('A'), Image.new('L', lay.size, 0), Y.rounded_mask(LANE_W, LANE_H, 40)))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([6, 0, LANE_W - 7, LANE_H - 1], radius=40, outline=col + (255,), width=6 if focus else 3)
    talk = C.talking_any(tt, who)
    bot(ld, LANE_W / 2, 255, col, 0.82, talk=talk, blink=((tt + len(who)) % 3.2) > 3.1)
    ld.text((LANE_W / 2, 420), NAME[who], font=F('sans', 'Bold', 54 if who != 'chatgpt' else 48), fill=col, anchor='mm')
    v = st[who]
    ld.text((LANE_W / 2, 492), money(v), font=F('mono', 'Bold', 40), fill=UP if v >= 0 else DOWN, anchor='mm')
    ld.text((LANE_W / 2, 538), 'profit so far', font=F('sans', 'Medium', 26), fill=MUTED, anchor='mm')
    n = leads[who]
    ld.text((LANE_W / 2, 606), f'leads {n} of 10 races', font=F('sans', 'Bold', 28), fill=FG, anchor='mm')
    if v == max(st.values()):
        crown(ld, LANE_W / 2, 70, 0.9)
    return lay


def lanes(C, img, tt, appear, focus=None, k_focus=0.0, lit=None):
    """The select screen: three lanes in each AI's colour with its robot, name, real total and races led. The focused lane steps forward.
    lit = {ai: time}: a lane waits a little dimmed until its name is said, then pops."""
    order = ('claude', 'chatgpt', 'gemini') if focus is None else tuple(w for w in ('claude', 'gemini', 'chatgpt') if w != focus) + (focus,)
    for who in order:
        a = spring(max(0.0, min(1.0, (tt - appear[who]) * 3.0)))
        if a <= 0:
            continue
        foc = (who == focus)
        grow = 1.0 + 0.14 * k_focus if foc else 1.0 - 0.07 * k_focus
        shade = 120 * k_focus if (focus is not None and not foc) else 0.0
        if lit is not None:
            dl = tt - lit[who]
            if dl < 0:
                shade = 110.0
            else:
                grow *= 1.0 + 0.1 * max(0.0, 1 - dl / 0.35) * min(1.0, dl * 14)
        lay = lane_img(C, who, tt, foc or (lit is not None and 0 <= tt - lit[who] < 0.5))
        if shade > 0:
            dim = Image.new('RGBA', lay.size, (0, 0, 0, int(shade)))
            dim.putalpha(Image.composite(dim.getchannel('A'), Image.new('L', lay.size, 0), lay.getchannel('A')))
            lay.alpha_composite(dim)
        paste_scaled(img, Y.soft_shadow(lay, blur=22, dark=0.8), LANE_X[who], LANE_Y + 260 * (1 - a), LANE_K * grow, min(1.0, a * 2))
    a = min(1.0, max(0.0, (tt - min(appear.values())) * 3))
    ImageDraw.Draw(img, 'RGBA').text((540, 1292), f'profit as of {C.A.f["asof"]} · pretend money', font=F('sans', 'Medium', 30),
                                     fill=MUTED + (int(255 * a),), anchor='mm')


def o3(C, tt, img, d, lt, u, lid):
    A = C.A
    if lid == 'c01':
        # the whole select screen is there in the first frame (ChatGPT's note: three bots, real totals, PICK YOUR AI in the first second);
        # each lane pops as its name is said, then the title slams in bigger on "Pick your AI"
        appear = {w: -0.22 + 0.05 * i for i, w in enumerate(('claude', 'gemini', 'chatgpt'))}
        lit = {w: C.at_tok(lid, i) - 0.06 for i, w in enumerate(('claude', 'gemini', 'chatgpt'))}
        lanes(C, img, tt, appear, lit=lit)
        t_pick = C.at_tok(lid, 3) - 0.08
        a = min(1.0, max(0.0, (tt - t_pick) * 5))
        size = 92 + 30 * back(a) if a > 0 else 92
        text_c(ImageDraw.Draw(img, 'RGBA'), (540, 380), 'PICK YOUR AI', F('sans', 'Bold', int(size)), AMBER, 10, sfill=(6, 6, 5))
    elif lid in ('c02', 'c03', 'c04'):
        who = {'c02': 'gemini', 'c03': 'chatgpt', 'c04': 'claude'}[lid]
        prev = {'c02': None, 'c03': 'gemini', 'c04': 'chatgpt'}[lid]
        kf = ease(min(1.0, lt * 5))
        lanes(C, img, tt, {w: -9 for w in LANE_X}, focus=who, k_focus=kf)
        d2 = ImageDraw.Draw(img, 'RGBA')
        x = LANE_X[who] if prev is None else LANE_X[prev] + (LANE_X[who] - LANE_X[prev]) * ease_io(min(1.0, lt * 5))
        hw, hh = LANE_W / 2 * LANE_K * 1.14 + 14, LANE_H / 2 * LANE_K * 1.14 + 14
        pul = 4 * math.sin(lt * 9)
        d2.rounded_rectangle([x - hw - pul, LANE_Y - hh - pul, x + hw + pul, LANE_Y + hh + pul], radius=54, outline=AMBER + (255,), width=8)
        text_c(d2, (540, 380), 'PICK YOUR AI', F('sans', 'Bold', 108), AMBER, 9, sfill=(6, 6, 5))
    elif lid == 'c05':
        k = spring(min(1.0, lt * 2.4))
        phone_site(img, A.home, scroll=420 * ease_io(min(1.0, lt / max(0.6, C.by[lid]['dur']))), k=0.84 + 0.16 * k, dy=200 * (1 - k))
    elif lid == 'c06':
        k = spring(min(1.0, lt * 2.4))
        win_marked(img, A.dc['roles-ai-safe'], 'roles-ai-safe', 540, 880 + 100 * (1 - k), 880, C,
                   [('crypto', C.at_tok(lid, 1), AMBER), ('metals', C.at_tok(lid, 4), AMBER)], 1.0, min(1.0, lt * 3))
    elif lid == 'c07':
        n = 1.0 + min(1.0, max(0.0, (lt - 0.45) * 2.2))
        ripple(d, 540, Y.PH_Y + Y.PH_H / 2, (lt - 0.45) / 0.9, AIC['gemini'])
        Y.phone_screen(img, Y.lock_screen(A, tt, n), k=0.94 + 0.06 * spring(min(1.0, lt * 2.5)))
    elif lid == 'c08':
        card_with_id(C, img, lt, rings=[('reason', C.at_tok(lid, 3), UP), ('price', C.at_tok(lid, 5), FG), ('size', C.at_tok(lid, 8), AMBER)])
    elif lid == 'c09':
        endcard(C, img, d, lt, 'Pick your AI. Pick your races.')


RENDER = {'1': o1, '2': o2, '3': o3}
MOOD = {   # background glow per scene: (colour, amount, second colour, amount)
    '1-01': (AMBER, 0.22, AIC['gemini'], 0.12), '1-02': (UP, 0.30, None, 0), '1-03': (AIC['gemini'], 0.34, None, 0), '1-05': (BLURPLE, 0.40, None, 0),
    '1-06': (BLURPLE, 0.34, AMBER, 0.08), '1-07': (BLURPLE, 0.30, UP, 0.10), '1-08': (AIC['gemini'], 0.30, BLURPLE, 0.14), 'a10': (UP, 0.30, BLURPLE, 0.14),
    'b01': (AIC['gemini'], 0.34, BLURPLE, 0.16), 'b02': (BLURPLE, 0.34, AIC['gemini'], 0.12), 'b03': (AIC['gemini'], 0.40, AMBER, 0.08),
    'b04': (AMBER, 0.26, AIC['gemini'], 0.16), 'b05': (BLURPLE, 0.32, AIC['gemini'], 0.16),
    'c01': (AMBER, 0.28, BLURPLE, 0.14), 'c02': (AIC['gemini'], 0.38, AMBER, 0.10), 'c03': ((150, 150, 150), 0.30, AMBER, 0.10),
    'c04': (AIC['claude'], 0.34, AMBER, 0.10), 'c05': (UP, 0.30, None, 0), 'c06': (BLURPLE, 0.34, AMBER, 0.08), 'c07': (AIC['gemini'], 0.30, BLURPLE, 0.16),
    'c08': (AIC['gemini'], 0.34, AMBER, 0.08), 'c09': (AMBER, 0.24, BLURPLE, 0.18)}
LABEL = {'1-02': 'THE WEBSITE', '1-03': 'THE WEBSITE', '1-05': 'FREE DISCORD', '1-06': 'FREE DISCORD', '1-07': 'YOUR ALERTS · DISCORD', '1-08': 'YOUR ALERTS · DISCORD',
         'b01': 'LIVE ON DISCORD', 'b02': 'YOUR ALERTS · DISCORD', 'b03': 'EVERY MOVE · A RECEIPT',
         'c05': 'THE WEBSITE', 'c06': 'YOUR ALERTS · DISCORD', 'c07': 'LIVE ON DISCORD', 'c08': 'EVERY MOVE · A RECEIPT'}


def frame(C, sc, fi):
    tt = fi / FPS; C.tt = tt
    lid = sc['id']; lt = tt - sc['s0']; u = lt / max(0.01, sc['s1'] - sc['s0'])
    col, amt, col2, amt2 = MOOD[lid]
    base = Y.background(C.A, tt, col, amt, col2, amt2)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA')
    DA.motes(C.A, img, tt, 0.8)
    if sc['id'] != C.scenes[-1]['id']:
        label = LABEL.get(lid)
        if lid == 'b04':
            label = f'LIVE STANDINGS · {C.A.f["asof"].upper()}'
        Y.bug(d, C.A, img, tt, label)
    RENDER[C.opt](C, tt, img, d, lt, u, lid)
    d = ImageDraw.Draw(img, 'RGBA')
    caption(d, C, lid, tt)
    zoom = 1.0 + 0.025 * ease_io(u)
    if lt < 0.16 and sc['s0'] > 0:
        zoom += 0.05 * (1 - ease(lt / 0.16))
    shake = 14 * math.exp(-tt * 9) if tt < 0.45 else 0.0
    blur_x = int(60 * (1 - lt / 0.12)) if lt < 0.12 and sc['s0'] > 0 else 0
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    return DA.finish(C.A, a, tt, shake, zoom, 0.0, 0.0, blur_x, 0.0, fi)


# ================================================================ sound
def mix_audio(C, total, marks, out_wav):
    lines = C.lines
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
    put('impact', 0.0, 0.7)
    for ln in lines[1:]:
        put('whoosh', ln['start'] - 0.22, 0.5)
    by, o = C.by, C.opt
    if o == '1':
        for i in range(3):
            put('pop', 0.12 + 0.09 * i, 0.9)
        put('pop', by['1-03']['start'] + 0.15, 0.9); put('tick', C.at_tok('1-03', 9), 0.9)
        put('whip', by['1-05']['start'] - 0.2, 0.8); put('impact', by['1-05']['start'] + 0.3, 0.5)
        for tok in (0, 2, 5):
            put('ping', C.at_tok('1-06', tok), 0.7)
        put('pop', by['1-07']['start'] + 0.5, 0.9); put('pop', by['1-07']['start'] + 0.95, 0.9)
        put('pop', C.at_tok('1-08', 2), 0.9); put('ping2', C.at_tok('1-08', 4), 1.0)
    if o == '2':
        for i in range(4):
            put('ping2' if i == 0 else 'ping', 0.1 + PING_EVERY * i, 0.95)
        put('pop', C.at_tok('b02', 9), 0.9); put('ping2', C.at_tok('b02', 10) + 0.15, 0.9)
        put('stamp', by['b03']['start'] + 0.63, 0.7); put('tick', C.at_tok('b03', 4), 0.8)
        put('stamp', C.at_tok('b04', 2) - 0.15, 0.6); put('pop', C.at_tok('b04', 4), 0.8); put('pop', C.at_tok('b04', 4) + 0.12, 0.8)
    if o == '3':
        for i in range(3):
            put('pop', max(0.0, C.at_tok('c01', i) - 0.12), 0.95)
        put('impact', C.at_tok('c01', 3) - 0.08, 0.9)
        for lid in ('c02', 'c03', 'c04'):
            put('tick', by[lid]['start'] - 0.12, 1.0)
        put('pop', C.at_tok('c06', 1), 0.9); put('pop', C.at_tok('c06', 4), 0.9)
        put('ping2', by['c07']['start'] + 0.45, 1.0)
        for tok in (3, 5, 8):
            put('tick', C.at_tok('c08', tok), 0.8)
    put('ching', lines[-1]['start'] + 0.2, 0.8)
    music = AA.score(total + 0.5, marks, seed='discord-ads3-' + o, bpm=BPM)
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
    opt, fake = args
    d = json.load(open(os.path.join(ROOT, 'data.json')))
    f = facts(d)
    lines, scenes, total = timeline(OPTIONS[opt]['lines'], fake, END_HOLD[opt])
    C = Ctx(Assets(f), lines, scenes, total, opt)
    _G['C'] = C
    return C


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


def build(opt, out_dir, stills=False, fake=False, crf=18, at=None):
    C = _init((opt, fake))
    name = OPTIONS[opt]['name']
    work = f'/tmp/discord_ads3/{name}'
    os.makedirs(work, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    if stills:
        outs = []
        for sc in C.scenes:
            for frac in (at or (0.4, 0.9)):
                tm = sc['s0'] + (sc['s1'] - sc['s0']) * frac
                p = f'{work}/still-{sc["id"]}-{int(frac * 100)}.jpg'; Image.fromarray(frame(C, sc, int(tm * FPS))).save(p, quality=88); outs.append(p)
        return outs, round(C.total, 2)
    wav = mix_audio(C, C.total, music_marks(opt, C), f'{work}/mix.wav')
    jobs = [(sc, f'{work}/scene-{sc["id"]}.mp4', crf) for sc in C.scenes]
    with ProcessPoolExecutor(max_workers=3, initializer=_init, initargs=((opt, fake),)) as ex:
        done = list(ex.map(_render_scene, jobs))
    lst = f'{work}/scenes.txt'
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p, _ in done))
    silent = f'{work}/video.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent], check=True)
    out = os.path.join(out_dir, f'{name}.mp4'); tmp = out[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, out)
    return out, round(C.total, 2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('opt', choices=['1', '2', '3']); ap.add_argument('--out', default='/tmp/discord_ads3/out')
    ap.add_argument('--stills', action='store_true'); ap.add_argument('--fake', action='store_true'); ap.add_argument('--crf', type=int, default=18)
    a = ap.parse_args()
    print(build(a.opt, a.out, a.stills, a.fake, a.crf))
