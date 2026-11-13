"""New to Discord: why and how to turn on our alerts (owner, Nov 13: "make a video for new to discord and pin it advertise the pros of
using notifications on our discord channel work with all models"). Pinned in #new-to-discord; reusable as a Short.

Ideas: ops/review/discord-howto-nov13.json. All three agreed: open on a real alert lighting up a phone, show the three real setup steps
(Customize -> tick; Only @mentions; phone notifications on), warn against "All messages", end with Nov 28. Gemini and ChatGPT: the AIs speak.
The hook is the real lead change of Nov 11 (ChatGPT takes the lead in Currencies, passing Claude), read from data.json; the render stops if
it is gone. Engine and look: ops/discord_ad.py; music and sounds: ops/ad_audio.py; voice: ops/voice/discord-howto-v1.json.

  python3 ops/discord_howto.py [--stills] [--out DIR]
"""
import argparse
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
import discord_ad as DA  # noqa: E402
import ad_audio as AA  # noqa: E402
from discord_ad import (F, W, H, FPS, SR, FG, MUTED, UP, AMBER, AIC, NAME, BLURPLE, L, R, CAP_Y, INVITE,  # noqa: E402,F401
                        ease, back, spring, clamp, paste_scaled, bot, bot_sprite, text_c, wrap, glint)

NAME_ID = 'discord-howto-v1'
DC_BG, DC_PANEL, DC_LINE, DC_TEXT, DC_MUTED = (49, 51, 56), (43, 45, 49), (63, 65, 71), (242, 243, 245), (148, 155, 164)
RED = (237, 66, 69)
GAP_AFTER = {'01': 0.30, '02': 0.20, '03': 0.25, '04': 0.25, '05': 0.25, '06': 0.25, '07': 0.30}
TEMPO = {'01': 1.04, '02': 1.08, '03': 1.06, '04': 1.06, '05': 1.05, '06': 1.08, '07': 1.05, '08': 1.06}
END_HOLD = 2.6
BPM = 120
WHO = {}


class Fail(Exception):
    pass


def lead_moment(d):
    ms = [m for m in d.get('moments') or [] if m.get('who') == 'chatgpt' and m.get('race') == 'Currencies' and m.get('over') == 'claude' and m['at'].startswith('2026-11-11')]
    if not ms:
        raise Fail('the Nov 11 lead change (ChatGPT, Currencies) is not in the ledger')
    return ms[0]


class Assets:
    def __init__(self, d):
        import discord_leads
        root = os.path.dirname(HERE)
        m = lead_moment(d)
        txt = discord_leads.text(m)
        self.lead_title = 'ChatGPT takes the lead in Currencies'
        self.lead_body = [ln for ln in txt.split('\n') if ln.startswith('Passed')][0]
        if self.lead_title not in txt:
            raise Fail('lead-change text changed')
        self.logo = Image.open(os.path.join(root, 'brand', 'logo-circle-512.png')).convert('RGBA')
        self.glyph = Image.open(os.path.join(HERE, 'assets', 'discord-glyph-white.png')).convert('RGBA')
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.42) / (H * 0.62)) ** 2)
        self.vig = np.clip(1.08 - 0.55 * r ** 1.6, 0.35, 1.0)[..., None].astype(np.float32)
        self.base = np.array(DA.BG, np.float32)[None, None, :] * np.ones((H, W, 1), np.float32)
        self.glow = np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy - 820) / 720) ** 2))[..., None].astype(np.float32)
        rng = np.random.default_rng(5)
        self.grain = [rng.normal(0, 5.0, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
        self.motes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(10, 34), rng.uniform(6, 22), rng.uniform(0, 6.28), rng.uniform(0.05, 0.14)) for _ in range(22)]
        yy2, xx2 = np.mgrid[-32:32, -32:32].astype(np.float32)
        blob = np.clip(1 - np.sqrt(xx2 ** 2 + yy2 ** 2) / 32, 0, 1) ** 1.6
        spr = np.zeros((64, 64, 4), np.uint8); spr[..., :3] = 255; spr[..., 3] = (blob * 255).astype(np.uint8)
        self.sprite = Image.fromarray(spr, 'RGBA')
        # the latest real moves, for the #live-trades scroll (who, the move, the race)
        self.moves = []
        for t in sorted(d.get('rivals_trades', []) + d.get('trades', []), key=lambda t: t.get('at', ''), reverse=True)[:40]:
            who = t.get('model', 'claude'); a = t.get('action'); nm = str(t.get('name') or t.get('symbol') or '')
            if a in ('Buy', 'Sell', 'Short', 'Cover', 'Bet', 'Won', 'Lost') and nm:
                self.moves.append((who, f"{a} {nm[:34]}", t.get('experiment', '')))
            if len(self.moves) >= 9:
                break


