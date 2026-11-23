/* Kahoa booking calendar client: one shared calendar for the coffee cart and events (2 bookings per date). */
(function () {
  var BASE = 'https://kahoa-checkoutout.chegekibuthu1.workers.dev/cal/';
  var cache = null, loading = null;
  function post(path, body) {
    return fetch(BASE + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().then(function (d) { return { http: r.status, d: d }; }); });
  }
  function today() {
    try { return new Date().toLocaleDateString('en-CA', { timeZone: 'America/Chicago' }); }
    catch (e) { return new Date().toISOString().slice(0, 10); }
  }
  function load(force) {
    if (cache && !force) return Promise.resolve(cache);
    if (loading && !force) return loading;
    loading = post('availability', { from: today(), to: '2099-12-31' }).then(function (r) {
      cache = r.d && r.d.capacity ? r.d : null; loading = null; return cache;
    }).catch(function () { loading = null; return null; });
    return loading;
  }
  function status(date) {
    if (!date) return Promise.resolve('none');
    if (date < today()) return Promise.resolve('past');
    return load().then(function (a) {
      if (!a) return 'unknown';
      if ((a.closed || []).indexOf(date) !== -1) return 'closed';
      var n = (a.counts || {})[date] || 0;
      if (n >= a.capacity) return 'full';
      if (n === a.capacity - 1) return 'last';
      return 'open';
    });
  }
  var MSG = {
    open: ['#2a7a3b', '✓ This date is available.'],
    last: ['#2a7a3b', '✓ Available. One spot left on this date.'],
    full: ['#b3261e', 'This date is fully booked. Please choose another date, or email info@kahoa.shop to join the waitlist.'],
    closed: ['#b3261e', 'We are not taking bookings on this date. Please choose another date.'],
    past: ['#b3261e', 'Please choose a future date.'],
    unknown: ['#7a5a3a', ''], none: ['', '']
  };
  function attach(inputId, opts) {
    var el = document.getElementById(inputId);
    if (!el) return;
    el.min = today();
    var m = document.createElement('div');
    m.className = 'kahoa-cal-msg';
    m.style.cssText = 'font-size:12.5px;font-weight:600;margin:6px 0 0;line-height:1.45;' + ((opts && opts.style) || '');
    el.insertAdjacentElement('afterend', m);
    function upd() {
      var d = el.value;
      status(d).then(function (s) {
        if (el.value !== d) return;
        var x = MSG[s] || MSG.none;
        m.style.color = (opts && opts.okColor && x[0] === '#2a7a3b') ? opts.okColor : x[0];
        m.textContent = x[1];
        el.dataset.calStatus = s;
      });
    }
    el.addEventListener('change', upd); el.addEventListener('input', upd);
    load().then(upd);
  }
  function hold(info) {
    return post('hold', info).then(function (r) {
      if (r.d && r.d.ok) return { ok: true, hold_id: r.d.hold_id };
      if (r.d && r.d.reason) { load(true); return { ok: false, reason: r.d.reason }; }
      return { ok: false, offline: true };
    }).catch(function () { return { ok: false, offline: true }; });
  }
  function confirm(holdId, paymentId) {
    if (!holdId) return Promise.resolve(false);
    return post('confirm', { hold_id: holdId, payment_id: paymentId || '' }).then(function (r) { return !!(r.d && r.d.ok); }).catch(function () { return false; });
  }
  function release(holdId) {
    if (!holdId) return Promise.resolve(false);
    return post('release', { hold_id: holdId }).then(function (r) { return !!(r.d && r.d.ok); }).catch(function () { return false; });
  }
  function reasonText(reason) {
    return reason === 'closed' ? 'Sorry, we are not taking bookings on that date. Please choose another date. Your card was not charged.'
      : reason === 'invalid' ? 'Please choose a future event date. Your card was not charged.'
      : 'Sorry, that date just filled up. Please choose another date. Your card was not charged.';
  }
  window.KahoaCal = { attach: attach, status: status, hold: hold, confirm: confirm, release: release, reasonText: reasonText, load: load, today: today };
})();
