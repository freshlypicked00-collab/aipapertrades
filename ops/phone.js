/* THE PHONE PASS (owner, Nov 20, 2026: "does papertrades.ai look 10/10 on mobile? make it 10/10. I'm happy with the current layout on
   desktop but mobile needs a lot of work ... ready to go on the first page of a newspaper ... amazing and easy to use for humans and
   first time visitors"). Claude with Gemini and ChatGPT: ops/review/PHONE_PASS_NOV20.md.

   THE RULES OF THIS FILE
   1. Phones only. Every part runs only while the screen is 700 px wide or less (the site's own phone width). On a wider screen it adds
      nothing and takes away whatever it added, so the computer layout is exactly what it was.
   2. No new numbers. The front page reads its three totals from the leader box the site already fills, so they can never differ from
      it; the list of races uses the same data and the same formatter as the site's own Scoreboard. Nothing here changes a race number.
   3. Reversible. One switch per part (ON, just below). Empty this file and ops/phone.css to reverse the whole pass. */
(function () {
  'use strict';
  var ON = { front: true, races: true, bar: true };
  var PH = window.matchMedia('(max-width: 700px)');
  var root = document.documentElement;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var mk = function (tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  var later = function (fn, ms) { return setTimeout(function () { try { fn(); } catch (e) {} }, ms); };
  var debounce = function (fn, ms) { var t = null; return function () { clearTimeout(t); t = setTimeout(function () { try { fn(); } catch (e) {} }, ms); }; };
  var onPhone = function (fn) { try { PH.addEventListener('change', fn); } catch (e) { try { PH.addListener(fn); } catch (e2) {} } };
  var ais = function () { try { return AIS; } catch (e) { return null; } };
  var idOf = function (name) { var A = ais(); if (!A) return null; for (var k in A) if (A[k].label === name) return k; return null; };
  var finale = function () { return root.classList.contains('pt-finale'); };
  var unclass = function () { for (var i = 0; i < arguments.length; i++) if (root.classList.contains(arguments[i])) root.classList.remove(arguments[i]); };   // never writes the class attribute when there is nothing to take off (a write, even of the same value, wakes everything that watches it)
  var calm = function () { try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } };   // a visitor who asked their phone for less motion gets a jump, not a glide
  var press = function (sel) { var b = $(sel); if (b) b.click(); return !!b; };
  var go = function (name) { try { goTab(name); } catch (e) { press('.st-tab[data-tab="' + name + '"]'); } };

  /* P1. THE FRONT PAGE (Overview, first screen). Before: a safety banner, a welcome card of two dense paragraphs, the leader box in
         13 px type, the side-race box, a cue line and five status lines, all the same weight: nothing said "start here".
         Now, in this order: the day, the question the site answers, (first visit: what it is, in the site's own words), the three
         overall totals as a podium, how to read them, (first visit: two buttons and the fairness note), then the countdown.
         The podium is read from the leader box, which stays in the page (hidden on phones while the podium is up) and is still what a
         tap opens: AI vs AI. If the leader box has no totals (a tie at the top), the box itself shows, exactly as before. */
  var front = null, front2 = null, frontSig = '';
  var readPill = function () {
    var chip = $('header.st-head .st-crown-line .st-crown-chip:not(.st-allin-chip)'); if (!chip || chip.hidden) return null;
    var n1 = $(':scope > .cr-n', chip), p1 = $(':scope > .cr-p', chip); if (!n1 || !p1) return null;
    var rows = [{ name: n1.textContent.trim(), amt: p1.textContent.trim(), up: p1.classList.contains('up') }];
    $$(':scope > .cr-g:not(.cr-races)', chip).forEach(function (g) { var n = $('.cr-n2', g), p = $('.cr-p', g); if (n && p) rows.push({ name: n.textContent.trim(), amt: p.textContent.trim(), up: p.classList.contains('up') }); });
    if (rows.length !== 3 || rows.some(function (r) { return !idOf(r.name); })) return null;
    var rc = $(':scope > .cr-races', chip), parts = [];   // its pieces sit side by side with no spaces between them: join them with one
    if (rc) Array.prototype.forEach.call(rc.childNodes, function (n) { var t = (n.textContent || '').replace(/\s+/g, ' ').trim(); if (t) parts.push(t); });
    return { chip: chip, rows: rows, races: parts.join(' ').replace(/^[\s·]+/, '').trim() };
  };
  var num = function (s) { var v = parseFloat(String(s).replace(/[^0-9.]/g, '')); return isFinite(v) ? v : 0; };
  var dayLine = function () {
    var p = $('header.st-head p.st-progress[data-phase="live"]'); if (!p) return 'Season 1';
    if (finale() || p.classList.contains('is-ended')) return 'Season 1 is over';
    var s = $('b.st-season', p); var t = s && s.parentNode ? s.parentNode.textContent.replace(/\s+/g, ' ').trim() : '';
    var m = /Day \d+ of \d+/.exec(t); return m ? m[0] : 'Season 1';   // the Season 1 badge sits right above this line
  };
  var dropFront = function () { if (front) front.remove(); if (front2) front2.remove(); front = front2 = null; frontSig = ''; unclass('pt-fr-on', 'pt-pod-on', 'pt-fr-new'); };
  var drawFront = function () {
    if (!ON.front || !PH.matches) { dropFront(); return; }
    var head = $('header.st-head'), title = head && $('h1.st-title', head); if (!title) return;
    var pill = readPill();
    var wel = $('.pt-welcome.pt-hero', head); var intro = !!(wel && !wel.hidden && wel.isConnected && $('.pt-hero-p', wel));
    var sig = [dayLine(), pill ? pill.rows.map(function (r) { return r.name + r.amt; }).join('|') + pill.races : 'none', intro, finale()].join('~');
    if (front && front.isConnected && sig === frontSig) return;
    frontSig = sig;
    var f = mk('div', 'pt-fr');
    f.appendChild(mk('p', 'pt-fr-k', dayLine()));
    f.appendChild(mk('h2', 'pt-fr-h', 'Which AI makes the most (pretend) money?'));
    if (intro) { var p0 = $('.pt-hero-p:not(.pt-hero-fair)', wel); if (p0) { var c0 = p0.cloneNode(true); c0.className = 'pt-fr-p'; f.appendChild(c0); } }
    if (pill) {
      var pod = mk('button', 'pt-pod'); pod.type = 'button';
      var lab = pill.chip.getAttribute('aria-label'); if (lab) pod.setAttribute('aria-label', lab);
      pod.addEventListener('click', function () { pill.chip.click(); });
      var h = mk('span', 'pt-pod-h'); h.append(mk('b', '', 'Overall'), mk('span', '', 'total profit across all ten races'), mk('span', 'pt-pod-tag', 'pretend money'));
      pod.appendChild(h);
      var max = Math.max.apply(null, pill.rows.map(function (r) { return num(r.amt); })) || 1;
      pill.rows.forEach(function (r, i) {
        var id = idOf(r.name), A = ais();
        var row = mk('span', 'pt-pod-r' + (i === 0 ? ' is-1' : '')); row.style.setProperty('--ai', A[id].color);
        var face = mk('span', 'pt-pod-face'); try { face.appendChild(window.ptRobot(id, 0, i === 0)); } catch (e) {}
        var nm = mk('span', 'pt-pod-n'); nm.appendChild(mk('b', '', r.name)); try { var tg = modelTag(id); if (tg) { var sm = mk('small', '', tg); sm.setAttribute('translate', 'no'); nm.appendChild(sm); } } catch (e) {}
        var bar = mk('span', 'pt-pod-b ' + (r.up ? 'up' : 'down')); var fill = mk('i'); fill.style.width = Math.max(1, Math.round(num(r.amt) / max * 500) / 10) + '%'; bar.appendChild(fill);   // a share of the whole track: the biggest amount reaches one end
        row.append(mk('span', 'pt-pod-k', i === 0 ? '1st' : i === 1 ? '2nd' : '3rd'), face, nm, mk('span', 'pt-pod-p ' + (r.up ? 'up' : 'down'), r.amt), bar);
        pod.appendChild(row);
      });
      if (pill.races) pod.appendChild(mk('span', 'pt-pod-f', pill.races));
      pod.appendChild(mk('span', 'pt-pod-go', 'Compare all three in AI vs AI →'));
      f.appendChild(pod);
    }
    var f2 = null;
    if (intro) {   // first visit: the welcome card's own buttons and its fairness note, same words; the card itself stays in the page, unseen on phones
      f2 = mk('div', 'pt-fr2');
      var row2 = mk('div', 'pt-fr-cta');
      var b1 = mk('button', 'pt-fr-btn is-main', ON.races ? 'See the ten races' : 'See the races'); b1.type = 'button';
      b1.addEventListener('click', function () { var t = $('#pt-races') || $('.st-podium'); if (t) t.scrollIntoView({ behavior: calm() ? 'auto' : 'smooth', block: 'start' }); });
      var orig2 = $('.pt-wel-btn:not(.is-main)', wel);
      var b2 = mk('button', 'pt-fr-btn', orig2 ? orig2.textContent : '🔔 Get notified'); b2.type = 'button';
      b2.addEventListener('click', function () { var o = $('.pt-welcome .pt-wel-btn:not(.is-main)'); if (o) o.click(); else press('.st-tt-notify'); });
      row2.append(b1, b2); f2.appendChild(row2);
      var fair = $('.pt-hero-fair', wel);
      if (fair) { var c1 = fair.cloneNode(true); c1.className = 'pt-fr-fair';
        $$('a', c1).forEach(function (a, i) { a.addEventListener('click', function (e) { var o = $$('.pt-welcome .pt-hero-fair a')[i]; if (o) { e.preventDefault(); o.click(); } }); });
        f2.appendChild(c1); }
      var hide = mk('button', 'pt-fr-hide', 'Hide this introduction'); hide.type = 'button';
      hide.addEventListener('click', function () { if (!press('.pt-welcome .pt-wel-x')) { var w = $('.pt-welcome'); if (w) w.remove(); } later(drawFront, 30); });
      f2.appendChild(hide);
    }
    if (front) front.remove(); if (front2) front2.remove();
    front = f; front2 = f2;
    title.after(f); if (f2) f.after(f2);
    root.classList.add('pt-fr-on'); root.classList.toggle('pt-pod-on', !!pill); root.classList.toggle('pt-fr-new', intro);
  };
  try {
    var kickFront = debounce(drawFront, 60);
    // drawn in the same step in which the site fills its leader box (this listener runs right after the site's own), so the phone never
    // shows the old top for a moment first; the timers are a second chance
    try { dash.onData(function () { try { drawFront(); } catch (e) {} }); } catch (e) {}
    later(drawFront, 300); later(drawFront, 1200); later(drawFront, 3000);
    onPhone(drawFront);
    var hd = $('header.st-head');
    if (hd && window.MutationObserver) {
      new MutationObserver(function (ms) { for (var i = 0; i < ms.length; i++) { var t = ms[i].target; if (front && (t === front || front.contains(t))) continue; if (front2 && (t === front2 || front2.contains(t))) continue; kickFront(); return; } }).observe(hd, { childList: true });
      var line = null, mo2 = new MutationObserver(kickFront);
      var hook = function () { var l = $('.st-crown-line', hd); if (l && l !== line) { line = l; mo2.observe(l, { childList: true, subtree: true }); kickFront(); } };
      hook(); later(hook, 1500); later(hook, 4000);
      var wasOver = finale();   // the finish (html.pt-finale) changes the day line and the list's wording: redraw both then, and only then
      new MutationObserver(function () { var f = finale(); if (f === wasOver) return; wasOver = f; kickFront(); later(drawRaces, 80); }).observe(root, { attributes: true, attributeFilter: ['class'] });
    }
    setInterval(function () { try { drawFront(); } catch (e) {} }, 60000);   // the day number turns over at midnight ET
  } catch (e) {}

  /* P2. THE TEN RACES at a glance (Overview, right under the front page). Before, the only way to see who was ahead in a race on a
         phone was a drop-down menu inside the Race standings card, which opens on a side race. Now one short list: each race, who is
         first in it, and that AI's profit or loss so far; a tap opens the race as that AI (what a Scoreboard tile does).
         "First" follows the site's own rule (the standings data's list of races each AI leads; level races lead nothing), the amounts
         are the same figures and formatter as the Scoreboard, and the side race is listed apart, as everywhere on the site. */
  var races = null, racesSig = '';
  var KEYS = ['Stocks', 'Crypto', 'China', 'Metals', 'Energy', 'Options', 'Currencies', 'Safe', 'Sports', 'Predictions'];
  var LEADS = { Stocks: 'Stocks', Crypto: 'Crypto', China: 'China stocks', Metals: 'Metals', Energy: 'Oil and energy', Options: 'Options', Currencies: 'Currencies', Safe: 'Play it safe', Sports: 'Sports', Predictions: 'Prediction markets' };   // the names the standings data uses (ops/build_site.py, _LBL)
  var TABOF = { Stocks: 'stocks', Crypto: 'crypto', China: 'china', Metals: 'metals', Energy: 'energy', Options: 'options', Currencies: 'currencies', Safe: 'safe', Sports: 'sports', Predictions: 'predictions' };
  var SIDE = [['AllInTrading', 'High risk: trading'], ['AllInSports', 'High risk: sports']];
  var useAi = function (id) { var s = document.getElementById('model-pick'); if (s && s.value !== id) { s.value = id; s.dispatchEvent(new Event('change')); } };
  var dropRaces = function () { if (races) races.remove(); races = null; racesSig = ''; unclass('pt-races-on'); };
  var drawRaces = function () {
    if (!ON.races || !PH.matches) { dropRaces(); return; }
    var hdr = $('div.st > header.st-head'), A = ais(); if (!hdr || !A) return;
    var st, ES;
    try { st = dash.baseData('standings'); var all = dash.baseData('exp_standings'); ES = Array.isArray(all) ? all[0] : all; } catch (e) { return; }
    if (!Array.isArray(st) || !ES) return;
    var label = function (k) { try { return LABEL[k] || k; } catch (e) { return k; } };
    var rows = [], led = {};
    KEYS.forEach(function (k) {
      var rs = ES[k]; if (!Array.isArray(rs) || !rs.length) return;
      var who = null; st.forEach(function (s) { if (A[s.id] && (s.leads || []).indexOf(LEADS[k]) >= 0) who = s.id; });
      var r = who ? rs.filter(function (x) { return x.id === who; })[0] : null;
      if (r && typeof r.profit === 'number') { rows.push({ k: k, name: label(k), id: who, v: r.profit, txt: stFmt.signed(r.profit, k), tab: TABOF[k] }); led[who] = (led[who] || 0) + 1; }
      else rows.push({ k: k, name: label(k), id: null, tab: TABOF[k] });
    });
    if (rows.length < 2) { dropRaces(); return; }
    var side = [];
    SIDE.forEach(function (s) { var rs; try { rs = allinRows(s[0]).slice().sort(function (a, b) { return b.profit - a.profit; }); } catch (e) { return; }
      if (!rs.length) return; var lead = rs.length > 1 && rs[0].profit - rs[1].profit >= 0.5 ? rs[0] : null;   // the same lead test as the side-race box
      side.push(lead && A[lead.id] ? { k: s[0], name: s[1], id: lead.id, v: lead.profit, txt: stFmt.signed(lead.profit, 'Stocks') } : { k: s[0], name: s[1], id: null }); });
    var sig = JSON.stringify([rows, side, finale()]);
    if (races && races.isConnected && sig === racesSig) return;
    racesSig = sig;
    var fin = finale();
    var sec = mk('section', 'pt-races'); sec.id = 'pt-races'; sec.setAttribute('aria-labelledby', 'pt-races-h');
    var h = mk('h2', '', rows.length === 10 ? 'The ten races' : 'The races'); h.id = 'pt-races-h'; sec.appendChild(h);
    sec.appendChild(mk('p', 'pt-races-sub', (fin ? 'Who finished first in each race, and its profit or loss.' : 'Who is first in each race right now, and its profit or loss so far.') + ' Tap a race to open it.'));
    var item = function (r) {
      var li = mk('li'), b = mk('button', 'pt-rc' + (r.id ? '' : ' is-level')); b.type = 'button';
      b.appendChild(mk('span', 'pt-rc-n', r.name));
      if (r.id) { b.style.setProperty('--ai', A[r.id].color);
        var w = mk('span', 'pt-rc-w'); try { w.appendChild(aiBadge(r.id, 16)); } catch (e) {} w.appendChild(document.createTextNode(A[r.id].label));
        b.append(w, mk('span', 'pt-rc-p ' + (r.v >= 0 ? 'up' : 'down'), r.txt));
        b.setAttribute('aria-label', r.name + ': ' + A[r.id].label + ' is first with ' + r.txt + '. Opens it as ' + A[r.id].label + '.'); }
      else { b.appendChild(mk('span', 'pt-rc-w pt-rc-lv', 'all level so far')); b.setAttribute('aria-label', r.name + ': all level so far. Opens it.'); }
      var ch = mk('span', 'pt-rc-go', '›'); ch.setAttribute('aria-hidden', 'true'); b.appendChild(ch);
      b.addEventListener('click', function () { if (r.id) useAi(r.id); if (r.tab) go(r.tab); else { try { window.ptGoAllin(r.k); } catch (e) { go('allin'); } } });
      li.appendChild(b); return li;
    };
    var ol = mk('ol', 'pt-rc-l'); rows.forEach(function (r) { ol.appendChild(item(r)); }); sec.appendChild(ol);
    if (side.length) { sec.appendChild(mk('p', 'pt-races-side', 'Side race · its own C$100,000 · never counted in the ten'));
      var ol2 = mk('ol', 'pt-rc-l pt-rc-side'); side.forEach(function (r) { ol2.appendChild(item(r)); }); sec.appendChild(ol2); }
    var tally = st.filter(function (s) { return A[s.id]; }).map(function (s) { return A[s.id].label + ' ' + (led[s.id] || 0); }).join(' · ');
    sec.appendChild(mk('p', 'pt-races-f', '🏁 Races led: ' + tally + '. This never decides the winner: the biggest total profit across the ten does.'));
    if (races) races.remove();
    races = sec; hdr.after(sec); root.classList.add('pt-races-on');   // straight after the top of the page, before the alerts box (ChatGPT's change to the order; Claude agreed)
  };
  try {
    try { dash.onData(function () { try { drawRaces(); } catch (e) {} }); } catch (e) {}
    later(drawRaces, 350); later(drawRaces, 1500); later(drawRaces, 3200);
    onPhone(drawRaces);
    document.addEventListener('change', function (e) { if (e.target && e.target.id === 'cur-pick') later(drawRaces, 120); });   // the viewer's currency choice, as on the Scoreboard
  } catch (e) {}

  /* P3. THE BAR AT THE BOTTOM. Before, the pages were reached from a "Menu" button in the page's fifth block, a round button that only
         showed while scrolling up, or a list of text links about nine screens down. Now five places are always one thumb-tap away:
         Overview (the top), Races (the list above), Ledger, AI vs AI, and Menu, which opens the same sheet of every page as before.
         Nothing is taken out of the Menu or the tab list, and the tab order is unchanged. Portrait phones only. */
  var bar = null, shade = null;
  var ICON = {
    home: '<path d="M3.5 11.2 12 4l8.5 7.2"/><path d="M5.8 9.8V20h12.4V9.8"/>',
    flag: '<path d="M5.5 21V3.5"/><path d="M5.5 4.5h12.2l-2.6 4 2.6 4H5.5"/>',
    list: '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><path d="M4.2 6.5h.6M4.2 12h.6M4.2 17.5h.6" stroke-width="2.6"/>',
    vs: '<path d="M4 8.5h14l-3.2-3.2"/><path d="M20 15.5H6l3.2 3.2"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>'
  };
  var RACE_TABS = { stocks: 1, crypto: 1, china: 1, metals: 1, energy: 1, options: 1, currencies: 1, safe: 1, sports: 1, predictions: 1, allin: 1 };
  var onList = function () { if (!races || !races.isConnected) return false; var r = races.getBoundingClientRect(); return r.top < window.innerHeight * 0.45 && r.bottom > window.innerHeight * 0.45; };   // the list of races fills the middle of the screen
  var where = function () { var t = root.getAttribute('data-tab') || 'overview'; return t === 'overview' ? (onList() ? 'races' : 'home') : RACE_TABS[t] ? 'races' : t === 'ledger' || t === 'allinledger' ? 'ledger' : t === 'h2h' ? 'h2h' : 'menu'; };   // the High risk ledger is a ledger: it lights Ledger (ChatGPT)
  var menuOpen = function () { var m = document.getElementById('m-menu'); return !!(m && !m.hidden); };
  var toggleMenu = function () { press('.m-menu-fab') || press('.m-menu-btn'); };
  var closeMenu = function () { if (menuOpen()) toggleMenu(); };
  var marked = '';
  var mark = function () {
    if (!bar) return; var open = menuOpen(), w = open ? 'menu' : where();
    if (w + open === marked) return;   // nothing changed since the last look (this runs on every scroll frame): write nothing
    marked = w + open;
    $$('button', bar).forEach(function (b) { var on = b.dataset.k === w; if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
    if (shade) shade.hidden = !open;
    root.classList.toggle('pt-menu-open', open);
  };
  var toRaces = function () {
    var land = function () { var t = $('#pt-races') || $('.st-podium'); if (t) window.scrollTo({ top: Math.max(0, t.getBoundingClientRect().top + window.scrollY - 40), behavior: 'auto' }); };
    if (where() !== 'home') { try { goTab('overview', false); } catch (e) { press('.st-tab[data-tab="overview"]'); } later(function () { drawRaces(); land(); }, 60); later(land, 400); } else land();
  };
  var dropBar = function () { if (bar) bar.remove(); if (shade) shade.remove(); bar = shade = null; marked = ''; unclass('pt-bar', 'pt-menu-open', 'pt-going-up'); };
  var drawBar = function () {
    if (!ON.bar || !PH.matches) { dropBar(); return; }
    if (bar && bar.isConnected) { mark(); return; }
    bar = mk('nav', 'pt-bar-nav'); bar.setAttribute('aria-label', 'Shortcuts');   // the footer's list of links is already called "Main pages"
    [['home', 'Overview', ICON.home, function () { closeMenu(); try { window.ptHome(); } catch (e) { go('overview'); window.scrollTo(0, 0); } }],
     ['races', 'Races', ICON.flag, function () { closeMenu(); toRaces(); }],
     ['ledger', 'Ledger', ICON.list, function () { closeMenu(); go('ledger'); }],
     ['h2h', 'AI vs AI', ICON.vs, function () { closeMenu(); go('h2h'); }],
     ['menu', 'Menu', ICON.menu, function () { toggleMenu(); }]].forEach(function (it) {
      var b = mk('button'); b.type = 'button'; b.dataset.k = it[0];
      b.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + it[2] + '</svg>';
      b.appendChild(mk('span', '', it[1]));
      if (it[0] === 'menu') { b.setAttribute('aria-controls', 'm-menu'); b.setAttribute('aria-haspopup', 'dialog'); }
      b.addEventListener('click', function () { try { it[3](); } catch (e) {} later(mark, 30); later(mark, 250); });
      bar.appendChild(b);
    });
    shade = mk('div', 'pt-bar-shade'); shade.hidden = true; shade.addEventListener('click', function () { closeMenu(); later(mark, 30); });
    document.body.append(shade, bar);
    root.classList.add('pt-bar'); marked = ''; mark();
  };
  try {
    drawBar();   // at once, before the page's first paint and before the site scrolls a linked page into place: the header's own Menu button
                 // must already be gone by then, or everything below it would shift up afterwards
    later(drawBar, 200); later(drawBar, 1500);
    onPhone(drawBar);
    window.addEventListener('pt-tab', function () { later(mark, 20); });
    var ticking = false, lastY = window.scrollY;
    window.addEventListener('scroll', function () {
      var y = window.scrollY, d = y - lastY; lastY = y;
      if (bar && (d > 6 || d < -6)) root.classList.toggle('pt-going-up', d < 0);   // the "Top" button shows while you scroll back up, not on top of what you are reading on the way down (ChatGPT)
      if (ticking || !bar) return; ticking = true; requestAnimationFrame(function () { ticking = false; try { mark(); } catch (e) {} });
    }, { passive: true });
    window.addEventListener('hashchange', function () { later(mark, 60); });
    if (window.MutationObserver) {
      new MutationObserver(function () { later(mark, 10); }).observe(root, { attributes: true, attributeFilter: ['data-tab'] });
      var hookMenu = function () { var m = document.getElementById('m-menu'); if (m && !m._ptBar) { m._ptBar = 1; new MutationObserver(function () { later(mark, 0); }).observe(m, { attributes: true, attributeFilter: ['hidden'] }); } };
      hookMenu(); later(hookMenu, 1500);
    }
  } catch (e) {}

  /* P5. A link straight to a page (papertrades.ai/#ledger) lands on that page's first line. The site scrolls there as it loads, but the
         top of the site then grows by a few lines once the data arrives (the one-line summary wraps, the "How to read this" line comes
         in), which pushed the page's start down the screen again, by up to 85 px on an iPhone. For the first three seconds, and only
         until the visitor touches the screen, the page is put back on its first line. Plain links to a tab only: a link to one trade,
         to a Guide section or to a search is left alone. */
  try {
    var tab0 = root.getAttribute('data-tab');
    if (PH.matches && tab0 && tab0 !== 'overview' && location.hash === '#' + tab0 && !location.search) {
      var touched = false;
      ['touchstart', 'wheel', 'keydown', 'mousedown'].forEach(function (ev) { window.addEventListener(ev, function () { touched = true; }, { once: true, passive: true, capture: true }); });
      var reland = function () {
        if (touched || !PH.matches || root.getAttribute('data-tab') !== tab0) return;
        var pg = $('.st-page:not([hidden])'); if (!pg) return;
        var off = pg.getBoundingClientRect().top - 44;   // 44: clear of the price ticker that stays at the top, the same figure the site uses
        if (Math.abs(off) > 3 && window.scrollY + off > 0) window.scrollBy(0, off);
      };
      [500, 900, 1400, 2200, 3000].forEach(function (ms) { later(reland, ms); });
    }
  } catch (e) {}

  /* P4. Over the three AI faces on the Overview: on phones the big question now sits at the very top of the page (P1), so the line over
         the faces says what the faces do. (The site already swaps to these same words while its welcome card is open.) */
  try {
    var pickLine = function () {
      var rowq = $('.st-hook-row'), q = rowq && $('.st-hook-q', rowq), old = $('.pt-pick-h');
      if (!ON.front || !PH.matches || !q) { if (old) old.remove(); return; }
      if (!old) { old = mk('p', 'pt-pick-h', 'Pick an AI to see its view'); q.after(old); }
    };
    pickLine(); later(pickLine, 400); later(pickLine, 2000); onPhone(pickLine);
  } catch (e) {}
})();
