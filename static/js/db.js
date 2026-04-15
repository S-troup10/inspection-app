const SUPABASE_URL = 'https://zmusspsqfcmjpqnwkpmx.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptdXNzcHNxZmNtanBxbndrcG14Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTUwNDcwNiwiZXhwIjoyMDU1MDgwNzA2fQ.Fl9y2FJhD09xBadglE9hzv5tFoGCxAU9_hRXZnePDg0';
const _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

let db;

const openDB = () => {
    const request = indexedDB.open('HV-storage', 1);

    request.onsuccess = (event) => {
        db = event.target.result;
    };

    request.onerror = (event) => {
        console.error('IndexedDB error:', event.target.error);
    };

    request.onupgradeneeded = (event) => {
        const db = event.target.result;

        const customersStore = db.createObjectStore('Customer', { keyPath: 'customer_id', autoIncrement: true });
        customersStore.createIndex('name', 'name', { unique: false });

        const inspectionsStore = db.createObjectStore('Inspection_Header', { keyPath: 'inspection_id', autoIncrement: true });
        inspectionsStore.createIndex('customer_id', 'customer_id');

        const detailsStore = db.createObjectStore('Inspection_Details', { keyPath: 'detail_id', autoIncrement: true });
        detailsStore.createIndex('inspection_id', 'inspection_id', { unique: false });

        const imageStore = db.createObjectStore('Images', { keyPath: 'image_id', autoIncrement: true });
        imageStore.createIndex('image_id', 'image_id', { unique: false });
    };
};

const getDataFromIndexedDB = (storeName) => {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);
        const request = store.getAll();
        request.onsuccess = (event) => resolve(event.target.result);
        request.onerror = (event) => reject(`Error fetching data from ${storeName}: ${event.target.error}`);
    });
};


const uploadImageToSupabase = async (imageBlob, imageId) => {
    const fileName = `image_${imageId}_${Date.now()}.jpg`;
    const { data, error } = await _supabase.storage.from('images').upload(fileName, imageBlob, { contentType: 'image/jpeg' });
    if (error) {
        console.error('Image upload error:', error);
        return null;
    }
    return `${SUPABASE_URL}/storage/v1/object/public/images/${fileName}`;
};


function renderImageByImageId(imageId, imgEl) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HV-storage', 1);

        request.onerror = (event) => {
            reject(`IndexedDB error: ${event.target.error}`);
        };

        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(['Images'], 'readonly');
            const store = transaction.objectStore('Images');
            const getRequest = store.get(imageId);

            getRequest.onerror = (e) => reject(e.target.error);

            getRequest.onsuccess = (e) => {
                const record = e.target.result;
                if (!record?.blob) {
                    reject('Image not found');
                    return;
                }
                const url = URL.createObjectURL(new Blob([record.blob], { type: 'image/jpeg' }));
                imgEl.src = url;
                imgEl.style.display = 'block';
                imgEl.onload = () => URL.revokeObjectURL(url);
                resolve(url);
            };
        };
    });
}

const insertDataWithImage = async (storeName, record, imageBlob) => {
    return new Promise((resolve, reject) => {
        if (!db) {
            reject('Database is not open.');
            return;
        }

        const transaction = db.transaction(['Images', storeName], 'readwrite');
        const imagesStore = transaction.objectStore('Images');
        const dataStore = transaction.objectStore(storeName);

        try {
            const dataRequest = dataStore.put(record);
            dataRequest.onsuccess = (event) => {
                const recordId = event.target.result;

                if (imageBlob) {
                    const imageRecord = { blob: imageBlob, customer_id: recordId };
                    const imageRequest = imagesStore.put(imageRecord);

                    imageRequest.onsuccess = (event) => {
                        const imageId = event.target.result;

                        const updateTransaction = db.transaction(storeName, 'readwrite');
                        const updateStore = updateTransaction.objectStore(storeName);
                        const getRequest = updateStore.get(recordId);

                        getRequest.onsuccess = () => {
                            const row = getRequest.result;
                            if (row) {
                                row.image_url = imageId;
                                const updateRequest = updateStore.put(row);
                                updateRequest.onsuccess = () => resolve();
                                updateRequest.onerror = (event) => reject(event.target.error);
                            }
                        };

                        getRequest.onerror = (event) => reject(event.target.error);
                    };

                    imageRequest.onerror = (event) => reject(event.target.error);
                } else {
                    resolve();
                }
            };

            dataRequest.onerror = (event) => reject(event.target.error);
        } catch (error) {
            transaction.abort();
            reject(`Transaction error: ${error}`);
        }
    });
};


const full_sync = async () => {
    await sync_client_with_server();
    await sync_server();
};


const sync_client_with_server = async () => {
    if (!db) {
        console.error('Database is not open. Attempting to open it...');
        const request = indexedDB.open(dbName, 1);
        request.onsuccess = (event) => {
            db = event.target.result;
            sync_client_with_server();
        };
        request.onerror = (event) => console.error('Failed to open database:', event);
        return;
    }

    const tables = ['Customer', 'Inspection_Header', 'Inspection_Details'];
    const dataToSync = {};

    for (const table of tables) {
        const tableData = await getDataFromIndexedDB(table);
        dataToSync[table] = tableData;
    }

    const imageData = await getDataFromIndexedDB('Images');
    const imageUploadPromises = [];

    for (const table in dataToSync) {
        const tableData = dataToSync[table];
        if (tableData && tableData.length > 0) {
            for (let row of tableData) {
                if (row.image_url && (typeof row.image_url === 'number' || !isNaN(row.image_url))) {
                    const imageRecord = imageData.find(img => img.image_id === row.image_url);

                    if (imageRecord) {
                        try {
                            const imageUrl = await uploadImageToSupabase(imageRecord.blob, imageRecord.image_id);

                            if (imageUrl) {
                                row.image_url = imageUrl;
                                const parts = imageUrl.split('/');
                                const new_image_id = parts[parts.length - 1];
                                imageUploadPromises.push(updateImageRecord(imageRecord, new_image_id, imageUrl));
                            }
                        } catch (error) {
                            console.error(`Failed to upload image (ID: ${imageRecord.image_id}):`, error);
                        }
                    } else {
                        console.error(`Image record for image_id ${row.image_url} not found in Images store.`);
                    }
                }
            }
        }

        await syncDataToServer(table, tableData);
    }

    await Promise.all(imageUploadPromises);
};

