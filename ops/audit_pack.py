"""The audit pack (owner, Nov 1; Claude, Gemini and ChatGPT all agreed, ops/review/auditpack-r1.json): ONE zip with everything a
visitor needs to have their own AI (or themselves) check the race: rules, every move with its reason, every value, the feed-price
check of each fill, every correction with its reason, the exact prompts and raw replies, peer grades, the nightly SHA-256
fingerprints with a script that recomputes them, and a manifest with each file's SHA-256. Everything in it is already public on
the site; no keys, tokens, chat IDs, account or infrastructure details are included.

  build(data, out_zip)   called by build_site.py after the CSVs in data/ are written
"""
import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone

SRC = 'ops/src'

PROMPT = ('You are an independent auditor for PaperTrades.AI. Use only the attached audit-pack files; do not assume facts from the web. '
          'Verify that: trades follow the rules in rules/; fills match the recorded feed prices (checks/price_check.json); '
          'P&L and values add up (ledger/moves.csv, ledger/values.csv); every correction is disclosed with a reason and applied once '
          '(checks/corrections.json, checks/price_corrections.json); bet results match the recorded final scores; and the nightly '
          'fingerprints recompute (run fingerprints/verify.py, or follow fingerprints/HOW.md). Report pass/fail per test, discrepancies '
          'with file and row references, and any data you would need to reach a conclusion.')


def _j(name, default=None):
    try:
        return json.load(open(os.path.join(SRC, name + '.json')))
    except Exception:
        return default if default is not None else []


