const CACHE_NAME = "hvEngineers-cache-v1";

const ITEMS_TO_CACHE = [
  '/index.html', 
  '/customer.html', 
  '/customerAdd.html', 
  '/customerEdit.html', 
  '/offline.html',
  '/inspectionDetails.html',
  '/inspectionDetailAdd.html',
  '/inspectionDetailEdit.html',
  '/inspections.html',
  '/inspectionsAdd.html',
  '/inspectionsEdit.html',
  '/selectPrint.html',


  '/static/manifest.json',
  '/static/css/style.css',
  '/static/images/hv.png',
  '/static/images/icon.png',
  '/static/images/offline.jpg',
  '/static/js/main.js'
  
]


self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) =>{
            console.log('cache opened')
            return cache.addAll(ITEMS_TO_CACHE)

        })
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              return caches.delete(cacheName);
            }
          })
        );
      })
    );
  });


self.addEventListener("fetch", (event) => {
    console.log('fetch function called');
    event.respondWith(
        caches.match(event.request)
        .then((cachedResponse) => {
            if (cachedResponse) {
                console.log(cachedResponse)
                return cachedResponse;
            }

            return fetch(event.request)
            .then((networkResponse) => {

                const responseClone = networkResponse.clone();

                const requestClone = event.request.clone();

                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(requestClone, responseClone)

                });

            return networkResponse
            });
        }) 
        .catch((error) => {
            console.error('fetch failed, returning offline if avalkiable', error)
            return caches.match('offline.html')
        })
        
        
        
    );
});
