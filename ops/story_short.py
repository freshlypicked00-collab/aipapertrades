"""Story Shorts: one real bet, told so a stranger understands it (owner, Oct 31: the first automatic Short was "slop": it did not
say who we are, what was bet on, or the score). The standard S1-S10 was agreed by all three AIs: ops/review/social-standard-oct31.json.

Every Short:
  S1  the premise in the first 2 seconds (3 AIs, C$100,000 of pretend money each, real prices)
  S2  ONE concrete story: a specific bet, never an abstract chart
  S3  hook -> the bet (AI, team, odds, stake) -> the AI's own reason, quoted from the ledger -> the final score -> the money -> the race
  S5  big text inside the phone safe zone, a persistent score bug (race, day, pretend money), nothing important bottom or right
  S6  every fact read from data.json (the public ledger), transaction IDs on screen; the render fails if anything is missing
  S7  previews only: nothing here posts. The owner approves each one first (the first 7 days).
Music: our own (ops/soundtrack.py). No voiceover yet: captions carry everything (most people watch muted).

  python3 ops/story_short.py bet G-AIS-017 [--out social/stories]   -> the story of the bet that this result settled
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postcard as pc
from postcard import AIS, AMBER, BG, FG, LINE, MUTED, PANEL, UP, DOWN, font

W, H, FPS = 1080, 1920, 30
L, R = 80, 930            # safe zone: nothing important within 150 px of the right edge (the like / comment buttons)
TOP, BOT = 250, 1430      # nor in the bottom 490 px (caption, account name) or the top 250 (the app's own bar)
NY = ZoneInfo('America/New_York')
RACE = {'Sports': 'SPORTS BETTING', 'AllInSports': 'ALL IN: SPORTS (SIDE RACE)', 'Predictions': 'PREDICTION MARKETS'}


class StoryError(Exception):
    pass


def money(v, sign=True):
    s = f'C${abs(v):,.0f}'
    return ('+' if v > 0.5 else '−' if v < -0.5 else '') + s if sign else s


def odds(o):
    return f'{int(o):+d}'.replace('-', '−')


def wrap(d, text, f, width):
    words, lines, cur = str(text).split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


# ---------- the facts, from the public ledger only
def bet_story(result_tx, data):
    rows = data.get('allin_trades', []) + data.get('rivals_trades', [])
    cb = next((b for b in data.get('bets', []) if b.get('tx_result') == result_tx), None)
    if cb:   # Claude's own Sports bets live in bets.json, in their own shape
        return claude_bet_story(cb, data)
    res = next((t for t in rows if t.get('tx') == result_tx), None)
    if not res or res.get('action') not in ('Won', 'Lost'):
        raise StoryError(f'{result_tx}: not a won or lost bet in the ledger')
    bet = next((t for t in rows if t.get('action') == 'Bet' and t.get('model') == res['model'] and t.get('experiment') == res['experiment']
                and (t.get('bet') or t.get('symbol')) == (res.get('bet') or res.get('symbol'))), None)
    if not bet:
        raise StoryError(f'{result_tx}: its bet is not in the ledger')
    m = re.match(r'^(?:[A-Z]+: )?(.+?) moneyline \((.+?) @ (.+?)\)$', bet.get('name', ''))
    if not m:
        raise StoryError('only moneyline bets have a story template so far: ' + bet.get('name', ''))
    pick, away, home = m.groups()
    fin = re.match(r'^(.+?) (\d+), (.+?) (\d+)$', res.get('final') or '')
    if not fin:
        raise StoryError('no final score in the ledger for ' + result_tx)
    league = (bet.get('name', '').split(':')[0] if ':' in bet.get('name', '') else '').strip()
    st = standings(res['experiment'], data)
    for k in ('reason', 'amount', 'price', 'tx'):
        if bet.get(k) in (None, ''):
            raise StoryError(f'the bet has no {k}')
    return {'model': res['model'], 'race': res['experiment'], 'league': league, 'pick': pick, 'away': away, 'home': home,
            'odds': int(bet['price']), 'stake': float(bet['amount']), 'reason': bet['reason'].strip(), 'bet_tx': bet['tx'], 'res_tx': result_tx,
            'won': res['action'] == 'Won', 'pnl': float(res.get('pnl', res.get('amount', 0))), 'final': [(fin[1], int(fin[2])), (fin[3], int(fin[4]))],
            'placed': bet['at'], 'settled': res['at'], 'standings': st, 'day': pc.day_of(datetime.fromisoformat(res['at'].replace('Z', '+00:00')))}


def claude_bet_story(b, data):
    if b.get('status') not in ('Won', 'Lost'):
        raise StoryError('Claude bet not won or lost')
    if b.get('market') != 'moneyline' or ' @ ' not in b.get('event', ''):
        raise StoryError('only moneyline bets have a story template so far')
    away, home = b['event'].split(' @ ', 1)
    fin = re.match(r'^(.+?) (\d+), (.+?) (\d+)$', b.get('final') or '')
    if not fin:
        raise StoryError('no final score in the ledger for ' + str(b.get('tx_result')))
    reason = re.split(r' What would prove it wrong:', b.get('note') or '')[0].strip()
    if not reason or not b.get('tx'):
        raise StoryError('the bet has no reason or no ID')
    return {'model': 'claude', 'race': 'Sports', 'league': (b.get('sport') or '').upper(), 'pick': b['pick'].replace(' moneyline', ''),
            'away': away, 'home': home, 'odds': int(b['odds']), 'stake': float(b['stake_cad']), 'reason': reason, 'bet_tx': b['tx'],
            'res_tx': b['tx_result'], 'won': b['status'] == 'Won', 'pnl': float(b.get('result_cad') or 0),
            'final': [(fin[1], int(fin[2])), (fin[3], int(fin[4]))], 'placed': b.get('placed_at'), 'settled': b.get('settled_at'),
            'standings': standings('Sports', data), 'day': pc.day_of(datetime.fromisoformat(b['settled_at']))}


def candidates(data, since_iso):
    """Every settled moneyline bet since that time with its result ID: [(abs money, result ID)], biggest first (S2: the day's biggest moment)."""
    out = []
    for t in data.get('allin_trades', []) + data.get('rivals_trades', []):
        if t.get('action') in ('Won', 'Lost') and t.get('tx') and t.get('at', '') >= since_iso and 'moneyline' in (t.get('name') or ''):
            out.append((abs(float(t.get('pnl', t.get('amount', 0)) or 0)), t['tx']))
    for b in data.get('bets', []):
        if b.get('status') in ('Won', 'Lost') and b.get('tx_result') and b.get('market') == 'moneyline':
            st = datetime.fromisoformat(b['settled_at']).astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%dT%H:%M:%SZ')
            if st >= since_iso:
                out.append((abs(float(b.get('result_cad') or 0)), b['tx_result']))
    return sorted(set(out), reverse=True)

def standings(race, data):
    hist = data.get('allin_history', []) if race.startswith('AllIn') else data.get('rivals_history', [])
    last = {}
    for h in hist:
        if h.get('experiment') == race:
            last[h['model']] = float(h['value'])
    if race == 'Sports' and 'claude' not in last:
        cs = [h for h in data.get('history', []) if h.get('portfolio') == 'Sports']
        if cs:
            last['claude'] = float(cs[-1]['value'])
    moved = {t['model'] for t in data.get('allin_trades', []) + data.get('rivals_trades', []) if t.get('experiment') == race}
    if race == 'Sports' and data.get('bets'):
        moved.add('claude')
    out = [{'id': k, 'profit': v - 100000.0} for k, v in last.items() if k in moved]
    last = {k: v for k, v in last.items() if k in moved}
    for k in ('claude', 'gemini', 'chatgpt'):
        if k not in last:
            out.append({'id': k, 'profit': None})   # no bet yet
    return sorted(out, key=lambda x: -(x['profit'] if x['profit'] is not None else -1e12))


# ---------- drawing
class F:
    def __init__(self):
        self.im = Image.new('RGB', (W, H), BG); self.d = ImageDraw.Draw(self.im)

    def t(self, xy, s, f, fill=FG, anchor='la'):
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor)


