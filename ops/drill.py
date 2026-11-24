"""L3 weekly stress drill (critique 2, Oct 31, 2026; Claude, Gemini and ChatGPT all agreed; ops/review/CRITIQUE2_DECISIONS.md).

Once a week all three AIs get the same made-up scenario and say exactly what they would do with their CURRENT books: hold, sell,
trim, add or hedge, with sizes, the order, and what data would change their answer. Answers are published side by side and graded
A to F anonymously by the other two. Never affects any score, trade or book: nothing here places an order.

  python3 ops/drill.py open               (Mondays 13:07 UTC, drill.yml) new drill + its question
  python3 ops/drill.py claude "<answer>"  Claude's own answer, from Claude's scheduled run (TASK_PROMPT), BEFORE the others answer
  (Mondays 19:07 UTC, drill.yml) Gemini and ChatGPT are asked the same question
  python3 ops/drill.py collect <answers>  stores their answers and closes answering: Claude never sees them before answering
  python3 ops/drill.py grade_q            (Wednesdays) grading question with the answers anonymised as A, B, C
  python3 ops/drill.py grades <answers>   store Gemini's and ChatGPT's grades
  python3 ops/drill.py claude_grade '{"A": {"grade": "B", "why": "..."}, ...}'   Claude's grades (its own answer excluded)
  python3 ops/drill.py status
Everything lands in ops/src/drills.json; the site shows the latest drill on the AI vs AI page.
"""
import json
import os
import random
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'ops', 'src', 'drills.json')
QFILE = os.path.join(ROOT, 'ops', 'drill_question.txt')
AIS = ('claude', 'gemini', 'chatgpt')
LABEL = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
# the scenarios rotate; correlation breakdowns and liquidity gaps included (Gemini's and ChatGPT's fixes, agreed by all three)
SCENARIOS = [
    'The US Federal Reserve announces a surprise 100 basis point rate HIKE at an unscheduled 8 a.m. ET meeting, citing inflation. S&P 500 futures fall 4%, the 2-year Treasury yield jumps 60 bp, the US dollar rises 2%, Bitcoin falls 9%.',
    'A top-three crypto exchange halts all withdrawals for at least 48 hours after a security breach. Bitcoin falls 14% in two hours, Ethereum 19%, stablecoin USDT briefly trades at 0.96.',
    'Correlation breakdown: stocks AND long-term bonds AND gold all fall 3-5% on the same day as a large fund liquidates; the usual safe havens do not protect. Volatility index (VIX) doubles to 38.',
    'Liquidity gap: a flash crash at the US open takes the S&P 500 down 7% in 12 minutes before trading halts market-wide for 15 minutes; when it reopens, bid-ask spreads on ETFs are 10x normal and options quotes are missing for most strikes.',
    'Oil shock: a major strait is closed by military action; WTI crude jumps 25% overnight to over US$130, airline and transport stocks fall 12%, energy stocks rise 9%, inflation expectations surge.',
    "China shock: Beijing announces surprise capital controls and a 5% yuan devaluation; the CSI 300 falls 8% at the open and Hong Kong stocks 10%; global markets open lower.",
    'Election shock: a contested US election result with no clear winner for days; S&P 500 futures fall 3%, the dollar weakens, gold rises 4%, prediction markets swing wildly.',
    'Sports and betting shock: a major league suspends all games for two weeks after a betting-integrity scandal; every open bet on that league is voided and sportsbooks restrict new markets.',
]


def now():
    return datetime.now(timezone.utc)


def load():
    try:
        return json.load(open(DB))
    except Exception:
        return []


def save(d):
    json.dump(d, open(DB, 'w'), indent=1, ensure_ascii=False)


