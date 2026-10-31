"""Original background music for the race-replay videos (owner, Oct 31: "no music there, can you make sound so that people watch";
all three AIs agreed on an original sound, no copyrighted music: ops/review/youtube-r2-oct30.json).

Everything here is synthesized from scratch with numpy (no samples, no library tracks, no AI music model), so there is
nothing to license and no Content ID claim is possible. Each day gets its own key and chord progression (seeded by the
date), with a riser that lands on the moment the winner appears.

  python3 ops/soundtrack.py out.wav 16 11.2 2026-10-31   -> 16 s, the hit at 11.2 s, seeded by that date
"""
import sys
import wave
import zlib

import numpy as np

SR = 44100
PROGS = [   # (chord roots as semitones from the key, minor/major per chord)
    [(0, 'm'), (8, 'M'), (3, 'M'), (10, 'M')],    # i  VI III VII
    [(0, 'm'), (5, 'm'), (8, 'M'), (10, 'M')],    # i  iv VI VII
    [(0, 'm'), (10, 'M'), (8, 'M'), (7, 'M')],    # i  VII VI V
    [(0, 'm'), (8, 'M'), (10, 'M'), (0, 'm')],    # i  VI VII i
]


def make(path, seconds=16.0, hit_at=11.2, seed='x', bpm=120):
    rng = np.random.default_rng(zlib.crc32(str(seed).encode()))
    n_all = int(SR * seconds); out = np.zeros(n_all); beat = 60 / bpm; bar = 4 * beat
    key = 45 + int(rng.integers(0, 7))          # A2 .. D#3
    prog = PROGS[int(rng.integers(0, len(PROGS)))]
    mid = lambda m: 440 * 2 ** ((m - 69) / 12)

    def env(n, a, d):
        e = np.exp(-np.arange(n) / SR / d); A = int(a * SR)
        if A: e[:A] *= np.linspace(0, 1, A)
        return e

    def add(sig, start):
        s = int(start * SR)
        if s >= n_all: return
        e = min(n_all, s + len(sig)); out[s:e] += sig[:e - s]

    def tone(f, dur, vol, a=0.005, d=0.3, kind='saw'):
        n = int(dur * SR); tt = np.arange(n) / SR
        ks = range(1, 9) if kind == 'saw' else range(1, 9, 2)
        x = sum(np.sin(2 * np.pi * f * k * tt) / k for k in ks) * (0.6 if kind == 'saw' else 1)
        return x * env(n, a, d) * vol

    def kick():
        n = int(0.35 * SR); tt = np.arange(n) / SR; f = 50 + 90 * np.exp(-tt * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * 0.9

    def hat(v):
        n = int(0.05 * SR); x = np.diff(np.concatenate([[0], rng.standard_normal(n)]))
        return x * np.exp(-np.arange(n) / SR * 90) * v

    bars = int(np.ceil(seconds / bar))
    for i in range(bars):
        root, q = prog[i % 4]; r = key + root; ch = [r, r + (3 if q == 'm' else 4), r + 7]; b0 = i * bar
        for m in ch: add(tone(mid(m + 12), bar, 0.035, a=0.4, d=3), b0)                      # pad
        for k in range(8): add(tone(mid(r - 12), beat / 2 * 0.9, 0.18, d=0.12, kind='sq'), b0 + k * beat / 2)   # bass
        if i >= 1:                                                                            # arpeggio
            arp = [ch[0] + 24, ch[1] + 24, ch[2] + 24, ch[1] + 24]
            for k in range(8): add(tone(mid(arp[k % 4]), 0.2, 0.07, d=0.09, kind='sq'), b0 + k * beat / 2)
        if 1 <= i < bars - 1:
            for k in range(4): add(kick(), b0 + k * beat)
        for k in range(8): add(hat(0.10 if k % 2 else 0.06), b0 + k * beat / 2)
    rs = max(0.0, hat_start := hit_at - 2.2); n = int((hit_at - rs) * SR)                        # riser into the reveal
    add(rng.standard_normal(n) * np.linspace(0, 1, n) ** 2 * 0.12, rs)
    n = int(1.5 * SR); tt = np.arange(n) / SR                                                 # the hit
    add(np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 2.5) * 0.6 + rng.standard_normal(n) * np.exp(-tt * 12) * 0.15, hit_at)
    out = np.convolve(out, np.ones(3) / 3, mode='same')
    fi, fo = int(0.3 * SR), int(1.5 * SR)
    out[:fi] *= np.linspace(0, 1, fi); out[-fo:] *= np.linspace(1, 0, fo)
    out = np.tanh(out * 1.3); out /= max(1e-9, np.max(np.abs(out))); out *= 0.85
    st = np.stack([out, np.roll(out, int(0.012 * SR)) * 0.95], 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())
    return path


if __name__ == '__main__':
    make(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else 'x')
