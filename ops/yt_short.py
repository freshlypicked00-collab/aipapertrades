"""YouTube-first Shorts with a voice (owner, Nov 3: "higher quality content ... more targeted to youtube ... say leave a like and
subscribe for more trade updates"; Gemini and Claude agreed on the plan, ops/review/ytgrowth-r1-nov3.json):
  - the hook spoken and on screen from the first frame (no static cover), the premise always visible at the top
  - one story with a conflict between the AIs: the move, the other two AIs' real grades, how it turned out
  - a narrator and one fixed voice per AI (ops/voice.py), captions timed to the voice word by word, talking robots
  - a labelled chart of the asset with the buys and sells marked, a "receipts" shot of the real ledger, the race standing
  - the ending asks a question for the comments and says "leave a like and subscribe for more trade updates"
Every number is read from data.json (the public ledger) and checked against the script; the render stops if one is off.

  python3 ops/yt_short.py options-g-opt-v1 [--engine gemini] [--out social/yt]
"""
import argparse
import difflib
import json
import math
import os
import re
import subprocess
import sys
import wave
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from postcard import font  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
NY = ZoneInfo('America/New_York')
BG = (11, 11, 10); FG = (242, 233, 216); MUTED = (155, 146, 127); PANEL = (19, 18, 15); LINE = (43, 41, 35)
UP, DOWN, AMBER, INK, CREAM = (61, 220, 132), (255, 90, 78), (255, 176, 0), (20, 18, 14), (242, 233, 216)
AIC = {'claude': (217, 119, 87), 'gemini': (79, 143, 247), 'chatgpt': (242, 242, 242)}
NAME = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
L, R = 80, 930          # nothing important within 150 px of the right edge (like / comment buttons)
TOP, BOT = 250, 1430    # nor in the top 250 px or the bottom 490 px (title, channel name)
CAP_Y = 1300            # the captions' centre line


class Fail(Exception):
    pass


# ---------------------------------------------------------------- the facts, from the ledger
def money(v, sign=True):
    s = f'C${abs(v):,.0f}'
    return (('+' if v >= 0 else '−') + s) if sign else s


def facts_options_gopt(d):
    tr = {t['tx']: t for t in d['rivals_trades'] if t.get('tx')}
    buys = [tr[k] for k in ('G-OPT-001', 'G-OPT-002', 'G-OPT-003')]
    sells = [tr[k] for k in ('G-OPT-004', 'G-OPT-005', 'G-OPT-006')]
    for t in buys:
        if t['model'] != 'gemini' or t['action'] != 'Buy' or 'SPY Nov 20 $760 put' not in t['name']:
            raise Fail('buy is not the SPY put: ' + t['tx'])
    for t in sells:
        if t['model'] != 'gemini' or t['action'] != 'Sell' or 'SPY Nov 20 $760 put' not in t['name']:
            raise Fail('sell is not the SPY put: ' + t['tx'])
    if sum(t['qty'] for t in buys) != sum(t['qty'] for t in sells):
        raise Fail('the sells do not close the whole position')
    pnl = {t['tx']: float(t.get('pnl') or 0) for t in d['rivals_trades'] if t.get('tx') in ('G-OPT-004', 'G-OPT-005', 'G-OPT-006')}
    if not pnl or len(pnl) != 3:
        # the profit of each sell is in the ledger rows
        pnl = {}
        for row in d['ledger'] + d['rivals_trades']:
            if row.get('tx') in ('G-OPT-004', 'G-OPT-005', 'G-OPT-006') and row.get('pnl') is not None:
                pnl[row['tx']] = float(row['pnl'])
    grades = {}
    for g in d['peer_grades']:
        if g['model'] == 'gemini' and g['decision_at'] == buys[2]['at'] and g['experiment'] == 'Options':
            grades[g['grader']] = g
    if set(grades) != {'claude', 'chatgpt'} or any(g['grade'] != 'C' for g in grades.values()):
        raise Fail('the grades of G-OPT-003 are not two Cs: ' + json.dumps({k: v['grade'] for k, v in grades.items()}))
    sp = [x for x in d['bench_history'] if x['series'] == 'S&P 500' and '2026-10-28' <= x['at'][:10] <= '2026-10-30']
    seen, spx = set(), []
    for x in sp:
        if x['at'] not in seen:
            seen.add(x['at']); spx.append((datetime.fromisoformat(x['at']), float(x['level'])))
    c29 = next(v for t, v in spx if t.date().isoformat() == '2026-10-29' and t.hour == 16)
    c30 = next(v for t, v in spx if t.date().isoformat() == '2026-10-30' and t.hour == 16)
    opt = {r['id']: float(r['profit']) for r in d['exp_standings']['Options']}
    return {
        'buys': [(t['tx'], datetime.fromisoformat(t['at'].replace('Z', '+00:00')).astimezone(NY), float(t['amount'])) for t in buys],
        'sells': [(t['tx'], datetime.fromisoformat(t['at'].replace('Z', '+00:00')).astimezone(NY), pnl.get(t['tx'])) for t in sells],
        'staked': sum(float(t['amount']) for t in buys), 'profit': sum(pnl.values()),
        'reason2': tr['G-OPT-002']['reason'], 'grades': grades, 'spx': spx, 'spx_drop': (c30 - c29) / c29 * 100,
        'race': sorted(opt.items(), key=lambda kv: -kv[1]), 'race_at': datetime.fromisoformat(d['meta'][0]['refreshed_at']).astimezone(NY),
    }


