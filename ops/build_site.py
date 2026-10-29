"""Build the standalone papertrades.ai site from the tracker page and its data files.

Usage: python3 build_site.py <tracker_dir> <out_dir>
Writes out_dir/index.html, out_dir/data.json, out_dir/CNAME, out_dir/.nojekyll
"""
import json, os, re, sys
from datetime import datetime, timezone, timedelta

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
  <footer class="st-foot">Paper Trades is an independent one-month experiment: Claude vs Gemini vs ChatGPT. No real money. Not investment or betting advice. Betting content is for adults (18+, or the legal age where you live). If betting is a problem for you or someone you know, free confidential help is available worldwide at <a href="https://www.gamblingtherapy.org" target="_blank" rel="noopener">gamblingtherapy.org</a>.<br>Privacy: no accounts, no ads and no cookies. Visits are counted with <a href="https://www.goatcounter.com" target="_blank" rel="noopener">GoatCounter</a>, which stores no personal data; your settings (language, theme, Beginner mode) are saved only in your own browser. © 2026 Paper Trades. All rights reserved.</footer>
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
  '<span><span class="st-count" data-draw="countdown">—</span> left until final scoring on Nov 28</span>\n      <span class="st-clock">New York <b class="st-count" data-draw="clock">—</b></span>\n      <span class="st-clock">Hong Kong <b class="st-count" data-draw="clock-hk">—</b></span>\n      <span class="st-clock">UTC <b class="st-count" data-draw="clock-utc">—</b></span>\n      <span class="st-clock st-since"><span class="st-since-who">Last update</span> <b class="st-count" data-draw="since-update">—</b></span>\n      <span class="st-clock"><span class="st-mkt" data-draw="market">—</span> <span class="st-mkt" data-draw="market-cn">—</span></span>\n      <label class="st-lang notranslate" translate="no" title="Language"><span aria-hidden="true">🌐</span><select id="lang-pick" aria-label="Language"><option value="en">English</option><option value="zh-CN">中文 (简体)</option><option value="zh-TW">中文 (繁體)</option><option value="hi">हिन्दी</option><option value="es">Español</option><option value="fr">Français</option><option value="ar">العربية</option><option value="bn">বাংলা</option><option value="pt">Português</option><option value="ru">Русский</option><option value="id">Bahasa Indonesia</option><option value="ur">اردو</option><option value="de">Deutsch</option><option value="ja">日本語</option><option value="ko">한국어</option><option value="tr">Türkçe</option></select></label> <button type="button" class="st-theme" id="sound-btn" aria-pressed="false" title="Play a cha-ching when an AI makes C$100 or more">🔈 Sound off</button> <button type="button" class="st-theme" id="beginner-btn" aria-pressed="false" title="Plain-English explanations for people new to markets and betting">🎓 Beginner</button> <button type="button" class="st-theme" id="theme-btn">Light mode</button>', 1)
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
  (function () {
    const btn = document.getElementById('theme-btn');
    if (!btn) return;
    const MODES = ['dark', 'light', 'reader'], NAME = { dark: 'Dark mode', light: 'Light mode', reader: 'Reader mode' };
    const cur = () => document.documentElement.dataset.theme || 'dark';
    const show = () => { const n = MODES[(MODES.indexOf(cur()) + 1) % 3]; btn.textContent = NAME[n]; btn.title = 'Now: ' + NAME[cur()] + '. Click for ' + NAME[n] + '.'; btn.setAttribute('aria-label', 'Switch to ' + NAME[n] + ' (now ' + NAME[cur()] + ')'); };
    btn.addEventListener('click', () => {
      const n = MODES[(MODES.indexOf(cur()) + 1) % 3];
      if (n === 'dark') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = n;
      try { localStorage.setItem('pt-theme', n); } catch (e) {}
      show();
      if (dash.redraw) dash.redraw();
    });
    show();
  })();
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
      const f = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' });
      const HOLIDAY = { '2026-11-26': 'Thanksgiving' }, EARLY = { '2026-11-27': 780 };   // US markets: closed / 1:00 p.m. ET close
      const tick = () => {
        const parts = Object.fromEntries(f.formatToParts(new Date()).map((x) => [x.type, x.value]));
        const mins = Number(parts.hour) * 60 + Number(parts.minute);
        const day = parts.year + '-' + parts.month + '-' + parts.day;
        const open = !['Sat', 'Sun'].includes(parts.weekday) && !HOLIDAY[day] && mins >= 570 && mins < (EARLY[day] || 960);
        el.textContent = open ? '● US market open' + (EARLY[day] ? ' (closes 1 p.m. ET)' : '') : HOLIDAY[day] ? '○ US market closed (' + HOLIDAY[day] + ')' : '○ US market closed';
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
/* Dark is the default; the theme button switches to a soft light mode (remembered per viewer). */
:root, :root { --font-sans: "IBM Plex Sans Condensed", system-ui, sans-serif; --font-serif: "IBM Plex Mono", ui-monospace, monospace;
 --color-bg:#0b0b0a; --color-panel:#121210; --color-fg:#f2e9d8; --color-fg-muted:#9b927f; --color-border-line:#2b2923;
 --color-ok:#3ddc84; --color-warn:#ffb000; --color-bad:#ff5a4e; --cds-text-secondary:#9b927f; --cds-surface-popover:#1a1916; --cds-border:#3a372f;
 --cds-chart-grid:#1e1d19; --cds-chart-axis:#3a372f; --cds-chart-reference:#6b6555;
 --series-1:#ffb000; --series-2:#4fc3f7; --series-3:#3ddc84; --series-4:#e8d48b; --cds-radius:2px; color-scheme:dark;
 --accent:#ffb000; --accent-bg:rgba(255,176,0,.06); --card-inset:#1d1c18; --title:#ffffff; }
:root[data-theme="light"] {
 --color-bg:#e6e1d6; --color-panel:#efebe2; --color-fg:#24221d; --color-fg-muted:#625b4d; --color-border-line:#cdc4b0;
 --color-ok:#137a46; --color-warn:#9a5c00; --color-bad:#b8352b; --cds-text-secondary:#625b4d; --cds-surface-popover:#efebe2; --cds-border:#c2b8a2;
 --cds-chart-grid:#dbd4c5; --cds-chart-axis:#bdb29b; --cds-chart-reference:#857c6a;
 --series-1:#a86400; --series-2:#1d6fa5; --series-3:#137a46; --series-4:#82661d; color-scheme:light;
 --accent:#9a5c00; --accent-bg:rgba(154,92,0,.07); --card-inset:#e9e4d9; --title:#24221d; }
:root[data-theme="reader"] {
 --color-bg:#f4ecd8; --color-panel:#f8f1e1; --color-fg:#433a2c; --color-fg-muted:#7a6d58; --color-border-line:#e0d4b8;
 --color-ok:#3f7d4f; --color-warn:#8a5a1c; --color-bad:#a24a3d; --cds-text-secondary:#7a6d58; --cds-surface-popover:#f8f1e1; --cds-border:#d8caa9;
 --cds-chart-grid:#e9dfc7; --cds-chart-axis:#cdbf9f; --cds-chart-reference:#9c8f76;
 --series-1:#8a5a1c; --series-2:#3d6e8f; --series-3:#3f7d4f; --series-4:#8a7340; color-scheme:light;
 --accent:#8a5a1c; --accent-bg:rgba(138,90,28,.06); --card-inset:#f1e8d2; --title:#3a3125; }
:root[data-theme="reader"] body { font-size: 17px; line-height: 1.65; letter-spacing: .005em; }
:root[data-theme="reader"] .st-note, :root[data-theme="reader"] p { line-height: 1.7; }
:root:not(#pt-a):not(#pt-b) { --ai-chatgpt:#f2f2f2; }   /* ChatGPT: white on dark, near-black on light */
:root[data-theme="light"]:not(#pt-a):not(#pt-b), :root[data-theme="reader"]:not(#pt-a):not(#pt-b) { --ai-chatgpt:#3a3125; }
body { background:var(--color-bg); }
.st-title { font-family: var(--font-serif); text-transform: uppercase; letter-spacing: .08em; color: var(--accent); font-size: 26px; }
.st-title::before { content: "▮ "; color:var(--accent); }
.st-card { border-color:var(--color-border-line); box-shadow: inset 0 1px 0 var(--card-inset); }
.st-big { font-family: var(--font-serif); font-weight:500; letter-spacing:-.02em; color:var(--color-fg); }
.st-label, .st-table th, .st-h2 { font-family: var(--font-serif); text-transform: uppercase; letter-spacing:.06em; }
.st-label { color:var(--accent); }
.st-h2 { font-size: 14px; color:var(--accent); }
.st-tab { font-family: var(--font-serif); text-transform: uppercase; letter-spacing:.06em; font-size:13px; }
.st-tab[aria-selected="true"] { color:var(--accent); border-bottom-color:var(--accent); }
.st-notice { border-color:var(--accent); background: var(--accent-bg); }
.st-table td { font-family: var(--font-serif); font-size: 13px; }
.st-progress .st-count { font-family: var(--font-serif); color:var(--accent); }

  .st-title { display: flex; align-items: center; gap: 14px; color: var(--title); }
  .st-title::before { content: none; }
  .st-logo { width: 1.4em; height: 1.4em; flex: none; border-radius: 8px; box-shadow: 0 0 0 1px var(--color-border-line); }
  .st-clock { display: inline-flex; align-items: baseline; gap: 8px; }
  .st-mkt { font-family: var(--font-serif); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--color-fg-muted); }
  .st-mkt.is-open { color: var(--color-ok); }
  .st-mkt.is-lunch { color: var(--color-warn); }
  .st-mkt + .st-mkt { margin-left: 10px; }
  .st-progress .st-count { font-variant-numeric: tabular-nums; }
  .st-sources a { color: var(--color-fg-muted); }
  .st-theme { margin-left: auto; font: 600 12px var(--font-serif); text-transform: uppercase; letter-spacing: .06em; color: var(--color-fg);
    background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: 999px; padding: 6px 12px; cursor: pointer; min-height: 32px; }
  .st-theme:hover { border-color: var(--accent); }
  .st-theme:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
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
      setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: '/' + name, title: 'Tab: ' + name }); } catch (e) {} },
      params: () => ({}), setParams() {}, resetParams() {}, refresh() {}, redraw() { schedule(); },
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
        .then((json) => { base = json; Object.assign(raw, json); status = 'ok'; let m = (window.ptLeader ? window.ptLeader(json) : json.leader) || 'claude'; if (m !== 'claude' && json.models && json.models[m]) api.useModel(m); else { modelListeners.forEach((fn) => { try { fn('claude'); } catch (e) {} }); runAll(); } })
        .catch((e) => { console.error('data.json failed to load', e); status = 'error'; runAll(); });
      // live refresh: every minute while the page is open, check the tiny data.ver fingerprint; download data.json only when it changed
      let ver = null;
      const getVer = () => fetch('data.ver?v=' + Date.now(), { cache: 'no-store' }).then((r) => r.ok ? r.text() : null).then((t) => (t || '').trim() || null).catch(() => null);
      setInterval(() => {
        if (!ver && base && base.ver) ver = base.ver;
        if (document.hidden) return;
        getVer().then((v) => {
          if (v && ver && v === ver) return null;   // nothing new
          const next = v;
          return fetch('data.json?v=' + Date.now(), { cache: 'no-store' }).then((r) => r.ok ? r.json() : null).then((json) => { if (json && next) ver = next; return json; });
        }).then((json) => {
          const sig = (j) => JSON.stringify([j.history, j.rivals_history, j.trades, j.rivals_trades, j.allin_history]).length + ':' + JSON.stringify(j.history).slice(-80) + JSON.stringify(j.rivals_history).slice(-80);
          if (!json || !base || sig(json) === sig(base)) return;
          const old = base; base = json; Object.assign(raw, json);
          const m = api.model; Object.keys(cache).forEach((k) => delete cache[k]); if (m !== 'claude' && json.models && json.models[m]) api.useModel(m); else runAll();
          try { if (window.ptOnData) window.ptOnData(old, json); } catch (e) { console.error(e); }
        }).catch(() => {});
      }, 60 * 1000);
    });
    return api;
  })();
