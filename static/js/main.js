
let db;

// Open IndexedDB
const openDB = () => {
    const request = indexedDB.open('hvEngineersDB', 1);
    request.onsuccess = (event) => {
        db = event.target.result;
        console.log('IndexedDB opened successfully');
    };

    request.onerror = (event) => {
        console.error('IndexedDB error:', event.target.error);
    };

    request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create object stores for each table (Customer, Inspection_Header, Inspection_Details, Revisions)
        const customersStore = db.createObjectStore('customers', { keyPath: 'customer_id', autoIncrement: true });
        customersStore.createIndex('name', 'name', { unique: true });

        const inspectionsStore = db.createObjectStore('inspection_headers', { keyPath: 'inspection_id', autoIncrement: true });
        inspectionsStore.createIndex('customer_id', 'customer_id'); // Foreign key to Customer

        const detailsStore = db.createObjectStore('inspection_details', { keyPath: 'detail_id', autoIncrement: true });
        detailsStore.createIndex('inspection_id', 'inspection_id'); // Foreign key to Inspection_Header

        const revisionsStore = db.createObjectStore('revisions', { keyPath: 'id', autoIncrement: true });
        revisionsStore.createIndex('inspection_id', 'inspection_id'); // Foreign key to Inspection_Header
    };

    
};


const populateCustomerTable = () => {
    const transaction = db.transaction(['customers'], 'readonly');
    const store = transaction.objectStore('customers');
    const request = store.getAll(); // Retrieve all customers
    
    request.onsuccess = (event) => {
        const customers = event.target.result;
        const tableBody = document.getElementById('customer-table-body');
        
        // Clear the table before populating
        tableBody.innerHTML = '';

        if (customers.length === 0) {
            // Show "No customers found" if the table is empty
            document.getElementById('no-customers-message').style.display = 'block';
        } else {
            // Hide the "No customers found" message if there are customers
            document.getElementById('no-customers-message').style.display = 'none';
            customers.forEach((customer) => {
                // Create table row for each customer
                const row = document.createElement('tr');
                
                // Logo column (Add your image source logic here if applicable)
                const logoCell = document.createElement('td');
                logoCell.textContent = 'Logo'; // Replace with your image source logic
                row.appendChild(logoCell);
                
                // Name column
                const nameCell = document.createElement('td');
                nameCell.textContent = customer.name; // Replace with actual customer name property
                row.appendChild(nameCell);
                
                // Site column
                const siteCell = document.createElement('td');
                siteCell.textContent = customer.site || 'N/A'; // Replace with actual site property
                row.appendChild(siteCell);
                
                // Edit button column
                const editCell = document.createElement('td');
                const editButton = document.createElement('a');
                editButton.href = `/edit-customer/${customer.customer_id}`; // Modify as needed
                editButton.textContent = 'Edit';
                editCell.appendChild(editButton);
                row.appendChild(editCell);
                
                // Append row to table body
                tableBody.appendChild(row);
            });
        }
    };
    
    request.onerror = (event) => {
        console.error('Error retrieving customers:', event.target.error);
    };
};




//insert