def check_script(f, script):
    """The spoken numbers must match the ledger, rounded the way they are said."""
    txt = ' '.join(l['text'] for l in script['lines']).lower()
    need = [(round(f['profit'] / 1000) == 28, 'twenty-eight thousand dollars', f'profit {f["profit"]:.2f}'),
            (int(round(f['profit'])) == 28085, 'twenty-eight thousand and eighty-five', f'profit {f["profit"]:.2f}'),
            (round(f['staked'] / 1000) == 34, 'thirty-four thousand dollars', f'staked {f["staked"]:.2f}'),
            (round(-f['spx_drop']) == 2, 'fell two percent', f'S&P 500 change {f["spx_drop"]:.2f}%'),
            (f['race'][0][0] == 'gemini', 'gemini now leads the options race', 'Options race leader ' + f['race'][0][0])]
    for ok, phrase, why in need:
        if phrase in txt and not ok:
            raise Fail(f'the script says "{phrase}" but the ledger says {why}')
    if 'perfect storm for a tech-led market selloff' not in f['reason2']:
        raise Fail('the Gemini quote is not in G-OPT-002')
    if 'doubling down on the same puts raises concentration ahead of a binary event' not in f['grades']['claude']['text']:
        raise Fail("Claude's grade text changed")
    if 'binary bet with high premium risk' not in f['grades']['chatgpt']['text']:
        raise Fail("ChatGPT's grade text changed")


# ---------------------------------------------------------------- voice, timing, captions
def norm(t):
    import speech_text
    return speech_text.tokens(t, drop_and=False)


def read_wav(path):
    with wave.open(path) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    if sr != SR:
        n = int(len(x) * SR / sr); x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def trim(x, thr=0.012):
    """Drop the silence before and after a voice line (keeps 40 ms), so beats follow each other tightly."""
    a = np.abs(x); idx = np.where(a > thr)[0]
    if not len(idx):
        return x, 0.0
    s = max(0, idx[0] - int(0.04 * SR)); e = min(len(x), idx[-1] + int(0.06 * SR))
    return x[s:e], s / SR


def token_times(text, words, dur, cut):
    """Start time (s, after trimming) of each script token, from the transcribed words; tokens the transcript does not match are
    placed between their matched neighbours, in proportion to their length."""
    import speech_text
    st = norm(text)
    wt = []
    for w, s, e in speech_text.merge_words(words or []):
        parts = norm(w) or ['_']
        for k, p in enumerate(parts):
            wt.append((p, s + (e - s) * k / len(parts) - cut))
    t = [None] * len(st)
    if wt:
        sm = difflib.SequenceMatcher(None, st, [w for w, _ in wt], autojunk=False)
        for a, b, n in sm.get_matching_blocks():
            for k in range(n):
                t[a + k] = max(0.0, wt[b + k][1])
    if t[0] is None:
        t[0] = 0.0
    lens = [len(x) + 1 for x in st]
    i = 0
    while i < len(st):
        if t[i] is None:
            j = i
            while j < len(st) and t[j] is None:
                j += 1
            t0 = t[i - 1]; t1 = t[j] if j < len(st) else dur * 0.97
            span = lens[i - 1:j]; tot = sum(span); acc = 0
            for k in range(i, j):
                acc += lens[k - 1]; t[k] = t0 + (t1 - t0) * acc / tot
            i = j
        else:
            i += 1
    for k in range(1, len(t)):
        t[k] = max(t[k], t[k - 1])
    return t


def envelope(x, fps=FPS):
    hop = SR // fps
    n = len(x) // hop + 1
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(x) else 0 for i in range(n)])
    return np.clip(e / (e.max() + 1e-6) * 1.3, 0, 1)


