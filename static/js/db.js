console.log('db.js ran');

let db;

const getBaseUrl = () => {
    const { protocol, hostname, port } = window.location;
    return `${protocol}//${hostname}${port ? `:${port}` : ''}`;
};

// Open IndexedDB and initialize the database structure
const openDB = () => {
    const request = indexedDB.open('HV-storage', 1);

    request.onsuccess = (event) => {
        db = event.target.result;
        console.log('IndexedDB opened successfully');
        
    };

    request.onerror = (event) => {
        console.error('IndexedDB error:', event.target.error);
    };

    request.onupgradeneeded = (event) => {
        
        const db = event.target.result;

        // Create object stores for each table
        const customersStore = db.createObjectStore('Customer', { keyPath: 'customer_id', autoIncrement: true });
        customersStore.createIndex('name', 'name', { unique: false });

        const inspectionsStore = db.createObjectStore('Inspection_Header', { keyPath: 'inspection_id', autoIncrement: true });
        inspectionsStore.createIndex('customer_id', 'customer_id');

        const detailsStore = db.createObjectStore('Inspection_Details', { keyPath: 'detail_id', autoIncrement: true });
        detailsStore.createIndex('inspection_id', 'inspection_id', { unique: false });


        console.log('Database structure initialized.');
        syncIndexedDB();
    };
};

// Fetch data from the server and store it in IndexedDB
const syncIndexedDB = async () => {
    const tables = ['Customer', 'Inspection_Header', 'Inspection_Details'];
    const baseUrl = getBaseUrl();

    for (const table of tables) {
        try {
            const response = await fetch(`${baseUrl}/sync/${table}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
            });

            if (!response.ok) {
                console.error(`Failed to fetch data for ${table}:`, response.statusText);
                continue;
            }

            const data = await response.json(); // List of dictionaries from the server
            storeDataInIndexedDB(table, data);
        } catch (error) {
            console.error(`Error syncing ${table}:`, error);
        }
    }
};

// Store data in the respective IndexedDB object store
const storeDataInIndexedDB = (storeName, data) => {
    if (!db) {
        console.error('Database is not open.');
        return;
    }

    const transaction = db.transaction(storeName, 'readwrite');
    const store = transaction.objectStore(storeName);

    data.forEach((item) => {
        store.put(item); // Add or update data in IndexedDB
    });

    transaction.oncomplete = () => {
        console.log(`${storeName} synced successfully.`);
    };

    transaction.onerror = (event) => {
        console.error(`Error storing data in ${storeName}:`, event.target.error);
    };
};

const getDataFromIndexedDB = (storeName) => {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);
        const request = store.getAll();

        request.onsuccess = (event) => {
            resolve(event.target.result);
        };

        request.onerror = (event) => {
            reject(`Error fetching data from ${storeName}: ${event.target.error}`);
        };
    });
};


// Sync IndexedDB with server
const sync_client_with_server = async () => {
    if (!db) {
        console.error('Database is not open.');
        return;
    }

    // Retrieve all tables in IndexedDB
    const tables = ['Customer', 'Inspection_Header', 'Inspection_Details'];
    const dataToSync = {};

    try {
        for (const table of tables) {
            const tableData = await getDataFromIndexedDB(table);

            // Safely encode Base64 fields if present in each record
            const encodedTableData = tableData.map(record => {
                if (record.image_url) {
                    // Encode the Base64 string safely
                    record.image_url = encodeURIComponent(record.image_url);
                }
                return record;
            });

            dataToSync[table] = encodedTableData;
        }

        console.log('Data to sync:', dataToSync);

        // Send data to Flask for processing
        const baseUrl = getBaseUrl();
        const response = await fetch(`${baseUrl}/sync/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(dataToSync),
        });

        if (response.ok) {
            const result = await response.json();
            console.log('Server response:', result);
            syncIndexedDB()
        } else {
            console.error('Failed to sync data with server:', response.statusText);
        }
    } catch (error) {
        console.error('Error during client-server sync:', error);
    }
};

openDB();