"""

# Live preview picture for shared links: the race card with the current standings (falls back to the logo picture).
OG_V = ''
LEADER = 'claude'
STANDINGS = []
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import racecard, hashlib
    _fx = json.load(open(os.path.join(SRC, 'fx.json')))
    _rows, _big = racecard.standings(float(_fx.get('usdcad') or 1.38), None, SRC)
    _sig = hashlib.sha1(json.dumps([[r['id'], round(r['total'] / 50)] for r in _rows]).encode()).hexdigest()[:10]
    _ogj = os.path.join(SRC, 'og.json')
    _old = json.load(open(_ogj)).get('sig') if os.path.exists(_ogj) else None
    _tab, _ = racecard.races(None, SRC)
    _sig = hashlib.sha1(json.dumps({e: [[m, round(p / 50)] for m, p in v] for e, v in _tab.items()}).encode()).hexdigest()[:10]
    if _tab and (_sig != _old or not os.path.exists(os.path.join(OUT, 'og.png'))):
        _now = datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
        racecard.races_card(_tab, None, 'Live standings · ' + _now.strftime('%a %b %-d, %-I:%M %p ET'), os.path.join(OUT, 'og.png'))
        json.dump({'sig': _sig, 'at': _now.isoformat()}, open(_ogj, 'w'))
    OG_V = _sig
    STANDINGS = [{'id': r['id'], 'total': round(r['total'], 2)} for r in _rows]
    LEADER = _rows[0]['id'] if _rows and len(_rows) > 1 and _rows[0]['total'] != _rows[1]['total'] else 'claude'
except Exception as _e:
    print('preview picture not updated:', _e)

SPLASH = '<div id="pt-splash" aria-hidden="true">\n  <style>\n    #pt-splash { position: fixed; inset: 0; z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 22px; background: #0b0b0a; transition: opacity .38s ease; }\n    #pt-splash.out { opacity: 0; pointer-events: none; }\n    #pt-splash .sp-logo { width: 112px; height: 112px; }\n    #pt-splash .sp-grid { stroke: #1f2a24; stroke-width: .6; }\n    #pt-splash .sp-line { stroke-dasharray: 40; stroke-dashoffset: 40; animation: sp-draw .8s cubic-bezier(.6,.1,.2,1) .15s forwards; }\n    #pt-splash .sp-dot { opacity: 0; transform-origin: 25px 11px; animation: sp-pop .35s ease-out .9s forwards; }\n    #pt-splash .sp-name { display: flex; gap: .06em; font: 600 clamp(26px, 6vw, 44px)/1 "IBM Plex Mono", ui-monospace, monospace; letter-spacing: .22em; color: #f2e9d8; }\n    #pt-splash .sp-name span { opacity: 0; transform: translateY(14px); animation: sp-up .45s ease-out forwards; }\n    #pt-splash .sp-sub { opacity: 0; font: 500 clamp(13px, 3.4vw, 17px)/1.3 "IBM Plex Sans Condensed", system-ui, sans-serif; letter-spacing: .04em; color: #9b927f; animation: sp-fade .5s ease-out 1.05s forwards; }\n    #pt-splash .sp-sub b { font-weight: 600; }\n    @keyframes sp-draw { to { stroke-dashoffset: 0; } }\n    @keyframes sp-pop { from { opacity: 0; transform: scale(.2); } to { opacity: 1; transform: scale(1); } }\n    @keyframes sp-up { to { opacity: 1; transform: none; } }\n    @keyframes sp-fade { to { opacity: 1; } }\n    @media (prefers-reduced-motion: reduce) { #pt-splash { display: none; } }\n  </style>\n  <svg class="sp-logo" viewBox="0 0 32 32">\n    <rect width="32" height="32" rx="7" fill="#17201c"/>\n    <path class="sp-grid" d="M4 10H28M4 16H28M4 22H28"/>\n    <path class="sp-line" d="M7 22l6-6 4 4 8-9" stroke="#4cc283" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>\n    <circle class="sp-dot" cx="25" cy="11" r="2.4" fill="#3ddc84"/>\n  </svg>\n  <div class="sp-name">PAPER TRADES</div>\n  \n  <script>\n    (function () {\n      var el = document.getElementById(\'pt-splash\'); if (!el) return;\n      if (window.matchMedia && window.matchMedia(\'(prefers-reduced-motion: reduce)\').matches) { el.remove(); return; }\n      var n = el.querySelector(\'.sp-name\'), t = n.textContent; n.textContent = \'\';\n      for (var i = 0; i < t.length; i++) { var s = document.createElement(\'span\'); s.textContent = t[i] === \' \' ? \'\\u00a0\' : t[i]; s.style.animationDelay = (0.45 + i * 0.04) + \'s\'; n.appendChild(s); }\n      var done = false;\n      function finish() { if (done) return; done = true; el.classList.add(\'out\'); setTimeout(function () { el.remove(); }, 420); if (!location.hash || location.hash === \'#overview\') window.scrollTo(0, 0); }\n      setTimeout(finish, 1750);\n      [\'click\', \'keydown\', \'touchstart\'].forEach(function (e) { window.addEventListener(e, finish, { once: true, passive: true }); });\n    })();\n  </script>\n</div>\n'   # opening animation (plain string: its CSS braces must not be read as placeholders)
html = f"""<!doctype html>
<html lang="en">
<head>
<script>try {{ const t = localStorage.getItem('pt-theme'); if (t === 'light' || t === 'reader') document.documentElement.dataset.theme = t; }} catch (e) {{}}</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Paper Trades - AI Trading Experiment</title>
<script data-goatcounter="https://jojojoj.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
<meta name="description" content="Claude vs Gemini vs ChatGPT: AI models trade head to head with pretend money and real prices, Oct 28 to Nov 28, 2026. Stocks, crypto, China stocks, metals, energy, options, currencies, a safe control, sports bets and prediction markets. Every decision logged. Not investment advice.">
<meta property="og:title" content="Paper Trades - AI Trading Experiment">
<meta property="og:site_name" content="Paper Trades">
<meta property="og:description" content="Claude vs Gemini vs ChatGPT: AI models trade head to head with pretend money and real prices, Oct 28 to Nov 28, 2026. Stocks, crypto, China stocks, metals, energy, options, currencies, a safe control, sports bets and prediction markets. Every decision logged. Not investment advice.">
<meta property="og:image" content="https://papertrades.ai/og.png?v={OG_V}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Paper Trades live standings: Claude vs Gemini vs ChatGPT in ten separate races, profit since the Oct 28 restart">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Paper Trades - AI Trading Experiment">
<meta name="twitter:image" content="https://papertrades.ai/og.png?v={OG_V}">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Paper Trades">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
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
{SPLASH}
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
for name in ('holdings', 'history', 'bets', 'log', 'rules', 'benchmark', 'indexes', 'events', 'prices', 'trades', 'bench_history', 'ledger', 'review', 'take', 'report', 'factcheck', 'plans', 'profile'):
    data[name] = json.load(open(os.path.join(SRC, name + '.json')))
