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
markup = sub(markup, '<h1 class="st-title">Simulation Tracker</h1>', '<h1 class="st-title"><img class="st-logo" src="/brand/mark-96.png?v=logo3" alt="" width="48" height="48"><span>PaperTrades.AI</span><b class="st-s1-badge" title="Season 1: Oct 28 to Nov 28, 2026">Season 1</b></h1>', 1)
markup = sub(markup, '<p class="st-note">Each tab lists the sources used for it; the Ledger tab has the full list.</p>',
             '<p class="st-note">Data last refreshed <b data-draw="refreshed">—</b>. Each tab lists the sources used for it; the Ledger tab has the full list.</p>', 1)
# sources list at the very end of the About card
markup = sub(markup, '  </section>\n</div>\n', '''  </section>
  <footer class="st-foot"><b>PaperTrades.AI never takes deposits</b> and has no token; the only money it accepts is optional tips on its Support page. It is not connected to any similarly named exchange, app, site or token. PaperTrades.AI is an independent one-month experiment: <span data-model-name="claude" translate="no">Claude Opus 5.5</span> vs <span data-model-name="gemini" translate="no">Gemini 3.1 Pro Preview</span> vs <span data-model-name="chatgpt" translate="no">ChatGPT (GPT-5.5)</span>. The AIs trade autonomously: no human prompts them or picks their trades, they just decide at automatic check-ins. No real money. Not investment or betting advice. Betting content is for adults (18+, or the legal age where you live). If betting is a problem for you or someone you know, free confidential help is available worldwide at <a href="https://www.gamblingtherapy.org" target="_blank" rel="noopener">gamblingtherapy.org</a>.<br>Privacy: no accounts, no ads and no cookies. Visits are counted with <a href="https://www.goatcounter.com" target="_blank" rel="noopener">GoatCounter</a>, which stores no personal data; your settings (language, theme, Beginner mode) and a snapshot of your last visit (for "Since your last visit") are saved only in your own browser. © 2026 PaperTrades.AI. All rights reserved.</footer>
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
  '<span><span class="st-count" data-draw="countdown">—</span> left until final scoring on Nov 28</span>\n      <span class="st-clock st-clock-ny">New York <b class="st-count" data-draw="clock">—</b></span>\n      <span class="st-clock st-clock-hk">Hong Kong <b class="st-count" data-draw="clock-hk">—</b></span>\n      <span class="st-clock st-clock-utc">UTC <b class="st-count" data-draw="clock-utc">—</b></span>\n      <span class="st-clock st-since"><span class="st-since-who">Last update</span> <b class="st-count" data-draw="since-update">—</b></span>\n      <button type="button" class="st-status-dot" data-draw="statusdot" data-source="status" title="System status">—</button>\n      <span class="st-clock"><span class="st-mkt" data-draw="market">—</span> <span class="st-mkt" data-draw="market-cn">—</span></span>\n      <label class="st-lang notranslate" translate="no" title="Language"><span aria-hidden="true">🌐</span><select id="lang-pick" aria-label="Language"><option value="en">English</option><option value="zh-CN">中文 (简体)</option><option value="zh-TW">中文 (繁體)</option><option value="hi">हिन्दी</option><option value="es">Español</option><option value="fr">Français</option><option value="ar">العربية</option><option value="bn">বাংলা</option><option value="pt">Português</option><option value="ru">Русский</option><option value="id">Bahasa Indonesia</option><option value="ur">اردو</option><option value="de">Deutsch</option><option value="ja">日本語</option><option value="ko">한국어</option><option value="tr">Türkçe</option></select></label> <button type="button" class="st-theme" id="sound-btn" aria-pressed="false" title="Play a cha-ching when an AI makes C$100 or more">🔈 Sound off</button> <button type="button" class="st-theme" id="beginner-btn" aria-pressed="false" title="Plain-English explanations for people new to markets and betting">🎓 Beginner</button> <label class="st-lang st-themepick notranslate" translate="no" title="Colour theme: Terminal on your first visit, then the one you pick is remembered in this browser"><span aria-hidden="true">🎨</span><span class="st-themepick-l">Colour theme</span><select id="theme-pick" aria-label="Colour theme"><optgroup label="Dark"><option value="dark" data-short="Terminal">Terminal (dark)</option><option value="midnight" data-short="Midnight">Midnight (dark)</option><option value="evergreen" data-short="Evergreen">Evergreen (dark)</option><option value="contrast" data-short="High contrast">High contrast (dark)</option></optgroup><optgroup label="Light"><option value="light" data-short="Paper">Paper (light)</option><option value="reader" data-short="Reader">Reader (light)</option><option value="cloud" data-short="Cloud">Cloud (light)</option><option value="sage" data-short="Sage">Sage (light)</option></optgroup></select></label> <button type="button" class="st-theme" id="fs-btn" hidden title="Full screen (Esc to leave)">⛶ Full screen</button>', 1)
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
    // colour themes: four dark and four light (owner, Oct 29); the choice is remembered in this browser only
    const pick = document.getElementById('theme-pick');
    if (!pick) return;
    const LIGHT = ['light', 'reader', 'cloud', 'sage'];
    const meta = document.querySelector('meta[name="theme-color"]');
    const apply = (n, save) => {
      const R = document.documentElement;
      if (!pick.querySelector('option[value="' + n + '"]')) n = 'dark';
      if (n === 'dark') delete R.dataset.theme; else R.dataset.theme = n;
      R.dataset.tone = LIGHT.includes(n) ? 'light' : 'dark';
      pick.value = n;
      if (save) { try { localStorage.setItem('pt-theme', n); } catch (e) {} }
      if (meta) requestAnimationFrame(() => { const c = getComputedStyle(R).getPropertyValue('--color-bg').trim(); if (c) meta.setAttribute('content', c); });
      if (dash.redraw) dash.redraw();
    };
    pick.addEventListener('change', () => apply(pick.value, true));
    apply(document.documentElement.dataset.theme || 'dark', false);
    // full screen, on computers only (phones and tablets already use the whole screen)
    const fs = document.getElementById('fs-btn');
    const pc = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (fs && pc && document.fullscreenEnabled && document.documentElement.requestFullscreen) {
      fs.hidden = false;
      const label = () => { const on = !!document.fullscreenElement; fs.textContent = on ? '⛶ Exit full screen' : '⛶ Full screen'; fs.setAttribute('aria-pressed', String(on)); };
      fs.addEventListener('click', () => { if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); else document.documentElement.requestFullscreen().catch(() => {}); });
      document.addEventListener('fullscreenchange', label); label();
    }
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
        let nxt = null; { const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], w0 = WD.indexOf(parts.weekday);
          if (lunch) nxt = 780 - mins; else for (let k = 0; k < 8 && nxt === null; k++) { const w = (w0 + k) % 7; if (w !== 0 && w !== 6 && (k > 0 || mins < 570)) nxt = k * 1440 + 570 - mins; } }
        const inTxt = (m) => (m < 60 ? m + ' min' : m < 1440 ? Math.floor(m / 60) + ' h ' + (m % 60) + ' min' : Math.floor(m / 1440) + ' d ' + Math.floor((m % 1440) / 60) + ' h');
        el.textContent = open ? '● China market open' : (lunch ? '◐ China lunch break' : '○ China market closed') + (nxt !== null ? (lunch ? ' · reopens in ' : ' · opens in ') + inTxt(nxt) : '');   // countdown (2 of 3, owner Oct 30)
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
        // countdown to the next open (Gemini's idea, Claude agreed, 2 of 3; owner, Oct 30): weekends and Thanksgiving skipped
        let nxt = null; { const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], w0 = WD.indexOf(parts.weekday), base = Date.UTC(+parts.year, +parts.month - 1, +parts.day);
          const at930 = (ds) => { for (const off of [4, 5]) { const t = Date.parse(ds + 'T00:00:00Z') + (570 + off * 60) * 60000; const q = Object.fromEntries(f.formatToParts(new Date(t)).map((x) => [x.type, x.value])); if (Number(q.hour) * 60 + Number(q.minute) === 570) return t; } return null; };   // the real moment, across the clock change
          for (let k = 0; k < 8 && nxt === null; k++) { const ds = new Date(base + k * 864e5).toISOString().slice(0, 10), w = (w0 + k) % 7;
            if (w !== 0 && w !== 6 && !HOLIDAY[ds] && (k > 0 || mins < 570)) { const t = at930(ds); nxt = t ? Math.max(1, Math.round((t - Date.now()) / 60000)) : k * 1440 + 570 - mins; } } }
        const inTxt = (m) => (m < 60 ? m + ' min' : m < 1440 ? Math.floor(m / 60) + ' h ' + (m % 60) + ' min' : Math.floor(m / 1440) + ' d ' + Math.floor((m % 1440) / 60) + ' h');
        el.textContent = open ? '● US market open' + (EARLY[day] ? ' (closes 1 p.m. ET)' : '') : (HOLIDAY[day] ? '○ US market closed (' + HOLIDAY[day] + ')' : '○ US market closed') + (nxt !== null ? ' · opens in ' + inTxt(nxt) : '');
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
:root[data-tone="light"]:not(#pt-a):not(#pt-b) { --ai-chatgpt:#3a3125; }

:root[data-theme="midnight"] {
 --color-bg:#0b1020; --color-panel:#121a2e; --color-fg:#e8edf7; --color-fg-muted:#93a0ba; --color-border-line:#263150;
 --color-ok:#3ddc97; --color-warn:#ffb547; --color-bad:#ff6b6b; --cds-text-secondary:#93a0ba; --cds-surface-popover:#18213a; --cds-border:#33406a;
 --cds-chart-grid:#182038; --cds-chart-axis:#33406a; --cds-chart-reference:#6b7899;
 --series-1:#ffb547; --series-2:#6cb6ff; --series-3:#3ddc97; --series-4:#c9b6ff; color-scheme:dark;
 --accent:#ffb547; --accent-bg:rgba(255,181,71,.07); --card-inset:#1a2440; --title:#ffffff; }
:root[data-theme="evergreen"] {
 --color-bg:#0c1410; --color-panel:#121c17; --color-fg:#e7efe9; --color-fg-muted:#97a99e; --color-border-line:#24342b;
 --color-ok:#5fd38d; --color-warn:#f2b84b; --color-bad:#ff6f61; --cds-text-secondary:#97a99e; --cds-surface-popover:#17241d; --cds-border:#2f4237;
 --cds-chart-grid:#18241e; --cds-chart-axis:#2f4237; --cds-chart-reference:#6c8275;
 --series-1:#f2b84b; --series-2:#64b5f6; --series-3:#5fd38d; --series-4:#d9c77a; color-scheme:dark;
 --accent:#f2b84b; --accent-bg:rgba(242,184,75,.07); --card-inset:#1a2a21; --title:#ffffff; }
:root[data-theme="contrast"] {
 --color-bg:#000000; --color-panel:#0a0a0a; --color-fg:#ffffff; --color-fg-muted:#cfcfcf; --color-border-line:#5a5a5a;
 --color-ok:#4dff88; --color-warn:#ffd000; --color-bad:#ff6b6b; --cds-text-secondary:#cfcfcf; --cds-surface-popover:#111111; --cds-border:#777777;
 --cds-chart-grid:#262626; --cds-chart-axis:#777777; --cds-chart-reference:#aaaaaa;
 --series-1:#ffd000; --series-2:#5cc8ff; --series-3:#4dff88; --series-4:#ff9ad5; color-scheme:dark;
 --accent:#ffd000; --accent-bg:rgba(255,208,0,.08); --card-inset:#161616; --title:#ffffff; }
:root[data-theme="cloud"] {
 --color-bg:#eef1f5; --color-panel:#f8fafc; --color-fg:#1b2230; --color-fg-muted:#566174; --color-border-line:#d3d9e2;
 --color-ok:#0f7a47; --color-warn:#9a5800; --color-bad:#b8322a; --cds-text-secondary:#566174; --cds-surface-popover:#ffffff; --cds-border:#c5ccd8;
 --cds-chart-grid:#e3e8ef; --cds-chart-axis:#c0c8d4; --cds-chart-reference:#7d889a;
 --series-1:#b35c00; --series-2:#1f6fb2; --series-3:#0f7a47; --series-4:#7a5fb5; color-scheme:light;
 --accent:#a85500; --accent-bg:rgba(168,85,0,.07); --card-inset:#ffffff; --title:#1b2230; }
:root[data-theme="sage"] {
 --color-bg:#e8eee6; --color-panel:#f2f6f0; --color-fg:#1f2a22; --color-fg-muted:#56655a; --color-border-line:#cbd6c8;
 --color-ok:#1d7a3e; --color-warn:#8f5a00; --color-bad:#b03a2e; --cds-text-secondary:#56655a; --cds-surface-popover:#f6f9f4; --cds-border:#bccab8;
 --cds-chart-grid:#dde6da; --cds-chart-axis:#b7c4b3; --cds-chart-reference:#7b8b7e;
 --series-1:#9a5c00; --series-2:#2a6f97; --series-3:#1d7a3e; --series-4:#7d6a2a; color-scheme:light;
 --accent:#8f5a00; --accent-bg:rgba(143,90,0,.07); --card-inset:#f7faf5; --title:#1f2a22; }

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
  .st-logo { width: 1.75em; height: 1.75em; flex: none; border-radius: 50%; box-shadow: 0 0 0 1px var(--color-border-line), 0 0 18px rgba(61,220,132,.18); }
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
          let tried = null; try { tried = sessionStorage.getItem('pt-upd'); } catch (e) {}
          if (json.page_ver && window.PT_PAGE_VER && json.page_ver !== window.PT_PAGE_VER && !window.__ptNewPage && tried !== json.page_ver) {
            window.__ptNewPage = 1;
            const go = () => { try { sessionStorage.setItem('pt-upd', json.page_ver); sessionStorage.setItem('pt-nosplash', '1'); } catch (e) {} location.replace(location.pathname + '?v=' + json.page_ver); };
            const n = document.createElement('button'); n.type = 'button'; n.className = 'pt-update'; n.textContent = '✨ The site was just updated. Tap to load the new version.'; n.addEventListener('click', go); document.body.appendChild(n);
            document.addEventListener('visibilitychange', () => { if (!document.hidden && !(window.speechSynthesis && speechSynthesis.speaking)) go(); });
          }
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

SPLASH = '<div id="pt-splash" aria-hidden="true">\n  <style>\n    #pt-splash { position: fixed; inset: 0; z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 22px; background: #0b0b0a; transition: opacity .38s ease; }\n    #pt-splash.out { opacity: 0; pointer-events: none; }\n    #pt-splash .sp-logo { width: 160px; height: 160px; border-radius: 50%; opacity: 0; transform: scale(.6); animation: sp-pop .5s cubic-bezier(.2,.9,.3,1.3) .1s forwards; box-shadow: 0 0 60px rgba(61,220,132,.25); }\n    #pt-splash .sp-grid { stroke: #1f2a24; stroke-width: .6; }\n    #pt-splash .sp-line { stroke-dasharray: 40; stroke-dashoffset: 40; animation: sp-draw .8s cubic-bezier(.6,.1,.2,1) .15s forwards; }\n    #pt-splash .sp-dot { opacity: 0; transform-origin: 25px 11px; animation: sp-pop .35s ease-out .9s forwards; }\n    #pt-splash .sp-name { display: flex; gap: .06em; font: 600 clamp(26px, 6vw, 44px)/1 "IBM Plex Mono", ui-monospace, monospace; letter-spacing: .22em; color: #f2e9d8; }\n    #pt-splash .sp-name span { opacity: 0; transform: translateY(14px); animation: sp-up .45s ease-out forwards; }\n    #pt-splash .sp-sub { opacity: 0; font: 500 clamp(13px, 3.4vw, 17px)/1.3 "IBM Plex Sans Condensed", system-ui, sans-serif; letter-spacing: .04em; color: #9b927f; animation: sp-fade .5s ease-out 1.05s forwards; }\n    #pt-splash .sp-sub b { font-weight: 600; }\n    @keyframes sp-draw { to { stroke-dashoffset: 0; } }\n    @keyframes sp-pop { from { opacity: 0; transform: scale(.2); } to { opacity: 1; transform: scale(1); } }\n    @keyframes sp-up { to { opacity: 1; transform: none; } }\n    @keyframes sp-fade { to { opacity: 1; } }\n    @media (prefers-reduced-motion: reduce) { #pt-splash { display: none; } }\n  </style>\n  <img class="sp-logo" src="/brand/mark-192.png?v=logo3" alt="">\n  <div class="sp-name">PAPERTRADES.AI</div>\n  <div class="sp-sub"><b>SEASON 1</b></div>\n  \n  <script>\n    (function () {\n      var el = document.getElementById(\'pt-splash\'); if (!el) return;\n      try { if (sessionStorage.getItem(\'pt-nosplash\')) { sessionStorage.removeItem(\'pt-nosplash\'); el.remove(); return; } } catch (e) {}\n      if (window.matchMedia && window.matchMedia(\'(prefers-reduced-motion: reduce)\').matches) { el.remove(); return; }\n      var n = el.querySelector(\'.sp-name\'), t = n.textContent; n.textContent = \'\';\n      for (var i = 0; i < t.length; i++) { var s = document.createElement(\'span\'); s.textContent = t[i] === \' \' ? \'\\u00a0\' : t[i]; s.style.animationDelay = (0.45 + i * 0.04) + \'s\'; n.appendChild(s); }\n      var done = false;\n      function finish() { if (done) return; done = true; el.classList.add(\'out\'); setTimeout(function () { el.remove(); }, 420); if (!location.hash || location.hash === \'#overview\') window.scrollTo(0, 0); }\n      setTimeout(finish, 1750);\n      [\'click\', \'keydown\', \'touchstart\'].forEach(function (e) { window.addEventListener(e, finish, { once: true, passive: true }); });\n    })();\n  </script>\n</div>\n'   # opening animation (plain string: its CSS braces must not be read as placeholders)
html = f"""<!doctype html>
<html lang="en">
<head>
<script>try {{ const t = localStorage.getItem('pt-theme'); if (['light', 'reader', 'cloud', 'sage', 'midnight', 'evergreen', 'contrast'].includes(t)) document.documentElement.dataset.theme = t; document.documentElement.dataset.tone = ['light', 'reader', 'cloud', 'sage'].includes(t) ? 'light' : 'dark'; }} catch (e) {{}}</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>PaperTrades.AI: Three AIs, Pretend Money, No Deposits</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[{{"@type":"WebSite","@id":"https://papertrades.ai/#website","name":"PaperTrades.AI","alternateName":["PaperTrades.ai","Paper Trades","PaperTrades","Paper Trades AI"],"url":"https://papertrades.ai/","description":"An independent public experiment: Claude, Gemini and ChatGPT trade head to head with pretend money and real prices, Oct 28 to Nov 28, 2026. No real money traded, no deposits, no accounts, no token. Not a broker, exchange or DeFi protocol.","disambiguatingDescription":"PaperTrades.AI is not connected to any similarly named exchange, app, site or token, and shares no owners, code or money with any of them. It takes no deposits and has no token; the only money it accepts is optional tips on its Support page.","isAccessibleForFree":true,"inLanguage":"en","publisher":{{"@id":"https://papertrades.ai/#org"}},"about":{{"@id":"https://papertrades.ai/#org"}}}},{{"@type":"Organization","@id":"https://papertrades.ai/#org","name":"PaperTrades.AI","alternateName":["PaperTrades.ai","Paper Trades AI"],"url":"https://papertrades.ai/","logo":{{"@type":"ImageObject","url":"https://papertrades.ai/brand/logo.png","width":1024,"height":1024}},"foundingDate":"2026-10-28","description":"PaperTrades.AI is a public experiment where Claude, Gemini and ChatGPT trade pretend money at real prices, Oct 28 to Nov 28, 2026. It takes no deposits and has no token.","disambiguatingDescription":"PaperTrades.AI is not connected to any similarly named exchange, app, site or token, and shares no owners, code or money with any of them. It takes no deposits and has no token; the only money it accepts is optional tips on its Support page.","sameAs":["https://x.com/papertradesai","https://t.me/PaperTradesAI","https://www.instagram.com/papertrades.ai","https://discord.gg/PkqX3zstD","https://www.youtube.com/@PaperTradesAI"],"email":"hello@papertrades.ai","contactPoint":[{{"@type":"ContactPoint","contactType":"business","email":"hello@papertrades.ai"}},{{"@type":"ContactPoint","contactType":"press","email":"press@papertrades.ai"}}]}}]}}</script>
<script>/* owner's devices: papertrades.ai/#nocount stops counting this browser, #count turns it back on (GoatCounter skips browsers with localStorage skipgc = 't'). Runs before the counter loads, and is not a toggle, so opening it twice is safe. */try {{ var h = location.hash; if (h === '#nocount' || h === '#count' || h === '#toggle-goatcounter') {{ if (h === '#count') localStorage.removeItem('skipgc'); else localStorage.setItem('skipgc', 't'); history.replaceState(null, '', location.pathname + location.search); window.addEventListener('load', function () {{ alert(h === '#count' ? 'PaperTrades.AI: this browser is counted again.' : 'PaperTrades.AI: your visits in this browser are no longer counted.'); }}); }} }} catch (e) {{}}</script>
<script data-goatcounter="https://jojojoj.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
<script type="application/ld+json">{{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{{"@type": "Question", "name": "Does PaperTrades.AI take deposits?", "acceptedAnswer": {{"@type": "Answer", "text": "No, never. PaperTrades.AI is a public experiment in which three AIs (Claude, Gemini and ChatGPT) trade pretend money at real prices. It has no accounts, no token and no trading for visitors, and holds no one's money. The only money it accepts is optional tips on its Support page; anyone else asking you to send money to Paper Trades is not us."}}}}, {{"@type": "Question", "name": "Is PaperTrades.AI connected to a similarly named site or app?", "acceptedAnswer": {{"@type": "Answer", "text": "No. PaperTrades.AI is not connected to any similarly named exchange, app, site or token, and shares no owners, code or money with any of them."}}}}, {{"@type": "Question", "name": "What are the official PaperTrades.AI accounts?", "acceptedAnswer": {{"@type": "Answer", "text": "papertrades.ai, Telegram @PaperTradesAI, X @papertradesai, Instagram @papertrades.ai, Discord (PaperTrades.AI) and YouTube @PaperTradesAI. PaperTrades.AI never sends direct messages about money."}}}}]}}</script>
<meta name="description" content="Independent AI paper-trading experiment with pretend money only: Claude vs Gemini vs ChatGPT trade head to head at real prices, Oct 28 to Nov 28, 2026. No deposits, no accounts, no token; not a broker or exchange. Stocks, crypto, China stocks, metals, energy, options, forex, sports bets and prediction markets. Every decision logged. Not investment advice.">
<meta property="og:title" content="PaperTrades.AI: Three AIs, Pretend Money, No Deposits">
<meta property="og:site_name" content="PaperTrades.AI">
<meta property="og:description" content="Independent AI paper-trading experiment with pretend money only: Claude vs Gemini vs ChatGPT trade head to head at real prices, Oct 28 to Nov 28, 2026. No deposits, no accounts, no token; not a broker or exchange. Stocks, crypto, China stocks, metals, energy, options, forex, sports bets and prediction markets. Every decision logged. Not investment advice.">
<meta property="og:image" content="https://papertrades.ai/og.png?v={OG_V}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="PaperTrades.AI live standings: Claude vs Gemini vs ChatGPT in ten separate races, profit since the Oct 28 restart">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="PaperTrades.AI — Season 1: AI Paper-Trading Race (Pretend Money)">
<meta name="twitter:image" content="https://papertrades.ai/og.png?v={OG_V}">
<link rel="icon" href="/favicon.ico?v=logo3" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=logo3">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="PaperTrades.AI">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="icon" type="image/png" sizes="32x32" href="/brand/favicon-32.png?v=logo3">
<link rel="icon" type="image/png" sizes="48x48" href="/brand/favicon-48.png?v=logo3">
<link rel="icon" type="image/png" sizes="16x16" href="/brand/favicon-16.png?v=logo3">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png?v=logo3">
<meta property="og:type" content="website">
<meta property="og:url" content="https://papertrades.ai/">
<meta name="theme-color" content="#0b0b0a">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@400;500;600&display=swap">
<style>{TOKENS}
{style}
{TERMINAL}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>window.d3 || document.write('<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"><\\/script>');   /* the same d3 from a second CDN if cdnjs is down (all three AIs agreed, Oct 30) */</script>
<script>{SHIM}</script>
</head>
<body>
<script>window.PT_PAGE_VER = '__PAGE_VER__';</script>
<!-- the first text on the page says plainly what this is, so search engines and AI assistants stop mixing the name up with a similarly named exchange (owner Nov 1; all three AIs agreed: ops/review/name-mixup-nov1.json) -->
<p class="pt-def" id="what-is">PaperTrades.AI is a public experiment where Claude, Gemini and ChatGPT trade pretend money at real prices, Oct 28 to Nov 28, 2026. It takes no deposits and has no token. <a href="/what-is-papertrades-ai.html">What is PaperTrades.AI?</a></p>
<style>.pt-def {{ margin: 0; padding: 5px 14px; font-size: 12px; line-height: 1.4; text-align: center; color: var(--color-fg-muted, #a9a495); background: var(--color-bg, #0b0b0a); }} .pt-def a {{ color: inherit; text-decoration: underline; white-space: nowrap; }}</style>
{SPLASH}
<!-- Safety banner for new visitors (owner, Nov 1, 2026; text and behaviour agreed by Claude, Gemini and ChatGPT: ops/review/safety-banner-nov1.json).
     Shown until the visitor closes it (remembered only in that browser), until Dec 1, 2026. -->
<div id="pt-safety" class="pt-safety" role="note" hidden><span class="pt-safety-t">🔒 PaperTrades.AI never takes deposits and will never message you asking for money, your password or personal information (optional tips are only on our Support page). We are not associated with any similarly named site or app. <a href="#official" data-goto="about">Official accounts →</a></span><button type="button" class="pt-safety-x" aria-label="Close this notice">✕</button></div>
<style>
  .pt-safety {{ display: flex; align-items: center; gap: 12px; justify-content: center; padding: 8px 44px 8px 14px; background: #15181d; color: #e8e6df; border-bottom: 1px solid #2a2f37; font-size: 13px; line-height: 1.4; text-align: center; position: relative; z-index: 60; }}
  .pt-safety[hidden] {{ display: none; }}
  .pt-safety a {{ color: #f5c542; white-space: nowrap; }}
  .pt-safety-x {{ position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font: inherit; background: none; border: 1px solid #3a404a; color: #e8e6df; border-radius: 999px; width: 28px; height: 28px; cursor: pointer; }}
  @media (max-width: 700px) {{ .pt-safety {{ font-size: 12.5px; justify-content: flex-start; padding: 8px 42px 8px 12px; }} }}
</style>
<script>
  (function () {{
    try {{
      var b = document.getElementById('pt-safety'); if (!b) return;
      if (Date.now() > Date.parse('2026-12-01T05:00:00Z')) {{ b.remove(); return; }}
      var closed = null; try {{ closed = localStorage.getItem('pt-safety-closed'); }} catch (e) {{}}
      if (closed) {{ b.remove(); return; }}
      b.hidden = false;
      b.querySelector('.pt-safety-x').addEventListener('click', function () {{ try {{ localStorage.setItem('pt-safety-closed', '1'); }} catch (e) {{}} b.remove(); }});
      b.querySelector('a').addEventListener('click', function () {{ setTimeout(function () {{ var o = document.getElementById('official'); if (o) o.scrollIntoView({{ behavior: 'smooth', block: 'start' }}); }}, 200); }});
    }} catch (e) {{}}
  }})();
</script>
<div id="dash-root">
{markup.strip()}
</div>
<script>
{script}
</script>
</body>
</html>
"""
import hashlib as _hlp
PAGE_VER = _hlp.sha1((html.replace(OG_V, '') if OG_V else html).encode()).hexdigest()[:12]   # not the share-picture tag, which changes with the standings   # changes whenever the page itself changes; open pages see it in data.json and update
html = html.replace('__PAGE_VER__', PAGE_VER)
open(os.path.join(OUT, 'index.html'), 'w').write(html)

# ---- data.json ----
data = {}
for name in ('holdings', 'history', 'bets', 'log', 'rules', 'benchmark', 'indexes', 'events', 'prices', 'trades', 'bench_history', 'ledger', 'review', 'take', 'report', 'factcheck', 'plans', 'profile'):
    data[name] = json.load(open(os.path.join(SRC, name + '.json')))
data['sources'] = json.load(open(os.path.join(SRC, 'sources.json')))
# results the race runner settled for Claude's bets go into Claude's decision log too, so "Last trade" and the Won / Lost counts include them
# (full-site review, Nov 1: Claude's Sports page still showed the Ravens bet as its last move after the loss). Site text, not Claude's words.
try:
    _seen = {str(x.get('detail', ''))[:3].strip() for x in data['log'] if x.get('portfolio') == 'Sports' and x.get('action') == 'Settle' and not str(x.get('detail', '')).startswith('Simulation before')}
    for _b in data['bets']:
        if _b.get('status') in ('Won', 'Lost', 'Push', 'Void') and _b.get('settled_at') and str(_b.get('bet')) not in _seen:
            _r = float(_b.get('result_cad') or 0)
            data['log'].append({'at': _b['settled_at'], 'portfolio': 'Sports', 'action': 'Settle', 'site_note': True,
                                'detail': f"{_b['bet']} {_b['status'].lower()}: {_b.get('pick')} ({_b.get('event')}), final {_b.get('final') or 'per ESPN'}; "
                                          f"{'+' if _r >= 0 else '−'}C${abs(_r):,.0f}. Settled by the race runner from the ESPN final (site note, not Claude's words)."})
except Exception as _e:
    print('runner settles not added to log:', _e)
try:   # the public log of site, posting and account updates, newest last (owner, Oct 30)
    data['changelog'] = json.load(open(os.path.join(SRC, 'changelog.json')))
except Exception:
    data['changelog'] = []
rv = os.path.join(SRC, 'rivals.json')
r = json.load(open(rv)) if os.path.exists(rv) else {'models': {}, 'trades': [], 'history': [], 'takes': []}
# R4 (root-cause vote, Oct 31; all three AIs agreed): one price source. From the switch, Claude's values on the site are the race runner's
# (rivals.json "claude_feed", the same check-ins and feeds as Gemini's and ChatGPT's), and its holdings show the runner's prices too, so a
# tile always equals the sum of its holdings. Claude's own valuations stay in history_own (its run times, its notes).
data['history_own'] = data['history']
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import official as _OF
    data['history'] = _OF.official_rows(data['history_own'], r.get('claude_feed', []))
    _fpx = _OF.latest_prices(r.get('claude_feed', []))
    _ffx = next((f.get('fx') for f in reversed(r.get('claude_feed', [])) if f.get('fx')), None)
    if _ffx:
        for _hr in data['holdings']:
            _k = (_hr['portfolio'], _hr['holding'])
            if _hr['portfolio'] == 'China' and str(_hr['holding']).startswith('Cash') and _hr.get('currency') == 'CNY' and _hr.get('quantity') and _ffx.get('USDCNY'):
                _hr['value_usd'] = round(float(_hr['quantity']) / _ffx['USDCNY'], 2)   # yuan cash at the same rate as the holdings and the official value (full-site review, Nov 1: US$100,281 vs US$100,210)
                continue
            if _k not in _fpx or not _hr.get('quantity') or str(_hr['holding']).startswith('Cash') or _hr['holding'] == 'USDC':
                continue
            _px, _pat = _fpx[_k]
            if _hr['portfolio'] == 'China':
                _hr['price_local'] = _px; _hr['value_usd'] = round(_hr['quantity'] * _px / _ffx['USDCNY'], 2); _ent = _hr.get('entry_local')
            else:
                _hr['price_usd'] = _px; _hr['value_cad'] = round(_hr['quantity'] * _px * _ffx['USDCAD'], 2); _ent = _hr.get('entry_usd')
            if _ent:
                _hr['change_pct'] = round(_px / _ent - 1, 4)
            _hr['price_source'] = 'Race runner (same feed and check-in as Gemini and ChatGPT)'; _hr['price_at'] = _pat
except Exception as _e:
    print('official values not applied:', _e)
try:   # public transaction IDs, read from the registry the race runner keeps in rivals.json (ops/txids.py); never assigned here
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import txids as _TX
    _REG = r.get('txids', {}) or {}
    for _t in r.get('trades', []):
        _t['tx'] = _REG.get(_TX.rival_key(_t)) if _t.get('model') in _TX.AI and _t.get('experiment') in _TX.RACE else None
except Exception as _e:
    print('transaction IDs skipped:', _e); _TX = None; _REG = {}
try:   # the search source ledger's public day files, searchlog/<UTC day>.json (all three AIs agreed, Oct 30)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import searchlog as _SL
    _SL.write_public(r)
except Exception as _e:
    print('search ledger files skipped:', _e)
# OPTION B (owner's go, Oct 29): from the switch, Claude's orders and stops are filled by the race runner. Claude's own price rules
# became runner stops at the switch, so the site shows those (and keeps the plain policy rules from rules.json).
try:
    data['option_b'] = [json.load(open(os.path.join(SRC, 'option_b.json')))]
except Exception:
    data['option_b'] = []
if (r.get('stops_migrated') or {}).get('claude'):
    data['rules'] = [x for x in data['rules'] if not (x.get('label') in ('Stop', 'Target') or (x.get('asset') and x.get('level') is not None))]
    for _st in (r.get('stops') or {}).get('claude', []):
        _act = 'Sell' if _st['direction'] == ('below' if _st['kind'] == 'stop' else 'above') else 'Cover'
        _share = 'all' if _st['fraction'] >= 1 else format(_st['fraction'], '.0%') + ' of'
        _move = 'falls' if _st['direction'] == 'below' else 'rises'
        _w = _st.get('watch') or ({'Gold': 'GC=F', 'Silver': 'SI=F'}.get(_st.get('name')) if _st['experiment'] == 'Metals' and _st.get('symbol') in ('GC=F', 'SI=F') else None)
        _watch = ' (watching USD/CAD)' if _w == 'CAD=X' else ' (on the futures price the runner watches)' if _w in ('GC=F', 'SI=F') else ''
        data['rules'].append({'portfolio': _st['experiment'], 'rule': f"{_act} {_share} {_st.get('name')} if it {_move} to {_st['level']:g}{_watch} ({_st['kind']}, checked at every run by the race runner).",
                              'asset': _st.get('name'), 'level': _st['level'], 'direction': _st['direction'], 'label': _st['kind'].capitalize(), 'stop_id': _st['id'],
                              **({'watch': _w} if _w else {}), **({'why': _st['reason']} if _st.get('reason') and not re.match(r'^(Sell|Cover|Buy)\b.*\((stop|target)\)\.?$', _st['reason']) else {})})
data['stops_log'] = (r.get('stops_log') or [])[-60:]
data['fingerprints'] = r.get('fingerprints') or []   # nightly ledger fingerprints (ops/fingerprint.py), recomputed by the visitor's browser


def _price_corrections():
    """Price corrections of past fills (full-audit vote V3, Oct 31; all three AIs agreed): Gemini's and ChatGPT's as applied by the race
    runner (rivals.json), Claude's as applied in its own files (ops/src/price_corrections.json with an "at"). Each carries the original
    fill price and the 1-minute bar price. Hashed in the nightly fingerprint ("P" lines), so the browser needs the same fields."""
    try:
        spec = {c['id']: c for c in json.load(open(os.path.join(SRC, 'price_corrections.json')))}
    except Exception:
        spec = {}
    keep = ('bar_minute', 'why', 'qty', 'feed', 'problem')
    out = [{**{k: v for k, v in spec.get(c['id'], {}).items() if k in keep}, **c} for c in (r.get('price_corrections') or [])]
    for c in spec.values():
        if c.get('model') == 'claude' and c.get('at'):
            out.append({k: c.get(k) for k in ('id', 'at', 'model', 'experiment', 'symbol', 'fill_at', 'action', 'fill_price', 'bar_price', 'amount', 'currency') + keep})
    return sorted(out, key=lambda c: (c['fill_at'], c['id']))


data['price_corrections'] = _price_corrections()
try:   # R6 (root-cause vote, Oct 31): the nightly full audit's summaries, newest first
    data['nightly_audit'] = json.load(open(os.path.join(SRC, 'nightly_audit.json')))[:7]
except Exception:
    data['nightly_audit'] = []
try:   # L1 luck check (critique 2, Oct 31; all three AIs agreed): written nightly by ops/luck.py; display only
    data['luck'] = [json.load(open(os.path.join(SRC, 'luck.json')))]
except Exception:
    data['luck'] = []
try:   # L2 wrong-if tracker (critique 2, Oct 31; all three AIs agreed): written nightly by ops/wrongif.py; display only
    data['wrongif'] = [json.load(open(os.path.join(SRC, 'wrongif.json')))]
except Exception:
    data['wrongif'] = []
try:   # L3 weekly stress drill (critique 2, Oct 31; all three AIs agreed): ops/drill.py; display only
    data['drills'] = json.load(open(os.path.join(SRC, 'drills.json')))[-4:]
except Exception:
    data['drills'] = []
# Profit on every closed trade (average cost) and every settled bet, so every trade table can show what went in,
# what came back and the profit. Buys and open bets are marked open. Sells carry "cost" (what that part cost) and "pnl".
def _annotate_rivals(r):
    lots = {}
    bets = {(mid, b['id']): b for mid, m in (r.get('models') or {}).items() for e, bk in (m.get('books') or {}).items() for b in bk.get('bets', [])}
    # Claude's All in book lives apart from Gemini's and ChatGPT's: without it, a settled Claude bet kept showing "open" (owner, Nov 1)
    bets.update({('claude', b['id']): b for e, bk in ((r.get('claude_allin') or {}).get('books') or {}).items() for b in (bk or {}).get('bets', [])})
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
            if t.get('pnl_cad') is not None and not china:   # the race runner's own profit (it knows the exact units and exchange rates); number audit round 4, Nov 1: QQQ, gold and silver stops showed USD costs as C$ and losses as gains
                t['pnl'] = round(float(t['pnl_cad']), 2); t['cost'] = round(val + t['pnl'] if a == 'Cover' else val - t['pnl'], 2)
            if t.get('held_after') is not None and float(t.get('held_after') or 0) <= 1e-12:
                L['u'] = 0.0; L['c'] = 0.0
            else:
                L['u'] -= L['u'] * f; L['c'] -= part


def _claude_realized_fix(trades, holdings):
    # a sale with no runner profit on it: take the holding's realized profit from the runner (it priced the units exactly) when that sale is the only one unaccounted for
    for h in holdings or []:
        rz = h.get('realized_cad')
        if rz is None or h.get('portfolio') == 'China':
            continue
        sales = [t for t in trades if t.get('portfolio') == h.get('portfolio') and t.get('holding') == h.get('holding') and t.get('action') == 'Sell']
        loose = [t for t in sales if t.get('pnl_cad') is None]
        if len(loose) == 1:
            t = loose[0]; others = sum(float(x.get('pnl') or 0) for x in sales if x is not t)
            t['pnl'] = round(float(rz) - others, 2); t['cost'] = round(float(t.get('cad') or 0) - t['pnl'], 2)


try:
    _annotate_rivals(r)
    _annotate_claude(data['trades'])
    _claude_realized_fix(data['trades'], data.get('holdings'))
except Exception as _e:
    print('trade profits not added:', _e)
def _nohist(books):   # price histories stay in rivals.json; the page gets them as each AI's 'prices'
    return {e: {**bk, 'positions': {k: {x: y for x, y in p.items() if x != 'hist'} for k, p in (bk.get('positions') or {}).items()}} if isinstance(bk, dict) else bk for e, bk in (books or {}).items()}
data['rivals_models'] = [{'id': k, **{x: v.get(x) for x in ('label', 'company', 'model', 'started', 'exps', 'last_run')}, 'books': _nohist(v['books'])} for k, v in r['models'].items()]
for k in ('trades', 'history', 'takes'):
    data['rivals_' + k] = r[k]
_cut = (min(datetime.now(timezone.utc), datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc)) - __import__('datetime').timedelta(days=2)).isoformat()   # stops moving after the race
data['fx_all'] = [{'cur': k, 'per_usd': v} for k, v in (r.get('fx_all') or {}).items()]
data['fx_meta'] = [json.load(open(os.path.join(SRC, 'fx.json')))]
_ai = [{'id': 'claude', 'started': (r.get('claude_allin') or {}).get('started'), 'books': (r.get('claude_allin') or {}).get('books', {})}] if r.get('claude_allin') else []
data['allin_models'] = _ai + [{'id': k, 'started': v.get('started'), 'books': _nohist({e: b for e, b in v['books'].items() if e.startswith('AllIn')})} for k, v in r['models'].items()]
data['allin_trades'] = [t for t in r['trades'] if str(t.get('experiment', '')).startswith('AllIn')]
# High risk: trading holdings with their own price at every check-in, so the per-holding price chart also works for the side race (owner, Oct 30)
data['allin_px'] = [{'model': k, 'exp': e, 'sym': sym, 'name': x.get('name') or sym, 'qty': x.get('qty'), 'entry': x.get('entry'), 'last': x.get('last'),
                     'priced_at': x.get('priced_at'), 'hist': x.get('hist') or []}
                    for k, v in r['models'].items() for e, b in (v.get('books') or {}).items() if e == 'AllInTrading'
                    for sym, x in (b.get('positions') or {}).items() if abs(float(x.get('qty') or 0)) > 1e-9]
data['allin_history'] = [h for h in r['history'] if str(h.get('experiment', '')).startswith('AllIn')]
data['rivals_trades'] = [t for t in r['trades'] if not str(t.get('experiment', '')).startswith('AllIn') and t.get('model') != 'claude']
data['rivals_history'] = [h for h in r['history'] if not str(h.get('experiment', '')).startswith('AllIn') and h.get('model') != 'claude']
data['factcheck'] = [dict(x, checker=x.get('checker', 'claude')) for x in data['factcheck']] + [x for x in r.get('factchecks', [])]   # from now on Gemini checks Claude; Claude's one earlier self-check stays visible
_cl = max((datetime.fromisoformat(h['at'].replace('Z', '+00:00')) for h in data['history_own']), default=None)   # Claude's own last run
data['checkins'] = ([{'id': 'claude', 'at': _cl.isoformat() if _cl else None, 'status': 'ok'}] +
                    [{'id': k, 'at': (v.get('last_run') or {}).get('at'), 'status': (v.get('last_run') or {}).get('status', '')} for k, v in r['models'].items()])
data['geo'] = [json.load(open(os.path.join(SRC, 'geo.json')))] if os.path.exists(os.path.join(SRC, 'geo.json')) else []
# a developing story that matters to a race (ops/src/story.json, refreshed at Claude's runs while it is active; owner, Oct 30)
data['story'] = [json.load(open(os.path.join(SRC, 'story.json')))] if os.path.exists(os.path.join(SRC, 'story.json')) else []
data['profiles'] = data['profile'] + r.get('profiles', [])
_lp = {}
for _p in r.get('plans', []):
    _lp[(_p.get('model'), _p.get('experiment'), _p.get('horizon'))] = _p   # the site shows only the newest plan per AI, race and card
data['rivals_plans'] = list(_lp.values())
data['plans'] = list({(x.get('experiment'), x.get('horizon')): x for x in data.get('plans', [])}.values())   # Claude's: newest per race and card
# News that moved the race (owner's request, Oct 30; Claude, Gemini and ChatGPT all agreed: ops/review/news-r1-oct30.json). Each moment's
# facts are written from named, dated sources in ops/src/news_moments.json; everything else is computed here at every build, so it stays
# current and the same for all three AIs: what each AI did (its trades in the moment's races and window, with its own reason, from the race
# record), what the market did (from the race's own price record) and each AI's latest plan for that race in its own words. A developing
# story's live figures come from ops/src/story.json (one source of truth: a correction there shows everywhere at once).
def _nmw(x):
    return datetime.fromisoformat(str(x).replace('Z', '+00:00'))
def _nm_trades(spec):
    t0 = _nmw(spec['from']); t1 = _nmw(spec['to']) if spec.get('to') else None
    races = set(spec.get('races') or [])
    pats = [str(p).lower() for p in (spec.get('assets') or [])]
    cites = re.compile(spec['cites'], re.I) if spec.get('cites') else None
    def ok(at, race, names, reason):
        w = _nmw(at)
        if w < t0 or (t1 and w > t1) or (races and race not in races):
            return False
        if not pats and not cites:
            return True
        return bool(pats and any(p in str(n).lower() for p in pats for n in names if n)) or bool(cites and cites.search(reason or ''))
    out = {'claude': [], 'gemini': [], 'chatgpt': []}
    for t in data['trades']:   # Claude's ten races (its High risk trades are in rivals.json, below)
        if ok(t['at'], t.get('portfolio'), [t.get('holding')], t.get('note')):
            px = t.get('price_usd') if t.get('price_usd') is not None else t.get('price_local')
            out['claude'].append({'at': _nmw(t['at']).isoformat(), 'race': t.get('portfolio'), 'action': t.get('action'), 'what': t.get('holding'),
                                  'cad': round(float(t.get('cad') or 0)) if t.get('cad') is not None else None, 'usd': None,
                                  'price': px, 'pcur': 'CNY' if t.get('price_local') is not None and t.get('price_usd') is None else 'USD', 'reason': t.get('note') or ''})
    for t in r.get('trades', []):
        m = t.get('model')
        if m not in out or (m == 'claude' and not str(t.get('experiment', '')).startswith('AllIn')):
            continue
        if ok(t['at'], t.get('experiment'), [t.get('name'), t.get('symbol')], t.get('reason')):
            amt = float(t.get('amount') or 0)
            out[m].append({'at': _nmw(t['at']).isoformat(), 'race': t.get('experiment'), 'action': t.get('action'), 'what': t.get('name') or t.get('symbol'),
                           'cad': round(amt) if t.get('cur') == 'CAD' else None, 'usd': round(amt) if t.get('cur') == 'USD' else None,
                           'price': t.get('price'), 'pcur': t.get('pcur') or 'USD', 'reason': t.get('reason') or ''})
    for k in out:
        out[k].sort(key=lambda x: x['at'])
    return out
def _nm_measure(spec):
    a, t0 = spec['asset'], _nmw(spec['from'])
    s = sorted(((_nmw(x['at']), float(x['price'])) for x in data['prices'] if x.get('asset') == a and x.get('price') is not None), key=lambda z: z[0])
    pre, post = [z for z in s if z[0] <= t0], [z for z in s if z[0] > t0]
    if not pre or not post or not pre[-1][1]:
        return None
    b, last = pre[-1], post[-1]
    lo, hi = min(post, key=lambda z: z[1]), max(post, key=lambda z: z[1])
    return {'label': spec.get('label') or a, 'before': b[1], 'before_at': b[0].isoformat(), 'last': last[1], 'last_at': last[0].isoformat(),
            'low': lo[1], 'low_at': lo[0].isoformat(), 'high': hi[1], 'high_at': hi[0].isoformat(), 'chg': last[1] / b[1] - 1}
def _nm_plans(race):
    out = {}
    for x in list(data.get('plans', [])) + list(data.get('rivals_plans', [])):
        mid = x.get('model') or 'claude'
        if x.get('experiment') == race and x.get('horizon') in ('day', 'week') and mid in ('claude', 'gemini', 'chatgpt'):
            out.setdefault(mid, []).append({'horizon': x['horizon'], 'text': x.get('text', ''), 'at': x.get('at')})
    for k in out:
        out[k].sort(key=lambda x: 0 if x['horizon'] == 'day' else 1)
    return out
data['news_moments'] = []
_nmp = os.path.join(SRC, 'news_moments.json')
for _m in (json.load(open(_nmp)) if os.path.exists(_nmp) else []):
    if _m.get('status') == 'hidden':
        continue
    try:
        _m = dict(_m)
        _m['ai_trades'] = _nm_trades(_m['trades']) if _m.get('trades') else {}
        _m['measured'] = [x for x in (_nm_measure(sp) for sp in _m.get('measure', [])) if x]
        _m['plans'] = _nm_plans(_m['plan_race']) if _m.get('plan_race') else {}
        data['news_moments'].append(_m)
    except Exception as _e:   # a broken entry is left out and named, never allowed to stop the build
        print(f"news_moments: skipped {_m.get('id')}: {_e}")
data['news_moments'].sort(key=lambda m: _nmw(m['at']), reverse=True)
# Betting minimums (no weekly minimum since Oct 28, 5:30 p.m. ET): C$3,000 a day and C$100,000 in total by Nov 28 for every AI.
# The daily minimum becomes 25% of the betting balance (Sports bankroll + Predictions value) once that is under C$12,000.
from zoneinfo import ZoneInfo as _ZI
_ny = _ZI('America/New_York')
_BFS, _BEND = '2026-10-28T17:45:00+00:00', '2026-11-28T21:00:00+00:00'
def _when(x):
    return datetime.fromisoformat(str(x).replace('Z', '+00:00'))
# every wager that counts toward the minimums, the same rule for all three AIs: bets and parlays placed and prediction-market buys;
# a bet the organiser cancelled before it started does not count (agreed item 10: the list is published as an audit table)
_bm_items = []
for _b in data['bets']:
    if _b.get('placed_at') and _b.get('status') != 'Void':
        _bm_items.append({'model': 'claude', 'at': _b['placed_at'], 'amount': float(_b.get('stake_cad') or 0), 'kind': 'Parlay' if _b.get('market') == 'parlay' else 'Bet',
                          'what': f"{_b.get('pick')} ({_b.get('event')})", 'race': 'Sports'})
for _t in data['trades']:
    if _t['portfolio'] == 'Predictions' and _t['action'] == 'Buy' and not str(_t['holding']).startswith('['):
        _bm_items.append({'model': 'claude', 'at': _t['at'], 'amount': float(_t.get('cad') or 0), 'kind': 'Prediction buy', 'what': _t['holding'], 'race': 'Predictions'})
for _t in r.get('trades', []):
    if _t.get('experiment') in ('Sports', 'Predictions') and _t.get('action') in ('Bet', 'Buy') and _t.get('model') in ('gemini', 'chatgpt') and not _t.get('void'):
        _bm_items.append({'model': _t['model'], 'at': _t['at'], 'amount': float(_t.get('amount') or 0), 'kind': ('Parlay' if _t.get('legs') else 'Bet') if _t['action'] == 'Bet' else 'Prediction buy',
                          'what': _t.get('name') or _t.get('symbol'), 'race': _t['experiment']})
_rows = {}
for _it in _bm_items:
    _rows.setdefault(_it['model'], []).append((_it['at'], _it['amount']))
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
def _said(x):   # what the graded decision was; a hold keeps the positions already open, which is often what got graded (owner, Nov 1: an F on a "no trade" hold read as nonsense)
    if str(x.get('action', '')).lower() == 'hold':
        return 'Hold: no new trade or bet at that check-in; it kept the positions and bets it already had in this race'
    return f"{x.get('action', '')} {x.get('what', '')}".strip()


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
# Prediction markets minimums from Mon Nov 2 (owner; Claude, Gemini and ChatGPT all agreed: ops/review/pred-sitout-nov2.json):
# C$3,000 bought each ET week (Mon-Sun), C$15,000 bought since the restart by Nov 28; progress per AI for the Prediction markets tab
data['predmins'] = []
_wk0 = _today - timedelta(days=_today.weekday())
for _m in ('claude', 'gemini', 'chatgpt'):
    _pi = [(_when(x['at']), x['amount']) for x in _bm_items if x['model'] == _m and x['race'] == 'Predictions' and _when(x['at']) >= _when(_BFS)]
    _wk = sum(v for a, v in _pi if a.astimezone(_ny).date() >= _wk0)
    _pp = r.get('claude_pred_penalties', []) if _m == 'claude' else ((((r.get('models') or {}).get(_m) or {}).get('books') or {}).get('Predictions') or {}).get('penalties', [])
    data['predmins'].append({'model': _m, 'week_start': _wk0.isoformat(), 'week_end': min(_wk0 + timedelta(days=6), _when(_BEND).astimezone(_ny).date()).isoformat(),
                             'week': round(_wk, 2), 'week_min': 3000.0, 'total': round(sum(v for a, v in _pi), 2), 'total_min': 15000.0,
                             'trades': len(_pi), 'penalties': [{'week': x.get('week'), 'amount': x.get('amount'), 'reason': x.get('reason')} for x in _pp]})
# High risk: sports betting minimums from Nov 1 (owner, Oct 31; all three AIs agreed): progress per AI for the High risk page
_AFROM = datetime(2026, 11, 1, tzinfo=_ny)
data['allinmins'] = []
for _m in ('claude', 'gemini', 'chatgpt'):
    _bk = ((r.get('claude_allin') or {}).get('books') or {}).get('AllInSports') if _m == 'claude' else (((r.get('models') or {}).get(_m) or {}).get('books') or {}).get('AllInSports')
    _bal = 100000.0 + sum(x['result'] for x in (_bk or {}).get('bets', []) if x['status'] not in ('Open', 'Void')) - sum(float(x['amount']) for x in (_bk or {}).get('penalties', []))
    _amin = 0.0 if _bal < 1 else (3000.0 if _bal >= 12000 else max(1.0, round(_bal * 0.25, 2)))
    _ad = {}
    for _t in r.get('trades', []):
        if _t.get('model') == _m and _t.get('experiment') == 'AllInSports' and _t.get('action') == 'Bet' and not _t.get('void'):
            _k = _when(_t['at']).astimezone(_ny).date().isoformat(); _ad[_k] = _ad.get(_k, 0.0) + float(_t.get('amount') or 0)
    _miss, _d = [], _AFROM.date()
    while _d < min(_today, _when(_BEND).astimezone(_ny).date() + timedelta(days=1)):
        if _ad.get(_d.isoformat(), 0.0) + 0.5 < _amin:
            _miss.append(_d.isoformat())
        _d += timedelta(days=1)
    data['allinmins'].append({'model': _m, 'balance': round(_bal, 2), 'day_min': _amin, 'today': round(_ad.get(_today.isoformat(), 0.0), 2),
                              'total': round(sum(v for k, v in _ad.items() if k >= _AFROM.date().isoformat()), 2), 'missed': _miss,   # only bets from Nov 1, when the rule starts (owner, Nov 1: Gemini showed C$331,000 counting Oct bets)
                               'started': _today >= _AFROM.date(),
                              'penalties': round(sum(float(x['amount']) for x in (_bk or {}).get('penalties', [])), 2)})
data['betmin_items'] = sorted([dict(_it, day=_when(_it['at']).astimezone(_ny).date().isoformat(), amount=round(_it['amount'], 2)) for _it in _bm_items if _when(_it['at']) >= _when(_BFS)],
                              key=lambda x: _when(x['at']), reverse=True)
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
# the crown goes to the AI leading the most races; races are never added together in public before the final (owner's rule)
_led = sorted(((len(x['leads']), x['id']) for x in STANDINGS), reverse=True)
LEADER_RACES = _led[0][1] if len(_led) > 1 and _led[0][0] > _led[1][0] else None
# the crown follows the official win rule: the highest total profit across the ten races (C$, China converted), agreed by all
# three AIs and the owner (Oct 29). From Oct 30 the owner asked for the total profit of each AI to be shown with the crown.
_byp = sorted(STANDINGS, key=lambda x: -x['total'])
LEADER = _byp[0]['id'] if len(_byp) > 1 and _byp[0]['total'] - _byp[1]['total'] >= 1 else None
data['leader_races'] = LEADER_RACES
data['overall_order'] = [x['id'] for x in _byp]
data['standings'] = [{'id': x['id'], 'leads': x['leads'], 'rank': i + 1, 'profit': round(x['total'])} for i, x in enumerate(_byp)]   # total profit in C$ now shown with the crown (owner's request, Oct 30)
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
def _merge_pie(items):
    """One slice per holding: repeat bets on the same pick are added together (Oct 29)."""
    out = {}
    for n, x in items:
        out[n] = out.get(n, 0.0) + float(x)
    return [{'name': n, 'value': round(x, 2)} for n, x in out.items() if x > 0.5]


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
        if _e == 'Sports':   # the bankroll is the start plus settled results; what isn't riding on an open bet is "Not bet" (Oct 29)
            _ob = [(n, x) for n, x in hv if not str(n).startswith('Cash')]
            hv = _ob + [('Not bet', max(0.0, v - sum(x for _, x in _ob)))]
        _es[_e].append({'id': 'claude', 'value': round(v, 2), 'profit': round(max(v, 0) - b0, 2), 'holds': held[:20], 'busted': v <= 0, 'eliminated': _ctot <= -100000,
                        'pie': _merge_pie(hv), 'last': last})
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
            last = {'at': lt['at'], 'text': f"{lt['action']} {lt.get('name') or lt['symbol']} ({b2c(abs(lt['amount']), lt['cur'])}): {'profit' if lt['pnl'] >= 0 else 'loss'} {b2c(abs(lt['pnl']), lt['cur'])}"}   # W3a: never "−C$396 profit"
        elif lt and lt['action'] in ('Won', 'Lost') and lt.get('amount') is not None:   # Gemini's and ChatGPT's results keep the result in amount (no stake field)
            last = {'at': lt['at'], 'text': f"{lt['action']} {lt.get('name') or lt['symbol']}: {'profit' if float(lt['amount']) >= 0 else 'loss'} {b2c(abs(float(lt['amount'])), lt['cur'])}"}
        else:
            last = {'at': lt['at'], 'text': f"{lt['action']} {lt.get('name') or lt['symbol']} ({b2c(abs(lt['amount']), lt['cur'])})"} if lt else None
        _es[_e].append({'id': _mid, 'value': round(v, 2), 'profit': round(max(v, 0) - 100000.0, 2), 'holds': held[:20],
                        'pie': _merge_pie(pie), 'last': last,
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
            if t.get('held_after') is not None and float(t['held_after']) <= 1e-9:
                f = 1.0   # sold out: the whole remaining cost (units from amount / price drift with the exchange rate)
            part = L['c'] * f
            pnl = float(t['pnl_cad']) if t.get('pnl_cad') is not None else ((amt - part) if side == 'long' else (part - amt))   # the profit the ledger recorded at the sale
            out.append({'name': t['holding'], 'pnl': pnl, 'at': t['at']})
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


# Biggest profits and losses in each race (owner, Oct 29), for all three AIs: each holding's profit so far (the part sold plus
# what is still held, at the latest price) and each settled bet (repeat bets on the same pick added together). Each race on
# its own, in its own currency; the "Races led" view lists the biggest single items across the ten races, never a total.
def _big_moves():
    fx = r.get('fx') or {'USDCAD': 1.4, 'USDCNY': 7.1}
    def conv(amt, pcur, cur):
        usd = amt if pcur == 'USD' else amt / fx.get('USDCNY', 7.1) if pcur == 'CNY' else amt / fx.get('USDCAD', 1.4)
        return usd if cur == 'USD' else usd * fx.get('USDCAD', 1.4)
    def realized(trades):   # {key: profit} at average cost, in the book's currency
        out, cost, names = {}, {}, {}
        for t in trades:
            key = f"{t['symbol']}|{t['outcome']}" if t.get('outcome') else t['symbol']
            names[key] = t.get('name') or t['symbol']
            c = cost.setdefault(key, {'qty': 0.0, 'cost': 0.0})
            q = abs(float(t.get('qty') or 0))
            if t['action'] in ('Buy', 'Short'):
                c['qty'] += q; c['cost'] += float(t['amount']) if t['action'] == 'Buy' else -float(t['amount'])
            elif t['action'] in ('Sell', 'Cover', 'Settled', 'Expired') and c['qty'] > 1e-12:
                f = min(1.0, (q or c['qty']) / c['qty']); part = c['cost'] * f
                out[key] = out.get(key, 0.0) + (-float(t['amount']) if t['action'] == 'Cover' else float(t['amount'])) - part
                c['cost'] -= part; c['qty'] -= c['qty'] * f
        names['__cost__'] = {k: v['cost'] for k, v in cost.items()}   # what is still invested in each holding, in the book's currency at the rates paid
        return out, names
    big = {}
    def add(race, mid, what, pnl, state, n=1, k=None, kind='pos'):
        if abs(pnl) >= 0.5:   # k + kind: the exact position or bet group, so the site's move story panel finds its trades (owner, Oct 31)
            big.setdefault(race, []).append({'id': mid, 'race': race, 'what': str(what)[:80], 'pnl': round(pnl, 2), 'state': state, 'n': n,
                                             'cur': 'USD' if race == 'China' else 'CAD', 'k': k, 'kind': kind})
    def bets(race, mid, rows):   # rows: (pick, event, profit, status)
        g = {}
        for pick, ev, p, st in rows:
            k = (pick, ev)
            x = g.setdefault(k, [0.0, 0, set()]); x[0] += p; x[1] += 1; x[2].add(st)
        for (pick, ev), (p, n, sts) in g.items():
            add(race, mid, f'{pick} ({ev})', p, 'won' if p > 0 else 'lost', n, k=[pick, ev], kind='bet')
    def rival_book(race, mid, bk, trades):
        cur = bk.get('cur', 'CAD')
        if race in ('Sports', 'AllInSports'):
            bets(race, mid, [(b.get('pick_team') or b.get('pick'), b.get('event', ''), float(b.get('result') or 0), b['status'])
                             for b in bk.get('bets', []) if b.get('status') in ('Won', 'Lost')])
            return
        rz, names = realized(trades)
        keys = (set(rz) | {k for k, q in (bk.get('positions') or {}).items() if abs(float(q.get('qty') or 0)) > 1e-9}) - {'__cost__'}
        for k in keys:
            q = (bk.get('positions') or {}).get(k) or {}
            held = abs(float(q.get('qty') or 0)) > 1e-9
            # profit still open = value now (latest price, today's rate) - what is still invested (at the rates actually paid): the real
            # result in the race's currency, the same sum the move story panel shows (owner, Oct 31); before, the cost was converted at today's rate
            left = names.get('__cost__', {}).get(k)
            un = ((conv(float(q['qty']) * float(q.get('last', q['entry'])), q.get('pcur', 'USD'), cur) - left) if left is not None
                  else conv(float(q['qty']) * (float(q.get('last', q['entry'])) - float(q['entry'])), q.get('pcur', 'USD'), cur)) if held else 0.0
            nm = (q.get('name') if held else None) or names.get(k) or k
            add(race, mid, nm + (' (short)' if held and float(q['qty']) < 0 else ''), rz.get(k, 0.0) + un, 'held' if held else 'closed', k=k)
    for e in _EXPS:
        # Claude
        if e == 'Sports':
            bets(e, 'claude', [(re.sub(r' moneyline$', '', str(b.get('pick', ''))), re.sub(r'\s*\(.*\)$', '', str(b.get('event', ''))), float(b.get('result_cad') or 0), b['status'])
                               for b in data['bets'] if b.get('status') in ('Won', 'Lost') and b.get('placed_at') and _when(b['placed_at']) >= _FS])
        else:
            rz = {}
            for c in _closed_claude(e):
                rz[c['name']] = rz.get(c['name'], 0.0) + c['pnl']
            held = {}
            for h in data['holdings']:
                if h['portfolio'] != e or str(h['holding']).startswith('Cash') or h['holding'] == 'USDC' or abs(float(h.get('quantity') or 0)) < 1e-9:
                    continue
                v, c = (h.get('value_usd'), h.get('cost_usd')) if e == 'China' else (h.get('value_cad'), h.get('cost_cad'))
                if v is None or c is None:
                    continue
                held[h['holding']] = (float(v) - float(c), float(v) < 0)
            # cash flow (owner, Oct 31: the move story panel's check): everything received - everything paid + value still held now, in
            # the race's currency at the rates actually used; it never depends on how a partial sale's cost was split
            flow, vnow = {}, {}
            for t in data['trades']:
                if t['portfolio'] != e or _when(t['at']) < _FS or str(t.get('holding', '')).startswith('[') or t['action'] not in ('Buy', 'Sell', 'Short', 'Cover', 'Settled', 'Expired'):
                    continue
                amt = float((t.get('usd') if e == 'China' else t.get('cad')) or 0)
                flow[t['holding']] = flow.get(t['holding'], 0.0) + (amt if t['action'] in ('Sell', 'Short', 'Settled', 'Expired') else -amt)
            for h in data['holdings']:
                if h['portfolio'] == e and h['holding'] in held:
                    vnow[h['holding']] = float((h.get('value_usd') if e == 'China' else h.get('value_cad')) or 0)
            for nm in set(rz) | set(held):
                un, short = held.get(nm, (0.0, False))
                tot = flow[nm] + vnow.get(nm, 0.0) if nm in flow else rz.get(nm, 0.0) + un
                add(e, 'claude', nm + (' (short)' if short and '(short)' not in nm else ''), tot, 'held' if nm in held else 'closed', k=nm)
        # Gemini and ChatGPT
        for mid, m in (r.get('models') or {}).items():
            bk = (m.get('books') or {}).get(e)
            if bk:
                rival_book(e, mid, bk, [t for t in r.get('trades', []) if t.get('model') == mid and t.get('experiment') == e])
    # the High risk side race (Claude's books are in claude_allin)
    for am in data.get('allin_models') or []:
        for e, bk in (am.get('books') or {}).items():
            if e in ('AllInTrading', 'AllInSports') and isinstance(bk, dict):
                rival_book(e, am['id'], bk, [t for t in data['allin_trades'] if t.get('model') == am['id'] and t.get('experiment') == e])
    out = {}
    for race, items in big.items():
        ups = sorted([x for x in items if x['pnl'] > 0], key=lambda x: -x['pnl'])[:3]
        downs = sorted([x for x in items if x['pnl'] < 0], key=lambda x: x['pnl'])[:3]
        out[race] = {'up': ups, 'down': downs}
    ten = [x for race in _EXPS for x in big.get(race, [])]
    cad = lambda x: x['pnl'] * (fx.get('USDCAD', 1.4) if x['cur'] == 'USD' else 1)
    out['Overall'] = {'up': sorted([x for x in ten if x['pnl'] > 0], key=lambda x: -cad(x))[:5],
                      'down': sorted([x for x in ten if x['pnl'] < 0], key=cad)[:5]}
    return out


try:
    data['big_moves'] = _big_moves()
except Exception as _e:
    print('biggest profits and losses not built:', _e)
    data['big_moves'] = {}


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
    took, nchg, ever = {}, {}, {}   # W14 (owner, Oct 30; all three AIs agreed): when the leader took over, how many lead changes, who has led before
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
                    took[race] = at; ever.setdefault(race, set()).add(top)
                continue
            if top != was and gap >= need:
                held = (at - took[race]).total_seconds() / 3600 if race in took else None
                again = top in ever.get(race, set())
                lead[race] = top
                took[race] = at; ever.setdefault(race, set()).add(top); nchg[race] = nchg.get(race, 0) + 1
                if race in last_at and (at - last_at[race]).total_seconds() < 12 * 3600:
                    continue
                last_at[race] = at
                out.append({'id': f"{race}-{at.strftime('%Y%m%d%H%M')}-{top}", 'at': at.isoformat().replace('+00:00', 'Z'), 'race': race,
                            'who': top, 'over': was, 'lead': round(gap, 2), 'cur': 'USD' if race == 'China' else 'CAD',
                            'profit': {m: round(vals[m], 2) for m in vals},
                            'held_h': round(held, 1) if held is not None else None, 'nth': nchg[race], 'again': again})
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
def _risk():
    """Best risk manager (owner, Oct 30; all three AIs agreed to a separate award that never changes the Nov 28 profit winner).
    Per race and AI: return since the restart, worst drop (largest fall from a high point, % of that high), and
    score = return / max(worst drop, RISK_FLOOR) for a gain; for a loss, return x max(worst drop, floor) / floor^2, so a
    bigger drop always scores worse. The award = the highest average score over the ten races. Only percentages
    are published: the total amounts stay hidden until Nov 28, as agreed."""
    ser = {}
    for h in data['history']:
        if h['portfolio'] in _EXPS:
            ser.setdefault(('claude', h['portfolio']), []).append((_when(h['at']), float(h['value'])))
    for h in r.get('history', []):
        if h.get('model') in ('gemini', 'chatgpt') and h.get('experiment') in _EXPS:
            ser.setdefault((h['model'], h['experiment']), []).append((_when(h['at']), float(h['value'])))
    races, avg = {}, {}
    for m in ('claude', 'gemini', 'chatgpt'):
        sc = []
        for e in _EXPS:
            pts = sorted(ser.get((m, e), []), key=lambda p: p[0])
            if m == 'claude':
                b0 = _lastv([(t.isoformat(), v) for t, v in pts])[1]
            else:
                b0 = 100000.0
            vals = [b0] + [max(v, 0.0) for t, v in pts if _FS < t <= RACE_END_DT]
            peak, dd = vals[0], 0.0
            for v in vals:
                peak = max(peak, v)
                if peak > 0:
                    dd = max(dd, (peak - v) / peak)
            ret = vals[-1] / b0 - 1 if b0 else 0.0
            d = max(dd, RISK_FLOOR)
            score = ret / d if ret >= 0 else ret * d / RISK_FLOOR ** 2   # for a loss a bigger drop must score worse, not better (the usual ratio would reward it)
            races.setdefault(e, {})[m] = {'ret': round(ret * 100, 3), 'dd': round(dd * 100, 3), 'score': round(score, 3)}
            sc.append(score)
        avg[m] = round(sum(sc) / len(sc), 3) if sc else 0.0
    order = sorted(avg, key=lambda k: -avg[k])
    # owner, Oct 30: show BOTH ways of crowning it: the average score (Claude and ChatGPT's choice) and races won on risk score
    # (Gemini's choice, so one extreme race can't swing it). A race tied on score counts for each AI tied; ties in races won
    # are broken by the average (ChatGPT: race wins as the tie-breaker's partner).
    wins = {m: sum(1 for e in races if races[e][m]['score'] >= max(races[e][o]['score'] for o in races[e])) for m in avg}
    order_wins = sorted(avg, key=lambda k: (-wins[k], -avg[k]))
    return {'floor_pct': RISK_FLOOR * 100, 'added': '2026-10-30', 'races': races, 'avg': avg, 'order': order, 'wins': wins, 'order_wins': order_wins}


RISK_FLOOR = 0.02   # a worst drop under 2% counts as 2%, so a tiny gain with almost no movement can't look like genius
try:   # estimated trading costs, display only (owner, Oct 31; all three AIs agreed it never changes the ranking: ops/review/costs-oct31.json)
    import costs as _CO
    data['costs'] = [_CO.build(r, SRC)]
except Exception as _e:
    print('costs not built:', _e); data['costs'] = []
try:
    data['risk'] = [_risk()]
except Exception as _e:
    print('risk scores not built:', _e)
    data['risk'] = []
def _riskdash():
    """E2 risk dashboard (critique 2, Oct 31; Claude, Gemini and ChatGPT all agreed). Display only. Per race and AI: worst drop,
    typical move between check-ins, largest holding now, amount traded (x the account), average holding time of closed
    positions, estimated cost drag; beta comes from the nightly luck check (ops/luck.py) when available."""
    import statistics as _st
    ser = {}
    for h in data['history']:
        if h['portfolio'] in _EXPS:
            ser.setdefault(('claude', h['portfolio']), []).append((_when(h['at']), float(h['value'])))
    for h in r.get('history', []):
        if h.get('model') in ('gemini', 'chatgpt') and h.get('experiment') in _EXPS:
            ser.setdefault((h['model'], h['experiment']), []).append((_when(h['at']), float(h['value'])))
    rk = (data.get('risk') or [{}])[0].get('races', {}) if data.get('risk') else {}
    co = (data.get('costs') or [{}])[0].get('races', {}) if data.get('costs') else {}
    lk = (data.get('luck') or [{}])[0].get('races', {}) if data.get('luck') else {}
    hold = {'claude': data.get('holdings', [])}
    for m in ('gemini', 'chatgpt'):
        hold[m] = ((data.get('models') or {}).get(m) or {}).get('holdings', [])
    # closed positions: open -> fully closed, from each AI's own trades
    spans = {}
    rows = [('claude', t.get('portfolio'), (t.get('portfolio'), t.get('holding')), t) for t in data.get('trades', []) if t.get('action') in ('Buy', 'Sell', 'Short', 'Cover') and not str(t.get('holding', '')).startswith('[')]
    rows += [(t.get('model'), t.get('experiment'), (t.get('experiment'), t.get('symbol'), t.get('outcome')), t) for t in r.get('trades', []) if t.get('model') in ('gemini', 'chatgpt') and t.get('action') in ('Buy', 'Sell', 'Short', 'Cover', 'Settled', 'Expired')]
    opened, qty = {}, {}
    for m, e, k, t in sorted(rows, key=lambda x: str(_when(x[3]['at']))):
        kk, tt = (m, k), _when(t['at'])
        if tt < _FS:
            continue
        if t['action'] in ('Buy', 'Short'):
            if qty.get(kk, 0) <= 1e-9:
                opened[kk] = tt
            qty[kk] = (t.get('held_after') if t.get('held_after') is not None else qty.get(kk, 0) + float(t.get('qty') or t.get('shares') or 1))
        else:
            q = t.get('held_after')
            qty[kk] = float(q) if q is not None else (max(0.0, qty.get(kk, 0) - float(t.get('qty') or 0)) if t.get('qty') else 0.0)
            if qty[kk] <= 1e-9 and kk in opened:
                spans.setdefault((m, e), []).append((tt - opened.pop(kk)).total_seconds() / 3600)
    out = {}
    for e in _EXPS:
        for m in ('claude', 'gemini', 'chatgpt'):
            pts = sorted(p for p in ser.get((m, e), []) if _FS < p[0] <= RACE_END_DT)
            rets = [b / a - 1 for (_, a), (_, b) in zip(pts, pts[1:]) if a]
            hs = [h for h in hold.get(m, []) if h.get('portfolio') == e]
            val = lambda h: float(h.get('value_usd') if e == 'China' and h.get('value_usd') is not None else h.get('value_cad') or 0)
            tot = sum(val(h) for h in hs)
            big = max([abs(val(h)) for h in hs if not str(h.get('holding', '')).startswith('Cash') and h.get('holding') != 'USDC'] or [0.0])
            c = (co.get(e) or {}).get(m) or {}
            sp = spans.get((m, e), [])
            out.setdefault(e, {})[m] = {
                'dd': (rk.get(e) or {}).get(m, {}).get('dd'),
                'move': round(100 * _st.pstdev(rets), 3) if len(rets) > 2 else None,
                'top': round(100 * big / tot, 1) if tot > 0 else None,
                'turnover': round(float(c.get('turnover') or 0) / 100000.0, 2) if c else None,
                'hold_h': round(sum(sp) / len(sp), 1) if sp else None, 'closed': len(sp),
                'cost_pct': round(100 * float(c.get('cost') or 0) / 100000.0, 3) if c else None,
                'beta': ((lk.get(e) or {}).get(m) or {}).get('beta'),
            }
    return out


data['penalties'] = [dict(x, model='claude') for x in r.get('claude_penalties', [])] + \
    [dict(x, model=_mid) for _mid, _m in (r.get('models') or {}).items() for x in ((_m.get('books') or {}).get('Sports') or {}).get('penalties', [])]
data['leader'] = LEADER   # the AI with the highest total profit (None when tied; the amount is never published before Nov 28); the page opens on the leader of the first race unless the viewer picked one
try:
    data['price_audit'] = [json.load(open(os.path.join(SRC, 'price_audit.json')))]   # Claude's prices vs the feeds (ops/price_audit.py)
except Exception:
    data['price_audit'] = []
try:   # what happened next: the latest price of everything sold in the last 31 days (ops/after.py, owner Oct 30)
    data['after'] = [json.load(open(os.path.join(SRC, 'after.json')))]
except Exception:
    data['after'] = []
if os.path.exists(os.path.join(SRC, 'px_long.json')):   # long price history per holding (ops/px_long.py), loaded by the page only for long chart ranges
    import shutil
    shutil.copyfile(os.path.join(SRC, 'px_long.json'), os.path.join(OUT, 'px_long.json'))
# Moments for the world to see, good and bad, by the same rules for all three AIs (owner's request, Oct 29):
# lead changes, any single trade or bet that made or lost at least 1,000 (1% of a race), penalties, fact checks found wrong, busts.
def _streaks():
    """Bet streaks, counted in GAMES (owner, Oct 31; Claude, Gemini and ChatGPT agreed W3/R1/R2: ops/streaks.py). Losing streaks too
    (Claude's change, Oct 30, so it is never selective). n = games; bets = the bet slips behind them; ids = those bets, for the panel."""
    import streaks as _SK
    out = []
    cb = [x for x in data.get('bets', []) if not x.get('placed_at') or _when(x['placed_at']) >= _FS]
    books = {('claude', 'Sports'): [dict(b, id=b.get('bet')) for b in cb]}
    for mid in ('gemini', 'chatgpt'):
        books[(mid, 'Sports')] = (((r.get('models') or {}).get(mid) or {}).get('books') or {}).get('Sports', {}).get('bets', [])
    for am in data.get('allin_models') or []:
        books[(am['id'], 'AllInSports')] = ((am.get('books') or {}).get('AllInSports') or {}).get('bets', [])
    for (mid, race), bets in books.items():
        st = _SK.streak(bets or [])
        if st and st['games'] >= 2:
            out.append(dict(st, n=st['games'], id=mid, race=race, label=_SK.label(st), short=_SK.label(st, True)))
    return out


try:
    data['streaks'] = _streaks()
except Exception as _e:
    print('streaks not built:', _e)
    data['streaks'] = []


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
# System status for visitors (Rules & Audit and the header dot): when each part last worked. The page judges "late" itself.
try:
    _soc = json.load(open(os.path.join(SRC, 'social.json'))).get('posted', {})
except Exception:
    _soc = {}
def _price_check():
    """The price check for the status board: its time and totals, plus the flags Claude confirmed wrong and has corrected
    (a corrections.json entry lists the row in "price_rows"), so a corrected flag no longer reads as "Delayed" (all three AIs agreed, Oct 30)."""
    pa = (data.get('price_audit') or [{}])[0]
    if not pa:
        return {}
    out = {k: v for k, v in pa.items() if k in ('at', 'summary')}
    try:
        corr = json.load(open(os.path.join(SRC, 'corrections.json')))
    except Exception:
        corr = []
    fixed = {}
    for c in corr:
        for h, at in (c.get('price_rows') or []):
            fixed[(h, at)] = c.get('at')
    rows = []
    for r in pa.get('rows') or []:
        if r.get('status') == 'flag' and any((b or {}).get('verdict') == 'claude_wrong' for b in (r.get('backup') or {}).values()) and (r.get('holding'), r.get('at')) in fixed:
            rows.append({'holding': r['holding'], 'at': r['at'], 'correction_at': fixed[(r['holding'], r['at'])]})
    out['corrected'] = rows
    return out


_ig = sorted((v.get('at') for v in _soc.values() if v.get('at')), reverse=True)
_notes = [n for _m in (r.get('models') or {}).values() for n in ((_m.get('last_run') or {}).get('notes') or [])]
data['status'] = [{
    'built_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'claude': max((h['at'] for h in data['history_own']), key=lambda t: _when(t), default=None),   # Claude's own last run (the watchdog reads it)
    'rivals': {mid: {'at': (m.get('last_run') or {}).get('at'), 'status': (m.get('last_run') or {}).get('status'), 'fail_streak': m.get('fail_streak', 0)} for mid, m in (r.get('models') or {}).items()},
    'odds': r.get('feeds') or {},
    'prices_missing': [n for n in _notes if 'no price' in n.lower() or 'price unavailable' in n.lower()][:5],
    'price_check': _price_check(),
    'telegram': r.get('telegram') or {},
    'instagram': {'last': _ig[0] if _ig else None, 'count_24h': sum(1 for t in _ig if (datetime.now(timezone.utc) - datetime.fromisoformat(t)).total_seconds() < 86400),
                  'error': (json.load(open(os.path.join(SRC, 'social.json'))).get('errors') if os.path.exists(os.path.join(SRC, 'social.json')) else None),
                  'blocked_until': (json.load(open(os.path.join(SRC, 'social.json'))).get('blocked_until') if os.path.exists(os.path.join(SRC, 'social.json')) else None)},
}]
data['pulse'] = [r['pulse']] if r.get('pulse') else []
data['ticker'] = (r.get('pulse') or {}).get('ticker') or []
try:
    data['facts'] = json.load(open(os.path.join(SRC, 'facts.json')))[-12:]   # official results (checked at the source), for the headline line
except Exception:
    data['facts'] = []   # the scrolling price ticker under the clocks   # each market's main price, last 1 and 3 hours (rivals.py)
data['day_reports'] = r.get('day_reports', [])   # Gemini's and ChatGPT's own Race Reports (Claude's are in report.json)
_lt = {}
for _x in r.get('thoughts', []):   # the site only ever shows each AI's latest note per race, so only those are sent (faster first load, agreed item 6)
    _k = (_x.get('model'), _x.get('experiment'))
    if _k not in _lt or _when(_x['at']) >= _when(_lt[_k]['at']):
        _lt[_k] = _x
data['rivals_thoughts'] = sorted(_lt.values(), key=lambda x: _when(x['at']))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_views
try:   # each of Claude's decisions carries its peer-grade key, so the other AIs' grades show under it (G7)
    import peer_grades as _PG
    for _t in data['trades']:   # and each trade row, for the holdings tables (owner, Oct 29)
        if _t.get('action') in ('Buy', 'Sell', 'Short', 'Cover') and not str(_t.get('holding', '')).startswith('['):
            _t['pg_key'] = _PG.key_of('claude', _t['at'], _t['portfolio'], _t['holding'], _t['action'])
    for _row in data['log']:
        _k = _PG.claude_key_for_log(_row, data['trades'], data['bets'])
        if _k:
            _row['pg_key'] = _k
except Exception as _e:
    print('peer grade keys not added:', _e)
# Claude's "vs. just holding Bitcoin" starts at the Oct 28 restart too, at the restart's exchange rate (the rate every AI's
# first trades filled at), so all three views show the same benchmark (Oct 29 review: it still had the 9:50 a.m. rate)
_RST = datetime(2026, 10, 28, 17, 44, tzinfo=timezone.utc)
_fx0 = model_views._fx_at(r.get('trades', []), _RST)
for _b in data.get('benchmark') or []:
    if _fx0 and _b.get('btc_start_usd') and _b.get('start_at') and _when(_b['start_at']) < _RST:
        _b.update(start_at=_RST.isoformat(), fx_start=_fx0)
data['models'] = model_views.build(r, {k: data[k] for k in ('indexes', 'bench_history', 'benchmark', 'prices', 'events')} | {'fx': json.load(open(os.path.join(SRC, 'fx.json')))})
try:
    data['riskdash'] = [_riskdash()]
except Exception as _e:
    print('risk dashboard not built:', _e); data['riskdash'] = []

try:   # IDs on Claude's own trades and bets, and on each rival's bets and their results (owner, Oct 30)
    if _TX:
        for _t in data.get('trades', []):
            if not str(_t.get('holding', '')).startswith('['):
                _t['tx'] = _REG.get(_TX.claude_trade_key(_t))
        for _b in data.get('bets', []):
            _k1, _k2 = _TX.claude_bet_keys(_b)
            _b['tx'] = _REG.get(_k1); _b['tx_result'] = _REG.get(_k2) if _k2 else None
        _BT = {}
        for _t in r.get('trades', []):
            if _t.get('experiment') == 'Sports' and _t.get('tx'):
                _BT[(_t['model'], _t.get('symbol'), 'bet' if _t['action'] == 'Bet' else 'res')] = _t['tx']
        for _mid, _v in (data.get('models') or {}).items():
            for _b in _v.get('bets', []):
                _b['tx'] = _BT.get((_mid, _b.get('bet'), 'bet')); _b['tx_result'] = _BT.get((_mid, _b.get('bet'), 'res'))
except Exception as _e:
    print('transaction IDs (views) skipped:', _e)
try:   # looking back: each AI's own reflection on its completed trades, keyed by the closing move's ID (all three AIs agreed, Oct 31)
    import lookback as _LB
    data['lookbacks'] = _LB.public(r)
except Exception as _e:
    print('looking back skipped:', _e); data['lookbacks'] = {}
try:   # graded holds (the latest note per race per closed race day where the AI did not trade) go into each AI's Decision log, with their grades
    import peer_grades as _PG2
    for _mid in ('claude', 'gemini', 'chatgpt'):
        _lg = data['log'] if _mid == 'claude' else ((data['models'].get(_mid) or {}).get('log'))
        if _lg is None:
            continue
        _acted = [d for d in _PG2.decisions(_mid, r) if d['action'] != 'Hold']
        for _h in _PG2._holds(_mid, r, _acted):
            _lg.append({'at': _h['at'], 'portfolio': _h['experiment'], 'action': 'Hold', 'detail': 'Held (no trade in this race that day): ' + _h['reason'], 'pg_key': _h['key']})
        _lg.sort(key=lambda x: _when(x['at']))
except Exception as _e:
    print('graded holds not added to the logs:', _e)
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
# ---- peer grades (agreed by all three AIs, Oct 29): every grade, and how each graded decision has turned out so far (G6).
# A bet: won or lost. A buy or short: the price move since (to the exit price once closed). A sale: whether the price is lower
# now than where it was sold. Moves under 0.2% count as neither right nor wrong.
def _peer():
    try:
        cg = json.load(open(os.path.join(SRC, 'claude_grades.json')))
    except Exception:
        cg = []
    pg = (r.get('peer_grades') or []) + cg
    # grades withdrawn because the grader was shown wrong information by the site (our bug, never the grader's opinion): kept, marked, never averaged
    try:
        voids = {(v['grader'], v['key']): (v['why'], v.get('at') or '') for v in json.load(open(os.path.join(SRC, 'peer_grades_void.json')))}
    except Exception:
        voids = {}
    def _void(g):   # only grades given BEFORE the withdrawal; the new grade made with the right information stands (fix, Oct 30)
        v = voids.get((g.get('grader'), g.get('key')))
        if not v:
            return None
        try:
            return v[0] if not v[1] or _when(g.get('at')) <= _when(v[1]) else None
        except Exception:
            return v[0]
    pg = [dict(g, void=_void(g)) if _void(g) else g for g in pg]
    def k_at(x):
        return _when(x).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    c_last = {}
    for _p in sorted(data.get('prices', []), key=lambda x: _when(x['at'])):
        c_last[_p['asset']] = float(_p['price'])
    for _h in data.get('holdings', []):
        _v = _h.get('price_usd', _h.get('price_local'))
        if _v is not None:
            c_last[_h['holding']] = float(_v)
    out = {}
    for g in pg:
        key = g.get('key')
        if not key or key in out:
            continue
        try:
            mid, at, exp, what, action = key.split('|', 4)
            res = None
            if action == 'Bet':
                if mid == 'claude':
                    b = next((x for x in data.get('bets', []) if x['bet'] == what), None)
                    st = b and b.get('status')
                else:
                    b = next((x for bk in ((r.get('models') or {}).get(mid, {}).get('books') or {}).values() for x in bk.get('bets', []) if x.get('id') == what), None)
                    st = b and b.get('status')
                if st in ('Won', 'Lost'):
                    res = {'state': 'closed', 'good': st == 'Won', 'what': st}
                elif st:
                    res = {'state': 'open' if st == 'Open' else 'closed', 'good': None, 'what': st}
            else:
                if mid == 'claude':
                    trs = sorted([t for t in data.get('trades', []) if t.get('portfolio') == exp and t.get('holding') == what], key=lambda t: _when(t['at']))
                    t0 = next((t for t in trs if k_at(t['at']) == at and t.get('action') == action), None)
                    p0 = t0 and t0.get('price_usd', t0.get('price_local'))
                    later = [t for t in trs if t0 and _when(t['at']) > _when(t0['at'])]
                    p1 = c_last.get(what)
                    held = any(h['portfolio'] == exp and h['holding'] == what and abs(float(h.get('quantity') or 0)) > 1e-9 for h in data.get('holdings', []))
                    pxk = lambda t: t.get('price_usd', t.get('price_local'))
                else:
                    trs = sorted([t for t in r.get('trades', []) if t.get('model') == mid and t.get('experiment') == exp and t.get('symbol') == what], key=lambda t: _when(t['at']))
                    t0 = next((t for t in trs if k_at(t['at']) == at and t.get('action') == action), None)
                    p0 = t0 and t0.get('price')
                    later = [t for t in trs if t0 and _when(t['at']) > _when(t0['at'])]
                    pos = (((r.get('models') or {}).get(mid, {}).get('books') or {}).get(exp) or {}).get('positions', {})
                    pp = next((q for kk, q in pos.items() if kk.split('|')[0] == what), None)
                    held = bool(pp)
                    p1 = pp.get('last') if pp else (later[-1].get('price') if later else None)
                    pxk = lambda t: t.get('price')
                if p0 and p1:
                    p0, p1 = float(p0), float(p1)
                    if action in ('Buy', 'Short'):
                        exit_ = next((t for t in later if t.get('action') in (('Sell',) if action == 'Buy' else ('Cover',))), None)
                        if exit_ and not held and pxk(exit_):
                            p1 = float(pxk(exit_))
                        mv = (p1 / p0 - 1) * (1 if action == 'Buy' else -1)
                        res = {'state': 'open' if held else 'closed', 'pct': round(mv, 4)}
                    else:
                        mv = p0 / p1 - 1   # sold above today's price: a good sale
                        # "move" is the plain price change since the sale, shown as such (the audit found "Closed: +0.0%" read as a realized result; Oct 30)
                        res = {'state': 'closed', 'kind': 'sale', 'pct': round(mv, 4), 'move': round(p1 / p0 - 1, 4)}
                    res['good'] = None if abs(res['pct']) < 0.002 else res['pct'] > 0
            if res:
                out[key] = res
        except Exception as _e:
            print('peer outcome skipped', key, _e)
    return pg[-2000:], out


data['peer_grades'], data['peer_outcomes'] = _peer()
# report-card grades (owner, Oct 31; all three AIs agreed) travel separately, so trade-grade averages, bias checks and stories never mix them in
data['report_grades'] = [g for g in data['peer_grades'] if g.get('action') == 'Report']
data['peer_grades'] = [g for g in data['peer_grades'] if g.get('action') != 'Report']
# A US dollar position is always worth US$1 in US dollars; what moves its C$ value is USD/CAD, so its price source is the
# exchange rate and where it came from (Oct 29 review: it said only "fixed")
try:
    _fxc = json.load(open(os.path.join(SRC, 'fx.json')))
except Exception:
    _fxc = {}
def _usd_src(rows, rate, src, at):
    for _h in rows or []:
        if str(_h.get('holding', '')).startswith('US dollar') and str(_h.get('price_source') or '').lower() in ('fixed', 'unit', '') and abs(float(_h.get('quantity') or 0)) > 1e-9 and rate:
            _h['price_source'] = src if src and 'USD/CAD' in src else f"USD/CAD {float(rate):.4f}" + (f" from {src}" if src else '')
            if at:
                _h['price_at'] = at
_usd_src(data.get('holdings'), _fxc.get('usdcad'), _fxc.get('usdcad_source'), _fxc.get('usdcad_at'))
for _mid, _mv in (data.get('models') or {}).items():
    _usd_src(_mv.get('holdings'), (r.get('fx') or {}).get('USDCAD'), 'Yahoo Finance', None)
# Call-out of the day (owner and Gemini, Oct 30): the sharpest thing one AI said about another in the last 24 hours, a fact-check found
# wrong or partly wrong, or a D or F grade on a trade. Ties go to the newest. Shown on Home and in the daily race post.
try:
    _now = datetime.now(timezone.utc)
    def _ts(x):
        return datetime.fromisoformat(str(x).replace('Z', '+00:00'))
    _cand = []
    for x in []:   # owner, Oct 30: the call-out is the worst GRADE only (fact-checks keep their own line under each take); Praise of the day sits under it
        if x.get('verdict') in ('wrong', 'partly') and x.get('text') and x.get('checker') and x.get('checker') != x.get('model'):
            _cand.append({'kind': 'fact', 'at': x['at'], 'by': x['checker'], 'about': x.get('model') or 'claude', 'race': x.get('experiment'),
                          'verdict': x['verdict'], 'said': x.get('take', ''), 'text': x['text'], 'source': x.get('source'), 'score': 3 if x['verdict'] == 'wrong' else 2})
    for x in data.get('peer_grades') or []:
        if x.get('grade') in ('D', 'F') and x.get('text') and x.get('grader') != x.get('model') and not x.get('void'):   # a withdrawn grade is never the call-out
            _cand.append({'kind': 'grade', 'at': x['at'], 'by': x['grader'], 'about': x['model'], 'race': x.get('experiment'), 'grade': x['grade'],
                          'said': _said(x), 'text': x['text'], 'score': 3 if x['grade'] == 'F' else 2})
    _co = None
    for _hrs in (24, 72):
        _p = [c for c in _cand if _now - _ts(c['at']) <= timedelta(hours=_hrs)]
        if _p:
            _co = max(_p, key=lambda c: (c['score'], _ts(c['at'])))
            break
    data['callout'] = [{k: v for k, v in _co.items() if k != 'score'}] if _co else []
    _by = {}
    for _race in sorted({c['race'] for c in _cand if c.get('race')}):   # each race's own call-out: last 24 hours, else the last 72
        for _hrs in (24, 72):
            _p = [c for c in _cand if c.get('race') == _race and _now - _ts(c['at']) <= timedelta(hours=_hrs)]
            if _p:
                _by[_race] = {k: v for k, v in max(_p, key=lambda c: (c['score'], _ts(c['at']))).items() if k != 'score'}
                break
    data['callout_by_race'] = [_by]
except Exception as _e:
    print('call-out skipped:', _e)
    data['callout'] = []
    data['callout_by_race'] = [{}]

# Praise of the day (owner, Oct 30): the opposite of the call-out. A decision that BOTH of the other two AIs graded A (A+, A or A-),
# graded anonymously and before the result was known. The newest in the last 24 hours, else 72; each race has its own.
try:
    _now = datetime.now(timezone.utc)
    def _ts2(x):
        return datetime.fromisoformat(str(x).replace('Z', '+00:00'))
    _gk = {}
    for x in data.get('peer_grades') or []:
        if x.get('void') or not x.get('text') or x.get('grader') == x.get('model') or not x.get('key'):
            continue
        _k = (x['key'], x['grader'])
        if _k not in _gk or str(x['at']) > str(_gk[_k]['at']):   # each grader's latest grade on that decision
            _gk[_k] = x
    _byk = {}
    for (_key, _gr), x in _gk.items():
        _byk.setdefault(_key, []).append(x)
    _PTS = {'A+': 4.3, 'A': 4, 'A-': 3.7}
    _pc = []
    for _key, gs in _byk.items():
        if len({g['grader'] for g in gs}) >= 2 and all(g.get('grade') in _PTS for g in gs):
            gs = sorted(gs, key=lambda g: g['grader'])
            x = gs[0]
            _pc.append({'kind': 'praise', 'at': x.get('decision_at') or x['at'], 'graded_at': max(g['at'] for g in gs), 'about': x['model'], 'race': x.get('experiment'),
                        'said': _said(x), 'grades': [{'by': g['grader'], 'grade': g['grade'], 'text': g['text']} for g in gs],
                        'score': sum(_PTS[g['grade']] for g in gs)})
    def _pick(pool):
        for _hrs in (24, 72):
            _p = [c for c in pool if _now - _ts2(c['graded_at']) <= timedelta(hours=_hrs)]
            if _p:
                return {k: v for k, v in max(_p, key=lambda c: (c['score'], _ts2(c['graded_at']))).items() if k != 'score'}
        return None
    _pr = _pick(_pc)
    data['praise'] = [_pr] if _pr else []
    _pby = {}
    for _race in sorted({c['race'] for c in _pc if c.get('race')}):
        _v = _pick([c for c in _pc if c.get('race') == _race])
        if _v:
            _pby[_race] = _v
    data['praise_by_race'] = [_pby]
except Exception as _e:
    print('praise skipped:', _e)
    data['praise'] = []
    data['praise_by_race'] = [{}]

import hashlib as _hl
data.pop('ver', None)
data['page_ver'] = PAGE_VER
data['ver'] = _hl.sha1(json.dumps(data, separators=(',', ':'), sort_keys=True).encode()).hexdigest()[:16]
# ---- Data & stats (owner, Oct 31: a reviewer's "10/10" list; Claude, Gemini and ChatGPT all agreed: ops/review/ten-r1-oct31.json) ----
# B1: every record as plain CSV files anyone can download and analyse (papertrades.ai/data/...); C2: decision-quality stats per AI and
# race, computed the same way for all three; A1: how often each AI checked in and how fresh the data is (measured, not claimed).
import csv as _csv
def _w(x):
    return datetime.fromisoformat(str(x).replace('Z', '+00:00')).astimezone(timezone.utc)
_LAB = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
_RT = list(r.get('trades', []))
_src = lambda n: json.load(open(os.path.join(SRC, n + '.json')))
# one list of moves for all three AIs (Claude's ten races from trades.json and bets.json; everything else from rivals.json)
_moves = []
for t in _src('trades'):
    _moves.append({'ai': 'claude', 'race': t.get('portfolio'), 'at': _w(t['at']), 'action': t.get('action'), 'what': t.get('holding'), 'symbol': t.get('holding'),
                   'qty': t.get('qty'), 'price': t.get('price_usd') if t.get('price_usd') is not None else t.get('price_local'), 'amount': t.get('cad'),
                   'cur': 'USD' if t.get('portfolio') == 'China' else 'CAD', 'reason': t.get('note') or '', 'wrong_if': t.get('wrong_if') or '', 'pnl': t.get('pnl_cad'), 'id': t.get('tx') or ''})
for b in _src('bets'):
    if b.get('placed_at'):
        _moves.append({'ai': 'claude', 'race': 'Sports', 'at': _w(b['placed_at']), 'action': 'Bet', 'what': f"{b.get('pick')} ({b.get('event')})", 'symbol': b.get('bet'),
                       'qty': None, 'price': b.get('odds'), 'amount': b.get('stake_cad'), 'cur': 'CAD', 'reason': b.get('note') or '', 'wrong_if': b.get('wrong_if') or '', 'pnl': None, 'id': b.get('tx') or ''})
    if b.get('status') in ('Won', 'Lost', 'Push', 'Void') and b.get('settled_at'):
        _moves.append({'ai': 'claude', 'race': 'Sports', 'at': _w(b['settled_at']), 'action': b['status'], 'what': f"{b.get('pick')} ({b.get('event')})", 'symbol': b.get('bet'),
                       'qty': None, 'price': b.get('odds'), 'amount': b.get('result_cad'), 'cur': 'CAD', 'reason': b.get('final') or '', 'wrong_if': '', 'pnl': float(b.get('result_cad') or 0), 'id': ''})
for t in _RT:
    if t.get('model') not in _LAB:
        continue
    _moves.append({'ai': t['model'], 'race': t.get('experiment'), 'at': _w(t['at']), 'action': t.get('action'), 'what': t.get('name') or t.get('symbol'), 'symbol': t.get('symbol'),
                   'qty': t.get('qty'), 'price': t.get('price'), 'amount': t.get('amount'), 'cur': t.get('cur') or 'CAD', 'reason': t.get('reason') or '', 'wrong_if': t.get('wrong_if') or '',
                   'pnl': (float(t['amount']) if t.get('action') in ('Won', 'Lost') and t.get('amount') is not None else 0.0 if t.get('action') in ('Push', 'Void') else t.get('pnl')),
                   'id': t.get('tx') or '', 'outcome': t.get('outcome')})
_moves.sort(key=lambda m: m['at'])
_RS = datetime(2026, 10, 28, 17, 45, tzinfo=timezone.utc)   # the restart: earlier moves (tuning runs, pre-race bets) are kept in the download but never counted
for m in _moves:
    m['counts'] = m['at'] >= _RS and not str(m.get('what') or '').startswith('[')
_all_moves, _moves = _moves, [m for m in _moves if m['counts']]
# average-cost profit on every sale or cover (the same rule as the site's tables), holding time from when the position was opened
_pos, _closed, _episodes = {}, [], []
for m in _moves:
    a = m['action']
    if a not in ('Buy', 'Sell', 'Short', 'Cover'):
        continue
    k = (m['ai'], m['race'], m['symbol'], m.get('outcome'))
    p = _pos.setdefault(k, {'q': 0.0, 'c': 0.0, 'sq': 0.0, 'sp': 0.0, 'start': None, 'ep': None})
    q, amt = float(m.get('qty') or 0), float(m.get('amount') or 0)
    if a in ('Buy', 'Short'):
        if (p['q'] <= 1e-9 and a == 'Buy') or (p['sq'] <= 1e-9 and a == 'Short'):
            p['start'] = m['at']; p['ep'] = {'ai': m['ai'], 'race': m['race'], 'pnl': 0.0, 'open': True, 'openers': []}; _episodes.append(p['ep'])
        p['ep']['openers'].append(m)
        if a == 'Buy':
            p['q'] += q; p['c'] += amt
        else:
            p['sq'] += q; p['sp'] += amt
        continue
    pnl = m.get('pnl')
    if pnl is None and q > 0:
        if a == 'Sell' and p['q'] > 1e-9:
            basis = p['c'] / p['q'] * min(q, p['q']); pnl = amt - basis; p['c'] -= basis; p['q'] = max(0.0, p['q'] - q)
        elif a == 'Cover' and p['sq'] > 1e-9:
            basis = p['sp'] / p['sq'] * min(q, p['sq']); pnl = basis - amt; p['sp'] -= basis; p['sq'] = max(0.0, p['sq'] - q)
    elif pnl is not None and q > 0 and a == 'Sell' and p['q'] > 1e-9:
        p['c'] -= p['c'] / p['q'] * min(q, p['q']); p['q'] = max(0.0, p['q'] - q)
    hold = (m['at'] - p['start']).total_seconds() / 3600 if p.get('start') else None
    _closed.append({'ai': m['ai'], 'race': m['race'], 'pnl': pnl, 'hold_h': hold, 'stop': str(m['reason']).startswith('Stop order reached'), 'target': str(m['reason']).startswith('Target order reached')})
    if p.get('ep') is not None and pnl is not None:
        p['ep']['pnl'] += pnl
        if p['q'] <= 1e-9 and p['sq'] <= 1e-9:
            p['ep']['open'] = False; p['start'] = None; p['ep'] = None
for m in _moves:
    if m['action'] in ('Won', 'Lost', 'Push', 'Void'):
        _closed.append({'ai': m['ai'], 'race': m['race'], 'pnl': m['pnl'], 'hold_h': None, 'stop': False, 'target': False, 'bet': True})
_usdcad = float((json.load(open(os.path.join(SRC, 'fx.json'))) or {}).get('usdcad') or 1.39)
for x in _closed:   # the all-races rows are in C$ (China stocks converted from US$ at the latest rate)
    x['pnl_c'] = (x['pnl'] * _usdcad if x['race'] == 'China' else x['pnl']) if x['pnl'] is not None else None
def _qual(rows):
    known = [x for x in rows if x['pnl'] is not None]
    w, l = [x['pnl'] for x in known if x['pnl'] > 0.5], [x['pnl'] for x in known if x['pnl'] < -0.5]
    hs = [x['hold_h'] for x in rows if x.get('hold_h') is not None]
    return {'closed': len(rows), 'known': len(known), 'wins': len(w), 'losses': len(l), 'win_rate': (len(w) / (len(w) + len(l))) if (w or l) else None,
            'avg_win': (sum(w) / len(w)) if w else None, 'avg_loss': (sum(l) / len(l)) if l else None, 'total': sum(x['pnl'] for x in known),
            'avg_hold_h': (sorted(hs)[len(hs) // 2] if hs else None), 'stops': sum(1 for x in rows if x['stop']), 'targets': sum(1 for x in rows if x['target'])}
_QR = []
for _ai in _LAB:
    for _race in sorted({x['race'] for x in _closed if x['ai'] == _ai}):
        _QR.append(dict(_qual([x for x in _closed if x['ai'] == _ai and x['race'] == _race]), ai=_ai, race=_race))
    _QR.append(dict(_qual([dict(x, pnl=x['pnl_c']) for x in _closed if x['ai'] == _ai and not str(x['race']).startswith('AllIn')]), ai=_ai, race='All ten races'))
# did the rivals' grades predict the results? each graded bet or buy whose result is known (a bet's result; a buy's whole position, once closed)
_GN = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}
_res = []
for g in data.get('peer_grades', []):
    if g.get('grade') not in _GN or g.get('void') or g.get('action') not in ('Bet', 'Buy', 'Short'):
        continue
    t0, sym = _w(g.get('decision_at') or g['at']), str(g.get('key') or '').split('|')[3] if len(str(g.get('key') or '').split('|')) > 4 else None
    out = None
    if g['action'] == 'Bet':
        rr = [m for m in _moves if m['ai'] == g['model'] and m['race'] == g.get('experiment') and m['action'] in ('Won', 'Lost') and sym and m['symbol'] == sym]
        out = rr[0]['pnl'] if rr else None
    else:
        for ep in _episodes:
            if ep['ai'] == g['model'] and ep['race'] == g.get('experiment') and not ep['open'] and any(abs((o['at'] - t0).total_seconds()) < 120 and (not sym or o['symbol'] == sym) for o in ep['openers']):
                out = ep['pnl']; break
    if out is not None and abs(out) > 0.5:
        _res.append({'grade': g['grade'], 'grader': g.get('grader'), 'won': out > 0})
data['quality'] = [{'rows': _QR, 'by_grade': [{'grade': k, 'n': sum(1 for x in _res if x['grade'] == k), 'won': sum(1 for x in _res if x['grade'] == k and x['won'])} for k in 'ABCDF'],
                   'by_grader': [{'grader': gr, 'avg_win': (lambda a: sum(a) / len(a) if a else None)([_GN[x['grade']] for x in _res if x['grader'] == gr and x['won']]),
                                  'avg_loss': (lambda a: sum(a) / len(a) if a else None)([_GN[x['grade']] for x in _res if x['grader'] == gr and not x['won']]),
                                  'n': sum(1 for x in _res if x['grader'] == gr)} for gr in _LAB],
                   'at': datetime.now(timezone.utc).isoformat(timespec='seconds')}]   # a one-item list, like story and geo
# A1: check-ins in the last 24 hours, the longest gap between them, and the latest one, per AI (from the value records)
_now = datetime.now(timezone.utc)
_ci = {'claude': sorted({_w(h['at']).replace(second=0, microsecond=0) for h in _src('history')})}
for h in r.get('history', []):
    if h.get('model') in ('gemini', 'chatgpt'):
        _ci.setdefault(h['model'], set()).add(_w(h['at']).replace(second=0, microsecond=0))
_spd = []
for _ai in _LAB:
    ts = sorted(_ci.get(_ai) or [])
    last24 = [t for t in ts if _now - t <= timedelta(hours=24)]
    span = ([ts[ts.index(last24[0]) - 1]] if last24 and ts.index(last24[0]) > 0 else []) + last24 + [_now]
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(span, span[1:])]
    _spd.append({'ai': _ai, 'n24': len(last24), 'max_gap_min': round(max(gaps)) if gaps else None, 'last': ts[-1].isoformat() if ts else None})
_lag = [x for x in r.get('alert_lag', []) if x.get('fill') and x.get('posted')]
for s_ in _spd:
    L = sorted((_w(x['posted']) - _w(x['fill'])).total_seconds() for x in _lag if x.get('model') == s_['ai'])
    s_['lag_n'], s_['lag_med_s'] = len(L), (round(L[len(L) // 2]) if L else None)
data['speed'] = _spd
# B1: the CSV downloads (every move, every value per race at every check-in, Claude's price record, every grade), with a README
_dd = os.path.join(OUT, 'data'); os.makedirs(_dd, exist_ok=True)
def _csvw(name, head, rows):
    with open(os.path.join(_dd, name), 'w', newline='') as f:
        w = _csv.writer(f); w.writerow(head); [w.writerow(x) for x in rows]
_csvw('moves.csv', ['time_utc', 'ai', 'race', 'action', 'what', 'symbol', 'quantity', 'price', 'amount', 'currency', 'id', 'reason', 'wrong_if', 'counts_in_race'],
      [[m['at'].isoformat(), _LAB[m['ai']], m['race'], m['action'], m['what'], m['symbol'], m['qty'], m['price'], m['amount'], m['cur'], m.get('id') or '', m['reason'], m['wrong_if'], 'yes' if m['counts'] else 'no (before the Oct 28 restart)'] for m in _all_moves])
_vals = [(_w(h['at']), 'claude', h['portfolio'], h['value']) for h in _src('history')] + [(_w(h['at']), h['model'], h['experiment'], h['value']) for h in r.get('history', []) if h.get('model') in _LAB]
_csvw('values.csv', ['time_utc', 'ai', 'race', 'value'], [[a.isoformat(), _LAB[b], c, d] for a, b, c, d in sorted(_vals)])
_csvw('prices_claude.csv', ['time_utc', 'asset', 'price', 'source'], [[_w(p_['at']).isoformat(), p_.get('asset'), p_.get('price'), p_.get('source') or ''] for p_ in sorted(_src('prices'), key=lambda x: _w(x['at']))])
_csvw('grades.csv', ['graded_utc', 'grader', 'about_ai', 'race', 'decision_utc', 'action', 'what', 'grade', 'reason'],
      [[g.get('at'), _LAB.get(g.get('grader'), g.get('grader')), _LAB.get(g.get('model'), g.get('model')), g.get('experiment'), g.get('decision_at'), g.get('action'), g.get('what'), g.get('grade'), g.get('text')]
       for g in data.get('peer_grades', [])])
open(os.path.join(_dd, 'README.txt'), 'w').write(
    'PaperTrades.AI Season 1 data (pretend money, real prices; Oct 28 to Nov 28, 2026). Updated at every check-in.\n\n'
    'moves.csv: every trade, bet and bet result of Claude, Gemini and ChatGPT in the ten races and the High risk side race, with its own reason.\n'
    '  amount is in the race\'s currency (C$, or US$ for China stocks); for a bet result it is the profit or loss.\n'
    'values.csv: each AI\'s value in each race at every check-in.\nprices_claude.csv: every price Claude used, with its source.\n'
    'grades.csv: every grade one AI gave another, given anonymously and before the result.\n\n'
    'The full record is fingerprinted every night (SHA-256, see Rules & Audit on papertrades.ai). Not financial advice.\n')
try:   # the audit pack: everything in one zip for a visitor's own AI (owner, Nov 1; all three AIs agreed)
    import audit_pack
    audit_pack.build(data, os.path.join(_dd, 'papertrades-audit-pack.zip'), _dd)
except Exception as _e:
    print('audit pack failed', _e)
data['downloads'] = [{'file': n, 'bytes': os.path.getsize(os.path.join(_dd, n))} for n in ('papertrades-audit-pack.zip', 'moves.csv', 'values.csv', 'prices_claude.csv', 'grades.csv', 'README.txt') if os.path.exists(os.path.join(_dd, n))]
data.pop('history_own', None)   # Claude's own valuations are not published twice (R4: the site shows the runner's)
json.dump(data, open(os.path.join(OUT, 'data.json'), 'w'), separators=(',', ':'))  # compact: smaller and faster to load
open(os.path.join(OUT, 'data.ver'), 'w').write(data['ver'])

# What a reader without JavaScript sees (Google, link previews, AI assistants): the day, who leads each race and the latest take,
# written straight into the page. The page's own code replaces it as it loads, so visitors see no difference (owner and Gemini, Oct 30).
try:
    import html as _hm
    _ip = os.path.join(OUT, 'index.html'); _pg = open(_ip).read()
    _AI = {'claude': 'Claude', 'gemini': 'Gemini', 'chatgpt': 'ChatGPT'}
    _LB = {'Stocks': 'Stocks and anything', 'Crypto': 'Crypto', 'China': 'China stocks', 'Metals': 'Metals', 'Energy': 'Oil and energy', 'Options': 'Options',
           'Currencies': 'Currencies (forex)', 'Safe': 'Play it safe', 'Sports': 'Sports betting', 'Predictions': 'Prediction markets'}
    _et = datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))   # EDT, then EST from Nov 1
    _day = max(1, min(32, (_et.date() - datetime(2026, 10, 28).date()).days + 1))
    _lead = _AI.get(data.get('leader') or '', '')
    _rows = []
    for _e, _lab in _LB.items():
        _r = (data.get('exp_standings') or {}).get(_e) or []
        if not _r:
            continue
        _sym = 'US$' if _e == 'China' else 'C$'
        _f = lambda v: ('+' if v >= 0 else '−') + _sym + f'{abs(v):,.0f}'
        if max(x['profit'] for x in _r) - min(x['profit'] for x in _r) < 0.5:
            _rows.append(f'<li><b>{_lab}</b>: all level so far</li>')
        else:
            _rows.append(f'<li><b>{_lab}</b>: ' + ', '.join(f"{i + 1}. {_AI.get(x['id'], x['id'])} {_f(x['profit'])}" for i, x in enumerate(_r[:3])) + '</li>')
    _snap = (f'<h2>Race standings</h2><p>Season 1 · Day {_day} of 32' + (f'. {_lead} leads overall (ranked by total profit since the Oct 28 restart, ' + ', '.join(f"{i + 1}. {_AI.get(x['id'], x['id'])} " + ('+' if x['profit'] >= 0 else '−') + f"C${abs(x['profit']):,.0f}" for i, x in enumerate(data.get('standings') or [])) + ')' if _lead else '') +
             '. Profit in each race since the Oct 28 restart:</p><ol>' + ''.join(_rows) + '</ol>')
    _pg = _pg.replace('aria-label="Race standings"></aside>', 'aria-label="Race standings">' + _snap + '</aside>', 1)
    _pg = _pg.replace('Day <b data-draw="day-num">—</b> of <b data-draw="day-total">—</b>', f'Day <b data-draw="day-num">{_day}</b> of <b data-draw="day-total">32</b>', 1)
    _tk = [x for x in (data.get('take') or []) if x.get('text') and not x.get('experiment')] or [x for x in (data.get('take') or []) if x.get('text')]
    if _tk:
        _pg = _pg.replace('<span data-draw="take" data-source="take">—</span>', '<span data-draw="take" data-source="take">“' + _hm.escape(_tk[-1]['text']) + '” — Claude</span>', 1)
    _co = (data.get('callout') or [None])[0]
    if _co:
        _lbl = ('FOUND WRONG' if _co.get('verdict') == 'wrong' else 'PARTLY WRONG') if _co['kind'] == 'fact' else 'GRADE ' + _co.get('grade', '')
        _pg = _pg.replace('<div class="st-callout gr" data-draw="callout" data-source="callout callout_by_race praise praise_by_race"></div>',
            '<div class="st-callout gr" data-draw="callout" data-source="callout callout_by_race praise praise_by_race"><p><b>Call-out of the day</b>: ' + _AI.get(_co['by'], _co['by']) + ' on ' + _AI.get(_co['about'], _co['about']) +
            ' (' + _lbl + '). ' + _hm.escape(_co['text']) + '</p></div>', 1)
    if datetime.now(timezone.utc) < datetime(2026, 11, 28, 21, 0, tzinfo=timezone.utc):   # the hidden "has ended" line only exists after the final scoring (readers without JavaScript saw it on day 3; audit, Oct 30)
        _pg = _pg.replace('<p class="st-progress" data-phase="ended" hidden><span>The experiment has ended. Final results are below.</span></p>', '<p class="st-progress" data-phase="ended" hidden></p>', 1)
    _fp = data.get('fingerprints') or []
    if _fp:
        _pg = _pg.replace('<span data-fp-chip>Every trade fingerprinted nightly</span>', '<span data-fp-chip>Ledger verified through ' + datetime.fromisoformat(_fp[-1]['day']).strftime('%b %-d') + '</span>', 1)
    if _lead:   # link previews and search results say who is winning today
        _d1 = f'Season 1 · Day {_day} of 32: {_lead} leads. '
        _pg = _pg.replace('<meta name="description" content="', '<meta name="description" content="' + _d1, 1).replace('<meta property="og:description" content="', '<meta property="og:description" content="' + _d1, 1)
    open(_ip, 'w').write(_pg)
except Exception as _e:
    print('static snapshot skipped:', _e)

open(os.path.join(OUT, 'CNAME'), 'w').write('papertrades.ai\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')
print('built', os.path.getsize(os.path.join(OUT, 'index.html')), 'bytes index,', os.path.getsize(os.path.join(OUT, 'data.json')), 'bytes data')
