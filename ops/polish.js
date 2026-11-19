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
      ['Using the heavy favorite Colorado Buffaloes', 'the recorded line for this bet was Colorado +300, the underdog, not the favourite (Houston was the favourite). Gemini\u2019s words are shown as written.']
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
})();