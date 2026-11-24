"""R7 of the root-cause vote (Oct 31; all three AIs agreed, with ChatGPT's regression fixtures): tests that replay the Oct 28-30 failures.
Offline (no network): every feed is a fake. Run from the repo root: python3 ops/tests/run_tests.py  (exit 1 on any failure).
The race runner runs these first; a failure stops the run and opens an alert, so untested code never touches the race."""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'ops'))
os.chdir(ROOT)
import rivals as R  # noqa: E402
sys.modules['rivals'] = R
REAL_GET = R.get_json


def ts(s):
    return int(datetime.fromisoformat(s).timestamp())


def chart(px, qt, bars, reg, cur='CNY'):
    return {'chart': {'result': [{'meta': {'regularMarketPrice': px, 'regularMarketTime': qt, 'currency': cur, 'longName': 'x',
                                           'currentTradingPeriod': {'regular': {'start': reg[0], 'end': reg[1]}}},
                                  'timestamp': [b[0] for b in bars], 'indicators': {'quote': [{'close': [b[1] for b in bars]}]}}]}}


def feed(fakes):
    def get(url, *a, **k):
        for sym, body in fakes.items():
            if '/chart/' + sym.replace('=', '%3D') + '?' in url or '/chart/' + sym + '?' in url:
                return body(url) if callable(body) else body
        raise ValueError('no fake for ' + url)
    R.get_json = get
    R._cache.clear(); R._stale.clear()


def at(s):
    t = datetime.fromisoformat(s)
    R.NOW = t
    R._wall = lambda: t


# ---- C3: the Shanghai open (Oct 29/30: fills at the previous day's close) ----
def test_china_open_previous_close_is_refused():
    at('2026-10-30T01:36:45+00:00')
    o, c, y = ts('2026-10-30T01:30:00+00:00'), ts('2026-10-30T07:00:00+00:00'), ts('2026-10-29T07:00:00+00:00')
    feed({'510300.SS': chart(4.111, y, [(y - 60, 4.111)], (o, c))})
    R.yahoo('510300.SS')
    assert R.stale_quote('China', '510300.SS'), 'a previous close at the open must be stale'


def test_china_open_uses_todays_bar():
    at('2026-10-30T01:36:45+00:00')
    o, c, y = ts('2026-10-30T01:30:00+00:00'), ts('2026-10-30T07:00:00+00:00'), ts('2026-10-29T07:00:00+00:00')
    feed({'510300.SS': chart(4.111, y, [(y - 60, 4.111), (o + 300, 4.066)], (o, c))})
    assert R.yahoo('510300.SS')[0] == 4.066 and not R.stale_quote('China', '510300.SS')


# ---- C1: Yahoo's quote field lagging during the session (SQQQ 49 min, Oct 30) ----
def test_lagging_quote_uses_fresh_minute_bar():
    at('2026-10-30T19:44:20+00:00')
    o, c = ts('2026-10-30T13:30:00+00:00'), ts('2026-10-30T20:00:00+00:00')
    old = ts('2026-10-30T18:55:00+00:00')
    five = chart(42.795, old, [(old, 42.795)], (o, c), 'USD')
    one = chart(42.795, old, [(ts('2026-10-30T19:43:00+00:00'), 42.2515)], (o, c), 'USD')
    feed({'SQQQ': lambda url: one if 'interval=1m' in url else five})
    assert abs(R.yahoo('SQQQ')[0] - 42.2515) < 1e-9 and not R.stale_quote('Stocks', 'SQQQ')


def test_lagging_quote_without_fresh_bar_is_refused():
    at('2026-10-30T19:44:20+00:00')
    o, c = ts('2026-10-30T13:30:00+00:00'), ts('2026-10-30T20:00:00+00:00')
    old = ts('2026-10-30T18:55:00+00:00')
    feed({'SQQQ': chart(42.795, old, [(old, 42.795)], (o, c), 'USD')})
    R.yahoo('SQQQ')
    assert R.stale_quote('Stocks', 'SQQQ'), 'a 49-minute-old quote in an open market must not fill'


def test_crypto_just_after_midnight_is_live():
    at('2026-10-31T00:00:40+00:00')
    d0 = ts('2026-10-31T00:00:00+00:00')
    feed({'BTC-USD': chart(77100.0, d0 - 20, [(d0 - 60, 77090.0)], (d0, d0 + 86399), 'USD')})
    R.yahoo('BTC-USD')
    assert not R.stale_quote('Crypto', 'BTC-USD')


# ---- C4: the yen rounded to 0.0063 ----
def test_yen_is_priced_exactly():
    at('2026-10-30T01:36:00+00:00')
    d0 = ts('2026-10-30T00:00:00+00:00'); q = ts('2026-10-30T01:35:30+00:00')
    feed({'JPYUSD=X': chart(0.0063, q, [(q, 0.0063)], (d0, d0 + 86399), 'USD'), 'JPY=X': chart(157.31, q, [(q, 157.31)], (d0, d0 + 86399), 'JPY')})
    assert abs(R.quote('Currencies', 'JPY')[0] - 1 / 157.31) < 1e-12


# ---- C2 / R2: no new futures positions ----
def test_new_futures_position_is_refused():
    at('2026-11-02T15:00:00+00:00')
    book = {'Metals': {'cur': 'CAD', 'cash': 100000.0, 'positions': {}}}
    try:
        R.execute('gemini', ['Metals'], book, {'experiment': 'Metals', 'action': 'buy', 'symbol': 'GC=F', 'amount': 1000}, {'USDCAD': 1.39, 'USDCNY': 7.1}, {'trades': []})
    except ValueError as e:
        assert 'futures' in str(e)
        return
    raise AssertionError('a new futures position was accepted')


# ---- R3: the automatic fill check (silver stop 0.5% high, SQQQ 1% high) ----
def test_fill_check_corrects_both_directions():
    import fillcheck as FC
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, 'ops', 'src'), os.path.join(tmp, 'ops', 'src'))
    cwd = os.getcwd(); os.chdir(tmp)
    try:
        t0 = datetime(2026, 11, 2, 15, 0, 30, tzinfo=timezone.utc)
        st = {'trades': [{'at': '2026-11-02T15:00:30Z', 'model': 'gemini', 'experiment': 'Stocks', 'action': 'Buy', 'symbol': 'SQQQ', 'price': 42.795, 'amount': 50000.0, 'cur': 'CAD'},
                         {'at': '2026-11-02T15:00:30Z', 'model': 'chatgpt', 'experiment': 'Stocks', 'action': 'Sell', 'symbol': 'QQQ', 'price': 684.0, 'amount': 10000.0, 'cur': 'CAD'}],
              'models': {'gemini': {'books': {'Stocks': {'cur': 'CAD', 'cash': 0.0, 'positions': {}}}}, 'chatgpt': {'books': {'Stocks': {'cur': 'CAD', 'cash': 0.0, 'positions': {}}}}}}
        bars = {'SQQQ': (42.24, 42.26, 42.21, 42.2515), 'QQQ': (690.0, 691.0, 689.9, 690.5)}

        def get(url, *a, **k):
            sym = re.search(r'/chart/([^?]+)\?', url).group(1)
            o, h, l, c = bars[sym]
            return {'chart': {'result': [{'timestamp': [int(t0.replace(second=0).timestamp())], 'indicators': {'quote': [{'open': [o], 'high': [h], 'low': [l], 'close': [c]}]}}]}}
        R.get_json = get
        R.tg = lambda *a, **k: None
        made = FC.run(st, now=t0 + timedelta(minutes=25))
        got = {c['symbol']: c['amount'] for c in made}
        assert abs(got['SQQQ'] - 50000.0 * (1 - 42.2515 / 42.795)) < 0.01, got     # overpaid: refunded
        assert abs(got['QQQ'] - 10000.0 * (690.5 / 684.0 - 1)) < 0.01, got         # sold too low: paid the difference
        assert abs(st['models']['gemini']['books']['Stocks']['cash'] - got['SQQQ']) < 1e-6
        assert not FC.run(st, now=t0 + timedelta(minutes=50)), 'a correction must happen once'
    finally:
        os.chdir(cwd); shutil.rmtree(tmp, ignore_errors=True)


