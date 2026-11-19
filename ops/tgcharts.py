"""Price picture for a Telegram trade post: the asset over 24 hours, 7 days and 30 days, with the fill marked.

Prices come from Yahoo Finance's public chart data (fetched in GitHub Actions). Returns a PNG path, or None
if the symbol can't be charted, so callers can fall back to another picture.
"""
import json, urllib.parse, urllib.request
from datetime import datetime, timezone

BG, FG, MUTED, LINE, UP, DOWN = '#0b0b0a', '#f2e9d8', '#9b927f', '#2b2923', '#3ddc84', '#ff5a4e'
COINS = {'Bitcoin': 'BTC-USD', 'Ethereum': 'ETH-USD', 'Solana': 'SOL-USD', 'XRP': 'XRP-USD', 'Dogecoin': 'DOGE-USD',
         'Cardano': 'ADA-USD', 'BNB': 'BNB-USD', 'Avalanche': 'AVAX-USD', 'Chainlink': 'LINK-USD', 'Litecoin': 'LTC-USD'}
METALS = {'Gold': 'GC=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 'Palladium': 'PA=F', 'Copper': 'HG=F'}
CUR = {'USD': 'US$', 'CNY': '¥', 'CAD': 'C$', 'HKD': 'HK$'}


def symbol_for(portfolio, holding, code=None):
    """Best Yahoo symbol for one of Claude's holdings, or None."""
    if portfolio in ('Predictions', 'Sports', 'Currencies') or holding.startswith('Cash'):
        return None
    if holding in COINS:
        return COINS[holding]
    if holding in METALS:
        return METALS[holding]
    if portfolio == 'China' and code:
        return code + ('.SS' if code[0] in '569' else '.SZ')
    tok = holding.split()[0]
    return tok if tok.replace('.', '').replace('-', '').isalnum() and tok.upper() == tok else None


def _series(symbol, rng, interval):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={rng}&interval={interval}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (PaperTrades chart)'})
    j = json.loads(urllib.request.urlopen(req, timeout=20).read())['chart']['result'][0]
    ts, cl = j.get('timestamp') or [], j['indicators']['quote'][0].get('close') or []
    pts = [(datetime.fromtimestamp(t, timezone.utc), c) for t, c in zip(ts, cl) if c is not None]
    return pts, j['meta'].get('currency', 'USD'), j['meta'].get('longName') or j['meta'].get('shortName') or symbol


def price_chart(symbol, title, color=None, mark_price=None, action='Buy', path='/tmp/price.png'):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as md
        plt.rcParams.update({'text.parse_math': False, 'font.size': 11, 'text.color': FG, 'xtick.color': MUTED, 'ytick.color': MUTED})
        panels = [('24 hours', '1d', '5m'), ('7 days', '5d', '30m'), ('30 days', '1mo', '1d')]
        data = []
        for name, rng, iv in panels:
            pts, cur, long = _series(symbol, rng, iv)
            if len(pts) >= 2:
                data.append((name, pts))
        if not data:
            return None
        sym = CUR.get(cur, cur + ' ')
        fig, axes = plt.subplots(1, len(data), figsize=(12, 4.2), facecolor=BG)
        axes = axes if len(data) > 1 else [axes]
        for ax, (name, pts) in zip(axes, data):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            ch = ys[-1] / ys[0] - 1
            col = UP if ch >= 0 else DOWN
            ax.set_facecolor(BG)
            ax.plot(xs, ys, color=color or col, lw=2)
            ax.fill_between(xs, ys, min(ys), color=color or col, alpha=.10)
            if mark_price:
                ax.axhline(mark_price, color=MUTED, lw=.9, ls='--')
                ax.plot([xs[-1]], [mark_price], marker='o', ms=8, color=UP if action == 'Buy' else DOWN, zorder=5)
            ax.set_title(f'{name}   {ch * 100:+.1f}%', color=col, loc='left', fontsize=12)
            loc = md.AutoDateLocator(maxticks=5)
            ax.xaxis.set_major_locator(loc)
            ax.xaxis.set_major_formatter(md.ConciseDateFormatter(loc))
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{sym}{v:,.2f}' if v < 1000 else f'{sym}{v:,.0f}'))
            for sp in ax.spines.values():
                sp.set_color(LINE)
            ax.grid(color=LINE, lw=.6)
        fig.suptitle(f'PAPERTRADES.AI · {title} · {long}', color=color or '#ffb000', fontsize=13, x=.01, ha='left', fontweight='bold')
        foot = (f'{action} at {sym}{mark_price:,.4g} (dashed line) · ' if mark_price else '') + 'Simulation only · papertrades.ai'
        fig.text(.99, .01, foot, color=MUTED, ha='right', fontsize=9)
        fig.tight_layout(rect=(0, .03, 1, .93))
        fig.savefig(path, dpi=110, facecolor=BG)
        plt.close(fig)
        return path
    except Exception as e:
        print('price chart failed', symbol, e)
        return None