const updateImageRecord = (imageRecord, image_id, image_url) => {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction('Images', 'readwrite');
        const store = transaction.objectStore('Images');
        imageRecord.image_id = image_id;
        imageRecord.image_url = image_url;
        const request = store.put(imageRecord);

        request.onsuccess = () => resolve();
        request.onerror = (event) => reject(`Error updating image record: ${event.target.error}`);
    });
};

const updateRowInIndexedDB = (table, row) => {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(table, 'readwrite');
        const store = transaction.objectStore(table);
        const request = store.put(row);

        request.onsuccess = () => resolve();
        request.onerror = (event) => reject(`Error updating row in ${table}: ${event.target.error}`);
    });
};


const syncDataToServer = async (table, data) => {
    try {
        const { error } = await _supabase.from(table).upsert(data);
        if (error) {
            console.error(`Error syncing data for table ${table}:`, error);
        }
    } catch (err) {
        console.error(`Failed to sync ${table} data:`, err);
    }
};


const sync_server = async () => {
    if (!db) return console.error('Database is not open.');

    const tables = ['Customer', 'Inspection_Header', 'Inspection_Details'];
    const imageDownloadPromises = [];

    for (const table of tables) {
        try {
            let { data, error } = await _supabase.from(table).select('*');

            if (error) {
                console.error(`Error fetching ${table} from server:`, error);
                continue;
            }

            if (data.length > 0) {
                const transaction = db.transaction([table, 'Images'], 'readwrite');
                const store = transaction.objectStore(table);
                const imageStore = transaction.objectStore('Images');

                for (let record of data) {
                    store.put(record);

                    if (record.image_url && record.image_url.startsWith(SUPABASE_URL)) {
                        const imageId = record.image_url.split('/').pop();

                        const imagePromise = new Promise((resolve) => {
                            const imageRequest = imageStore.get(imageId);
                            imageRequest.onerror = () => resolve();
                            imageRequest.onsuccess = async (event) => {
                                if (!event.target.result) {
                                    try {
                                        const encodedImageId = encodeURIComponent(imageId);
                                        const { data: imageBlob, error: imgError } = await _supabase.storage
                                            .from('images')
                                            .download(encodedImageId);

                                        if (!imgError && imageBlob) {
                                            const reader = new FileReader();
                                            reader.readAsArrayBuffer(imageBlob);
                                            reader.onloadend = () => {
                                                const imageBuffer = new Blob([reader.result], { type: 'image/jpeg' });
                                                const imageTransaction = db.transaction('Images', 'readwrite');
                                                const newImageStore = imageTransaction.objectStore('Images');
                                                const putReq = newImageStore.put({ image_id: imageId, blob: imageBuffer, image_url: record.image_url });
                                                putReq.onsuccess = () => resolve();
                                                putReq.onerror = () => resolve();
                                            };
                                            reader.onerror = () => resolve();
                                        } else {
                                            console.error(`Error downloading image ${imageId}:`, imgError);
                                            resolve();
                                        }
                                    } catch (fetchError) {
                                        console.error(`Failed to cache image ${imageId}:`, fetchError);
                                        resolve();
                                    }
                                } else {
                                    resolve();
                                }
                            };
                        });

                        imageDownloadPromises.push(imagePromise);
                    }
                }
            }
        } catch (err) {
            console.error(`Sync error for ${table}:`, err);
        }
    }

    await Promise.all(imageDownloadPromises);
};


const deleteRecord = async (storeName, key) => {
    if (!db) {
        console.error('Database is not open.');
        return Promise.reject('Database is not open.');
    }

    try {
        const primaryKeyField = getPrimaryKeyField(storeName);

        const { data, error: fetchError } = await _supabase
            .from(storeName)
            .select(primaryKeyField)
            .eq(primaryKeyField, key)
            .single();

        if (fetchError && fetchError.code !== 'PGRST116') {
            console.error(`Error checking for record in Supabase (${storeName}):`, fetchError);
            throw new Error(`Failed to check for record in Supabase: ${fetchError.message}`);
        }

        if (data) {
            const { error: deleteError } = await _supabase
                .from(storeName)
                .delete()
                .eq(primaryKeyField, key);

            if (deleteError) {
                console.error(`Error deleting record from Supabase (${storeName}):`, deleteError);
                throw new Error(`Failed to delete record from Supabase: ${deleteError.message}`);
            }
        }

        await deleteRecordFromIndexedDB(storeName, key);

    } catch (error) {
        console.error(`Failed to delete record ${key} from ${storeName}:`, error);
        throw error;
    }
};

const getPrimaryKeyField = (storeName) => {
    const primaryKeys = {
        'Customer': 'customer_id',
        'Inspection_Header': 'inspection_id',
        'Inspection_Details': 'detail_id'
    };
    return primaryKeys[storeName] || 'id';
};

const deleteRecordFromIndexedDB = (storeName, key) => {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.delete(key);

        request.onsuccess = () => resolve();
        request.onerror = (event) => reject(`Error deleting from IndexedDB: ${event.target.error}`);
    });
};


openDB();
