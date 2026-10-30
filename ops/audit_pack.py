"""Build an audit pack for an independent review by Gemini and ChatGPT (owner, Oct 30): every AI's books, bets, recent trades,
stops, betting minimums, price-check flags and fingerprints, as plain text, plus the site's visible text if given.

  python3 ops/audit_pack.py [site_text_file] > ops/review/audit-pack.md

Read-only: it never changes any data. Values use the last stored prices (no live quotes), so they match the site.
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

S = 'ops/src/'
J = lambda n, d=None: json.load(open(S + n + '.json')) if os.path.exists(S + n + '.json') else d
NOW = datetime.now(timezone.utc)
START = 100000.0
AIS = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
EXPS = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions', 'AllInTrading', 'AllInSports']


def ts(x):
    return datetime.fromisoformat(str(x).replace('Z', '+00:00')).astimezone(timezone.utc)


def et(x):
    try:
        return ts(x).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).strftime('%b %d %H:%M ET')
    except Exception:
        return str(x)


def clip(s, n=220):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 1] + '…'


r = J('rivals')
fx = r.get('fx') or {}
usdcad = float(fx.get('USDCAD') or (J('fx') or {}).get('usdcad') or 1.39)
out = []
w = out.append
w(f'# Paper Trades audit pack, generated {NOW.strftime("%Y-%m-%d %H:%M")} UTC ({et(NOW.isoformat())})')
w('Values use the last stored prices (the same ones the site shows). Times are UTC unless marked ET. Money: C$ unless marked (China in US$).')
w(f'Exchange rates stored by the race runner: {json.dumps(fx)}; Claude\'s fx.json: {json.dumps(J("fx"))}')

# ---- books
w('\n## 1. Every AI\'s books (value, cash, positions)')
hist = J('history', [])
for mid in ('claude', 'gemini', 'chatgpt'):
    w(f'\n### {AIS[mid]}')
    if mid == 'claude':
        H = J('holdings', [])
        for e in EXPS[:10]:
            rows = [x for x in H if x['portfolio'] == e]
            if not rows:
                continue
            cur = 'US$' if e == 'China' else 'C$'
            tot = sum(float(x.get('value_usd') if e == 'China' else x.get('value_cad') or 0) for x in rows)
            if e == 'Sports':   # the bankroll is the start plus settled results (minus penalties), not the cash row
                tot = START + sum(float(b.get('result_cad') or 0) for b in J('bets', []) if b.get('status') != 'Open' and b.get('placed_at') and ts(b['placed_at']) >= datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)) - sum(float(x.get('amount') or 0) for x in (r.get('claude_penalties') or []))
            last = [h for h in hist if h['portfolio'] == e]
            hv = last[-1]['value'] if last else None
            w(f'- **{e}**: value {cur}{tot:,.2f} (history {cur}{hv:,.2f} at {last[-1]["at"] if last else "-"}), profit {cur}{tot - START:,.2f}')
            for x in rows:
                w(f'  - {x["holding"]}: qty {x.get("quantity")}, entry {x.get("entry_usd", x.get("entry_local"))}, now {x.get("price_usd", x.get("price_local"))}, value {x.get("value_usd") if e == "China" else x.get("value_cad")}, priced {x.get("price_at") or x.get("as_of") or "?"}, source: {clip(x.get("price_source"), 120)}')
        for e, b in ((r.get('claude_allin') or {}).get('books') or {}).items():   # the All in side race (audit, Oct 30: it was missing)
            if e == 'AllInSports':
                val = START + sum(x['result'] for x in b.get('bets', []) if x['status'] != 'Open')
                w(f'- **{e}** (side race): value C${val:,.2f}')
                for x in b.get('bets', []):
                    w(f'  - {x["id"]}: {clip(x.get("event"), 80)} · {x.get("pick_team")} {x.get("odds")} · stake {x["stake"]} · {x["status"]} {x.get("result", "")} · final {clip(x.get("final"), 80)}')
                continue
            val = b['cash'] + sum(p['qty'] * p.get('last', p['entry']) * (usdcad if p['pcur'] == 'USD' else 1) for p in b['positions'].values())
            w(f'- **{e}** (side race): value ≈ C${val:,.2f}, cash C${b["cash"]:,.2f}')
            for k, p in b['positions'].items():
                w(f'  - {p.get("name", k)} [{k}]: qty {p["qty"]:,.4f}, entry {p["entry"]}, now {p.get("last")} {p["pcur"]}, priced {p.get("priced_at")}')
        bets = J('bets', [])
        fresh = [b for b in bets if b.get('placed_at') and ts(b['placed_at']) >= datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)]
        w(f'- **Sports bets since the restart** ({len(fresh)}):')
        for b in fresh:
            w(f'  - {b.get("bet")}: {clip(b.get("event"), 90)} · pick {b.get("pick")} · odds {b.get("odds")} · stake C${b.get("stake_cad")} · status {b.get("status")} · result C${b.get("result_cad")} · starts {b.get("starts_at")} · closing {b.get("closing_odds")}')
    else:
        m = r['models'][mid]
        for e in EXPS:
            b = m['books'].get(e)
            if not b:
                continue
            cur = 'US$' if b['cur'] == 'USD' else 'C$'
            if e in ('Sports', 'AllInSports'):
                val = START + sum(x['result'] for x in b.get('bets', []) if x['status'] != 'Open') - sum(p['amount'] for p in b.get('penalties', []))
                opn = sum(x['stake'] for x in b.get('bets', []) if x['status'] == 'Open')
                w(f'- **{e}**: value {cur}{val:,.2f} (open stakes {cur}{opn:,.2f}, penalties {[p["amount"] for p in b.get("penalties", [])]})')
                for x in b.get('bets', []):
                    legs = (' legs: ' + '; '.join(f'{l.get("pick_team")} {l.get("odds")} {l.get("status")}' for l in x['legs'])) if x.get('legs') else ''
                    w(f'  - {x["id"]}: {clip(x.get("event"), 80)} · {x.get("pick_team")} {x.get("odds")} · stake {x["stake"]} · to win {x.get("to_win")} · {x["status"]} {x.get("result", "")} · starts {x.get("starts_at")} · final {clip(x.get("final"), 80)} · closing {x.get("closing_odds")}{legs}')
                continue
            val = b['cash']
            lines = []
            for k, p in b['positions'].items():
                px = p.get('last', p['entry'])
                v = p['qty'] * px * ((usdcad if b['cur'] == 'CAD' else 1) if p['pcur'] == 'USD' else (1 / float(fx.get('USDCNY') or 7) * (usdcad if b['cur'] == 'CAD' else 1)) if p['pcur'] == 'CNY' else 1)
                val += v
                lines.append(f'  - {p.get("name", k)} [{k}]: qty {p["qty"]:,.4f}, entry {p["entry"]}, now {px} {p["pcur"]}, value {cur}{v:,.2f}, priced {p.get("priced_at")}')
            hv = [h for h in r['history'] if h['model'] == mid and h['experiment'] == e]
            w(f'- **{e}**: value ≈ {cur}{val:,.2f} (history {cur}{hv[-1]["value"]:,.2f} at {hv[-1]["at"]})' if hv else f'- **{e}**: value ≈ {cur}{val:,.2f}')
            w(f'  - cash {cur}{b["cash"]:,.2f}' + (' · BUSTED' if b.get('busted') else ''))
            out.extend(lines)
        w(f'- last run: {json.dumps(m.get("last_run"))[:600]}')
        w(f'- fail streak: {m.get("fail_streak")}')

# ---- stops
w('\n## 2. Stop and target orders held by the race runner')
for s in r.get('stops') or []:
    w(f'- {json.dumps(s)[:300]}')
w('\n### Recent stop log')
for s in (r.get('stops_log') or [])[-15:]:
    w(f'- {json.dumps(s)[:300]}')

# ---- trades in the last 48 hours
w('\n## 3. Every trade, bet and settlement in the last 48 hours (all AIs)')
cut = NOW - timedelta(hours=48)
rows = []
for t in r.get('trades', []):
    if ts(t['at']) >= cut:
        rows.append((t['at'], AIS.get(t['model'], t['model']), t['experiment'], t['action'], t.get('name') or t.get('symbol'), f'qty {t.get("qty")} @ {t.get("price")} {t.get("pcur")}', f'{t.get("cur")} {t.get("amount")}', clip(t.get('reason')), clip(t.get('wrong_if'), 120), 'void' if t.get('void') else ''))
for t in J('trades', []):
    if ts(t['at']) >= cut:
        rows.append((t['at'], 'Claude', t['portfolio'], t['action'], t['holding'], f'@ {t.get("price_usd", t.get("price_local"))}', f'C$ {t.get("cad")}' if t.get('cad') is not None else f'US$ {t.get("usd")}', clip(t.get('note') or t.get('reason')), '', t.get('filled_by', '')))
for b in J('bets', []):
    for k in ('placed_at', 'settled_at'):
        if b.get(k) and ts(b[k]) >= cut:
            rows.append((b[k], 'Claude', 'Sports', 'Bet' if k == 'placed_at' else b.get('status'), clip(b.get('event'), 70), f'pick {b.get("pick")} {b.get("odds")}', f'C$ {b.get("stake_cad") if k == "placed_at" else b.get("result_cad")}', clip(b.get('note')), '', ''))
for x in sorted(rows, key=lambda z: ts(z[0])):
    w('- ' + ' | '.join(str(v) for v in x if v != ''))

# ---- betting minimums and penalties
w('\n## 4. Betting minimums (C$3,000 every ET day from Oct 29, C$100,000 in total by Nov 28) and penalties')
sys.path.insert(0, 'ops')
try:
    import rivals as R
    for mid in ('claude', 'gemini', 'chatgpt'):
        d, tot = R.wagered(r, mid, claude=(mid == 'claude'))
        w(f'- {AIS[mid]}: wagered per ET day {d}, total C${tot:,.2f}')
except Exception as e:
    w(f'- could not compute: {e}')
w(f'- Claude penalties: {json.dumps(r.get("claude_penalties"))[:400]}')

# ---- price check
w('\n## 5. Automatic price check of Claude\'s prices (ops/src/price_audit.json): rows flagged')
pa = J('price_audit', {}) or {}
rows = pa.get('rows') if isinstance(pa, dict) else pa
flag = [x for x in (rows or []) if isinstance(x, dict) and str(x.get('status', x.get('verdict', ''))).lower() not in ('ok', 'match', 'pass', '')]
w(f'- {len(rows or [])} prices checked, {len(flag)} not OK')
for x in flag[:30]:
    w(f'  - {json.dumps(x)[:300]}')

# ---- fingerprints, takes, call-out, fact checks
w('\n## 6. Nightly ledger fingerprints')
for f in r.get('fingerprints') or []:
    w(f'- {json.dumps(f)}')
w('\n## 7. Latest takes')
tk = J('take', [])
w(f'- Claude overall: {clip(([x for x in tk if not x.get("experiment")] or [{}])[-1].get("text"), 400)}')
for mid in ('gemini', 'chatgpt'):
    t = [x for x in r.get('takes', []) if x.get('model') == mid]
    w(f'- {AIS[mid]} overall: {clip(t[-1].get("text") if t else "", 400)}')
fc = J('factcheck', []) + (r.get('factchecks') or [])
w(f'\n## 8. Fact checks: {len(fc)} in total; the last 10:')
for x in fc[-10:]:
    w(f'- {x.get("at")} {x.get("checker", "claude")} checked {x.get("model")}: {x.get("verdict")} · take: {clip(x.get("take"), 140)} · {clip(x.get("text"), 200)}')

# ---- site text
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    w('\n## 9. What the site shows (visible text of the main tabs, from a browser, cut to a few thousand characters each)')
    w(open(sys.argv[1]).read())
print('\n'.join(out))
