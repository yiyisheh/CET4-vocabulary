/* Service worker: cache the whole app (incl. embedded audio) for full offline use.
   Bump CACHE when index.html changes so clients pick up the new version. */
var CACHE = "cet4-1250-v1";
var ASSETS = [
  "./", "./index.html", "./manifest.webmanifest",
  "./icon-180.png", "./icon-192.png", "./icon-512.png"
];

self.addEventListener("install", function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(ASSETS); })
    .then(function(){ return self.skipWaiting(); }));
});

self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.map(function(k){ if(k!==CACHE) return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});

// cache-first: instant + offline. Falls back to network for anything uncached.
self.addEventListener("fetch", function(e){
  if(e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(function(hit){
      return hit || fetch(e.request).then(function(res){
        return res;
      }).catch(function(){ return caches.match("./index.html"); });
    })
  );
});
