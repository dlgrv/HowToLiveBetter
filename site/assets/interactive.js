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

  // Local preview (:8000) talks to make api-dev (:8090) unless __HTLB_API_FORCE__ is set.
  var _host = (typeof location !== 'undefined' && location.hostname) || '';
  var _local = _host === '127.0.0.1' || _host === 'localhost';
  var API =
    (_local && !(typeof window !== 'undefined' && window.__HTLB_API_FORCE__)
      ? 'http://127.0.0.1:8090/api/htlb/v1'
      : null) ||
    (typeof window !== 'undefined' && window.__HTLB_API__) ||
    'https://api.dlgrv.com/api/htlb/v1';
  var PB =
    (_local && !(typeof window !== 'undefined' && window.__HTLB_API_FORCE__)
      ? 'http://127.0.0.1:8090'
      : null) ||
    (typeof window !== 'undefined' && window.__HTLB_PB__) ||
    'https://api.dlgrv.com';
  var SYNC_KEY = 'htlb_sync_token';
  var AUTH_KEY = 'htlb_auth_token';
  var AUTH_USER_KEY = 'htlb_auth_user';

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
      else {
        localStorage.removeItem(AUTH_KEY);
        setAuthUser(null);
      }
    } catch (e) {}
  }
  function setAuthUser(rec) {
    try {
      if (!rec) {
        localStorage.removeItem(AUTH_USER_KEY);
        return;
      }
      localStorage.setItem(
        AUTH_USER_KEY,
        JSON.stringify({
          name: rec.name || '',
          username: rec.username || '',
          email: rec.email || '',
        })
      );
    } catch (e) {}
  }
  function authUser() {
    try {
      return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || 'null');
    } catch (e) {
      return null;
    }
  }
  /** Prefer name, then username/nick, then email. */
  function authDisplayName(u) {
    if (!u) return '';
    var name = String(u.name || '').trim();
    if (name) return name;
    var nick = String(u.username || '').trim();
    if (nick) return nick;
    return String(u.email || '').trim();
  }

  async function refreshAuthUser() {
    var tok = authToken();
    if (!tok) {
      setAuthUser(null);
      return null;
    }
    try {
      var res = await fetch(PB + '/api/collections/users/auth-refresh', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          Authorization: 'Bearer ' + tok,
        },
        credentials: 'omit',
      });
      if (res.status === 401) {
        setAuthToken('');
        return null;
      }
      if (!res.ok) return authUser();
      var data = await res.json();
      if (data.token) setAuthToken(data.token);
      if (data.record) {
        setAuthUser(data.record);
        return data.record;
      }
    } catch (e) {
      console.warn('auth refresh', e);
    }
    return authUser();
  }

  function headers(extra) {
    var h = Object.assign({ Accept: 'application/json', 'Content-Type': 'application/json' }, extra || {});
    var a = authToken();
    if (a) h.Authorization = 'Bearer ' + a;
    var s = syncToken();
    if (s) h['X-HTLB-Sync'] = s;
    return h;
  }

  /** Useful endpoints: Bearer only — never send guest sync (avoids guest useful hydrate). */
  function usefulHeaders() {
    var h = { Accept: 'application/json', 'Content-Type': 'application/json' };
    var a = authToken();
    if (a) h.Authorization = 'Bearer ' + a;
    return h;
  }

  async function api(path, opts) {
    opts = opts || {};
    var res = await fetch(API + path, {
      method: opts.method || 'GET',
      headers: opts.headers || headers(),
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

  async function usefulApi(path, opts) {
    opts = opts || {};
    return api(path, {
      method: opts.method,
      body: opts.body,
      headers: usefulHeaders(),
    });
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

  function formatUsefulLabel(count) {
    var L = labels();
    var n = Number(count) || 0;
    return (L.useful || 'Useful') + ' (' + n + ')';
  }

  function promptSignIn() {
    setAuthToken('');
    var acc = document.getElementById('account');
    if (acc) {
      acc.open = true;
      var btn = document.getElementById('account-btn');
      if (btn) {
        try {
          btn.focus();
        } catch (e) {}
      }
      return;
    }
    location.assign(loginHref());
  }

  async function toggleUseful(entryId, useful) {
    if (!authToken()) {
      promptSignIn();
      var err = new Error('sign-in required');
      err.status = 401;
      throw err;
    }
    try {
      return await usefulApi('/useful', {
        method: 'POST',
        body: { entryId: entryId, useful: !!useful },
      });
    } catch (err) {
      if (err && err.status === 401) {
        promptSignIn();
      }
      throw err;
    }
  }

  async function hydrateUseful() {
    if (!window.CARDS || !CARDS.length) return;
    var ids = [];
    var byId = {};
    CARDS.forEach(function (card) {
      var el = card.el;
      if (!el) return;
      var btn = el.querySelector('.htlb-useful');
      if (!btn) return;
      var id = btn.dataset.entry;
      if (!id) return;
      ids.push(id);
      byId[id] = btn;
    });
    var chunk = 50;
    for (var i = 0; i < ids.length; i += chunk) {
      var part = ids.slice(i, i + chunk);
      try {
        var data = await usefulApi('/useful?entryIds=' + encodeURIComponent(part.join(',')));
        var items = (data && data.items) || [];
        items.forEach(function (it) {
          var btn = byId[it.entryId];
          if (!btn) return;
          applyUsefulState(btn, it.useful, it.count);
        });
      } catch (e) {
        console.warn('useful hydrate', e);
        break;
      }
    }
  }

  function applyUsefulState(btn, useful, count) {
    var on = !!useful;
    btn.dataset.on = on ? '1' : '0';
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (typeof count === 'number') btn.dataset.count = String(count);
    var n = typeof count === 'number' ? count : Number(btn.dataset.count) || 0;
    btn.textContent = formatUsefulLabel(n);
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
          if (auth.record) setAuthUser(auth.record);
          return mergeGuest();
        })
        .then(function () {
          return refreshAuthUser();
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
    setAuthUser(null);
    // Previous guest was merged into the user; mint a clean anonymous session.
    refreshGuest()
      .catch(function (e) {
        console.warn('guest refresh after logout', e);
      })
      .finally(function () {
        renderAccountMenu();
        hydrateUseful().catch(function () {});
      });
  }

  /** Stub login for HTLB_DEV=1 API (localhost preview only). */
  async function loginDev() {
    var data = await api('/dev/login', { method: 'POST', body: {} });
    if (!data || !data.token) throw new Error('dev login: no token');
    setAuthToken(data.token);
    if (data.email) setAuthUser({ email: data.email, name: '', username: '' });
    try {
      await mergeGuest();
    } catch (e) {
      console.warn('merge after dev login', e);
    }
    await refreshAuthUser();
    dispatchEvent(new CustomEvent('htlb:auth', { detail: { ok: true, dev: true } }));
    renderAccountMenu();
    await hydrateUseful().catch(function () {});
  }

  function isLocalPreview() {
    return _local;
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
      useful: t.usefulLabel || 'Useful',
      myUseful: t.accountUseful || 'My useful',
    };
  }

  function siteBase() {
    return (typeof window !== 'undefined' && window.__HTLB_BASE__) || '';
  }

  function usefulHref() {
    return siteBase() + 'useful/';
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

    if (isLocalPreview()) {
      ensureDevLoginButton();
    }

    addEventListener('htlb:auth', function (ev) {
      if (ev && ev.detail && ev.detail.ok) redirectAfterAuth();
    });
  }

  function ensureDevLoginButton() {
    var actions = document.querySelector('.login-actions') || document.querySelector('.account-menu');
    if (!actions || document.getElementById('login-dev')) return;
    api('/dev/status')
      .then(function (st) {
        if (!st || !st.enabled) return;
        var b = document.createElement('button');
        b.type = 'button';
        b.id = 'login-dev';
        b.className = 'login-provider';
        b.textContent = 'Dev sign-in';
        b.addEventListener('click', function () {
          setLoginBusy(true);
          setLoginStatus('Dev sign-in…');
          loginDev()
            .then(function () {
              setLoginBusy(false);
              setLoginStatus('');
            })
            .catch(function (err) {
              console.warn(err);
              setLoginBusy(false);
              setLoginStatus('Dev sign-in failed', 'error');
            });
        });
        actions.appendChild(b);
      })
      .catch(function () {});
  }

  function entryId(e) {
    return e.id || String(e.sec) + '-' + String(e.n);
  }

  function enhanceCards() {
    var cards = window.CARDS;
    if (!cards || !cards.length) return;
    cards.forEach(function (card) {
      var e = card.e;
      var el = card.el;
      if (!el || el.querySelector('.htlb-actions')) return;
      var id = entryId(e);
      e.id = id;
      var bar = document.createElement('div');
      bar.className = 'htlb-actions';
      var useful = document.createElement('button');
      useful.type = 'button';
      useful.className = 'htlb-useful';
      useful.dataset.entry = id;
      useful.dataset.count = '0';
      useful.setAttribute('aria-pressed', 'false');
      useful.textContent = formatUsefulLabel(0);
      useful.addEventListener('click', function () {
        if (!authToken()) {
          promptSignIn();
          return;
        }
        // One in-flight vote per button — blocks double-click / spam clicks.
        if (useful.dataset.busy === '1') return;
        var on = useful.dataset.on !== '1';
        useful.dataset.busy = '1';
        useful.disabled = true;
        toggleUseful(id, on)
          .then(function (r) {
            applyUsefulState(useful, r.useful, r.count);
          })
          .catch(function (err) {
            if (err && err.status === 401) return;
            console.warn(err);
          })
          .finally(function () {
            useful.dataset.busy = '';
            useful.disabled = false;
          });
      });
      bar.appendChild(useful);
      // After Sources (<details class="src">); fall back to end of card.
      var src = el.querySelector('details.src') || el.querySelector('.src');
      if (src && src.parentNode) src.parentNode.insertBefore(bar, src.nextSibling);
      else el.appendChild(bar);
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
      note.id = 'htlb-account-who';
      note.textContent = authDisplayName(authUser()) || L.signedIn;
      menu.appendChild(note);
      menu.appendChild(
        menuButton(L.myUseful, function () {
          location.assign(usefulHref());
        })
      );
      menu.appendChild(menuButton(L.logout, logout));
      refreshAuthUser().then(function (rec) {
        var el = document.getElementById('htlb-account-who');
        if (!el) return;
        var who = authDisplayName(rec || authUser());
        if (who) el.textContent = who;
      });
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
    if (isLocalPreview()) {
      api('/dev/status')
        .then(function (st) {
          if (!st || !st.enabled) return;
          if (!document.getElementById('account-menu')) return;
          menu.appendChild(
            menuButton('Dev sign-in', function () {
              loginDev().catch(function (err) {
                console.warn('dev login', err);
              });
            })
          );
        })
        .catch(function () {});
    }
  }

  async function init() {
    try {
      await ensureGuest();
    } catch (e) {
      console.warn('htlb interactive init', e);
    }
    if (authToken()) {
      await refreshAuthUser().catch(function () {});
    }
    enhanceCards();
    renderAccountMenu();
    hydrateUseful().catch(function (e) {
      console.warn('htlb useful hydrate', e);
    });
  }

  function padSec(sec) {
    var s = String(sec);
    return s.length >= 2 ? s : ('0' + s).slice(-2);
  }

  function entrySec(entryId) {
    var i = String(entryId).indexOf('-');
    return i > 0 ? String(entryId).slice(0, i) : '';
  }

  async function resolveUsefulTitles(entryIds, lang, readmes) {
    var titles = {};
    var secs = {};
    entryIds.forEach(function (id) {
      var sec = entrySec(id);
      if (sec) secs[sec] = true;
    });
    var secList = Object.keys(secs);
    if (!secList.length) return titles;

    var readmeName = (readmes && readmes[lang]) || 'README.md';
    var base = siteBase();
    var md = '';
    try {
      var rr = await fetch(base + readmeName, { cache: 'no-cache' });
      if (rr.ok) md = await rr.text();
    } catch (e) {
      console.warn('useful titles readme', e);
    }
    var files = [];
    if (md) {
      files = Array.from(md.matchAll(/\]\((book\/[^)]+\.md)\)/g), function (m) {
        return m[1];
      });
    }

    await Promise.all(
      secList.map(async function (sec) {
        var pad = padSec(sec);
        var re = new RegExp('(?:^|/)' + pad + '-');
        var file = files.find(function (f) {
          return re.test(f);
        });
        if (!file) {
          // zh / root book/ fallback guesses
          var guesses = [
            'book/' + lang + '/' + pad + '-',
            'book/' + pad + '-',
          ];
          file = files.find(function (f) {
            return guesses.some(function (g) {
              return f.indexOf(g) === 0 || f.indexOf('/' + pad + '-') !== -1;
            });
          });
        }
        if (!file) return;
        try {
          var res = await fetch(base + file, { cache: 'no-cache' });
          if (!res.ok) return;
          var text = await res.text();
          var reTitle = /^### (\d+)\. (.+)$/gm;
          var m;
          while ((m = reTitle.exec(text))) {
            titles[sec + '-' + m[1]] = m[2].trim();
          }
        } catch (e) {
          console.warn('useful title chapter', file, e);
        }
      })
    );
    return titles;
  }

  async function initUsefulPage(opts) {
    opts = opts || {};
    var i18n = opts.i18n || {};
    var status = document.getElementById('useful-status');
    var list = document.getElementById('useful-list');
    var empty = document.getElementById('useful-empty');
    if (!list) return;

    if (!authToken()) {
      location.assign(loginHref());
      return;
    }

    if (status) status.textContent = i18n.loading || 'Loading…';

    try {
      var data = await usefulApi('/useful/mine');
      var items = (data && data.items) || [];
      var ids = items.map(function (it) {
        return it.entryId;
      }).filter(Boolean);
      var lang =
        (typeof window !== 'undefined' && window.__HTLB_LANG__) || 'en';
      var titles = await resolveUsefulTitles(ids, lang, opts.readmes || {});

      if (status) status.textContent = '';
      list.innerHTML = '';
      if (!ids.length) {
        list.hidden = true;
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      list.hidden = false;
      ids.forEach(function (id) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = siteBase() + lang + '/#e-' + id;
        a.textContent = titles[id] || id;
        li.appendChild(a);
        list.appendChild(li);
      });
    } catch (err) {
      console.warn('useful page', err);
      if (err && err.status === 401) {
        setAuthToken('');
        location.assign(loginHref());
        return;
      }
      if (status) status.textContent = i18n.error || 'Could not load your list.';
      list.hidden = true;
      if (empty) empty.hidden = true;
    }
  }

  window.HTLBInteractive = {
    init: init,
    ensureGuest: ensureGuest,
    loginOAuth: loginOAuth,
    loginDev: loginDev,
    logout: logout,
    loginHref: loginHref,
    usefulHref: usefulHref,
    initLoginPage: initLoginPage,
    initUsefulPage: initUsefulPage,
    api: api,
  };

  addEventListener('htlb:ready', function () {
    init();
  });
  // If the book finished loading before this script ran, init immediately.
  if (window.CARDS && window.CARDS.length) {
    init();
  }
})();