class Ctx:
    def __init__(self, A, lines, scenes, total):
        self.A, self.lines, self.scenes, self.total = A, lines, scenes, total
        self.by = {ln['id']: ln for ln in lines}

    def at_tok(self, lid, k):
        ln = self.by[lid]; return ln['start'] + ln['tok'][max(0, min(k, len(ln['tok']) - 1))]

    def talking(self, lid, tt):
        ln = self.by[lid]; i = int((tt - ln['start']) * FPS)
        return float(ln['env'][i]) if 0 <= i < len(ln['env']) else 0.0


def timeline(script, vdir, words):
    lines, t = [], 0.12
    for ln in script['lines']:
        f_ = TEMPO.get(ln['id'], 1.0)
        src = DA.tempo_wav(f'{vdir}/{ln["id"]}.wav', f_, f'/tmp/discord_howto/vo/{ln["id"]}-{f_}.wav')
        x, cut = DA.trim(DA.read_wav(src)); dur = len(x) / SR
        wl = [[w_, a_ / f_, b_ / f_] for w_, a_, b_ in (words.get(ln['id']) or [])]
        tok = DA.token_times(ln['text'], wl, dur, cut)
        lines.append({**ln, 'x': x, 'start': t, 'dur': dur, 'tok': tok, 'env': DA.envelope(x)})
        t += dur + GAP_AFTER.get(ln['id'], 0.3)
    by = {ln['id']: ln for ln in lines}
    beat = 60 / BPM; verse = by['02']['start'] - 0.05
    want = verse + math.ceil((by['08']['start'] - verse) / beat - 1e-6) * beat   # the end card lands on the beat
    if want > by['08']['start']:
        by['08']['start'] = want
    total = by['08']['start'] + by['08']['dur'] + END_HOLD
    scenes = [{'id': ln['id'], 's0': 0.0 if i == 0 else ln['start'] - 0.12, 's1': total if i == len(lines) - 1 else lines[i + 1]['start'] - 0.12} for i, ln in enumerate(lines)]
    marks = {'verse': verse, 'build': by['07']['start'] - 0.1, 'drop': by['08']['start'], 'outro': by['08']['start'] + by['08']['dur'] + 0.2}
    return lines, scenes, total, marks


# ---------------------------------------------------------------- pieces of the screens
def phone(img, d, cx, cy, w_=600, h_=1060, lit=1.0):
    """A plain phone (no brand): rounded body, dark screen, a notch. Returns the screen box."""
    d.rounded_rectangle([cx - w_ / 2 - 14, cy - h_ / 2 - 14, cx + w_ / 2 + 14, cy + h_ / 2 + 14], radius=78, fill=(30, 30, 32, 255), outline=(90, 90, 96, 255), width=3)
    sc = (int(18 + 20 * lit), int(18 + 22 * lit), int(26 + 40 * lit))
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], radius=66, fill=sc + (255,))
    d.rounded_rectangle([cx - 70, cy - h_ / 2 + 18, cx + 70, cy - h_ / 2 + 52], radius=17, fill=(0, 0, 0, 255))
    return (cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2)


def banner(img, d, A, x0, y0, w_, title, body, sub, p=1.0):
    """A phone notification from our server (Discord's own icon left, our name, the channel, the text)."""
    yy = y0 - (1 - ease(p)) * 160
    a = int(255 * min(1, p * 2))
    d.rounded_rectangle([x0, yy, x0 + w_, yy + 190], radius=34, fill=(58, 58, 64, int(a * 0.96)))
    d.rounded_rectangle([x0 + 22, yy + 24, x0 + 86, yy + 88], radius=16, fill=BLURPLE + (a,))
    paste_scaled(img, A.glyph, x0 + 54, yy + 56, 0.075, a / 255)
    d.text((x0 + 104, yy + 26), sub, font=F('sans', 'Medium', 26), fill=(200, 200, 205, a))
    d.text((x0 + w_ - 26, yy + 26), 'now', font=F('sans', 'Medium', 24), fill=(170, 170, 175, a), anchor='ra')
    d.text((x0 + 104, yy + 62), title, font=F('sans', 'Bold', 32), fill=(255, 255, 255, a))
    d.text((x0 + 104, yy + 106), body, font=F('sans', 'Medium', 28), fill=(225, 225, 230, a))


