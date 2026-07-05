// sw.js - Service Worker for Offline Support
const CACHE_NAME = 'prime-shop-v2';

const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/custom.js',
  '/offline.html'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request).catch(() => {
          return caches.match('/offline.html');
        });
      })
  );
});