/* Service worker: keep the app usable offline.
   Do NOT hand-edit anything below marked __…__; build_html.py injects it.

   The app is split in two (see WEB_HANDOFF §4.1):
     - the shell (index.html, ~560KB: layout, logic, all 1250 entries of text) — precached here
     - two audio packs of raw mp3 bytes (~36MB) — fetched and cached BY THE PAGE, which reads
       them through a streaming reader so it can draw a real progress bar. We only need to serve
       them from cache afterwards, which the cache-first handler below does for free.

   The cache name is deliberately STABLE across builds. Versioning lives in the file names
   instead (audio-us.<hash>.bin), so a rebuild that only touches CSS re-downloads 560KB and
   leaves 36MB of audio untouched. Stale entries are pruned against MANIFEST on activate. */
var CACHE = "cet4-1250";
// The shell's content hash. It is not used for anything at runtime — it is here so that a rebuild
// that only touched the shell (a CSS line, say) still changes THESE bytes. Browsers decide there
// is an update by byte-comparing sw.js; without this line an unhashed index.html plus PRECACHE
// lists that never move would leave sw.js identical forever, and the cache-first shell would
// never be replaced on any device that already installed it.
var BUILD = "c9e8910bfc2b";
// PRECACHE is downloaded here on install (small). KEEP additionally lists the audio packs, which
// the PAGE downloads and caches — precaching them here too would fetch the same 36MB twice.
var PRECACHE = ["./index.html", "./manifest.webmanifest", "./icon-180.png", "./icon-192.png", "./icon-512.png"];
var KEEP = ["./index.html", "./manifest.webmanifest", "./icon-180.png", "./icon-192.png", "./icon-512.png", "./audio-us.9f9a204cb2.bin", "./audio-ex.7b5586bace.bin"];
var APP = "./index.html";
// Navigations ask for "./", not "./index.html", so we answer them from the one cached copy
// rather than caching both URLs (that stored the same bytes twice).

self.addEventListener("install", function(e){
  // cache:"reload" bypasses the HTTP cache. Without it an upgrade can bake a STALE index.html
  // into the offline cache and serve it forever — and across the shell/pack split that is fatal,
  // since an old inlined index.html has empty audio blocks and no AUDIO_INDEX = a mute app.
  // The shell is ~560KB, so forcing revalidation costs nothing.
  function reqs(){
    try { return PRECACHE.map(function(u){ return new Request(u, { cache: "reload" }); }); }
    catch(err){ return PRECACHE; }              // very old Safari: no cache option on Request
  }
  // NOTE: we deliberately do NOT skipWaiting() here. A rebuilt SW installs and then WAITS; the app
  // does not auto-update. The page only tells us to take over (SKIP_WAITING below) after the user
  // confirms the update in the "检测到新版本" dialog. See template.html's update IIFE / WEB_HANDOFF §10.2.
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(reqs()); }));
});

// The page posts this once the user confirms the update; only then do we activate and take control
// (which fires controllerchange on the page → a single reload into the new version).
self.addEventListener("message", function(e){
  if(e.data && e.data.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("activate", function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){
    // Drop what this build no longer references — chiefly audio packs whose hash changed.
    // Anything still listed keeps its bytes, which is the whole point of hashed pack names.
    return c.keys().then(function(reqs){
      var keep = KEEP.map(function(u){ return new URL(u, self.registration.scope).href; });
      return Promise.all(reqs.map(function(r){
        if(keep.indexOf(r.url) === -1) return c.delete(r);
      }));
    });
  }).then(function(){
    return caches.keys().then(function(keys){     // older builds used per-hash cache names
      return Promise.all(keys.map(function(k){ if(k !== CACHE) return caches.delete(k); }));
    });
  }).then(function(){ return self.clients.claim(); }));
});

// cache-first: instant + offline. Falls back to network for anything uncached.
self.addEventListener("fetch", function(e){
  if(e.request.method !== "GET") return;
  var navigation = e.request.mode === "navigate";
  e.respondWith(
    caches.match(e.request).then(function(hit){
      if(hit) return hit;
      if(navigation) return caches.match(APP).then(function(app){   // "./" -> the one cached copy
        return app || fetch(e.request);
      });
      // Anything else must fail honestly. Falling back to APP here would answer an uncached
      // audio pack with 200 text/html, and the page would cache that HTML under the pack URL
      // and go permanently mute. Only navigations may be answered with the shell.
      return fetch(e.request);
    })
  );
});
