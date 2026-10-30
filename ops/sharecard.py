"""Telegram pictures in the same design as the site's Share cards (owner's request, Oct 29): a dark square card with the
AI's colour bar, a bold headline, one plain sentence, and the big green or red amount, or the asset's 24-hour price line
with the fill marked. Fonts are the website's (IBM Plex, in ops/fonts).

    one_card(who, race, headline, sentence, ...)  -> PNG path
    trade_card(who, t, path)                      -> PNG path for one trade, bet or result (rivals' trade dicts)
    moves_card(who, moves, path)                  -> PNG path for several moves in one check-in
Everything fails soft: on any error the callers get None and fall back to their old picture or plain text.
"""
import os
from datetime import datetime, timezone

S = 1080
BG, FG, MUTED, ORANGE, UP, DOWN, LINE = (20, 19, 15), (242, 242, 242), (155, 146, 127), (217, 119, 87), (61, 220, 132), (255, 107, 107), (43, 41, 35)
AIS = {'claude': ('Claude', (217, 119, 87)), 'gemini': ('Gemini', (79, 143, 247)), 'chatgpt': ('ChatGPT', (242, 242, 242))}
LABEL = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy',
         'Options': 'Options', 'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets',
         'AllInTrading': 'All in: trading', 'AllInSports': 'All in: sports'}
SYM = {'CAD': 'C$', 'USD': 'US$', 'CNY': '¥', 'HKD': 'HK$'}
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
VERB = {'Buy': 'buys', 'Sell': 'sells', 'Short': 'shorts', 'Cover': 'covers', 'Bet': 'places a bet', 'Won': 'wins a bet', 'Lost': 'loses a bet',
        'Push': 'gets a refund', 'Void': 'gets a refund', 'Settled': 'settles', 'Expired': 'lets an option expire', 'Penalty': 'is fined'}


def _font(weight, px):
    from PIL import ImageFont
    name = {'bold': 'IBMPlexSansCondensed-Bold.ttf', 'semi': 'IBMPlexSansCondensed-SemiBold.ttf', 'med': 'IBMPlexSansCondensed-Medium.ttf',
            'reg': 'IBMPlexSansCondensed-Regular.ttf', 'mono': 'IBMPlexMono-Medium.ttf'}[weight]
    try:
        return ImageFont.truetype(os.path.join(FONTS, name), px)
    except Exception:
        return ImageFont.load_default()


def _who(x):
    k = str(x or '').lower()
    return k if k in AIS else {'claude (anthropic)': 'claude'}.get(k, 'claude')


def money(v, cur='CAD'):
    return SYM.get(cur, cur + ' ') + f'{abs(v):,.0f}'


def price(v, cur='USD'):
    s = SYM.get(cur, cur + ' ')
    return f'{s}{v:,.0f}' if v >= 1000 else f'{s}{v:,.2f}' if v >= 10 else f'{s}{v:,.3f}' if v >= 1 else f'{s}{v:.4f}'


def short_name(nm):
    nm = str(nm or '').split(' (')[0]
    nm = nm[:-4] if nm.endswith(' USD') else nm
    return nm.split(': ', 1)[-1]


def _wrap(g, text, font, x, y, maxw, lh, fill, max_lines=4):
    words, line, lines = str(text).split(), '', []
    for w in words:
        t = (line + ' ' + w).strip()
        if g.textlength(t, font=font) > maxw and line:
            lines.append(line)
            line = w
        else:
            line = t
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and g.textlength(lines[-1] + '…', font=font) > maxw:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + '…'
    for ln in lines:
        g.text((x, y), ln, font=font, fill=fill)
        y += lh
    return y


def _base(who, race, when=None):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (S, S), BG)
    g = ImageDraw.Draw(im)
    g.rectangle([0, 0, S, 14], fill=AIS[who][1])
    g.text((80, 78), 'PAPER TRADES · AI VS AI', font=_font('bold', 30), fill=ORANGE)
    w = (when or datetime.now(timezone.utc)).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
    sub = (LABEL.get(race, race) if race else 'ALL TEN RACES').upper() + ' · ' + w.strftime('%b %-d, %-I:%M %p ET').replace('AM', 'a.m.').replace('PM', 'p.m.')
    g.text((80, 128), sub, font=_font('med', 30), fill=MUTED)
    return im, g


def _foot(g, line='Every trade and bet · pretend money, real prices'):
    g.text((80, S - 150), line, font=_font('med', 28), fill=MUTED)
    g.text((80, S - 100), 'papertrades.ai', font=_font('bold', 36), fill=FG)
    h = '@PaperTradesAI'
    f = _font('med', 30)
    g.text((S - 80 - g.textlength(h, font=f), S - 96), h, font=f, fill=MUTED)


