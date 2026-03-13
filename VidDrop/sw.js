const CACHE = 'viddrop-v1';
const ASSETS = ['/', '/index.html', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // API isteklerini cache'leme
  if (e.request.url.includes('/api/')) return;

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).catch(() => caches.match('/index.html')))
  );
});

// Share target - başka uygulamalardan link paylaşımı
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname === '/' && url.searchParams.has('url')) {
    const sharedUrl = url.searchParams.get('url');
    e.respondWith(
      Response.redirect(`/?shared=${encodeURIComponent(sharedUrl)}`, 302)
    );
  }
});