# ---- R5: append-only (the erased check-in, the edited take) ----
def test_append_only_catches_erasures_and_edits():
    import appendonly as A
    before = {'trades': [{'model': 'gemini', 'at': '2026-10-28T17:46:57Z', 'experiment': 'Sports', 'action': 'Bet', 'symbol': 'G1', 'amount': 5000.0}],
              'takes': [{'model': 'chatgpt', 'at': '2026-10-28T17:49:34Z', 'text': 'a long take, and a CAD-positive USD short'}]}
    after = {'trades': [], 'takes': [{'model': 'chatgpt', 'at': '2026-10-28T17:49:34Z', 'text': 'a long take.'}]}
    A.old = lambda path, sha: before if path.endswith('rivals.json') else None
    probs = A.compare('x', lambda p: after if p.endswith('rivals.json') else None)
    assert any('disappeared' in p for p in probs) and any('changed' in p for p in probs), probs
    A.old = lambda path, sha: before if path.endswith('rivals.json') else None
    grown = copy.deepcopy(before); grown['trades'].append({'model': 'chatgpt', 'at': 'z', 'experiment': 'Stocks', 'action': 'Buy', 'symbol': 'QQQ'})
    assert not A.compare('x', lambda p: grown if p.endswith('rivals.json') else None), 'appending must be fine'


# ---- R8: the shell ate "$76,900" and "$3 billion" (Oct 30 log) ----
def test_money_text_guard():
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, 'ops', 'src'), os.path.join(tmp, 'src'))
    bad = {'at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'), 'prices': {}, 'trades': [], 'bets': [],
           'log': [{'portfolio': 'Crypto', 'action': 'Hold', 'detail': 'frozen assets have reached about US billion'}]}
    json.dump(bad, open(os.path.join(tmp, 'in.json'), 'w'))
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'ops', 'update.py'), os.path.join(tmp, 'src'), os.path.join(tmp, 'in.json')], capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode != 0 and 'REFUSED' in (r.stderr + r.stdout), (r.returncode, r.stderr[-300:])


# ---- C6: the price check compared prices with bars from another time of day ----
def test_price_check_uses_its_own_minutes():
    import price_audit as PA
    day = datetime(2026, 10, 30, tzinfo=timezone.utc)
    stamps = [int((day + timedelta(minutes=m)).timestamp()) for m in range(0, 24 * 60, 1)]
    calls = []

    def get(url, *a, **k):
        calls.append(url)
        return {'chart': {'result': [{'timestamp': stamps, 'indicators': {'quote': [{'low': [float(i) for i in range(len(stamps))], 'high': [float(i) + 0.5 for i in range(len(stamps))], 'close': [float(i) for i in range(len(stamps))]}]}}]}}
    PA.R.get_json = get
    PA._bars.clear()
    a = PA.bars('X', day + timedelta(hours=10), day + timedelta(hours=10, minutes=5))
    b = PA.bars('X', day + timedelta(hours=15), day + timedelta(hours=15, minutes=5))
    assert a[0][3] == 600.0 and b[0][3] == 900.0, (a[:1], b[:1])
    assert len(calls) == 1, 'one fetch per symbol and day'