data['sources'] = json.load(open(os.path.join(SRC, 'sources.json')))
rv = os.path.join(SRC, 'rivals.json')
r = json.load(open(rv)) if os.path.exists(rv) else {'models': {}, 'trades': [], 'history': [], 'takes': []}
# Profit on every closed trade (average cost) and every settled bet, so every trade table can show what went in,
# what came back and the profit. Buys and open bets are marked open. Sells carry "cost" (what that part cost) and "pnl".
def _annotate_rivals(r):
    lots = {}
    bets = {(mid, b['id']): b for mid, m in (r.get('models') or {}).items() for e, bk in (m.get('books') or {}).items() for b in bk.get('bets', [])}
    for t in sorted(r.get('trades', []), key=lambda t: t['at']):
        a = t['action']
        if a in ('Bet', 'Parlay'):
            t['stake'] = round(float(t.get('amount') or 0), 2)
            b = bets.get((t.get('model'), t.get('bet')))
            if b:
                t['to_win'] = b.get('to_win'); t['status'] = b.get('status')
                if b.get('status') in ('Won', 'Lost', 'Push', 'Void'):
                    t['result'] = float(b.get('result') or 0)
            continue
        if a in ('Won', 'Lost', 'Push', 'Void'):
            b = bets.get((t.get('model'), t.get('bet')))
            if b:
                t['stake'] = b.get('stake'); t['pnl'] = round(float(b.get('result') or 0), 2)
            continue
        key = (t.get('model'), t['experiment'], f"{t['symbol']}|{t['outcome']}" if t.get('outcome') else t['symbol'])
        L = lots.setdefault(key, {'qty': 0.0, 'cost': 0.0})
        qty, amt = float(t.get('qty') or 0), float(t.get('amount') or 0)
        if a in ('Buy', 'Short'):
            L['qty'] += qty; L['cost'] += amt
        elif a in ('Sell', 'Cover', 'Settled', 'Expired') and L['qty'] > 1e-12:
            f = min(1.0, qty / L['qty']) if qty else 1.0
            part = L['cost'] * f
            pnl = (part - amt) if a == 'Cover' else (amt - part)   # a short made money if it cost less to buy back than it raised
            t['cost'] = round(part, 2); t['pnl'] = round(pnl, 2)
            L['qty'] -= L['qty'] * f; L['cost'] -= part