def _spark(g, pts, box, color, mark=None, cur='USD'):
    """24-hour price line in box (x0, y0, x1, y1); the fill price as a dashed line and a dot."""
    x0, y0, x1, y1 = box
    ys = [p[1] for p in pts] + ([mark] if mark else [])
    lo, hi = min(ys), max(ys)
    if hi - lo < 1e-12:
        hi, lo = hi * 1.001 + 1e-9, lo * 0.999
    t0, t1 = pts[0][0].timestamp(), pts[-1][0].timestamp() or 1
    X = lambda t: x0 + (x1 - x0) * (t.timestamp() - t0) / max(1, t1 - t0)
    Y = lambda v: y1 - (y1 - y0) * (v - lo) / (hi - lo)
    line = [(X(t), Y(v)) for t, v in pts]
    g.polygon(line + [(line[-1][0], y1), (line[0][0], y1)], fill=tuple(int(c * 0.22 + b * 0.78) for c, b in zip(color, BG)))
    g.line(line, fill=color, width=5, joint='curve')
    sym = SYM.get(cur, '')
    fmt = (lambda v: f'{sym}{v:,.0f}') if hi >= 1000 else (lambda v: f'{sym}{v:,.2f}') if hi >= 1 else (lambda v: f'{sym}{v:.4f}')
    f = _font('mono', 24)
    g.text((x1 + 12, Y(hi) - 12), fmt(hi), font=f, fill=MUTED)
    g.text((x1 + 12, Y(lo) - 12), fmt(lo), font=f, fill=MUTED)
    if mark:
        ym = Y(mark)
        for xx in range(int(x0), int(x1), 22):
            g.line([(xx, ym), (min(xx + 11, x1), ym)], fill=MUTED, width=2)
        g.ellipse([line[-1][0] - 12, ym - 12, line[-1][0] + 12, ym + 12], fill=FG, outline=BG, width=4)
    ch = pts[-1][1] / pts[0][1] - 1 if pts[0][1] else 0
    g.text((x0, y1 + 14), f'Last 24 hours  {ch * 100:+.1f}%', font=_font('semi', 28), fill=UP if ch >= 0 else DOWN)


def one_card(who, race, headline, sentence, amount=None, cur='CAD', spark=None, mark=None, bad=None, when=None, path='/tmp/card.png', big=None, small=None):
    try:
        who = _who(who)
        im, g = _base(who, race, when)
        neg = bad if bad is not None else (amount is not None and amount < 0)
        y = _wrap(g, headline, _font('bold', 86), 80, 210, S - 160, 96, DOWN if neg else AIS[who][1], max_lines=2)
        y = _wrap(g, sentence, _font('med', 44), 80, y + 34, S - 160, 56, FG, max_lines=4)
        if spark and len(spark) >= 2:
            top = max(y + 50, 560)
            _spark(g, spark, (80, top, S - 230, S - 230), AIS[who][1] if who != 'chatgpt' else (200, 200, 200), mark, cur)
        elif amount is not None or big:
            yb = max(y + 60, 600)
            txt, col = big if big else (('+' if amount >= 0 else '−') + money(amount, cur), UP if amount >= 0 else DOWN)
            g.text((80, yb), txt, font=_font('bold', 150), fill=col)
            if small:
                g.text((84, yb + 175), small, font=_font('med', 34), fill=MUTED)
        _foot(g)
        im.save(path, optimize=True)
        return path
    except Exception as e:
        print('sharecard failed:', e)
        return None


def _series(symbol):
    try:
        import tgcharts
        pts, cur, _ = tgcharts._series(symbol, '1d', '5m')
        return pts, cur
    except Exception:
        return None, None


def trade_card(who, t, path='/tmp/trade_card.png', symbol=None):
    try:
        return _trade_card(who, t, path, symbol)
    except Exception as e:
        print('sharecard trade_card failed:', e)
        return None