def bell(d, cx, cy, k=1.0):
    """A notification bell, drawn (the font has no emoji)."""
    if k <= 0.05:
        return
    d.chord([cx - 62 * k, cy - 80 * k, cx + 62 * k, cy + 40 * k], 180, 360, fill=FG + (255,))
    d.polygon([(cx - 62 * k, cy - 20 * k), (cx + 62 * k, cy - 20 * k), (cx + 80 * k, cy + 44 * k), (cx - 80 * k, cy + 44 * k)], fill=FG + (255,))
    d.ellipse([cx - 16 * k, cy + 40 * k, cx + 16 * k, cy + 72 * k], fill=FG + (255,))
    d.ellipse([cx - 9 * k, cy - 98 * k, cx + 9 * k, cy - 80 * k], fill=FG + (255,))


def tap(d, x, y, u):
    """A finger tap: a ring that grows and fades."""
    if 0 <= u <= 1:
        r = 26 + 46 * ease(u); a = int(200 * (1 - u))
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, a), width=6)
        d.ellipse([x - 20, y - 20, x + 20, y + 20], fill=(255, 255, 255, int(150 * (1 - u))))


def check(d, x, y, on, k=1.0, col=BLURPLE):
    s = 46
    if on:
        q = back(k * 1.0) if k < 1 else 1.0
        d.rounded_rectangle([x, y, x + s, y + s], radius=10, fill=col + (255,))
        d.line([(x + 10, y + 24), (x + 20, y + 34), (x + 37, y + 13)], fill=(255, 255, 255, 255), width=int(6 * min(1.0, q)) + 1, joint='curve')
    else:
        d.rounded_rectangle([x, y, x + s, y + s], radius=10, outline=(120, 124, 132, 255), width=4)


def dc_window(d, title, y0=430, y1=1240, back_arrow=True):
    d.rounded_rectangle([L - 20, y0, R + 10, y1], radius=30, fill=DC_BG + (250,))
    d.rounded_rectangle([L - 20, y0, R + 10, y0 + 96], radius=30, fill=DC_PANEL + (255,))
    d.rectangle([L - 20, y0 + 60, R + 10, y0 + 96], fill=DC_PANEL + (255,))
    if back_arrow:
        d.text((L + 14, y0 + 48), '‹', font=F('sans', 'Bold', 64), fill=DC_TEXT, anchor='lm')
    d.text((540, y0 + 48), title, font=F('sans', 'Bold', 40), fill=DC_TEXT, anchor='mm')


# ---------------------------------------------------------------- the scenes
def s01(C, tt, img, d, lt):
    A = C.A
    scr = phone(img, d, 540, 860, 600, 1000, lit=0.4 + 0.6 * ease((lt - 0.05) * 6))
    d.text((540, scr[1] + 170), '9:14', font=F('sans', 'Medium', 130), fill=(235, 235, 240, 255), anchor='mm')
    d.text((540, scr[1] + 262), 'Wednesday, November 11', font=F('sans', 'Medium', 32), fill=(210, 210, 215, 255), anchor='mm')
    banner(img, d, A, scr[0] + 22, scr[1] + 340, scr[2] - scr[0] - 44, A.lead_title, A.lead_body, 'PaperTrades.AI · #lead-changes', p=(lt - 0.08) * 3.2)
    talk = C.talking('01', tt)
    paste_scaled(img, bot_sprite(AIC['chatgpt'], 0.8, talk=talk, blink=False), 870, 1060, 1.0)
    d.text((540, scr[3] + 60), 'a real alert from Nov 11', font=F('mono', 'Medium', 26), fill=MUTED, anchor='mm')


def s02(C, tt, img, d, lt):
    t_pick = C.at_tok('02', 8)
    # "Don't mute us": the mute button, struck out
    p = back(lt * 4)
    d.rounded_rectangle([540 - 300 * p, 520, 540 + 300 * p, 660], radius=70, fill=(60, 30, 32, 255), outline=RED + (255,), width=5)
    text_c(d, (540, 590), 'Mute server', F('sans', 'Bold', int(56 * p) + 1), DC_TEXT)
    t_x = C.at_tok('02', 4) - 0.05
    if tt > t_x:
        q = ease((tt - t_x) * 5)
        d.line([(250, 640 - 120 * q + 120 * (1 - q)), (250 + 580 * q, 540)], fill=RED + (255,), width=12)
    # "Nothing pings you until you pick it": a bell with 0
    if tt > C.at_tok('02', 5) - 0.1:
        q = back((tt - C.at_tok('02', 5) + 0.1) * 4)
        cx, cy = 540, 880
        d.ellipse([cx - 120 * q, cy - 120 * q, cx + 120 * q, cy + 120 * q], fill=(36, 38, 46, 255), outline=BLURPLE + (255,), width=6)
        bell(d, cx, cy + 6, 1.0 * q)
        d.ellipse([cx + 50 * q, cy - 110 * q, cx + 130 * q, cy - 30 * q], fill=(70, 70, 76, 255))
        text_c(d, (cx + 90 * q, cy - 70 * q), '0', F('sans', 'Bold', int(48 * q) + 1), FG)
    if tt > t_pick - 0.1:
        a = int(255 * clamp((tt - t_pick + 0.1) * 4))
        text_c(d, (540, 1080), 'until YOU pick it', F('sans', 'Bold', 64), AMBER + (a,), 5)
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        e = ease((lt - 0.2 - 0.1 * i) * 3)
        paste_scaled(img, bot_sprite(AIC[k], 0.55, blink=False), 330 + i * 210, 1235 + (1 - e) * 200, 1.0, e)


