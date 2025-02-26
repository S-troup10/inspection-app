console.log('db.js ran');



const SUPABASE_URL = 'https://zmusspsqfcmjpqnwkpmx.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptdXNzcHNxZmNtanBxbndrcG14Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTUwNDcwNiwiZXhwIjoyMDU1MDgwNzA2fQ.Fl9y2FJhD09xBadglE9hzv5tFoGCxAU9_hRXZnePDg0';
const _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

let db;

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

        const customersStore = db.createObjectStore('Customer', { keyPath: 'customer_id', autoIncrement: true });
        customersStore.createIndex('name', 'name', { unique: false });

        const inspectionsStore = db.createObjectStore('Inspection_Header', { keyPath: 'inspection_id', autoIncrement: true });
        inspectionsStore.createIndex('customer_id', 'customer_id');

        const detailsStore = db.createObjectStore('Inspection_Details', { keyPath: 'detail_id', autoIncrement: true });
        detailsStore.createIndex('inspection_id', 'inspection_id', { unique: false });

        const imageStore = db.createObjectStore('Images', { keyPath: 'image_id', autoIncrement: true });
        imageStore.createIndex('image_id', 'image_id', { unique: false });

        console.log('Database structure initialized.');
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
            // Insert the customer record first
            const dataRequest = dataStore.add(record);
            dataRequest.onsuccess = (event) => {
                const customerId = event.target.result; // Get the auto-incremented ID
                console.log("Inserted customer with ID:", customerId);

                if (imageBlob) {
                    // Store the image with reference to customer_id
                    const imageRecord = { blob: imageBlob, customer_id: customerId };
                    const imageRequest = imagesStore.add(imageRecord);

                    imageRequest.onsuccess = (event) => {
                        const imageId = event.target.result; // Get the image ID
                        console.log("Inserted image with ID:", imageId);

                        // Now update the customer record with the image URL (imageId)
                        const updateTransaction = db.transaction(storeName, 'readwrite');
                        const updateStore = updateTransaction.objectStore(storeName);
                        const getCustomerRequest = updateStore.get(customerId);

                        getCustomerRequest.onsuccess = () => {
                            const customer = getCustomerRequest.result;
                            if (customer) {
                                customer.image_url = imageId; // Assign image ID as reference

                                const updateRequest = updateStore.put(customer);
                                updateRequest.onsuccess = () => {
                                    console.log("Updated customer with image_url:", imageId);
                                    resolve();
                                };
                                updateRequest.onerror = (event) => reject(event.target.error);
                            }
                        };

                        getCustomerRequest.onerror = (event) => reject(event.target.error);
                    };

                    imageRequest.onerror = (event) => reject(event.target.error);
                } else {
                    resolve(); // No image, just resolve
                }
            };

            dataRequest.onerror = (event) => reject(event.target.error);
        } catch (error) {
            transaction.abort();
            reject(`Transaction error: ${error}`);
        }
    });
};