// Function to save customer data with last_modified timestamp
const saveCustomer = (customerData) => {
    // Get the image file from the form
    const imageInput = document.getElementById('customer-image');
    const imageFile = imageInput.files[0];

    if (!imageFile) {
        console.error('No image file provided.');
        return;
    }

    // Set the last_modified field to the current timestamp before saving
    customerData.last_modified = new Date().toISOString();

    // Handle image caching and saving
    const reader = new FileReader();
    reader.onloadend = () => {
        // Image is loaded, now we can store it in the cache
        const imageBlob = reader.result; // The binary image data

        // Save the image to the cache (for offline usage)
        caches.open('customer-images').then((cache) => {
            const imageURL = URL.createObjectURL(imageBlob); // Create a URL for the image

            // Add the image to cache
            cache.put(imageURL, new Response(imageBlob)).then(() => {
                console.log('Image saved to cache');
                
                // Now we can store the customer data with the image URL
                customerData.imagePath = imageURL; // Store the image URL/path in the customer data

                // Open IndexedDB and save customer data
                const transaction = db.transaction(['customers'], 'readwrite');
                const store = transaction.objectStore('customers');
                store.add(customerData);  // Add the record, will automatically generate a new customer_id
                transaction.oncomplete = () => console.log('Customer saved successfully');
                transaction.onerror = (event) => console.error('Error saving customer:', event.target.error);
            }).catch((err) => {
                console.error('Failed to cache image:', err);
            });
        });
    };

    reader.onerror = (err) => {
        console.error('Error reading image file:', err);
    };

    // Read the image file as a binary string (could also use DataURL or Blob URL)
    reader.readAsArrayBuffer(imageFile);
};


// Function to save inspection header data with last_modified timestamp
const saveInspectionHeader = (inspectionData) => {
    // Set the last_modified field to the current timestamp before saving
    inspectionData.last_modified = new Date().toISOString();

    const transaction = db.transaction(['inspection_headers'], 'readwrite');
    const store = transaction.objectStore('inspection_headers');
    
    store.add(inspectionData);  // Add the record, will automatically generate a new inspection_id
    transaction.oncomplete = () => console.log('Inspection Header saved successfully');
    transaction.onerror = (event) => console.error('Error saving inspection header:', event.target.error);
};

// Function to save inspection details data with last_modified timestamp
const saveInspectionDetails = (inspectionDetails) => {
    // Set the last_modified field to the current timestamp before saving
    inspectionDetails.last_modified = new Date().toISOString();

    const transaction = db.transaction(['inspection_details'], 'readwrite');
    const store = transaction.objectStore('inspection_details');
    
    store.add(inspectionDetails);  // Add the record, will automatically generate a new detail_id
    transaction.oncomplete = () => console.log('Inspection Details saved successfully');
    transaction.onerror = (event) => console.error('Error saving inspection details:', event.target.error);
};

// Function to save revision data with last_modified timestamp
const saveRevision = (revisionData) => {
    // Set the last_modified field to the current timestamp before saving
    revisionData.date = new Date().toISOString(); // Assuming 'date' is the timestamp for revisions

    const transaction = db.transaction(['revisions'], 'readwrite');
    const store = transaction.objectStore('revisions');
    
    store.add(revisionData);  // Add the record, will automatically generate a new id
    transaction.oncomplete = () => console.log('Revision saved successfully');
    transaction.onerror = (event) => console.error('Error saving revision:', event.target.error);
};


// fetch section

// Function to retrieve customers
const getCustomers = () => {
    const transaction = db.transaction(['customers'], 'readonly');
    const store = transaction.objectStore('customers');
    const request = store.getAll(); // Retrieve all customers
    request.onsuccess = (event) => {
        console.log('Customers retrieved:', event.target.result);
    };
    request.onerror = (event) => console.error('Error retrieving customers:', event.target.error);
};

const getInspections = () => {
    const transaction = db.transaction(['inspections'], 'readonly');
    const store = transaction.objectStore('inspections');
    const request = store.getAll(); 
    request.onsuccess = (event) => {
        console.log('inspections retrieved:', event.target.result);
    };
    request.onerror = (event) => console.error('Error retrieving inspections:', event.target.error);
};

// Function to retrieve inspections by customer ID
const getInspectionsByCustomerId = (customerId) => {
    const transaction = db.transaction(['inspection_headers'], 'readonly');
    const store = transaction.objectStore('inspection_headers');
    const index = store.index('customer_id');
    const request = index.getAll(customerId); // Get all inspections for the customer
    request.onsuccess = (event) => {
        console.log('Inspections for customer:', event.target.result);
    };
    request.onerror = (event) => console.error('Error retrieving inspections:', event.target.error);
};