def s03(C, tt, img, d, lt):
    """Tap the server name -> Channels & Roles -> Customize."""
    t_name, t_cr, t_cu = C.at_tok('03', 2), C.at_tok('03', 6), C.at_tok('03', 9)
    # the server's channel list
    d.rounded_rectangle([L - 20, 430, R + 10, 1240], radius=30, fill=DC_BG + (250,))
    d.rounded_rectangle([L - 20, 430, R + 10, 540], radius=30, fill=DC_PANEL + (255,))
    paste_scaled(img, A_logo(C), L + 30, 485, 64 / 512)
    d.text((L + 74, 485), 'PaperTrades.AI', font=F('sans', 'Bold', 44), fill=DC_TEXT, anchor='lm'); cx_ = L + 74 + d.textlength('PaperTrades.AI', font=F('sans', 'Bold', 44)) + 26; d.line([(cx_ - 12, 478), (cx_, 492), (cx_ + 12, 478)], fill=DC_TEXT, width=5)
    for i, nm in enumerate(('new-to-discord', 'welcome-and-rules', 'daily-results', 'lead-changes', 'live-trades', 'crypto')):
        d.text((L + 20, 590 + i * 80), '#  ' + nm, font=F('sans', 'Medium', 40), fill=DC_MUTED, anchor='lm')
    tap(d, 330, 485, (tt - t_name) * 2.2)
    if tt > t_name + 0.15:   # the server menu slides up
        p = ease((tt - t_name - 0.15) * 3.5)
        y0 = 1240 - 700 * p
        d.rounded_rectangle([L - 20, y0, R + 10, 1240 + 30], radius=34, fill=(35, 36, 40, 252))
        items = ['Invite', 'Notifications', 'Channels & Roles', 'Settings', 'Mark As Read']
        for i, it in enumerate(items):
            yy = y0 + 70 + i * 100
            hl = it == 'Channels & Roles' and tt > t_cr - 0.1
            if hl:
                d.rounded_rectangle([L + 6, yy - 40, R - 16, yy + 40], radius=20, fill=BLURPLE + (255,))
            d.text((L + 40, yy), it, font=F('sans', 'Bold' if hl else 'Medium', 44), fill=(255, 255, 255) if hl else DC_TEXT, anchor='lm')
        tap(d, 540, y0 + 270, (tt - t_cr) * 2.2)
    if tt > t_cu - 0.25:   # the Channels & Roles page with its Customize tab
        p = ease((tt - t_cu + 0.25) * 4)
        xo = (1 - p) * 900
        d.rounded_rectangle([L - 20 + xo, 430, R + 10 + xo, 1240], radius=30, fill=DC_BG + (255,))
        d.text((540 + xo, 490), 'Channels & Roles', font=F('sans', 'Bold', 42), fill=DC_TEXT, anchor='mm')
        for i, (tab_, on) in enumerate((('Customize', True), ('Browse Channels', False))):
            x0 = L + 10 + i * 410 + xo
            d.rounded_rectangle([x0, 560, x0 + 390, 640], radius=40, fill=(BLURPLE if on else DC_PANEL) + (255,))
            d.text((x0 + 195, 600), tab_, font=F('sans', 'Bold', 38), fill=(255, 255, 255), anchor='mm')
        d.text((L + 10 + xo, 720), 'Which headlines should ping you?', font=F('sans', 'Bold', 40), fill=DC_TEXT, anchor='lm')
        tap(d, L + 330 + xo, 600, (tt - t_cu) * 2.2)


def A_logo(C):
    return C.A.logo


OPTS = [('📊', 'Daily results', 'The scoreboard after each daily close'), ('👑', 'Lead changes', 'When an AI takes the lead in a race'),
        ('💥', 'Big moments', 'Big wins and losses, new records'), ('📢', 'Season news', 'Important announcements only')]