const sync_client_with_server = async () => {
    if (!db) {
      console.error('Database is not open. Attempting to open it...');
      const request = indexedDB.open(dbName, 1);
      request.onsuccess = (event) => {
        db = event.target.result;
        console.log('Database opened successfully.');
        sync_client_with_server(); // Retry sync after opening DB
      };
      request.onerror = (event) => console.error('Failed to open database:', event);
      return;
    }
  
    // 1. Get data rows from the tables to sync
    const tables = ['Customer', 'Inspection_Header', 'Inspection_Details'];
    const dataToSync = {};
  
    for (const table of tables) {
      const tableData = await getDataFromIndexedDB(table);
      dataToSync[table] = tableData;
    }
  
    // 2. Handle image synchronization:
    //    Check the Images store for records whose image_url is still a local reference (e.g. a number).
    const imageData = await getDataFromIndexedDB('Images');
    console.log(imageData);
    const imageUploadPromises = [];
  
    // Loop through each table to check image_url
    for (const table in dataToSync) {
      const tableData = dataToSync[table];
      if (tableData && tableData.length > 0) {
        for (let row of tableData) {
          if (row.image_url && (typeof row.image_url === 'number' || !isNaN(row.image_url))) {
            console.log('Found image_url as number or placeholder in table:', table, 'Row ID:', row.id);
  
            // Find corresponding image in the Images store by image_id
            const imageRecord = imageData.find(img => img.image_id === row.image_url);
            console.log(imageRecord);
  
            if (imageRecord) {
              try {
                // Upload the image blob to Supabase Storage
                const imageUrl = await uploadImageToSupabase(imageRecord.blob, imageRecord.image_id);
                
                if (imageUrl) {
                  // Log that the image was successfully saved and the file name
                  console.log(`Photo saved successfully: ${imageRecord.image_id}. URL: ${imageUrl}`);
  
                  // Update the image_url in the data row with the Supabase URL
                  row.image_url = imageUrl;
                  
                  const parts = imageUrl.split('/');
                  const new_image_id = parts[parts.length - 1];

                  
                  
                  

  
                  // Remove the blob from the image record
                  //delete imageRecord.blob;
  
                  // Push a promise to update the image record in IndexedDB
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
  
      // Sync the data with Supabase
      await syncDataToServer(table, tableData);
    }
  
    // Wait for all image updates to finish
    await Promise.all(imageUploadPromises);
    console.log('Images synced to Supabase successfully.');
  
    console.log('Data synced to Supabase successfully.');
  };
  
  // Helper: Update an image record in the "Images" store in IndexedDB.
  const updateImageRecord = (imageRecord, image_id, image_url) => {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction('Images', 'readwrite');
      const store = transaction.objectStore('Images');
      imageRecord.image_id = image_id
      imageRecord.image_url = image_url
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
  
  
  // Helper: Sync data to Supabase using an upsert
  const syncDataToServer = async (table, data) => {
    try {
      const { error } = await _supabase.from(table).upsert(data);
      if (error) {
        console.error(`Error syncing data for table ${table}:`, error);
      } else {
        console.log(`${table} data synced successfully.`);
      }
    } catch (err) {
      console.error(`Failed to sync ${table} data:`, err);
    }
  };
  
  


const sync_server = async () => {
    if (!db) return console.error('Database is not open.');

    const tables = ['Customer', 'Inspection_Header', 'Inspection_Details'];
    const imageUploadPromises = [];  // Ensure this array is initialized to track image uploads

    for (const table of tables) {
        try {
            // Fetch data from Supabase
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
                    store.put(record); // Store record in IndexedDB

                    // Check if image_url exists and is a Supabase link
                    if (record.image_url && record.image_url.startsWith(SUPABASE_URL)) {
                        const imageId = record.image_url.split('/').pop();

                        // Check if the image is already cached
                        const imageRequest = imageStore.get(imageId);
                        imageRequest.onsuccess = async (event) => {
                            if (!event.target.result) {
                                try {
                                    // If not cached, download the image and store it
                                    const encodedImageId = encodeURIComponent(imageId);
                                    const { data: imageBlob, error: imgError } = await _supabase.storage.from('images').download(encodedImageId);

                                    if (!imgError && imageBlob) {
                                        const reader = new FileReader();
                                        reader.readAsArrayBuffer(imageBlob);

                                        reader.onloadend = () => {
                                            const imageBuffer = new Blob([reader.result], { type: 'image/jpeg' });

                                            // Open a new transaction to store the image
                                            const imageTransaction = db.transaction('Images', 'readwrite');
                                            const newImageStore = imageTransaction.objectStore('Images');
                                            newImageStore.put({ image_id: imageId, blob: imageBuffer, image_url: record.image_url });

                                            
                                        };
                                    } else {
                                        console.error(`Error downloading image ${imageId}:`, imgError);
                                    }
                                } catch (fetchError) {
                                    console.error(`Failed to cache image ${imageId}:`, fetchError);
                                }
                            }
                        };
                    }
                }
                console.log(`${table} synced from server.`);
            }
        } catch (err) {
            console.error(`Sync error for ${table}:`, err);
        }
    }

    // Ensure the image caching is completed before proceeding
    await Promise.all(imageUploadPromises);

    console.log('Server sync complete, images uploaded successfully.');

    // After everything is complete, trigger client sync
    sync_client_with_server();  // Call sync_client_with_server when everything is done
};




openDB();
