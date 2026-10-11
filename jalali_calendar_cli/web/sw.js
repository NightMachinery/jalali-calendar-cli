// Holiday calendar page, offline. Network first: online, every request goes to the server
// as if this worker were not here, and a copy is kept; offline, or when the server has not
// answered within TIMEOUT, the last copy is served. So a redeployed page shows on the next
// open, and an installed app still opens without a connection.
"use strict";

var CACHE = "holidays";
var TIMEOUT = 3000;
// Everything the page loads; tests/test_html.py checks that the icons are all here.
var FILES = [
  "./",
  "theme.css",
  "app.js",
  "manifest.webmanifest",
  "icon.svg",
  "icon-192.png",
  "icon-512.png",
  "icon-maskable-512.png",
  "apple-touch-icon.png",
];

// Kept without the query, so `app.js?v=<hash>` replaces the previous copy rather than
// adding one per deploy, and without the page's `#view/mode/date`.
function key(url) {
  return url.split("#")[0].split("?")[0];
}

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches
      .open(CACHE)
      .then(function (cache) {
        return cache.addAll(
          FILES.map(function (f) {
            return new Request(f, { cache: "reload" });
          })
        );
      })
      .then(function () {
        return self.skipWaiting();
      })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches
      .keys()
      .then(function (names) {
        return Promise.all(
          names
            .filter(function (n) {
              return n !== CACHE;
            })
            .map(function (n) {
              return caches.delete(n);
            })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;

  var network = fetch(req);
  // registered now: once the response is served from the cache, it would be too late
  e.waitUntil(
    network
      .then(function (res) {
        if (!res.ok || res.redirected) return;
        var copy = res.clone();
        return caches.open(CACHE).then(function (cache) {
          return cache.put(key(req.url), copy);
        });
      })
      .catch(function () {})
  );
  var timeout = new Promise(function (resolve, reject) {
    setTimeout(reject, TIMEOUT);
  });

  e.respondWith(
    Promise.race([network, timeout]).catch(function () {
      return caches
        .match(key(req.url))
        .then(function (hit) {
          // the page under another name, such as index.html
          return hit || (req.mode === "navigate" && caches.match("./"));
        })
        .then(function (hit) {
          // nothing kept: wait for the network after all
          return hit || network;
        });
    })
  );
});
