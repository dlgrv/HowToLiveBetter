/**
 * HTLB interactive client — guest sync + optional OAuth (Google/GitHub).
 * Guest: X-HTLB-Sync. User: Authorization Bearer. Never mix.
 */
(function () {
  'use strict';

  var API =
    (typeof window !== 'undefined' && window.__HTLB_API__) ||
    'https://api.dlgrv.com/api/htlb/v1';
  var PB =
    (typeof window !== 'undefined' && window.__HTLB_PB__) ||
    'https://api.dlgrv.com';
  var SYNC_KEY = 'htlb_sync_token';
  var AUTH_KEY = 'htlb_auth_token';

  function syncToken() {
    try {
      return localStorage.getItem(SYNC_KEY) || '';
    } catch (e) {
      return '';
    }
  }
  function setSyncToken(t) {
    try {
      if (t) localStorage.setItem(SYNC_KEY, t);
      else localStorage.removeItem(SYNC_KEY);
    } catch (e) {}
  }
  function authToken() {
    try {
      return localStorage.getItem(AUTH_KEY) || '';
    } catch (e) {
      return '';
    }
  }
  function setAuthToken(t) {
    try {
      if (t) localStorage.setItem(AUTH_KEY, t);
      else localStorage.removeItem(AUTH_KEY);
    } catch (e) {}
  }

  function headers(extra) {
    var h = Object.assign({ Accept: 'application/json', 'Content-Type': 'application/json' }, extra || {});
    var a = authToken();
    if (a) h.Authorization = 'Bearer ' + a;
    var s = syncToken();
    if (s) h['X-HTLB-Sync'] = s;
    return h;
  }

  async function api(path, opts) {
    opts = opts || {};
    var res = await fetch(API + path, {
      method: opts.method || 'GET',
      headers: headers(opts.headers),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      credentials: 'omit',
    });
    if (!res.ok) {
      var err = new Error('api ' + res.status);
      err.status = res.status;
      throw err;
    }
    if (res.status === 204) return null;
    return res.json();
  }

  async function ensureGuest() {
    if (syncToken()) return syncToken();
    var data = await api('/guest/session', { method: 'POST', body: {} });
    setSyncToken(data.token);
    return data.token;
  }

  async function toggleUseful(entryId, useful) {
    await ensureGuest();
    return api('/useful', { method: 'POST', body: { entryId: entryId, useful: !!useful } });
  }

  async function toggleBookmark(entryId, on) {
    await ensureGuest();
    if (on) return api('/bookmarks', { method: 'PUT', body: { entryId: entryId } });
    return api('/bookmarks?entryId=' + encodeURIComponent(entryId), { method: 'DELETE' });
  }

  async function mergeGuest() {
    if (!authToken() || !syncToken()) return null;
    return api('/merge', { method: 'POST', body: {} });
  }

  /** OAuth via PocketBase popup (Google / GitHub only). */
  function loginOAuth(provider) {
    if (provider !== 'google' && provider !== 'github') {
      throw new Error('unsupported provider');
    }
    var w = 600;
    var h = 700;
    var left = (screen.width - w) / 2;
    var top = (screen.height - h) / 2;
    var popup = window.open(
      'about:blank',
      'htlb_oauth',
      'width=' + w + ',height=' + h + ',left=' + left + ',top=' + top
    );
    if (!popup) throw new Error('popup blocked');

    // Load PocketBase UMD only for authWithOAuth2
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/pocketbase@0.28.4/dist/pocketbase.umd.js';
    s.onload = function () {
      var PBCtor = window.PocketBase;
      if (!PBCtor) {
        popup.close();
        return;
      }
      var pb = new PBCtor(PB);
      pb.collection('users')
        .authWithOAuth2({ provider: provider, urlCallback: function (url) { popup.location = url; } })
        .then(function (auth) {
          setAuthToken(auth.token);
          return mergeGuest();
        })
        .then(function () {
          try { popup.close(); } catch (e) {}
          dispatchEvent(new CustomEvent('htlb:auth', { detail: { ok: true } }));
          renderAccountMenu();
        })
        .catch(function (err) {
          console.warn('oauth failed', err);
          try { popup.close(); } catch (e) {}
        });
    };
    document.head.appendChild(s);
  }

  function logout() {
    setAuthToken('');
    renderAccountMenu();
  }

  function labels() {
    var t = typeof T === 'function' ? T() : {};
    return {
      aria: t.accountAria || 'Account',
      signIn: t.accountSignIn || 'Sign in',
      google: t.accountGoogle || 'Continue with Google',
      github: t.accountGithub || 'Continue with GitHub',
      logout: t.accountLogout || 'Log out',
      signedIn: t.accountSignedIn || 'Signed in',
      hint: t.accountHint || 'Sign in so that on any of your devices you can continue reading where you left off, and keep which recommendations you marked as useful.',
    };
  }

  function siteBase() {
    return (typeof window !== 'undefined' && window.__HTLB_BASE__) || '';
  }

  function loginHref() {
    return siteBase() + 'login/?next=' + encodeURIComponent(location.href);
  }

  function closeAccount() {
    var acc = document.getElementById('account');
    if (acc) acc.open = false;
  }

  function menuButton(text, onClick) {
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('role', 'menuitem');
    b.textContent = text;
    b.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      closeAccount();
      onClick();
    });
    return b;
  }

  function safeNextUrl() {
    var p = new URLSearchParams(location.search);
    var next = p.get('next') || '';
    if (!next) return '';
    try {
      var u = new URL(next, location.origin);
      if (u.origin !== location.origin) return '';
      return u.pathname + u.search + u.hash;
    } catch (e) {
      return '';
    }
  }

  function defaultBookUrl() {
    var lang =
      (typeof window !== 'undefined' && window.__HTLB_LANG__) ||
      (function () {
        try {
          return localStorage.getItem('htlb-lang') || '';
        } catch (e) {
          return '';
        }
      })() ||
      'en';
    if (!/^(en|ru|zh|es|pt|ar|id)$/.test(lang)) lang = 'en';
    return siteBase() + lang + '/';
  }

  function redirectAfterAuth() {
    location.assign(safeNextUrl() || defaultBookUrl());
  }

  function initLoginPage() {
    if (authToken()) {
      redirectAfterAuth();
      return;
    }

    ensureGuest().catch(function (e) {
      console.warn('htlb login init', e);
    });

    var g = document.getElementById('login-google');
    var gh = document.getElementById('login-github');
    if (g) {
      g.addEventListener('click', function () {
        loginOAuth('google');
      });
    }
    if (gh) {
      gh.addEventListener('click', function () {
        loginOAuth('github');
      });
    }

    addEventListener('htlb:auth', function (ev) {
      if (ev && ev.detail && ev.detail.ok) redirectAfterAuth();
    });
  }

  function entryId(e) {
    return e.id || String(e.sec) + '-' + String(e.n);
  }

  function enhanceCards() {
    if (!window.CARDS || !CARDS.length) return;
    CARDS.forEach(function (card) {
      var e = card.e;
      var el = card.el;
      if (!el || el.querySelector('.htlb-actions')) return;
      var id = entryId(e);
      e.id = id;
      var bar = document.createElement('div');
      bar.className = 'htlb-actions';
      bar.style.cssText = 'display:flex;gap:.5rem;margin:.5rem 0;font-size:.85rem';
      var useful = document.createElement('button');
      useful.type = 'button';
      useful.textContent = 'Useful';
      useful.dataset.entry = id;
      useful.addEventListener('click', function () {
        var on = useful.dataset.on !== '1';
        toggleUseful(id, on)
          .then(function (r) {
            useful.dataset.on = r.useful ? '1' : '0';
            useful.textContent = r.useful ? 'Useful ✓ (' + r.count + ')' : 'Useful (' + r.count + ')';
          })
          .catch(function (err) {
            console.warn(err);
          });
      });
      var bm = document.createElement('button');
      bm.type = 'button';
      bm.textContent = 'Bookmark';
      bm.addEventListener('click', function () {
        var on = bm.dataset.on !== '1';
        toggleBookmark(id, on)
          .then(function () {
            bm.dataset.on = on ? '1' : '0';
            bm.textContent = on ? 'Bookmarked ✓' : 'Bookmark';
          })
          .catch(function (err) {
            console.warn(err);
          });
      });
      bar.appendChild(useful);
      bar.appendChild(bm);
      var title = el.querySelector('h3, .t, .title') || el.firstElementChild;
      if (title && title.parentNode) title.parentNode.insertBefore(bar, title.nextSibling);
      else el.insertBefore(bar, el.firstChild);
    });
  }

  function wireAccountLoginRedirect(acc) {
    if (acc.dataset.htlbLoginGate === '1') return;
    acc.dataset.htlbLoginGate = '1';
    acc.addEventListener(
      'click',
      function (e) {
        if (acc.dataset.signedIn === '1') return;
        if (!e.target.closest('summary')) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        acc.open = false;
        location.assign(loginHref());
      },
      true
    );
  }

  function renderAccountMenu() {
    var old = document.getElementById('htlb-account');
    if (old) old.remove();

    var acc = document.getElementById('account');
    var menu = document.getElementById('account-menu');
    var btn = document.getElementById('account-btn');
    if (!acc || !menu) return;

    wireAccountLoginRedirect(acc);

    var L = labels();
    var signedIn = !!authToken();
    acc.dataset.signedIn = signedIn ? '1' : '0';
    if (!signedIn) acc.open = false;
    if (btn) {
      var label = signedIn ? L.aria : L.signIn;
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      btn.setAttribute('aria-haspopup', signedIn ? 'menu' : 'false');
    }

    menu.innerHTML = '';
    if (!signedIn) return;

    var note = document.createElement('span');
    note.className = 'account-note';
    note.textContent = L.signedIn;
    menu.appendChild(note);
    menu.appendChild(menuButton(L.logout, logout));
  }

  async function init() {
    try {
      await ensureGuest();
    } catch (e) {
      console.warn('htlb interactive init', e);
    }
    enhanceCards();
    renderAccountMenu();
  }

  window.HTLBInteractive = {
    init: init,
    ensureGuest: ensureGuest,
    loginOAuth: loginOAuth,
    logout: logout,
    loginHref: loginHref,
    initLoginPage: initLoginPage,
    api: api,
  };

  addEventListener('htlb:ready', function () {
    init();
  });
})();
