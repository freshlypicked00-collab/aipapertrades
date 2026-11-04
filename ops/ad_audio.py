"""Original music and sound effects for the PaperTrades.AI commercials (owner, Nov 4: "make it high production").

Everything is synthesized here with numpy/scipy: no samples, no library tracks, no AI music model, and none of Discord's own
sounds, so there is nothing to license and no Content ID claim is possible (same rule as ops/soundtrack.py).

  score(seconds, marks, seed)  -> stereo float32 array (SR) arranged around the edit's marks:
      marks = {'verse': s, 'build': s, 'drop': s, 'outro': s}   (each optional; the drop is the payoff moment)
  sfx(name)                    -> mono float32: ping, ping2, buzz, whoosh, whip, impact, riser, sub, stamp, ching, tick, pop, sweep
"""
import zlib

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _env(n, a=0.005, d=0.3, s=0.0, r=0.05, hold=None):
    """Attack, exponential decay towards a sustain level, release at the end."""
    t = np.arange(n) / SR
    e = s + (1 - s) * np.exp(-t / max(1e-4, d))
    A = int(a * SR)
    if A:
        e[:A] *= np.linspace(0, 1, A)
    R = int(r * SR)
    if R and R < n:
        e[-R:] *= np.linspace(1, 0, R)
    return e


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f, SR / 2.2), 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, max(f, 10), 'high', fs=SR, output='sos'), x)


def bp(x, f1, f2, order=2):
    return sosfilt(butter(order, [max(f1, 10), min(f2, SR / 2.2)], 'band', fs=SR, output='sos'), x)


