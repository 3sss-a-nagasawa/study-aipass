/**
 * Service Worker: アプリ本体をキャッシュし、オフラインでも出題できるようにする。
 * 問題データは localStorage にあるためキャッシュ対象外。Gemini API への通信もキャッシュしない。
 * アプリを更新したら CACHE_VERSION を上げる。
 */
const CACHE_VERSION = "aipass-v1";
const APP_FILES = [
  "./",
  "index.html",
  "style.css",
  "manifest.webmanifest",
  "js/quiz.js",
  "js/storage.js",
  "js/feedback.js",
  "js/app.js",
  "js/settings.js",
  "icons/icon-180.png",
  "icons/icon-192.png",
  "icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_VERSION).then((cache) => cache.addAll(APP_FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  // 古いバージョンのキャッシュを削除する
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // 同じ配信元の GET だけを扱う（Gemini API などは素通し）
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  // ネットワーク優先で最新を取得し、失敗したらキャッシュを返す
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true }).then((cached) => cached || caches.match("index.html")))
  );
});
