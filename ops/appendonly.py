"""R5 of the root-cause vote (Oct 31; all three AIs agreed, ChatGPT's amendment included): append-only enforcement.

At the start of every race-runner run, the record on main is compared with the last commit this check verified (ops/src/integrity.json):
  - no existing trade, bet, result, take, fact check, peer grade or Claude log entry may change or disappear (new rows are fine;
    bets may settle: only their placement must stay the same; the runner's own transaction ids may be added);
  - nobody but the race runner (paper-trades-bot) may touch Gemini's and ChatGPT's record (ops/src/rivals.json).
Anything found opens an "Integrity alert" issue at once (the owner gets it by email and on the GitHub app). The check never changes the
record; it only reports. Old versions are read through the GitHub API, so the run stays a shallow checkout.
Usage (in rivals.yml, with GH_TOKEN): python3 ops/appendonly.py            -> check and write the new verified commit to integrity.json
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.environ.get('GITHUB_REPOSITORY', 'freshlypicked00-collab/aipapertrades')
STATE = 'ops/src/integrity.json'
BOT = 'paper-trades-bot'


def gh(*args, raw=False):
    cmd = ['gh', 'api'] + (['-H', 'Accept: application/vnd.github.raw'] if raw else []) + list(args)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300])
    return out.stdout if raw else json.loads(out.stdout)


def old(path, sha):
    try:
        return json.loads(gh(f'repos/{REPO}/contents/{path}?ref={sha}', raw=True))
    except Exception:
        return None


def rows(data, key=None):
    return (data or {}).get(key, []) if key else (data or [])


def key_of(r, fields):
    return json.dumps([r.get(f) for f in fields], sort_keys=True, ensure_ascii=False)


# (file, list key or None, identity fields, fields that must never change)
RULES = [
    ('ops/src/rivals.json', 'trades', ('model', 'at', 'experiment', 'action', 'symbol', 'bet'), ('price', 'qty', 'amount', 'reason', 'odds', 'pick', 'stake')),
    ('ops/src/rivals.json', 'takes', ('model', 'at'), ('text',)),
    ('ops/src/rivals.json', 'factchecks', ('checker', 'model', 'take_at', 'experiment'), ('verdict', 'text', 'source')),
    ('ops/src/rivals.json', 'peer_grades', ('grader', 'key', 'at'), ('grade', 'text')),
    ('ops/src/trades.json', None, ('at', 'portfolio', 'holding', 'action'), ('price_usd', 'price_local', 'cad', 'usd', 'shares')),
    ('ops/src/bets.json', None, ('bet',), ('placed_at', 'pick', 'odds', 'stake_cad', 'event')),
    ('ops/src/log.json', None, ('at', 'portfolio', 'action'), ('detail',)),
    ('ops/src/take.json', None, ('at', 'experiment'), ('text',)),
    ('ops/src/claude_grades.json', None, ('key',), ('grade', 'text')),
]


def compare(base, head_files):
    problems = []
    cache = {}
    for path, lk, ident, fixed in RULES:
        if path not in cache:
            cache[path] = (old(path, base), head_files(path))
        before, after = cache[path]
        if before is None or after is None:
            continue
        b, a = rows(before, lk), rows(after, lk)
        now = {}
        for r in a:
            now.setdefault(key_of(r, ident), []).append(r)
        for r in b:
            k = key_of(r, ident)
            if not now.get(k):
                problems.append(f'{path}{"[" + lk + "]" if lk else ""}: a row disappeared: {k[:160]}')
                continue
            if not any(all(x.get(f) == r.get(f) for f in fixed) for x in now[k]):
                diff = {f: (r.get(f), now[k][0].get(f)) for f in fixed if now[k][0].get(f) != r.get(f)}
                problems.append(f'{path}{"[" + lk + "]" if lk else ""}: a row changed: {k[:120]} {json.dumps(diff, ensure_ascii=False)[:240]}')
    return problems


def authors(base, head):
    """Commits between base and head that touched rivals.json, by anyone but the runner."""
    try:
        cmp = gh(f'repos/{REPO}/compare/{base}...{head}')
    except Exception as e:
        return [f'could not list the commits since {base[:7]}: {e}']
    out = []
    for c in cmp.get('commits', []):
        name = (c.get('commit') or {}).get('author', {}).get('name', '')
        if name == BOT:
            continue
        try:
            files = [f['filename'] for f in gh(f"repos/{REPO}/commits/{c['sha']}").get('files', [])]
        except Exception:
            files = []
        if 'ops/src/rivals.json' in files:
            out.append(f"Gemini's and ChatGPT's record (rivals.json) was changed by {name}, not the race runner: commit {c['sha'][:7]} \"{(c.get('commit') or {}).get('message', '').splitlines()[0][:100]}\"")
    return out


def main():
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    base = st.get('checked_sha')
    if not base or base == head:
        st.update(checked_sha=head, at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        json.dump(st, open(STATE, 'w'), indent=1)
        print('integrity: nothing new to check' if base else 'integrity: first run, baseline set')
        return
    problems = compare(base, lambda p: json.load(open(p)) if os.path.exists(p) else None) + authors(base, head)
    st.update(checked_sha=head, at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), last_problems=problems[:20])
    json.dump(st, open(STATE, 'w'), indent=1)
    if not problems:
        print(f'integrity: {base[:7]}..{head[:7]} append-only, ok')
        return
    print('::warning::integrity: ' + ' | '.join(problems[:5]))
    body = (f'The append-only check (root-cause vote R5, Oct 31) found changes to the past record between {base[:7]} and {head[:7]}:\n\n'
            + '\n'.join('- ' + p for p in problems[:40])
            + '\n\nNothing was changed by this check. If a change was an approved correction, it must also be in ops/src/corrections.json and announced on Telegram; otherwise restore the record from the earlier commit.')
    subprocess.run(['gh', 'label', 'create', 'integrity', '--color', 'B60205', '--description', 'Past record changed'], capture_output=True)
    subprocess.run(['gh', 'issue', 'create', '--title', f'Integrity alert: past record changed ({head[:7]})', '--label', 'integrity', '--body', body], capture_output=True)


if __name__ == '__main__':
    main()