def _trade_card(who, t, path='/tmp/trade_card.png', symbol=None):
    """t: a rivals.py trade dict (experiment, action, symbol, name, amount, cur, price, pcur, stake, pnl, at)."""
    who = _who(who)
    try:
        when = datetime.fromisoformat(str(t.get('at')).replace('Z', '+00:00')) if t.get('at') else None
    except Exception:
        when = None
    nm, act, exp, cur = str(t.get('name') or t.get('symbol') or ''), t.get('action', ''), t.get('experiment', ''), t.get('cur', 'CAD')
    head = AIS[who][0] + ' ' + VERB.get(act, act.lower())
    base = exp.replace('AllIn', '')
    if act in ('Won', 'Lost', 'Push', 'Void') or (base == 'Sports' and act != 'Bet'):
        amt = float(t.get('pnl') if t.get('pnl') is not None else t.get('amount') or 0)
        if act == 'Lost':
            amt = -abs(float(t.get('stake') or t.get('amount') or amt))
        sent = nm.split(' (')[0] + (f" · stake {money(t['stake'], cur)}" if t.get('stake') else '')
        return one_card(who, exp, head, sent, amt if act != 'Push' else 0.0, cur, path=path, bad=act == 'Lost', when=when)
    if act == 'Bet':
        odds = t.get('price')
        game = nm.split(' (', 1)[1].rstrip(')') if ' (' in nm else ''
        sent = f"On the {short_name(nm)}" + (f" at {int(odds):+d}" if isinstance(odds, (int, float)) else '') + (f" · {game}" if game else '')
        stake = float(t.get('amount') or t.get('stake') or 0)
        win = t.get('to_win')
        if win is None and isinstance(odds, (int, float)) and odds:
            win = stake * (100 / -odds if odds < 0 else odds / 100)
        return one_card(who, exp, head, sent, None, cur, path=path, bad=False, big=(money(stake, cur), FG), small=f"stake · to win {money(win, cur)}" if win else 'stake', when=when)
    pc = t.get('pcur') or 'USD'
    px = t.get('price')
    head = AIS[who][0] + ' ' + VERB.get(act, act.lower()) + ' ' + short_name(nm)
    sent = f"{money(t.get('amount', 0), cur)}" + (f" at {price(px, pc)}" if isinstance(px, (int, float)) else '') + (' a coin' if base == 'Crypto' else ' an ounce' if 'Gold' in nm or 'Silver' in nm and 'Shares' not in nm else '')
    if t.get('pnl') is not None and act in ('Sell', 'Cover'):
        sent += f" · {'profit' if t['pnl'] >= 0 else 'loss'} {money(t['pnl'], cur)}"
    pts, pcur = _series(symbol or t.get('symbol')) if (symbol or t.get('symbol')) and base not in ('Predictions', 'Sports') else (None, None)
    if pts and len(pts) >= 2:
        return one_card(who, exp, head, sent, None, pcur or pc, spark=pts, mark=px if isinstance(px, (int, float)) else None, path=path, bad=act in ('Sell',) and (t.get('pnl') or 0) < 0, when=when)
    unit = ' a coin' if base == 'Crypto' else ' a share' if base in ('Stocks', 'China', 'Safe', 'Energy') else ''
    sent = (f"At {price(px, pc)}{unit}" if isinstance(px, (int, float)) else short_name(nm)) + (f" · {'profit' if t['pnl'] >= 0 else 'loss'} {money(t['pnl'], cur)}" if t.get('pnl') is not None and act in ('Sell', 'Cover') else '')
    if act in ('Sell', 'Cover') and t.get('pnl') is not None:
        return one_card(who, exp, head, sent, t['pnl'], cur, path=path, small='profit' if t['pnl'] >= 0 else 'loss', when=when)
    return one_card(who, exp, head, sent, None, cur, path=path, bad=False, big=(money(t.get('amount', 0), cur), FG), small='position size', when=when)


def moves_card(who, moves, path='/tmp/moves_card.png'):
    """Several moves in one check-in: the headline and up to 6 one-line moves."""
    try:
        who = _who(who)
        im, g = _base(who, None)
        y = _wrap(g, f"{AIS[who][0]} makes {len(moves)} move{'s' if len(moves) != 1 else ''}", _font('bold', 86), 80, 210, S - 160, 96, AIS[who][1], max_lines=2)
        y += 30
        f, fs = _font('semi', 40), _font('med', 30)
        for t in moves[:6]:
            act = t.get('action', '')
            col = UP if act in ('Buy', 'Won', 'Cover') else DOWN if act in ('Sell', 'Lost', 'Short') else FG
            nm = str(t.get('name') or t.get('symbol') or '').split(' (')[0]
            amt = t.get('pnl') if act in ('Won', 'Lost') and t.get('pnl') is not None else t.get('amount', 0)
            line = f"{act} {nm}"
            while g.textlength(line, font=f) > S - 420 and len(line) > 8:
                line = line[:-2].rstrip() + '…' if not line.endswith('…') else line[:-2] + '…'
            g.text((80, y), line, font=f, fill=col)
            a = (('+' if amt >= 0 else '−') if act in ('Won', 'Lost') else '') + money(amt, t.get('cur', 'CAD'))
            g.text((S - 80 - g.textlength(a, font=f), y), a, font=f, fill=col)
            g.text((80, y + 48), LABEL.get(t.get('experiment', ''), t.get('experiment', '')), font=fs, fill=MUTED)
            y += 100
            if y > S - 260:
                break
        if len(moves) > 6:
            g.text((80, y), f'+{len(moves) - 6} more on papertrades.ai', font=fs, fill=MUTED)
        _foot(g)
        im.save(path, optimize=True)
        return path
    except Exception as e:
        print('sharecard failed:', e)
        return None


