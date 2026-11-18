"""Health alerts as ONE GitHub issue, which emails the owner (and anyone watching the repo).

Owner, Nov 18: the Oct 30 alert issue (an Instagram error) was never closed, and the old step skipped every later alert with
"a health issue is already open". So ChatGPT ran out of OpenRouter credit on Nov 3, Nov 12 and Nov 16 and no email went out;
it missed whole days and was fined for the missed betting minimums. Now:
- problems and no open alert issue: open one (email);
- problems and an open issue: add a comment when a NEW problem appears, and a reminder every 12 hours while one lasts (email);
- no problems for 2 hours: close the open issue, so the next problem opens a fresh one.

Usage: python3 ops/health_issue.py /tmp/alert.txt   (lines starting with "- " are the problems; HEALTH_DRY=1 prints instead of posting)
"""
import json, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone

REPO = os.environ.get('GITHUB_REPOSITORY', 'freshlypicked00-collab/aipapertrades')
DRY = bool(os.environ.get('HEALTH_DRY'))
NOW = datetime.now(timezone.utc)
TITLE = 'Paper Trades needs attention'
MARK = re.compile(r'<!-- health-keys: (.*?) -->', re.S)
REMIND = timedelta(hours=12)
QUIET = timedelta(hours=2)
FOOT = ("Most likely causes: API credit ran out (OpenRouter for ChatGPT, Google billing for Gemini), a key expired, or Claude's "
        "scheduled tasks are paused. Fix it and the next run recovers on its own. This issue closes itself once everything has "
        "been fine for 2 hours, so the next problem opens a new one.")


def key(line):
    """The same problem keeps the same key from run to run: only its numbers change (streaks, hours, balances, times)."""
    return re.sub(r'\d+', '#', line.strip())[:80]


def marker(keys):
    return '<!-- health-keys: ' + json.dumps(sorted(keys)) + ' -->'


def gh(method, path, data=None):
    if DRY and method != 'GET':
        print(f'[dry] {method} {path}: {json.dumps(data)[:300] if data else ""}')
        return {}
    cmd = ['gh', 'api', '-X', method, path]
    if data is not None:
        cmd += ['--input', '-']
    r = subprocess.run(cmd, input=json.dumps(data) if data is not None else None, capture_output=True, text=True)
    if r.returncode:
        print(f'gh api {method} {path} failed: {r.stderr.strip()[:300]}')
        return None
    return json.loads(r.stdout) if r.stdout.strip() else {}


def when(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def last_notice(issue):
    """(keys, time) of the latest alert posted on the issue: its newest comment with a marker, else the issue body."""
    keys, at = None, when(issue['created_at'])
    m = MARK.search(issue.get('body') or '')
    if m:
        keys = set(json.loads(m.group(1)))
    comments = gh('GET', f"repos/{REPO}/issues/{issue['number']}/comments?per_page=100") or []
    for c in comments:
        m = MARK.search(c.get('body') or '')
        if m:
            keys, at = set(json.loads(m.group(1))), when(c['created_at'])
    return keys, at


SEEN = re.compile(r'<!-- health-seen: (\S+) -->')


def mark_seen(issue):
    """Note in the issue body (an edit sends no email) when a problem was last seen, so 'closes after 2 quiet hours' is measured
    from the last bad check, not from the last email."""
    body = SEEN.sub('', issue.get('body') or '').rstrip() + f"\n<!-- health-seen: {NOW.strftime('%Y-%m-%dT%H:%M:%SZ')} -->"
    gh('PATCH', f"repos/{REPO}/issues/{issue['number']}", {'body': body})


def main(path):
    lines = [l.rstrip() for l in open(path) if l.startswith('- ')] if os.path.exists(path) else []
    keys = {key(l) for l in lines}
    issues = [i for i in (gh('GET', f'repos/{REPO}/issues?state=open&labels=health&per_page=20') or []) if 'pull_request' not in i]
    issue = min(issues, key=lambda i: i['number']) if issues else None
    text = '\n'.join(lines)
    if not lines:
        if issue:
            _, at = last_notice(issue)
            m = SEEN.search(issue.get('body') or '')
            at = max(at, when(m.group(1))) if m else at
            if NOW - at >= QUIET:
                gh('POST', f"repos/{REPO}/issues/{issue['number']}/comments", {'body': 'All clear: every check passed for 2 hours. Closing; the next problem opens a new issue.'})
                gh('PATCH', f"repos/{REPO}/issues/{issue['number']}", {'state': 'closed'})
                print(f"closed health issue #{issue['number']}")
        return
    if not issue:
        subprocess.run(['gh', 'label', 'create', 'health', '-R', REPO, '--color', 'B60205', '--description', 'Automatic health alerts'],
                       capture_output=True) if not DRY else None
        r = gh('POST', f'repos/{REPO}/issues', {'title': TITLE, 'labels': ['health'], 'body': f'{text}\n\n{FOOT}\n\n{marker(keys)}'})
        print('opened a health issue', (r or {}).get('number', ''))
        return
    mark_seen(issue)
    old, at = last_notice(issue)
    new = keys - (old or set())
    if new or NOW - at >= REMIND:
        head = 'New problem:' if new else 'Still not fixed (reminder every 12 hours while a problem lasts):'
        gh('POST', f"repos/{REPO}/issues/{issue['number']}/comments", {'body': f'{head}\n\n{text}\n\n{marker(keys)}'})
        print(f"commented on health issue #{issue['number']}: {head}")
    else:
        print(f"health issue #{issue['number']} already reports these problems (last notice {at:%b %d %H:%M} UTC)")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/alert.txt')
