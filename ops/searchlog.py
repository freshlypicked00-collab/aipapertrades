"""Search source ledger (owner's proposal, Oct 30; Claude, Gemini and ChatGPT all agreed: ops/review/searchlog-r1-oct30.json).

For every check-in of every AI, permanently: the time, the AI, its search queries (up to 10), the links it used (title + URL,
up to 10) and how many searches it made. Links only, never the text of a page. For transparency, not scoring.

Where it is kept:
  - Gemini and ChatGPT: rivals.json "search_log" (written by rivals.py at each check-in; the last 4 days are kept there)
  - Claude: ops/src/claude_searches.json, one entry per run:  python3 ops/searchlog.py add '{"queries": [...], "links": [{"title": ..., "url": ...}], "searches": 7}'
  - Public: searchlog/<UTC day>.json, built by build_site.py from both. A closed day's file is written once and never changed;
    its SHA-256 goes into that day's nightly fingerprint (fingerprint.py), next to the trades-and-bets fingerprint.
Started Oct 31, 2026 (00:00 UTC). Earlier check-ins can't be rebuilt.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

START = datetime(2026, 10, 31, tzinfo=timezone.utc)
CLAUDE = 'ops/src/claude_searches.json'
OUT = 'searchlog'
MAXQ, MAXL = 10, 10
KEEP_DAYS = 4   # rivals.json keeps this many days; older days are already frozen in searchlog/
# query parameters that track people or carry secrets: dropped from every link (ChatGPT's risk point: no sensitive details kept forever)
DROP = re.compile(r'^(utm_.*|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|igshid|_hs.*|ref|ref_src|.*token.*|.*key.*|sig|signature|auth.*|session.*|sid|email|e|user.*|uid)$', re.I)


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _t(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def clean_url(u):
    u = str(u or '').strip()
    if not re.match(r'^https?://', u, re.I):
        return None
    p = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=False) if not DROP.match(k)]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, urlencode(q), ''))


def entry(model, at, queries, links, searches=None, status=None):
    qs, seen = [], set()
    for q in queries or []:
        q = re.sub(r'\s+', ' ', str(q)).strip()[:200]
        if q and q.lower() not in seen:
            seen.add(q.lower()); qs.append(q)
    ls, seenu = [], set()
    for l in links or []:
        u = clean_url(l.get('url') if isinstance(l, dict) else l)
        if not u or u in seenu:
            continue
        seenu.add(u)
        title = re.sub(r'\s+', ' ', str((l.get('title') if isinstance(l, dict) else '') or '')).strip()[:160]
        ls.append({'title': title or urlsplit(u).netloc, 'url': u})
    e = {'at': at, 'model': model, 'queries': qs[:MAXQ], 'links': ls[:MAXL], 'searches': searches if isinstance(searches, int) else len(qs)}
    if status and status != 'ok':
        e['status'] = status
    return e


def add_rival(state, model, at, search_log_items, sources, searched, status='ok'):
    """rivals.py, once per check-in of Gemini or ChatGPT."""
    if _t(at) < START:
        return
    qs = []
    for s in search_log_items or []:
        qs += s.get('queries') or []
    log = state.setdefault('search_log', [])
    log.append(entry(model, at, qs, sources, searched, status))
    cut = _iso(datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS))
    state['search_log'] = [x for x in log if x['at'] >= cut]


def _claude():
    try:
        return json.load(open(CLAUDE))
    except Exception:
        return []


def day_entries(day, state):
    """Every recorded check-in whose time falls on this UTC day, all three AIs, oldest first."""
    rows = [x for x in (state.get('search_log') or []) + _claude() if x.get('at', '')[:10] == day]
    return sorted(rows, key=lambda x: (x['at'], x['model']))


def payload(day, rows):
    """The exact bytes of a day's public file (the fingerprint hashes these)."""
    doc = {'day': day, 'note': 'Search source ledger: each AI check-in, its search queries and the links it used (links only). '
                               'Recorded from Oct 31, 2026, 00:00 UTC (Oct 30, 8 p.m. ET). For transparency, not scoring.', 'checkins': rows}
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def write_public(state, now=None):
    """build_site.py: a day's file is rewritten at each build until that day's nightly fingerprint is published; then it is frozen."""
    now = now or datetime.now(timezone.utc)
    os.makedirs(OUT, exist_ok=True)
    today = now.date().isoformat()
    days = sorted({x['at'][:10] for x in (state.get('search_log') or []) + _claude() if x.get('at', '') >= _iso(START)})
    written = []
    frozen = {f['day'] for f in state.get('fingerprints', []) if f.get('search_sha256')}
    for day in days:
        path = os.path.join(OUT, day + '.json')
        if day in frozen and os.path.exists(path):
            continue   # fingerprinted: never changed again
        data = payload(day, day_entries(day, state))
        old = open(path, 'rb').read() if os.path.exists(path) else None
        if old != data:
            open(path, 'wb').write(data); written.append(day)
    idx = sorted(f[:-5] for f in os.listdir(OUT) if re.match(r'^\d{4}-\d{2}-\d{2}\.json$', f))
    ib = (json.dumps({'days': idx, 'start': START.date().isoformat()}, separators=(',', ':')) + '\n').encode()
    ip = os.path.join(OUT, 'index.json')
    if not os.path.exists(ip) or open(ip, 'rb').read() != ib:
        open(ip, 'wb').write(ib)
    return written


def freeze(day, state):
    """fingerprint.py, once, 2 hours after the day's close: write the day's final file and return its SHA-256 and check-in count."""
    if day < START.date().isoformat():
        return None, 0
    rows = day_entries(day, state)
    data = payload(day, rows)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, day + '.json'), 'wb').write(data)
    return hashlib.sha256(data).hexdigest(), len(rows)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'add':   # Claude, once per run
        d = json.loads(sys.argv[2])
        at = d.get('at') or _iso(datetime.now(timezone.utc))
        if _t(at) < START:
            sys.exit('the search ledger starts Oct 31, 2026 (00:00 UTC)')
        e = entry('claude', at, d.get('queries'), d.get('links'), d.get('searches'))
        if not e['queries'] and not e['links']:
            sys.exit('nothing to record: give the queries you searched and the links you used')
        rows = _claude(); rows.append(e)
        json.dump(rows, open(CLAUDE, 'w'), ensure_ascii=False, indent=0)
        print(f"recorded: {len(e['queries'])} queries, {len(e['links'])} links at {e['at']}")
    elif len(sys.argv) >= 2 and sys.argv[1] == 'check':   # re-hash every frozen day file against the published fingerprints
        st = json.load(open('ops/src/rivals.json'))
        for f in st.get('fingerprints', []):
            if f.get('search_sha256'):
                h = hashlib.sha256(open(os.path.join(OUT, f['day'] + '.json'), 'rb').read()).hexdigest()
                print(f['day'], 'OK' if h == f['search_sha256'] else 'CHANGED')
    else:
        print(__doc__)