# ---- the nightly fingerprint: Python and the visitor's browser must make the same lines ----
def test_fingerprint_python_matches_browser():
    import fingerprint as FP
    if not shutil.which('node'):
        print('   (node not found: browser half skipped)')
        return
    html = open(os.path.join(ROOT, 'ops', 'src', 'index.html'), encoding='utf-8').read()
    i = html.index('const fpLines = (close) => {'); j = html.index('\n  };', i) + 4
    js = html[i:j]
    data = {'trades': [{'at': '2026-10-29T10:00:00-04:00', 'portfolio': 'Crypto', 'holding': 'Bitcoin', 'action': 'Sell', 'cad': 11287.7, 'price_usd': 79005.48}],
            'bets': [{'bet': 'S1', 'placed_at': '2026-10-28T17:21:00-04:00', 'pick': 'Brewers', 'odds': -149, 'stake_cad': 4000, 'status': 'Won', 'settled_at': '2026-10-28T23:59:00-04:00', 'result_cad': 2684.56}],
            'rivals_trades': [{'model': 'gemini', 'at': '2026-10-29T01:36:43Z', 'experiment': 'China', 'action': 'Buy', 'symbol': '510300.SS', 'amount': 49973.05, 'price': 4.152}],
            'allin_trades': [], 'price_corrections': [{'id': 'PC5', 'model': 'gemini', 'at': '2026-10-31T06:49:22Z', 'experiment': 'China', 'symbol': '159915.SZ', 'fill_at': '2026-10-30T01:36:45Z', 'amount': -1012.04}]}
    close = datetime(2026, 11, 1, tzinfo=timezone.utc)
    py = FP.lines(data['trades'], data['bets'], data['rivals_trades'], close, data['price_corrections'])
    prog = 'const dash={baseData:(k)=>D[k]};const D=' + json.dumps(data) + ';' + js + ';console.log(JSON.stringify(fpLines(Date.parse("2026-11-01T00:00:00Z"))));'
    out = subprocess.run(['node', '-e', prog], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr[-300:]
    assert json.loads(out.stdout) == py, (json.loads(out.stdout), py)


# ---- C5 / R4: one price source (Claude shown 1st in Crypto from a 42-minute-old quote, Oct 29) ----
def test_official_values_come_from_the_runner_after_the_switch():
    import official as OF
    own = [{'at': '2026-10-31T02:22:55-04:00', 'portfolio': 'Crypto', 'value': 1.0}, {'at': '2026-10-31T04:20:00-04:00', 'portfolio': 'Crypto', 'value': 999.0}]
    feed = [{'at': '2026-10-31T07:15:06Z', 'experiment': 'Crypto', 'value': 2.0}, {'at': '2026-10-31T08:15:06Z', 'experiment': 'Crypto', 'value': 3.0}]
    rows = OF.official_rows(own, feed)
    assert [r['value'] for r in rows] == [1.0, 2.0, 3.0], rows        # Claude's own value after the switch is not used
    assert rows[1]['at'] == '2026-10-31T03:15:06-04:00', rows[1]      # the same time format as Claude's own rows


def main():
    tests = [(n, f) for n, f in globals().items() if n.startswith('test_') and callable(f)]
    failed = 0
    for n, f in tests:
        saved = (R.get_json, R.NOW, R._wall, R.tg)
        try:
            f()
            print('ok  ', n)
        except Exception:
            failed += 1
            print('FAIL', n); traceback.print_exc()
        finally:
            R.get_json, R.NOW, R._wall, R.tg = saved
            R._cache.clear(); R._stale.clear()
    print(f'{len(tests) - failed} passed, {failed} failed')
    sys.exit(1 if failed else 0)



def test_calibration_fields_are_cleaned():
    """Oct 31 (all three AIs agreed): p_works is 0-1 (65 means 65%), wrong_lvl needs a symbol and exactly one of below/above."""
    assert R.clean_p(0.65) == 0.65 and R.clean_p('65') == 0.65 and R.clean_p(2000) is None and R.clean_p('x') is None and R.clean_p(None) is None
    assert R.clean_lvl({'symbol': 'SPY', 'below': 735}) == {'symbol': 'SPY', 'below': 735.0}
    assert R.clean_lvl({'symbol': 'SPY', 'below': 1, 'above': 2}) is None and R.clean_lvl({'symbol': '', 'below': 1}) is None and R.clean_lvl('SPY<735') is None

def test_report_cards_are_graded_once_per_closed_day():
    """Oct 31 (all three AIs agreed): only the latest report card of each race and CLOSED race day is graded; never the "All" notes."""
    import peer_grades as PG
    from datetime import datetime as _d, timezone as _tz
    st = {'reviews': [
        {'at': '2026-10-30T00:20:00Z', 'model': 'gemini', 'experiment': 'Stocks', 'grade': 'B', 'text': 'first'},
        {'at': '2026-10-30T01:10:00Z', 'model': 'gemini', 'experiment': 'Stocks', 'grade': 'A', 'text': 'final'},
        {'at': '2026-10-30T01:10:00Z', 'model': 'gemini', 'experiment': 'All', 'grade': None, 'text': 'notes'},
        {'at': '2026-10-31T15:00:00Z', 'model': 'gemini', 'experiment': 'Stocks', 'grade': 'C', 'text': 'still open'}],
        'history': [{'at': '2026-10-29T00:00:00Z', 'model': 'gemini', 'experiment': 'Stocks', 'value': 100000},
                    {'at': '2026-10-30T00:00:00Z', 'model': 'gemini', 'experiment': 'Stocks', 'value': 101000}]}
    rs = PG._reports('gemini', st, _d(2026, 10, 31, 20, 0, tzinfo=_tz.utc))
    assert len(rs) == 1 and rs[0]['day'] == '2026-10-29' and 'final' in rs[0]['reason'] and '+1,000 that day' in rs[0]['result'], rs


def test_health_alert_is_not_silenced_by_an_open_issue():
    """Nov 18: an open alert issue (Oct 30, Instagram) silenced every later alert, so ChatGPT ran out of credit three times with no email.
    The same problem must keep one key from run to run (only its numbers change), and a new problem must get a new key."""
    import health_issue as H
    a = '- ChatGPT is OUT OF API CREDIT: 43 check-in(s) in a row failed, the latest at 2026-11-18T05:15 UTC. Top up now'
    b = '- ChatGPT is OUT OF API CREDIT: 44 check-in(s) in a row failed, the latest at 2026-11-18T06:15 UTC. Top up now'
    c = '- ChatGPT: OpenRouter credit is down to US$12.40, about 1.4 days at the recent pace of US$8.90 a day.'
    assert H.key(a) == H.key(b) and H.key(a) != H.key(c), (H.key(a), H.key(b), H.key(c))
    assert H.MARK.search(H.marker({H.key(a)})) and 'already open' not in open('.github/workflows/rivals.yml').read()


def test_outage_days_owe_no_minimum_and_are_refunded():
    """Nov 18 vote (Claude and Gemini agreed, 2 of 3): a penalty for a day the AI could not check in at all (its API credit or service
    down) is refunded once, with a Refund line; such a day owes no minimum and lowers the C$100,000 totals by C$3,000; a day with any
    working check-in, or one that failed for the AI's own reply, still owes the minimum."""
    saved_now, saved_tg = R.NOW, R.tg
    R.NOW, R.tg = datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc), (lambda *a, **k: None)
    try:
        pen = lambda d, e='Sports': {'day': d, 'at': d + 'T12:00:00Z', 'amount': 500.0, 'reason': 'missed'}
        st = {'trades': [], 'notices': {}, 'models': {'chatgpt': {'books': {'Sports': {'bets': [], 'penalties': [pen('2026-11-12'), pen('2026-11-15')]},
                                                                          'AllInSports': {'bets': [], 'penalties': [pen('2026-11-17')]}},
                                                                'day_log': {'2026-11-18': {'ok': 0, 'down': 9, 'other': 0},     # out all day: excused
                                                                            '2026-11-19': {'ok': 1, 'down': 8, 'other': 0},     # one working check-in: owes it
                                                                            '2026-11-20': {'ok': 0, 'down': 0, 'other': 5}}}}}  # its own replies failed: owes it
        assert R.excused_days(st, 'chatgpt') == {'2026-11-12', '2026-11-17', '2026-11-18'}, R.excused_days(st, 'chatgpt')
        assert R.total_min(st, 'chatgpt', R.PENALTY_FROM) == 91000.0
        R.apply_outage_refunds(st)
        sp, al = st['models']['chatgpt']['books']['Sports'], st['models']['chatgpt']['books']['AllInSports']
        assert [p['day'] for p in sp['penalties']] == ['2026-11-15'] and [p['day'] for p in sp['refunded_penalties']] == ['2026-11-12'], sp
        assert al['penalties'] == [] and al['refunded_penalties'][0]['day'] == '2026-11-17' and R.allin_balance(al) == 100000.0
        assert [(t['experiment'], t['action'], t['symbol'], t['amount']) for t in st['trades']] == [('Sports', 'Refund', 'R-2026-11-12', 500.0), ('AllInSports', 'Refund', 'RA-2026-11-17', 500.0)]
        assert 'refunded' in st['notices']['chatgpt'] and st['excused']['chatgpt'] == ['2026-11-12', '2026-11-17', '2026-11-18']
        R.apply_outage_refunds(st)   # never twice
        assert len(st['trades']) == 2 and len(sp['refunded_penalties']) == 1
        assert R.is_outage('error: HTTP Error 402: Payment Required') and R.is_outage('error: <urlopen error timed out>')
        assert not R.is_outage('error: Expecting value: line 1 column 1 (char 0)') and not R.is_outage('ok')
    finally:
        R.NOW, R.tg = saved_now, saved_tg


def test_a_day_the_runner_never_ran_owes_no_minimum():
    """GitHub would not start any run from Nov 21, 12:14 p.m. ET. A finished ET day with no check-in on record at all (the runner never
    asked the AI) is an outage day like one whose API was down: no daily minimum, C$3,000 off the totals. A day with a working
    check-in, or with only the AI's own failed replies, still owes it; with no log at all nothing is excused; Claude's own test
    (a day with no update at all) is not touched."""
    saved_now, saved_tg = R.NOW, R.tg
    R.NOW, R.tg = datetime(2026, 11, 24, 15, 0, tzinfo=timezone.utc), (lambda *a, **k: None)
    try:
        st = {'trades': [], 'models': {'gemini': {'books': {'Sports': {'bets': [], 'penalties': []}}, 'day_log': {
            '2026-11-20': {'ok': 31, 'down': 0, 'other': 0}, '2026-11-21': {'ok': 12, 'down': 0, 'other': 0},
            # Nov 22: nothing at all (the runner never ran)
            '2026-11-23': {'ok': 0, 'down': 0, 'other': 4}}}}}   # its own replies failed: still owes it
        assert R.no_run_days(st, 'gemini') == {'2026-11-22'} and R.excused_days(st, 'gemini') == {'2026-11-22'}, R.excused_days(st, 'gemini')
        assert R.total_min(st, 'gemini', R.PENALTY_FROM) == R.TOTAL_MIN - R.DAY_MIN
        assert R.excused_days({'models': {'gemini': {}}}, 'gemini') == set()   # no log yet: nothing is excused by mistake
        assert R.excused_days({'models': {'gemini': {'day_log': {}}}}, 'gemini') == set()
        assert R.no_run_days(st, 'claude') == set()   # Claude's test is its own
        st['models']['gemini']['eliminated'] = True   # an AI that is out of the race has no check-ins by design
        assert R.no_run_days(st, 'gemini') == set()
    finally:
        R.NOW, R.tg = saved_now, saved_tg


