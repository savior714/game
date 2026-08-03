(function loadCanonicalSync(global) {
  'use strict';

  const AUTH_READY_EVENT = 'aiden-auth-module-loaded';
  if (global.SyncEngine || global.__aidenSyncLoaderStarted) return;
  global.__aidenSyncLoaderStarted = true;

  const loader = document.currentScript
    || document.querySelector('script[src$="/domains/reward/sync-engine.js"], script[src$="domains/reward/sync-engine.js"]');
  if (!loader?.src) {
    console.error('[SyncLoader] unable to resolve compatibility loader URL');
    return;
  }
  const canonicalUrl = new URL('../sync/sync-engine.js', loader.src).href;

  function loadSync() {
    if (global.SyncEngine || document.getElementById('aiden-canonical-sync')) return;
    const canonical = document.createElement('script');
    canonical.id = 'aiden-canonical-sync';
    canonical.src = canonicalUrl;
    canonical.onerror = () => {
      console.error('[SyncLoader] canonical sync module failed to load:', canonical.src);
    };
    document.head.appendChild(canonical);
  }

  if (global.Auth) loadSync();
  else global.addEventListener(AUTH_READY_EVENT, loadSync, { once: true });
})(window);
