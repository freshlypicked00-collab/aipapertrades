"""Build the standalone papertrades.ai site from the tracker page and its data files.

Usage: python3 build_site.py <tracker_dir> <out_dir>
Writes out_dir/index.html, out_dir/data.json, out_dir/CNAME, out_dir/.nojekyll
"""
import json, os, re, sys
from datetime import datetime, timezone

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
page = open(os.path.join(SRC, 'index.html')).read()

# ---- split the tracker page into its style, markup and script ----
i, j = page.index('<style>'), page.index('</style>')
k, l = page.index('<script>'), page.rindex('</script>')
style = page[i + 7:j]
markup = page[j + 8:k]
script = page[k + 8:l]

def sub(text, a, b, count=None):
    n = text.count(a)
    assert n and (count is None or n == count), (n, a[:80])
    return text.replace(a, b)

# fonts: own families, neutral names
for part in ('style', 'markup', 'script'):
    t = locals()[part]
    t = t.replace('var(--font-anthropic-sans)', 'var(--font-sans)').replace('var(--font-anthropic-serif)', 'var(--font-serif)')
    locals()[part]  # noqa
    if part == 'style': style = t
    elif part == 'markup': markup = t
    else: script = t

# SVG colours via style() so CSS variables always resolve
script = re.sub(r"\.attr\('(stroke|fill)', '(var\(--[a-z0-9-]+\))'\)", r".style('\1', '\2')", script)

# site name and About wording
markup = sub(markup, '<h1 class="st-title">Simulation Tracker</h1>', '<h1 class="st-title"><svg class="st-logo" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#17201c"/><path d="M7 22l6-6 4 4 8-9" stroke="#4cc283" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Paper Trades</span></h1>', 1)
markup = sub(markup, '<p class="st-note">Each tab lists the sources used for it; the Ledger tab has the full list.</p>',
             '<p class="st-note">Data last refreshed <b data-draw="refreshed">—</b>. Each tab lists the sources used for it; the Ledger tab has the full list.</p>', 1)
# sources list at the very end of the About card
markup = sub(markup, '  </section>\n</div>\n', '''  </section>
  <footer class="st-foot">Paper Trades is an independent 30-day experiment. No real money. Not investment or betting advice.</footer>
</div>
''', 1)

script += """
  dash.draw('refreshed', (el) => {
    const d = dash.data('meta');
    el.textContent = d.status === 'ok' && d.data[0] ? stFmt.when(d.data[0].refreshed_at) : '—';
  });
"""

# --- live New York clock, market status, and a per-second countdown
markup = sub(markup, '<span><span class="st-count" data-draw="countdown">—</span> left until final scoring on Nov 28</span>',
  '<span><span class="st-count" data-draw="countdown">—</span> left until final scoring on Nov 28</span>\n      <span class="st-clock">New York <b class="st-count" data-draw="clock">—</b></span>\n      <span class="st-clock">Hong Kong <b class="st-count" data-draw="clock-hk">—</b></span>\n      <span class="st-clock">UTC <b class="st-count" data-draw="clock-utc">—</b></span>\n      <span class="st-clock"><span class="st-mkt" data-draw="market">—</span> <span class="st-mkt" data-draw="market-cn">—</span></span>', 1)
script = sub(script, """el.textContent = d + (d === 1 ? ' day, ' : ' days, ') + h + (h === 1 ? ' hour' : ' hours');
      };
      tick();
      return setInterval(tick, 60 * 1000);""", """const m = Math.floor((ms % (60 * 60 * 1000)) / 60000);
        const s = Math.floor((ms % 60000) / 1000);
        const p2 = (n) => String(n).padStart(2, '0');
        el.textContent = d + 'd ' + p2(h) + 'h ' + p2(m) + 'm ' + p2(s) + 's';
      };
      tick();
      return setInterval(tick, 1000);""", 1)