# ---------------- detailed move cards (owner, Oct 30; agreed by Claude, Gemini and ChatGPT: ops/review/tradecards-oct30.json) ----------------
# Owner: "they don't show when you bought in, the price, or why". One card per move, sent as an album after a cover card:
# what (with ticker and quantity), price, size (and % of the race), fill time, the average entry for exits, the AI's own reason
# ("why", at most WHY_MAX characters, cut with "…", never reworded), its "what would prove it wrong", and the 24-hour price line
# only when the feed has it (no empty space reserved). The same layout, limits and order (chronological) for all three AIs.
# Never invents a number: a missing field is left out. 1080 wide, 1080 to 1350 tall (fits the content; 1350 with a chart).
H2 = 1350
WHY_MAX, WRONG_MAX = 480, 220   # owner, Oct 30: 'make sure descriptive, I like where it explains why' (the full reason, almost always)
UNIT = {'Crypto': ' a coin', 'Metals': ' an ounce', 'Stocks': ' a share', 'Safe': ' a share', 'China': ' a share', 'Energy': ' a share'}
QTY = {'Crypto': 'coins', 'Metals': 'oz', 'Stocks': 'shares', 'Safe': 'shares', 'China': 'shares', 'Energy': 'shares', 'Currencies': 'units', 'AllInTrading': 'shares'}
BARREL = ('CL=F', 'BZ=F')


