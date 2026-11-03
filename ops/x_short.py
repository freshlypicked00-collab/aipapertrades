"""Each day's story Shorts on X too (owner, Nov 2: "Daily Shorts posting to X automatically" -> yes).

Runs right after the YouTube story step (.github/workflows/youtube.yml). Posts every story Short made in the last 36 hours that
YouTube published and X hasn't had yet: the same video, a short caption (no link in the post), and the Short's race page as the
first reply. Never posts the same Short twice (key "short-<transaction ID>"); at most 2 a run.

  python3 ops/x_short.py            post what's waiting
  python3 ops/x_short.py --dry      show what would be posted
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xpost  # noqa: E402

ROOT = os.path.dirname(HERE)
LOG = os.path.join(HERE, 'src', 'youtube.json')
PAGE = {'Sports': 'sports', 'AllInSports': 'allin', 'Predictions': 'predictions'}


def caption(meta):
    s = meta['story']
    who = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}[s['model']]
    nb = len(s.get('parts') or [1])
    o = f'+{s["odds"]}' if s['odds'] > 0 else f'−{abs(s["odds"])}'
    stake = f'C${s["stake"]:,.0f}'
    res = 'won' if s['won'] else 'lost'
    hi, lo = max(p for _, p in s['final']), min(p for _, p in s['final'])
    pnl = ('+' if s['won'] else '−') + f'C${abs(s["pnl"]):,.0f}'
    race = 'High risk side race' if s['race'] == 'AllInSports' else 'Sports betting'
    return (f'{who} bet {stake} on a {o} {"underdog" if s["odds"] > 0 else "favourite"}{f" ({nb} bets)" if nb > 1 else ""}. '
            f'It {res} {hi}-{lo}: {pnl}. {"🎯" if s["won"] else "💥"}\n\n'
            f'Claude vs Gemini vs ChatGPT, C$100,000 of pretend money each, real odds. {race}, no humans picking.\n\n'
            f'#AI #{who} #PaperTradesAI')


def main(dry=False):
    log = json.load(open(LOG))
    since = datetime.now(timezone.utc) - timedelta(hours=36)
    done = {p.get('key') for p in xpost._load()['posts']}
    n = 0
    for p in log.get('posts', []):
        if p.get('kind') != 'story' or p.get('status') != 'PUBLISHED' or not p.get('video') or not p.get('at'):
            continue
        if datetime.fromisoformat(p['at']) < since:
            continue
        key = 'short-' + p['tx']
        if key in done:
            continue
        mp4 = os.path.join(ROOT, p['video'])
        meta = json.load(open(mp4[:-4] + '.json'))
        text = caption(meta)
        link = f'Every bet, the AI’s own reason and the final score: https://papertrades.ai/?utm_source=x#{PAGE.get(meta["story"]["race"], "sports")}'
        print(key, '\n', text, '\n', link)
        if not dry:
            xpost.post_video(text, mp4, key, reply_link=link)
        n += 1
        if n >= 2:
            break
    if not n:
        print('no new story Short for X')


if __name__ == '__main__':
    main('--dry' in sys.argv)
