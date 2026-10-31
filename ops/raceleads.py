"""The race-lead post (owner, Oct 31): "Day N of 32: who leads each race?" for Telegram, Discord and X, built from the live
standings in data.json (never typed by hand), with the All in side race ALWAYS included as its own lines (owner's rule, Oct 31).

    python3 ops/raceleads.py            # writes ops/note.txt (Telegram/Discord) and ops/x_note.json (X); prints both
    python3 ops/raceleads.py --key K    # the X post's key (default race-leads-<ET date>)

Then publish: telegram.yml mode note (also copies to Discord) and x.yml mode note.
Rules kept: each race is its own; a lead needs at least C$0.50 (US$ for China) over second place; nothing is added across races;
the side race is labelled "side race", never counted with the ten. The name is written PaperTrades.AI.
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, 'data.json')))
NAME = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
LABEL = {'Stocks': 'Stocks', 'Crypto': 'Crypto', 'China': 'China', 'Metals': 'Metals', 'Energy': 'Energy', 'Options': 'Options',
         'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports', 'Predictions': 'Predictions'}
ORDER = list(LABEL)
SIDE = {'AllInTrading': 'trading', 'AllInSports': 'sports'}
START = datetime(2026, 10, 28, tzinfo=timezone.utc)


def money(v, race):
    return ('US$' if race == 'China' else 'C$') + f'{abs(v):,.0f}'


def main():
    key = sys.argv[sys.argv.index('--key') + 1] if '--key' in sys.argv else None
    es = D['exp_standings']; es = es[0] if isinstance(es, list) else es
    leads = {m: [] for m in NAME}; best = None
    for race in ORDER:
        rows = sorted(es.get(race) or [], key=lambda r: -float(r.get('profit') or 0))
        if len(rows) > 1 and float(rows[0]['profit']) - float(rows[1]['profit']) >= 0.5 and rows[0]['id'] in leads:
            leads[rows[0]['id']].append(race)
        for r in rows:
            if best is None or float(r['profit']) > best[2]:
                best = (r['id'], race, float(r['profit']))
    # the All in side race: each AI's latest value per part
    last = {}
    for h in sorted(D.get('allin_history') or [], key=lambda x: x['at']):
        last[(h['model'], h['experiment'])] = float(h['value'])
    side = []
    for exp, nm in SIDE.items():
        rows = sorted([(m, last[(m, exp)] - 100000) for m in NAME if (m, exp) in last], key=lambda x: -x[1])
        if len(rows) > 1 and rows[0][1] - rows[1][1] >= 0.5:
            side.append((nm, rows[0][0], rows[0][1]))
    now = datetime.now(timezone(timedelta(hours=-4)) if datetime.now(timezone.utc) < datetime(2026, 11, 1, 6, tzinfo=timezone.utc) else timezone(timedelta(hours=-5)))
    day = (now.date() - datetime(2026, 10, 28).date()).days + 1
    ranked = sorted(NAME, key=lambda m: (-len(leads[m]), list(NAME).index(m)))
    lines_tg = [f'🏁 <b>Day {day} of 32: who leads each race?</b>', '']
    lines_x = [f'Day {day}/32: who leads each race? 🏁']
    for m in ranked:
        n = len(leads[m]); rs = ', '.join(LABEL[r] for r in leads[m])
        lines_tg.append(f"{NAME[m]} leads {n}" + (f': {rs}' if n else ''))
        lines_x.append(f"{NAME[m]}: {n}" + (' (' + ', '.join('Safe' if r == 'Safe' else LABEL[r] for r in leads[m]) + ')' if n else ''))
    if side:
        lines_tg += ['', '🎲 <b>Side race (All in, no limits, never counted in the ten):</b>']
        lines_tg += [f'{NAME[m]} leads All in {nm}, up {money(v, "")}' for nm, m, v in side]
        lines_x.append('Side race (All in): ' + ', '.join((f'{NAME[m]} leads {nm}' if i == 0 else f'{NAME[m]} {nm}') for i, (nm, m, v) in enumerate(side)))
    if best:
        lines_tg += ['', f'Best result in the ten races: {NAME[best[0]]} in {LABEL[best[1]]}, up {money(best[2], best[1])}.']
        lines_x.append(f'Best: {NAME[best[0]]} in {LABEL[best[1]]}, +{money(best[2], best[1])}')
    lines_tg.append('Each race is scored on its own. Pretend money, real prices. Live standings on PaperTrades.AI')
    tg, xt = '\n'.join(lines_tg), '\n'.join(lines_x)
    open(os.path.join(ROOT, 'ops', 'note.txt'), 'w').write(tg + '\n')
    k = key or f'race-leads-{now.date().isoformat()}'
    json.dump({'key': k, 'text': xt, 'link': f'https://papertrades.ai/?utm_source=x&utm_campaign={k}'},
              open(os.path.join(ROOT, 'ops', 'x_note.json'), 'w'), indent=1, ensure_ascii=False)
    print(tg); print('-----'); print(xt); print(len(xt), 'chars')


if __name__ == '__main__':
    main()
