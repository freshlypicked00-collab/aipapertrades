/* The polish pass (owner, Nov 18; Claude and Gemini: ops/review/POLISH_DECISIONS_NOV18.md). Small behaviours only, each in its own
   try block so one failing can never stop the page. Nothing here reads or changes a race number: it only re-presents what is on the page. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var mk = function (tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  var later = function (fn, ms) { return setTimeout(function () { try { fn(); } catch (e) {} }, ms); };
  var tab = function (name) { var t = $('.st-tab[data-tab="' + name + '"]'); if (t) t.click(); };

  /* 1. A card that has nothing to show keeps its place with one quiet line (P13, Gemini's version), instead of a bare title. */
  var emptyCards = function () {
    $$('.st-page:not([hidden]) .st-card').forEach(function (card) {
      var h = $('h2[id$="-events"], h2#h-events-all', card); if (!h) return;
      var note = $('.pt-empty-note', card);
      var shown = Array.prototype.some.call(card.children, function (c) { return c !== h && c !== note && c.offsetParent !== null && c.offsetHeight > 0; });
      if (!shown && !note) { card.appendChild(mk('p', 'pt-empty-note', 'Nothing scheduled right now.')); }
      else if (shown && note) note.remove();
    });
  };
  try { later(emptyCards, 1500); later(emptyCards, 5000); window.addEventListener('pt-tab', function () { later(emptyCards, 400); }); setInterval(function () { try { emptyCards(); } catch (e) {} }, 30000); } catch (e) {}

  /* 2. Footer: one row of links to the main pages above the small print (P14). They press the same tabs the menu does. */
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

  /* 3. The welcome card (first visit, computers and tablets): the three overall totals on the right, read from the leader pill the
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
})();