script += """
  dash.draw('clock', {
    mount: (el) => {
      const f = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit', second: '2-digit' });
      const tick = () => { el.textContent = f.format(new Date()); };
      tick();
      return setInterval(tick, 1000);
    },
    update: () => {},
    unmount: (el, id) => clearInterval(id)
  });
  dash.draw('clock-hk', {
    mount: (el) => {
      const f = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Hong_Kong', hour: 'numeric', minute: '2-digit', second: '2-digit' });
      const tick = () => { el.textContent = f.format(new Date()); };
      tick();
      return setInterval(tick, 1000);
    },
    update: () => {},
    unmount: (el, id) => clearInterval(id)
  });
  dash.draw('clock-utc', {
    mount: (el) => {
      const f = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
      const tick = () => { el.textContent = f.format(new Date()); };
      tick();
      return setInterval(tick, 1000);
    },
    update: () => {},
    unmount: (el, id) => clearInterval(id)
  });
  dash.draw('market-cn', {
    mount: (el) => {
      const f = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Shanghai', weekday: 'short', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' });
      const tick = () => {
        const parts = Object.fromEntries(f.formatToParts(new Date()).map((x) => [x.type, x.value]));
        const mins = (Number(parts.hour) % 24) * 60 + Number(parts.minute);
        const weekday = !['Sat', 'Sun'].includes(parts.weekday);
        const open = weekday && ((mins >= 570 && mins < 690) || (mins >= 780 && mins < 900));
        const lunch = weekday && mins >= 690 && mins < 780;
        el.textContent = open ? '● China market open' : lunch ? '◐ China lunch break' : '○ China market closed';
        el.title = lunch ? 'Shanghai and Shenzhen pause 11:30 a.m. to 1:00 p.m. Beijing time' : 'Shanghai and Shenzhen trade 9:30–11:30 a.m. and 1:00–3:00 p.m. Beijing time, weekdays';
        el.classList.toggle('is-open', open);
        el.classList.toggle('is-lunch', lunch);
      };
      tick();
      return setInterval(tick, 30 * 1000);
    },
    update: () => {},
    unmount: (el, id) => clearInterval(id)
  });
  dash.draw('market', {
    mount: (el) => {
      const f = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' });
      const tick = () => {
        const parts = Object.fromEntries(f.formatToParts(new Date()).map((x) => [x.type, x.value]));
        const mins = Number(parts.hour) * 60 + Number(parts.minute);
        const open = !['Sat', 'Sun'].includes(parts.weekday) && mins >= 570 && mins < 960;
        el.textContent = open ? '● US market open' : '○ US market closed';
        el.classList.toggle('is-open', open);
      };
      tick();
      return setInterval(tick, 30 * 1000);
    },
    update: () => {},
    unmount: (el, id) => clearInterval(id)
  });
"""

TERMINAL = """
:root, :root { --font-sans: "IBM Plex Sans Condensed", system-ui, sans-serif; --font-serif: "IBM Plex Mono", ui-monospace, monospace;
 --color-bg:#0b0b0a; --color-panel:#121210; --color-fg:#f2e9d8; --color-fg-muted:#9b927f; --color-border-line:#2b2923;
 --color-ok:#3ddc84; --color-warn:#ffb000; --color-bad:#ff5a4e; --cds-text-secondary:#9b927f; --cds-surface-popover:#1a1916; --cds-border:#3a372f;
 --cds-chart-grid:#1e1d19; --cds-chart-axis:#3a372f; --cds-chart-reference:#6b6555;
 --series-1:#ffb000; --series-2:#4fc3f7; --series-3:#3ddc84; --series-4:#e8d48b; --cds-radius:2px; color-scheme:dark; }
body { background:#0b0b0a; }
.st-title { font-family: var(--font-serif); text-transform: uppercase; letter-spacing: .08em; color: #ffb000; font-size: 26px; }
.st-title::before { content: "▮ "; color:#ffb000; }
.st-card { border-color:#2b2923; box-shadow: inset 0 1px 0 #1d1c18; }
.st-big { font-family: var(--font-serif); font-weight:500; letter-spacing:-.02em; color:#f2e9d8; }
.st-label, .st-table th, .st-h2 { font-family: var(--font-serif); text-transform: uppercase; letter-spacing:.06em; }
.st-label { color:#ffb000; }
.st-h2 { font-size: 14px; color:#ffb000; }
.st-tab { font-family: var(--font-serif); text-transform: uppercase; letter-spacing:.06em; font-size:13px; }
.st-tab[aria-selected="true"] { color:#ffb000; border-bottom-color:#ffb000; }
.st-notice { border-color:#ffb000; background: rgba(255,176,0,.06); }
.st-table td { font-family: var(--font-serif); font-size: 13px; }
.st-progress .st-count { font-family: var(--font-serif); color:#ffb000; }

  .st-title { display: flex; align-items: center; gap: 14px; color: #ffffff; }
  .st-title::before { content: none; }
  .st-logo { width: 1.4em; height: 1.4em; flex: none; border-radius: 8px; box-shadow: 0 0 0 1px #2b2923; }
  .st-clock { display: inline-flex; align-items: baseline; gap: 8px; }
  .st-mkt { font-family: var(--font-serif); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--color-fg-muted); }
  .st-mkt.is-open { color: var(--color-ok); }
  .st-mkt.is-lunch { color: var(--color-warn); }
  .st-mkt + .st-mkt { margin-left: 10px; }
  .st-progress .st-count { font-variant-numeric: tabular-nums; }
  .st-sources a { color: var(--color-fg-muted); }
"""

