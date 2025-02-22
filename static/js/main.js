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
            if (imageBlob) {
                // Generate a unique customer ID (auto-increment alternative)
                const customerId = crypto.randomUUID();
                record.customer_id = customerId; // Assign primary key

                // Store the image in the Images store
                const imageRecord = { blob: imageBlob, customer_id: customerId };
                const imageRequest = imagesStore.add(imageRecord);

                imageRequest.onsuccess = (event) => {
                    const imageId = event.target.result;
                    record.image_url = imageId; // Store image ID instead of full image

                    // Insert the record into the data store
                    const dataRequest = dataStore.add(record);
                    dataRequest.onsuccess = () => resolve();
                    dataRequest.onerror = (event) => reject(event.target.error);
                };

                imageRequest.onerror = (event) => reject(event.target.error);
            } else {
                // No image, just insert the record
                const dataRequest = dataStore.add(record);
                dataRequest.onsuccess = () => resolve();
                dataRequest.onerror = (event) => reject(event.target.error);
            }
        } catch (error) {
            transaction.abort();
            reject(`Transaction error: ${error}`);
        }
    });
};
const renderImage = (tableName, entityId, imgElementId) => {
    return new Promise((resolve, reject) => {
        if (!db) {
            reject("Database is not open.");
            return;
        }

        const transaction = db.transaction([tableName], "readonly");
        const store = transaction.objectStore(tableName);

        // Fetch the record using the primary key (entityId)
        const request = store.get(entityId);

        request.onsuccess = (event) => {
            const record = event.target.result;
            if (record && record.image_url) {
                // Fetch the actual image from the "Images" table using image_url (which stores image ID)
                const imageTransaction = db.transaction(["Images"], "readonly");
                const imageStore = imageTransaction.objectStore("Images");
                const imageRequest = imageStore.get(record.image_url);

                imageRequest.onsuccess = (imgEvent) => {
                    const imageRecord = imgEvent.target.result;
                    if (imageRecord && imageRecord.blob) {
                        // Convert Blob to an Object URL for displaying (Always JPG)
                        const blob = new Blob([imageRecord.blob], { type: "image/jpeg" });
                        const imageUrl = URL.createObjectURL(blob);

                        // Set the image source
                        const imgElement = document.getElementById(imgElementId);
                        if (imgElement) {
                            imgElement.src = imageUrl;
                            imgElement.style.display = "block"; // Ensure visibility
                        }

                        resolve(imageUrl);
                    } else {
                        reject(`Image not found for image_url: ${record.image_url}`);
                    }
                };

                imageRequest.onerror = (event) => reject(`Error fetching image: ${event.target.error}`);
            } else {
                reject(`No image_url found for entity ID: ${entityId}`);
            }
        };

        request.onerror = (event) => reject(`Error fetching record: ${event.target.error}`);
    });
};
