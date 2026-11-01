"""Full independent re-check of every fill and every bet (owner, Oct 31: "make sure every number is correct, and that nobody
has cheated"). Runs on GitHub's runner, which can reach the feeds (.github/workflows/audit.yml). READ-ONLY for race data: it only
writes ops/review/full-audit-<day>.json.

1. Every buy, sell, short and cover of all three AIs since the Oct 28 restart (the ten races and High risk; Gemini's and ChatGPT's
   fills from ops/src/rivals.json, Claude's High risk fills there too; Claude's main-race prices are already checked hourly by
   ops/price_audit.py): the fill price against the market at that minute.
     stocks, funds, crypto, futures, currencies, China: Yahoo Finance 1-minute bars within 5 minutes of the fill
     prediction markets: Polymarket's price history within 15 minutes
     options: Cboe keeps no history, so only what can be proven: a buy never below the option's intrinsic value at that minute
2. Every sports bet of all three AIs (main Sports and High risk: sports): the game's real start and final score from ESPN; placed before
   the start; the recorded result follows from the score; the payout follows from the stake and the odds.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
FS = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)
NOW = datetime.now(timezone.utc)
UA = {'User-Agent': 'Mozilla/5.0 (PaperTrades audit; papertrades.ai)'}
OCC = re.compile(r'^([A-Z]{1,6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$')


def t(s):
    d = datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def get(url, timeout=25):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            err = e
            time.sleep(1.5 * (i + 1))
    raise err


_bars = {}


def bars(sym, at, pad=6):
    """1-minute bars (low, high) within pad minutes of at, from Yahoo (regular and extended data as Yahoo returns them)."""
    t0, t1 = int((at - timedelta(minutes=pad)).timestamp()), int((at + timedelta(minutes=pad)).timestamp())
    key = (sym, t0 // 600)
    if key not in _bars:
        out = []
        for host in ('query1', 'query2'):
            try:
                j = get(f'https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={t0 - 600}&period2={t1 + 600}&interval=1m&includePrePost=true')
                res = j['chart']['result'][0]
                q = res['indicators']['quote'][0]
                for ts, lo, hi, cl in zip(res.get('timestamp') or [], q.get('low') or [], q.get('high') or [], q.get('close') or []):
                    if lo is not None and hi is not None:
                        out.append((ts, float(lo), float(hi), float(cl) if cl is not None else None))
                break
            except Exception:
                continue
        _bars[key] = out
    return [b for b in _bars[key] if t0 <= b[0] <= t1]


def tol_for(exp, sym):
    if sym.endswith('-USD'):
        return 0.0075
    if sym.endswith('=F') or sym.endswith('=X'):
        return 0.004
    return 0.003


def feed_sym(tr):
    exp, sym = tr.get('experiment'), str(tr.get('symbol') or '')
    if exp == 'Currencies':
        return None if sym.upper() == 'USD' else f'{sym.upper()}USD=X'
    return sym


def check_fill(tr):
    exp, sym, px, at = tr.get('experiment'), str(tr.get('symbol') or ''), tr.get('price'), t(tr['at'])
    row = {'at': tr['at'], 'model': tr.get('model'), 'experiment': exp, 'action': tr.get('action'), 'symbol': sym, 'name': tr.get('name'),
           'price': px, 'pcur': tr.get('pcur'), 'qty': tr.get('qty'), 'amount': tr.get('amount')}
    try:
        px = float(px)
    except Exception:
        row.update(status='no_price')
        return row
    # the amount follows from quantity x price (x the exchange rate when the race's currency differs)
    try:
        fx = tr.get('fx') or {}
        q = float(tr.get('qty') or 0)
        val_p = q * px   # options: qty is already contracts x 100 (shares), as the race records it
        if tr.get('pcur') == 'CNY':
            val_usd = val_p / float(fx.get('USDCNY') or 0) if fx.get('USDCNY') else None
        else:
            val_usd = val_p
        val = val_usd * float(fx.get('USDCAD')) if (val_usd is not None and tr.get('cur') == 'CAD' and fx.get('USDCAD')) else val_usd
        if val is not None and tr.get('amount') not in (None, '') and q:
            gap = abs(abs(float(tr['amount'])) - abs(val)) / max(1.0, abs(val))
            row['amount_check'] = 'ok' if gap < 0.002 else f'amount {tr["amount"]} vs qty x price {val:.2f}'
    except Exception as e:
        row['amount_check'] = f'not checked ({str(e)[:60]})'
    if exp == 'Predictions':
        row.update(poly_check(tr, px, at))
        return row
    if OCC.match(sym):
        tk, yy, mm, dd, cp, k = OCC.match(sym).groups()
        k = int(k) / 1000
        b = bars(tk, at)
        if not b:
            row.update(status='no_data', basis=f'no 1-minute bars for {tk}')
            return row
        lo, hi = min(x[1] for x in b), max(x[2] for x in b)
        intr_hi = max(0.0, (hi - k) if cp == 'C' else (k - lo))
        intr_lo = max(0.0, (lo - k) if cp == 'C' else (k - hi))
        row.update(basis=f'{tk} {lo:.2f}-{hi:.2f} within 6 min; intrinsic {intr_lo:.2f}-{intr_hi:.2f} (Cboe keeps no option history)')
        if tr.get('action') == 'Buy' and px < intr_lo - 0.05:
            row.update(status='flag', note='bought below the option\'s intrinsic value: impossible at a real ask')
        elif tr.get('action') == 'Sell' and px > intr_hi + max(0.5, 0.6 * px):
            row.update(status='flag', note='sold far above the intrinsic value: check the bid')
        else:
            row.update(status='ok_partial')
        return row
    fs = feed_sym(tr)
    if fs is None:
        row.update(status='ok', basis='US dollar is always 1.0')
        return row
    b = bars(fs, at)
    if not b:
        row.update(status='no_data', basis=f'no 1-minute bars for {fs}')
        return row
    lo, hi = min(x[1] for x in b), max(x[2] for x in b)
    tol = tol_for(exp, fs)
    gap = 0.0 if lo <= px <= hi else (lo - px) / lo if px < lo else (px - hi) / hi
    row.update(feed=fs, feed_low=round(lo, 6), feed_high=round(hi, 6), gap_pct=round(gap * 100, 3), tolerance=f'{tol * 100:.2f}%',
               status='ok' if gap == 0 else 'close' if gap <= tol else 'flag', basis='Yahoo 1-minute bars within 6 minutes')
    return row


_poly = {}


def poly_check(tr, px, at):
    slug, outcome = tr.get('symbol'), tr.get('outcome')
    try:
        if slug not in _poly:
            m = get(f'https://gamma-api.polymarket.com/markets?slug={urllib.parse.quote(slug)}')[0]
            outs = json.loads(m['outcomes']) if isinstance(m['outcomes'], str) else m['outcomes']
            toks = json.loads(m['clobTokenIds']) if isinstance(m['clobTokenIds'], str) else m['clobTokenIds']
            _poly[slug] = dict(zip(outs, toks))
        tok = _poly[slug].get(outcome)
        t0, t1 = int((at - timedelta(minutes=15)).timestamp()), int((at + timedelta(minutes=15)).timestamp())
        h = get(f'https://clob.polymarket.com/prices-history?market={tok}&startTs={t0}&endTs={t1}&fidelity=1').get('history') or []
        if not h:
            h = get(f'https://clob.polymarket.com/prices-history?market={tok}&startTs={t0 - 3600}&endTs={t1 + 3600}&fidelity=10').get('history') or []
        if not h:
            return {'status': 'no_data', 'basis': 'no Polymarket history for that window'}
        ps = [float(x['p']) for x in h]
        lo, hi = min(ps), max(ps)
        gap = 0.0 if lo <= px <= hi else min(abs(px - lo), abs(px - hi))
        return {'feed': 'Polymarket', 'feed_low': lo, 'feed_high': hi, 'gap_abs': round(gap, 4), 'tolerance': '0.03',
                'status': 'ok' if gap == 0 else 'close' if gap <= 0.03 else 'flag', 'basis': 'Polymarket price history within 15 minutes'}
    except Exception as e:
        return {'status': 'no_data', 'basis': f'Polymarket lookup failed: {str(e)[:80]}'}


# ------------------------------------------------------------------ bets
_games = {}


def espn(sport, league, gid):
    k = (sport, league, str(gid))
    if k not in _games:
        try:
            j = get(f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={gid}')
            c = j['header']['competitions'][0]
            teams = {x['homeAway']: x for x in c['competitors']}
            st = c['status']['type']
            win = next((s for s, x in teams.items() if x.get('winner')), None)
            _games[k] = {'start': c.get('date'), 'completed': bool(st.get('completed')), 'state': st.get('name'),
                         'home': teams['home']['team']['displayName'], 'away': teams['away']['team']['displayName'],
                         'home_score': teams['home'].get('score'), 'away_score': teams['away'].get('score'), 'winner': win}
        except Exception as e:
            _games[k] = {'error': str(e)[:100]}
    return _games[k]


def payout(stake, odds):
    o = float(odds)
    return stake * (o / 100 if o > 0 else 100 / abs(o))


SPORT_OF = {'nba': 'basketball', 'wnba': 'basketball', 'mens-college-basketball': 'basketball', 'nfl': 'football', 'college-football': 'football',
            'nhl': 'hockey', 'mlb': 'baseball'}


def all_bets():
    out = []
    cb = json.load(open(os.path.join(SRC, 'bets.json')))
    cb = cb if isinstance(cb, list) else cb.get('bets', [])
    for b in cb:
        out.append({'model': 'claude', 'race': 'Sports', 'id': b.get('bet'), 'game': b.get('game'), 'league': b.get('league'),
                    'sport': b.get('espn_sport') or SPORT_OF.get(str(b.get('league'))), 'side': b.get('side'), 'pick': b.get('pick'), 'event': b.get('event'),
                    'odds': b.get('odds'), 'stake': b.get('stake_cad'), 'result': b.get('result_cad'), 'status': b.get('status'),
                    'placed_at': b.get('placed_at'), 'starts_at': b.get('starts_at'), 'final': b.get('final'), 'legs': b.get('legs') or []})
    r = json.load(open(os.path.join(SRC, 'rivals.json')))
    books = [(mid, exp, (m.get('books') or {}).get(exp) or {}) for mid, m in (r.get('models') or {}).items() for exp in ('Sports', 'AllInSports')]
    books += [('claude', 'AllInSports', ((r.get('claude_allin') or {}).get('books') or {}).get('AllInSports') or {})]
    for mid, exp, bk in books:
        for b in bk.get('bets', []):
            out.append({'model': mid, 'race': exp, 'id': b.get('id'), 'game': b.get('game'), 'league': b.get('league'), 'sport': b.get('sport'),
                        'side': b.get('pick'), 'pick': b.get('pick_team'), 'event': b.get('event'), 'odds': b.get('odds'), 'stake': b.get('stake'),
                        'result': b.get('result'), 'to_win': b.get('to_win'), 'status': b.get('status'), 'placed_at': b.get('placed_at'),
                        'starts_at': b.get('starts_at'), 'final': b.get('final'), 'legs': b.get('legs') or []})
    return out


def check_bet(b):
    row = {k: b.get(k) for k in ('model', 'race', 'id', 'event', 'pick', 'odds', 'stake', 'result', 'status', 'placed_at', 'starts_at', 'final')}
    notes, status = [], 'ok'
    if b.get('placed_at') and t(b['placed_at']) < FS:
        row.update(status='before_restart', note='practice bet from before the Oct 28 restart (does not count)')
        return row
    legs = b.get('legs') or []
    games = legs if legs else [b]
    for lg in games:
        gid = lg.get('game')
        sport, league = lg.get('sport') or b.get('sport'), lg.get('league') or b.get('league')
        if not (gid and sport and league):
            notes.append('no ESPN game id; not checkable')
            status = 'no_data'
            continue
        g = espn(sport, league, gid)
        if g.get('error'):
            notes.append('ESPN lookup failed: ' + g['error'])
            status = 'no_data'
            continue
        start = t(g['start']) if g.get('start') else None
        if start and b.get('placed_at') and t(b['placed_at']) >= start:
            notes.append(f"PLACED AFTER THE START: placed {b['placed_at']}, game started {g['start']}")
            status = 'flag'
        rec = lg.get('starts_at') or b.get('starts_at')
        if start and rec and abs((t(rec) - start).total_seconds()) > 15 * 60:
            notes.append(f"recorded start {rec} differs from ESPN {g['start']}")
            if status == 'ok':
                status = 'note'
        row.setdefault('espn', []).append({k: g.get(k) for k in ('start', 'state', 'away', 'away_score', 'home', 'home_score', 'winner')})
        if g.get('completed') and not legs:
            side = b.get('side')
            exp_res = 'Push' if g['winner'] is None and sport != 'soccer' else ('Won' if g['winner'] == side else 'Lost')
            st = b.get('status')
            if st in ('Won', 'Lost', 'Push') and st != exp_res:
                notes.append(f'RESULT DISAGREES WITH THE SCORE: recorded {st}, the score says {exp_res}')
                status = 'flag'
            if st == 'Open' and NOW - start > timedelta(hours=6):
                notes.append('game finished but the bet is still open')
                status = 'flag' if status == 'ok' else status
            if st in ('Won', 'Lost') and b.get('stake') is not None and b.get('odds') is not None and b.get('result') is not None:
                want = payout(float(b['stake']), b['odds']) if st == 'Won' else -float(b['stake'])
                if abs(float(b['result']) - want) > 0.05:
                    notes.append(f"PAYOUT: recorded {b['result']} but stake {b['stake']} at {b['odds']} gives {want:.2f}")
                    status = 'flag'
    if b.get('status') == 'Void':
        notes.append('voided (stake returned): see corrections.json / the notices for why')
        if status == 'ok':
            status = 'note'
    row.update(status=status, notes=notes)
    return row


def main():
    r = json.load(open(os.path.join(SRC, 'rivals.json')))
    since = FS
    if os.environ.get('NIGHTLY'):   # R6 (root-cause vote, Oct 31): the nightly run re-checks the last 2 days (earlier days were checked already)
        since = max(FS, NOW - timedelta(days=2))
    fills = [x for x in r.get('trades', []) if x.get('action') in ('Buy', 'Sell', 'Short', 'Cover') and t(x['at']) >= since
             and x.get('experiment') not in ('Sports', 'AllInSports')]
    print(f'checking {len(fills)} fills')
    frows = [check_fill(x) for x in fills]
    bets = all_bets()
    if os.environ.get('NIGHTLY'):
        bets = [b for b in bets if not b.get('placed_at') or t(b['placed_at']) >= since - timedelta(days=2)]
    print(f'checking {len(bets)} bets')
    brows = [check_bet(b) for b in bets]
    import collections
    summ = {'fills': dict(collections.Counter(x['status'] for x in frows)), 'fill_amounts': dict(collections.Counter(str(x.get('amount_check', 'n/a'))[:2] for x in frows)),
            'bets': dict(collections.Counter(x['status'] for x in brows))}
    out = {'at': NOW.isoformat(timespec='seconds'), 'summary': summ, 'fills': frows, 'bets': brows}
    path = os.path.join(os.path.dirname(SRC), 'review', f'full-audit-{NOW.strftime("%Y-%m-%d-%H%M")}.json')
    json.dump(out, open(path, 'w'), indent=1)
    print('summary', json.dumps(summ))
    for x in frows:
        if x['status'] in ('flag',) or (x.get('amount_check') not in (None, 'ok')):
            print('::warning::FILL', json.dumps({k: x.get(k) for k in ('at', 'model', 'experiment', 'action', 'symbol', 'price', 'feed_low', 'feed_high', 'gap_pct', 'gap_abs', 'status', 'amount_check', 'note')}))
    for x in brows:
        if x['status'] in ('flag', 'note'):
            print('::warning::BET', json.dumps({k: x.get(k) for k in ('model', 'race', 'id', 'event', 'status', 'notes')}))
    print('written', path)
    if os.environ.get('NIGHTLY'):
        nightly(out, r)


def nightly(out, r):
    """R6: publish the nightly audit's summary for Rules & Audit (ops/src/nightly_audit.json, newest first, 40 nights) and open an
    "Audit flag" issue for any fill or bet flag that is not an option (the option check is a plausibility test) and not already corrected."""
    corrected = {(c.get('model'), c.get('fill_at')) for c in r.get('price_corrections', [])}
    flags = [x for x in out['fills'] if (x['status'] == 'flag' or x.get('amount_check') not in (None, 'ok')) and x.get('experiment') != 'Options'
             and not str(x.get('symbol', '')).startswith(('SPY2', 'QQQ2')) and not x.get('note', '').startswith('sold far above') and (x.get('model'), x.get('at')) not in corrected]
    bflags = [x for x in out['bets'] if x['status'] == 'flag']
    p = os.path.join(SRC, 'nightly_audit.json')
    try:
        hist = json.load(open(p))
    except Exception:
        hist = []
    hist.insert(0, {'at': out['at'], 'fills_checked': len(out['fills']), 'bets_checked': len(out['bets']), 'summary': out['summary'],
                    'open_flags': [{k: x.get(k) for k in ('at', 'model', 'experiment', 'action', 'symbol', 'price', 'feed_low', 'feed_high', 'gap_pct', 'status')} for x in flags]
                    + [{k: x.get(k) for k in ('model', 'race', 'id', 'event', 'status', 'notes')} for x in bflags]})
    json.dump(hist[:40], open(p, 'w'), indent=1)
    if flags or bflags:
        import subprocess
        body = 'The nightly full audit (root-cause vote R6) found fills or bets outside the feeds that are not corrected yet:\n\n' + '\n'.join(
            '- ' + json.dumps({k: x.get(k) for k in ('at', 'model', 'experiment', 'action', 'symbol', 'id', 'price', 'feed_low', 'feed_high', 'gap_pct', 'status', 'notes')}) for x in (flags + bflags)[:30])
        subprocess.run(['gh', 'label', 'create', 'audit-flag', '--color', 'D93F0B', '--description', 'Nightly audit flag'], capture_output=True)
        subprocess.run(['gh', 'issue', 'create', '--title', f"Audit flag: {len(flags) + len(bflags)} to review ({out['at'][:10]})", '--label', 'audit-flag', '--body', body], capture_output=True)


if __name__ == '__main__':
    main()