TOKENS = """
  :root {
    --font-sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
    --font-serif: "Source Serif 4", Georgia, "Times New Roman", serif;
    --color-bg: #f6f7f5; --color-panel: #ffffff; --color-fg: #17201c; --color-fg-muted: #5b6660;
    --color-border-line: #dfe3df; --color-ok: #17804a; --color-warn: #b7791f; --color-bad: #c0392b;
    --cds-text-secondary: #5b6660; --cds-surface-popover: #ffffff; --cds-border: #d3d8d4;
    --cds-shadow-popover: 0 6px 24px rgba(20, 30, 25, .12);
    --cds-chart-grid: #e8ebe8; --cds-chart-axis: #b9c0bb; --cds-chart-reference: #8a948e;
    --series-1: #2563a8; --series-2: #c2610c; --series-3: #2f8a57; --series-4: #a3842a;
    --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 14px; --cds-gap-lg: 20px; --cds-gap-xl: 28px;
    --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 18px;
    --cds-radius: 10px;
    --cds-font-size-caption: 12.5px; --cds-font-size-body: 14.5px; --cds-font-size-heading: 18px; --cds-font-size-title: 30px;
    --cds-font-weight-medium: 500; --cds-dur-slow: 300ms;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --color-bg: #101412; --color-panel: #171c19; --color-fg: #e6ebe7; --color-fg-muted: #9aa59f;
      --color-border-line: #2a312d; --color-ok: #4cc283; --color-warn: #e0a53d; --color-bad: #ef6b5b;
      --cds-text-secondary: #9aa59f; --cds-surface-popover: #1d2420; --cds-border: #323a35;
      --cds-shadow-popover: 0 6px 24px rgba(0, 0, 0, .45);
      --cds-chart-grid: #232a26; --cds-chart-axis: #3d4641; --cds-chart-reference: #6f7a74;
      --series-1: #6aa5e8; --series-2: #f0954a; --series-3: #5fc48a; --series-4: #d8b75a;
      color-scheme: dark;
    }
  }
  [hidden] { display: none !important; }
  html { -webkit-text-size-adjust: 100%; }
  body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-sans); font-size: var(--cds-font-size-body); line-height: 1.5; }
  #dash-root { max-width: 1180px; margin-inline: auto; padding-block: 28px 40px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
  a { color: inherit; text-underline-offset: 2px; }
  .st-h3 { font-size: var(--cds-font-size-body); font-weight: 600; margin: var(--cds-gap-sm) 0 0; }
  .st-sources { margin: 0; padding-left: 1.2em; columns: 2 18rem; font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); }
  .st-sources li { break-inside: avoid; margin-bottom: 2px; }
  .st-foot { font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); text-align: center; padding-block: var(--cds-pad-md); }
"""