def test_a_fine_for_a_day_the_runner_never_ran_is_refunded_in_the_right_words():
    """If the first run after the gap has already fined the AIs for the missed day, the next run with this rule refunds each fine once,
    and the ledger line, the public post and the AI's notice say what really happened (the runner never ran), not 'API credit'."""
    saved_now, saved_tg, saved_vote, posts = R.NOW, R.tg, R.NO_RUN_VOTE, []
    R.NOW, R.tg = datetime(2026, 11, 23, 15, 0, tzinfo=timezone.utc), (lambda text, *a, **k: posts.append(text))
    R.NO_RUN_VOTE = ''   # first without the "who agreed" words, then with them
    try:
        pen = lambda d: {'day': d, 'at': d + 'T05:10:00Z', 'amount': 500.0, 'reason': 'missed'}
        log = {'2026-11-20': {'ok': 31, 'down': 0, 'other': 0}, '2026-11-21': {'ok': 12, 'down': 0, 'other': 0}, '2026-11-23': {'ok': 2, 'down': 0, 'other': 0}}
        st = {'trades': [], 'notices': {}, 'models': {
            'gemini': {'books': {'Sports': {'bets': [], 'penalties': [pen('2026-11-22')]}, 'AllInSports': {'bets': [], 'penalties': [pen('2026-11-22')]}}, 'day_log': dict(log)},
            'chatgpt': {'books': {'Sports': {'bets': [], 'penalties': [pen('2026-11-19'), pen('2026-11-22')]}},   # Nov 19: its API was down all day
                        'day_log': dict(log, **{'2026-11-19': {'ok': 0, 'down': 9, 'other': 0}})}}}
        R.apply_outage_refunds(st)
        g = st['models']['gemini']['books']
        assert g['Sports']['penalties'] == [] and g['AllInSports']['penalties'] == [] and R.allin_balance(g['AllInSports']) == 100000.0
        assert [p['day'] for p in g['Sports']['refunded_penalties']] == ['2026-11-22']
        lines = {(t['model'], t['experiment'], t['symbol']): t for t in st['trades']}
        assert set(lines) == {('gemini', 'Sports', 'R-2026-11-22'), ('gemini', 'AllInSports', 'RA-2026-11-22'),
                              ('chatgpt', 'Sports', 'R-2026-11-19'), ('chatgpt', 'Sports', 'R-2026-11-22')}, set(lines)
        assert all(t['action'] == 'Refund' and t['amount'] == 500.0 for t in lines.values())
        why = lines[('gemini', 'Sports', 'R-2026-11-22')]['reason']
        assert 'Gemini was never asked on Nov 22 (ET): the race runner did not run at all that day.' in why, why
        assert why.endswith('Outage rule of Nov 18 (Claude and Gemini agreed, 2 of 3), which also covers a day the race runner never ran.'), why
        assert 'API credit' not in why
        old = lines[('chatgpt', 'Sports', 'R-2026-11-19')]['reason']   # a day its API was down keeps the Nov 18 words
        assert 'because its API credit or service was down. Outage rule of Nov 18 (Claude and Gemini agreed, 2 of 3).' in old and 'runner' not in old, old
        assert 'the race runner itself was down and you were never asked on those days' in st['notices']['gemini']
        assert 'or the race runner itself was down' in st['notices']['chatgpt']   # one day of each kind
        assert 'Sports total minimum is now C$97,000' in st['notices']['gemini'], st['notices']['gemini']
        assert len(posts) == 4 and all('penalty refunded' in x for x in posts) and sum('never asked' in x for x in posts) == 3
        assert st['excused'] == {'gemini': ['2026-11-22'], 'chatgpt': ['2026-11-12', '2026-11-17', '2026-11-19', '2026-11-22'], 'claude': st['excused']['claude']}
        R.apply_outage_refunds(st)   # never twice
        assert len(st['trades']) == 4 and len(posts) == 4
        # once the vote is in, the public lines say who agreed
        R.NO_RUN_VOTE = 'Gemini and ChatGPT agreed, Nov 23'
        st2 = {'trades': [], 'notices': {}, 'models': {'gemini': {'books': {'Sports': {'bets': [], 'penalties': [pen('2026-11-22')]}}, 'day_log': dict(log)}}}
        R.apply_outage_refunds(st2)
        assert st2['trades'][0]['reason'].endswith('which also covers a day the race runner never ran (Gemini and ChatGPT agreed, Nov 23).'), st2['trades'][0]['reason']
        # Claude, Nov 22: voted on by name (Gemini and ChatGPT waived its fines; Claude did not vote). Its Sports fine lives in
        # claude_penalties (no ledger line here); its High risk fine is a ledger line here, so the refund must be one too. The line
        # says who decided, not "Outage rule of Nov 18".
        assert R.excused_days({'models': {}}, 'claude') >= {'2026-11-22'} and R.total_min({'models': {}}, 'claude', R.PENALTY_FROM) == R.TOTAL_MIN - R.DAY_MIN
        st3 = {'trades': [], 'notices': {}, 'models': {}, 'claude_penalties': [pen('2026-11-22'), pen('2026-11-05')],
               'claude_allin': {'books': {'AllInSports': {'bets': [], 'penalties': [pen('2026-11-22')]}}}}
        n = len(posts)
        R.apply_outage_refunds(st3)
        assert [p['day'] for p in st3['claude_penalties']] == ['2026-11-05'] and [p['day'] for p in st3['claude_penalties_refunded']] == ['2026-11-22']
        ab = st3['claude_allin']['books']['AllInSports']
        assert ab['penalties'] == [] and ab['refunded_penalties'][0]['day'] == '2026-11-22' and R.allin_balance(ab) == 100000.0
        assert [(t['model'], t['experiment'], t['action'], t['symbol'], t['amount']) for t in st3['trades']] == [('claude', 'AllInSports', 'Refund', 'RA-2026-11-22', 500.0)], st3['trades']
        why = st3['trades'][0]['reason']
        assert 'Claude had queued its Nov 22 (ET) bets just after midnight' in why and 'Outage rule of Nov 18' not in why, why
        assert why.endswith('Waived by Gemini and ChatGPT on Nov 23, the same remedy as for their own outage day; Claude did not vote on its own fine.'), why
        assert st3['claude_penalties_refunded'][0]['refund_rule'].startswith('Waived by Gemini and ChatGPT on Nov 23') and len(posts) == n + 2
        assert all('Waived by Gemini and ChatGPT' in x for x in posts[n:]) and 'notices' in st3 and 'claude' not in st3['notices']
        R.apply_outage_refunds(st3)   # never twice
        assert len(st3['trades']) == 1 and len(posts) == n + 2
    finally:
        R.NOW, R.tg, R.NO_RUN_VOTE = saved_now, saved_tg, saved_vote