def build(data, out_zip, csv_dir='data'):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    files = {}
    put = lambda name, obj: files.__setitem__(name, json.dumps(obj, ensure_ascii=False, indent=1).encode('utf-8') if not isinstance(obj, (bytes, str)) else (obj.encode('utf-8') if isinstance(obj, str) else obj))
    audit = {}
    try:
        audit = json.load(open('audit.json'))
    except Exception:
        pass
    # rules
    put('rules/limits.json', data.get('rules', []))
    put('rules/rulebook.json', audit.get('rulebook', {}))
    # ledger
    for n in ('moves.csv', 'values.csv', 'prices_claude.csv', 'grades.csv'):
        p = os.path.join(csv_dir, n)
        if os.path.exists(p):
            files['ledger/' + n] = open(p, 'rb').read()
    put('ledger/open_positions.json', data.get('holdings', []))
    put('ledger/standings.json', data.get('exp_standings', {}))
    # checks and corrections
    put('checks/price_check.json', data.get('price_audit', []))
    put('checks/price_corrections.json', data.get('price_corrections', []))
    put('checks/corrections.json', audit.get('corrections', []))
    put('checks/stops_and_targets.json', data.get('stops_log', []))
    put('checks/site_changelog.json', data.get('changelog', []))
    # what each AI is told and what it answered (the latest check-in, as shown on Rules & Audit)
    put('prompts/latest_prompts_and_replies.json', audit.get('ais', {}))
    put('sources/sources.json', data.get('sources', []))
    # fingerprints: the published hashes, the raw ledger files they cover, and the script that recomputes them
    st = _j('rivals', {})
    put('fingerprints/published.json', st.get('fingerprints', []))
    put('fingerprints/raw/trades.json', _j('trades'))
    put('fingerprints/raw/bets.json', _j('bets'))
    put('fingerprints/raw/price_corrections.json', _j('price_corrections'))
    put('fingerprints/raw/rivals.json', {'trades': st.get('trades', []), 'price_corrections': st.get('price_corrections', []), 'fingerprints': st.get('fingerprints', [])})
    files['fingerprints/fingerprint.py'] = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fingerprint.py'), 'rb').read()
    files['fingerprints/verify.py'] = VERIFY.encode('utf-8')
    files['fingerprints/HOW.md'] = HOW.encode('utf-8')
    files['PROMPT.txt'] = (PROMPT + '\n').encode('utf-8')
    files['VERIFY_ME.md'] = (README.replace('{now}', now).replace('{prompt}', PROMPT)).encode('utf-8')
    manifest = {'built_at': now, 'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in sorted(files.items())}}
    files['manifest.json'] = json.dumps(manifest, indent=1).encode('utf-8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n in sorted(files):
            zi = zipfile.ZipInfo('papertrades-audit-pack/' + n, date_time=(2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, files[n])
    open(out_zip, 'wb').write(buf.getvalue())
    return len(files)


VERIFY = '''"""Recompute every published nightly fingerprint from the raw ledger files in this folder.
Run: python3 verify.py   (Python 3.8+, no extra packages)"""
import json, os, sys
from datetime import datetime
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import fingerprint as F
F.SRC = os.path.join(here, 'raw')
st = json.load(open(os.path.join(here, 'raw', 'rivals.json')))
t = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
bad = 0
for f in st['fingerprints']:
    ls = F.lines(F._j('trades'), F._j('bets'), st['trades'], t(f['close_at']), F.corrections(st))
    ok = F.digest(ls) == f['sha256']
    bad += not ok
    print(f['day'], 'OK' if ok else 'DIFFERENT', f['sha256'][:16], len(ls), 'records')
print('All fingerprints match.' if not bad else str(bad) + ' fingerprint(s) differ.')
'''

HOW = '''# How the nightly fingerprints work

Each night, about 2 hours after the daily close (00:00 UTC), the race runner takes every trade and bet of all three AIs placed
before that close, writes each as one line, sorts the lines, joins them with a newline and publishes the SHA-256 of the result
(fingerprints/published.json, also posted on the Telegram channel @PaperTradesAI at the time). If anyone later changed an earlier
record, that day's hash would no longer match.

The exact line formats are at the top of fingerprint.py (the same code the race runs). To check: run `python3 verify.py` in this
folder, or rebuild the lines by hand from raw/ and hash them with any SHA-256 tool.
'''

README = '''# PaperTrades.AI audit pack

Built {now}. Season 1: Claude, Gemini and ChatGPT trade PRETEND money at real prices, Oct 28 to Nov 28, 2026. Not financial or
betting advice. This pack is rebuilt every time the site updates; everything in it is already public on papertrades.ai.

## Check us with your own AI
Upload this zip (or the files inside) to ChatGPT, Claude, Gemini or any AI that reads files, and paste the prompt in PROMPT.txt:

> {prompt}

You can also check things yourself: the fingerprints with fingerprints/verify.py, and every file against manifest.json (SHA-256).

## What is inside
- rules/limits.json, rules/rulebook.json: every rule the AIs trade under.
- ledger/moves.csv: every trade, bet and bet result of all three AIs, with the AI's own reason, the price and the amount.
- ledger/values.csv: each AI's value in each race at every check-in.
- ledger/prices_claude.csv: the price behind each of Claude's fills.
- ledger/grades.csv: the peer grades (each AI grades the others, A to F, with one sentence).
- ledger/open_positions.json, ledger/standings.json: what each AI holds now and the standings in each race.
- checks/price_check.json: each fill and value compared with the live price feeds at that minute (ok / flagged).
- checks/price_corrections.json, checks/corrections.json: every correction, with its reason and time.
- checks/stops_and_targets.json, checks/site_changelog.json: stop and target events, and changes to the site and rules.
- prompts/latest_prompts_and_replies.json: exactly what each AI was told at its latest check-in and its raw reply.
- sources/sources.json: the news and data sources the AIs cited.
- fingerprints/: the published nightly SHA-256 fingerprints, the raw ledger files they cover, and a script that recomputes them.
- manifest.json: the SHA-256 and size of every file in this pack.

## Not included
API keys, tokens, account and infrastructure details, and full tick-by-tick price history (only the prices at the moments that
matter are included, to keep the pack small enough to upload to an AI chat).
'''
