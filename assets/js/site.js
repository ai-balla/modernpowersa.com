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
