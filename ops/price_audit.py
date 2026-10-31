"""Independent price check of Claude's own numbers (owner's decision with Gemini and ChatGPT, Oct 29).

Gemini's and ChatGPT's fills and values come straight from the race's price feeds. Claude's check-ins run where those feeds
can't be reached, so Claude looks prices up itself and writes them (with a source) into its updates. This script runs on the
same GitHub runner as the rivals' check-ins and compares every price Claude used since the Oct 28 restart, fills and
valuations, with the feed at the time Claude stated:
  - Yahoo Finance 1-minute bars (regular session, the same price the rivals get) for stocks, funds, crypto, currencies,
    metals (COMEX futures, compared with Claude's spot price) and China ETFs;
  - Polymarket's own price history for prediction markets.
A price passes when it lies inside the feed's low-high range around that time, give or take the tolerance below.
Results go to ops/src/price_audit.json (shown in Rules & Audit). Flags are not corrections by themselves: Claude reviews
each one and logs a correction only when a price was really wrong. Checked rows are cached, so each run only checks new ones.
"""
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R  # noqa: E402  (get_json, with retries and a user agent)

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
OUT = os.path.join(SRC, 'price_audit.json')
START = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)

# Claude's holding name -> (feed symbol, how to read it, tolerance, note)
MAP = {
    'Bitcoin': ('BTC-USD', 'usd', 0.01, ''), 'Ethereum': ('ETH-USD', 'usd', 0.01, ''), 'Solana': ('SOL-USD', 'usd', 0.01, ''),
    'Gold': ('GC=F', 'usd', 0.015, 'Claude uses the spot price; the feed is COMEX futures, which usually trade a little above spot'),
    'Silver': ('SI=F', 'usd', 0.02, 'Claude uses the spot price; the feed is COMEX futures, which usually trade a little above spot'),
    'Japanese yen': ('JPY=X', 'inv', 0.005, 'US$ per yen (the feed quotes yen per US$)'),
    'Euro': ('EUR=X', 'inv', 0.005, 'US$ per euro'), 'British pound': ('GBP=X', 'inv', 0.005, 'US$ per pound'),
    'Canadian dollar': ('CAD=X', 'inv', 0.005, 'US$ per C$'), 'Swiss franc': ('CHF=X', 'inv', 0.005, 'US$ per franc'),
    'Australian dollar': ('AUD=X', 'inv', 0.005, 'US$ per A$'), 'Mexican peso': ('MXN=X', 'inv', 0.005, 'US$ per peso'),
    'CSI 300 ETF': ('510300.SS', 'local', 0.005, ''), 'SSE Dividend ETF': ('510880.SS', 'local', 0.005, ''),
    'STAR 50 ETF': ('588000.SS', 'local', 0.005, ''),
}
PRED = {  # prediction markets: Polymarket event slug, words that pick the market, outcome
    'Democrats win the Senate (Yes)': ('which-party-will-win-the-senate-in-2026', 'democrat', 'Yes'),
}
SKIP = {'US dollar'}   # the base currency of the dollar position: always 1.0


def when(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def feed_for(holding):
    if holding in MAP:
        return MAP[holding]
    if re.fullmatch(r'[A-Z]{1,5}', holding or ''):
        return (holding, 'usd', 0.005, '')
    return None


_bars = {}


def bars(sym, t0, t1):
    """1-minute regular-session bars [(time, low, high, close)] for sym between t0 and t1 (cached per symbol and day)."""
    # Full audit, Oct 31: the cache was keyed by day but filled with only the first window asked for, so later checks on the same day were
    # compared with bars from another time of day (32 rows). Now whole UTC days are fetched once and the minutes asked for are kept.
    d0 = datetime(t0.year, t0.month, t0.day, tzinfo=timezone.utc)
    d1 = datetime(t1.year, t1.month, t1.day, tzinfo=timezone.utc) + timedelta(days=1)
    key = (sym, d0, d1)
    if key in _bars:
        return [b for b in _bars[key] if t0 <= b[0] <= t1]
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={int(d0.timestamp())}'
           f'&period2={int(d1.timestamp())}&interval=1m&includePrePost=false')
    out = []
    try:
        j = R.get_json(url, timeout=25)['chart']['result'][0]
        q = j['indicators']['quote'][0]
        for i, ts in enumerate(j.get('timestamp') or []):
            lo, hi, cl = q['low'][i], q['high'][i], q['close'][i]
            if lo is not None and hi is not None and cl is not None:
                out.append((datetime.fromtimestamp(ts, timezone.utc), float(lo), float(hi), float(cl)))
    except Exception as e:
        print(f'::warning::price check: no Yahoo bars for {sym}: {str(e)[:120]}')
    _bars[key] = out
    return [b for b in out if t0 <= b[0] <= t1]


