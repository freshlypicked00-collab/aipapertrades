"""Daily share image: every race on its own (each experiment is a separate race; nothing is added together until the end).

races() returns, per race, the three AIs best first with their profit since the Oct 28 restart (China in US$), plus the day's biggest move;
races_card() draws a 1200x675 PNG for Telegram and social sharing. standings()/race_card() (total profit) are kept for the final result only.
"""
import json
from datetime import datetime, timezone, timedelta

FS = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)
AIS = {'claude': ('Claude', 'Anthropic', '#d97757'), 'gemini': ('Gemini', 'Google', '#4f8ff7'), 'chatgpt': ('ChatGPT', 'OpenAI', '#f2f2f2')}
LABEL = {'Stocks': 'Stocks', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy', 'Options': 'Options',
         'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports', 'Predictions': 'Prediction markets'}
T = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))


def _series(src='ops/src'):
    """{(model, exp): [(time, value), ...]} for every AI."""
    out = {}
    for h in json.load(open(f'{src}/history.json')):
        out.setdefault(('claude', h['portfolio']), []).append((T(h['at']), float(h['value'])))
    try:
        for h in json.load(open(f'{src}/rivals.json')).get('history', []):
            out.setdefault((h['model'], h['experiment']), []).append((T(h['at']), float(h['value'])))
    except FileNotFoundError:
        pass
    for v in out.values():
        v.sort(key=lambda p: p[0])   # by time only; on a tie the row written last wins (same as the site)
    return out


def standings(usdcad, day_start=None, src='ops/src'):
    ser = _series(src)
    day_start = day_start or datetime.now(timezone.utc) - timedelta(days=1)
    rows, moves = [], []
    for mid in AIS:
        total, made, lost, n = 0.0, 0.0, 0.0, 0
        for (m, e), pts in ser.items():
            if m != mid or e.startswith('AllIn'):
                continue
            k = usdcad if e == 'China' else 1
            pre = [v for t, v in pts if t <= FS]
            base = pre[-1] if (mid == 'claude' and pre) else 100000.0
            end = max(0.0, pts[-1][1])
            g = (end - base) * k
            total += g; n += 1
            made += max(g, 0); lost += min(g, 0)
            before = [v for t, v in pts if t <= day_start] or [base]
            if before:
                moves.append((abs(end - before[-1]) * k, mid, e, (end - before[-1]) * k, end / before[-1] - 1 if before[-1] else 0))
        if n:
            rows.append({'id': mid, 'total': total, 'made': made, 'lost': lost})
    rows.sort(key=lambda r: -r['total'])
    big = max(moves) if moves else None
    return rows, big


ORDER = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']


def races(day_start=None, src='ops/src'):
    """{race: [(ai, profit), ...] best first} and the biggest move since day_start (in that race's own currency)."""
    ser = _series(src)
    day_start = day_start or datetime.now(timezone.utc) - timedelta(days=1)
    out, moves = {}, []
    for e in ORDER:
        rows = []
        for mid in AIS:
            pts = ser.get((mid, e))
            if not pts:
                continue
            pre = [v for t, v in pts if t <= FS]
            base = pre[-1] if (mid == 'claude' and pre) else 100000.0
            end = max(0.0, pts[-1][1])
            rows.append((mid, end - base))
            before = [v for t, v in pts if t <= day_start] or [base]
            moves.append((abs(end - before[-1]) / max(before[-1], 1), mid, e, end - before[-1], end / before[-1] - 1 if before[-1] else 0))
        if rows:
            out[e] = sorted(rows, key=lambda x: -x[1])
    big = max(moves) if moves else None
    return out, big


def money(x, e):
    return ('+' if x >= 0 else '−') + ('US$' if e == 'China' else 'C$') + f'{abs(x):,.0f}'


