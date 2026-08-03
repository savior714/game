(function loadCanonicalAuth(global) {
  'use strict';

  const AUTH_READY_EVENT = 'aiden-auth-module-loaded';

  function announceReady() {
    global.dispatchEvent(new Event(AUTH_READY_EVENT));
  }

  if (global.Auth) {
    announceReady();
    return;
  }
  if (global.__aidenAuthLoaderStarted) return;
  global.__aidenAuthLoaderStarted = true;

  const loader = document.currentScript
    || document.querySelector('script[src$="/domains/reward/auth.js"], script[src$="domains/reward/auth.js"]');
  if (!loader?.src) {
    console.error('[AuthLoader] unable to resolve compatibility loader URL');
    return;
  }

  const canonical = document.createElement('script');
  canonical.id = 'aiden-canonical-auth';
  canonical.src = new URL('../auth/auth.js', loader.src).href;
  canonical.onload = announceReady;
  canonical.onerror = () => {
    console.error('[AuthLoader] canonical auth module failed to load:', canonical.src);
  };
  document.head.appendChild(canonical);
})(window);
