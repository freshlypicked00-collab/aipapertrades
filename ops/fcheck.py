"""Claude's fact checks of ChatGPT (the loop: Gemini checks Claude, ChatGPT checks Gemini, Claude checks ChatGPT).

  python3 ops/fcheck.py todo
      lists what to check now: ChatGPT's newest overall take if it is not checked yet, and every one of its newest race takes (the
      one-sentence take per race shown on the site under that race) that states a checkable fact and is not checked yet.

For each one, append an entry to ops/src/factcheck.json: at (ET ISO, now), model "chatgpt", take_at (the take's exact "at" as listed),
experiment (only for a race take: the race name as listed), take (its text, may be shortened), verdict ("ok", "partly", "wrong",
"unverified", or "none" when it states no checkable fact: plans, opinions or its own holdings; "none" is stored but never shown),
text (one or two neutral sentences with the correct fact; "" for "none"), source (a URL; "" for "none").
The site shows a check only under the exact take it is about (same AI, same take, same race).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R  # noqa: E402

if __name__ == '__main__':
    st = json.load(open('ops/src/rivals.json'))
    try:
        mine = json.load(open('ops/src/factcheck.json'))
    except Exception:
        mine = []
    st_view = {'thoughts': st.get('thoughts', []), 'factchecks': [x for x in mine if x.get('model') == 'chatgpt']}
    done = {x.get('take_at') for x in mine if x.get('model') == 'chatgpt' and not x.get('experiment')}
    takes = [x for x in st.get('takes', []) if x.get('model') == 'chatgpt']
    if takes:
        t = max(takes, key=lambda x: x['at'])
        print('OVERALL TAKE' + (' (already checked)' if t['at'] in done else ' (check it)') + f": take_at {t['at']}\n  \"{t['text']}\"")
    races = R.race_takes_to_check(st_view, 'chatgpt')
    print(f'RACE TAKES TO CHECK ({len(races)}):' if races else 'RACE TAKES: none with a checkable fact waiting.')
    for e, x in races:
        print(f"  experiment {e}, take_at {x['at']}\n    \"{x['text']}\"")