SHIM = r"""
  // Minimal data layer: loads data.json, runs calculations and draws the page.
  window.dash = (() => {
    const raw = {}; let status = 'loading';
    const calcs = {}; const cache = {};
    const listeners = []; const draws = []; const modelListeners = []; let base = null;
    const mounted = new WeakMap();
    const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    const rowsOf = (id) => {
      if (id in raw) return raw[id];
      if (id in calcs) {
        if (!(id in cache)) cache[id] = calcs[id].fn(...calcs[id].inputs.map(rowsOf));
        return cache[id];
      }
      return [];
    };
    const api = {
      get colors() { return ['--series-1', '--series-2', '--series-3', '--series-4', '--series-1', '--series-2', '--series-3', '--series-4'].map(cssColor); },
      data(id) {
        if (status !== 'ok') return { status, data: [], columns: [], meta: [], refreshing: false };
        if (!(id in raw) && !(id in calcs)) return { status: 'missing', data: [], columns: [], meta: [], refreshing: false };
        let data;
        try { data = rowsOf(id); } catch (e) { console.error('calc failed', id, e); return { status: 'error', data: [], columns: [], meta: [], message: String(e) }; }
        return { status: 'ok', data, columns: data[0] ? Object.keys(data[0]) : [], meta: [], refreshing: false };
      },
      onData(fn) { listeners.push(fn); try { fn(); } catch (e) { console.error(e); } },
      calc(id, def) { calcs[id] = def; },
      loader() {},
      draw(name, def) { draws.push([name, def]); },
      setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
      params: () => ({}), setParams() {}, resetParams() {}, refresh() {},
      model: 'claude',
      models() { return base && base.models ? base.models : {}; },
      baseData(id) { return base && base[id] ? base[id] : []; },
      useModel(id) {
        if (!base) return;
        const view = id !== 'claude' && base.models && base.models[id];
        Object.keys(raw).forEach((k) => delete raw[k]);
        Object.assign(raw, base, view || {});
        Object.keys(cache).forEach((k) => delete cache[k]);
        api.model = view ? id : 'claude';
        modelListeners.forEach((fn) => { try { fn(api.model); } catch (e) { console.error(e); } });
        runAll();
      },
      onModel(fn) { modelListeners.push(fn); }
    };
    const visible = (el) => !el.closest('[hidden]');
    const runAll = () => {
      listeners.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
      draws.forEach(([name, def]) => {
        document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => {
          if (!visible(el)) return;
          try {
            if (typeof def === 'function') { def(el); return; }
            if (!mounted.has(el)) { el.replaceChildren(); mounted.set(el, def.mount ? def.mount(el) : undefined); }
            if (def.update) def.update(el, mounted.get(el));
          } catch (e) { console.error('draw failed', name, e); }
        });
      });
    };
    let queued = false;
    const schedule = () => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; runAll(); }); };
    window.addEventListener('DOMContentLoaded', () => {
      runAll();
      new MutationObserver((ms) => { if (ms.some((m) => m.target.matches && m.target.matches('[data-page]'))) schedule(); }).observe(document.getElementById('dash-root'), { attributes: true, attributeFilter: ['hidden'], subtree: true });
      let w = window.innerWidth;
      window.addEventListener('resize', () => { if (window.innerWidth !== w) { w = window.innerWidth; schedule(); } });
      if (window.matchMedia) window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', schedule);
      fetch('data.json?v=' + Date.now(), { cache: 'no-store' })
        .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then((json) => { base = json; Object.assign(raw, json); status = 'ok'; let m = 'claude'; try { m = localStorage.getItem('pt-model') || 'claude'; } catch (e) {} if (m !== 'claude' && json.models && json.models[m]) api.useModel(m); else { modelListeners.forEach((fn) => { try { fn('claude'); } catch (e) {} }); runAll(); } })
        .catch((e) => { console.error('data.json failed to load', e); status = 'error'; runAll(); });
    });
    return api;
  })();
"""

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Paper Trades - AI Trading Experiment</title>
<meta name="description" content="Can an AI trade? Ten separate 30-day experiments with pretend money and real prices: stocks, crypto, China stocks, metals, energy, options, currencies, a safe control, sports bets and prediction markets. Every decision logged. Not investment advice.">
<meta property="og:title" content="Paper Trades - AI Trading Experiment">
<meta property="og:site_name" content="Paper Trades">
<meta property="og:description" content="Can an AI trade? Ten separate 30-day experiments with pretend money and real prices: stocks, crypto, China stocks, metals, energy, options, currencies, a safe control, sports bets and prediction markets. Every decision logged. Not investment advice.">
<meta property="og:image" content="https://papertrades.ai/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Paper Trades logo: a chart line going up">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Paper Trades - AI Trading Experiment">
<meta name="twitter:image" content="https://papertrades.ai/og.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png">
<meta property="og:type" content="website">
<meta property="og:url" content="https://papertrades.ai/">
<meta name="theme-color" content="#0b0b0a">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2317201c'/%3E%3Cpath d='M7 22l6-6 4 4 8-9' stroke='%234cc283' stroke-width='3' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@400;500;600&display=swap">
<style>{TOKENS}
{style}
{TERMINAL}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>{SHIM}</script>
</head>
<body>
<div id="dash-root">
{markup.strip()}
</div>
<script>
{script}
</script>
</body>
</html>
"""
open(os.path.join(OUT, 'index.html'), 'w').write(html)

# ---- data.json ----
data = {}
for name in ('holdings', 'history', 'bets', 'log', 'rules', 'benchmark', 'indexes', 'events', 'prices', 'trades', 'bench_history', 'ledger', 'review', 'take'):
    data[name] = json.load(open(os.path.join(SRC, name + '.json')))
data['sources'] = json.load(open(os.path.join(SRC, 'sources.json')))
rv = os.path.join(SRC, 'rivals.json')
r = json.load(open(rv)) if os.path.exists(rv) else {'models': {}, 'trades': [], 'history': [], 'takes': []}
data['rivals_models'] = [{'id': k, **{x: v.get(x) for x in ('label', 'company', 'model', 'started', 'exps', 'last_run')}, 'books': v['books']} for k, v in r['models'].items()]
for k in ('trades', 'history', 'takes'):
    data['rivals_' + k] = r[k]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_views
data['models'] = model_views.build(r, {k: data[k] for k in ('indexes', 'bench_history', 'benchmark', 'prices', 'events')} | {'fx': json.load(open(os.path.join(SRC, 'fx.json')))})
times = [r['at'] for r in data['log'] + data['history']]
data['meta'] = [{'refreshed_at': max(times, key=lambda t: datetime.fromisoformat(t))}]
json.dump(data, open(os.path.join(OUT, 'data.json'), 'w'), indent=1)

open(os.path.join(OUT, 'CNAME'), 'w').write('papertrades.ai\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')
print('built', os.path.getsize(os.path.join(OUT, 'index.html')), 'bytes index,', os.path.getsize(os.path.join(OUT, 'data.json')), 'bytes data')