def test_late_stop_remedy_is_the_first_scheduled_run_at_or_below_the_level():
    """ops/outage_stops.py (read-only): where each of ChatGPT's two SQQQ stops would have filled on Mon Nov 23 had the runner run, and
    the cash correction that would restate it. The first chance is the 9:35 a.m. ET run; a price above the level waits for a later run."""
    import outage_stops as O
    ms = O.scheduled_minutes()
    assert [t.strftime('%H:%M') for t in ms[:6]] == ['14:35', '14:38', '14:43', '14:53', '15:08', '15:13'] and ms[-1].strftime('%H:%M') == '20:53', ms[:6]
    ep = lambda hm: int(datetime.fromisoformat(f'2026-11-23T{hm}:00+00:00').timestamp())
    low = {ep('14:30') + 60 * i: 49.8 for i in range(390)}          # opened far below both stops: both fill at the 9:35 run
    a, b = O.plan(low)
    assert a['bar_minute'] == b['bar_minute'] == '2026-11-23T14:35Z' and a['bar_price'] == 49.8
    assert a['correction'] == round(6262.91 * (49.8 / 45.61 - 1), 2) and b['correction'] == round(15657.28 * (49.8 / 45.61 - 1), 2)
    later = {k: 57.0 for k in low}; later[ep('14:38')] = 56.0; later[ep('14:43')] = 55.5   # crosses 56.20 first, 55.90 one run later
    a, b = O.plan(later)
    assert (a['bar_minute'], a['bar_price']) == ('2026-11-23T14:38Z', 56.0) and (b['bar_minute'], b['bar_price']) == ('2026-11-23T14:43Z', 55.5)
    between = {k: 57.0 for k in low}; between[ep('14:36')] = 50.0   # a dip between two scheduled runs is not a fill: the runner was not looking
    assert all('bar_price' not in r for r in O.plan(between))
    assert all('bar_price' not in r for r in O.plan({k: 57.0 for k in low})) and all('bar_price' not in r for r in O.plan({}))


def test_one_ai_cannot_use_up_the_whole_run():
    """Nov 19: from Nov 18, 10:14 p.m. ET every check-in was killed at the 30-minute job limit before anything was saved, and Gemini
    and ChatGPT both missed 8 hours. Each AI's model requests now share one clock (MODEL_BUDGET): a request to a model host is cut
    off when the clock runs out, other requests are untouched, and 2 AIs x the budget fits well inside the job limit."""
    import time
    saved = R._fetch, R.ASK['deadline'], R.ASK_FLOOR
    slow = {'s': 3}
    R._fetch = lambda *a, **k: (time.sleep(slow['s']), {'ok': 1})[1]
    try:
        R.ASK_FLOOR = 0.2
        R.ASK['deadline'] = time.monotonic() + 1            # 1 s left on the clock; the answer would take 3 s
        t0 = time.monotonic()
        try:
            R.get_json('https://openrouter.ai/api/v1/chat/completions', {}, b'{}', timeout=60)
            raise AssertionError('a hung model request was not cut off')
        except TimeoutError as e:
            assert 'no full answer after' in str(e) and time.monotonic() - t0 < 2.5, (str(e), time.monotonic() - t0)
        slow['s'] = 0
        R.ASK_FLOOR = 15
        R.ASK['deadline'] = time.monotonic() + 5            # under the floor: refused at once
        try:
            R.get_json('https://generativelanguage.googleapis.com/v1beta/models/x:generateContent?key=k', {}, b'{}', timeout=60)
            raise AssertionError('a request after the deadline was sent')
        except TimeoutError as e:
            assert 'out of time' in str(e), str(e)
        assert R.get_json('https://query1.finance.yahoo.com/v8/finance/chart/X', timeout=60) == {'ok': 1}   # prices are not model requests
        R.ASK['deadline'] = None
        assert R.get_json('https://openrouter.ai/api/v1/chat/completions', {}, b'{}', timeout=60) == {'ok': 1}
        assert R.is_outage('error: no full answer after 540 s from https://openrouter.ai/api/v1/chat/completions') and R.is_outage('error: out of time: the 540 s this AI has for one check-in are used up')
        assert 2 * R.MODEL_BUDGET + R.NEWS_BUDGET <= 22 * 60, 'two AI turns and the news must fit well inside the 30-minute job'
    finally:
        R._fetch, R.ASK['deadline'], R.ASK_FLOOR = saved


def test_animated_card_recorder_cannot_spin_forever():
    """Nov 19: the recorder for animated cards names images by id(); Python reuses the id of a freed image, two alias links pointed at
    each other and root() looped for good. Every check-in from Nov 18, 10:14 p.m. ET stalled on one result card until the job limit
    killed it. A loop now raises (that card goes out as a still) instead of spinning."""
    try:
        import animate
        from PIL import Image, ImageDraw
    except Exception:
        return   # no Pillow on this machine: the race runner skips animated cards too
    rec = animate._Rec()
    rec.alias = {1: 2, 2: 1}
    try:
        rec.root(1)
        raise AssertionError('an alias loop did not raise')
    except RuntimeError:
        pass
    rec.alias = {3: 2, 2: 1}
    assert rec.root(3) == 1 and rec.root(7) == 7

    def card(path):
        im = Image.new('RGB', (200, 120), (10, 10, 10))
        for _ in range(60):                       # many short-lived crops: this is what lets ids be reused
            im = im.crop((0, 0, 200, 120))
            ImageDraw.Draw(im).rectangle([10, 10, 60, 40], fill=(200, 60, 60))
        im.save(path)
        return path
    out, rec = animate.record(card, '/tmp/_pt_test_card.png')
    assert rec.saved and all(k != v for k, v in rec.alias.items())
    els, base, final = animate.elements(rec)      # Nov 19 repair: tags are never reused, so this always comes back, with the elements
    animate.check(els, base, final)               # ... and they put the still card back together exactly


def test_animation_always_ends_on_the_still_card():
    """Nov 19 (owner; Claude and Gemini agreed, ops/review/followups-nov19.json, F3): an animation is only used if its last frame is the
    still card. A card like the real ones (header bar, text, a robot pasted on a converted copy, trimmed to fit) passes; a recording that
    lost its drawing steps (what happened on GitHub's new runner: an almost empty card) is refused, so the still goes out."""
    try:
        import animate
        from PIL import Image, ImageDraw
    except Exception:
        return

    def card(path):
        im = Image.new('RGB', (400, 520), (18, 18, 16))
        g = ImageDraw.Draw(im)
        g.rectangle([0, 0, 400, 8], fill=(79, 143, 247))
        g.text((20, 30), 'Gemini sells Bitcoin', fill=(242, 233, 216))
        g.rounded_rectangle([20, 80, 200, 160], radius=12, fill=(30, 30, 28), outline=(70, 70, 66), width=2)
        g.text((30, 100), 'C$29,246', fill=(61, 220, 132))
        bot = Image.new('RGBA', (40, 40), (0, 0, 0, 0)); ImageDraw.Draw(bot).ellipse([0, 0, 39, 39], fill=(79, 143, 247, 255))
        base = im.convert('RGBA'); base.alpha_composite(bot, (340, 20)); im.paste(base.convert(im.mode))   # sharecard._robot on an RGB card
        im = im.crop((0, 0, 400, 300))                                                                       # sharecard._finish
        ImageDraw.Draw(im).text((20, 270), '@PaperTradesAI', fill=(155, 146, 127))
        im.save(path)
        return path
    _, rec = animate.record(card, '/tmp/_pt_test_card2.png')
    els, base, final = animate.elements(rec)
    mean, off = animate.check(els, base, final)
    assert mean == 0 and off == 0 and any(e.kind == 'paste' and e.sprite.size[0] <= 45 for e in els), (mean, off, [(e.kind, e.sprite.size) for e in els])
    rec.ops = [op for op in rec.ops if op[1] == 'text' and '@PaperTradesAI' in str(op[2][1:2])]   # only the mark is left
    els, base, final = animate.elements(rec)
    try:
        animate.check(els, base, final)
        raise AssertionError('an almost empty animation passed the check')
    except RuntimeError as e:
        assert 'does not end on the still card' in str(e), e
    try:
        animate.make_gif(card, ('/tmp/_pt_test_card2.png',), {}, '/tmp/_pt_never.gif', rec=rec)
        raise AssertionError('make_gif made a GIF from a recording that does not end on the still')
    except RuntimeError:
        assert not os.path.exists('/tmp/_pt_never.gif')