def _annotate_claude(trades):
    lots = {}
    for t in sorted(trades, key=lambda t: datetime.fromisoformat(str(t['at']).replace('Z', '+00:00'))):
        a, china = t['action'], t['portfolio'] == 'China'
        val = float((t.get('usd') if china else t.get('cad')) or 0)
        px = float((t.get('price_local') if china else t.get('price_usd')) or 0)
        units = float(t.get('shares') or t.get('qty') or 0) or ((float(t.get('cny') or 0) if china else val) / px if px else 0)
        L = lots.setdefault((t['portfolio'], t['holding'], 'short' if a in ('Short', 'Cover') else 'long'), {'u': 0.0, 'c': 0.0})
        if a in ('Buy', 'Short'):
            L['u'] += units; L['c'] += val
        elif a in ('Sell', 'Cover', 'Settled', 'Expired') and L['u'] > 1e-12:
            f = min(1.0, units / L['u']) if units else 1.0
            part = L['c'] * f
            t['cost'] = round(part, 2); t['pnl'] = round((part - val) if a == 'Cover' else (val - part), 2)
            L['u'] -= L['u'] * f; L['c'] -= part


try:
    _annotate_rivals(r)
    _annotate_claude(data['trades'])
except Exception as _e:
    print('trade profits not added:', _e)
data['rivals_models'] = [{'id': k, **{x: v.get(x) for x in ('label', 'company', 'model', 'started', 'exps', 'last_run')}, 'books': v['books']} for k, v in r['models'].items()]
for k in ('trades', 'history', 'takes'):
    data['rivals_' + k] = r[k]
_cut = (min(datetime.now(timezone.utc), datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)) - __import__('datetime').timedelta(days=2)).isoformat()   # stops moving after the race
data['fx_all'] = [{'cur': k, 'per_usd': v} for k, v in (r.get('fx_all') or {}).items()]
data['fx_meta'] = [json.load(open(os.path.join(SRC, 'fx.json')))]
_ai = [{'id': 'claude', 'started': (r.get('claude_allin') or {}).get('started'), 'books': (r.get('claude_allin') or {}).get('books', {})}] if r.get('claude_allin') else []
data['allin_models'] = _ai + [{'id': k, 'started': v.get('started'), 'books': {e: b for e, b in v['books'].items() if e.startswith('AllIn')}} for k, v in r['models'].items()]
data['allin_trades'] = [t for t in r['trades'] if str(t.get('experiment', '')).startswith('AllIn')]
data['allin_history'] = [h for h in r['history'] if str(h.get('experiment', '')).startswith('AllIn')]
data['rivals_trades'] = [t for t in r['trades'] if not str(t.get('experiment', '')).startswith('AllIn') and t.get('model') != 'claude']
data['rivals_history'] = [h for h in r['history'] if not str(h.get('experiment', '')).startswith('AllIn') and h.get('model') != 'claude']
data['factcheck'] = [dict(x, checker=x.get('checker', 'claude')) for x in data['factcheck']] + [x for x in r.get('factchecks', [])]   # from now on Gemini checks Claude; Claude's one earlier self-check stays visible
_cl = max((datetime.fromisoformat(h['at'].replace('Z', '+00:00')) for h in data['history']), default=None)
data['checkins'] = ([{'id': 'claude', 'at': _cl.isoformat() if _cl else None, 'status': 'ok'}] +
                    [{'id': k, 'at': (v.get('last_run') or {}).get('at'), 'status': (v.get('last_run') or {}).get('status', '')} for k, v in r['models'].items()])
data['geo'] = [json.load(open(os.path.join(SRC, 'geo.json')))] if os.path.exists(os.path.join(SRC, 'geo.json')) else []
data['profiles'] = data['profile'] + r.get('profiles', [])
_lp = {}
for _p in r.get('plans', []):
    _lp[(_p.get('model'), _p.get('experiment'), _p.get('horizon'))] = _p   # the site shows only the newest plan per AI, race and card
data['rivals_plans'] = list(_lp.values())
data['plans'] = list({(x.get('experiment'), x.get('horizon')): x for x in data.get('plans', [])}.values())   # Claude's: newest per race and card
# Betting minimums (no weekly minimum since Oct 28, 5:30 p.m. ET): C$3,000 a day and C$100,000 in total by Nov 28 for every AI.
# The daily minimum becomes 25% of the betting balance (Sports bankroll + Predictions value) once that is under C$12,000.
from zoneinfo import ZoneInfo as _ZI
_ny = _ZI('America/New_York')
_BFS, _BEND = '2026-10-28T17:45:00+00:00', '2026-11-28T21:00:00+00:00'
def _when(x):
    return datetime.fromisoformat(str(x).replace('Z', '+00:00'))
_rows = {'claude': [(b.get('placed_at'), float(b.get('stake_cad') or 0)) for b in data['bets'] if b.get('placed_at')] +
                   [(t['at'], float(t.get('cad') or 0)) for t in data['trades'] if t['portfolio'] == 'Predictions' and t['action'] == 'Buy' and not str(t['holding']).startswith('[')]}
for _t in r.get('trades', []):
    if _t.get('experiment') in ('Sports', 'Predictions') and _t.get('action') in ('Bet', 'Buy') and _t.get('model') in ('gemini', 'chatgpt') and not _t.get('void'):
        _rows.setdefault(_t['model'], []).append((_t['at'], float(_t.get('amount') or 0)))
def _betbal(mid):
    if mid == 'claude':
        sp = 100000.0 + sum(float(b.get('result_cad') or 0) for b in data['bets'] if b.get('status') not in ('Open', None)) - sum(float(x['amount']) for x in r.get('claude_penalties', []))
        return sp + sum(float(h.get('value_cad') or 0) for h in data['holdings'] if h['portfolio'] == 'Predictions')
    m = (r.get('models') or {}).get(mid) or {}
    bk, fxr = m.get('books') or {}, r.get('fx') or {}
    tot = 0.0
    if 'Sports' in bk:
        tot += 100000.0 + sum(x['result'] for x in bk['Sports'].get('bets', []) if x['status'] not in ('Open', 'Void')) - sum(float(x['amount']) for x in bk['Sports'].get('penalties', []))
    if 'Predictions' in bk:
        pb = bk['Predictions']
        def _cad(q):
            amt = q['qty'] * q.get('last', q['entry'])
            usd = amt if q['pcur'] == 'USD' else amt / fxr.get('USDCNY', 7) if q['pcur'] == 'CNY' else amt / fxr.get('USDCAD', 1.4)
            return usd if pb['cur'] == 'USD' else usd * fxr.get('USDCAD', 1.4)
        tot += pb['cash'] + sum(_cad(q) for q in pb['positions'].values())
    return tot or 200000.0
