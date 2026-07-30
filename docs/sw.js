/* Service worker: cache the whole app (incl. embedded audio) for full offline use.
   CACHE carries a content hash injected by build_html.py — it changes automatically
   whenever the app changes, which re-installs this SW and refreshes the cache.
   Do NOT hand-edit the version; just rebuild. */
var CACHE = "cet4-1250-53c7e8a42dea";
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
