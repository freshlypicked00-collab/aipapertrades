// Paper Trades app: keeps the race live. Pages and data always come fresh from the network;
// the last page seen is kept only as an offline fallback, and the icons are cached.
const CACHE = 'pt-app-v1';
const ICONS = ['/icon-192.png', '/icon-512.png', '/icon-maskable-512.png', '/apple-touch-icon.png'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ICONS)).catch(() => {})); self.skipWaiting(); });
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;                       // fonts, charts library, maps: the browser handles them
  if (req.mode === 'navigate') {                                     // the page: network first, last copy if offline
    e.respondWith(fetch(req).then((r) => { const c = r.clone(); caches.open(CACHE).then((x) => x.put('/', c)); return r; })
      .catch(() => caches.match('/').then((r) => r || new Response('You are offline. Paper Trades will update when you are back online.', { headers: { 'Content-Type': 'text/plain' } }))));
    return;
  }
  if (ICONS.includes(url.pathname)) e.respondWith(caches.match(req).then((r) => r || fetch(req)));
  // everything else (data.json, data.ver, og.png...) goes straight to the network
});