data['betmins'] = []
_today = datetime.now(_ny).date()
for _m in ('claude', 'gemini', 'chatgpt'):
    _rs = [(a, v) for a, v in _rows.get(_m, []) if _when(a) >= _when(_BFS)]
    _bal = _betbal(_m)
    _dmin = 3000.0 if _bal >= 12000 else max(1.0, round(_bal * 0.25, 2))
    _d, _dlast = _when(_BFS).astimezone(_ny).date(), _when(_BEND).astimezone(_ny).date()
    while _d <= min(_today, _dlast):
        _a = datetime(_d.year, _d.month, _d.day, tzinfo=_ny); _b = datetime.combine(_d + timedelta(days=1), datetime.min.time(), tzinfo=_ny)
        _a, _b = max(_a, _when(_BFS)), min(_b, _when(_BEND))
        data['betmins'].append({'model': _m, 'week': 'Day', 'day': _d.isoformat(), 'start': _a.isoformat(), 'end': _b.isoformat(), 'min': _dmin,
                                'wagered': round(sum(v for a, v in _rs if _a <= _when(a) < _b), 2)})
        _d += timedelta(days=1)
    data['betmins'].append({'model': _m, 'week': 'Total', 'start': _BFS, 'end': _BEND, 'min': 100000, 'wagered': round(sum(v for a, v in _rs), 2), 'day_min': _dmin})
# which experiments each AI leads right now (highest value of the three; ties lead nothing)
_LBL = {'Stocks': 'Stocks', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy', 'Options': 'Options',
        'Currencies': 'Currencies', 'Safe': 'Play it safe', 'Sports': 'Sports', 'Predictions': 'Prediction markets'}
_last = {}
for _h in sorted(data['history'], key=lambda h: _when(h['at']) if '_when' in globals() else 0):
    _last[('claude', _h['portfolio'])] = float(_h['value'])
for _h in sorted(r.get('history', []), key=lambda h: h['at']):
    if _h.get('model') in ('gemini', 'chatgpt') and _h['experiment'] in _LBL:
        _last[(_h['model'], _h['experiment'])] = float(_h['value'])
for _s in STANDINGS:
    _s['leads'] = []
for _e, _lab in _LBL.items():
    _vals = {m: _last.get((m, _e)) for m in ('claude', 'gemini', 'chatgpt')}
    if None in _vals.values():
        continue
    _top = max(_vals.values())
    _who = [m for m, v in _vals.items() if abs(v - _top) < 0.5]
    if len(_who) == 1:
        for _s in STANDINGS:
            if _s['id'] == _who[0]:
                _s['leads'].append(_lab)
data['standings'] = STANDINGS
# Race standings per experiment (each race is separate): value now, profit since the restart, and what each AI holds
_FS = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)
_EXPS = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions']
_es = {e: [] for e in _EXPS}
def b2c(x, cur='CAD'):
    return ('US$' if cur == 'USD' else 'C$') + f'{float(x):,.0f}'
def _lastv(rows):
    rows = sorted(rows, key=lambda x: _when(x[0]))
    pre = [v for a, v in rows if _when(a) <= _FS]
    return (rows[-1][1] if rows else None), (pre[-1] if pre else 100000.0)
_cfx = (r.get('fx') or {}).get('USDCAD', 1.4)
_ctot = 0.0   # Claude's total profit since the restart, for the same ELIMINATED flag the others get
for _e in _EXPS:
    _v, _b = _lastv([(h['at'], float(h['value'])) for h in data['history'] if h['portfolio'] == _e])
    if _v is not None:
        _ctot += (max(_v, 0) - _b) * (_cfx if _e == 'China' else 1)
for _e in _EXPS:
    v, b0 = _lastv([(h['at'], float(h['value'])) for h in data['history'] if h['portfolio'] == _e])
    if v is not None:
        hv = [(h['holding'], float(h.get('value_cad') or h.get('value_usd') or 0)) for h in data['holdings'] if h['portfolio'] == _e and float(h.get('value_cad') or h.get('value_usd') or 0) > 0.5]
        _shorts = [f"{h['holding']} (short)" for h in data['holdings'] if h['portfolio'] == _e and float(h.get('value_cad') or h.get('value_usd') or 0) < -0.5]   # shorts are holdings too
        hv += [(f"{b['pick']} ({b['event']})", float(b['stake_cad'])) for b in data['bets'] if _e == 'Sports' and b.get('status') == 'Open']
        held = [n for n, _ in hv if not str(n).startswith('Cash')] + _shorts
        lt = [t for t in data['trades'] if t['portfolio'] == _e and not str(t.get('holding', '')).startswith('[')]
        lt = max(lt, key=lambda t: _when(t['at']), default=None)
        # Sports: the latest bet placed or settled; a result always says the stake and the profit (never just one number)
        _bev = []
        for b in (data['bets'] if _e == 'Sports' else []):
            if b.get('placed_at'):
                _bev.append((b['placed_at'], f"Bet {b2c(b['stake_cad'])} on {b['pick']}"))
            if b.get('status') in ('Won', 'Lost', 'Push', 'Void') and (b.get('settled_at') or b.get('placed_at')):
                _r = float(b.get('result_cad') or 0)
                _txt = {'Won': f"Won {b['pick']}: +{b2c(_r)} profit on a {b2c(b['stake_cad'])} stake",
                        'Lost': f"Lost {b['pick']}: −{b2c(-_r)} (the {b2c(b['stake_cad'])} stake)",
                        'Push': f"Push on {b['pick']}: {b2c(b['stake_cad'])} stake returned, no profit",
                        'Void': f"Void {b['pick']}: {b2c(b['stake_cad'])} stake returned, no profit"}[b['status']]
                _sa = b.get('settled_at') or b['placed_at']
                _bev.append((_sa if _when(_sa) >= _when(b['placed_at']) else b['placed_at'], _txt))
        lb = max(_bev, key=lambda x: _when(x[0]), default=None)
        last = ({'at': lb[0], 'text': lb[1]} if lb else
                {'at': lt['at'], 'text': f"{lt['action']} {lt['holding']}" + (f" ({b2c(lt['cad'])})" if lt.get('cad') else '')} if lt else None)
        _es[_e].append({'id': 'claude', 'value': round(v, 2), 'profit': round(max(v, 0) - b0, 2), 'holds': held[:20], 'busted': v <= 0, 'eliminated': _ctot <= -100000,
                        'pie': [{'name': n, 'value': round(x, 2)} for n, x in hv], 'last': last})
    for _mid, _m in (r.get('models') or {}).items():
        v, _ = _lastv([(h['at'], float(h['value'])) for h in r.get('history', []) if h['model'] == _mid and h['experiment'] == _e])
        bk = (_m.get('books') or {}).get(_e)
        if v is None or not bk:
            continue
        _fx = r.get('fx') or {'USDCAD': 1.4, 'USDCNY': 7.1}
        def _val(q, cur=bk.get('cur', 'CAD')):
            amt = abs(q['qty'] * q.get('last', q['entry']))
            usd = amt if q['pcur'] == 'USD' else amt / _fx['USDCNY'] if q['pcur'] == 'CNY' else amt / _fx['USDCAD']
            return usd if cur == 'USD' else usd * _fx['USDCAD']
        pos = [((q.get('name') or k) + (' (short)' if q.get('qty', 0) < 0 else ''), _val(q)) for k, q in bk.get('positions', {}).items() if abs(q.get('qty', 0)) > 1e-9]
        ob = [(f"{b['pick_team']} ({b['event']})", b['stake']) for b in bk.get('bets', []) if b['status'] == 'Open']
        held = [n for n, _ in pos + ob]
        pie = pos + ob + ([('Cash', bk['cash'])] if _e != 'Sports' and bk.get('cash', 0) > 0.5 else [])
        if _e == 'Sports':
            pie.append(('Not bet', max(0.0, v - sum(x for _, x in ob))))
        lt = max([t for t in r.get('trades', []) if t.get('model') == _mid and t['experiment'] == _e and t['action'] not in ('Void',)], key=lambda t: _when(t['at']), default=None)
        if lt and lt['action'] in ('Won', 'Lost', 'Push') and lt.get('stake') is not None:   # a result says the stake and the profit
            _p = float(lt.get('pnl') if lt.get('pnl') is not None else lt['amount'])
            _nm = lt.get('name') or lt['symbol']
            _tx = (f"Won {_nm}: +{b2c(_p)} profit on a {b2c(lt['stake'])} stake" if lt['action'] == 'Won' else
                   f"Lost {_nm}: −{b2c(abs(_p))} (the {b2c(lt['stake'])} stake)" if lt['action'] == 'Lost' else
                   f"Push on {_nm}: {b2c(lt['stake'])} stake returned, no profit")
            last = {'at': lt['at'], 'text': _tx}
        elif lt and lt['action'] in ('Sell', 'Cover', 'Settled', 'Expired') and lt.get('pnl') is not None:
            last = {'at': lt['at'], 'text': f"{lt['action']} {lt.get('name') or lt['symbol']} ({b2c(abs(lt['amount']), lt['cur'])}): {'+' if lt['pnl'] >= 0 else '−'}{b2c(abs(lt['pnl']), lt['cur'])} profit"}
        else:
            last = {'at': lt['at'], 'text': f"{lt['action']} {lt.get('name') or lt['symbol']} ({b2c(abs(lt['amount']), lt['cur'])})"} if lt else None
        _es[_e].append({'id': _mid, 'value': round(v, 2), 'profit': round(max(v, 0) - 100000.0, 2), 'holds': held[:20],
                        'pie': [{'name': n, 'value': round(x, 2)} for n, x in pie if x > 0.5], 'last': last,
                        'busted': bool(bk.get('busted')), 'eliminated': bool(_m.get('eliminated'))})
    _es[_e].sort(key=lambda x: -x['value'])