def bug(fr, s):   # the persistent score bug (ChatGPT's addition): race, day, pretend money
    fr.d.rectangle((0, 0, W, 210), fill=BG)
    ic = os.path.join(os.path.dirname(pc.HERE), 'icon-512.png')
    if os.path.exists(ic):
        im = Image.open(ic).convert('RGBA').resize((56, 56), Image.LANCZOS); fr.im.paste(im, (L, 120), im)
    fr.t((L + 72, 148), 'PAPERTRADES.AI', font('mono', 'SemiBold', 38), FG, 'lm')
    fr.t((R, 148), f'SEASON 1 · DAY {s["day"]}', font('mono', 'Medium', 26), MUTED, 'rm')
    fr.t((L, 214), RACE.get(s['race'], s['race'].upper()), font('mono', 'SemiBold', 26), UP, 'lm')
    fr.t((R, 214), 'PRETEND MONEY', font('mono', 'SemiBold', 26), AMBER, 'rm')


def footer(fr):
    fr.t((L, BOT - 10), 'Pretend money · real odds · not betting advice', font('sans', 'Regular', 36), MUTED)


def block(fr, y, lines, f, fill, gap=1.18):
    for ln in lines:
        fr.t((L, y), ln, f, fill); y += int(f.size * gap)
    return y


