const CACHE_NAME = "hvEngineers-cache-v1";

const EXCLUDED_ROUTES = [
    '/select-Inspections',
    '/sync/Inspection_Details',
    '/sync/Customer',
    '/sync/Inspection_Header',
    '/rest/v1/Inspection_Details?select=*',
    '/rest/v1/Customer?select=*',
    '/rest/v1/Inspection_Header?select=*'

];

const ITEMS_TO_CACHE = [
    '/',
    '/customer',
    '/customer-Add',
    '/inspections',
    '/inspection-Add',
    '/inspection-Details',
    '/inspectionDetails-Add',
    '/customer/edit',
    '/inspections/edit',
    '/inspection-Details/edit',
    '/static/manifest.json',
    '/static/css/style.css',
    '/static/images/hv.png',
    '/static/images/icon.png',
    '/static/images/offline.jpg',
    '/static/js/main.js',
    '/static/js/db.js',
    '/static/js/table.js'
];

// Install Event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Cache opened and populated');
            return cache.addAll(ITEMS_TO_CACHE);
        })
    );
});

// Activate Event
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

// Fetch Event
self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    const shouldExclude = url.pathname.startsWith('/rest') || EXCLUDED_ROUTES.some(route => event.request.url.includes(route));


    if (event.request.method === "POST" || shouldExclude) {
        event.respondWith(fetch(event.request));
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }

                return fetch(event.request).then((networkResponse) => {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                    return networkResponse;
                });
            })
            .catch(() => caches.match('/offline.html'))
    );
});

// Sync Event
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-client-server') {
        console.log('Sync event triggered: Syncing client with server...');
        event.waitUntil(syncClientWithServer());
    }
});

// Sync Function to Import and Call from db.js
async function syncClientWithServer() {
    try {
        // Import the `sync_client_with_server` function from db.js
        await importScripts('/static/js/db.js');

        // Ensure the `sync_client_with_server` function is available
        if (typeof sync_client_with_server === 'function') {
            await sync_client_with_server();
            console.log('Client-server sync completed successfully.');
        } else {
            console.error('sync_client_with_server function not found in db.js.');
        }
    } catch (error) {
        console.error('Error during client-server sync:', error);
    }
}