def test_move_posts_say_which_number_is_which():
    """Nov 19 (all three AIs agreed, W1 to W6): one wording for every move post. The action and the race, then the thing in plain words
    (an option's plain name, never the exchange code), then a money line that names the amount and the price; the brand on the last line."""
    opt = {'experiment': 'Options', 'action': 'Buy', 'symbol': 'NVDA261120P00150000', 'outcome': None, 'name': 'NVDA Nov 20 $150 put', 'price': 4.3, 'pcur': 'USD', 'qty': 500, 'amount': 3074.28, 'cur': 'CAD'}
    assert R.post_lines(opt) == '🟢 <b>Bought · Options</b>\nNVDA Nov 20 $150 put\nBought C$3,074 at US$4.30 per share (5 contracts)', R.post_lines(opt)
    cov = {'experiment': 'Currencies', 'action': 'Cover', 'symbol': 'EUR', 'outcome': None, 'name': 'Euro', 'price': 1.0971, 'pcur': 'USD', 'qty': 63297.8, 'amount': 99513.29, 'cur': 'CAD'}
    assert R.post_lines(cov) == '🔺 <b>Bought back · Currencies</b>\nEuro (EUR)\nBought back for C$99,513 at US$1.0971 per EUR', R.post_lines(cov)
    sh = dict(cov, action='Short', amount=100000.0, price=1.1078)
    assert R.post_lines(sh).startswith('🔻 <b>Sold short · Currencies</b>\nEuro (EUR)\nSold short C$100,000 at ')
    bet = {'experiment': 'AllInSports', 'action': 'Bet', 'symbol': 'C99', 'outcome': None, 'name': 'NBA: San Antonio Spurs moneyline (LA Clippers @ San Antonio Spurs)', 'price': -1200, 'pcur': 'CAD', 'qty': 1, 'amount': 3000.0, 'cur': 'CAD'}
    assert R.post_lines(bet) == ('🎯 <b>Bet · High risk: sports</b>\nNBA: San Antonio Spurs moneyline (LA Clippers @ San Antonio Spurs)\n'
                                 'Bet C$3,000 at -1200 · to win C$250 profit (-1200: bet C$1,200 to win C$100)'), R.post_lines(bet)
    pred = {'experiment': 'Predictions', 'action': 'Buy', 'symbol': 'another-fed-rate-hike-in-2026', 'outcome': 'Yes', 'name': 'Another Fed rate hike in 2026?', 'price': 0.962, 'pcur': 'USD', 'qty': 2185.0, 'amount': 3000.0, 'cur': 'CAD'}
    assert R.post_lines(pred).split('\n')[1] == 'Another Fed rate hike in 2026? · Yes'
    assert R.post_foot().startswith('PaperTrades.AI · Claude vs Gemini vs ChatGPT · https://')


def _ledger_functions():
    """The Ledger's own profit steps, taken straight from ops/build_site.py's text (it cannot be imported: it builds the site when run)."""
    src = open(os.path.join(ROOT, 'ops', 'build_site.py')).read()
    code = '\n'.join(re.search(r'^def ' + n + r'\(.*?(?=^\S)', src, re.S | re.M).group(0) for n in ('_annotate_rivals', '_annotate_claude', '_claude_realized_fix'))
    ns = {'datetime': datetime}
    exec(code, ns)
    return ns


def test_sale_posts_show_the_ledgers_result():
    """Nov 19 (owner: "sale posts say the result ... the same number the Ledger shows in every case"; Claude and Gemini agreed):
    for EVERY sale, short bought back, settlement and expiry on record, the post's profit and cost must equal the Ledger's to the cent
    (part sales, shorts and US$ positions included). No figure, no line."""
    import saleresult as S
    L = _ledger_functions()
    st = json.load(open(os.path.join(ROOT, 'ops', 'src', 'rivals.json')))
    led = copy.deepcopy(st); L['_annotate_rivals'](led)
    want = [(i, t['cost'], t['pnl']) for i, t in enumerate(led['trades']) if t['action'] in S.CLOSES and t.get('pnl') is not None]
    assert len(want) >= 150, len(want)
    R.POST_STATE = st
    try:
        for i, cost, pnl in want:
            t = st['trades'][i]
            got = S.for_rival(st['trades'], t)
            assert got and (got['cost'], got['pnl']) == (cost, pnl), (i, t['model'], t['experiment'], t['symbol'], got, cost, pnl)
            last = R.post_lines(t).split('\n')[-1]
            sym = 'US$' if t['cur'] == 'USD' else 'C$'
            assert (('+' if pnl >= 0.005 else '−') + sym + f'{abs(pnl):,.2f}') in last or (abs(pnl) < 0.005 and 'Broke even' in last), (i, last, pnl)
            assert last.startswith(('Profit on this ', 'Loss on this ', 'Broke even on this ')), last
            assert ('this part was' in last) == got['part'], (i, last)
        closes_without = [t for i, t in enumerate(led['trades']) if t['action'] in S.CLOSES and t.get('pnl') is None]
        for t0 in closes_without:   # the Ledger has no figure: the post has no result line
            assert R.post_result(st['trades'][led['trades'].index(t0)]) == ''
        buy = next(t for t in st['trades'] if t['action'] == 'Buy')
        assert R.post_result(buy) == '' and len(R.post_lines(buy).split('\n')) == 3
        stranger = dict(want and st['trades'][want[0][0]], at='2030-01-01T00:00:00Z')   # a sale the records do not hold
        assert R.post_result(stranger) == ''
    finally:
        R.POST_STATE = None
    assert R.post_result(st['trades'][want[0][0]]) == ''   # no records at hand: left out, never guessed
    # Claude's ten races: the same check against the Ledger's steps for ops/src/trades.json
    tr = json.load(open(os.path.join(ROOT, 'ops', 'src', 'trades.json'))); hd = json.load(open(os.path.join(ROOT, 'ops', 'src', 'holdings.json')))
    led = copy.deepcopy(tr); L['_annotate_claude'](led); L['_claude_realized_fix'](led, hd)
    want = {i: (t['cost'], t['pnl']) for i, t in enumerate(led) if t['action'] in S.CLOSES and t.get('pnl') is not None}
    got = {i: (c, p) for i, c, p, _ in S.claude_results(tr, hd)}
    assert got == want and len(want) >= 15, (got, want)
    last = max(want)
    res = S.for_claude(tr, hd, tr[last]['portfolio'], tr[last]['holding'], tr[last]['action'])
    assert res and (res['cost'], res['pnl']) == want[last]
    assert S.for_claude(tr, hd, 'Stocks', 'No such holding', 'Sell') is None
    # the words
    assert S.line('Sell', {'pnl': -376.83, 'cost': 15000.0, 'part': False, 'cur': 'CAD'}) == 'Loss on this sale: −C$376.83 (bought for C$15,000)'
    assert S.line('Sell', {'pnl': 23.09, 'cost': 10000.0, 'part': True, 'cur': 'CAD'}) == 'Profit on this sale: +C$23.09 (this part was bought for C$10,000)'
    assert S.line('Cover', {'pnl': 486.71, 'cost': 100000.0, 'part': False, 'cur': 'CAD'}) == 'Profit on this short: +C$486.71 (sold short for C$100,000)'
    assert S.line('Sell', {'pnl': -1701.57, 'cost': 39993.0, 'part': False, 'cur': 'USD'}) == 'Loss on this sale: −US$1,701.57 (bought for US$39,993)'
    assert S.line('Expired', {'pnl': -3074.28, 'cost': 3074.28, 'part': False, 'cur': 'CAD'}) == 'Loss on this position: −C$3,074.28 (bought for C$3,074)'
    assert S.line('Buy', {'pnl': 5, 'cost': 5}) == '' and S.line('Sell', None) == ''


