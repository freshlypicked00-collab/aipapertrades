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

if __name__ == '__main__':
    main()
