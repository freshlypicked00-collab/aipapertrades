"""Email Nicole a manual-post task (owner, Oct 31): whenever Claude, Gemini or ChatGPT want something posted where the bot
can't post (Instagram, TikTok, Reddit, Hacker News, Facebook...), Nicole does it by hand.

How it reaches her: this runs inside GitHub Actions as github-actions[bot] and comments on the open issue
"Tasks for Nicole (manual posts)". GitHub emails the owner's notifications to Nicole (default notifications email,
set Oct 31), so every task arrives in her inbox. Images must be public papertrades.ai URLs (social/nicole/...).

Usage: python3 ops/nicole.py ops/nicole/<task>.md      (the file's first line is the title)
"""
import json, os, subprocess, sys

REPO = os.environ.get('GITHUB_REPOSITORY', 'freshlypicked00-collab/aipapertrades')
TITLE = '📬 Tasks for Nicole (manual posts)'
INTRO = ("Hi Nicole! Every time PaperTrades.AI needs a post somewhere the bot can't post (Instagram, Reddit, Hacker News, TikTok...), "
         "the task arrives here as a new comment, and GitHub emails it to you. Do each task as written, then reply to the owner "
         "with a screenshot. Questions? Ask the owner.\n\nRules for every post: write the name as **PaperTrades.AI**; it's pretend money, "
         "never investment or betting advice; we're not connected to papertrade.xyz, Anthropic, Google or OpenAI.")


def gh(*a):
    return subprocess.run(['gh', *a], check=True, capture_output=True, text=True).stdout


def issue():
    for i in json.loads(gh('api', f'repos/{REPO}/issues?state=open&per_page=100')):
        if i.get('title') == TITLE and not i.get('pull_request'):
            return i['number']
    return json.loads(gh('api', '-X', 'POST', f'repos/{REPO}/issues', '-f', f'title={TITLE}', '-f', f'body={INTRO}'))['number']


if __name__ == '__main__':
    path = sys.argv[1]
    text = open(path).read().strip()
    n = issue()
    gh('api', '-X', 'POST', f'repos/{REPO}/issues/{n}/comments', '-f', f'body={text}')
    sent = 'ops/nicole/sent.json'
    log = json.load(open(sent)) if os.path.exists(sent) else []
    log.append({'file': os.path.basename(path), 'issue': n})
    json.dump(log, open(sent, 'w'), indent=1)
    print(f'::notice title=Nicole::task sent (issue #{n})')
