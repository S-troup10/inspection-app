const CACHE_NAME = "hvEngineers-cache-v1";

const ITEMS_TO_CACHE = [
  '/index.html', 
  '/customer.html', 
  '/customerAdd.html', 
  '/customerEdit.html', 
  '/inspectionDetails.html',
  '/inspectionDetailAdd.html',
  '/inspectionDetailEdit.html',
  '/inspections.html',
  '/inspectionsAdd.html',
  '/inspectionsEdit.html',

  '/static/manifest.json',
  '/static/css/style.css',
  '/static/images/hv.png',
  '/static/images/icon.png',
  '/static/images/offline.jpg',
  '/static/js/main.js',
  '/static/js/db.js',
  '/static/js/table.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Cache opened and populated');
            return cache.addAll(ITEMS_TO_CACHE);
        })
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName); // Delete old caches
                    }
                })
            );
        }).then(() => {
            console.log("Cache updated");
        })
    );
});

self.addEventListener("fetch", (event) => {
    if (event.request.method === "POST") {
        // Directly fetch POST requests from the network
        event.respondWith(fetch(event.request));
        return;
    }

    event.respondWith(
        caches.match(event.request) // Try to find the resource in the cache first
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // If resource is found in cache, serve it
                    return cachedResponse;
                }

                // Otherwise, fetch from network and cache the response
                return fetch(event.request).then((networkResponse) => {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                    return networkResponse;
                });
            })
            .catch((error) => {
                console.error("Resource not available in cache or network:", error);
                // Fallback to offline page if all else fails
                return caches.match('/offline.html');
            })
    );
});