def feed_range(sym, t):
    """(low, high, what) around time t: the bars within 5 minutes, else the last close before t (market closed)."""
    near = [b for b in bars(sym, t - timedelta(minutes=30), t + timedelta(minutes=30)) if abs((b[0] - t).total_seconds()) <= 300]
    if near:
        return min(b[1] for b in near), max(b[2] for b in near), '1-minute bars within 5 minutes'
    before = [b for b in bars(sym, t - timedelta(days=4), t + timedelta(minutes=1)) if b[0] <= t]
    if before:
        b = before[-1]
        return b[3], b[3], 'last regular-session close (' + b[0].strftime('%b %-d %H:%M UTC') + ')'
    return None


_poly = {}


def poly_range(holding, t):
    slug, word, outcome = PRED[holding]
    if slug not in _poly:
        tok = None
        try:
            ev = R.get_json(f'https://gamma-api.polymarket.com/events?slug={urllib.parse.quote(slug)}', timeout=20)
            for m in (ev[0].get('markets') if ev else []) or []:
                if word in (str(m.get('groupItemTitle', '')) + ' ' + str(m.get('question', ''))).lower():
                    names, toks = json.loads(m.get('outcomes') or '[]'), json.loads(m.get('clobTokenIds') or '[]')
                    tok = toks[names.index(outcome)] if outcome in names else None
                    break
        except Exception as e:
            print(f'::warning::price check: Polymarket lookup failed for {slug}: {str(e)[:120]}')
        _poly[slug] = tok
    tok = _poly[slug]
    if not tok:
        return None
    try:
        j = R.get_json(f'https://clob.polymarket.com/prices-history?market={tok}&startTs={int((t - timedelta(minutes=90)).timestamp())}'
                       f'&endTs={int((t + timedelta(minutes=90)).timestamp())}&fidelity=1', timeout=20)
        pts = [(datetime.fromtimestamp(p['t'], timezone.utc), float(p['p'])) for p in j.get('history', [])]
    except Exception as e:
        print(f'::warning::price check: Polymarket history failed: {str(e)[:120]}')
        return None
    near = [p for p in pts if abs((p[0] - t).total_seconds()) <= 1800] or ([min(pts, key=lambda p: abs((p[0] - t).total_seconds()))] if pts else [])
    if not near:
        return None
    return min(p[1] for p in near), max(p[1] for p in near), 'Polymarket price history within 30 minutes'


def items():
    """Every price Claude used since the restart: fills (trades.json) and valuations (prices.json)."""
    out = []
    for x in json.load(open(os.path.join(SRC, 'trades.json'))):
        if when(x['at']) < START or x.get('portfolio') in ('Sports',):
            continue
        px = x.get('price_usd', x.get('price_local'))
        if px is not None:
            out.append(('fill', x['at'], x.get('portfolio', ''), x['holding'], float(px), x.get('action', '')))
    for x in json.load(open(os.path.join(SRC, 'prices.json'))):
        if when(x['at']) >= START and x.get('price') is not None:
            out.append(('value', x['at'], '', x['asset'], float(x['price']), ''))
    return out


