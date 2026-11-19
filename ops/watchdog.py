"""The race watchdog (owner, Nov 19: "alert me when Gemini or ChatGPT has had no finished check-in for 2 hours").

Why it exists: on Nov 18, 10:14 p.m. to Nov 19, 5:14 a.m. ET every check-in was stopped at GitHub's 30-minute job limit and nobody was
told for 8 hours. The health check that should have told the owner is the LAST step of the very run that was stopped, so it never ran;
a stopped run counts as "cancelled", not "failed", so the "last 3 runs failed" rule saw nothing; and each AI's failure count only goes
up when a check-in finishes. Nothing outside the stuck run was looking. This is: its own workflow (.github/workflows/watchdog.yml),
on its own timer, that only reads the saved records and asks one question: when did each AI last finish a check-in?

  no finished check-in for 2 hours (Gemini, ChatGPT)  -> alert
  no update for 3 hours (Claude)                      -> alert
An alert is a GitHub issue (GitHub emails the owner) and a private Telegram note to the owner through the task bot. A reminder
follows every 3 hours while it lasts; when everyone is checking in again the issue is closed and the owner is told. Nothing public.

  python3 ops/watchdog.py            (WATCHDOG_DRY=1 prints what it would do and sends nothing)
"""
import json, os, subprocess, sys
from datetime import datetime, timedelta, timezone

REPO = os.environ.get('GITHUB_REPOSITORY', 'freshlypicked00-collab/aipapertrades')
DRY = bool(os.environ.get('WATCHDOG_DRY'))
RACE_END = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)
RIVAL_LIMIT = timedelta(hours=2)
CLAUDE_LIMIT = timedelta(hours=3)
REMIND = timedelta(hours=3)
LABEL = 'race-stalled'
TITLE = 'Race stalled: an AI has not checked in'


def when(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def et(t):
    from zoneinfo import ZoneInfo
    return t.astimezone(ZoneInfo('America/New_York')).strftime('%a %b %-d, %-I:%M %p ET').replace('AM', 'a.m.').replace('PM', 'p.m.')


def ago(d):
    m = int(d.total_seconds() // 60)
    return f'{m // 60} h {m % 60} min'


def problems(state, history, now):
    """One line per AI that is overdue. Pure: the same records and clock always give the same lines."""
    out = []
    if now >= RACE_END:
        return out
    for mid, m in (state.get('models') or {}).items():
        if m.get('eliminated'):
            continue
        at = (m.get('last_run') or {}).get('at')
        if not at:
            continue
        late = now - when(at)
        if late > RIVAL_LIMIT:
            out.append(f"{m.get('label', mid)}: no finished check-in for {ago(late)} (the last one was {et(when(at))}).")
    try:
        last = max(when(x['at']) for x in history)
        if now - last > CLAUDE_LIMIT:
            out.append(f'Claude: no update for {ago(now - last)} (the last one was {et(last)}).')
    except Exception:
        pass
    return out


def gh(method, path, data=None):
    if DRY and method != 'GET':
        print(f'[dry] {method} {path}: {json.dumps(data)[:300] if data else ""}')
        return {}
    r = subprocess.run(['gh', 'api', '-X', method, path] + (['--input', '-'] if data is not None else []), input=json.dumps(data) if data is not None else None,
                       capture_output=True, text=True, timeout=60)
    if r.returncode:
        print(f'gh api {method} {path} failed: {r.stderr.strip()[:300]}')
        return None
    return json.loads(r.stdout) if r.stdout.strip() else {}


def recent_runs():
    """How the last race runs ended, for the note ("5 of the last 6 runs were stopped")."""
    try:
        runs = (gh('GET', f'repos/{REPO}/actions/workflows/rivals.yml/runs?per_page=8') or {}).get('workflow_runs') or []
        done = [r for r in runs if r.get('status') == 'completed'][:6]
        bad = [r for r in done if r.get('conclusion') in ('cancelled', 'failure', 'timed_out')]
        return f'{len(bad)} of the last {len(done)} race runs were stopped or failed.' if done and bad else ''
    except Exception:
        return ''


def tell(text):
    if DRY:
        print('[dry] Telegram note to the owner:\n' + text)
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nicole_bot
        nicole_bot.tell_owner(text)
    except Exception as e:
        print('Telegram note failed:', str(e)[:200])


def main():
    now = datetime.now(timezone.utc)
    state = json.load(open('ops/src/rivals.json'))
    try:
        history = json.load(open('ops/src/history.json'))
    except Exception:
        history = []
    probs = problems(state, history, now)
    for p in probs:
        print('-', p)
    issues = gh('GET', f'repos/{REPO}/issues?state=open&labels={LABEL}&per_page=5') or []
    issue = issues[0] if issues else None
    link = f'https://github.com/{REPO}/actions/workflows/rivals.yml'
    if probs:
        extra = recent_runs()
        body = ('\n'.join('- ' + p for p in probs) + (f'\n\n{extra}' if extra else '') +
                f'\n\nWhat to do: open {link} and look at the newest runs. If they are being stopped or are failing, tell Claude '
                '("the race is stalled") or run the workflow by hand with mode "force". Most common causes: an AI\'s API credit ran out, '
                'a key expired, or a run is stuck.\n\nThis alert closes itself when every AI is checking in again.')
        note = '🚨 <b>The race needs you</b>\n' + '\n'.join('• ' + p for p in probs) + (f'\n{extra}' if extra else '') + f'\n<a href="{link}">Open the race runs</a>'
        if not issue:
            gh('POST', f'repos/{REPO}/labels', {'name': LABEL, 'color': 'B60205', 'description': 'An AI has not finished a check-in for hours'})
            gh('POST', f'repos/{REPO}/issues', {'title': TITLE, 'labels': [LABEL], 'body': body})
            tell(note)
            print('alert opened')
        else:
            comments = gh('GET', f"repos/{REPO}/issues/{issue['number']}/comments?per_page=100") or []
            last = when(comments[-1]['created_at']) if comments else when(issue['created_at'])
            if now - last >= REMIND:
                gh('POST', f"repos/{REPO}/issues/{issue['number']}/comments", {'body': 'Still stalled.\n\n' + body})
                tell(note.replace('The race needs you', 'The race still needs you'))
                print('reminder sent')
            else:
                print('alert already open; next reminder in', ago(REMIND - (now - last)))
    elif issue:
        gh('POST', f"repos/{REPO}/issues/{issue['number']}/comments", {'body': 'Every AI is checking in again. Closing.'})
        gh('PATCH', f"repos/{REPO}/issues/{issue['number']}", {'state': 'closed'})
        tell('✅ <b>The race is running again</b>: every AI has checked in.')
        print('recovered: alert closed')
    else:
        print('all three are checking in on time' if now < RACE_END else 'the race is over: nothing to watch')


if __name__ == '__main__':
    main()
