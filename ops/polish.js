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
    if (PH.addEventListener) PH.addEventListener('change', sweep);
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
})();