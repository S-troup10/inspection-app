// Define a cache name
const CACHE_NAME = 'hv-engineers-cache-v1';

// List of assets to cache
const CACHE_ASSETS = [
    
    '/static/css/style.css',
    '/static/css/reportStyle.css',
    '/static/images/hv.png',
    '/static/js/service_worker.js',  // Add more JavaScript files if needed
    '/manifest.json',  // Ensure manifest is cached too
    '/templates/index.html',
    '/templates/customer.html',
    '/templates/customerAdd.html',
    '/templates/customerEdit.html',
    '/templates/base.html',
    '/templates/inspectionDetails.html',
    '/templates/inspectionDetailAdd.html',
    '/templates/inspectionDetailEdit.html',
    '/templates/inspections.html',
    '/templates/inspectionsAdd.html',
    '/templates/inspectionsEdit.html',
    '/templates/report.html',
    '/templates/revisions.html',
    '/templates/revisionsAdd.html',
    '/templates/selectPrint.html',
    '/local_data.db'





];

// Install event: cache the specified assets
self.addEventListener('install', (event) => {
    console.log('Service Worker: Install Event');

    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Service Worker: Caching assets...');
            // Debug each asset being cached
            return Promise.all(
                CACHE_ASSETS.map((asset) => {
                    console.log(`Service Worker: Attempting to cache ${asset}`);
                    return cache.add(asset).catch((error) => {
                        console.error(`Service Worker: Failed to cache ${asset}`, error);
                    });
                })
            );
        }).then(() => {
            console.log('Service Worker: Caching completed');
        }).catch((error) => {
            console.error('Service Worker: Cache installation failed', error);
        })
    );
});


// Activate event: clean up old caches
self.addEventListener('activate', (event) => {
    const cacheWhitelist = [CACHE_NAME];  // Add more cache versions as you update them
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (!cacheWhitelist.includes(cacheName)) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Fetch event: serve assets from cache or fetch from the network if not cached
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            // Return cached response if available
            if (cachedResponse) {
                console.log('Service Worker: Serving cached asset', event.request.url);
                return cachedResponse;
            }
            // Otherwise, fetch from the network
            return fetch(event.request);
        })
    );
});