def sweep_lp(x, f0, f1, steps=24):
    """A low-pass filter that opens (or closes) over the length of x, in steps (cheap and smooth enough under a mix)."""
    out = np.zeros_like(x); n = len(x); seg = max(1, n // steps)
    for i in range(0, n, seg):
        u = i / max(1, n - 1)
        f = f0 * (f1 / f0) ** u
        y = lp(x[max(0, i - 2048):i + seg], f)
        out[i:i + seg] = y[-len(x[i:i + seg]):]
    return out


def saw(f, t, detune=0.0, voices=1, rng=None):
    rng = rng or np.random.default_rng(0)
    y = np.zeros_like(t)
    for v in range(voices):
        dv = (v - (voices - 1) / 2) * detune
        ph = rng.random()
        y += 2 * ((t * f * (1 + dv) + ph) % 1) - 1
    return y / max(1, voices) ** 0.7


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def reverb(x, seconds=1.6, mix=0.25, seed=3):
    """A simple convolution reverb with a decaying noise tail (synthesized impulse, no recorded room)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 4.6 / seconds)
    ir = lp(ir, 6000); ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    from scipy.signal import fftconvolve
    wet = fftconvolve(x, ir)[:len(x)]
    return x * (1 - mix) + wet * mix * 0.9


# ---------------------------------------------------------------- sound effects
def sfx(name, seed=7):
    rng = np.random.default_rng(seed)
    if name in ('ping', 'ping2'):   # our own notification: two soft bell partials, a rising third (ping2 is a fifth higher)
        base = 1046.5 if name == 'ping' else 1568.0
        t = _t(0.55)
        a = np.sin(2 * np.pi * base * t) * np.exp(-t * 9) + 0.35 * np.sin(2 * np.pi * base * 2.76 * t) * np.exp(-t * 18)
        b = np.sin(2 * np.pi * base * 1.26 * t) * np.exp(-t * 7)
        y = a * 0.5
        k = int(0.075 * SR); y[k:] += b[:len(y) - k] * 0.55
        y[:int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
        return (y * 0.42).astype(np.float32)
    if name == 'buzz':   # a phone vibrating twice on a table
        t = _t(0.62); y = np.zeros_like(t)
        for s0 in (0.0, 0.34):
            m = (t >= s0) & (t < s0 + 0.22)
            tt = t[m] - s0
            y[m] += np.sign(np.sin(2 * np.pi * 172 * tt)) * np.sin(np.pi * tt / 0.22) ** 0.5
        y = lp(y, 900) + 0.15 * lp(rng.standard_normal(len(y)), 300) * (np.abs(y) > 0.01)
        return (y * 0.38).astype(np.float32)
    if name in ('whoosh', 'whip'):
        dur = 0.42 if name == 'whoosh' else 0.24
        t = _t(dur); x = rng.standard_normal(len(t))
        c = dur * 0.55
        k = np.exp(-((t - c) / (dur * 0.24)) ** 2)
        y = bp(x, 400, 5200) * k
        y = sweep_lp(y, 900, 9000) if name == 'whip' else y
        return (y * (0.32 if name == 'whoosh' else 0.38)).astype(np.float32)
    if name == 'impact':   # a cinematic hit: a sub drop, a noise crack and a low boom tail
        t = _t(1.6)
        f = 38 + 110 * np.exp(-t * 14)
        sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
        crack = hp(rng.standard_normal(len(t)), 1500) * np.exp(-t * 38) * 0.6
        boom = lp(rng.standard_normal(len(t)), 180) * np.exp(-t * 3.2) * 1.4
        y = sub * 0.9 + crack + boom
        return (reverb(y, 1.8, 0.2) * 0.55).astype(np.float32)
    if name == 'sub':
        t = _t(1.2); f = 55 * np.exp(-t * 1.2) + 30
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) * 0.6).astype(np.float32)
    if name == 'riser':   # 2 s of noise and a rising tone that lands on the next downbeat
        t = _t(2.0); u = t / t[-1]
        x = rng.standard_normal(len(t))
        n = sweep_lp(hp(x, 300), 600, 12000) * u ** 2.2 * 0.45
        tone = np.sin(2 * np.pi * np.cumsum(220 + 880 * u ** 2) / SR) * u ** 3 * 0.12
        return (n + tone).astype(np.float32)
    if name == 'stamp':   # a rubber stamp hitting paper
        t = _t(0.5)
        y = lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 30) * 1.2 + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 18) * 0.8
        return (y * 0.6).astype(np.float32)
    if name == 'ching':   # a bright win chime
        t = _t(1.1); y = np.zeros_like(t)
        for i, m in enumerate((84, 88, 91, 96)):
            k = int(i * 0.045 * SR)
            tt = t[:len(t) - k]
            y[k:] += np.sin(2 * np.pi * mtof(m) * tt) * np.exp(-tt * 4.2) * (0.7 - i * 0.08)
        return (reverb(y, 1.2, 0.25) * 0.3).astype(np.float32)
    if name == 'tick':
        t = _t(0.03)
        return (hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 300) * 0.25).astype(np.float32)
    if name == 'pop':
        t = _t(0.12); f = 520 * np.exp(-t * 18) + 300
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30) * 0.4).astype(np.float32)
    if name == 'sweep':   # a reversed cymbal-like swell into a hit
        t = _t(1.2); u = t / t[-1]
        y = hp(rng.standard_normal(len(t)), 4000) * u ** 3
        return (y * 0.22).astype(np.float32)
    raise ValueError(name)


# ---------------------------------------------------------------- the score
def score(seconds, marks=None, seed='ad', bpm=120, key=50):
    """A short commercial cue in D minor (key = MIDI root), arranged around the edit:
    intro (pulse and pad) -> verse (kick, bass, arp) at marks['verse'] -> build (riser, snare roll) at marks['build']
    -> drop (everything, the payoff) at marks['drop'] -> outro (one big chord and its tail) at marks['outro']."""
    marks = dict(marks or {})
    rng = np.random.default_rng(zlib.crc32(str(seed).encode()))
    n = int(seconds * SR) + SR
    L = np.zeros(n); R = np.zeros(n)
    beat = 60 / bpm
    v0 = marks.get('verse', 2.0); b0 = marks.get('build', seconds * 0.55); d0 = marks.get('drop', seconds * 0.65)
    o0 = marks.get('outro', seconds - 3.0)
    prog = [(0, 'm'), (-4, 'M'), (-9, 'M'), (-2, 'M')]   # i - VI - III - VII  (Dm Bb F C)

    def add(sig, at, pan=0.0, gain=1.0):
        s = int(at * SR)
        if s >= n or s + len(sig) <= 0:
            return
        if s < 0:
            sig = sig[-s:]; s = 0
        e = min(n, s + len(sig)); sg = sig[:e - s] * gain
        L[s:e] += sg * (1 - max(0, pan)); R[s:e] += sg * (1 + min(0, pan))

    def chord_at(t):
        bar = int(max(0, t - v0) // (4 * beat)) if t >= v0 else 0
        return prog[bar % len(prog)]

    def chord_notes(root, q, octave=0):
        third = 3 if q == 'm' else 4
        return [key + root + 12 * octave, key + root + third + 12 * octave, key + root + 7 + 12 * octave]

    # pad, the whole cue (dark and filtered in the intro, open in the drop)
    t_bar = 4 * beat
    tt = 0.0
    while tt < o0:
        r, q = chord_at(tt + 0.01)
        dur = (v0 - tt + 0.3) if tt < v0 else t_bar + 0.3   # the intro pad holds until the verse
        t = _t(dur)
        y = np.zeros_like(t)
        for m in chord_notes(r, q, 1):
            y += saw(mtof(m), t, detune=0.006, voices=5, rng=rng)
        bright = 5200 if tt >= d0 else 2400 if tt >= v0 else 900
        y = lp(y, bright) * _env(len(t), 0.25, 9, 0.85, 0.3)
        g = 0.05 if tt < v0 else 0.06 if tt < d0 else 0.085
        add(y, tt, -0.25, g); add(np.roll(y, 220), tt, 0.25, g)
        tt = tt + t_bar if tt >= v0 else v0
    # the intro pulse: a ticking clock and a low heartbeat until the verse
    k = 0.0
    while k < v0:
        add(sfx('tick'), k, 0.3, 0.9)
        k += beat / 2
    for hb in np.arange(0.0, v0, beat * 2):
        t = _t(0.3); f = 60 * np.exp(-t * 10) + 40
        add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.5, hb)

    # drums
    def kick():
        t = _t(0.42); f = 48 + 120 * np.exp(-t * 32)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8.5)
        y[:int(0.004 * SR)] += hp(rng.standard_normal(int(0.004 * SR)), 2000) * 0.4
        return y * 0.9

    def clap():
        t = _t(0.3); x = bp(rng.standard_normal(len(t)), 900, 6000)
        e = np.exp(-t * 22)
        for d_ in (0.0, 0.012, 0.024):
            k_ = int(d_ * SR); e[k_:] += np.exp(-np.arange(len(t) - k_) / SR * 40) * 0.6
        return reverb(x * e * 0.5, 0.9, 0.3)

    def hat(open_=False):
        t = _t(0.25 if open_ else 0.06)
        return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.22

    K, C, Hc, Ho = kick(), clap(), hat(), hat(True)
    sc = np.ones(n)   # side-chain: the pad and bass duck on every kick (the pumping sound of a produced track)
    tb = v0
    while tb < o0:
        i_beat = int(round((tb - v0) / beat))
        in_build = b0 <= tb < d0
        in_drop = tb >= d0
        if not in_build or (tb - b0) < (d0 - b0) * 0.5:
            add(K, tb, 0, 0.95 if in_drop else 0.8)
            s = int(tb * SR); e = min(n, s + int(0.25 * SR))
            sc[s:e] = np.minimum(sc[s:e], 0.35 + 0.65 * (np.arange(e - s) / (0.25 * SR)) ** 0.6)
        if i_beat % 2 == 1 and (in_drop or tb >= v0 + 4 * beat):
            add(C, tb, 0.05, 0.75 if in_drop else 0.55)
        add(Hc, tb + beat / 2, 0.35, 0.8)
        if in_drop:
            add(Ho, tb + beat / 2, -0.3, 0.6); add(Hc, tb + beat / 4, 0.4, 0.5); add(Hc, tb + 3 * beat / 4, 0.4, 0.5)
        tb += beat
    # the build: a snare roll that speeds up, and a riser that lands on the drop
    if b0 < d0:
        t_ = b0; step = beat / 2
        while t_ < d0 - 0.02:
            u = (t_ - b0) / (d0 - b0)
            add(C * (0.35 + 0.6 * u), t_, 0.0, 0.7)
            step = beat / 2 if u < 0.35 else beat / 4 if u < 0.7 else beat / 8
            t_ += step
        rz = sfx('riser'); add(rz, d0 - len(rz) / SR, 0, 1.0)
        add(sfx('sweep'), d0 - 1.2, 0, 1.0)

    # bass: an offbeat pluck in the verse, rolling eighths in the drop
    tb = v0
    while tb < o0:
        r, q = chord_at(tb + 0.01)
        m = key + r - 12
        eighths = 8 if tb >= d0 else 4
        for j in range(eighths):
            at = tb + j * (4 * beat) / eighths + (beat / 2 if eighths == 4 else 0)
            if at >= o0:
                break
            if b0 <= at < d0 and (at - b0) > (d0 - b0) * 0.5:
                continue
            t = _t(beat * 0.45)
            y = saw(mtof(m), t, 0.003, 2, rng) * 0.6 + np.sin(2 * np.pi * mtof(m) * t)
            y = lp(y, 700 if tb < d0 else 1100) * _env(len(t), 0.004, 0.18, 0.4, 0.03)
            add(y, at, 0, 0.32)
        tb += 4 * beat
    # arp: sixteenth-note plucks over the chord, from the verse on (an octave up in the drop)
    tb = v0
    pat = [0, 1, 2, 1, 2, 3, 2, 1]
    while tb < o0:
        r, q = chord_at(tb + 0.01)
        notes = chord_notes(r, q, 2 if tb >= d0 else 1) + [key + r + 12 * (3 if tb >= d0 else 2)]
        for j in range(16):
            at = tb + j * beat / 4
            if at >= o0 or (b0 <= at < d0 and j % 2):
                continue
            m = notes[pat[j % len(pat)]]
            t = _t(beat / 4 * 0.95)
            y = (saw(mtof(m), t, 0.004, 3, rng) * 0.5 + np.sign(np.sin(2 * np.pi * mtof(m) * t)) * 0.3)
            y = lp(y, 3800 if tb >= d0 else 2200) * _env(len(t), 0.002, 0.07, 0.0, 0.01)
            add(y, at, 0.45 if j % 2 else -0.45, 0.07 if tb >= d0 else 0.05)
        tb += 4 * beat
    # the outro: one big D minor chord with an impact, and its tail
    t = _t(max(0.5, seconds + 1 - o0))
    y = np.zeros_like(t)
    for m in chord_notes(0, 'm', 0) + chord_notes(0, 'm', 1) + [key + 24]:
        y += saw(mtof(m), t, 0.007, 5, rng)
    y = lp(y, 4200) * _env(len(t), 0.01, 1.4, 0.0, 0.2)
    add(reverb(y, 2.4, 0.4) * 0.09, o0, -0.2); add(reverb(np.roll(y, 300), 2.4, 0.4) * 0.09, o0, 0.2)
    add(K, o0, 0, 1.0); add(sfx('sub'), o0, 0, 0.9)

    # side-chain the whole bed slightly, then a gentle master: soft clip and level
    L *= 0.6 + 0.4 * sc; R *= 0.6 + 0.4 * sc
    st = np.stack([L, R], 1)
    st = np.tanh(st * 1.4) / np.tanh(1.4)
    st /= max(1e-6, np.abs(st).max() / 0.85)
    return st[:int(seconds * SR)].astype(np.float32)


def write_wav(path, x):
    import wave
    x = np.asarray(x, np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    return path


if __name__ == '__main__':
    import sys
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 30
    write_wav(sys.argv[1] if len(sys.argv) > 1 else '/tmp/ad_score.wav', score(secs, {'verse': 2.0, 'build': 15.0, 'drop': 17.0, 'outro': 27.0}))
