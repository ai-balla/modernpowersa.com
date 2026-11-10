/* MPMS site behaviour. Every page works without this file; it only adds enhancements. */
(function () {
  'use strict';

  /* Remember language choice (used by the root language chooser). */
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[data-lang]');
    if (!a) return;
    try { localStorage.setItem('mpms-lang', a.getAttribute('data-lang')); } catch (e) { /* storage unavailable */ }
  });
  try {
    var pageLang = document.documentElement.lang;
    if (!document.body.classList.contains('chooser') && (pageLang === 'ar' || pageLang === 'en')) {
      localStorage.setItem('mpms-lang', pageLang);
    }
  } catch (e) { /* ignore */ }

  /* Mobile navigation */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    var setOpen = function (open) {
      nav.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    toggle.addEventListener('click', function () { setOpen(!nav.classList.contains('open')); });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && nav.classList.contains('open')) { setOpen(false); toggle.focus(); }
    });
    window.addEventListener('resize', function () { if (window.innerWidth > 1080) setOpen(false); });
  }

  /* Project filter */
  var filterBox = document.querySelector('.filter');
  var table = document.getElementById('project-table');
  if (filterBox && table) {
    filterBox.hidden = false;
    var sel = document.getElementById('svc-filter');
    var count = filterBox.querySelector('[data-count]');
    sel.addEventListener('change', function () {
      var v = sel.value, n = 0;
      table.querySelectorAll('tbody tr').forEach(function (tr) {
        var show = !v || (' ' + tr.getAttribute('data-services') + ' ').indexOf(' ' + v + ' ') > -1;
        tr.hidden = !show;
        if (show) n++;
      });
      count.textContent = n;
    });
  }


  /* ---------- Motion and media (all optional; content works without it) ---------- */
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Overlay header turns solid once the page scrolls past the top of the hero */
  var overlay = document.querySelector('.site-header.is-overlay');
  if (overlay) {
    var onScroll = function () { overlay.classList.toggle('is-solid', window.scrollY > 40); };
    onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* Hero video: respect reduced motion and offer a pause control */
  var hero = document.querySelector('.hero-video');
  var vbtn = document.querySelector('.video-toggle');
  if (hero) {
    var setBtn = function (paused) {
      if (!vbtn) return;
      vbtn.setAttribute('aria-pressed', paused ? 'true' : 'false');
      vbtn.setAttribute('aria-label', vbtn.getAttribute(paused ? 'data-label-play' : 'data-label-pause'));
    };
    if (reduce) { hero.removeAttribute('autoplay'); hero.pause(); setBtn(true); }
    else { var pr = hero.play(); if (pr && pr.catch) pr.catch(function () { setBtn(true); }); }
    if (vbtn) vbtn.addEventListener('click', function () {
      if (hero.paused) { hero.play(); setBtn(false); } else { hero.pause(); setBtn(true); }
    });
  }

  /* Background videos further down play only while visible */
  var lazyVideos = document.querySelectorAll('video.band-video');
  if (lazyVideos.length && 'IntersectionObserver' in window && !reduce) {
    var vio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var v = en.target;
        if (en.isIntersecting) { v.preload = 'auto'; var p = v.play(); if (p && p.catch) p.catch(function () {}); }
        else v.pause();
      });
    }, { threshold: 0.15 });
    lazyVideos.forEach(function (v) { vio.observe(v); });
  }

  /* Figures count up once when the stats band first appears */
  var counters = document.querySelectorAll('.stat-n[data-count]');
  if (counters.length && 'IntersectionObserver' in window && !reduce) {
    var fmt = function (n, plain) { return plain ? String(n) : n.toLocaleString('en-US'); };
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, span = el.querySelector('span') || el, target = parseInt(el.getAttribute('data-count'), 10);
        var plain = el.hasAttribute('data-plain'), start = plain ? Math.max(target - 60, 0) : 0, t0 = null;
        var step = function (ts) {
          if (!t0) t0 = ts;
          var k = Math.min((ts - t0) / 1400, 1), eased = 1 - Math.pow(1 - k, 3);
          span.textContent = fmt(Math.round(start + (target - start) * eased), plain);
          if (k < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
        cio.unobserve(el);
      });
    }, { threshold: 0.6 });
    counters.forEach(function (c) { cio.observe(c); });
  }

  /* Lightbox for work photos */
  var closeLabel = document.documentElement.lang === 'ar' ? 'إغلاق' : 'Close';
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[data-lightbox]');
    if (!a) return;
    ev.preventDefault();
    var opener = a;
    var box = document.createElement('div');
    box.className = 'lightbox'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true');
    var img = document.createElement('img'); img.src = a.getAttribute('href'); img.alt = (a.querySelector('img') || {}).alt || '';
    var btn = document.createElement('button'); btn.type = 'button'; btn.textContent = closeLabel;
    box.appendChild(img); box.appendChild(btn); document.body.appendChild(box);
    document.body.style.overflow = 'hidden'; btn.focus();
    var close = function () { box.remove(); document.body.style.overflow = ''; document.removeEventListener('keydown', key); opener.focus(); };
    var key = function (e) { if (e.key === 'Escape') close(); };
    btn.addEventListener('click', close);
    box.addEventListener('click', function (e) { if (e.target === box) close(); });
    document.addEventListener('keydown', key);
  });

  /* Home page: show the three latest published updates from the blog */
  var upd = document.querySelector('[data-updates]');
  var updTarget = document.querySelector('[data-updates-target]');
  if (upd && updTarget && window.fetch && window.DOMParser) {
    fetch(upd.getAttribute('data-updates'), { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.text() : ''; }).then(function (html) {
      if (!html) return;
      var doc = new DOMParser().parseFromString(html, 'text/html');
      var cards = Array.prototype.slice.call(doc.querySelectorAll('.cms-blog-card'), 0, 3);
      cards.forEach(function (c) {
        var link = c.querySelector('h2 a'); if (!link) return;
        var art = document.createElement('article'); art.className = 'update-card';
        var im = c.querySelector('img');
        if (im) { var i2 = document.createElement('img'); i2.src = im.getAttribute('src'); i2.alt = ''; i2.loading = 'lazy'; art.appendChild(i2); }
        var d = document.createElement('div');
        var sm = c.querySelector('small'); if (sm) { var s2 = document.createElement('small'); s2.textContent = sm.textContent; d.appendChild(s2); }
        var h = document.createElement('h3'); var a2 = document.createElement('a'); a2.href = link.getAttribute('href'); a2.textContent = link.textContent; h.appendChild(a2); d.appendChild(h);
        var p = c.querySelector('p'); if (p) { var p2 = document.createElement('p'); p2.textContent = p.textContent; d.appendChild(p2); }
        art.appendChild(d); updTarget.appendChild(art);
      });
      if (updTarget.children.length) upd.classList.add('has-items');
    }).catch(function () {});
  }

  /* Request form */
  var form = document.getElementById('request-form');
  if (!form) return;
  var M = {};
  try { M = JSON.parse(form.getAttribute('data-messages')); } catch (e) { M = {}; }
  form.setAttribute('novalidate', '');
  form.elements.ts.value = String(Math.floor(Date.now() / 1000));

  var params = new URLSearchParams(location.search);
  var t = params.get('type'), s = params.get('service');
  if (t && form.elements.type.querySelector('option[value="' + CSS.escape(t) + '"]')) form.elements.type.value = t;
  if (s && form.elements.service.querySelector('option[value="' + CSS.escape(s) + '"]')) form.elements.service.value = s;

  var summary = document.querySelector('.err-summary');
  var status = document.querySelector('.form-status');
  var btn = form.querySelector('button[type=submit]');
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  var PHONE = /^\+?[0-9 ()\-]{7,20}$/;

  function setError(name, msg) {
    var el = form.elements[name];
    var box = document.getElementById(name + '-err');
    if (!el || !box) return;
    if (msg) { el.setAttribute('aria-invalid', 'true'); box.textContent = msg; box.hidden = false; }
    else { el.removeAttribute('aria-invalid'); box.textContent = ''; box.hidden = true; }
  }

  function validate() {
    var errs = [];
    function check(name, ok, msg) {
      setError(name, ok ? '' : msg);
      if (!ok) {
        var label = form.querySelector('label[for="' + name + '"]');
        errs.push({ name: name, label: name === 'consent' ? M.f_consent_short : (label ? label.textContent.replace('*', '').trim() : name), msg: msg });
      }
    }
    var v = function (n) { return (form.elements[n].value || '').trim(); };
    check('name', v('name').length > 0, M.err_required);
    check('email', v('email').length > 0 && EMAIL.test(v('email')), v('email') ? M.err_email : M.err_required);
    check('phone', !v('phone') || PHONE.test(v('phone')), M.err_phone);
    var msgLen = v('message').length;
    check('message', msgLen > 0 && msgLen <= 5000, msgLen ? M.err_long : M.err_required);
    check('consent', form.elements.consent.checked, M.err_consent);
    return errs;
  }

  function showSummary(errs) {
    var ul = summary.querySelector('ul');
    ul.innerHTML = '';
    errs.forEach(function (x) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#' + x.name;
      a.textContent = x.label + ': ' + x.msg;
      a.addEventListener('click', function (ev) { ev.preventDefault(); form.elements[x.name].focus(); });
      li.appendChild(a); ul.appendChild(li);
    });
    summary.hidden = false;
    summary.focus();
  }

  function showStatus(ok) {
    status.className = 'form-status' + (ok ? '' : ' is-fail');
    status.innerHTML = '';
    var h = document.createElement('h3'); h.textContent = ok ? M.ok_h : M.fail_h;
    var p = document.createElement('p'); p.textContent = ok ? M.ok_p : M.fail_p;
    status.appendChild(h); status.appendChild(p);
    status.hidden = false;
    status.focus();
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    status.hidden = true;
    var errs = validate();
    if (errs.length) { showSummary(errs); return; }
    summary.hidden = true;
    btn.disabled = true; btn.textContent = M.f_sending;
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'Accept': 'application/json' },
      credentials: 'same-origin'
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false }; }).then(function (data) {
        return r.ok && data && data.ok === true ? data : Promise.reject(data);
      });
    }).then(function () {
      showStatus(true);
      form.reset();
      form.hidden = true;
    }).catch(function (data) {
      if (data && data.errors) {
        var errs2 = Object.keys(data.errors).map(function (k) {
          var msg = M[data.errors[k]] || M.err_required;
          setError(k, msg);
          var label = form.querySelector('label[for="' + k + '"]');
          return { name: k, label: k === 'consent' ? M.f_consent_short : (label ? label.textContent.replace('*', '').trim() : k), msg: msg };
        });
        if (errs2.length) { showSummary(errs2); return; }
      }
      showStatus(false);
    }).then(function () {
      btn.disabled = false; btn.textContent = M.f_submit;
    });
  });
})();