def test_sale_picture_shows_the_ledgers_profit():
    """Nov 19: the picture of a sale worked its profit out from the price move alone (no exchange rate) and disagreed with the Ledger
    (ChatGPT's Bitcoin sale: picture −C$460, Ledger −C$376.83). It now takes the Ledger's figure for every sale on record."""
    try:
        import sharecard
    except Exception:
        return   # no Pillow on this machine: no pictures are made either
    import saleresult as S
    st = json.load(open(os.path.join(ROOT, 'ops', 'src', 'rivals.json')))
    n = 0
    for t, cost, pnl, part in S.rival_results(st['trades']):
        if t['action'] not in ('Sell', 'Cover'):
            continue
        bi = sharecard.exit_info(t, st['trades'])
        if bi is None:
            continue
        assert bi.get('pnl') == pnl, (t['model'], t['experiment'], t['symbol'], bi.get('pnl'), pnl)
        assert cost <= 0 or abs(bi['ret'] - pnl / cost) < 1e-12
        n += 1
    assert n >= 100, n


def test_a_stuck_picture_or_run_is_stopped():
    """Nov 19 (owner: "the race must never stop again"): a picture that never finishes is dropped after CARD_BUDGET and the post goes
    out without it; a whole check-in that is still going after RUN_BUDGET is stopped by us, in time for the publish and health steps.
    The stall of Nov 18 was a loop inside a picture that asked the network for nothing, so no request timeout could end it."""
    import time
    import timelimit as T
    import sharecard

    def spin(*a, **k):
        while True:
            try:
                time.sleep(0.01)
            except Exception:      # like the retry loops in the real code: an ordinary "except Exception" must not swallow the stop
                pass
    saved = sharecard.trade_card, sharecard.album, sharecard.moves_card, R.tgcharts.price_chart, R.chart, R.CARD_BUDGET, R.RUN_BUDGET, R.main
    try:
        sharecard.trade_card = sharecard.album = spin
        R.CARD_BUDGET = 0.2
        R.guard_pictures()
        t0 = time.monotonic()
        assert sharecard.trade_card('Gemini', {}) is None and sharecard.album('Gemini', []) == []
        assert time.monotonic() - t0 < 2.5
        R.guard_pictures()                                 # twice is safe: no guard around a guard
        with T.limit(5, 'outer'):                          # a limit inside a limit: the inner one fires, the outer one lives on
            assert T.guarded(spin, 0.1, 'inner')() is None
        try:
            with T.limit(0.2, 'outer'):
                T.guarded(lambda: time.sleep(0.01), 5, 'inner')()
                spin()
            raise AssertionError('the outer limit was lost after an inner one')
        except T.StepTimeout:
            pass
        R.main, R.RUN_BUDGET = spin, 0.3
        if os.path.exists('/tmp/run_stopped.txt'):
            os.remove('/tmp/run_stopped.txt')
        t0 = time.monotonic()
        R.run()                                            # comes back by itself, and leaves the note the health check reads
        assert time.monotonic() - t0 < 3 and 'the whole check-in' in open('/tmp/run_stopped.txt').read()
        os.remove('/tmp/run_stopped.txt')
    finally:
        sharecard.trade_card, sharecard.album, sharecard.moves_card, R.tgcharts.price_chart, R.chart, R.CARD_BUDGET, R.RUN_BUDGET, R.main = saved


def test_each_turn_is_saved_and_pushed_as_it_goes():
    """Nov 19 (owner: "save each AI's turn as soon as it is done"): checkpoint() writes the records at once and, on GitHub's runner,
    pushes that one file to main from a scratch copy, leaving the run's own folder alone (so the Publish step still sees a change to
    publish). Tried here against a throwaway repository. A push that cannot work never raises into the check-in."""
    tmp = tempfile.mkdtemp()
    saved = R.STATE, os.getcwd(), os.environ.get('GITHUB_ACTIONS'), dict(R.SAVED)
    g = lambda *a, cwd=None: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'init.defaultBranch=main', *a], cwd=cwd, capture_output=True, text=True)
    try:
        origin, work = os.path.join(tmp, 'origin.git'), os.path.join(tmp, 'work')
        g('init', '-q', '--bare', origin)
        g('clone', '-q', origin, work)
        os.makedirs(os.path.join(work, 'ops', 'src'))
        json.dump({'trades': [], 'models': {}}, open(os.path.join(work, 'ops', 'src', 'rivals.json'), 'w'))
        g('add', '-A', cwd=work); g('commit', '-qm', 'start', cwd=work); g('push', '-q', 'origin', 'HEAD:main', cwd=work)
        os.chdir(work)
        R.STATE = 'ops/src/rivals.json'
        state = {'trades': [], 'models': {'gemini': {'last_run': {'at': 'x', 'status': 'ok'}}}, 'history': [{'at': '2026-10-28T00:00:00Z', 'model': 'gemini', 'experiment': 'Stocks', 'value': 1}] * 3}
        os.environ.pop('GITHUB_ACTIONS', None)
        assert R.checkpoint(state, 'local') is True                      # off GitHub: the file is written, nothing is pushed
        assert json.load(open(R.STATE))['models']['gemini']['last_run']['status'] == 'ok' and len(json.load(open(R.STATE))['history']) == 3   # nothing thinned
        assert g('rev-list', '--count', 'main', cwd=origin).stdout.strip() == '1'
        os.environ['GITHUB_ACTIONS'] = 'true'
        assert R.checkpoint(state, "Gemini's turn") is True
        assert g('rev-list', '--count', 'main', cwd=origin).stdout.strip() == '2'
        assert 'last_run' in g('show', 'main:ops/src/rivals.json', cwd=origin).stdout
        assert "Gemini's turn" in g('log', '-1', '--format=%s', 'main', cwd=origin).stdout
        assert g('diff', '--quiet', '--', 'ops/src/rivals.json', cwd=work).returncode == 1   # the run's own folder still shows the change: Publish goes ahead
        assert g('rev-list', '--count', 'HEAD', cwd=work).stdout.strip() == '1' and not os.path.exists('/tmp/pt_checkpoint')
        state['models']['gemini']['last_run']['status'] = 'second'
        other = os.path.join(tmp, 'other'); g('clone', '-q', origin, other)   # someone else pushes in between: the checkpoint still lands on top
        open(os.path.join(other, 'x.txt'), 'w').write('x'); g('add', '-A', cwd=other); g('commit', '-qm', 'other', cwd=other); g('push', '-q', 'origin', 'HEAD:main', cwd=other)
        assert R.checkpoint(state, 'ChatGPT') is True
        assert g('rev-list', '--count', 'main', cwd=origin).stdout.strip() == '4' and 'second' in g('show', 'main:ops/src/rivals.json', cwd=origin).stdout
        assert g('show', 'main:x.txt', cwd=origin).stdout == 'x'
        g('remote', 'set-url', 'origin', os.path.join(tmp, 'nowhere.git'), cwd=work)
        state['models']['gemini']['last_run']['status'] = 'third'
        assert R.checkpoint(state, 'no remote') is False                 # cannot push: says so, does not raise; the file on disk is still written
        assert json.load(open(R.STATE))['models']['gemini']['last_run']['status'] == 'third'
    finally:
        os.chdir(saved[1]); R.STATE = saved[0]
        R.SAVED.clear(); R.SAVED.update(saved[3])
        if saved[2] is None:
            os.environ.pop('GITHUB_ACTIONS', None)
        else:
            os.environ['GITHUB_ACTIONS'] = saved[2]
        shutil.rmtree(tmp, ignore_errors=True)