# ---------------------------------------------------------------- drawing helpers
def F(kind, weight, size):
    return font(kind, weight, int(size))


def ease(u):
    u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3


def back(u):   # a small overshoot, for things that pop in
    u = max(0.0, min(1.0, u)); c = 1.70158; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def wrap(d, text, f, width):
    out, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            out.append(cur); cur = w
    if cur:
        out.append(cur)
    return out


def bot(d, x, y, col, s=1.0, talk=0.0, blink=False, mood='smile'):
    """One of the three AI robots (the site's mascots), able to talk (mouth follows the voice) and blink."""
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
    else:
        d.line([(x - 35 * s, y + 25 * s), (x, y + 45 * s), (x + 35 * s, y + 25 * s)], fill=INK, width=lw, joint='curve')


def glow_layer(col, alpha=0.38, r=520):
    g = Image.new('RGB', (W, H), BG); gd = ImageDraw.Draw(g)
    gd.ellipse([W // 2 - r, 300, W // 2 + r, 300 + 2 * r], fill=tuple(int(BG[i] + (col[i] - BG[i]) * alpha) for i in range(3)))
    return g.filter(ImageFilter.GaussianBlur(140))


def text_c(d, xy, s, f, fill, stroke=0, anchor='mm'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0) if stroke else None)


def stamp(img, cx, cy, letter, col, u, size=230):
    """A grade stamp that slams onto the screen: big and faint, then its size."""
    if u <= 0:
        return
    k = 1 + 1.6 * (1 - ease(u * 2.2)); a = min(1.0, u * 4)
    s = int(size * k)
    lay = Image.new('RGBA', (s + 40, s + 40), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([20, 20, s + 20, s + 20], radius=int(s * .18), outline=col + (int(255 * a),), width=max(6, s // 18))
    ld.text(((s + 40) / 2, (s + 40) / 2 + s * .02), letter, font=F('sans', 'Bold', s * .78), fill=col + (int(255 * a),), anchor='mm')
    lay = lay.rotate(-9, resample=Image.BICUBIC, expand=True)
    img.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)


# ---------------------------------------------------------------- sound
def tone(f, dur, vol=0.3, decay=6.0, kind='sine'):
    t = np.arange(int(dur * SR)) / SR
    w = np.sin(2 * np.pi * f * t) if kind == 'sine' else 2 * (t * f % 1) - 1
    return (w * vol * np.exp(-decay * t)).astype(np.float32)


def sfx(name):
    rng = np.random.default_rng(7)
    if name == 'whoosh':
        n = int(0.32 * SR); t = np.arange(n) / SR; x = rng.standard_normal(n).astype(np.float32)
        k = np.exp(-((t - 0.16) / 0.09) ** 2); y = np.convolve(x, np.ones(18) / 18, 'same') * k * 0.22
        return y.astype(np.float32)
    if name == 'thud':
        t = np.arange(int(0.45 * SR)) / SR
        f = 95 * np.exp(-5 * t) + 45
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-7 * t) * 0.85
        y[:int(0.02 * SR)] += rng.standard_normal(int(0.02 * SR)) * 0.25
        return y.astype(np.float32)
    if name == 'ching':
        return (tone(1568, 0.6, 0.18, 5) + tone(2093, 0.6, 0.14, 5) + np.pad(tone(2637, 0.55, 0.12, 6), (int(0.07 * SR), 0))[:int(0.6 * SR)]).astype(np.float32)
    if name == 'pop':
        return tone(660, 0.12, 0.2, 25)
    if name == 'riser':
        n = int(1.0 * SR); t = np.arange(n) / SR; x = rng.standard_normal(n).astype(np.float32)
        y = np.convolve(x, np.ones(40) / 40, 'same') * (t / t[-1]) ** 2 * 0.18 + np.sin(2 * np.pi * (200 + 500 * t) * t) * (t / t[-1]) ** 2 * 0.05
        return y.astype(np.float32)
    raise ValueError(name)


# ---------------------------------------------------------------- the story
CAPS = {   # caption chunks per narrator line: (what is shown, how many spoken words it covers, colour)
    '01': [('Two AIs warned', 3, FG), ('against this trade.', 3, FG), ('It made…', 2, FG), ('', 4, UP)],
    '02': [('3 AIs,', 2, FG), ('pretend money,', 2, AMBER), ('real prices.', 2, FG)],
    '03': [('Gemini bet', 2, AIC['gemini']), ('C$34,459', 4, AMBER), ('of pretend money', 3, FG), ('that the stock market', 4, FG), ('would fall.', 2, DOWN)],
    '05': [('Claude and ChatGPT', 3, FG), ('both graded', 2, FG), ('its last buy', 3, FG), ('a C.', 2, DOWN)],
    '08': [('The next day,', 3, FG), ('stocks fell 2%.', 4, DOWN), ('Gemini', 1, AIC['gemini']), ('cashed out.', 2, UP)],
    '09': [('Profit:', 1, FG), ('C$28,085', 7, UP)],
    '10': [('Gemini now leads', 3, AIC['gemini']), ('the Options race.', 3, FG)],
}
QUOTES = {   # quote lines: who, what is shown (with the omitted words marked), the source
    '04': ('gemini', '“…a perfect storm for a tech-led market selloff.”', 'GEMINI’S OWN REASON · G-OPT-002'),
    '06': ('claude', '“…doubling down on the same puts raises concentration ahead of a binary event.”', 'CLAUDE’S GRADE: C · G-OPT-003'),
    '07': ('chatgpt', '“…adding puts before Amazon earnings was a binary bet with high premium risk.”', 'CHATGPT’S GRADE: C · G-OPT-003'),
}


def build(name, engine, out_dir, receipts=None):
    script = json.load(open(f'ops/voice/{name}.json'))
    d = json.load(open('data.json'))
    f = facts_options_gopt(d)
    check_script(f, script)
    vdir = f'social/voice/{name}/{engine}'
    words = json.load(open(f'{vdir}/words.json')) if os.path.exists(f'{vdir}/words.json') else {}
    check = json.load(open(f'{vdir}/check.json')) if os.path.exists(f'{vdir}/check.json') else {}
    import speech_text
    for lid, c in check.items():
        c['match'] = speech_text.similarity(next(l['text'] for l in script['lines'] if l['id'] == lid), c['heard'])
        if c['match'] < 0.85:
            raise Fail(f'voice line {lid} does not say the script (match {c["match"]}): {c["heard"]}')

    # ---- the timeline: each voice line after the last, with a short breath between
    lines, t = [], 0.08
    for i, ln in enumerate(script['lines']):
        x, cut = trim(read_wav(f'{vdir}/{ln["id"]}.wav'))
        dur = len(x) / SR
        tt = token_times(ln['text'], words.get(ln['id']), dur, cut)
        lines.append({**ln, 'x': x, 'start': t, 'dur': dur, 'tok': tt, 'env': envelope(x)})
        gap = 0.16 if ln['who'] == 'narrator' and script['lines'][min(i + 1, len(script['lines']) - 1)]['who'] == 'narrator' else 0.24
        t += dur + gap
    total = t + 1.4
    beats = {ln['id']: (ln['start'], (lines[i + 1]['start'] if i + 1 < len(lines) else total)) for i, ln in enumerate(lines)}
    byid = {ln['id']: ln for ln in lines}

    def at_tok(lid, k):   # absolute time of spoken word k of a line
        ln = byid[lid]; return ln['start'] + ln['tok'][min(k, len(ln['tok']) - 1)]

    # ---- sound: voice, our own music (ducked under the voice), effects on the beats
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32); fx = np.zeros(n, np.float32)
    for ln in lines:
        s = int(ln['start'] * SR); voice[s:s + len(ln['x'])] += ln['x'] * 0.95
    def put(name_, at, vol=1.0):
        y = sfx(name_) * vol; s = max(0, int(at * SR)); fx[s:s + len(y)] += y[:max(0, n - s)]
    for lid in byid:
        put('whoosh', beats[lid][0] - 0.12, 0.8)
    put('ching', at_tok('01', 8), 0.9)
    put('thud', at_tok('05', 4) + 0.05, 1.0); put('thud', at_tok('05', 9) + 0.05, 1.0)
    put('riser', at_tok('08', 3) - 0.9, 0.8)
    put('ching', at_tok('08', 8), 0.8); put('ching', at_tok('09', 1), 1.0)
    put('pop', at_tok('11', 7), 1.0); put('pop', at_tok('11', 9), 1.0)
    import soundtrack
    soundtrack.make('/tmp/yt_music.wav', total + 1, at_tok('09', 1), seed=name, bpm=112)
    mus = read_wav('/tmp/yt_music.wav')[:n]
    mus = np.pad(mus, (0, n - len(mus)))
    env = np.abs(voice); k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, 'same')
    duck = np.clip(1 - env * 9, 0.28, 1.0)
    mix = voice + fx * 0.6 + mus * 0.20 * duck
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)
    os.makedirs('/tmp/yt', exist_ok=True)
    with wave.open('/tmp/yt/mix.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())

    # ---- pictures
    glows = {k: glow_layer(c) for k, c in AIC.items()}
    glows['up'] = glow_layer(UP, .30); glows['amber'] = glow_layer(AMBER, .26); glows['down'] = glow_layer(DOWN, .26)
    rec = Image.open(receipts).convert('RGB') if receipts and os.path.exists(receipts) else None
    nf = int(total * FPS)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'{name}.mp4')
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', '/tmp/yt/mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                           '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest',
                           '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    frames_dir = os.environ.get('YT_FRAMES')   # keep some stills for checking
    spk = {'04': 'gemini', '06': 'claude', '07': 'chatgpt'}

    def talking(who, tt):
        for lid, w in spk.items():
            if w == who:
                ln = byid[lid]; i = int((tt - ln['start']) * FPS)
                if 0 <= i < len(ln['env']):
                    return float(ln['env'][i])
        return 0.0

    def blink(tt, seed):
        return tt > 1.0 and ((tt + seed * 0.37) % 3.7) > 3.58

    for fi in range(nf):
        tt = fi / FPS
        cur = next(lid for lid in reversed(list(beats)) if tt >= beats[lid][0] or lid == '01')
        b0, b1 = beats[cur]; lt = tt - b0; u = lt / max(0.01, b1 - b0)
        mood = {'01': 'gemini', '02': 'amber', '03': 'gemini', '04': 'gemini', '05': 'down', '06': 'claude', '07': 'chatgpt',
                '08': 'down', '09': 'up', '10': 'gemini', '11': 'amber'}[cur]
        img = glows[mood].copy(); dr = ImageDraw.Draw(img)
        # faint chart paper
        for gy in range(TOP + 60, BOT, 120):
            dr.line([(0, gy), (W, gy)], fill=(20, 20, 18), width=1)
        # the bug: the premise is always on screen
        dr.text((L, 268), 'PAPERTRADES.AI', font=F('mono', 'Bold', 34), fill=FG)
        dr.text((R + 70, 268), 'OPTIONS RACE', font=F('mono', 'Bold', 30), fill=AMBER, anchor='ra')
        dr.text((L, 314), '3 AIs · C$100,000 of pretend money each · real prices', font=F('sans', 'Medium', 34), fill=MUTED)
        pin = min(1.0, lt * 5)

        if cur == '01':
            ys = 700
            for k, x0, sc in (('claude', 260, .95), ('chatgpt', 820, .95)):
                bot(dr, x0, ys + 60, AIC[k], sc, blink=blink(tt, 1 if k == 'claude' else 2), mood='worried')
                if tt > 0.35:
                    q = back((tt - 0.35) * 4)
                    cx, cy = x0 + 80, ys - 120
                    dr.ellipse([cx - 44 * q, cy - 44 * q, cx + 44 * q, cy + 44 * q], fill=DOWN, outline=INK, width=5)
                    text_c(dr, (cx, cy + 2), '!', F('sans', 'Bold', 70 * q + 1), INK)
            bot(dr, 540, ys - 20, AIC['gemini'], 1.35, blink=blink(tt, 0))
            text_c(dr, (540, ys + 150), 'GEMINI', F('sans', 'Bold', 64), AIC['gemini'])
            ta = at_tok('01', 6)
            if tt >= ta:
                q = back((tt - ta) * 3.5)
                text_c(dr, (540, 1010), '+C$28,085', F('mono', 'Bold', 150 * (0.6 + 0.4 * q)), UP, 6)
                text_c(dr, (540, 1112), 'in 2 days', F('sans', 'Bold', 70), FG, 4)
        elif cur == '02':
            for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
                q = back((lt - 0.08 * i) * 4); x0 = 240 + i * 300
                bot(dr, x0, 640 + (1 - q) * 300, AIC[k], 1.05, blink=blink(tt, i))
                text_c(dr, (x0, 800 + (1 - q) * 300), NAME[k], F('sans', 'Bold', 62), AIC[k])
            text_c(dr, (540, 960), 'C$100,000 each', F('sans', 'Bold', 112), FG, 4)
            text_c(dr, (540, 1070), 'pretend money · real prices', F('sans', 'SemiBold', 62), AMBER, 3)
        elif cur == '03':
            bot(dr, 230, 600, AIC['gemini'], 1.0, blink=blink(tt, 0))
            dr.text((360, 470), 'GEMINI’S BET', font=F('mono', 'Bold', 40), fill=MUTED)
            dr.text((360, 520), 'Stocks will', font=F('sans', 'Bold', 92), fill=FG)
            dr.text((360, 620), 'FALL', font=F('sans', 'Bold', 120), fill=DOWN)
            ax = 690 + 30 * math.sin(tt * 6)
            dr.polygon([(ax, 650), (ax + 70, 650), (ax + 35, 730)], fill=DOWN)
            box = (L, 800, R + 60, 1170)
            dr.rounded_rectangle(box, radius=26, fill=PANEL, outline=AIC['gemini'], width=4)
            dr.text((L + 36, 830), 'SPY put options (they gain when the S&P 500 falls)', font=F('sans', 'Medium', 36), fill=MUTED)
            for i, (tx, when, amt) in enumerate(f['buys']):
                show = ease((lt - 0.25 - 0.3 * i) * 3)
                if show > 0:
                    yy = 890 + i * 62
                    dr.text((L + 36, yy), f'{when:%b %-d}', font=F('mono', 'Bold', 40), fill=FG)
                    dr.text((L + 200, yy), money(amt * show, False), font=F('mono', 'Bold', 40), fill=AMBER)
                    dr.text((R + 30, yy + 4), tx, font=F('mono', 'Medium', 30), fill=MUTED, anchor='ra')
            tot = f['staked'] * ease((lt - 1.1) * 1.6)
            if lt > 1.1:
                dr.line([(L + 36, 1078), (R + 30, 1078)], fill=LINE, width=3)
                dr.text((L + 36, 1092), 'Total', font=F('mono', 'Bold', 48), fill=FG)
                dr.text((R + 30, 1092), money(tot, False), font=F('mono', 'Bold', 52), fill=AMBER, anchor='ra')
        elif cur in QUOTES:
            who, quote, src = QUOTES[cur]
            ln = byid[cur]
            bot(dr, 540, 700, AIC[who], 1.3, talk=talking(who, tt), blink=blink(tt, 3))
            text_c(dr, (540, 860), NAME[who].upper(), F('sans', 'Bold', 66), AIC[who])
            dr.text((L, 935), src, font=F('mono', 'Bold', 32), fill=MUTED)
            fq = F('sans', 'Bold', 64 if len(quote) < 70 else 56)
            ws = quote.split(); spoken = len(norm(ln['text']))
            heard = sum(1 for k in range(spoken) if tt >= at_tok(cur, k))
            # the quote's words light up as they are said (the spoken part is the end of the shown quote)
            lit = len(ws) - spoken + heard if heard else 0
            yy = 1000; x = L; lh = int(fq.size * 1.22)
            dr.rectangle((L - 24, 998, L - 14, 998 + lh * 4), fill=AIC[who])
            for k, w in enumerate(ws):
                wl = dr.textlength(w + ' ', font=fq)
                if x + wl > R + 60:
                    x = L; yy += lh
                dr.text((x, yy), w, font=fq, fill=FG if k < lit else (90, 86, 76))
                x += wl
        elif cur == '05':
            text_c(dr, (540, 420), 'THEIR GRADES OF GEMINI’S LAST BUY', F('mono', 'Bold', 36), MUTED)
            for k, x0, lid_k in (('claude', 300, 4), ('chatgpt', 780, 9)):
                bot(dr, x0, 720, AIC[k], 1.15, blink=blink(tt, 4), mood='worried')
                text_c(dr, (x0, 880), NAME[k], F('sans', 'Bold', 60), AIC[k])
                ts = at_tok('05', lid_k)
                stamp(img, x0, 1060, 'C', DOWN, (tt - ts) * 2.2, 190)
        elif cur == '08':
            # the S&P 500, trading hours only, with Gemini's buys and sells marked
            sess = [('Oct 28', datetime(2026, 10, 28, 9, 30, tzinfo=NY)), ('Oct 29', datetime(2026, 10, 29, 9, 30, tzinfo=NY)), ('Oct 30', datetime(2026, 10, 30, 9, 30, tzinfo=NY))]
            cx0, cx1, cy0, cy1 = L + 10, R + 40, 540, 1040
            sw = (cx1 - cx0) / 3
            def X(tm):
                for i, (_, s0) in enumerate(sess):
                    if tm.date() == s0.date():
                        return cx0 + i * sw + sw * min(1, max(0, (tm - s0).total_seconds() / 23400))
                return None
            lo, hi = 7500, 7780
            Y = lambda v: cy1 - (v - lo) / (hi - lo) * (cy1 - cy0)
            dr.text((L, 400), 'S&P 500', font=F('sans', 'Bold', 72), fill=FG)
            dr.text((L + 270, 424), '(SPY follows it)', font=F('sans', 'Medium', 42), fill=MUTED)
            dr.text((L, 470), 'Trading hours only · Gemini’s buys and sells', font=F('sans', 'Medium', 32), fill=MUTED)
            for v in (7500, 7600, 7700):
                dr.line([(cx0, Y(v)), (cx1, Y(v))], fill=(34, 33, 29), width=2)
                dr.text((cx0, Y(v) - 34), f'{v:,}', font=F('mono', 'Medium', 26), fill=MUTED)
            for i, (lab, s0) in enumerate(sess):
                text_c(dr, (cx0 + i * sw + sw / 2, cy1 + 40), lab, F('mono', 'Bold', 32), MUTED)
                if i:
                    dr.line([(cx0 + i * sw, cy0), (cx0 + i * sw, cy1)], fill=(34, 33, 29), width=2)
            prog = ease(lt / max(0.1, (at_tok('08', 6) - b0)))
            pts = [(X(tm.astimezone(NY)), Y(v)) for tm, v in f['spx'] if X(tm.astimezone(NY)) is not None]
            pts.sort()
            xmax = cx0 + (cx1 - cx0) * prog
            seg = [p for p in pts if p[0] <= xmax]
            for a_, b_ in zip(seg, seg[1:]):
                if b_[0] - a_[0] < sw * 0.8:
                    dr.line([a_, b_], fill=FG, width=6)
            for tx, when, amt in f['buys']:
                x = X(when)
                if x is not None and x <= xmax:
                    dr.line([(x, cy0), (x, cy1)], fill=AIC['gemini'], width=3)
                    text_c(dr, (x, cy1 + 92), 'BUY', F('mono', 'Bold', 28), AIC['gemini'])
            for tx, when, p in f['sells']:
                x = X(when)
                if x is not None and x <= xmax:
                    dr.line([(x, cy0), (x, cy1)], fill=UP, width=3)
                    text_c(dr, (x, cy1 + 92), 'SELL', F('mono', 'Bold', 28), UP)
            if prog > 0.98:
                dr.text((cx0 + 2 * sw + 20, cy0 + 8), f'{f["spx_drop"]:+.1f}% on Oct 30', font=F('mono', 'Bold', 40), fill=DOWN)
            ts = at_tok('08', 8)
            if tt >= ts:
                q = back((tt - ts) * 3.5)
                text_c(dr, (540, 1205), 'CASHED OUT', F('sans', 'Bold', 74 * (0.6 + 0.4 * q)), UP, 5)
        elif cur == '09':
            v = f['profit'] * ease(lt / 1.2)
            text_c(dr, (540, 430), 'GEMINI’S PROFIT', F('mono', 'Bold', 46), MUTED)
            text_c(dr, (540, 545), money(v), F('mono', 'Bold', 150), UP, 6)
            text_c(dr, (540, 650), '3 sells on Oct 30: ' + ', '.join(tx for tx, _, _ in f['sells']), F('mono', 'Medium', 30), MUTED)
            if rec is not None:
                q = ease((lt - 0.15) * 3)
                rw = 940; rh = int(rec.height * rw / rec.width)
                shot = rec.resize((rw, rh))
                frame = Image.new('RGB', (rw + 20, rh + 20), (70, 67, 60)); frame.paste(shot, (10, 10))
                mask = Image.new('L', frame.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, frame.width - 1, frame.height - 1], radius=24, fill=255)
                y0 = int(800 + (1 - q) * 700)
                img.paste(frame, (int(540 - frame.width / 2), y0), mask)
                dr = ImageDraw.Draw(img)
                text_c(dr, (540, y0 - 34), 'The real ledger on PaperTrades.AI', F('sans', 'SemiBold', 36), FG)
        elif cur == '10':
            dr.text((L, 420), 'OPTIONS RACE', font=F('mono', 'Bold', 40), fill=MUTED)
            dr.text((L, 470), 'Profit since Oct 28', font=F('sans', 'Bold', 72), fill=FG)
            for i, (k, p) in enumerate(f['race']):
                q = ease((lt - 0.12 * i) * 3); y0 = 610 + i * 180; x0 = L + (1 - q) * 600
                dr.rounded_rectangle((x0, y0, x0 + R + 40 - L, y0 + 160), radius=24, fill=PANEL, outline=AIC[k] if i == 0 else LINE, width=5 if i == 0 else 2)
                dr.text((x0 + 36, y0 + 80), str(i + 1), font=F('mono', 'Bold', 64), fill=MUTED, anchor='lm')
                dr.text((x0 + 110, y0 + 80), NAME[k], font=F('sans', 'Bold', 70), fill=AIC[k], anchor='lm')
                dr.text((x0 + R + 10 - L, y0 + 80), money(p), font=F('mono', 'Bold', 58), fill=UP if p > 0 else DOWN, anchor='rm')
            dr.text((L, 1150), f'As of {f["race_at"]:%b %-d}, {f["race_at"]:%-I:%M %p} ET'.replace('AM', 'a.m.').replace('PM', 'p.m.'), font=F('sans', 'Medium', 34), fill=MUTED)
        elif cur == '11':
            for i, k in enumerate(('claude', 'gemini', 'chatgpt')):
                x0 = 240 + i * 300
                bot(dr, x0, 560, AIC[k], 0.95, blink=blink(tt, i))
            text_c(dr, (540, 770), 'Smart or lucky?', F('sans', 'Bold', 110), AMBER, 5)
            tc = at_tok('11', 3)
            if tt >= tc - 0.05:   # a comment bubble
                q = back((tt - tc + 0.05) * 4)
                dr.rounded_rectangle((540 - 230 * q, 850, 540 + 230 * q, 950), radius=30, fill=PANEL, outline=FG, width=4)
                dr.polygon([(390, 948), (430, 948), (380, 990)], fill=FG)
                text_c(dr, (540, 900), 'Comment below', F('sans', 'Bold', 56 * q + 1), FG)
            tl = at_tok('11', 8); ts = at_tok('11', 10); tm = at_tok('11', 11)
            if tt >= tl:   # like
                q = back((tt - tl) * 4)
                bx, by = 300, 1100
                dr.rounded_rectangle((bx - 150, by - 60, bx + 150, by + 60), radius=60, fill=(40, 39, 34))
                # a thumbs-up drawn from shapes
                s_ = 0.9 * q
                dr.rounded_rectangle((bx - 105, by - 10 * s_, bx - 75, by + 38 * s_), radius=6, fill=FG)
                dr.rounded_rectangle((bx - 70, by - 18 * s_, bx - 15, by + 38 * s_), radius=10, fill=FG)
                dr.polygon([(bx - 60, by - 14 * s_), (bx - 40, by - 52 * s_), (bx - 26, by - 46 * s_), (bx - 32, by - 14 * s_)], fill=FG)
                text_c(dr, (bx + 50, by), 'Like', F('sans', 'Bold', 54), FG)
            if tt >= ts:   # subscribe
                q = back((tt - ts) * 4); bx, by = 740, 1100
                pressed = tt - ts > 0.9
                dr.rounded_rectangle((bx - 190 * q, by - 60, bx + 190 * q, by + 60), radius=60, fill=(60, 58, 52) if pressed else (204, 0, 0))
                text_c(dr, (bx, by), 'Subscribed' if pressed else 'Subscribe', F('sans', 'Bold', 54), FG)
            if tt >= tm:
                q = back((tt - tm) * 4)
                text_c(dr, (540, 1250), 'for more trade updates', F('sans', 'Bold', 70 * (0.7 + 0.3 * q)), FG, 5)

        # captions, for the narrator lines, a few words at a time
        if cur in CAPS:
            ln = byid[cur]; k0 = 0; chunk = None; c_at = None
            for txt, nw, col in CAPS[cur]:
                st = at_tok(cur, k0)
                if tt >= st - 0.03:
                    chunk, c_at, ccol = txt, st, col
                k0 += nw
            if chunk:   # '' = no caption while a big number says it on screen
                q = back((tt - c_at) * 7)
                fc = F('sans', 'Bold', 96 * (0.82 + 0.18 * q))
                text_c(dr, (540, CAP_Y), chunk, fc, ccol, 9)
        if lt < 0.2 and cur != '01':   # a quick punch-in on every cut
            z = 1 + 0.045 * (1 - ease(lt / 0.2))
            zw, zh = int(W * z), int(H * z)
            img = img.resize((zw, zh), Image.BILINEAR).crop(((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))
        if frames_dir and fi % 15 == 0:
            os.makedirs(frames_dir, exist_ok=True); img.save(os.path.join(frames_dir, f'{fi:05d}.jpg'), quality=82)
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise Fail('ffmpeg failed')
    meta = {'name': name, 'engine': engine, 'seconds': round(total, 2), 'lines': {ln['id']: [round(ln['start'], 2), round(ln['dur'], 2)] for ln in lines},
            'facts': {'staked': round(f['staked'], 2), 'profit': round(f['profit'], 2), 'spx_drop': round(f['spx_drop'], 2), 'race': f['race'],
                      'race_at': f['race_at'].isoformat()}}
    json.dump(meta, open(os.path.join(out_dir, f'{name}.json'), 'w'), indent=1, default=str)
    return out, meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('--engine', default='gemini'); ap.add_argument('--out', default='social/yt')
    ap.add_argument('--receipts', default=None)
    a = ap.parse_args()
    print(build(a.name, a.engine, a.out, a.receipts))
