"""R4 of the root-cause vote (Oct 31; all three AIs agreed): one price source for every public number.

From the first check-in at which the race runner valued Claude's holdings at its own feed prices (rivals.json "claude_feed", written by
claude_feed_values in ops/rivals.py at every check-in, at the same moment as Gemini's and ChatGPT's values), Claude's official values
are those rows. Claude's own valuations (ops/src/history.json, from its own quotes) stay in its files for its decisions and notes, and
are used for everything before the switch. Standings, day closes, lead changes, moments, race cards and posts read official_rows().
"""
import json
import os
from datetime import datetime, timezone

SWITCH = datetime(2026, 10, 31, 7, 15, tzinfo=timezone.utc)   # the first claude_feed check-in (3:15 a.m. ET Oct 31)


def _t(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(timezone.utc)


def official_rows(history, feed):
    """Claude's value rows in history.json format: its own before SWITCH, the runner's (claude_feed) from SWITCH on."""
    rows = [h for h in history if _t(h['at']) < SWITCH]
    from zoneinfo import ZoneInfo
    et = ZoneInfo('America/New_York')   # the same time format as Claude's own rows, so string comparisons stay right
    rows += [{'at': _t(f['at']).astimezone(et).isoformat(timespec='seconds'), 'portfolio': f['experiment'], 'value': f['value'], 'close': False, 'source': 'race runner'}
             for f in feed if _t(f['at']) >= SWITCH]
    return sorted(rows, key=lambda h: _t(h['at']))


def load(src='ops/src'):
    hist = json.load(open(os.path.join(src, 'history.json')))
    try:
        feed = json.load(open(os.path.join(src, 'rivals.json'))).get('claude_feed', [])
    except Exception:
        feed = []
    return official_rows(hist, feed)


def latest_prices(feed):
    """{(race, holding): (price, at)} from the newest claude_feed check-in: the runner's price for each of Claude's holdings."""
    out = {}
    for f in feed:
        for h, px in (f.get('prices') or {}).items():
            k = (f['experiment'], h)
            if k not in out or _t(f['at']) >= _t(out[k][1]):
                out[k] = (px, f['at'])
    return out
