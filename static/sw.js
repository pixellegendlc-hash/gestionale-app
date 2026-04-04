const CACHE = 'gestionale-v2';
const ASSETS = ['/', '/static/manifest.json', '/static/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS).catch(()=>{})));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if(e.request.url.includes('/api/')) return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});

// ── PUSH NOTIFICATIONS ──
self.addEventListener('push', e => {
  if(!e.data) return;
  let payload;
  try { payload = e.data.json(); }
  catch { payload = { title: 'Gestionale', body: e.data.text() }; }

  e.waitUntil(
    self.registration.showNotification(payload.title || 'Gestionale', {
      body:    payload.body   || '',
      icon:    '/static/icon-192.png',
      badge:   '/static/icon-192.png',
      vibrate: [200, 100, 200],
      data:    { url: payload.url || '/' },
      actions: [{ action: 'open', title: 'Apri' }]
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/';
  e.waitUntil(
    clients.matchAll({ type: 'window' }).then(cs => {
      if(cs.length > 0) { cs[0].focus(); cs[0].navigate(url); }
      else clients.openWindow(url);
    })
  );
});
