"""Ask Gemini and ChatGPT a question that is NOT a trading turn (feedback, code review); nothing in their books changes.

- ops/ask.txt: the question. ops/ask_files.txt (optional): repo files to attach, one path per line.
- First runs a short live diagnostic of each AI's web search and the OpenRouter credit left, saved to ops/review/diag.json.
- The answers are saved to ops/review/<ASK_NAME or 'answers'>.json (committed by the workflow) and printed as notices.
Both AIs are asked at the same time, so a long review fits in the job's time limit.
"""
import json, os, sys, textwrap, threading, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rivals as R

R.MODEL_TIMEOUT = 900   # a long review can take several minutes
NAME = os.environ.get('ASK_NAME') or 'answers'
os.makedirs('ops/review', exist_ok=True)


def keys():
    out = {}
    if os.environ.get('GEMINI_API_KEY'):
        out['gemini'] = ('gemini', os.environ['GEMINI_API_KEY'])
    if os.environ.get('OPENAI_API_KEY'):
        out['chatgpt'] = ('openai', os.environ['OPENAI_API_KEY'])
    elif os.environ.get('OPENROUTER_API_KEY'):
        out['chatgpt'] = ('openrouter', os.environ['OPENROUTER_API_KEY'])
    return out


def gemini(key, model, prompt, search):
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}]}
    if search:
        body['tools'] = [{'google_search': {}}]
    j = R.get_json(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
                   {'Content-Type': 'application/json'}, json.dumps(body).encode(), timeout=R.MODEL_TIMEOUT)
    cand = j['candidates'][0]
    gm = cand.get('groundingMetadata') or {}
    text = ''.join(p.get('text', '') for p in cand.get('content', {}).get('parts', []))
    return text, {'queries': gm.get('webSearchQueries', []), 'chunks': len(gm.get('groundingChunks', [])),
                  'finish': cand.get('finishReason'), 'usage': j.get('usageMetadata')}


def openrouter(key, model, prompt, variant='plugin', effort=None):
    hdr = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'HTTP-Referer': R.SITE, 'X-Title': 'Paper Trades'}
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt}]}
    if variant == 'plugin':
        body['plugins'] = [{'id': 'web', 'max_results': 6}]
    elif variant == 'online':
        body['model'] = model + ':online'
    elif variant == 'options':
        body['web_search_options'] = {'search_context_size': 'medium'}
    if effort:
        body['reasoning'] = {'effort': effort}
    j = R.get_json('https://openrouter.ai/api/v1/chat/completions', hdr, json.dumps(body).encode(), timeout=R.MODEL_TIMEOUT)
    msg = j['choices'][0]['message']
    ann = msg.get('annotations') or []
    return msg.get('content') or '', {'annotations': len(ann), 'urls': [a.get('url_citation', {}).get('url') for a in ann][:5],
                                      'usage': j.get('usage'), 'model': j.get('model'), 'provider': j.get('provider')}


