// Function to render an image from IndexedDB
const renderImage = (storeName, imageId, imgElement) => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HV-storage');

        request.onsuccess = (event) => {
            const db = event.target.result;
            const transaction = db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);

            let lookupId = imageId;

            // If it's a Supabase URL, extract the filename
            if (typeof imageId === "string" && imageId.startsWith("https://")) {
                try {
                    const url = new URL(imageId);
                    lookupId = url.pathname.split("/").pop(); // Extract filename
                } catch (error) {
                    console.error("Invalid URL format:", imageId);
                    return reject("Invalid Supabase URL.");
                }
            } 

            // Convert to number only if it's numeric
            if (!isNaN(lookupId) && lookupId !== "") {
                lookupId = Number(lookupId);
            }

            const getRequest = store.get(lookupId);

            getRequest.onsuccess = (event) => {
                const record = event.target.result;
                if (record && record.blob) {
                    const blob = new Blob([record.blob], { type: 'image/jpeg' });
                    const imageUrl = URL.createObjectURL(blob);
                    imgElement.src = imageUrl;
                    resolve(imageUrl);
                } else {
                    reject(`No image found for image_id: ${lookupId}`);
                }
            };

            getRequest.onerror = () => reject('Error fetching image from IndexedDB.');
        };

        request.onerror = () => reject('Error opening IndexedDB.');
    });
};

// Function to generate a table
const generateTable = async (dbName, storeName, containerId, columns = [], query = null) => {
    const request = indexedDB.open(dbName);

    request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);

        const getAllRequest = store.getAll();
        getAllRequest.onsuccess = (event) => {
            let records = event.target.result;
            console.log(records);

            if (query) {
                records = records.filter(record => {
                    const recordValue = record[query.index];
                    const queryValue = query.value;
                    return recordValue !== undefined && String(recordValue) === String(queryValue);
                });
            }

            if (records.length === 0) {
                const container = document.getElementById(containerId);
                container.innerHTML = '<p>No records found.</p>';
                return;
            }

            createTable(records, columns, containerId);
        };
    };
};

// Function to create the table
const createTable = (records, columns, containerId) => {
    const table = document.createElement('table');
    table.id = `${containerId}Table`;
    table.classList.add('styled-table');

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach((column) => {
        const th = document.createElement('th');
        th.textContent = column.charAt(0).toUpperCase() + column.slice(1);
        headerRow.appendChild(th);
    });

    const editTh = document.createElement('th');
    editTh.textContent = 'Actions';
    headerRow.appendChild(editTh);
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    records.forEach((record) => {
        const row = document.createElement('tr');
        columns.forEach((col) => {
            const cell = document.createElement('td');

            if (col === "image_url" && record.image_url) {  
                const img = document.createElement('img');
                img.alt = 'Loading image...';
                img.style.width = '50px';
                img.style.height = '50px';
                img.style.objectFit = 'cover';
                cell.appendChild(img);
            
                let imageId = record.image_url;
            
                // Check if it's a Supabase URL and extract the filename
                if (typeof imageId === "string" && imageId.startsWith("https://")) {
                    try {
                        const url = new URL(imageId);
                        imageId = url.pathname.split("/").pop(); // Extract filename
                    } catch (error) {
                        console.error("Invalid Supabase URL:", imageId);
                        img.alt = "Invalid URL";
                        return;
                    }
                } 
            
                // If it's a number, convert it to an integer
                if (!isNaN(imageId) && imageId !== "") {
                    imageId = parseInt(imageId);
                }
            
                // Fetch image from IndexedDB
                renderImage("Images", imageId, img)
                    .then((imageUrl) => {
                        img.src = imageUrl;
                    })
                    .catch((error) => {
                        console.error(error);
                        img.alt = "No image found";
                    });
            
            } else {
                cell.textContent = record[col] !== undefined ? record[col] : 'N/A';
            }
            row.appendChild(cell);
        });

        const editCell = document.createElement('td');
        const editButton = document.createElement('button');
        editButton.textContent = 'Edit';
        editButton.classList.add('edit-btn');
        editButton.onclick = (event) => {
            event.stopPropagation();
            editRecord(record);
        };
        editCell.appendChild(editButton);
        row.appendChild(editCell);

        tbody.appendChild(row);
    });

    table.appendChild(tbody);

    const container = document.getElementById(containerId);
    container.innerHTML = '';
    container.appendChild(table);
};

// Function to edit a record
const editRecord = (record) => {
    // Store the record in localStorage
    localStorage.setItem('edit_record', JSON.stringify(record));

    // Redirect to the current URL with '/edit' appended to it
    window.location.href = window.location.href + '/edit';
};

// Function to add table styling
const addTableStyling = () => {
    const style = document.createElement('style');
    style.textContent = `
    .styled-table {
        width: 100%;
        max-width: 100%;
        margin: 20px auto;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 14px;
    }

    .styled-table th, .styled-table td {
        padding: 15px;
        text-align: left;
        border-bottom: 1px solid #ddd;
        word-wrap: break-word;
    }

    .styled-table th {
        background-color: var(--secondary-color, #f2f2f2);
        font-size: 16px;
        font-weight: bold;
        text-align: center;
    }

    .styled-table tr:nth-child(even) {
        background-color: #fafafa;
    }

    .styled-table tr:hover {
        background-color: #f1f1f1;
    }

    .styled-table img {
        width: 50px;
        height: 50px;
        object-fit: cover;
        display: block;
        margin: auto;
    }

    @media (max-width: 768px) {
        .styled-table th, .styled-table td {
            font-size: 12px;
            padding: 10px;
        }
    }
    `;
    document.head.appendChild(style);
};

// Apply default table styling
addTableStyling();