def races_card(table, big, title, path='/tmp/pt_race.png'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'text.parse_math': False})
    BG, FG, MUTED, UP, DOWN = '#0b0b0a', '#f2e9d8', '#9b927f', '#3ddc84', '#ff5a4e'
    fig = plt.figure(figsize=(12, 6.75), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1200); ax.set_ylim(675, 0); ax.axis('off')
    ax.text(60, 58, 'PAPERTRADES.AI', color='#ffb000', fontsize=20, fontweight='bold', family='monospace')
    ax.text(60, 92, title, color=FG, fontsize=15)
    ax.text(1140, 58, 'Ten separate races · Claude vs Gemini vs ChatGPT', color=MUTED, fontsize=12, ha='right')
    ax.text(1140, 92, 'Each race on its own · profit since the Oct 28 restart', color=MUTED, fontsize=12, ha='right')
    ax.text(60, 135, 'RACE', color=MUTED, fontsize=10, family='monospace')
    for j, h in enumerate(('1ST', '2ND', '3RD')):
        ax.text(330 + j * 280, 135, h, color=MUTED, fontsize=10, family='monospace')
    y = 158
    for i, e in enumerate(ORDER):
        rows = table.get(e) or []
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((50, y - 4), 1100, 42, color='#141310', zorder=0))
        ax.text(60, y + 17, LABEL.get(e, e) + (' (US$)' if e == 'China' else ''), color=FG, fontsize=13, fontweight='bold', va='center')
        even = rows and max(r[1] for r in rows) - min(r[1] for r in rows) < 0.5
        if not rows or even:
            ax.text(330, y + 17, 'All even so far' if rows else 'No results yet', color=MUTED, fontsize=12, va='center')
        else:
            for j, (mid, p) in enumerate(rows[:3]):
                x = 330 + j * 280
                ax.add_patch(plt.Rectangle((x - 12, y + 6), 5, 22, color=AIS[mid][2]))
                lead = j == 0 and len(rows) > 1 and p - rows[1][1] >= 0.5
                tied = len(rows) > 1 and any(abs(p - q) < 0.5 for k, (_, q) in enumerate(rows) if k != j)
                ax.text(x, y + 17, AIS[mid][0] + (' (tied)' if tied else ''), color=FG, fontsize=13, fontweight='bold' if lead else 'normal', va='center')
                ax.text(x + 250, y + 17, money(p, e), color=UP if p >= 0 else DOWN, fontsize=13, ha='right', va='center', family='monospace')
        y += 44
    if big:
        _, mid, e, d, pct = big
        ax.text(60, 625, f"Biggest move today: {AIS[mid][0]} in {LABEL.get(e, e)}, {money(d, e)} ({pct * 100:+.1f}%)", color=UP if d >= 0 else DOWN, fontsize=13)
    ax.text(1140, 655, 'papertrades.ai · @PaperTradesAI · pretend money, real prices', color=MUTED, fontsize=10, ha='right')
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)
    return path


def race_card(rows, big, title, path='/tmp/pt_race.png', height=6.75):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'text.parse_math': False})
    BG, FG, MUTED, UP, DOWN = '#0b0b0a', '#f2e9d8', '#9b927f', '#3ddc84', '#ff5a4e'
    fig = plt.figure(figsize=(12, height), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1200); ax.set_ylim(675, 0); ax.axis('off')
    ax.text(60, 70, 'PAPERTRADES.AI', color='#ffb000', fontsize=22, fontweight='bold', family='monospace')
    ax.text(60, 112, title, color=FG, fontsize=17)
    ax.text(1140, 70, 'Which AI makes the most money?', color=MUTED, fontsize=13, ha='right')
    ax.text(60, 160, 'TOTAL PROFIT SINCE THE OCT 28 RESTART (C$, ALL 10 EXPERIMENTS)', color=MUTED, fontsize=11, family='monospace')
    y = 215
    for i, r in enumerate(rows):
        name, co, col = AIS[r['id']]
        ax.add_patch(plt.Rectangle((60, y - 38), 1080, 96, color='#161512', zorder=0))
        ax.add_patch(plt.Rectangle((60, y - 38), 8, 96, color=col))
        ax.text(95, y + 2, f'#{i + 1}', color=MUTED, fontsize=20, va='center')
        ax.text(160, y - 6, name, color=FG, fontsize=24, fontweight='bold', va='center')
        ax.text(160, y + 28, co, color=MUTED, fontsize=12, va='center')
        s = ('+' if r['total'] >= 0 else '−') + f"C${abs(r['total']):,.0f}"
        ax.text(1110, y - 4, s, color=UP if r['total'] >= 0 else DOWN, fontsize=30, ha='right', va='center', family='monospace')
        ax.text(1110, y + 30, f"made +C${r['made']:,.0f} · lost −C${-r['lost']:,.0f}", color=MUTED, fontsize=11, ha='right', va='center')
        y += 112
    if big:
        _, mid, e, d, pct = big
        ax.text(60, 572, 'BIGGEST MOVE TODAY', color=MUTED, fontsize=11, family='monospace')
        ax.text(60, 604, f"{AIS[mid][0]} in {LABEL.get(e, e)}: {'+' if d >= 0 else '−'}C${abs(d):,.0f} ({pct * 100:+.1f}%)", color=UP if d >= 0 else DOWN, fontsize=17)
    ax.text(1140, 640, 'papertrades.ai · @PaperTradesAI · simulation with pretend money', color=MUTED, fontsize=11, ha='right')
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)
    return path


if __name__ == '__main__':
    t, big = races()
    print(t, big)
    print(races_card(t, big, 'After Day 1 · Wed Oct 28'))