def openai(key, model, prompt, search=True):
    body = {'model': model, 'input': prompt}
    if search:
        body['tools'] = [{'type': 'web_search'}]
    j = R.get_json('https://api.openai.com/v1/responses', {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                   json.dumps(body).encode(), timeout=R.MODEL_TIMEOUT)
    out, urls, calls = [], [], 0
    for item in j.get('output', []):
        if item.get('type') == 'web_search_call':
            calls += 1
        for c in item.get('content', []) or []:
            if c.get('type') == 'output_text':
                out.append(c['text'])
                urls += [a.get('url') for a in c.get('annotations', []) or [] if a.get('url')]
    return '\n'.join(out), {'search_calls': calls, 'urls': urls[:5], 'usage': j.get('usage')}


def err(e):
    if isinstance(e, urllib.error.HTTPError):
        try:
            return f'HTTP {e.code}: ' + e.read().decode()[:400]
        except Exception:
            return f'HTTP {e.code}'
    return f'{type(e).__name__}: {str(e)[:300]}'


K = keys()
ONLY = [x.strip() for x in (os.environ.get('ASK_ONLY') or '').split(',') if x.strip()]
if ONLY:   # e.g. ASK_ONLY=gemini: ask just that AI (saves the other's credit)
    K = {k: v for k, v in K.items() if k in ONLY}
MODELS = {}
if 'gemini' in K:
    try:
        MODELS['gemini'] = R.pick_gemini(K['gemini'][1])[0]
    except Exception as e:
        MODELS['gemini'] = 'gemini-2.5-pro'
if 'chatgpt' in K:
    kind, key = K['chatgpt']
    try:
        MODELS['chatgpt'] = (R.pick_openrouter(key)[0] if kind == 'openrouter' else R.pick_openai(key))
    except Exception:
        MODELS['chatgpt'] = 'openai/gpt-5' if kind == 'openrouter' else 'gpt-5'

# ---- 1. live diagnostic: does each AI really search the web, and how much OpenRouter credit is left?
DQ = ('Use a web search now. What is the latest Brent crude oil price and the time of that quote, and what is one top business headline '
      'from today? Reply in 2 short lines and give the URL of each page you used.')
diag = {'at': R.iso(), 'models': MODELS}
TEST_SEARCH = bool(os.environ.get('ASK_DIAG'))   # the live search test costs credit; the credit balance check is free
if 'gemini' in K and TEST_SEARCH:
    try:
        t, meta = gemini(K['gemini'][1], MODELS['gemini'], DQ, True)
        diag['gemini_search'] = {'reply': t[:500], **meta}
    except Exception as e:
        diag['gemini_search'] = {'error': err(e)}
if 'chatgpt' in K:
    kind, key = K['chatgpt']
    if kind == 'openrouter':
        for v in (('plugin', 'options', 'online') if TEST_SEARCH else ()):
            try:
                t, meta = openrouter(key, MODELS['chatgpt'], DQ, v)
                diag['chatgpt_search_' + v] = {'reply': t[:500], **meta}
            except Exception as e:
                diag['chatgpt_search_' + v] = {'error': err(e)}
        for path in ('credits', 'key'):
            try:
                diag['openrouter_' + path] = R.get_json(f'https://openrouter.ai/api/v1/{path}', {'Authorization': f'Bearer {key}'})
            except Exception as e:
                diag['openrouter_' + path] = {'error': err(e)}
    elif TEST_SEARCH:
        try:
            t, meta = openai(key, MODELS['chatgpt'], DQ)
            diag['chatgpt_search_openai'] = {'reply': t[:500], **meta}
        except Exception as e:
            diag['chatgpt_search_openai'] = {'error': err(e)}
json.dump(diag, open('ops/review/diag.json', 'w'), indent=1, ensure_ascii=False)
print('::notice title=diag::' + json.dumps({k: (v if not isinstance(v, dict) else {x: v[x] for x in v if x in ('queries', 'chunks', 'annotations', 'search_calls', 'error', 'urls', 'data')}) for k, v in diag.items()})[:3800])

# ---- 2. the question, with the attached files
q = open('ops/ask.txt').read().strip()
SEARCH = q.startswith('[WEB SEARCH ON]')   # an audit that must check prices and results online (owner, Oct 30); off by default
if SEARCH:
    q = q[len('[WEB SEARCH ON]'):].strip()
files = []
if os.path.exists('ops/ask_files.txt'):
    files = [x.strip() for x in open('ops/ask_files.txt') if x.strip() and not x.startswith('#')]
for f in files:
    try:
        q += f'\n\n===== FILE: {f} =====\n' + open(f).read()
    except Exception as e:
        q += f'\n\n===== FILE: {f} (could not be read: {e}) ====='
# Every question starts with today's date (owner, Oct 30): Gemini once "corrected" the race year to 2024 because ask mode, unlike the
# trading check-ins, never told the AIs the date. The date line comes from the runner's clock, so no AI has to guess it.
from datetime import datetime as _dt
from zoneinfo import ZoneInfo as _ZI
_now = _dt.now(_ZI('America/New_York'))
q = (f"TODAY'S DATE (from the race runner's clock, authoritative): {_now.strftime('%A %B %-d, %Y, %-I:%M %p')} ET. "
     "Season 1 of PaperTrades.AI runs Oct 28 to Nov 28, 2026. Dates and years written in this question are correct; do not change them. "
     "If something conflicts with what you remember, trust this date and say what you are unsure of instead of guessing.\n\n") + q
print(f'question: {len(q):,} characters, {len(files)} files')

answers = {}


def run(mid):
    kind, key = K[mid]
    model = MODELS[mid]
    try:
        if mid == 'gemini':
            text, meta = gemini(key, model, q, SEARCH)
        elif kind == 'openrouter':
            text, meta = openrouter(key, model, q, 'plugin' if SEARCH else 'none', 'high')
        else:
            text, meta = openai(key, model, q, SEARCH)
        answers[mid] = {'model': model, 'answer': text, 'meta': meta}
    except Exception as e:
        answers[mid] = {'model': model, 'answer': '', 'error': err(e)}


threads = [threading.Thread(target=run, args=(m,)) for m in K]
for t in threads:
    t.start()
for t in threads:
    t.join()
out = {'at': R.iso(), 'question': open('ops/ask.txt').read().strip(), 'files': files, 'answers': answers}
json.dump(out, open(f'ops/review/{NAME}.json', 'w'), indent=1, ensure_ascii=False)
for mid, a in answers.items():
    head = a.get('error') or a['answer']
    print(f'::notice title={mid}::' + head[:3500].replace('\n', ' / ').replace('%', '%25').replace('\r', ''))
