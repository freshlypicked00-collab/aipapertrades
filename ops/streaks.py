"""Bet streaks counted in GAMES, not bet slips (owner, Oct 31: "8 wins in a row ... implies 8 games"; Claude, Gemini and ChatGPT all
agreed W3, R1, R2: ops/review/streak-oct31.json).

A game counts once however many bets an AI placed on it: it is WON when every settled bet on it won, LOST when every one lost (bets on
both sides of one game end a streak). Pushes and voids are skipped. A parlay counts as its own game. Games are ordered by when their
last bet settled. A streak is shown only when it covers at least 3 different games (R1). Losing streaks follow the same rule.
"""
from datetime import datetime, timezone

RESTART = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)


def _t(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def game_key(b):
    if b.get('legs'):
        return 'parlay:' + str(b.get('id') or b.get('bet'))
    return str(b.get('game') or '') or (str(b.get('event', '')) + '|' + str(b.get('starts_at', '')))


def streak(bets):
    """{'k': 'W'|'L', 'games': n, 'bets': m, 'ids': [bet ids, oldest first], 'since': time} for the latest run, or None."""
    games = {}
    for b in bets or []:
        if b.get('status') not in ('Won', 'Lost') or not b.get('settled_at'):
            continue
        try:
            t = _t(b['settled_at'])
            if b.get('placed_at') and _t(b['placed_at']) < RESTART:
                continue
        except Exception:
            continue
        g = games.setdefault(game_key(b), {'res': set(), 'at': t, 'ids': [], 'n': 0})
        g['res'].add(b['status']); g['at'] = max(g['at'], t); g['n'] += 1
        g['ids'].append((t, str(b.get('id') or b.get('bet'))))
    order = sorted(games.values(), key=lambda g: g['at'])
    if not order:
        return None
    last = order[-1]['res']
    if len(last) != 1:
        return None   # bets on both sides of the latest game: no streak
    k = next(iter(last))
    run = []
    for g in reversed(order):
        if g['res'] != {k}:
            break
        run.append(g)
    run.reverse()
    ids = [i for g in run for _, i in sorted(g['ids'])]
    return {'k': 'W' if k == 'Won' else 'L', 'games': len(run), 'bets': sum(g['n'] for g in run), 'ids': ids,
            'since': min(g['at'] for g in run).isoformat().replace('+00:00', 'Z')}


def label(s, short=False):
    """'3 games won in a row' (+ ' (8 winning bets)' in the long form when bets != games)."""
    if not s:
        return ''
    w = 'won' if s['k'] == 'W' else 'lost'
    txt = f"{s['games']} games {w} in a row"
    if not short and s['bets'] != s['games']:
        txt += f" ({s['bets']} {'winning' if s['k'] == 'W' else 'losing'} bets)"
    return txt