// Function to retrieve inspection details by inspection ID
const getInspectionDetailsByInspectionId = (inspectionId) => {
    const transaction = db.transaction(['inspection_details'], 'readonly');
    const store = transaction.objectStore('inspection_details');
    const index = store.index('inspection_id');
    const request = index.getAll(inspectionId); // Get all details for the inspection
    request.onsuccess = (event) => {
        console.log('Inspection details for inspection:', event.target.result);
    };
    request.onerror = (event) => console.error('Error retrieving inspection details:', event.target.error);
};

// Function to retrieve revisions by inspection ID
const getRevisionsByInspectionId = (inspectionId) => {
    const transaction = db.transaction(['revisions'], 'readonly');
    const store = transaction.objectStore('revisions');
    const index = store.index('inspection_id');
    const request = index.getAll(inspectionId); // Get all revisions for the inspection
    request.onsuccess = (event) => {
        console.log('Revisions for inspection:', event.target.result);
    };
    request.onerror = (event) => console.error('Error retrieving revisions:', event.target.error);
};

/// update section


// Function to update customer data
const updateCustomer = (customerData) => {
    const transaction = db.transaction(['customers'], 'readwrite');
    const store = transaction.objectStore('customers');
    
    // Ensure that we update the record with the matching primary key (customer_id)
    store.put(customerData);  // put will update if the record already exists
    transaction.oncomplete = () => console.log('Customer updated successfully');
    transaction.onerror = (event) => console.error('Error updating customer:', event.target.error);
};

// Function to update inspection header data
const updateInspectionHeader = (inspectionData) => {
    const transaction = db.transaction(['inspection_headers'], 'readwrite');
    const store = transaction.objectStore('inspection_headers');
    
    store.put(inspectionData);  // put will update if the record already exists
    transaction.oncomplete = () => console.log('Inspection Header updated successfully');
    transaction.onerror = (event) => console.error('Error updating inspection header:', event.target.error);
};

// Function to update inspection details data
const updateInspectionDetails = (inspectionDetails) => {
    const transaction = db.transaction(['inspection_details'], 'readwrite');
    const store = transaction.objectStore('inspection_details');
    
    store.put(inspectionDetails);  // put will update if the record already exists
    transaction.oncomplete = () => console.log('Inspection Details updated successfully');
    transaction.onerror = (event) => console.error('Error updating inspection details:', event.target.error);
};

// Function to update revision data
const updateRevision = (revisionData) => {
    const transaction = db.transaction(['revisions'], 'readwrite');
    const store = transaction.objectStore('revisions');
    
    store.put(revisionData);  // put will update if the record already exists
    transaction.oncomplete = () => console.log('Revision updated successfully');
    transaction.onerror = (event) => console.error('Error updating revision:', event.target.error);
};





// Sync data with the server when back online
const syncDataToServer = () => {
    // Retrieve all data from IndexedDB
    const currentTime = new Date().toISOString();
    
    // Filter data that has been modified since the last sync
    const updatedCustomers = allCustomersData.filter(customer => new Date(customer.last_modified) > lastSyncTime);
    const updatedInspections = allInspectionsData.filter(inspection => new Date(inspection.last_modified) > lastSyncTime);
    const updatedInspectionDetails = allInspectionDetailsData.filter(detail => new Date(detail.last_modified) > lastSyncTime);
    const updatedRevisions = allRevisionsData.filter(revision => new Date(revision.date) > lastSyncTime);


    // Assuming that the data has been populated into the arrays by the above functions:
    fetch('/api/syncData', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            customers: updatedCustomers,
            inspections: updatedInspections,
            inspectionDetails: updatedInspectionDetails,
            revisions: updatedRevisions,
        }),
    })
    .then(response => response.json())
    .then(data => console.log('Sync successful:', data))
    .catch(error => console.error('Sync failed:', error));
};

// Initialize IndexedDB when app starts
openDB();
