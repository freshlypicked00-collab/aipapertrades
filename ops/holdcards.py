"""Two pictures per AI for Discord #holdings (owner, Nov 13: "one showing portfolio and then another showing like 24-hour change").

    portfolio_card(data, mid, path)  -> each race's value, profit and what the money is in (a split bar per race)
    change_card(data, mid, path)     -> each race's change over the last 24 hours, green right / red left

Same look as the Telegram cards (sharecard.py: IBM Plex, dark card, the AI's colour and robot). Numbers come from data.json,
the file the site shows, so they always match the site. China is counted in US$ like on the site.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharecard as SC  # noqa: E402

W, H = 1080, 1500
ORDER = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
GREY = (88, 84, 74)


def _when(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def _money(x, race, sign=False):
    cur = 'US$' if race == 'China' else 'C$'
    s = f'{cur}{abs(round(x)):,}'
    return ('+' if x >= 0 else '−') + s if sign else ('−' + s if x < 0 else s)


TALL = 4000   # draw on a tall canvas, then cut it to the content (never shorter than H): every holding always fits


def _flow(g, bits, font, maxw):
    """Lay the pieces out on as many lines as they need, each piece kept whole (a piece longer than a line is broken at a space)."""
    lines, cur = [], ''
    for b in bits:
        cand = f'{cur} · {b}' if cur else b
        if g.textlength(cand, font=font) <= maxw:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = ''
        for w in b.split(' '):
            c2 = f'{cur} {w}' if cur else w
            if g.textlength(c2, font=font) <= maxw or not cur:
                cur = c2
            else:
                lines.append(cur)
                cur = w
    if cur:
        lines.append(cur)
    return lines


def _finish(im, g, y, line, path):
    h = max(H, int(y) + 150)
    im = im.crop((0, 0, W, h))
    from PIL import ImageDraw
    _foot(ImageDraw.Draw(im), line, h)
    im.save(path)
    return path


def _canvas(mid, title):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (W, TALL), SC.BG)
    g = ImageDraw.Draw(im)
    name, col = SC.AIS[mid]
    g.rectangle([0, 0, W, 14], fill=col)
    g.text((70, 62), 'PAPERTRADES.AI', font=SC._font('bold', 30), fill=SC.ORANGE)
    g.text((70, 104), f'{name.upper()} · {title}', font=SC._font('bold', 54), fill=FG if mid != 'chatgpt' else SC.FG)
    t = datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
    g.text((70, 172), t.strftime('%b %-d, %-I:%M %p ET').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' · pretend money, real prices',
           font=SC._font('med', 28), fill=SC.MUTED)
    SC._robot(im, mid, W - 70 - 92, 52, 92)
    return im, g, col


FG = SC.FG


def _foot(g, line, h=H):
    g.text((70, h - 96), line, font=SC._font('med', 26), fill=SC.MUTED)
    f = SC._font('bold', 34)
    g.text((W - 70 - g.textlength('papertrades.ai', font=f), h - 100), 'papertrades.ai', font=f, fill=FG)


def _rows(data, mid):
    es = data.get('exp_standings') or {}
    out = []
    for race in ORDER:
        r = next((x for x in es.get(race, []) if x.get('id') == mid), None)
        if r:
            out.append((race, r))
    return out


def portfolio_card(data, mid, path):
    im, g, col = _canvas(mid, 'WHAT IT HOLDS')
    rows = _rows(data, mid)
    y, rh = 240, 126
    shades = [col, tuple(int(c * .72) for c in col), tuple(int(c * .5) for c in col), tuple(int(c * .36) for c in col)]
    for race, r in rows:
        v, p = float(r['value']), float(r['profit'])
        pct = p / (v - p) * 100 if v - p else 0
        g.text((70, y), SC.LABEL.get(race, race), font=SC._font('semi', 32), fill=FG)
        right = f"{_money(v, race)}"
        f = SC._font('bold', 32)
        pr = f"{_money(p, race, True)} ({'+' if pct >= 0 else '−'}{abs(pct):.1f}%)"
        fp = SC._font('semi', 28)
        g.text((W - 70 - g.textlength(pr, font=fp), y + 3), pr, font=fp, fill=SC.UP if p >= 0 else SC.DOWN)
        g.text((W - 70 - g.textlength(pr, font=fp) - 24 - g.textlength(right, font=f), y), right, font=f, fill=FG)
        # the split bar: holdings in the AI's colour (biggest first), cash / not bet in grey; shorts are left out of the bar and named
        pie = sorted(r.get('pie') or [], key=lambda s: -float(s['value']))
        cashv = sum(float(s['value']) for s in pie if str(s['name']).startswith(('Cash', 'Not bet')))
        held = [s for s in pie if not str(s['name']).startswith(('Cash', 'Not bet')) and not str(s['name']).endswith('(short)')]
        shorts = [s for s in pie if str(s['name']).endswith('(short)')]
        tot = sum(float(s['value']) for s in held) + cashv or 1
        x0, x1, by = 70, W - 70, y + 48
        x = x0
        for i, s in enumerate(held):
            w = (x1 - x0) * float(s['value']) / tot
            g.rectangle([x, by, x + w - 2, by + 16], fill=shades[min(i, 3)])
            x += w
        if cashv > 0.5:
            g.rectangle([x, by, x1, by + 16], fill=GREY)
        # every holding, full name and amount (owner, Nov 13: "make sure all holdings show ... always")
        nm = (lambda n: str(n).strip()) if race == 'Predictions' else SC.short_name   # a market's full question and side (Yes/No) matter
        bits = [f"{nm(s['name'])} {_money(float(s['value']), race)}" for s in held]
        bits += [f"short {SC.short_name(str(s['name'])[:-8])} {_money(float(s['value']), race)}" for s in shorts]
        if cashv > 0.5:
            bits.append(('not bet' if race == 'Sports' else 'cash') + f' {_money(cashv, race)}')
        fl = SC._font('reg', 24)
        lines = _flow(g, bits, fl, W - 140)
        for i, ln in enumerate(lines):
            g.text((70, by + 24 + i * 30), ln, font=fl, fill=SC.MUTED)
        y += rh + 30 * max(0, len(lines) - 1)
    return _finish(im, g, y, 'Bar = how the money is split · grey = cash · China in US$', path)


def change_card(data, mid, path):
    im, g, col = _canvas(mid, 'LAST 24 HOURS')
    hist = data['history'] if mid == 'claude' else (data.get('models', {}).get(mid, {}).get('history') or [])
    rows = _rows(data, mid)
    now = datetime.now(timezone.utc)
    ch = []
    for race, r in rows:
        pts = [(_when(h['at']), float(h['value'])) for h in hist if h.get('portfolio') == race]
        if not pts:
            continue
        v = float(r['value'])
        then = min(pts, key=lambda t: abs((t[0] - (now - timedelta(hours=24))).total_seconds()))
        d = v - then[1]
        ch.append((race, d, d / then[1] * 100 if then[1] else 0))
    big = max((abs(d) for _, d, _ in ch), default=1) or 1
    y, rh, mid_x = 250, 112, W // 2
    for race, d, pct in ch:
        g.text((70, y), SC.LABEL.get(race, race), font=SC._font('semi', 30), fill=FG)
        txt = f"{_money(d, race, True)} ({'+' if pct >= 0 else '−'}{abs(pct):.1f}%)" if abs(d) >= 0.5 else 'no change'
        f = SC._font('bold', 30)
        g.text((W - 70 - g.textlength(txt, font=f), y), txt, font=f, fill=SC.MUTED if abs(d) < 0.5 else SC.UP if d >= 0 else SC.DOWN)
        by = y + 48
        g.line([mid_x, by - 6, mid_x, by + 26], fill=SC.LINE, width=2)
        w = (W // 2 - 90) * abs(d) / big
        if abs(d) >= 0.5:
            if d >= 0:
                g.rectangle([mid_x, by, mid_x + w, by + 20], fill=SC.UP)
            else:
                g.rectangle([mid_x - w, by, mid_x, by + 20], fill=SC.DOWN)
        y += rh
    up = sorted([c for c in ch if c[1] > 0.5], key=lambda c: -c[1])
    dn = sorted([c for c in ch if c[1] < -0.5], key=lambda c: c[1])
    line = []
    if up:
        line.append(f"Best: {SC.LABEL.get(up[0][0], up[0][0])} {_money(up[0][1], up[0][0], True)}")
    if dn:
        line.append(f"Worst: {SC.LABEL.get(dn[0][0], dn[0][0])} {_money(dn[0][1], dn[0][0], True)}")
    return _finish(im, g, y, ' · '.join(line) or 'Compared with the check-in nearest to 24 hours ago', path)


def highrisk_card(data, path):
    """High risk side races: what each AI holds now in both, and its result so far (owner, Nov 13)."""
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (W, TALL), SC.BG)
    g = ImageDraw.Draw(im)
    g.rectangle([0, 0, W, 14], fill=SC.DOWN)
    g.text((70, 62), 'PAPERTRADES.AI', font=SC._font('bold', 30), fill=SC.ORANGE)
    g.text((70, 104), '🎲 HIGH RISK · WHAT EACH AI HOLDS'.replace('🎲 ', ''), font=SC._font('bold', 54), fill=FG)
    t = datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
    g.text((70, 172), t.strftime('%b %-d, %-I:%M %p ET').replace('AM', 'a.m.').replace('PM', 'p.m.') + ' · side races · pretend money, real prices',
           font=SC._font('med', 28), fill=SC.MUTED)
    hist = data.get('allin_history') or []
    y = 240
    for exp, title in (('AllInTrading', 'HIGH RISK: TRADING'), ('AllInSports', 'HIGH RISK: SPORTS')):
        g.text((70, y), title, font=SC._font('bold', 30), fill=SC.ORANGE)
        y += 52
        for m in data.get('allin_models') or []:
            mid = m['id']
            name, col = SC.AIS[mid]
            pts = sorted(((_when(h['at']), float(h['value'])) for h in hist if h['model'] == mid and h['experiment'] == exp), key=lambda p: p[0])
            if not pts:
                continue
            v, v0 = pts[-1][1], pts[0][1]
            p = v - v0
            b = (m.get('books') or {}).get(exp) or {}
            cash = float(b.get('cash') or 0)
            SC._robot(im, mid, 70, y - 4, 56)
            g.text((142, y), name, font=SC._font('semi', 34), fill=col if mid != 'chatgpt' else FG)
            f, fp = SC._font('bold', 34), SC._font('semi', 28)
            pr = f"{_money(p, exp, True)} ({'+' if p >= 0 else '−'}{abs(p / v0 * 100 if v0 else 0):.1f}%)"
            g.text((W - 70 - g.textlength(pr, font=fp), y + 4), pr, font=fp, fill=SC.UP if p >= 0 else SC.DOWN)
            vt = _money(v, exp)
            g.text((W - 70 - g.textlength(pr, font=fp) - 24 - g.textlength(vt, font=f), y), vt, font=f, fill=FG)
            if exp == 'AllInSports':
                bets = [x for x in (b.get('bets') or []) if str(x.get('status', '')).lower() == 'open']
                stake = lambda x: float(x.get('stake_cad') or x.get('stake') or 0)
                bits = [f"{str(x.get('pick_team') or x.get('pick') or '').strip()} {_money(stake(x), exp)}" for x in bets]
                bits.append(f'not bet {_money(v - sum(stake(x) for x in bets), exp)}')   # the bankroll minus what is riding (the book's cash is not updated by results)
            else:
                pos = b.get('positions') or {}
                wsum = sum(abs(float(q['qty']) * float(q['last'])) for q in pos.values()) or 1
                held = v - cash
                bits = [f"{SC.short_name(q.get('name') or k)}{' (short)' if float(q['qty']) < 0 else ''} {_money(held * abs(float(q['qty']) * float(q['last'])) / wsum, exp)}"
                        for k, q in sorted(pos.items(), key=lambda kv: -abs(float(kv[1]['qty']) * float(kv[1]['last'])))]
                bits.append(f'cash {_money(cash, exp)}')
            fl = SC._font('reg', 25)
            lines = _flow(g, bits, fl, W - 70 - 142)   # every holding, full name (owner, Nov 13: "make sure all holdings show ... always")
            for i, ln in enumerate(lines):
                g.text((142, y + 50 + i * 32), ln, font=fl, fill=SC.MUTED)
            y += 118 + 32 * max(0, len(lines) - 1)
        y += 30
    return _finish(im, g, y, 'Each AI got C$100,000 per side race · one big swing can end it', path)


if __name__ == '__main__':
    import json
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = json.load(open(os.path.join(root, 'data.json')))
    who = sys.argv[1] if len(sys.argv) > 1 else 'gemini'
    print(portfolio_card(d, who, f'/tmp/hold_{who}_1.png'), change_card(d, who, f'/tmp/hold_{who}_2.png'), highrisk_card(d, '/tmp/hold_highrisk.png'))