# Scoreboard stats per AI per race: biggest drop from a high, win rate and best/worst closed trade, and a "lucky or skilled" score
def _closed_claude(e):
    """Profit or loss of each closed trade or settled bet in Claude's race e, at average cost."""
    out, lots = [], {}
    if e == 'Sports':
        return [{'name': b['pick'], 'pnl': float(b['result_cad'] or 0), 'at': b.get('settled_at') or b['placed_at']}
                for b in data['bets'] if b.get('status') in ('Won', 'Lost') and b.get('result_cad') is not None and _when(b['placed_at']) >= _FS]
    for t in sorted([t for t in data['trades'] if t['portfolio'] == e and _when(t['at']) >= _FS], key=lambda t: _when(t['at'])):
        a, amt, px = t['action'], float(t.get('cad') or 0), float(t.get('price_usd') or 0)
        if not amt or not px:
            continue
        side = 'short' if a in ('Short', 'Cover') else 'long'
        L = lots.setdefault((t['holding'], side), {'u': 0.0, 'c': 0.0})
        u = amt / px
        if a in ('Buy', 'Short'):
            L['u'] += u; L['c'] += amt
        elif a in ('Sell', 'Cover', 'Settled', 'Expired') and L['u'] > 1e-12:
            f = min(1.0, u / L['u']) if a in ('Sell', 'Cover') else 1.0
            part = L['c'] * f
            out.append({'name': t['holding'], 'pnl': (amt - part) if side == 'long' else (part - amt), 'at': t['at']})
            L['u'] -= L['u'] * f; L['c'] -= part
    return out


def _closed_rival(mid, e):
    bk = (((r.get('models') or {}).get(mid) or {}).get('books') or {}).get(e) or {}
    if e == 'Sports':
        return [{'name': b['pick_team'], 'pnl': float(b['result']), 'at': b.get('settled_at') or b['placed_at']}
                for b in bk.get('bets', []) if b['status'] in ('Won', 'Lost')]
    out, cost = [], {}
    for t in [t for t in r.get('trades', []) if t.get('model') == mid and t['experiment'] == e]:
        key = f"{t['symbol']}|{t['outcome']}" if t.get('outcome') else t['symbol']
        c = cost.setdefault(key, {'qty': 0.0, 'cost': 0.0})
        if t['action'] in ('Buy', 'Short'):
            c['qty'] += t['qty']; c['cost'] += t['amount'] if t['action'] == 'Buy' else -t['amount']
        elif t['action'] in ('Sell', 'Cover', 'Settled', 'Expired') and c['qty'] > 0:
            f = min(1.0, t['qty'] / c['qty']); part = c['cost'] * f
            out.append({'name': t.get('name') or t['symbol'], 'pnl': (-t['amount'] if t['action'] == 'Cover' else t['amount']) - part, 'at': t['at']})
            c['cost'] -= part; c['qty'] -= t['qty']
    return out


def _stats(series, closed, now_v, base=100000.0):
    pts = [base] + [v for _, v in sorted(series, key=lambda x: _when(x[0]))] + [now_v]
    peak, dd, dd_amt = pts[0], 0.0, 0.0
    for v in pts:
        peak = max(peak, v)
        if peak > 0 and (peak - v) / peak > dd:
            dd, dd_amt = (peak - v) / peak, peak - v
    ret = (now_v - base) / base
    wins = [c for c in closed if c['pnl'] > 0.005]
    s = {'drop_pct': round(100 * dd, 2), 'drop': round(dd_amt, 2), 'ret_pct': round(100 * ret, 2), 'closed': len(closed),
         'wins': len(wins), 'win_rate': round(100 * len(wins) / len(closed)) if closed else None}
    if closed:
        b, w = max(closed, key=lambda c: c['pnl']), min(closed, key=lambda c: c['pnl'])
        s['best'] = {'name': b['name'], 'pnl': round(b['pnl'], 2)}
        s['worst'] = {'name': w['name'], 'pnl': round(w['pnl'], 2)}
    # return per unit of the worst dip; below a 0.5% dip there is too little risk taken to judge
    s['skill'] = round(ret / dd, 2) if dd >= 0.005 else None
    return s


for _e in _EXPS:
    for row in _es[_e]:
        if row['id'] == 'claude':
            ser = [(h['at'], float(h['value'])) for h in data['history'] if h['portfolio'] == _e and _when(h['at']) >= _FS]
            row['stats'] = _stats(ser, _closed_claude(_e), row['value'], row['value'] - row['profit'] if row['value'] > 0 else 100000.0)
        else:
            ser = [(h['at'], float(h['value'])) for h in r.get('history', []) if h['model'] == row['id'] and h['experiment'] == _e]
            row['stats'] = _stats(ser, _closed_rival(row['id'], _e), row['value'])
