"""Estimated trading costs, DISPLAY ONLY (owner, Oct 31, after a reviewer's point that Season 1 is a frictionless sandbox).

All three AIs agreed (ops/review/costs-oct31.json): Season 1 rules stay exactly as agreed on Oct 28 (no costs in the fills, C1);
a second number "after estimated trading costs" is shown next to each AI's profit and is NEVER used for ranking, standings,
elimination or the bust rule (C2). The cost table (C3) is ChatGPT's sourced correction of Claude's first draft, which Claude
accepted (Gemini had accepted the first draft as it was): two of three on these exact figures.

Charged on the amount traded, each way (buys, sells, shorts and covers), the same for all three AIs, from the Oct 28 restart on:
"""
import json
import os
import re

VERSION = 'v1.1 (Oct 31)'
RESTART = '2026-10-28T17:45:00Z'
OCC = re.compile(r'^[A-Z]{1,6}\d{6}[CP]\d{8}$')
RATE = {   # share of the amount traded
    'stock': 0.0005,      # US stocks and ETFs: spread plus small fees
    'china': 0.0005,      # China A-shares: commission and exchange fees (plus 0.05% stamp duty on sales, below)
    'crypto': 0.0020,     # crypto exchange taker fees and spread
    'commodity': 0.0005,  # metals and energy ETFs and futures
    'fx': 0.0001,         # major currencies
    'option': 0.03,       # options: 3% of the premium (bid-ask spread)
    'prediction': 0.025,  # prediction markets: 2.5% of the premium (venue fees are highest near 50 cents)
    'sports': 0.0,        # sportsbook odds already include the bookmaker's cut
}
CHINA_STAMP = 0.0005
TABLE = [('US stocks and ETFs', '0.05%'), ('China A-shares', '0.05% + 0.05% stamp duty on sales'), ('Crypto', '0.20%'),
         ('Metals and energy', '0.05%'), ('Currencies (majors)', '0.01%'), ('Options', '3% of the premium'),
         ('Prediction markets', '2.5% of the premium'), ('Sports bets', '0 (the cut is in the odds)')]
TRADE_ACTIONS = ('Buy', 'Sell', 'Short', 'Cover')


def kind(race, symbol=''):
    s = str(symbol or '')
    if race in ('Sports', 'AllInSports'):
        return 'sports'
    if race == 'Predictions':
        return 'prediction'
    if race == 'Options' or OCC.match(s.split('|')[0]):
        return 'option'
    if race == 'Currencies' or s.endswith('=X'):
        return 'fx'
    if race == 'China' or s.endswith(('.SS', '.SZ')):
        return 'china'
    if race == 'Crypto' or s.endswith('-USD'):
        return 'crypto'
    if race in ('Metals', 'Energy') or s.endswith('=F'):
        return 'commodity'
    return 'stock'


def cost_of(race, symbol, action, amount):
    k = kind(race, symbol)
    c = abs(amount) * RATE[k]
    if k == 'china' and action == 'Sell':
        c += abs(amount) * CHINA_STAMP
    return c


def _utc(s):
    from datetime import datetime, timezone
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def build(state, src):
    """{'version', 'table', 'races': {race: {model: {'cost', 'turnover', 'trades'}}}} in each race's own currency
    (China in US$, everything else in C$)."""
    races = {}

    def add(model, race, symbol, action, amount):
        r = races.setdefault(race, {}).setdefault(model, {'cost': 0.0, 'turnover': 0.0, 'trades': 0})
        r['cost'] += cost_of(race, symbol, action, amount); r['turnover'] += abs(amount); r['trades'] += 1

    for t in state.get('trades', []):   # Gemini's and ChatGPT's ten races, and every AI's All in
        if t.get('action') in TRADE_ACTIONS and _utc(t['at']) >= RESTART and t.get('model') in ('claude', 'gemini', 'chatgpt'):
            add(t['model'], t['experiment'], t.get('symbol'), t['action'], float(t.get('amount') or 0))
    try:
        mine = json.load(open(os.path.join(src, 'trades.json')))
    except Exception:
        mine = []
    for t in mine:   # Claude's ten races
        if t.get('action') not in TRADE_ACTIONS or str(t.get('holding', '')).startswith('[') or _utc(t['at']) < RESTART:
            continue
        amt = t.get('usd') if t.get('portfolio') == 'China' else t.get('cad')
        add('claude', t['portfolio'], t.get('symbol') or '', t['action'], float(amt or 0))
    for r in races.values():
        for v in r.values():
            v['cost'] = round(v['cost'], 2); v['turnover'] = round(v['turnover'], 2)
    return {'version': VERSION, 'table': TABLE, 'races': races}