def check(kind, at, pf, holding, px, act):
    t = when(at)
    row = {'kind': kind, 'at': at, 'holding': holding, 'action': act, 'claude': px}
    if pf:
        row['portfolio'] = pf
    if holding in SKIP:
        return None
    if holding in PRED:
        rg, tol, note, sym = poly_range(holding, t), 0.03, 'tolerance 3 cents', 'Polymarket'
        absolute = True
    else:
        f = feed_for(holding)
        if not f:
            row.update(status='no_feed', note='no matching feed symbol')
            return row
        sym, how, tol, note = f
        absolute = False
        rg = feed_range(sym, t)
        if rg and how == 'inv':
            rg = (1 / rg[1], 1 / rg[0], rg[2])
    row['feed'] = sym
    if not rg:
        row.update(status='no_data', note='the feed has no data for that time')
        return row
    lo, hi, what = rg
    gap = 0.0 if lo <= px <= hi else (lo - px if px < lo else px - hi)
    rel = gap if absolute else gap / px
    row.update(feed_low=round(lo, 6), feed_high=round(hi, 6), basis=what, gap_pct=None if absolute else round(100 * rel, 3),
               gap_abs=round(gap, 4) if absolute else None, tolerance=(f'{tol * 100:.0f} cents' if absolute else f'{tol * 100:.1f}%'),
               status='ok' if rel <= tol else 'flag')
    if note:
        row['note'] = note
    return row


BACKUP_PROMPT = '''You are {label}, one of the three AIs in the Paper Trades race (Claude vs Gemini vs ChatGPT, simulated money, papertrades.ai).
An automatic price check flagged one of Claude's prices because it lies outside the price feed's range at that time.
Act as an independent BACKUP CHECK of Claude's price: look the price up yourself (search the web if you can) and judge it.

Holding: {holding} ({what})
Time Claude stated: {at}
Claude's price: {claude}
Feed ({feed}, {basis}): low {lo}, high {hi}; gap {gap}; allowed tolerance {tol}
{note}
Reply with ONLY this JSON, no other text:
{{"verdict": "claude_wrong" | "close_enough" | "feed_wrong" | "cannot_tell", "price": <the price you found for that time, or null>, "note": "<one plain-English sentence, at most 30 words>"}}'''
VERDICTS = ('claude_wrong', 'close_enough', 'feed_wrong', 'cannot_tell')


