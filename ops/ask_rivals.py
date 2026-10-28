"""Ask Gemini and ChatGPT for feedback (not a trading turn): reads ops/ask.txt, prints each answer as GitHub
notices (readable through the API) and saves them to ops/src/feedback.json. Nothing about their books changes."""
import json, os, sys, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R

q = open('ops/ask.txt').read().strip()
out = []
for mid, r in R.RIVALS.items():
    key = os.environ.get(r['env'])
    ask, pick = r['ask'], r['pick']
    if not key and mid == 'chatgpt' and os.environ.get('OPENROUTER_API_KEY'):
        key, ask, pick = os.environ['OPENROUTER_API_KEY'], R.ask_openrouter, R.pick_openrouter
    if not key:
        print(f'::notice title={mid}::no key'); continue
    text, err = '', ''
    for model in pick(key)[:2]:
        try:
            text, _ = ask(key, model, q)
            if text.strip():
                break
        except Exception as e:
            err = str(e)[:200]
    text = text.strip() or f'(no answer: {err})'
    out.append({'at': R.iso(), 'model': mid, 'question': q[:400], 'answer': text})
    for i, part in enumerate(textwrap.wrap(text.replace('\n', ' / '), 3500)[:6]):
        print(f'::notice title={mid} part {i + 1}::' + part.replace('%', '%25').replace('\r', ''))
try:
    old = json.load(open('ops/src/feedback.json'))
except Exception:
    old = []
json.dump(old + out, open('ops/src/feedback.json', 'w'), indent=1, ensure_ascii=False)