def s04(C, tt, img, d, lt):
    dc_window(d, 'Channels & Roles')
    d.text((L + 10, 580), 'Which headlines should ping you?', font=F('sans', 'Bold', 42), fill=DC_TEXT, anchor='lm')
    ticks = [C.at_tok('04', 1), C.at_tok('04', 3), C.at_tok('04', 6), None]
    for i, (em, nm, desc) in enumerate(OPTS):
        yy = 650 + i * 140
        on = ticks[i] is not None and tt >= ticks[i]
        d.rounded_rectangle([L - 4, yy, R - 6, yy + 120], radius=22, fill=((52, 56, 92) if on else DC_PANEL) + (255,), outline=(BLURPLE if on else DC_LINE) + (255,), width=3)
        d.text((L + 26, yy + 40), nm, font=F('sans', 'Bold', 42), fill=DC_TEXT, anchor='lm')
        d.text((L + 26, yy + 90), desc, font=F('sans', 'Medium', 28), fill=DC_MUTED, anchor='lm')
        check(d, R - 76, yy + 37, on, (tt - ticks[i]) * 5 if on else 0)
        if ticks[i]:
            tap(d, R - 53, yy + 60, (tt - ticks[i]) * 2.4)


def s05(C, tt, img, d, lt):
    dc_window(d, 'Channels & Roles')
    d.ellipse([L + 10, 562, L + 46, 598], fill=AIC['gemini'] + (255,)); d.text((L + 60, 580), 'Gemini: which races should ping you?', font=F('sans', 'Bold', 40), fill=DC_TEXT, anchor='lm')
    t_c = C.at_tok('05', 4)
    races = [('', 'Stocks and anything'), ('', 'Crypto'), ('', 'China stocks'), ('', 'Metals')]
    for i, (em, nm) in enumerate(races):
        yy = 640 + i * 108
        on = nm == 'Crypto' and tt >= t_c
        d.rounded_rectangle([L - 4, yy, R - 6, yy + 92], radius=20, fill=((40, 56, 92) if on else DC_PANEL) + (255,), outline=(AIC['gemini'] if on else DC_LINE) + (255,), width=3)
        d.text((L + 26, yy + 46), nm, font=F('sans', 'Bold', 40), fill=DC_TEXT, anchor='lm')
        check(d, R - 76, yy + 23, on, (tt - t_c) * 5 if on else 0, AIC['gemini'])
        if nm == 'Crypto':
            tap(d, R - 53, yy + 46, (tt - t_c) * 2.4)
    paste_scaled(img, bot_sprite(AIC['gemini'], 0.62, talk=C.talking('05', tt), blink=False), 160, 1140, 1.0)
    if tt > C.at_tok('05', 9):
        a = int(255 * clamp((tt - C.at_tok('05', 9)) * 4))
        d.text((280, 1150), 'Gemini · Crypto: a ping only\nwhen Gemini moves in Crypto', font=F('sans', 'Bold', 34), fill=FG + (a,), anchor='lm')


def s06(C, tt, img, d, lt):
    """Only @mentions, then the phone's own switch."""
    t_om, t_ph = C.at_tok('06', 6), C.at_tok('06', 11)
    if tt < t_ph - 0.2:
        dc_window(d, 'Notifications')
        for i, (opt, desc) in enumerate((('All Messages', 'every message: too many'), ('Only @mentions', 'only the alerts you picked'), ('Nothing', 'silence'))):
            yy = 600 + i * 150
            on = opt == 'Only @mentions' and tt >= t_om
            d.rounded_rectangle([L - 4, yy, R - 6, yy + 126], radius=22, fill=((52, 56, 92) if on else DC_PANEL) + (255,), outline=(BLURPLE if on else DC_LINE) + (255,), width=3)
            d.text((L + 30, yy + 44), opt, font=F('sans', 'Bold', 44), fill=DC_TEXT, anchor='lm')
            d.text((L + 30, yy + 94), desc, font=F('sans', 'Medium', 28), fill=(RED if i == 0 else DC_MUTED), anchor='lm')
            cx, cy = R - 54, yy + 63
            d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], outline=(BLURPLE if on else (120, 124, 132)) + (255,), width=5)
            if on:
                d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=BLURPLE + (255,))
                tap(d, cx, cy, (tt - t_om) * 2.4)
        if tt > t_om:
            a = int(255 * clamp((tt - t_om) * 3))
            d.text((540, 1110), 'the sweet spot', font=F('sans', 'Bold', 44), fill=UP + (a,), anchor='mm')
    else:
        p = ease((tt - t_ph + 0.2) * 4)
        d.rounded_rectangle([L - 20, 430, R + 10, 1240], radius=30, fill=(28, 28, 30, 252))
        d.text((540, 500), 'Settings  ›  Notifications  ›  Discord', font=F('sans', 'Bold', 36), fill=(235, 235, 240), anchor='mm')
        rows = [('Allow Notifications', True), ('Lock Screen', True), ('Banners', True), ('Sounds', True)]
        for i, (nm, main) in enumerate(rows):
            yy = 600 + i * 130
            d.rounded_rectangle([L, yy, R - 10, yy + 104], radius=20, fill=(44, 44, 48, 255))
            d.text((L + 30, yy + 52), nm, font=F('sans', 'Bold' if i == 0 else 'Medium', 40), fill=(240, 240, 245), anchor='lm')
            sw_on = clamp((tt - t_ph - 0.15 - 0.08 * i) * 4) if True else 0
            x0, y0 = R - 150, yy + 26
            col = tuple(int(70 + (c - 70) * sw_on) for c in (52, 199, 89))
            d.rounded_rectangle([x0, y0, x0 + 110, y0 + 54], radius=27, fill=col + (255,))
            kx = x0 + 27 + 56 * ease(sw_on)
            d.ellipse([kx - 23, y0 + 4, kx + 23, y0 + 50], fill=(255, 255, 255, 255))
        tap(d, R - 70, 652, (tt - t_ph - 0.15) * 2.4)