def test_watchdog_tells_when_an_ai_has_not_checked_in():
    """Nov 19 (owner: "alert me when Gemini or ChatGPT has had no finished check-in for 2 hours"). The 8-hour stall raised no alert
    because the only health check was a step of the stalled run itself. ops/watchdog.py runs on its own and reads only the records."""
    import watchdog as W
    now = datetime(2026, 11, 19, 8, 0, tzinfo=timezone.utc)
    st = {'models': {'gemini': {'label': 'Gemini', 'last_run': {'at': '2026-11-19T03:14:00Z'}}, 'chatgpt': {'label': 'ChatGPT', 'last_run': {'at': '2026-11-19T06:30:00Z'}}}}
    hist = [{'at': '2026-11-19T07:15:00Z'}]
    p = W.problems(st, hist, now)
    assert len(p) == 1 and p[0].startswith('Gemini: no finished check-in for 4 h 46 min') and '10:14 p.m. ET' in p[0], p
    st['models']['gemini']['last_run']['at'] = '2026-11-19T06:01:00Z'
    assert W.problems(st, hist, now) == []                                         # 1 h 59 min: not yet
    st['models']['chatgpt']['last_run']['at'] = '2026-11-19T05:59:00Z'
    assert [x.split(':')[0] for x in W.problems(st, [{'at': '2026-11-19T04:00:00Z'}], now)] == ['ChatGPT', 'Claude']
    assert W.problems(st, hist, datetime(2026, 11, 28, 22, 0, tzinfo=timezone.utc)) == []   # after the finish there is nothing to watch
    wf = open(os.path.join(ROOT, '.github', 'workflows', 'watchdog.yml')).read()
    assert 'schedule:' in wf and 'workflow_run:' in wf and 'ops/watchdog.py' in wf and 'rivals' not in wf.split('concurrency:')[1].split('jobs:')[0]   # two starters of its own, its own queue


def test_a_question_cannot_cancel_a_queued_race_run():
    """Nov 19: GitHub keeps one waiting run per concurrency group, and a newer one cancels it. Questions for the AIs (mode ask) used
    the race's group, so a question could replace a queued check-in. They now wait in a group of their own."""
    wf = open(os.path.join(ROOT, '.github', 'workflows', 'rivals.yml')).read()
    grp = re.search(r"^concurrency:\n  group: (.+)\n  cancel-in-progress: false", wf, re.M).group(1)
    assert "inputs.mode == 'ask' && 'rivals-ask'" in grp and "inputs.mode == 'prices' && 'rivals-prices'" in grp and grp.rstrip(' }').endswith("|| 'rivals'"), grp


def test_a_picture_that_timed_out_is_not_posted_twice():
    """Nov 21: Gemini's Texans win (Nov 19, 11:16 p.m. ET) went out twice on Telegram. The animated card's upload got no answer within
    60 s although Telegram had posted it, and the runner then sent the still card as well. Now a post that went out whole but got no
    answer in time is not sent again (and an animation gets 120 s); one Telegram refused, or one that never left, still falls back to
    the still card. The album sender follows the same rule."""
    import urllib.error
    import urllib.request
    import sharecard
    tmp = tempfile.mkdtemp()
    png, png2, gif = os.path.join(tmp, 'c.png'), os.path.join(tmp, 'd.png'), os.path.join(tmp, 'c.gif')
    for f in (png, png2, gif):
        open(f, 'wb').write(b'x')
    calls, texts = [], []

    def fake(*outcomes):
        it = iter(outcomes)

        def urlopen(req, timeout=None):
            calls.append((req.full_url.rsplit('/', 1)[1], timeout))
            o = next(it)
            if isinstance(o, BaseException):
                raise o

            class Ok:
                def read(self):
                    return b'{"ok": true, "result": {"message_id": 1}}'
            return Ok()
        return urlopen
    # The picture libraries are installed only in the runs that make pictures; the 15-minute settle runs skip them, so the animated
    # cards module is absent there. This test used to insist on it, so it failed in every settle run and stopped it with a "tests
    # failing" alert (both that fired: Nov 21, 7:14 a.m. ET and Nov 24, 1:48 a.m. ET). The rule under test needs only gif_of, so
    # a stand-in lets it run everywhere.
    had_cards = R.animate
    if not had_cards:
        class _Cards:
            gif_of = staticmethod(lambda p: None)
        R.animate = _Cards()
    saved = urllib.request.urlopen, R.tg, R.QUIET_TG, R.animate.gif_of, os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    try:
        os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID'] = 't', 'c'
        R.QUIET_TG = False
        R.tg = lambda text, **k: texts.append(text)
        R.animate.gif_of = lambda p: gif
        urllib.request.urlopen = fake(TimeoutError('The read operation timed out'))            # sent whole, no answer: nothing more
        R.tg_photo('Won', png, _dc=False)
        assert calls == [('sendAnimation', 120)] and texts == [], (calls, texts)
        calls.clear()
        urllib.request.urlopen = fake(urllib.error.HTTPError('u', 400, 'Bad Request', {}, None), 'ok')   # refused: the still card goes
        R.tg_photo('Won', png, _dc=False)
        assert [c[0] for c in calls] == ['sendAnimation', 'sendPhoto'] and texts == [], (calls, texts)
        calls.clear()
        urllib.request.urlopen = fake(urllib.error.URLError(TimeoutError('timed out')), 'ok')   # never got there whole: the still card goes
        R.tg_photo('Won', png, _dc=False)
        assert [c[0] for c in calls] == ['sendAnimation', 'sendPhoto'] and texts == [], (calls, texts)
        calls.clear()
        R.animate.gif_of = lambda p: None
        urllib.request.urlopen = fake(TimeoutError('The read operation timed out'), 'ok')       # an album: sent whole, no answer
        assert sharecard.tg_album('t', 'c', [png, png2], 'short caption') is True and [c[0] for c in calls] == ['sendMediaGroup'], calls
        calls.clear()
        urllib.request.urlopen = fake(urllib.error.HTTPError('u', 400, 'Bad Request', {}, None))
        assert sharecard.tg_album('t', 'c', [png, png2], 'short caption') is False and [c[0] for c in calls] == ['sendMediaGroup'], calls
    finally:
        urllib.request.urlopen, R.tg, R.QUIET_TG, R.animate.gif_of = saved[:4]
        R.animate = had_cards
        for k, v in (('TELEGRAM_BOT_TOKEN', saved[4]), ('TELEGRAM_CHAT_ID', saved[5])):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

if __name__ == '__main__':
    main()
