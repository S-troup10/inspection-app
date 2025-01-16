const generateTable = async (dbName, storeName, containerId, columns = [], query = null) => {
    const request = indexedDB.open(dbName);

    request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);

        // Fetch all records from the store
        const getAllRequest = store.getAll();
        getAllRequest.onsuccess = (event) => {
            let records = event.target.result;
            console.log(records)

            // If a query is provided, filter the records
            if (query) {
                records = records.filter(record => {
                    // Ensure the record contains the specified index and it matches the query value
                    const recordValue = record[query.index];
                    const queryValue = query.value;

                    // Ensure both values are treated as strings for comparison
                    if (recordValue !== undefined && String(recordValue) === String(queryValue)) {
                        return true; // Include the record
                    }
                    return false; // Discard the record if it doesn't match the query
                });
            }

            // If no records match the query or all records are empty
            if (records.length === 0) {
                //console.log(`No records found in ${storeName} for ${query ? `${query.index} = ${query.value}` : 'all records'}.`);
                const container = document.getElementById(containerId);
                container.innerHTML = '<p>No records found.</p>'; // Show feedback
                return;
            }

            // Generate the table with the filtered records
            createTable(records, columns, containerId);
        };

        getAllRequest.onerror = (event) => {
            console.error(`Error fetching all records from ${storeName}:`, event.target.error);
        };
    };

    request.onerror = (event) => {
        console.error(`Error opening database ${dbName}:`, event.target.error);
    };
};

const createTable = (records, columns, containerId) => {
    const table = document.createElement('table');
    table.id = `${containerId}Table`;
    table.classList.add('styled-table');

    // Create table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach((column) => {
        const th = document.createElement('th');
        th.textContent = column.charAt(0).toUpperCase() + column.slice(1); // Capitalize column names
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create table body
    const tbody = document.createElement('tbody');
    records.forEach((record) => {
        const row = document.createElement('tr');
        columns.forEach((col) => {
            const cell = document.createElement('td');
            const value = record[col] !== undefined ? record[col] : 'N/A';
            if (col === 'image_url' && value) {
                // Handle image URL as an image
                const img = document.createElement('img');
                img.src = value;
                img.alt = 'Image';
                img.style.width = '50px';
                img.style.height = '50px';
                img.style.objectFit = 'cover';
                cell.appendChild(img);
            } else {
                cell.textContent = value;
            }
            row.appendChild(cell);
        });
        tbody.appendChild(row);
    });

    table.appendChild(tbody);

    // Insert the table into the specified container
    const container = document.getElementById(containerId);
    container.innerHTML = ''; // Clear existing content
    container.appendChild(table);

    console.log(`Table for ${containerId} created successfully.`);
};

// Add default table styling
const addTableStyling = () => {
    const style = document.createElement('style');
    style.textContent = `
/* General Table Styling */
.styled-table {
    width: 100%; /* Make the table span the full width of the container */
    max-width: 100%; /* Ensure it doesn't exceed the container width */
    margin: 20px auto; /* Center the table vertically and horizontally with some margin */
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 14px;
}

.styled-table th, .styled-table td {
    padding: 15px; /* Increase padding for better readability */
    text-align: left;
    border-bottom: 1px solid #ddd;
    word-wrap: break-word; /* Ensure long text wraps properly */
}

.styled-table th {
    background-color: var(--secondary-color, #f2f2f2); /* Add a default light gray background if --secondary-color is not defined */
    font-size: 16px;
    font-weight: bold;
    text-align: center; /* Center-align headers for a cleaner look */
}

.styled-table tr:nth-child(even) {
    background-color: #fafafa; /* Use a subtle color for even rows */
}

.styled-table tr:hover {
    background-color: #f1f1f1; /* Highlight the row on hover */
}

.styled-table img {
    width: 50px;
    height: 50px;
    object-fit: cover;
    display: block;
    margin: auto;
}

/* Add some responsiveness */
@media (max-width: 768px) {
    .styled-table th, .styled-table td {
        font-size: 12px; /* Adjust font size for smaller screens */
        padding: 10px;
    }
}
    `;
    document.head.appendChild(style);
};

// Apply default table styling
addTableStyling();