def backup_reviews(rows, limit=4):
    """Owner, Oct 30: when Claude's price check is held up by flags, Gemini and ChatGPT check each flagged price as a backup.
    Each model answers once per flagged row (row['backup'][model]); their verdicts are shown on the site and never change
    Claude's numbers (only Claude logs corrections, with a Check log entry)."""
    who = []
    for mid, r in R.RIVALS.items():
        key = os.environ.get(r['env'])
        if not key and mid == 'chatgpt' and os.environ.get('OPENROUTER_API_KEY'):
            key, r = os.environ['OPENROUTER_API_KEY'], {**r, 'pick': R.pick_openrouter, 'ask': R.ask_openrouter}
        if key:
            who.append((mid, r, key))
    asked = 0
    for row in [x for x in rows if x['status'] == 'flag']:
        for mid, r, key in who:
            if (row.get('backup') or {}).get(mid) or asked >= limit:
                continue
            asked += 1
            gap = f"{row['gap_pct']}%" if row.get('gap_pct') is not None else f"{row.get('gap_abs')}"
            prompt = BACKUP_PROMPT.format(label=r['label'], holding=row['holding'], what='a trade fill' if row['kind'] == 'fill' else 'a valuation',
                                          at=row['at'], claude=row['claude'], feed=row.get('feed'), basis=row.get('basis'), lo=row.get('feed_low'),
                                          hi=row.get('feed_high'), gap=gap, tol=row.get('tolerance'), note=('Note: ' + row['note']) if row.get('note') else '')
            try:
                picks = r['pick'](key)
                text = ''
                for model in (picks if isinstance(picks, list) else [picks]):
                    try:
                        text, _ = r['ask'](key, model, prompt)
                        break
                    except Exception as e:
                        print(f'::warning::backup check: {mid} {model} failed: {str(e)[:120]}')
                m = re.search(r'\{.*\}', text or '', re.S)
                j = json.loads(m.group(0)) if m else {}
                v = j.get('verdict') if j.get('verdict') in VERDICTS else None
                if not v:
                    continue   # no usable answer: tried again next run
                rec = {'verdict': v, 'note': str(j.get('note') or '')[:240], 'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
                if isinstance(j.get('price'), (int, float)):
                    rec['price'] = j['price']
                row.setdefault('backup', {})[mid] = rec
                print(f"::notice::backup check by {r['label']}: {row['holding']} at {row['at']}: {v}")
            except Exception as e:
                print(f'::warning::backup check by {mid} failed: {str(e)[:160]}')
    return asked


def main():
    old = {}
    try:
        for r in json.load(open(OUT)).get('rows', []):
            if r.get('status') in ('ok', 'flag'):   # settled; no_data and no_feed are tried again
                old[(r['kind'], r['at'], r['holding'])] = r
    except Exception:
        pass
    rows, new = [], 0
    for it in items():
        k = (it[0], it[1], it[3])
        if k in old:
            rows.append(old[k])
            continue
        if datetime.now(timezone.utc) - when(it[1]) < timedelta(minutes=20):   # let the feed's bars settle first
            continue
        r = check(*it)
        if r:
            rows.append(r)
            new += 1
    rows.sort(key=lambda r: (when(r['at']), r['holding']))
    flags = [r for r in rows if r['status'] == 'flag']
    for r in flags[-10:]:
        print(f"::warning::price check flag: {r['kind']} {r['holding']} at {r['at']}: Claude {r['claude']} vs feed {r.get('feed_low')}-{r.get('feed_high')}")
    before = json.dumps([r.get('backup') for r in flags], sort_keys=True)
    try:
        backup_reviews(rows)
    except Exception as e:
        print(f'::warning::backup checks failed: {str(e)[:160]}')
    if json.dumps([r.get('backup') for r in flags], sort_keys=True) != before:
        new += 1   # save the new backup verdicts
    summ = {s: sum(1 for r in rows if r['status'] == s) for s in ('ok', 'flag', 'no_data', 'no_feed')}
    summ['backup_pending'] = sum(1 for r in flags if len(r.get('backup') or {}) < 2)
    summ['backup_wrong'] = sum(1 for r in flags if any(b['verdict'] == 'claude_wrong' for b in (r.get('backup') or {}).values()))
    try:
        prev = json.load(open(OUT))
    except Exception:
        prev = {}
    if new or not prev:
        json.dump({'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'since': START.strftime('%Y-%m-%dT%H:%M:%SZ'),
                   'summary': summ, 'rows': rows}, open(OUT, 'w'), indent=1)
    print(f'::notice::price check: {new} new; totals {summ}')


def recheck():
    """Full audit, Oct 31 (read-only): re-check every settled row with the fixed bars cache, because rows checked before the fix could
    have been compared with bars from another time of day. Writes ops/review/full-audit-recheck-<time>.json; changes nothing else."""
    old = {}
    for r in json.load(open(OUT)).get('rows', []):
        old[(r['kind'], r['at'], r['holding'])] = r
    out, changed = [], []
    for it in items():
        k = (it[0], it[1], it[3])
        o = old.get(k)
        if not o or o.get('status') not in ('ok', 'flag'):
            continue
        r = check(*it) or {}
        row = {'kind': it[0], 'at': it[1], 'holding': it[3], 'claude': it[4], 'old': o.get('status'), 'new': r.get('status'),
               'old_feed': [o.get('feed_low'), o.get('feed_high')], 'new_feed': [r.get('feed_low'), r.get('feed_high')], 'basis': r.get('basis'), 'gap_pct': r.get('gap_pct'), 'tolerance': r.get('tolerance')}
        out.append(row)
        if row['old'] != row['new'] or row['old_feed'] != row['new_feed']:
            changed.append(row)
    summ = {'rows': len(out), 'status_changed': sum(1 for r in out if r['old'] != r['new']), 'feed_range_changed': len(changed),
            'now_flag': sum(1 for r in out if r['new'] == 'flag'), 'was_flag': sum(1 for r in out if r['old'] == 'flag')}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'review', 'full-audit-recheck-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M') + '.json')
    json.dump({'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'summary': summ, 'changed': changed, 'rows': out}, open(p, 'w'), indent=1)
    print('recheck', summ, 'written', p)


if __name__ == '__main__':
    recheck() if os.environ.get('PRICE_RECHECK') else main()
