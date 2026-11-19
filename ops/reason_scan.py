"""Reasons against their own recorded numbers (improvement pass, Nov 19): lists every trade or prediction-market move by Gemini or ChatGPT
whose written reason quotes a price, a side or an amount that differs from what was recorded for that same move. It only prints
candidates for a person or an AI to read; it never changes anything. A real contradiction gets a site-only note (ops/polish.js, 3).
  python3 ops/reason_scan.py"""
import json, re, sys
st = json.load(open('ops/src/rivals.json'))
T = [t for t in st['trades'] if t.get('action') in ('Buy', 'Sell', 'Short', 'Cover') and t.get('reason') and not str(t['reason']).startswith(('Stop order', 'Target', 'Expired', 'Market resolved'))]
print(len(T), 'runner trades with an AI reason')
num = lambda s: float(s.replace(',', ''))
hits = []
for t in T:
    r = t['reason']; px = float(t['price']); amt = float(t['amount']); exp = t['experiment']; why = []
    if t.get('outcome'):
        o = t['outcome'].lower(); other = {'yes': 'no', 'no': 'yes'}.get(o)
        if other and re.search(r"\b(buy(ing)?|bought|back(ing)?|bet(ting)? on|adding to|holding|my)\s+(the\s+)?['\"“]?%s['\"”]?\b" % other, r, re.I) and not re.search(r"['\"“]?%s['\"”]?" % o, r, re.I):
            why.append(f'side: holds {t["outcome"]}, reason speaks of {other}')
        for m_ in re.finditer(r'(\d{1,2}(?:\.\d+)?)\s*(?:¢|cents?)', r):
            c = float(m_.group(1)) / 100
            if abs(c - px) > 0.03 and abs(c - (1 - px)) > 0.03: why.append(f'cents {m_.group(0)} vs fill {px:.3f}')
        for m_ in re.finditer(r'\b(0\.\d{2,4})\b', r):
            c = float(m_.group(1))
            if abs(c - px) > 0.03 and abs(c - (1 - px)) > 0.03 and not re.search(r'(below|above|under|over|falls?|rises?|drops?)\D{0,25}' + re.escape(m_.group(1)), r, re.I): why.append(f'price {m_.group(1)} vs fill {px:.3f}')
    else:
        for m_ in re.finditer(r'(?:US\$|\$)\s?([\d,]+(?:\.\d+)?)', r):
            try: v = num(m_.group(1))
            except Exception: continue
            ctx = r[max(0, m_.start() - 40):m_.start()].lower()
            if px and 0.8 * px <= v <= 1.25 * px and abs(v / px - 1) > 0.04 and re.search(r'\b(at|near|around|price of|trading|now|current(ly)?|fill(ed)?|bought|sold|entry)\b[^.]{0,25}$', ctx) and not re.search(r'(stop|target|below|above|under|over|if|break|fall|rise|support|resistance|level)[^.]{0,30}$', ctx):
                why.append(f'price {m_.group(0)} vs fill {px:,.4g}')
    for m_ in re.finditer(r'C\$\s?([\d,]+(?:\.\d+)?)(k)?', r):
        try: v = num(m_.group(1)) * (1000 if m_.group(2) else 1)
        except Exception: continue
        ctx = r[max(0, m_.start() - 30):m_.start()].lower()
        if amt and 0.6 * amt <= v <= 1.6 * amt and abs(v / amt - 1) > 0.08 and re.search(r'(buy|sell|invest|put|deploy|allocat|stake|position of|adding|add)[^.]{0,22}$', ctx):
            why.append(f'amount {m_.group(0)} vs filled C${amt:,.0f}')
    a = t['action']; nm = (t.get('name') or '') + ' ' + t['symbol']
    inv = re.search(r'short|inverse|bear|SQQQ|SH\b|PSQ|SPXS|SDS|NVD', nm, re.I)
    if a == 'Buy' and not inv and not t.get('outcome') and re.search(r'\b(shorting|going short|short(ing)? (the |this )?(position|trade))\b', r, re.I) and not re.search(r'cover|close|exit', r, re.I): why.append('reason speaks of shorting, action is Buy')
    if a == 'Short' and re.search(r'\b(going long|buying the dip|accumulat)', r, re.I): why.append('reason speaks of buying, action is Short')
    if a == 'Sell' and re.search(r'^(buy|adding|opening|initiat)', r.strip(), re.I): why.append('reason opens with a buy, action is Sell')
    if a == 'Buy' and re.search(r'^(sell|exit|clos|taking profit|trimming)', r.strip(), re.I): why.append('reason opens with a sale, action is Buy')
    if why: hits.append((t, why))
print(len(hits), 'candidates')
for t, why in hits:
    print(f"\n[{t['at'][:16]}] {t['model']} {t['experiment']} {t['action']} {t.get('name') or t['symbol']} {('('+t['outcome']+')') if t.get('outcome') else ''} px {t['price']} amt {t['amount']} {t['cur']}\n  >> {'; '.join(why)}\n  {t['reason'][:420]}")