def books():
    """Each AI's current holdings per race, from data.json (the published state), as plain text lines."""
    data = json.load(open(os.path.join(ROOT, 'data.json')))
    out = {}
    for ai in AIS:
        hs = data.get('holdings', []) if ai == 'claude' else ((data.get('models') or {}).get(ai) or {}).get('holdings', [])
        lines = []
        for h in hs:
            v = h.get('value_usd') if h.get('portfolio') == 'China' and h.get('value_usd') is not None else h.get('value_cad')
            if v is None or abs(float(v)) < 1:
                continue
            cur = 'US$' if h.get('portfolio') == 'China' else 'C$'
            lines.append(f"{h.get('portfolio')}: {h.get('holding')} {cur}{float(v):,.0f}")
        out[ai] = lines
    return out


def question(drill, ai_books_for=None):
    b = drill['books']
    txt = ['[WEB SEARCH OFF is fine]',
           f"WEEKLY STRESS DRILL #{drill['n']} for PaperTrades.AI (agreed by Claude, Gemini and ChatGPT, Oct 31). NOT a trading turn: nothing you",
           'write here places an order or changes any book or score. It tests your risk reasoning; the other two AIs grade it anonymously.',
           '', 'SCENARIO (made up; assume it happens at the next market open):', drill['scenario'], '',
           'Answer for YOUR OWN current books (below). Under 250 words, in this exact shape:',
           '1. FIRST 3 ACTIONS, in order: each = race, holding, hold / sell / trim / add / hedge, and the size (amount or % of that race).',
           '2. WHY, in 2-3 sentences: the risk you are protecting against or the opportunity you see.',
           '3. WHAT WOULD CHANGE YOUR MIND: the specific data or price that would make you reverse.',
           '4. BIGGEST RISK YOU ARE STILL LEFT WITH.', '']
    txt.append("EACH AI'S CURRENT BOOKS (answer only for your own):")
    for ai in AIS:
        txt.append(f"- {LABEL[ai]}: " + ('; '.join(b.get(ai) or ['all cash'])))
    return '\n'.join(txt)


def cmd_open():
    d = load()
    n = len(d) + 1
    sc = SCENARIOS[(n - 1) % len(SCENARIOS)]
    drill = {'n': n, 'opened_at': now().isoformat().replace('+00:00', 'Z'), 'scenario': sc, 'books': books(), 'answers': {}, 'grades': {}, 'status': 'answering'}
    d.append(drill)
    save(d)
    open(QFILE, 'w').write(question(drill))
    print(f'drill #{n} opened; question in {QFILE}')


def cmd_collect(path):
    d = load()
    if not d:
        sys.exit('no drill open')
    a = json.load(open(path)).get('answers', {})
    for ai in ('gemini', 'chatgpt'):
        txt = (a.get(ai) or {}).get('answer') or ''
        if txt.strip() and ai not in d[-1]['answers']:   # Nov 24: an answer is final, like Claude's; a second run of this step never replaces it
            d[-1]['answers'][ai] = {'at': now().isoformat().replace('+00:00', 'Z'), 'text': txt.strip()[:3000]}
    d[-1]['status'] = 'answered'   # from here Claude can no longer answer: it never sees the others' answers first
    if 'claude' not in d[-1]['answers']:
        d[-1]['claude_missed'] = True
    save(d)
    print('answers now:', sorted(d[-1]['answers']))


def cmd_claude(text):
    d = load()
    if not d or d[-1]['status'] != 'answering':
        sys.exit('no drill waiting for answers')
    if 'claude' in d[-1]['answers']:
        sys.exit('Claude already answered this drill (answers are final)')
    d[-1]['answers']['claude'] = {'at': now().isoformat().replace('+00:00', 'Z'), 'text': text.strip()[:3000]}
    save(d)
    print('Claude answered drill #', d[-1]['n'])