def s07(C, tt, img, d, lt):
    A = C.A
    dc_window(d, '# live-trades', back_arrow=False)
    d.text((R - 20, 478), 'muted', font=F('sans', 'Medium', 30), fill=DC_MUTED, anchor='rm')
    off = (lt * 150) % 110
    for i, (who, mv, race) in enumerate(A.moves * 2):
        yy = 560 + i * 110 - off
        if yy < 540 or yy > 1010:
            continue
        d.ellipse([L + 6, yy, L + 66, yy + 60], fill=AIC.get(who, FG) + (255,))
        d.text((L + 86, yy + 2), NAME.get(who, who), font=F('sans', 'Bold', 32), fill=AIC.get(who, FG))
        d.text((L + 86, yy + 40), mv, font=F('sans', 'Medium', 30), fill=DC_TEXT)
    paste_scaled(img, bot_sprite(AIC['claude'], 0.62, talk=C.talking('07', tt), blink=False), 160, 1140, 1.0)
    d.rounded_rectangle([290, 1100, R, 1170], radius=35, fill=(30, 32, 40, 240), outline=MUTED + (255,), width=2)
    d.text((610, 1135), 'every move · no pings', font=F('sans', 'Bold', 36), fill=FG, anchor='mm')


def s08(C, tt, img, d, lt):
    A = C.A
    s = C.by['08']['start']; el = tt - s
    DA.rays(img, 540, 600, tt, BLURPLE, 0.10 * min(1, max(0, el) * 2), n=10, length=1300)
    d = ImageDraw.Draw(img, 'RGBA')
    paste_scaled(img, glint(A.logo, (el - 0.4) / 1.0, 0.14, 0.5), 540, 600, 0.62 * spring(max(0, el) * 1.6, 8, 5))
    rows = [('✓', 'No spam: nothing pings you until you pick it', UP), ('✓', 'Lead changes and big moments as they happen', UP),
            ('✓', 'One daily scoreboard, or just your AI', UP), ('!', 'We never DM you about money', AMBER)]
    for i, (ic, t_, col) in enumerate(rows):
        e = ease((el - 0.25 - 0.18 * i) * 3)
        if e <= 0:
            continue
        yy = 860 + i * 72
        d.text((L + 30 + (1 - e) * 200, yy), ic, font=F('sans', 'Bold', 40), fill=col + (int(255 * e),), anchor='lm')
        d.text((L + 90 + (1 - e) * 200, yy), t_, font=F('sans', 'Bold', 36), fill=FG + (int(255 * e),), anchor='lm')
    t_now = C.at_tok('08', 10) - 0.1
    if tt > t_now:
        q = back((tt - t_now) * 4)
        bw, bh = 700 * q, 116 * q
        d.rounded_rectangle([540 - bw / 2, 1210 - bh / 2, 540 + bw / 2, 1210 + bh / 2], radius=max(1, int(58 * q)), fill=BLURPLE + (255,))
        d.text((540, 1210), 'Pick your alerts now', font=F('sans', 'Bold', int(52 * q) + 1), fill=(255, 255, 255), anchor='mm')
    t_end = C.at_tok('08', 14) - 0.1
    if tt > t_end:
        a = int(255 * clamp((tt - t_end) * 3))
        d.text((540, 1310), 'Season 1 ends Nov 28 · pretend money · not advice', font=F('sans', 'Medium', 32), fill=MUTED + (a,), anchor='mm')
        d.text((540, 1362), 'Channels & Roles  ›  Customize', font=F('mono', 'Bold', 34), fill=AMBER + (a,), anchor='mm')
    for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
        p = ease((el - 0.3 - 0.1 * i) * 3)
        hop = 18 * max(0, math.sin((el - 0.8) * 6 - i)) if el > 0.8 else 0
        bot(d, 300 + i * 240, 1700 + (1 - p) * 320 - hop, AIC[k], 0.8, mood='cheer' if hop > 8 else 'smile')


