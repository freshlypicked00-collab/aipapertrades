"""Attach the daily write-ups to a closed ledger day.

Usage:
    python3 ops/ledger_note.py ops/src notes.json

notes.json:
    {"day": "2026-10-28",
     "All": "How the day went overall and how I think I did.",
     "Stocks": "...", "Crypto": "...", "Metals": "...", "Sports": "...", "China": "..."}

Only the portfolios given are changed. Re-running overwrites earlier notes.
"""
import json
import os
import sys

SRC, NOTES = sys.argv[1], sys.argv[2]
p = os.path.join(SRC, 'ledger.json')
ledger = json.load(open(p))
notes = json.load(open(NOTES))
day = notes.pop('day')
hit = 0
for r in ledger:
    if r['day'] == day and r['portfolio'] in notes:
        r['note'] = notes[r['portfolio']]
        hit += 1
if not hit:
    raise SystemExit(f'No ledger rows for {day}; has that day closed yet?')
json.dump(ledger, open(p, 'w'), indent=1, ensure_ascii=False)
print(f'Wrote {hit} notes for {day}. Changed data files: ledger')