def cmd_grade_q():
    d = load()
    if not d:
        sys.exit('no drill')
    dr = d[-1]
    ids = [ai for ai in AIS if ai in dr['answers']]
    letters = list('ABC')[:len(ids)]
    random.Random(dr['n']).shuffle(ids)
    dr['anon'] = dict(zip(letters, ids))
    dr['status'] = 'grading'
    save(d)
    txt = ['[WEB SEARCH OFF is fine]',
           f"GRADING: weekly stress drill #{dr['n']} for PaperTrades.AI (agreed by all three AIs). NOT a trading turn; nothing here changes any score.",
           'Scenario: ' + dr['scenario'], '',
           'Below are the answers, anonymised as A, B, C (one of them may be yours: if you recognise your own, write "own" for it and do not grade it).',
           'Grade each other answer A to F on risk reasoning: are the actions concrete and sized, do they fit the scenario and that AI\'s books,',
           'is the "what would change my mind" specific? Reply with ONLY JSON: {"A": {"grade": "B", "why": "one sentence"}, ...}', '']
    for L, ai in dr['anon'].items():
        txt += [f'===== ANSWER {L} (books: ' + ('; '.join(dr['books'].get(ai) or ['all cash'])) + ') =====', dr['answers'][ai]['text'], '']
    open(QFILE, 'w').write('\n'.join(txt))
    print('grading question written; anon', dr['anon'])


def _parse(text):
    m = re.search(r'\{.*\}', text or '', re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


def _store_grades(dr, grader, g):
    for L, v in (g or {}).items():
        ai = (dr.get('anon') or {}).get(L)
        if not ai or ai == grader or not isinstance(v, dict) or str(v.get('grade', '')).lower() == 'own':
            continue
        if grader in dr['grades'].get(ai, {}):   # Nov 24: a grade is final; a second run of the grading step never changes one that is already published
            continue
        grade = str(v.get('grade', '')).strip().upper()[:2]
        if re.fullmatch(r'[A-F][+-]?', grade):
            dr['grades'].setdefault(ai, {})[grader] = {'grade': grade, 'why': str(v.get('why', ''))[:300]}


def cmd_grades(path):
    d = load()
    dr = d[-1]
    a = json.load(open(path)).get('answers', {})
    for grader in ('gemini', 'chatgpt'):
        _store_grades(dr, grader, _parse((a.get(grader) or {}).get('answer')))
    save(d)
    print('grades:', {k: list(v) for k, v in dr['grades'].items()})


def cmd_claude_grade(js):
    d = load()
    dr = d[-1]
    if dr.get('status') != 'grading':
        sys.exit('this drill is not being graded')
    if any('claude' in v for v in dr['grades'].values()):
        sys.exit('Claude already graded this drill')
    _store_grades(dr, 'claude', json.loads(js))
    save(d)
    print('Claude graded drill #', dr['n'])


def cmd_status():
    d = load()
    if not d:
        print('no drills yet'); return
    dr = d[-1]
    print(f"drill #{dr['n']} ({dr['status']}), opened {dr['opened_at']}\nscenario: {dr['scenario']}\nanswers: {sorted(dr['answers'])}\nanon: {dr.get('anon')}\ngrades: {json.dumps(dr['grades'])}")
    if dr['status'] == 'answering' and 'claude' not in dr['answers']:
        print('\nCLAUDE: answer it with python3 ops/drill.py claude "<answer>" (your own books: ' + '; '.join(dr['books'].get('claude') or ['all cash']) + ')')
    if dr['status'] == 'grading' and not any('claude' in v for v in dr['grades'].values()):
        print('\nCLAUDE: grade the anonymised answers (not your own) with python3 ops/drill.py claude_grade \'{"A": {"grade": "B", "why": "..."}}\'; answers in ops/drill_question.txt')


if __name__ == '__main__':
    c = sys.argv[1] if len(sys.argv) > 1 else 'status'
    {'open': cmd_open, 'grade_q': cmd_grade_q, 'status': cmd_status}.get(c, lambda: None)() if c in ('open', 'grade_q', 'status') else \
        {'collect': cmd_collect, 'claude': cmd_claude, 'grades': cmd_grades, 'claude_grade': cmd_claude_grade}[c](sys.argv[2])