data['exp_standings'] = _es


# Moments: each time the lead changes hands in a race (each race on its own, never totals), replayed from the value history (so it rebuilds the same
# on either workflow). A new leader must be ahead by at least C$250 in a race (C$500 overall); at most one moment per race per 12 hours.
def _moments():
    ev = [(_when(h['at']), 'claude', h['portfolio'], float(h['value'])) for h in data['history'] if h['portfolio'] in _EXPS and _when(h['at']) >= _FS]
    ev += [(_when(h['at']), h['model'], h['experiment'], float(h['value'])) for h in r.get('history', [])
           if h.get('model') in ('gemini', 'chatgpt') and h['experiment'] in _EXPS and _when(h['at']) >= _FS]
    ev.sort(key=lambda x: x[0])
    base = {}
    for _e in _EXPS:   # Claude's values on Oct 28 before the restart time count from its restart value
        base[('claude', _e)] = _lastv([(h['at'], float(h['value'])) for h in data['history'] if h['portfolio'] == _e])[1]
    cur, lead, last_at, out = {}, {}, {}, []
    fx = float(_cfx)
    groups = {}
    for at, mid, e, v in ev:   # values saved at the same moment are applied together, so a half-updated race never looks like a lead change
        groups.setdefault((at, e), []).append((mid, v))
    for (at, e) in sorted(groups, key=lambda k: k[0]):
        for mid, v in groups[(at, e)]:
            cur[(mid, e)] = max(v, 0) - base.get((mid, e), 100000.0)
        if at > RACE_END_DT:
            break
        for race in (e,):   # each race on its own: lead changes are never counted on totals (owner's rule)
            if race == 'Overall':
                if any((m, x) not in cur for m in ('claude', 'gemini', 'chatgpt') for x in ('Stocks',)):
                    continue
                vals = {m: sum(cur.get((m, x), 0.0) * (fx if x == 'China' else 1) for x in _EXPS) for m in ('claude', 'gemini', 'chatgpt')}
                need = 500.0
            else:
                if any((m, race) not in cur for m in ('claude', 'gemini', 'chatgpt')):
                    continue
                vals = {m: cur[(m, race)] for m in ('claude', 'gemini', 'chatgpt')}
                need = 250.0 if race != 'China' else 250.0 / fx
            order = sorted(vals, key=lambda m: -vals[m])
            top, gap = order[0], vals[order[0]] - vals[order[1]]
            was = lead.get(race)
            if was is None:
                if gap >= need:
                    lead[race] = top
                continue
            if top != was and gap >= need:
                lead[race] = top
                if race in last_at and (at - last_at[race]).total_seconds() < 12 * 3600:
                    continue
                last_at[race] = at
                out.append({'id': f"{race}-{at.strftime('%Y%m%d%H%M')}-{top}", 'at': at.isoformat().replace('+00:00', 'Z'), 'race': race,
                            'who': top, 'over': was, 'lead': round(gap, 2), 'cur': 'USD' if race == 'China' else 'CAD',
                            'profit': {m: round(vals[m], 2) for m in vals}})
    return out[::-1][:20]


def _forecasts():
    """Forecast rounds (sealed until all three AIs are in or the round closes) and the Best forecaster table."""
    import forecasts as FC
    now = datetime.fromisoformat(os.environ['PT_NOW']) if os.environ.get('PT_NOW') else datetime.now(timezone.utc)   # PT_NOW: tests only
    allf = [x for x in r.get('forecasts', []) if x.get('model') in ('gemini', 'chatgpt')] + [x for x in FC.load_claude() if x.get('model') == 'claude']
    ser = {}
    for h in data['history']:
        if h['portfolio'] in FC.RACES:
            ser.setdefault(('claude', h['portfolio']), []).append((_when(h['at']), float(h['value'])))
    for h in r.get('history', []):
        if h.get('model') in ('gemini', 'chatgpt') and h['experiment'] in FC.RACES:
            ser.setdefault((h['model'], h['experiment']), []).append((_when(h['at']), float(h['value'])))
    base = {('claude', e): _lastv([(h['at'], float(h['value'])) for h in data['history'] if h['portfolio'] == e])[1] for e in FC.RACES}

    def actual(race, at):
        out = {}
        for m in FC.AIS:
            pts = sorted(ser.get((m, race), []), key=lambda p: p[0])
            pts = [v for t, v in pts if t <= at]
            if not pts:
                return None
            out[m] = max(pts[-1], 0) - base.get((m, race), 100000.0)
        return out
    rounds, table = [], {m: {'id': m, 'points': 0.0, 'calls': 0, 'rounds': 0, 'missed': 0, 'right': 0} for m in FC.AIS}
    for rd in FC.ROUNDS:
        if now < FC.t(rd['open']):
            rounds.append({'id': rd['id'], 'open': rd['open'], 'due': rd['due'], 'week': rd['week'], 'week_label': rd['week_label'], 'state': 'upcoming', 'sent': []})
            continue
        got = {x['model']: x for x in allf if x['round'] == rd['id']}
        closed = now >= FC.t(rd['due'])
        sealed = not closed and len(got) < 3
        row = {'id': rd['id'], 'open': rd['open'], 'due': rd['due'], 'week': rd['week'], 'week_label': rd['week_label'], 'final_label': FC.FINAL_LABEL,
               'state': 'sealed' if sealed else 'shown', 'sent': sorted(got)}
        if not sealed:
            row['forecasts'] = {m: {'at': x['at'], 'races': x['races']} for m, x in got.items()}
            res = {}
            for tgt, at in (('week', FC.t(rd['week'])), ('final', FC.t(FC.FINAL))):
                if now < at + timedelta(minutes=10):
                    continue
                for race in FC.RACES:
                    a = actual(race, at)
                    if not a:
                        continue
                    top = max(a.values())
                    res.setdefault(race, {})[tgt] = {'winners': [m for m in FC.AIS if abs(a[m] - top) < 0.005], 'profit': {m: round(a[m], 2) for m in FC.AIS}, 'points': {}}
                    for m, x in got.items():
                        call = (x['races'].get(race) or {}).get(tgt)
                        pts = FC.score_call(call, a) if call else None
                        if pts is not None:
                            res[race][tgt]['points'][m] = pts
                            table[m]['points'] += pts; table[m]['calls'] += 1
                            if max(call, key=call.get) in res[race][tgt]['winners']:
                                table[m]['right'] += 1
            row['results'] = res
        for m in FC.AIS:
            if m in got:
                table[m]['rounds'] += 1
            elif closed:
                table[m]['missed'] += 1
        rounds.append(row)
    tb = sorted(table.values(), key=lambda x: (-x['points'], -x['calls']))
    for x in tb:
        x['points'] = round(x['points'], 1)
        x['avg'] = round(x['points'] / x['calls'], 1) if x['calls'] else None
    return {'rounds': rounds, 'table': tb}


