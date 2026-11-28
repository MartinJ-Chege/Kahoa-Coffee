/* Kahoa tracking: Meta Pixel + Google Analytics 4, one file for every public page.
   To turn on the Meta Pixel, paste the Pixel (Dataset) ID from Meta Events Manager below.
   Until then, only Google Analytics events are sent. Tracking can never break the page. */
(function () {
  var PIXEL_ID = '';            // e.g. '123456789012345'
  var GA_ID = 'G-MP3BK1KXZ7';
  var CUR = 'USD';
  if (window.__kahoaTrack) return;
  window.__kahoaTrack = true;

  /* ---- Google Analytics (only if the page doesn't already load it) ---- */
  window.dataLayer = window.dataLayer || [];
  if (typeof window.gtag !== 'function') {
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', GA_ID);
    var g = document.createElement('script');
    g.async = true; g.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(g);
  }

  /* ---- Meta Pixel ---- */
  if (PIXEL_ID && !window.fbq) {
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
      t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    window.fbq('init', PIXEL_ID);
    window.fbq('track', 'PageView');
  }

  var GA_NAME = { ViewContent: 'view_item', AddToCart: 'add_to_cart', InitiateCheckout: 'begin_checkout', Purchase: 'purchase', Lead: 'generate_lead', Subscribe: 'purchase' };
  var lastFired = {};
  function track(name, p) {
    try {
      p = p || {};
      var key = name + '|' + (p.content_name || '') + '|' + (p.value || '');
      var now = Date.now();
      if (lastFired[key] && now - lastFired[key] < 3000) return;   // no double counting
      lastFired[key] = now;
      if (window.fbq && PIXEL_ID) window.fbq('track', name, p);
      var ga = { currency: p.currency || CUR };
      if (p.value != null) ga.value = Number(p.value);
      if (p.content_name) ga.items = [{ item_name: p.content_name, item_category: p.content_category || '' }];
      if (p.content_category) ga.lead_type = p.content_category;
      if (p.order_id) ga.transaction_id = p.order_id;
      window.gtag('event', GA_NAME[name] || name, ga);
    } catch (e) { }
  }
  window.kahoaTrack = track;
  function money(n) { n = Number(n); return isFinite(n) ? Math.round(n * 100) / 100 : undefined; }

  /* ---- Purchases and leads: watch the site's own calls to the Kahoa system ---- */
  if (window.fetch) {
    var _fetch = window.fetch;
    window.fetch = function (input, init) {
      var url = '', body = null;
      try {
        url = typeof input === 'string' ? input : (input && input.url) || '';
        if (init && typeof init.body === 'string') body = JSON.parse(init.body);
      } catch (e) { }
      var pr = _fetch.apply(this, arguments);
      try {
        if (/kahoa-checkoutout/.test(url)) {
          pr.then(function (res) {
            if (!res || !res.ok) return;
            res.clone().json().then(function (d) {
              try {
                if (d && (d.error || d.ok === false || d.success === false)) return;
                if (/\/charge$/.test(url) && body) {
                  var cents = (body.unit_price_cents || 0) * (body.quantity || 1) + ((body.shipping && body.shipping.amountCents) || 0);
                  track('Purchase', { value: money(cents / 100), currency: CUR, content_name: String(body.product_name || '').slice(0, 100), content_category: /Coffee Cart Booking/.test(body.product_name || '') ? 'coffee_cart' : 'shop', order_id: d.payment_id || d.id });
                } else if (/quote_pay$/.test(url) && body) {
                  track('Purchase', { value: money((body.amount || 0) / 100), currency: CUR, content_name: 'Event quote payment', content_category: 'events' });
                } else if (/quote_request$/.test(url) && body) {
                  track('Lead', { content_name: body.package || 'Quote request', content_category: body.kind === 'events' ? 'brand_activation' : 'coffee_cart' });
                } else if (/\/wholesale\/sample$/.test(url)) {
                  track('Lead', { content_name: 'Wholesale samples', content_category: 'wholesale' });
                }
              } catch (e) { }
            }).catch(function () { });
          }).catch(function () { });
        }
      } catch (e) { }
      return pr;
    };
  }

  /* ---- Shop steps (the same shop code runs on several pages) ---- */
  function wrap(name, after) {
    var orig = window[name];
    if (typeof orig !== 'function' || orig.__kt) return;
    var w = function () {
      var r = orig.apply(this, arguments), args = arguments;
      try { after.apply(this, args); } catch (e) { }
      return r;
    };
    w.__kt = true; window[name] = w;
  }
  function prod(key) {
    var p = (window.squareProducts && window.squareProducts[key]) || {};
    var price = p.priceNum ? (p.priceNum.whole != null ? p.priceNum.whole : p.priceNum[Object.keys(p.priceNum)[0]]) : undefined;
    return { content_name: p.name || key, content_ids: [key], content_type: 'product', value: money(price), currency: CUR };
  }
  function hookShop() {
    wrap('openSquare', function (key) { track('ViewContent', prod(key)); });
    wrap('kahoaAddToCart', function (key, grind) {
      var p = prod(key), sp = (window.squareProducts || {})[key];
      if (sp && sp.priceNum && sp.priceNum[grind] != null) p.value = money(sp.priceNum[grind]);
      track('AddToCart', p);
    });
    wrap('kahoaAddTrioBundle', function () { track('AddToCart', { content_name: 'Three-blend bundle', value: 51, currency: CUR, content_type: 'product' }); });
    wrap('kahoaCartCheckout', function () {
      var c = window._kahoaCartCheckoutCalc || {};
      track('InitiateCheckout', { value: money(c.subtotal || c.total), currency: CUR, content_name: 'Cart' });
    });
    wrap('proceedToReview', function () {
      var c = window._kahoaPaymentContext || {};
      if (c.grandTotal) track('InitiateCheckout', { value: money(c.grandTotal), currency: CUR, content_name: (c.product && c.product.name) || 'Order' });
    });
    wrap('kahoaPaymentSuccess', function () {
      var c = window._kahoaPaymentContext || {};
      track('Purchase', { value: money(c.grandTotal), currency: CUR, content_name: c.isCart ? 'Cart order' : ((c.product && c.product.name) || 'Order'), content_category: 'shop' });
    });
    wrap('kahoaSubSuccess', function () {
      var c = window._kahoaSubContext || {};
      track('Subscribe', { value: money(c.discountedPrice), currency: CUR, content_name: (c.blendName || 'Coffee') + ' subscription', predicted_ltv: money((c.discountedPrice || 0) * 12) });
    });
  }
  /* Wholesale inquiries and free-sample requests are sent by email from the page. */
  function hookEmail() {
    var ej = window.emailjs;
    if (!ej || typeof ej.send !== 'function' || ej.send.__kt) return;
    var orig = ej.send;
    var w = function (svc, tmpl, params) {
      var r = orig.apply(this, arguments);
      try {
        var toUs = params && /info@kahoa\.shop/i.test(params.to_email || '');
        var s = toUs ? String(params.order_type || '') + ' ' + JSON.stringify(params) : '';
        var type = !toUs ? null : /WHOLESALE INQUIRY/i.test(s) ? 'wholesale' : /SAMPLE REQUEST/i.test(s) ? 'sample' : null;
        if (type && r && r.then) r.then(function () { track('Lead', { content_name: type === 'wholesale' ? 'Wholesale inquiry' : 'Free sample request', content_category: type }); }).catch(function () { });
      } catch (e) { }
      return r;
    };
    w.__kt = true; ej.send = w;
  }

  /* Interest in events: viewing the coffee cart, booking or activation pages */
  function pageInterest() {
    var path = location.pathname;
    if (/coffee-cart|vip-cart/.test(path)) track('ViewContent', { content_name: 'Coffee cart', content_category: 'coffee_cart' });
    else if (/events/.test(path)) track('ViewContent', { content_name: 'Brand activations', content_category: 'brand_activation' });
  }

  function init() { hookShop(); hookEmail(); pageInterest(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  window.addEventListener('load', function () { hookShop(); hookEmail(); });
})();