def render(s, out):
    who, col = AIS[s['model']]
    win = s['won']
    tmp = tempfile.mkdtemp()
    scenes = [  # (seconds, draw(frame, t in 0..1, local seconds))
        (2.4, 'premise'), (2.8, 'hook'), (4.2, 'bet'), (5.2, 'reason'), (4.0, 'final'), (3.4, 'money'), (5.0, 'race'), (3.4, 'end')]
    total = sum(x for x, _ in scenes)
    big, mid, small = font('sans', 'Bold', 118), font('sans', 'Bold', 80), font('sans', 'Regular', 46)
    n = 0
    for dur, name in scenes:
        frames = int(round(dur * FPS))
        for i in range(frames):
            u = i / max(1, frames - 1); a = ease(u * 3)   # quick ease-in over the first third
            fr = F(); bug(fr, s); y = {'premise': 360, 'hook': 420, 'bet': 360, 'reason': 380, 'final': 440, 'money': 420, 'race': 330, 'end': 420}[name]
            if name == 'premise':
                y = block(fr, y, ['3 AIs got', 'C$100,000 each'], big, FG)
                y = block(fr, y + 10, ['of pretend money', 'to trade and bet', 'at real prices.'], mid, MUTED)
                x = L
                for k in ('claude', 'gemini', 'chatgpt'):
                    fr.t((x, y + 50), AIS[k][0], font('sans', 'Bold', 76), AIS[k][1]); x += fr.d.textlength(AIS[k][0], font=font('sans', 'Bold', 76)) + 44
                fr.t((L, y + 190), 'Today:', font('sans', 'Bold', 96), AMBER)
            elif name == 'hook':
                y = block(fr, y, [who], font('sans', 'Bold', 160), col)
                kind = 'favourite' if s['odds'] < 0 else 'underdog'
                if 'very safe' in s['reason'].lower():
                    y = block(fr, y + 10, wrap(fr.d, f'called a {odds(s["odds"])} {kind} “very safe”…', big, R - L), big, FG)
                    y = block(fr, y + 30, [f'and bet {money(s["stake"], False)}', 'on it.'], big, AMBER)
                else:
                    y = block(fr, y + 10, wrap(fr.d, f'bet {money(s["stake"], False)} on a {odds(s["odds"])} {kind}.', big, R - L), big, FG)
                    y = block(fr, y + 30, ['Did it pay off?'], big, AMBER)
            elif name == 'bet':
                fr.t((L, y), 'THE BET', font('mono', 'SemiBold', 40), MUTED); y += 80
                box = (L, y, R, y + 900)
                fr.d.rounded_rectangle(box, radius=26, fill=PANEL, outline=col, width=4)
                yy = y + 60
                fr.t((L + 40, yy), f'{who} · {s["league"] or "Sports"}', font('mono', 'SemiBold', 44), col); yy += 100
                for ln in wrap(fr.d, s['pick'], font('sans', 'Bold', 100), R - L - 80):
                    fr.t((L + 40, yy), ln, font('sans', 'Bold', 100), FG); yy += 112
                fr.t((L + 40, yy), 'to win the game', font('sans', 'Regular', 52), MUTED); yy += 100
                opp = s['home'] if s['pick'] == s['away'] else s['away']
                fr.t((L + 40, yy), ('at ' if s['pick'] == s['away'] else 'vs ') + opp, font('sans', 'SemiBold', 60), FG); yy += 130
                fr.t((L + 40, yy), f'Odds {odds(s["odds"])}', font('mono', 'Bold', 64), AMBER); yy += 96
                fr.t((L + 40, yy), f'Stake {money(s["stake"], False)}', font('mono', 'Bold', 64), FG); yy += 110
                fr.t((L + 40, yy), f'Transaction ID {s["bet_tx"]}', font('mono', 'Medium', 34), MUTED)
            elif name == 'reason':
                fr.t((L, y), f'{who.upper()}’S REASON, FROM THE LEDGER', font('mono', 'SemiBold', 38), MUTED); y += 100
                q = '“' + s['reason'] + '”'
                shown = q[:max(1, int(len(q) * ease(u * 1.6)))]
                fq = font('sans', 'SemiBold', 84 if len(q) < 110 else 74 if len(q) < 150 else 64)
                fr.d.rectangle((L, y, L + 12, y + 860), fill=col)
                yy = y
                for ln in wrap(fr.d, shown, fq, R - L - 40):
                    fr.t((L + 40, yy), ln, fq, FG); yy += int(fq.size * 1.22)
            elif name == 'final':
                fr.t((L, y), 'FINAL SCORE', font('mono', 'SemiBold', 40), MUTED); y += 110
                for team, pts in s['final']:
                    shown = int(round(pts * ease(u * 1.5)))
                    winner = pts == max(p for _, p in s['final'])
                    tl = wrap(fr.d, team, font('sans', 'Bold', 84), R - L - 260)
                    for j, ln in enumerate(tl):
                        fr.t((L, y + j * 94), ln, font('sans', 'Bold', 84), FG if winner else MUTED)
                    fr.t((R, y), str(shown), font('mono', 'Bold', 170), FG if winner else MUTED, 'ra')
                    y += max(240, 94 * len(tl) + 80)
                margin = abs(s['final'][0][1] - s['final'][1][1])
                if u > 0.55:
                    fr.t((L, y + 20), f'{s["pick"].split()[0]} {"won" if win else "lost"} by {margin}.', font('sans', 'Bold', 84), UP if win else DOWN)
            elif name == 'money':
                fr.t((L, y), 'THE RESULT', font('mono', 'SemiBold', 40), MUTED); y += 110
                fr.t((L, y), 'BET WON' if win else 'BET LOST', font('sans', 'Bold', 170), UP if win else DOWN); y += 230
                v = s['pnl'] * ease(u * 1.4)
                fr.t((L, y), money(v), font('mono', 'Bold', 150), UP if win else DOWN); y += 210
                fr.t((L, y), f'for {who}', font('sans', 'Bold', 96), col); y += 150
                fr.t((L, y), f'Result: transaction ID {s["res_tx"]}', font('mono', 'Medium', 34), MUTED)
            elif name == 'race':
                fr.t((L, y), 'WHERE IT LEAVES THE RACE', font('mono', 'SemiBold', 40), MUTED); y += 100
                fr.t((L, y), RACE.get(s['race'], s['race']).title().replace('(Side Race)', '(side race)'), font('sans', 'Bold', 76), FG); y += 140
                for pos, r in enumerate(s['standings']):
                    nm, c = AIS[r['id']]
                    fr.d.rounded_rectangle((L, y, R, y + 190), radius=22, fill=PANEL, outline=c if r['id'] == s['model'] else LINE, width=4 if r['id'] == s['model'] else 2)
                    fr.t((L + 40, y + 95), str(pos + 1), font('mono', 'Bold', 68), MUTED, 'lm')
                    fr.t((L + 115, y + 95), nm, font('sans', 'Bold', 72), c, 'lm')
                    if r['profit'] is None:
                        fr.t((R - 40, y + 95), 'no bet yet', font('sans', 'Regular', 54), MUTED, 'rm')
                    else:
                        fr.t((R - 36, y + 95), money(r['profit']), font('mono', 'Bold', 60), UP if r['profit'] > 0.5 else DOWN if r['profit'] < -0.5 else FG, 'rm')
                    y += 215
                fr.t((L, y + 10), 'Profit in this race since Oct 28, as on PaperTrades.AI', font('sans', 'Regular', 40), MUTED)
            elif name == 'end':
                fe = font('sans', 'Bold', 100); y = block(fr, y + 40, wrap(fr.d, 'Every bet and trade, with the AI’s own reasons:', fe, R - L), fe, FG)
                fr.t((L, y + 60), 'PaperTrades.AI', font('mono', 'Bold', 96), AMBER)
                fr.t((L, y + 240), 'Follow for tomorrow’s moves', font('sans', 'SemiBold', 62), MUTED)
            footer(fr)
            if a < 1 and name != 'premise':   # a short fade between scenes
                fr.im = Image.blend(Image.new('RGB', (W, H), BG), fr.im, max(0.25, a))
            fr.im.save(os.path.join(tmp, f'{n:05d}.png')); n += 1
    os.makedirs(out, exist_ok=True)
    stem = os.path.join(out, f'story-{s["res_tx"]}')
    import soundtrack
    hit = sum(x for x, _ in scenes[:4])   # the hit lands on the final score
    wav = soundtrack.make(os.path.join(tmp, 'track.wav'), total, hit, s['res_tx'])
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%05d.png'), '-i', wav,
                    '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '160k', '-af', 'volume=0.7', '-shortest',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', stem + '.mp4'], check=True)
    shutil.copy(os.path.join(tmp, f'{int(sum(x for x, _ in scenes[:6]) * FPS) - 5:05d}.png'), stem + '-thumb.png')
    shutil.rmtree(tmp)
    title = (f'{who} bet {money(s["stake"], False)} on a {odds(s["odds"])} {"favourite" if s["odds"] < 0 else "underdog"}. '
             f'It {"won" if win else "lost"} {s["final"][0][1]}-{s["final"][1][1]}. #Shorts')
    desc = (f'3 AIs (Claude, Gemini and ChatGPT) each got C$100,000 of pretend money to trade and bet with real prices, Oct 28 to Nov 28, 2026.\n'
            f'{who} bet {money(s["stake"], False)} on the {s["pick"]} moneyline at {odds(s["odds"])} ({s["away"]} @ {s["home"]}). '
            f'Its reason, from the public ledger: "{s["reason"]}"\n'
            f'Final: {s["final"][0][0]} {s["final"][0][1]}, {s["final"][1][0]} {s["final"][1][1]}. {who} {"won" if win else "lost"} {money(abs(s["pnl"]), False)}.\n'
            f'Check it yourself: transaction IDs {s["bet_tx"]} and {s["res_tx"]} at PaperTrades.AI (papertrades.ai)\n'
            'Pretend money. Not betting or investment advice.\n#Shorts #AI #Claude #Gemini #ChatGPT')
    json.dump({'story': s, 'title': title, 'description': desc, 'seconds': round(total, 1)}, open(stem + '.json', 'w'), indent=1, ensure_ascii=False)
    return stem + '.mp4', title, desc


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['bet'])
    ap.add_argument('tx')
    ap.add_argument('--out', default='social/stories')
    a = ap.parse_args()
    d = json.load(open('data.json'))
    try:
        st = bet_story(a.tx.upper(), d)
    except StoryError as e:
        sys.exit(f'no Short: {e}')
    p, t, ds = render(st, a.out)
    print(p); print(t); print(ds)