try:
    data['forecasts'] = _forecasts()
except Exception as _e:
    print('forecasts not built:', _e)
    data['forecasts'] = {'rounds': [], 'table': []}
try:
    RACE_END_DT = datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)
    data['moments'] = _moments()
except Exception as _e:
    print('moments not built:', _e)
    data['moments'] = []
data['penalties'] = [dict(x, model='claude') for x in r.get('claude_penalties', [])] + \
    [dict(x, model=_mid) for _mid, _m in (r.get('models') or {}).items() for x in ((_m.get('books') or {}).get('Sports') or {}).get('penalties', [])]
data['leader'] = LEADER   # the AI leading the race on total profit; the page opens on it unless the viewer picked one
try:
    data['price_audit'] = [json.load(open(os.path.join(SRC, 'price_audit.json')))]   # Claude's prices vs the feeds (ops/price_audit.py)
except Exception:
    data['price_audit'] = []
# Moments for the world to see, good and bad, by the same rules for all three AIs (owner's request, Oct 29):
# lead changes, any single trade or bet that made or lost at least 1,000 (1% of a race), penalties, fact checks found wrong, busts.
def _all_moments():
    out = [dict(m, type='lead') for m in data.get('moments', [])]
    BIG = 1000.0
    def add(at, who, race, typ, amt=None, what='', extra=None):
        try:
            if _when(at) < _FS or _when(at) > RACE_END_DT:
                return
        except Exception:
            return
        out.append({'id': f"{typ}-{race}-{who}-{_when(at).strftime('%Y%m%d%H%M%S')}", 'at': _when(at).isoformat().replace('+00:00', 'Z'), 'type': typ, 'who': who,
                    'race': race, 'amount': None if amt is None else round(amt, 2), 'cur': 'USD' if race == 'China' else 'CAD', 'what': what, **(extra or {})})
    for t in data.get('rivals_trades', []):
        pnl = t.get('pnl')
        if pnl is not None and abs(pnl) >= BIG and t.get('experiment') in _EXPS:
            nm = re.sub(r'^[A-Z]+: ', '', str(t.get('name') or t.get('symbol') or ''))
            add(t['at'], t['model'], t['experiment'], 'win' if pnl > 0 else 'loss', pnl, nm, {'action': t.get('action')})
    for t in data.get('trades', []):
        pnl = t.get('pnl')
        if pnl is not None and abs(pnl) >= BIG and t.get('portfolio') in _EXPS:
            add(t['at'], 'claude', t['portfolio'], 'win' if pnl > 0 else 'loss', pnl, str(t.get('holding', '')), {'action': t.get('action')})
    for b in data.get('bets', []):
        if b.get('status') in ('Won', 'Lost') and b.get('settled_at'):
            pnl = float(b.get('result_cad') or 0) if b['status'] == 'Won' else -float(b.get('stake_cad') or 0)
            if abs(pnl) >= BIG:
                add(b['settled_at'], 'claude', 'Sports', 'win' if pnl > 0 else 'loss', pnl, str(b.get('pick', '')), {'action': b['status']})
    for x in data.get('penalties', []):
        if x.get('at'):
            add(x['at'], x.get('model', 'claude'), 'Sports', 'penalty', -abs(float(x.get('amount') or x.get('cad') or 0)), 'less than the daily betting minimum')
    for f in data.get('factcheck', []):
        if f.get('verdict') == 'wrong' and f.get('model') in ('claude', 'gemini', 'chatgpt'):
            add(f['at'], f['model'], 'Overall', 'factcheck', None, str(f.get('text', ''))[:200], {'checker': f.get('checker')})
    for mid, m in (r.get('models') or {}).items():
        for e, b in (m.get('books') or {}).items():
            if b.get('busted') and e in _EXPS:
                add(b['busted'], mid, e, 'busted', None, 'lost everything in this race')
    out.sort(key=lambda m: m['at'], reverse=True)
    return out[:40]
try:
    data['moments_all'] = _all_moments()
except Exception as _e:
    print('moments_all not built:', _e)
    data['moments_all'] = [dict(m, type='lead') for m in data.get('moments', [])]
data['day_reports'] = r.get('day_reports', [])   # Gemini's and ChatGPT's own Race Reports (Claude's are in report.json)
data['rivals_thoughts'] = [x for x in r.get('thoughts', []) if x['at'].replace('Z', '+00:00') >= _cut]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_views
data['models'] = model_views.build(r, {k: data[k] for k in ('indexes', 'bench_history', 'benchmark', 'prices', 'events')} | {'fx': json.load(open(os.path.join(SRC, 'fx.json')))})
times = [r['at'] for r in data['log'] + data['history']]
data['meta'] = [{'refreshed_at': max(times, key=lambda t: datetime.fromisoformat(t))}]
# audit.json: the exact instructions each AI gets and its latest raw reply, plus the corrections log (loaded only by the Audit tab)
try:
    _corr = json.load(open(os.path.join(SRC, 'corrections.json')))
except Exception:
    _corr = []
_aud = {'built_at': datetime.now(timezone.utc).isoformat(), 'corrections': _corr, 'ais': {}}
try:
    _tp = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TASK_PROMPT.md')).read()
except Exception:
    _tp = ''
_cl = next((c for c in data.get('checkins', []) if c.get('id') == 'claude'), {})
_aud['ais']['claude'] = {'model': 'Claude Opus 5.5 (claude-opus-5-5)', 'at': _cl.get('at'), 'how': 'Claude runs as scheduled sessions that follow the instructions below (and the longer runbook they point to), look up prices on the web, and record every trade with ops/update.py.', 'prompt': _tp, 'reply': None}
for _mid, _a in (r.get('audit') or {}).items():
    _aud['ais'][_mid] = {'model': _a.get('model'), 'at': _a.get('at'), 'searches': _a.get('searches'), 'how': 'Sent by ops/rivals.py at each check-in; this is the full text of the latest one, and the raw reply exactly as the AI sent it.',
                         'prompt': _a.get('prompt', ''), 'reply': _a.get('reply', '')}
try:
    import rulebook
    _aud['rulebook'] = rulebook.build()   # every rule, from the same constants the race code enforces
except Exception as _e:
    print('rulebook not built:', _e)
json.dump(_aud, open(os.path.join(OUT, 'audit.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
# data.ver: a tiny fingerprint of the data (also stored inside data.json as "ver"). Open pages check data.ver every minute
# and download data.json only when it changed.
import hashlib as _hl
data.pop('ver', None)
data['ver'] = _hl.sha1(json.dumps(data, separators=(',', ':'), sort_keys=True).encode()).hexdigest()[:16]
json.dump(data, open(os.path.join(OUT, 'data.json'), 'w'), separators=(',', ':'))  # compact: smaller and faster to load
open(os.path.join(OUT, 'data.ver'), 'w').write(data['ver'])

open(os.path.join(OUT, 'CNAME'), 'w').write('papertrades.ai\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')
print('built', os.path.getsize(os.path.join(OUT, 'index.html')), 'bytes index,', os.path.getsize(os.path.join(OUT, 'data.json')), 'bytes data')