SCENES = {'01': s01, '02': s02, '03': s03, '04': s04, '05': s05, '06': s06, '07': s07, '08': s08}
MOOD = {'01': (AIC['chatgpt'], 0.16, BLURPLE, 0.14), '02': (RED, 0.16, BLURPLE, 0.14), '03': (BLURPLE, 0.30, None, 0), '04': (BLURPLE, 0.30, AMBER, 0.08),
        '05': (AIC['gemini'], 0.32, None, 0), '06': (BLURPLE, 0.28, UP, 0.08), '07': (AIC['claude'], 0.28, None, 0), '08': (BLURPLE, 0.38, UP, 0.12)}


def karaoke(d, C, lid, tt):
    """The spoken line at the bottom, words lighting up as they are said (the AIs' lines in their colour)."""
    ln = C.by[lid]
    if lid == '08' or tt < ln['start'] - 0.05 or tt > ln['start'] + ln['dur'] + 0.5:   # the end card shows the words itself
        return
    who = ln['who']; col = AIC.get(who, FG) if who != 'narrator' else FG
    ws = ln['text'].replace('at-mentions', '@mentions').replace('Channels and Roles', 'Channels & Roles').replace('November twenty-eighth', 'Nov 28').split()
    n = len(ln['tok'])
    heard = sum(1 for k in range(n) if tt >= C.at_tok(lid, k))
    lit = min(len(ws), int(round(heard * len(ws) / max(1, n))))
    fq = F('sans', 'Bold', 58)
    rows = wrap(d, ' '.join(ws), fq, R - L + 20)
    if len(rows) > 3:
        fq = F('sans', 'Bold', 50); rows = wrap(d, ' '.join(ws), fq, R - L + 20)
    yy = CAP_Y - (len(rows) - 1) * 34; k = 0
    for row in rows:
        x = 540 - d.textlength(row, font=fq) / 2
        for w_ in row.split():
            on = k < lit
            d.text((x, yy), w_, font=fq, fill=(col if on else (120, 114, 100)), anchor='lm', stroke_width=6, stroke_fill=(6, 6, 5))
            x += d.textlength(w_ + ' ', font=fq); k += 1
        yy += 68


def frame(C, sc, fi):
    tt = fi / FPS; lid = sc['id']; lt = tt - sc['s0']; u = lt / max(0.01, sc['s1'] - sc['s0'])
    col, amt, col2, amt2 = MOOD[lid]
    base = DA.background(C.A, tt, col, amt, col2, amt2)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA')
    DA.floor(d, tt, tuple(int(c) for c in col))
    DA.motes(C.A, img, tt, 0.9)
    DA.bug(d, C.A, img, tt, 'New to Discord? 30 seconds to set up your alerts')
    SCENES[lid](C, tt, img, d, lt)
    d = ImageDraw.Draw(img, 'RGBA')
    karaoke(d, C, lid, tt)
    zoom = 1.0 + 0.03 * DA.ease_io(u)
    if lt < 0.16 and lid != '01':
        zoom += 0.05 * (1 - ease(lt / 0.16))
    shake = aberr = flash = 0.0
    for h_, k in ((0.1, 1.0), (C.by['08']['start'], 0.8)):
        e = tt - h_
        if 0 <= e < 0.45:
            shake = max(shake, 16 * k * math.exp(-e * 9)); aberr = max(aberr, 7 * k * math.exp(-e * 12))
    blur_x = int(60 * (1 - lt / 0.12)) if lid in ('03', '06', '08') and lt < 0.12 else 0
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    return DA.finish(C.A, a, tt, shake, zoom, 0.0, aberr, blur_x, flash, fi)


