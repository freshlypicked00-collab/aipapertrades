/* The polish pass (owner, Nov 18; Claude and Gemini: ops/review/POLISH_DECISIONS_NOV18.md). Small behaviours only, each in its own
   try block so one failing can never stop the page. Nothing here reads or changes a race number: it only re-presents what is on the page. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var mk = function (tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  var later = function (fn, ms) { return setTimeout(function () { try { fn(); } catch (e) {} }, ms); };
  var tab = function (name) { var t = $('.st-tab[data-tab="' + name + '"]'); if (t) t.click(); };

  /* 1. Footer: one row of links to the main pages above the small print (P14). They press the same tabs the menu does. */
  try {
    var foot = $('footer.st-foot');
    if (foot && !$('.pt-foot-nav')) {
      var nav = mk('nav', 'pt-foot-nav'); nav.setAttribute('aria-label', 'Main pages');
      [['overview', 'Overview'], ['ledger', 'Ledger'], ['h2h', 'AI vs AI'], ['news', 'News'], ['rules', 'How it works'], ['audit', 'Rules & Audit'], ['guide', 'Guide'], ['about', 'About'], ['support', 'Support']].forEach(function (p) {
        if (!$('.st-tab[data-tab="' + p[0] + '"]')) return;
        var b = mk('button', '', p[1]); b.type = 'button';
        b.addEventListener('click', function () { tab(p[0]); if (p[0] === 'overview') window.scrollTo({ top: 0, behavior: 'auto' }); });
        nav.appendChild(b);
      });
      var off = mk('button', '', 'Official accounts'); off.type = 'button';
      off.addEventListener('click', function () { tab('about'); if (window.ptSpot) window.ptSpot(function () { return document.getElementById('official'); }, { wait: 350 }); });
      nav.appendChild(off);
      foot.insertBefore(nav, foot.firstChild);   // inside the footer, above the small print
    }
  } catch (e) {}

  /* 2. The welcome card (first visit, computers and tablets): the three overall totals on the right, read from the leader pill the
        site already fills, so the numbers can never differ from it (Gemini's idea 3 in its smallest form). */
  try {
    var COLORS = { Claude: '#d97757', Gemini: '#4f8ff7', ChatGPT: 'var(--ai-chatgpt, #f2f2f2)' };
    var ID = { Claude: 'claude', Gemini: 'gemini', ChatGPT: 'chatgpt' };
    var readPill = function () {
      var chip = $('.st-crown-chip:not(.st-allin-chip)'); if (!chip) return null;
      var n1 = $(':scope > .cr-n', chip), p1 = $(':scope > .cr-p', chip); if (!n1 || !p1) return null;
      var rows = [{ name: n1.textContent.trim(), amt: p1.textContent.trim(), up: p1.classList.contains('up') }];
      $$(':scope > .cr-g:not(.cr-races)', chip).forEach(function (g) { var n = $('.cr-n2', g), p = $('.cr-p', g); if (n && p) rows.push({ name: n.textContent.trim(), amt: p.textContent.trim(), up: p.classList.contains('up') }); });
      return rows.length === 3 ? rows : null;
    };
    var face = function (name) {
      var bots = $$('.st-bots .st-bot'); var id = ID[name];
      for (var i = 0; i < bots.length; i++) { var b = bots[i]; if ((b.dataset && (b.dataset.model === id || b.dataset.ai === id)) || new RegExp('^\\s*' + name, 'i').test(b.textContent)) { var r = $('.ai-robot', b); if (r) return r.cloneNode(true); } }
      return mk('span', '');
    };
    var pod = function () {
      var hero = $('.pt-welcome.pt-hero'); if (!hero || hero.hidden) return;
      var rows = readPill(); if (!rows) return;
      var sig = rows.map(function (r) { return r.name + r.amt; }).join('|');
      var old = $('.pt-hero-pod', hero); if (old && old.dataset.sig === sig) return; if (old) old.remove();
      var box = mk('div', 'pt-hero-pod'); box.dataset.sig = sig;
      box.appendChild(mk('p', 'pt-hero-pod-h', 'Overall right now · pretend money'));
      rows.forEach(function (r, i) {
        var row = mk('div', 'pt-hero-pod-r' + (i === 0 ? ' is-1' : ''));
        var nm = mk('span', 'pt-hero-pod-n', r.name); nm.style.color = COLORS[r.name] || '';
        row.append(mk('span', 'pt-hero-pod-k', i === 0 ? '👑 1st' : i === 1 ? '2nd' : '3rd'), face(r.name), nm, mk('span', 'pt-hero-pod-p ' + (r.up ? 'up' : 'down'), r.amt));
        box.appendChild(row);
      });
      box.appendChild(mk('p', 'pt-hero-pod-f', 'Profit across the ten races. The High risk side race is scored on its own.'));
      hero.appendChild(box); hero.classList.add('has-pod');
    };
    // the card redraws itself at every data refresh: put the block back at once (an observer), and look for the card for the first minute
    var watched = null;
    var watch = function () { var hero = $('.pt-welcome.pt-hero'); if (!hero) return; try { pod(); } catch (e) {}
      if (watched === hero || !window.MutationObserver) return; watched = hero;
      new MutationObserver(function () { try { pod(); } catch (e) {} }).observe(hero, { childList: true }); };
    var tries = 0; var iv = setInterval(function () { watch(); if (++tries > 40) clearInterval(iv); }, 1500);
    later(watch, 800);
  } catch (e) {}

  /* 3. Night pass (Nov 19), S2: a site-only fact check beside a bet's reason when the reason contradicts the recorded numbers. The AI's
        words stay exactly as written; the note is added after them wherever that reason is shown. One entry per reason: the exact
        opening words to look for, and the note. (Claude scanned all 237 sports bets on Nov 19: these two are the only ones.)
     4. S7: the day menu of the "what moved" bars gets a name for screen readers. */
  try {
    var NOTES = [
      ['Backing the massive favorite Colorado Buffaloes (-380)', 'the recorded line for this bet was Colorado +300, the underdog, not a \u2212380 favourite (Houston was the favourite). Gemini\u2019s words are shown as written.'],
      ['Using the heavy favorite Colorado Buffaloes', 'the recorded line for this bet was Colorado +300, the underdog, not the favourite (Houston was the favourite). Gemini\u2019s words are shown as written.'],
      // Improvement pass (Nov 19): the same scan run over every trade and prediction-market buy and sale (373 by Gemini and ChatGPT, 53 by
      // Claude; ops/reason_scan.py). Gemini's and ChatGPT's reasons never contradict their own recorded numbers; two of Claude's quote a price
      // that is not the price the order was filled at.
      ['Polymarket priced Paxton at about 31 cents', 'the recorded fill for this buy was 25.5 cents a share, not about 31. Claude\u2019s words are shown as written.'],
      ['Talarico leads Paxton in the count', 'the recorded fill for this sale was about half a cent a share (0.55 cents), not near 2 cents. Claude\u2019s words are shown as written.']
    ];
    var label = function () { $$('[data-draw="contrib-bars"] select:not([aria-label])').forEach(function (s) { s.setAttribute('aria-label', 'Choose a day'); }); };
    var noteIn = function (root) {   // rows that are in the page but folded away or on another page of a list are noted too, so the note is there when they show
      var hits = [], check = function (n) {
        var v = n.nodeValue, pe = n.parentNode;
        if (!v || v.length < 40 || !pe || pe.nodeName === 'SCRIPT' || pe.nodeName === 'STYLE' || (pe.classList && pe.classList.contains('pt-fcnote'))) return;
        for (var i = 0; i < NOTES.length; i++) { if (v.indexOf(NOTES[i][0]) !== -1) { hits.push([n, NOTES[i][1]]); return; } }
      };
      if (root.nodeType === 3) check(root);
      else if (root.nodeType === 1) { var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); for (var n = tw.nextNode(); n; n = tw.nextNode()) check(n); }
      hits.forEach(function (h) {
        var n = h[0], nx = n.nextSibling;
        if (!n.parentNode || (nx && nx.nodeType === 1 && nx.classList.contains('pt-fcnote'))) return;   // gone, or already noted
        var note = mk('span', 'pt-fcnote'); note.appendChild(mk('b', '', 'Fact check (site note): ')); note.appendChild(document.createTextNode(h[1]));
        n.parentNode.insertBefore(note, nx);
      });
    };
    var queue = [], due = null;
    var run = function () { due = null; var q = queue; queue = []; try { label(); } catch (e) {}
      q.forEach(function (x) { try { if (x.isConnected) noteIn(x); } catch (e) {} }); };
    if (window.MutationObserver) {
      new MutationObserver(function (ms) {
        for (var i = 0; i < ms.length; i++) { var a = ms[i].addedNodes; for (var j = 0; j < a.length; j++) { var x = a[j];
          if (x.nodeType === 1 ? !x.classList.contains('pt-fcnote') && (x.childElementCount > 0 || (x.textContent || '').length >= 40) : x.nodeType === 3 && (x.nodeValue || '').length >= 40) queue.push(x); } }
        if (queue.length && !due) due = setTimeout(run, 400);
      }).observe(document.body, { childList: true, subtree: true });
    }
    later(function () { label(); noteIn(document.body); }, 1500);
  } catch (e) {}

  /* 5. Night pass (Nov 19), B5: on Rules & Audit the three newest corrections stay open; each older one folds to its title and two lines
        (polish.css 29) and opens on a tap or Enter; one button opens them all. A correction another part of the page jumps to is opened. */
  try {
    var KEEP = 3;
    var fold = function () {
      var ul = document.getElementById('au-corr-list'); if (!ul || ul.dataset.ptFold) return;
      var lis = $$(':scope > li', ul); if (lis.length <= KEEP + 1) return;
      ul.dataset.ptFold = '1';
      lis.slice(KEEP).forEach(function (li) { li.classList.add('pt-fold'); li.tabIndex = 0; li.setAttribute('role', 'button'); li.setAttribute('aria-expanded', 'false'); li.title = 'Show the whole entry'; });
      var open = function (li) { li.classList.remove('pt-fold'); li.removeAttribute('role'); li.removeAttribute('title'); li.removeAttribute('tabindex'); li.removeAttribute('aria-expanded'); };
      ul.addEventListener('click', function (e) { var li = e.target.closest && e.target.closest('li.pt-fold'); if (li) open(li); });
      ul.addEventListener('keydown', function (e) { if (e.key !== 'Enter' && e.key !== ' ') return; var li = e.target.closest && e.target.closest('li.pt-fold'); if (li) { e.preventDefault(); open(li); } });
      var all = mk('button', 'pt-fold-all', 'Show all ' + lis.length + ' corrections in full'); all.type = 'button';
      all.addEventListener('click', function () { $$('li.pt-fold', ul).forEach(open); all.remove(); });
      ul.parentNode.insertBefore(all, ul.nextSibling);
      // the status panel can jump to one correction and light it up: open that one
      if (window.MutationObserver) new MutationObserver(function (ms) { ms.forEach(function (m) { var li = m.target; if (li.classList && li.classList.contains('pt-fold') && (li.className !== 'pt-fold' || li.style.cssText)) open(li); }); })
        .observe(ul, { attributes: true, attributeFilter: ['class', 'style'], subtree: true });
    };
    var fv = setInterval(function () { try { fold(); } catch (e) {} }, 1200);
    later(function () { clearInterval(fv); if (window.MutationObserver) { var pg = document.getElementById('audit') || document.body;
      new MutationObserver(function () { try { fold(); } catch (e) {} }).observe(pg, { childList: true, subtree: true }); } }, 60000);
  } catch (e) {}
  /* 6. Improvement pass (Nov 19), phones only (700 px and under): the longest pages fold more. NOTHING is removed: every folded part
        has a button that shows it, a part another place on the page jumps to opens by itself, and computers are untouched (polish.css 31).
        Before, at 375 px: Ledger 17,800 px, Rules & Audit 14,200, Prediction markets 13,900, How it works 13,800, News 13,100.
          a) long lists show their first few rows with "Show all N";   b) older News stories fold to headline, date and first paragraph;
          c) the peer grades under a holding fold to one line that still shows the grades;   d) the rule groups after the first start closed. */
  try {
    var PH = window.matchMedia('(max-width: 700px)');
    var LISTS = [   // [selector, rows that stay, what the rows are, elements per row]
      ['.lg-review-box > ul', 3, 'grades', 1], ['.lg-sims', 4, 'races', 1], ['ul.st-how', 3, 'points', 1], ['ul.st-exp-list', 4, 'lines', 1],
      ['.st-about > ul:not(.st-how):not(.st-exp-list)', 3, 'points', 1], ['dl.pt-gl-list', 5, 'words', 2],
      ['.rules-doc > ul', 3, 'rules', 1], ['ul.st-geo-up', 3, 'updates', 1], ['#fingerprints tbody', 5, 'days', 1]];
    var busy = false;
    var btnFor = function (box, after) {
      var b = box._ptBtn;
      if (!b || !b.isConnected) {
        b = mk('button', 'pt-c-btn'); b.type = 'button';
        b.addEventListener('click', function () { box.dataset.ptOpen = box.dataset.ptOpen === '1' ? '0' : '1'; sweep();
          if (box.dataset.ptOpen !== '1') { var r = box.getBoundingClientRect(); if (r.top < 0) window.scrollBy(0, r.top - 90); } });
        box._ptBtn = b;
      }
      var at = box.tagName === 'TBODY' ? box.parentNode : box;   // rows of a table: the button goes under the table, not inside it
      if (after) { if (at.nextSibling !== b) at.parentNode.insertBefore(b, at.nextSibling); } else if (box.lastElementChild !== b) box.appendChild(b);
      return b;
    };
    var say = function (b, open, shut, more) { var t = open ? 'Show less ▴' : more + ' ▾'; if (b.textContent !== t) b.textContent = t; b.setAttribute('aria-expanded', String(open)); };
    var clamp = function (box, keep, noun, unit) {
      var kids = $$(':scope > *', box).filter(function (c) { return !c.classList.contains('pt-c-btn'); });
      var rows = Math.floor(kids.length / unit);
      if (!PH.matches || rows <= keep + 1) { kids.forEach(function (c) { c.classList.remove('pt-c-hid'); }); if (box._ptBtn) box._ptBtn.remove(); return; }
      var open = box.dataset.ptOpen === '1';
      kids.forEach(function (c, i) { c.classList.toggle('pt-c-hid', !open && i >= keep * unit); });
      say(btnFor(box, true), open, false, 'Show all ' + rows + ' ' + noun);
    };
    var foldBody = function (box, keepSel, more, startOpen) {
      if (!PH.matches) { box.classList.remove('pt-b-fold'); if (box._ptBtn) box._ptBtn.remove(); return; }
      if (box.dataset.ptOpen == null) box.dataset.ptOpen = startOpen ? '1' : '0';
      if (keepSel) $$(keepSel, box).forEach(function (k) { if (k.parentNode === box) k.classList.add('pt-b-keep'); });
      var open = box.dataset.ptOpen === '1';
      var b = btnFor(box, false); b.classList.add('pt-b-keep');
      box.classList.toggle('pt-b-fold', !open);
      say(b, open, false, more);
    };
    // f) a long reason in a trade list shows its first four lines with "more" (the words themselves are untouched and all still in the page;
    //    a reason that carries a fact-check note is never shortened, so the note is always in view)
    var INLINE = { SPAN: 1, B: 1, I: 1, EM: 1, A: 1, FONT: 1, STRONG: 1, SMALL: 1 };
    var clampWhy = function (td) {
      var sp = td.querySelector(':scope > .pt-why'), btn = td.querySelector(':scope > .pt-why-btn');
      if (!PH.matches) { if (sp) sp.classList.remove('pt-why-shut'); if (btn) btn.remove(); return; }
      if (!sp) {
        var run = [], len = 0, n = td.firstChild;
        while (n && (n.nodeType === 3 || (n.nodeType === 1 && INLINE[n.tagName] && !/tx-wrap|pt-why-btn|pt-c-btn|lg-lb|st-pill/.test(n.className || '')))) { run.push(n); len += (n.textContent || '').length; n = n.nextSibling; }
        if (len < 260 || !run.length || run[0].nodeType !== 3) return;
        sp = mk('span', 'pt-why'); td.insertBefore(sp, run[0]); run.forEach(function (x) { sp.appendChild(x); });
      }
      var open = td.dataset.ptWhy === '1' || !!sp.querySelector('.pt-fcnote');
      sp.classList.toggle('pt-why-shut', !open);
      if (!open && sp.scrollHeight - sp.clientHeight < 50) { sp.classList.remove('pt-why-shut'); if (btn) btn.remove(); return; }   // folding would save under two lines: leave it whole
      if (sp.querySelector('.pt-fcnote')) { if (btn) btn.remove(); return; }
      if (!btn) { btn = mk('button', 'pt-why-btn'); btn.type = 'button';
        btn.addEventListener('click', function (e) { e.stopPropagation(); td.dataset.ptWhy = td.dataset.ptWhy === '1' ? '0' : '1'; clampWhy(td); });
        sp.parentNode.insertBefore(btn, sp.nextSibling); }
      var t = open ? 'less ▴' : 'more ▾'; if (btn.textContent !== t) btn.textContent = t; btn.setAttribute('aria-expanded', String(open));
    };
    // h) each card of the Ledger's trade list shows when, race, action, what and the profit; one button shows the details, the money
    //    figures and the reason. A row that carries a fact-check note, or that a link jumps to, starts open.
    var PH6 = window.matchMedia('(max-width: 600px)');
    var ledgerRows = function () {
      $$('#lg-trades table.st-table.pt-cards > tbody > tr').forEach(function (tr) {
        var tds = tr.children, btn = tr.querySelector('.pt-row-btn');
        if (tds.length !== 10) return;
        if (!PH6.matches) { tr.classList.remove('pt-row-shut'); if (btn) btn.remove(); return; }   // cards are drawn at 600 px and under
        var open = tr.dataset.ptOpen === '1' || !!tr.querySelector('.pt-fcnote');
        tr.classList.toggle('pt-row-shut', !open);
        if (!btn) { btn = mk('button', 'pt-c-btn pt-row-btn'); btn.type = 'button';
          btn.addEventListener('click', function (e) { e.stopPropagation(); tr.dataset.ptOpen = tr.dataset.ptOpen === '1' ? '0' : '1'; ledgerRows(); });
          tds[7].appendChild(btn); }
        var t = open ? 'Show less ▴' : 'Details and reason ▾'; if (btn.textContent !== t) btn.textContent = t; btn.setAttribute('aria-expanded', String(open));
      });
    };
    var LEDGER_CARDS = true;   // h) the Ledger's "Every trade and bet" list as cards on phones (it was a 1,442 px wide table in a 336 px box)
    var ruleSet = {};   // rule groups the visitor opened or closed by hand keep that state; the others: the first open, the rest closed
    document.addEventListener('click', function (e) { var sm = e.target.closest && e.target.closest('.au-rules > details > summary'); if (!sm) return;
      ruleSet[sm.textContent.trim().slice(0, 40)] = !sm.parentNode.open; }, true);
    var sweep = function () {
      if (busy) return; busy = true;
      try {
        LISTS.forEach(function (L) { $$(L[0]).forEach(function (box) { clamp(box, L[1], L[2], L[3]); }); });
        $$('.nm-page .nm-card').forEach(function (a, i) { foldBody(a, '.nm-h, .nm-meta, .nm-lede', 'Read the story', i < 2); });
        $$('.pg').forEach(function (g) { var rows = $$(':scope > .pg-row', g); if (!rows.length) return;
          var marks = rows.map(function (r) { var f = r.firstElementChild; var t = f ? f.textContent.trim() : ''; return t.length <= 2 ? t : ''; }).filter(Boolean);
          foldBody(g, null, (rows.length === 1 ? 'Peer grade' : 'Peer grades') + (marks.length === rows.length ? ': ' + marks.join(' · ') : ' (' + rows.length + ')'), false); });
        if (LEDGER_CARDS && typeof ptLabelTable === 'function') $$('#lg-trades table.st-table').forEach(function (t) { if (!t.classList.contains('pt-cards') || t.querySelector(':scope > tbody > tr > td:not([data-label])')) ptLabelTable(t); }); if (LEDGER_CARDS) ledgerRows();   // h) see polish.css 38
        $$('#predictions > section.st-card').forEach(function (c) { var h = c.querySelector(':scope > h2'); if (h && /^Betting minimums/.test(h.textContent.trim())) foldBody(c, ':scope > h2', 'Show more', false); });   // g) as the Sports page already does
        $$('.lg-lb').forEach(function (g) { if (g.querySelector(':scope > .lg-lb-h')) foldBody(g, '.lg-lb-h', 'Read the look-back', false); });   // e) full pass, Nov 20
        $$('td.lg-why, td.gx-why, table.pt-cards td.wrap').forEach(clampWhy);                                                              // f)
        if (PH.matches) $$('.au-rules').forEach(function (box) { $$(':scope > details', box).forEach(function (d, i) {
          var key = (d.querySelector('summary') || d).textContent.trim().slice(0, 40), want = key in ruleSet ? ruleSet[key] : i === 0;
          if (d.open !== want) d.open = want; }); });
      } catch (e) {}
      busy = false;
    };
    // a part that something jumps to (a direct link, "Find this bet in the ledger", a status line) opens first
    var reveal = function (el) {
      if (!el || !el.closest) return;
      var changed = false, n = el;
      while (n && n !== document.body) {
        if (n.classList && n.classList.contains('pt-c-hid') && n.parentNode && n.parentNode.dataset.ptOpen !== '1') { n.parentNode.dataset.ptOpen = '1'; changed = true; }
        if (n.classList && n.classList.contains('pt-b-fold')) { n.dataset.ptOpen = '1'; changed = true; }
        if (n.classList && n.classList.contains('pt-why-shut') && n.parentNode) { n.parentNode.dataset.ptWhy = '1'; changed = true; }
        if (n.classList && n.classList.contains('pt-row-shut')) { n.dataset.ptOpen = '1'; changed = true; }
        if (n.tagName === 'DETAILS' && !n.open && n.parentNode && n.parentNode.classList.contains('au-rules')) { ruleSet[(n.querySelector('summary') || n).textContent.trim().slice(0, 40)] = true; n.open = true; }
        n = n.parentNode;
      }
      if (changed) sweep();
    };
    ['ptUnfold', 'ptSpot'].forEach(function (name) { var orig = window[name]; if (typeof orig !== 'function') return;
      window[name] = function (el) { try { reveal(el); } catch (e) {} return orig.apply(this, arguments); }; });
    var timer = null, kick = function () { if (busy) return; clearTimeout(timer); timer = setTimeout(sweep, 250); };
    later(sweep, 600); later(sweep, 2500);
    if (window.MutationObserver) new MutationObserver(kick).observe(document.getElementById('dash-root') || document.body, { childList: true, subtree: true });
    if (PH.addEventListener) { PH.addEventListener('change', sweep); PH6.addEventListener('change', sweep); }
    window.addEventListener('pt-tab', kick);
  } catch (e) {}
  /* 7. Improvement pass (Nov 19): one line under the leader box that says how to read it (owner: "a one-line 'how to read this page' cue
        by the standings"; ChatGPT's pick in the full-pass review). Words only; no number is read or changed (polish.css 32). */
  try {
    var cue = function () {
      var box = $('.st-crown-line'); if (!box || !box.parentNode || $('.pt-cue')) return;
      var p = mk('p', 'pt-cue');
      p.appendChild(mk('b', '', 'How to read this: '));
      p.appendChild(document.createTextNode('each number is that AI’s profit or loss since Oct 28, in pretend money. '));
      var up = mk('span', 'is-up', 'Green is up'), dn = mk('span', 'is-down', 'red is down');
      p.appendChild(up); p.appendChild(document.createTextNode(', ')); p.appendChild(dn); p.appendChild(document.createTextNode('.'));
      box.parentNode.insertBefore(p, box.nextSibling);
    };
    later(cue, 700); later(cue, 2600); later(cue, 6000);
  } catch (e) {}
  /* 8. Improvement pass (Nov 19): the finish. A dress rehearsal with the clock set past Sat Nov 28, 4:00 p.m. ET showed the top of the
        site still saying "0d 00h 00m 00s left until final scoring" and "Gemini leads overall", as if the race were still on (the old rule
        that hid the countdown hides the wrong line since the slim top was added). From the finish on, and never before it: the countdown
        line becomes "Season 1 is over" (polish.css 34) and "leads" becomes "finished first". Words only; every number is left alone.
        To look at it before the day: add ?finale to the address. */
  try {
    var END = Date.parse('2026-11-28T16:00:00-05:00');
    var over = function () { return Date.now() >= END || /[?&]finale\b/.test(location.search); };
    var SWAPS = [[/\bleads overall\b/g, 'finished first overall'], [/\bleads (trading|sports)\b/g, 'finished first in $1'], [/^Right now: /, 'At the finish: '],
      [/\bleads both ways right now\b/, 'finished first both ways']];   // site-written lines only (the roots below): never a line an AI wrote
    var finale = function () {
      if (!over()) return;
      document.documentElement.classList.add('pt-finale');
      $$('header.st-head, .st-crowns, .pt-wel, .st-bots, #viewing-name, .pt-slimline, .ra-both').forEach(function (root) {
        var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), n, v, w;
        while ((n = tw.nextNode())) { v = n.nodeValue; if (!v || v.indexOf('leads') === -1 && v.indexOf('Right now') === -1) continue;
          w = v; SWAPS.forEach(function (x) { w = w.replace(x[0], x[1]); }); if (w !== v) n.nodeValue = w; }
      });
    };
    later(finale, 900); setInterval(function () { try { finale(); } catch (e) {} }, 4000);
  } catch (e) {}
  /* 9. Full pass (Nov 19 to 20), HELD for the owner's OK: the "Final result" card, the one place to cite and share when Season 1 ends
        (MISSION plan item 3). It is NOT shown to visitors yet: FINAL_LIVE is false, so it appears only when the address ends in ?finale
        (a preview with today's standings, clearly marked). When the owner says yes, set FINAL_LIVE to true: from Sat Nov 28, 4:00 p.m. ET
        the card then sits at the top of the Overview by itself, with its own address (papertrades.ai/#final).
        Every figure is read from the same data as the leader box and the race standings; nothing is worked out differently here.
        "Won" is used only once the final scoring is recorded and no bet is open; until then it says "finished first" (all three AIs agreed). */
  try {
    var FINAL_LIVE = false;
    var F_END = Date.parse('2026-11-28T16:00:00-05:00');
    var fPreview = /[?&]finale?\b/.test(location.search);
    var fOn = function () { return fPreview || (FINAL_LIVE && Date.now() >= F_END); };
    var fmtC = function (v, race) { return (typeof stFmt !== 'undefined' && stFmt.signed) ? stFmt.signed(v, race || 'Stocks') : (v >= 0 ? '+' : '−') + 'C$' + Math.round(Math.abs(v)).toLocaleString('en-US'); };
    var whenET = function (t) { try { return new Date(t).toLocaleString('en-US', { timeZone: 'America/New_York', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).replace('AM', 'a.m.').replace('PM', 'p.m.') + ' ET'; } catch (e) { return ''; } };
    var nameOf = function (id) { var a = (typeof AIS !== 'undefined' && AIS[id]) || {}; var b = mk('b', 'pt-fin-n', a.label || id); if (a.color) b.style.color = a.color; return b; };
    var finalCard = function () {
      var pg = $('header.st-head'); if (!pg || !pg.parentNode || typeof dash === 'undefined') return;   // right under the header, above everything else on the Overview
      var old = document.getElementById('final');
      if (!fOn()) { if (old) old.remove(); return; }
      var st = dash.baseData('standings'), es = dash.baseData('exp_standings'); var ES = Array.isArray(es) ? es[0] : es;
      if (!Array.isArray(st) || !st.length || !ES) return;
      var rows = st.filter(function (r) { return typeof r.profit === 'number'; }).slice().sort(function (a, b) { return b.profit - a.profit; });
      if (rows.length < 2) return;
      // what is still moving: the final scoring (recorded in the value history) and bets on games not finished yet
      var hist = dash.baseData('rivals_history') || [], finals = hist.filter(function (h) { return h && h.final; });
      var scoredAt = finals.length ? finals.map(function (h) { return Date.parse(h.at); }).sort()[0] : null;
      var open = 0, lastSettled = 0;
      var seeBet = function (b) { if (!b) return; if (b.status === 'Open') open++; var t = Date.parse(b.settled_at || ''); if (t && t > lastSettled) lastSettled = t; };
      (dash.baseData('bets') || []).forEach(seeBet);
      (dash.baseData('rivals_models') || []).forEach(function (m) { var bk = m.books || {}; Object.keys(bk).forEach(function (e) { ((bk[e] || {}).bets || []).forEach(seeBet); }); });
      var ended = Date.now() >= F_END, settled = ended && scoredAt && open === 0;
      var sig = JSON.stringify([rows.map(function (r) { return [r.id, Math.round(r.profit)]; }), Object.keys(ES).map(function (e) { return (ES[e] || []).map(function (r) { return Math.round(r.profit); }); }), ended, scoredAt, open, lastSettled]);
      if (old && old._sig === sig) return;
      var card = mk('section', 'st-card pt-final'); card.id = 'final'; card._sig = sig; card.setAttribute('aria-labelledby', 'h-final');
      var h = mk('h2', 'st-h2', (ended ? '🏁 Final result' : '🏁 Final result (preview)') + ' · Season 1'); h.id = 'h-final'; card.appendChild(h);
      card.appendChild(mk('p', 'pt-fin-sub', 'Claude vs Gemini vs ChatGPT · Oct 28 to Nov 28, 2026 · pretend money, real prices'));
      var status = !ended ? 'Preview only: these are today’s standings, not the final result. This card appears by itself at the finish, Sat Nov 28, 4:00 p.m. ET.'
        : !scoredAt ? 'The race ended at 4:00 p.m. ET. Final scoring is being done now; the figures below are from the last check-in.'
        : open ? 'Final scoring done ' + whenET(scoredAt) + '. ' + open + (open === 1 ? ' Sports bet is' : ' Sports bets are') + ' still open, so the Sports totals can still change. Until then this is the order at the finish.'
        : 'Final. Scoring done ' + whenET(scoredAt) + (lastSettled > F_END ? '; the last open bet settled ' + whenET(lastSettled) : '') + '. Includes every penalty, refund, voided bet and settled bet. Nothing changes after this.';
      card.appendChild(mk('p', 'pt-fin-status' + (settled ? ' is-final' : ''), status));
      var lead = mk('p', 'pt-fin-lead'); lead.appendChild(document.createTextNode(settled ? '🏆 ' : '👑 ')); lead.appendChild(nameOf(rows[0].id));
      lead.appendChild(document.createTextNode((settled ? ' won Season 1' : ended ? ' finished first' : ' leads') + ' with the most total profit: '));
      var top = mk('b', 'pt-fin-amt ' + (rows[0].profit >= 0 ? 'is-up' : 'is-down'), fmtC(rows[0].profit)); lead.appendChild(top); lead.appendChild(mk('span', 'pt-fin-tag', ' pretend money')); card.appendChild(lead);
      var ol = mk('ol', 'pt-fin-order');
      rows.forEach(function (r, i) { var li = mk('li'); li.appendChild(mk('span', 'pt-fin-medal', ['🥇', '🥈', '🥉'][i] || String(i + 1)));
        li.appendChild(nameOf(r.id)); li.appendChild(mk('span', 'pt-fin-amt ' + (r.profit >= 0 ? 'is-up' : 'is-down'), fmtC(r.profit)));
        var n = (r.leads || []).length; li.appendChild(mk('span', 'pt-fin-won', 'first in ' + n + ' of ' + Object.keys(ES).length + ' races')); ol.appendChild(li); });
      card.appendChild(ol);
      card.appendChild(mk('p', 'pt-fin-note', 'Total profit or loss across the ten races. Each AI started every race with C$100,000 of pretend money (China stocks: US$100,000, converted to C$ for the total). The most total profit wins.'));
      card.appendChild(mk('h3', 'st-h3', settled ? 'The ten races: who finished first' : 'The ten races: who is first'));
      var grid = mk('div', 'pt-fin-races');
      Object.keys(ES).forEach(function (e) { var rr = (ES[e] || []).slice().sort(function (a, b) { return b.profit - a.profit; }); if (!rr.length) return;
        var row = mk('div', 'pt-fin-race'); row.appendChild(mk('span', 'pt-fin-rl', (typeof LABEL !== 'undefined' && LABEL[e]) || e));
        var tie = rr.length > 1 && rr[0].profit - rr[1].profit < 0.5;
        if (tie) row.appendChild(mk('span', 'pt-fin-n', 'tie')); else row.appendChild(nameOf(rr[0].id));
        row.appendChild(mk('span', 'pt-fin-amt ' + (rr[0].profit >= 0 ? 'is-up' : 'is-down'), fmtC(rr[0].profit, e))); grid.appendChild(row); });
      card.appendChild(grid);
      try { var side = [['AllInTrading', 'trading'], ['AllInSports', 'sports']].map(function (x) { var rr = allinRows(x[0]).slice().sort(function (a, b) { return b.profit - a.profit; }); return rr.length ? [x[1], rr[0]] : null; }).filter(Boolean);
        if (side.length) { var sp = mk('p', 'pt-fin-note pt-fin-side'); sp.appendChild(mk('b', '', 'High risk side race (never counted in the result): '));
          side.forEach(function (x, i) { if (i) sp.appendChild(document.createTextNode(' · ')); sp.appendChild(document.createTextNode(x[0] + ' ')); sp.appendChild(nameOf(x[1].id)); sp.appendChild(document.createTextNode(' ' + fmtC(x[1].profit))); }); card.appendChild(sp); } } catch (e) {}
      var act = mk('div', 'pt-fin-act'), url = 'https://papertrades.ai/#final';
      var words = 'PaperTrades.AI, Season 1 ' + (settled ? 'final result' : ended ? 'at the finish' : 'standings') + ': ' + ((typeof AIS !== 'undefined' && AIS[rows[0].id] || {}).label || rows[0].id) + (settled ? ' won' : ended ? ' finished first' : ' leads') + ' with ' + fmtC(rows[0].profit) + ' of pretend money. Claude vs Gemini vs ChatGPT, ten races, real prices.';
      var sh = mk('button', 'pt-fin-btn is-main', 'Share'); sh.type = 'button';
      sh.addEventListener('click', function () { if (navigator.share) navigator.share({ title: 'PaperTrades.AI: Season 1 final result', text: words, url: url }).catch(function () {}); else if (navigator.clipboard) navigator.clipboard.writeText(words + ' ' + url).then(function () { sh.textContent = 'Copied ✓'; later(function () { sh.textContent = 'Share'; }, 1800); }); });
      var cp = mk('button', 'pt-fin-btn', 'Copy link'); cp.type = 'button';
      cp.addEventListener('click', function () { if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { cp.textContent = 'Copied ✓'; later(function () { cp.textContent = 'Copy link'; }, 1800); }); });
      var a1 = mk('a', 'pt-fin-link', 'Audit pack'); a1.href = 'data/papertrades-audit-pack.zip'; a1.title = 'Check it yourself: every rule, trade, bet and price check in one file';
      var a2 = mk('button', 'pt-fin-link', 'Rules + fingerprints'); a2.type = 'button'; a2.addEventListener('click', function () { tab('audit'); });
      act.appendChild(sh); act.appendChild(cp); act.appendChild(a1); act.appendChild(a2); card.appendChild(act);
      card.appendChild(mk('p', 'pt-fin-foot', 'Pretend money only. No deposits, no accounts, no token. Not investment or betting advice. One month is short, so luck matters.'));
      if (old) old.replaceWith(card); else { pg.parentNode.insertBefore(card, pg.nextSibling);
        if (location.hash === '#final') later(function () { try { card.scrollIntoView({ block: 'start' }); } catch (e) {} }, 200); }
    };
    if (fPreview || FINAL_LIVE) { later(finalCard, 1200); later(finalCard, 3500); setInterval(function () { try { finalCard(); } catch (e) {} }, 20000);
      if (typeof dash !== 'undefined' && dash.onData) dash.onData(function () { later(finalCard, 300); }); }
  } catch (e) {}
  /* 10. Full pass (Nov 20; Claude, Gemini and ChatGPT all picked this one): "Add to calendar" beside the countdown. One tap saves the
         finish (Sat Nov 28, 4:00 p.m. ET) to the visitor's own calendar, with a reminder 15 minutes before and the link to the result.
         A reason to come back at the one moment that matters; no new number on the site, nothing sent anywhere. Gone after the finish. */
  try {
    var calBtn = function () {
      var sp = $('header.st-head .st-progress [data-draw="countdown"]'); if (!sp || !sp.parentNode || $('.pt-cal') || Date.now() >= Date.parse('2026-11-28T16:00:00-05:00')) return;
      var ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//PaperTrades.AI//Season 1//EN', 'BEGIN:VEVENT', 'UID:season1-final@papertrades.ai', 'DTSTAMP:20261120T000000Z',
        'DTSTART:20261128T210000Z', 'DTEND:20261128T213000Z', 'SUMMARY:PaperTrades.AI: Season 1 final result (Claude vs Gemini vs ChatGPT)',
        'DESCRIPTION:The race ends at 4:00 p.m. ET. See who finished first: https://papertrades.ai/?utm_source=calendar#final\\nPretend money only. Not investment or betting advice.',
        'URL:https://papertrades.ai/?utm_source=calendar#final', 'BEGIN:VALARM', 'TRIGGER:-PT15M', 'ACTION:DISPLAY', 'DESCRIPTION:PaperTrades.AI: the final result in 15 minutes', 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
      var a = mk('a', 'pt-cal', '📅 Add to calendar'); a.href = 'data:text/calendar;charset=utf-8,' + encodeURIComponent(ics); a.download = 'papertrades-ai-season-1-final.ics';
      a.title = 'Save the finish (Sat Nov 28, 4:00 p.m. ET) to your calendar'; a.setAttribute('aria-label', 'Add the finish, Saturday November 28 at 4:00 p.m. Eastern, to your calendar');
      a.addEventListener('click', function () { try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: 'finale/calendar', title: 'Add to calendar', event: true }); } catch (e) {} });
      sp.parentNode.appendChild(document.createTextNode(' ')); sp.parentNode.appendChild(a);
    };
    later(calBtn, 800); later(calBtn, 3000);
  } catch (e) {}
})();