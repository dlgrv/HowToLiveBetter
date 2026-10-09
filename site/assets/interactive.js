/**
 * HTLB interactive client — guest sync + optional OAuth (Google/GitHub).
 * Guest: X-HTLB-Sync. User: Authorization Bearer. Never mix.
 *
 * Auth/sync only on book.dlgrv.com (+ local preview). GitHub Pages stays
 * a static mirror without account UI.
 */
(function () {
  'use strict';

  function interactiveHostOk() {
    var h = (typeof location !== 'undefined' && location.hostname) || '';
    return (
      h === 'book.dlgrv.com' ||
      h === '127.0.0.1' ||
      h === 'localhost' ||
      h.endsWith('.book.dlgrv.com')
    );
  }

  if (!interactiveHostOk()) {
    function hideAccount() {
      var acc = document.getElementById('account');
      if (acc) acc.hidden = true;
    }
    window.HTLBInteractive = {
      init: hideAccount,
      ensureGuest: function () { return Promise.resolve(null); },
      loginOAuth: function () {},
      logout: function () {},
      loginHref: function () { return '#'; },
      initLoginPage: function () {
        hideAccount();
        location.replace('../en/');
      },
      api: function () { return Promise.reject(new Error('interactive disabled')); },
    };
    addEventListener('htlb:ready', hideAccount);
    if (document.readyState !== 'loading') hideAccount();
    else document.addEventListener('DOMContentLoaded', hideAccount);
    return;
  }

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

  /** Drop merged/revoked guest token and mint a fresh one. */
  async function refreshGuest() {
    setSyncToken('');
    return ensureGuest();
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
    try {
      return await api('/merge', { method: 'POST', body: {} });
    } catch (err) {
      // After logout/re-login the stored guest is often already merged → 401.
      // Auth itself succeeded; refresh guest and continue signed-in.
      if (err && err.status === 401) {
        console.warn('merge skipped (stale guest)', err);
        await refreshGuest();
        return null;
      }
      throw err;
    }
  }

  function setLoginStatus(text, tone) {
    var el = document.getElementById('login-status');
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = '';
      el.removeAttribute('data-tone');
      return;
    }
    el.hidden = false;
    el.textContent = text;
    if (tone) el.setAttribute('data-tone', tone);
    else el.removeAttribute('data-tone');
  }

  function setLoginBusy(busy) {
    ['login-google', 'login-github'].forEach(function (id) {
      var b = document.getElementById(id);
      if (b) b.disabled = !!busy;
    });
  }

  /** OAuth via PocketBase popup (Google / GitHub only). */
  function loginOAuth(provider) {
    if (provider !== 'google' && provider !== 'github') {
      throw new Error('unsupported provider');
    }
    var L = labels();
    var w = 600;
    var h = 700;
    var left = (screen.width - w) / 2;
    var top = (screen.height - h) / 2;
    var popup = window.open(
      'about:blank',
      'htlb_oauth',
      'width=' + w + ',height=' + h + ',left=' + left + ',top=' + top
    );
    if (!popup) {
      setLoginStatus(L.loginError || 'Sign-in failed. Close the popup and try again.', 'error');
      throw new Error('popup blocked');
    }

    setLoginBusy(true);
    setLoginStatus(L.loginWorking || 'Waiting for sign-in…');

    // PocketBase UMD (vendored latest npm JS SDK; Go server version is independent — see api/go.mod)
    function failOAuth(err) {
      console.warn('oauth failed', err);
      try { popup.close(); } catch (e) {}
      setLoginBusy(false);
      setLoginStatus(L.loginError || 'Sign-in failed. Close the popup and try again.', 'error');
      dispatchEvent(new CustomEvent('htlb:auth', { detail: { ok: false, error: String(err && err.message || err) } }));
    }
    function runOAuth() {
      var PBCtor = window.PocketBase;
      if (!PBCtor) {
        failOAuth(new Error('PocketBase SDK missing'));
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
          setLoginBusy(false);
          setLoginStatus('');
          dispatchEvent(new CustomEvent('htlb:auth', { detail: { ok: true } }));
          renderAccountMenu();
        })
        .catch(failOAuth);
    }
    if (window.PocketBase) {
      runOAuth();
      return;
    }
    var s = document.createElement('script');
    s.src = siteBase() + 'assets/pocketbase.umd.js';
    s.onload = runOAuth;
    s.onerror = function () { failOAuth(new Error('failed to load PocketBase SDK')); };
    document.head.appendChild(s);
  }

  function logout() {
    setAuthToken('');
    // Previous guest was merged into the user; mint a clean anonymous session.
    refreshGuest()
      .catch(function (e) {
        console.warn('guest refresh after logout', e);
      })
      .finally(function () {
        renderAccountMenu();
      });
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
      loginWorking: t.loginWorking || 'Waiting for sign-in…',
      loginError: t.loginError || 'Sign-in failed. Close the popup and try again.',
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

  function renderAccountMenu() {
    var old = document.getElementById('htlb-account');
    if (old) old.remove();

    var acc = document.getElementById('account');
    var menu = document.getElementById('account-menu');
    var btn = document.getElementById('account-btn');
    if (!acc || !menu) return;

    var L = labels();
    var signedIn = !!authToken();
    acc.dataset.signedIn = signedIn ? '1' : '0';
    if (btn) {
      var label = signedIn ? L.aria : L.signIn;
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      btn.setAttribute('aria-haspopup', 'menu');
    }

    menu.innerHTML = '';
    if (signedIn) {
      var note = document.createElement('span');
      note.className = 'account-note';
      note.textContent = L.signedIn;
      menu.appendChild(note);
      menu.appendChild(menuButton(L.logout, logout));
      return;
    }

    if (L.hint) {
      var hint = document.createElement('span');
      hint.className = 'account-note';
      hint.textContent = L.hint;
      menu.appendChild(hint);
    }
    menu.appendChild(
      menuButton(L.signIn, function () {
        location.assign(loginHref());
      })
    );
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