def mix(C, total, marks, out):
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    for ln in C.lines:
        s = int(ln['start'] * SR); voice[s:s + len(ln['x'])] += ln['x'][:max(0, n - s)] * 0.95
    fx = np.zeros(n, np.float32)

    def put(name, at, vol=1.0):
        y = AA.sfx(name) * vol; s = int(at * SR)
        if s < 0:
            y = y[-s:]; s = 0
        fx[s:s + len(y)] += y[:max(0, n - s)]
    put('buzz', 0.05, 0.9); put('ping', 0.12, 1.0); put('impact', 0.1, 0.5)
    put('stamp', C.at_tok('02', 4), 0.7)
    for k in (2, 6, 9):
        put('pop', C.at_tok('03', k), 0.8)
    for k in (1, 3, 6):
        put('pop', C.at_tok('04', k), 0.9); put('tick', C.at_tok('04', k) + 0.02, 0.8)
    put('pop', C.at_tok('05', 4), 0.9); put('ping2', C.at_tok('05', 9), 0.6)
    put('pop', C.at_tok('06', 6), 0.9); put('ching', C.at_tok('06', 11) + 0.2, 0.7)
    for lid in ('03', '06', '08'):
        put('whoosh', C.by[lid]['start'] - 0.3, 0.6)
    put('impact', C.by['08']['start'], 0.7)
    music = AA.score(total + 0.5, marks, seed='discord-howto', bpm=BPM)
    m = np.zeros((n, 2), np.float32); m[:min(n, len(music))] = music[:n]
    env = np.convolve(np.abs(voice), np.ones(int(0.2 * SR)) / (0.2 * SR), 'same')
    duck = np.convolve(np.clip(1 - env * 9.0, 0.25, 1.0), np.ones(int(0.08 * SR)) / (0.08 * SR), 'same')
    st = m * (0.48 * duck)[:, None] + voice[:, None] + (fx * 0.75)[:, None]
    st = st[:int(total * SR)]; st /= max(1.0, np.abs(st).max() / 0.97)
    AA.write_wav(out, st)


_G = {}


def _init(_=None):
    d = json.load(open('data.json'))
    script = json.load(open(f'ops/voice/{NAME_ID}.json'))
    vdir = f'social/voice/{NAME_ID}/gemini'
    words = json.load(open(f'{vdir}/words.json')) if os.path.exists(f'{vdir}/words.json') else {}
    lines, scenes, total, marks = timeline(script, vdir, words)
    _G['C'] = Ctx(Assets(d), lines, scenes, total)
    return lines, scenes, total, marks


def _render(job):
    sc, path = job; C = _G['C']
    f0, f1 = int(round(sc['s0'] * FPS)), int(round(sc['s1'] * FPS)); tmp = path[:-4] + '.part.mp4'
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        ff.stdin.write(frame(C, sc, fi).tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise Fail('ffmpeg failed: ' + sc['id'])
    os.replace(tmp, path); return path


def build(out_dir='/tmp/discord_howto/out', stills=False):
    lines, scenes, total, marks = _init()
    C = _G['C']; work = '/tmp/discord_howto'; os.makedirs(work, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    if stills:
        ts = [0.5, C.at_tok('02', 8) + 0.3, C.at_tok('03', 6) + 0.3, C.at_tok('03', 9) + 0.4, C.at_tok('04', 6) + 0.4, C.at_tok('05', 9) + 0.3,
              C.at_tok('06', 6) + 0.4, C.at_tok('06', 11) + 0.6, C.by['07']['start'] + 1.0, total - 0.4]
        out = []
        for i, t in enumerate(ts):
            sc = next(s for s in scenes if s['s0'] <= t < s['s1'] or s is scenes[-1])
            p = f'{work}/still-{i:02d}.jpg'; Image.fromarray(frame(C, sc, int(t * FPS))).save(p, quality=90); out.append(p)
        return out, round(total, 2)
    mix(C, total, marks, f'{work}/mix.wav')
    with ProcessPoolExecutor(max_workers=2, initializer=_init) as ex:
        done = list(ex.map(_render, [(sc, f'{work}/scene-{sc["id"]}.mp4') for sc in scenes]))
    open(f'{work}/scenes.txt', 'w').write(''.join(f"file '{p}'\n" for p in done))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{work}/scenes.txt', '-c', 'copy', f'{work}/video.mp4'], check=True)
    out = f'{out_dir}/{NAME_ID}.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{work}/video.mp4', '-i', f'{work}/mix.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out + '.part.mp4'], check=True)
    os.replace(out + '.part.mp4', out)
    return out, round(total, 2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--stills', action='store_true'); ap.add_argument('--out', default='/tmp/discord_howto/out')
    a = ap.parse_args(); print(build(a.out, a.stills))