def _et(at):
    try:
        w = datetime.fromisoformat(str(at).replace('Z', '+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
        return w, w.strftime('%-I:%M %p ET').replace('AM', 'a.m.').replace('PM', 'p.m.'), w.strftime('%b %-d')
    except Exception:
        return None, '', ''


def _clip(text, n):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= n else text[:n].rsplit(' ', 1)[0].rstrip(',;:.') + '…'


def _unit(t):
    base = str(t.get('experiment', '')).replace('AllIn', '')
    if str(t.get('symbol')) in BARREL:
        return ' a barrel', 'barrels'
    if base == 'Metals' and str(t.get('symbol', '')).endswith('=F'):
        return ' an ounce', 'oz'
    if base == 'Trading':
        return ('', '') if len(str(t.get('symbol', ''))) > 12 else ((' a coin', 'coins') if str(t.get('symbol', '')).endswith('-USD') else (' a share', 'shares'))
    return UNIT.get(base, ''), QTY.get(base, '')


def qty_txt(q, t):
    """'0.0552 BTC', '12,600 shares', '69.2 barrels' (the unit from the asset)."""
    q = abs(float(q))
    n = f'{q:,.0f}' if q >= 1000 else f'{q:,.1f}' if q >= 100 else f'{q:,.2f}' if q >= 1 else f'{q:.4f}'
    sym = str(t.get('symbol') or '')
    if sym.endswith('-USD') and len(sym) <= 9:
        return n + ' ' + sym[:-4]
    u = _unit(t)[1]
    return n + (' ' + u if u else '')


def exit_info(t, trades):
    """Everything about a sell or cover: the exact numbers recorded with the trade when present (Claude's trades from Oct 30),
    else worked out from the same AI's earlier trades. Keys: avg, since, pct, pnl, n, short, held (before), sold, left."""
    bi = buy_in(trades or [], t) or {}
    if t.get('entry') is not None:
        px = float(t['price']); e = float(t['entry'])
        short = t.get('action') == 'Cover'
        bi.update({'avg': e, 'pct': (e / px - 1) if short else (px / e - 1), 'short': short})
        bi.setdefault('n', 2)
    if t.get('pnl') is not None and t.get('action') in ('Sell', 'Cover'):
        bi['pnl'] = float(t['pnl'])
    if not bi.get('avg'):
        return None
    if t.get('held_before') is not None:
        bi['held'] = float(t['held_before'])
    sold = t.get('qty')
    if sold:
        bi['sold'] = abs(float(sold))
    if t.get('held_after') is not None:
        bi['left'] = float(t['held_after'])
    elif bi.get('held') and bi.get('sold'):
        bi['left'] = max(0.0, bi['held'] - bi['sold'])
    return bi


def race_value(history, model, exp, at):
    """The race's value just before a move, from rivals.json history (model, experiment, value) or Claude's history.json (portfolio, value)."""
    best = None
    for h in history or []:
        e = h.get('experiment') or h.get('portfolio')
        if e != exp or (h.get('model') or 'claude') != model or str(h.get('at')) >= str(at):
            continue
        if best is None or str(h['at']) > str(best['at']):
            best = h
    try:
        return float(best['value']) if best else None
    except Exception:
        return None


def buy_in(trades, t):
    """Average entry and first entry date of the position a Sell/Cover closes, from the same AI's earlier trades in that race."""
    try:
        opener = 'Short' if t.get('action') == 'Cover' else 'Buy'
        q = cost = 0.0
        first, n = None, 0
        for x in trades:
            if x is t or str(x.get('at')) > str(t.get('at')) or x == t or (x.get('at') == t.get('at') and x.get('action') == t.get('action')):
                continue   # later trades and the move itself
            if x.get('model') != t.get('model') or x.get('experiment') != t.get('experiment') or x.get('symbol') != t.get('symbol') or x.get('outcome') != t.get('outcome'):
                continue
            if x.get('action') == opener and x.get('qty') and x.get('price') is not None:
                q += float(x['qty']); cost += float(x['qty']) * float(x['price']); first = first or x.get('at'); n += 1
            elif x.get('action') == t.get('action') and x.get('qty') and q > 0:
                k = min(1.0, float(x['qty']) / q); q -= q * k; cost -= cost * k
                if q <= 1e-9:
                    q = cost = 0.0; first, n = None, 0
        if q <= 0 or t.get('price') is None:
            return None
        avg = cost / q
        move = float(t['price']) / avg - 1
        pct = -move if opener == 'Short' else move
        amt = float(t.get('amount') or 0)
        pnl = (amt * pct / (1 + move)) if amt else None   # amount is the exit value; profit on the part closed
        return {'avg': avg, 'since': first, 'pct': pct, 'pnl': pnl, 'n': n, 'short': opener == 'Short', 'held': q}
    except Exception:
        return None


def _box(g, x, y, w, h, label, value, sub=None, col=FG):
    g.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=(28, 27, 22), outline=LINE, width=2)
    g.text((x + 22, y + 16), label, font=_font('semi', 24), fill=MUTED)
    f = _font('bold', 40)
    while g.textlength(value, font=f) > w - 44 and f.size > 26:
        f = _font('bold', f.size - 2)
    g.text((x + 22, y + 52), value, font=f, fill=col)
    if sub:
        g.text((x + 22, y + 104), sub, font=_font('med', 26), fill=MUTED)


def _quote(g, text, x, y, maxw, color_bar):
    y0 = y
    f, lh = (_font('med', 40), 52) if len(text) <= 300 else (_font('med', 36), 47)
    y = _wrap(g, '“' + text + '”', f, x + 28, y, maxw - 28, lh, FG, max_lines=10)
    g.rectangle([x, y0 + 6, x + 6, y - 10], fill=color_bar)
    return y


def _head(g, who, exp, at, idx=None, total=None, top=None):
    nm_ai, col_ai = AIS[who]
    g.rectangle([0, 0, S, 14], fill=col_ai)
    g.text((80, 70), 'PAPER TRADES · AI VS AI', font=_font('bold', 30), fill=ORANGE)
    w, hm, day = _et(at)
    sub = (top or LABEL.get(exp, exp).upper()) + (f' · {day}, {hm}' if hm else '')
    g.text((80, 116), sub, font=_font('med', 30), fill=MUTED)
    if idx and total and total > 1:
        s = f'{idx} / {total}'
        g.text((S - 80 - g.textlength(s, font=_font('semi', 30)), 116), s, font=_font('semi', 30), fill=MUTED)


def _finish(im, g, y, path, line='Pretend money, real prices · every move on papertrades.ai'):
    H = int(min(H2, max(1080, y + 200)))   # fits the content: square when it fits, up to 4:5 (no empty space reserved)
    im = im.crop((0, 0, S, H))
    from PIL import ImageDraw
    g = ImageDraw.Draw(im)
    g.text((80, H - 150), line, font=_font('med', 28), fill=MUTED)
    g.text((80, H - 100), 'papertrades.ai', font=_font('bold', 36), fill=FG)
    h = '@PaperTradesAI'
    g.text((S - 80 - g.textlength(h, font=_font('med', 30)), H - 96), h, font=_font('med', 30), fill=MUTED)
    im.save(path, optimize=True)
    return path


def move_card(who, t, path='/tmp/move_card.png', buyin=None, race_val=None, spark=None, idx=None, total=None):
    """One move in full. t: a rivals.py-style trade dict. buyin: buy_in(). race_val: race_value() before the move (same currency as amount)."""
    try:
        from PIL import Image, ImageDraw
        who = _who(who)
        nm_ai, col_ai = AIS[who]
        bar = col_ai if who != 'chatgpt' else MUTED
        act, exp = t.get('action', ''), t.get('experiment', '')
        base = exp.replace('AllIn', '')
        im = Image.new('RGB', (S, H2), BG)
        g = ImageDraw.Draw(im)
        _head(g, who, exp, t.get('at'), idx, total)
        nm = str(t.get('name') or t.get('symbol') or '')
        is_bet = base == 'Sports' or act == 'Bet'
        if is_bet and act == 'Bet':
            head = f"{nm_ai} bets on the {short_name(nm)}"
        elif act in ('Won', 'Lost', 'Push', 'Void', 'Settled'):
            head = f"{nm_ai} {VERB.get(act, act.lower())}"
        else:
            head = f"{nm_ai} {VERB.get(act, act.lower())} {short_name(nm)}"
        y = _wrap(g, head, _font('bold', 76), 80, 176, S - 160, 84, DOWN if act == 'Lost' else col_ai if who != 'chatgpt' else FG, max_lines=2)
        cur, pc = t.get('cur', 'CAD'), t.get('pcur') or 'USD'
        px, amt = t.get('price'), t.get('amount')
        unit1, units = _unit(t)
        # ticker and quantity (ChatGPT's must-have)
        sub = []
        if is_bet and ' (' in nm:
            sub.append(nm.split(' (', 1)[1].rstrip(')'))
        elif act in ('Won', 'Lost', 'Push', 'Void', 'Settled'):
            sub.append(short_name(nm))
        else:
            sym = str(t.get('symbol') or '')
            if sym and sym.upper() != short_name(nm).upper():
                sub.append(sym + (f" ({t['outcome']})" if t.get('outcome') else ''))
            q = t.get('qty')
            if q and units and base != 'Predictions':
                q = float(q)
                sub.append(qty_txt(q, t))
        if sub:
            y = _wrap(g, ' · '.join(sub), _font('med', 32), 80, y + 4, S - 160, 40, MUTED, max_lines=2)
        y += 26
        # fact strip
        facts = []
        pct_race = f'{amt / race_val * 100:.0f}% of the race' if (amt and race_val) else None
        if is_bet and act == 'Bet':
            if isinstance(px, (int, float)):
                facts.append(('ODDS', f'{int(px):+d}', None))
            if amt:
                facts.append(('STAKE', money(amt, cur), pct_race))
            win = t.get('to_win')
            if win is None and isinstance(px, (int, float)) and px and amt:
                win = amt * (100 / -px if px < 0 else px / 100)
            if win:
                facts.append(('TO WIN', money(win, cur), None))
        elif act in ('Won', 'Lost', 'Push', 'Void'):
            if t.get('stake'):
                facts.append(('STAKE', money(t['stake'], cur), None))
            p = t.get('pnl')
            if p is not None:
                facts.append(('RESULT', ('+' if p >= 0 else '−') + money(p, cur), None))
            facts.append(('SETTLED', _et(t.get('at'))[1] or '—', None))
        else:
            if isinstance(px, (int, float)):
                facts.append(('PRICE', price(px, pc), unit1.strip() or None))
            if amt:
                facts.append(('SIZE', money(amt, cur), pct_race))
            facts.append(('FILLED', _et(t.get('at'))[1] or '—', _et(t.get('at'))[2] or None))
        bw, gap = (S - 160 - 40) // 3, 20
        for i, (lb, v, sb) in enumerate(facts[:3]):
            vc = (UP if v.startswith('+') else DOWN if v.startswith('−') else FG) if lb == 'RESULT' else FG
            _box(g, 80 + i * (bw + gap), y, bw, 146, lb, v, sb, vc)
        y += 176
        # the exit (owner: "for sure you need to show the buy-in price, when you bought in, how many sold"):
        # units sold of units held and what's left, the average entry and its date, the exit price, and the result on that part
        if buyin and act in ('Sell', 'Cover'):
            short = buyin.get('short')
            g.text((80, y), 'THE ' + ('COVER' if short else 'SALE'), font=_font('semi', 26), fill=MUTED)
            y += 40
            if buyin.get('sold'):
                held = buyin.get('held')
                part = f" of {qty_txt(held, t)} held ({buyin['sold'] / held * 100:.0f}%)" if held and held >= buyin['sold'] * 0.999 else ''
                left = buyin.get('left')
                tail = (' · all of it' if left is not None and left <= 1e-9 else f" · {qty_txt(left, t)} left" if left else '')
                y = _wrap(g, f"{'Covered' if short else 'Sold'} {qty_txt(buyin['sold'], t)}{part}{tail}", _font('semi', 36), 80, y, S - 160, 46, FG, max_lines=2)
            w0, hm0, d0 = _et(buyin.get('since'))
            lab = ('Shorted' if short else 'Bought') + (' at an average of ' if buyin.get('n', 1) > 1 else ' at ')
            when0 = (f', first on {d0} at {hm0}' if buyin.get('n', 1) > 1 else f' on {d0} at {hm0}') if d0 else ''
            y = _wrap(g, f"{lab}{price(buyin['avg'], pc)}{unit1}{when0}", _font('med', 34), 80, y + 4, S - 160, 44, FG, max_lines=2)
            y = _wrap(g, f"{'Covered' if short else 'Sold'} at {price(px, pc)}{unit1} on {_et(t.get('at'))[2]} at {_et(t.get('at'))[1]}", _font('med', 34), 80, y, S - 160, 44, FG, max_lines=2)
            res = f"{buyin['pct'] * 100:+.1f}%".replace('-', '−') + (f"   {'+' if buyin['pnl'] >= 0 else '−'}{money(buyin['pnl'], cur)} on this {'cover' if short else 'sale'}" if buyin.get('pnl') is not None else '')
            g.text((80, y + 6), res, font=_font('bold', 54), fill=UP if buyin['pct'] >= 0 else DOWN)
            y += 92
        why = _clip(t.get('reason'), WHY_MAX)
        if why:
            g.text((80, y + 6), f'WHY · IN {nm_ai.upper()}’S OWN WORDS', font=_font('semi', 26), fill=MUTED)
            y = _quote(g, why, 80, y + 50, S - 160, bar) + 14
        if act in ('Buy', 'Short', 'Bet'):
            wrong = _clip(t.get('wrong_if'), WRONG_MAX)
            g.text((80, y + 6), 'WHAT WOULD PROVE IT WRONG', font=_font('semi', 26), fill=MUTED)
            y = _wrap(g, wrong or 'Not given.', _font('reg', 34), 80, y + 46, S - 160, 44, FG if wrong else MUTED, max_lines=4) + 10
        if spark and len(spark) >= 2 and y < H2 - 470:   # the reason comes first; the chart only where it still fits
            _spark(g, spark, (80, y + 40, S - 230, H2 - 250), col_ai if who != 'chatgpt' else (200, 200, 200), px if isinstance(px, (int, float)) else None, pc)
            y = H2
        return _finish(im, g, y, path)
    except Exception as e:
        print('sharecard move_card failed:', e)
        return None


def cover_card(who, moves, path='/tmp/cover_card.png', more=0, exits=None):
    """The album's first picture: the headline and one row per move with its price (each move's details follow)."""
    try:
        from PIL import Image, ImageDraw
        who = _who(who)
        nm_ai, col_ai = AIS[who]
        im = Image.new('RGB', (S, H2), BG)
        g = ImageDraw.Draw(im)
        _head(g, who, None, moves[0].get('at'), top='ONE CHECK-IN')
        y = _wrap(g, f"{nm_ai} makes {len(moves)} move{'s' if len(moves) != 1 else ''}", _font('bold', 86), 80, 176, S - 160, 96, col_ai if who != 'chatgpt' else FG, max_lines=2) + 30
        f, fs = _font('semi', 40), _font('med', 30)
        shown = 0
        for t in moves:
            if y > H2 - 340:
                break
            act = t.get('action', '')
            col = UP if act in ('Buy', 'Won', 'Cover') else DOWN if act in ('Sell', 'Lost', 'Short') else FG
            amt = t.get('pnl') if act in ('Won', 'Lost') and t.get('pnl') is not None else t.get('amount', 0)
            a = (('+' if amt >= 0 else '−') if act in ('Won', 'Lost') else '') + money(amt or 0, t.get('cur', 'CAD'))
            line = f"{act} {short_name(t.get('name') or t.get('symbol'))}"
            while g.textlength(line, font=f) > S - 200 - g.textlength(a, font=f) and len(line) > 8:
                line = line[:-2].rstrip() + '…'
            g.text((80, y), line, font=f, fill=col)
            g.text((S - 80 - g.textlength(a, font=f), y), a, font=f, fill=col)
            race = '  ' + LABEL.get(t.get('experiment', ''), t.get('experiment', ''))   # the race, next to the name on every row
            x2 = 80 + g.textlength(line, font=f)
            if x2 + g.textlength(race, font=_font('med', 28)) < S - 110 - g.textlength(a, font=f):
                g.text((x2, y + 10), race, font=_font('med', 28), fill=MUTED)
            px = t.get('price')
            pc = t.get('pcur') or 'USD'
            ex = (exits or [None] * len(moves))[moves.index(t)] if exits else None
            det = ''
            if ex and isinstance(px, (int, float)):
                # a sell on the cover: how much, the buy-in, the exit, the result
                pct = f"{ex['pct'] * 100:+.1f}%".replace('-', '−')
                room = S - 200 - g.textlength(pct, font=_font('bold', 30))
                core = (qty_txt(ex['sold'], t) + ' · ' if ex.get('sold') else '') + f"bought {price(ex['avg'], pc)}" + (f" {_et(ex.get('since'))[2]}" if ex.get('since') else '') + f" → sold {price(px, pc)}"
                det = core
                while g.textlength(det, font=fs) > room and len(det) > 10:
                    det = det[:-2].rstrip() + '…'
                g.text((80, y + 50), det, font=fs, fill=MUTED)
                g.text((S - 80 - g.textlength(pct, font=_font('bold', 30)), y + 50), pct, font=_font('bold', 30), fill=UP if ex['pct'] >= 0 else DOWN)
            else:
                if isinstance(px, (int, float)):
                    det += (f'odds {int(px):+d}' if act == 'Bet' else (qty_txt(t['qty'], t) + ' ' if t.get('qty') and act != 'Bet' and t.get('experiment') != 'Predictions' else '') + 'at ' + price(px, pc) + _unit(t)[0])
                g.text((80, y + 50), det, font=fs, fill=MUTED)
            y += 112
            shown += 1
        if shown < len(moves) or more:
            g.text((80, y), f'+{len(moves) - shown + more} more on papertrades.ai', font=fs, fill=MUTED)
            y += 50
        g.text((80, y + 30), 'Swipe for each move: price, size, time and why →', font=_font('semi', 32), fill=FG)
        return _finish(im, g, y + 80, path, 'Pretend money, real prices')
    except Exception as e:
        print('sharecard cover_card failed:', e)
        return None


def album(who, moves, trades=None, history=None, prefix='/tmp/album', series=None, limit=9):
    """Pictures for one check-in, in order: [cover] + one card per move (chronological, at most `limit` cards; the cover says how many more).
    A single move gets just its card. trades: the full trade list (for entries); history: value history (for % of the race);
    series: function(symbol) -> 24h points or None. Returns a list of PNG paths (empty on failure)."""
    try:
        mv = sorted(moves, key=lambda t: str(t.get('at', '')))
        out = []
        if len(mv) > 1:
            ex = [exit_info(t, trades) if t.get('action') in ('Sell', 'Cover') else None for t in mv]
            c = cover_card(who, mv, f'{prefix}-0.png', more=max(0, len(mv) - limit), exits=ex)
            if c:
                out.append(c)
        for i, t in enumerate(mv[:limit], 1):
            base = str(t.get('experiment', '')).replace('AllIn', '')
            bi = exit_info(t, trades) if t.get('action') in ('Sell', 'Cover') else None
            rv = race_value(history, _who(who) if t.get('model') is None else t.get('model'), t.get('experiment'), t.get('at')) if history else None
            sp = None
            if series and t.get('symbol') and base not in ('Predictions', 'Sports'):
                try:
                    sp = series(t['symbol'])
                except Exception:
                    sp = None
            p = move_card(who, t, f'{prefix}-{i}.png', bi, rv, sp, i if len(mv) > 1 else None, min(len(mv), limit) if len(mv) > 1 else None)
            if p:
                out.append(p)
        return out
    except Exception as e:
        print('sharecard album failed:', e)
        return []


def tg_album(token, chat, photos, caption='', silent=False):
    """Send pictures as ONE Telegram album (sendMediaGroup, 2 to 10), the caption on the first. Returns True when sent.
    A caption over 1,020 characters is sent as a text message right after the album."""
    import json as _j, urllib.request, urllib.parse
    photos = [p for p in photos if p][:10]
    if not (token and chat) or len(photos) < 2:
        return False
    short = caption if len(caption) <= 1020 else ''
    media = [dict({'type': 'photo', 'media': f'attach://p{i}'}, **({'caption': short, 'parse_mode': 'HTML'} if i == 0 and short else {})) for i in range(len(photos))]
    b = '----ptalbum'
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in
             (('chat_id', chat), ('media', _j.dumps(media)), ('disable_notification', 'true' if silent else 'false'))]
    for i, p in enumerate(photos):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="p{i}"; filename="p{i}.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(p, 'rb').read() + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMediaGroup', b''.join(parts), {'Content-Type': f'multipart/form-data; boundary={b}'})
        urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        print('telegram album failed:', e)
        return False
    if caption and not short:
        try:
            data = urllib.parse.urlencode({'chat_id': chat, 'text': caption, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true', 'disable_notification': 'true'}).encode()
            urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data, timeout=20).read()
        except Exception as e:
            print('telegram album caption failed:', e)
    return True


def chart_points(symbol, experiment):
    """24-hour points for a move's price line, or None (no chart for options, bets and prediction markets)."""
    base = str(experiment or '').replace('AllIn', '')
    if base in ('Sports', 'Predictions', 'Options') or len(str(symbol)) > 12:
        return None
    sym = str(symbol)
    if base == 'Currencies':
        sym = 'CAD=X' if sym == 'USD' else ('JPY=X' if sym == 'JPY' else f'{sym}USD=X')
    pts, _ = _series(sym)
    if base == 'Currencies' and sym == 'JPY=X' and pts:
        return None   # the card shows the yen in US$; JPY=X is yen per dollar, so no line rather than an upside-down one
    return pts


def just_reason(text):
    """Claude's log line minus its bookkeeping ("Sold Bitcoin: C$11,288 at US$79,005.5." before, "Filled by the race runner ..." after),
    so its card shows only the reason, like Gemini's and ChatGPT's."""
    import re
    t = ' '.join(str(text or '').split())
    t = re.sub(r'^(Bought|Sold|Shorted|Covered|Bet|Queued)\b[^:]{0,80}:\s*(?:C\$|US\$|¥)[\d,]+(?:\.\d+)? at (?:C\$|US\$|¥)?[\d,]+(?:\.\d+)?\.?\s*', '', t)
    t = re.sub(r'\s*Filled by the race runner.*$', '', t)
    return t.strip()
