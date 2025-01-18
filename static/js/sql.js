

    let db;

    // Initialize the database with SQL.js
    async function initializeDB() {
        const SQL = await initSqlJs({ locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.0/${file}` });
        db = new SQL.Database();

        // Create tables if they don't exist
        createTables();

        // Load data from IndexedDB if available
        loadDatabaseFromIndexedDB();

        console.log('Database initialized.');
    }

    // Create tables in SQL.js if they don't exist
    function createTables() {
        db.run(`
            CREATE TABLE IF NOT EXISTS Customer (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                site TEXT,
                image_url TEXT DEFAULT NULL,
                last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        `);

        db.run(`
            CREATE TABLE IF NOT EXISTS Inspection_Header (
                inspection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                summary TEXT,
                customer_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                image_url TEXT DEFAULT NULL,
                title TEXT,
                last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
            )
        `);

        db.run(`
            CREATE TABLE IF NOT EXISTS Inspection_Details (
                detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id INTEGER NOT NULL,
                area TEXT,
                item TEXT,
                action_required TEXT,
                probability INTEGER,
                consequence INTEGER,
                time_ranking INTEGER,
                unit TEXT,
                observations TEXT,
                recommendations TEXT,
                picture_caption TEXT,
                display_on_report BOOLEAN,
                image_url TEXT DEFAULT NULL,
                last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inspection_id) REFERENCES Inspection_Header(inspection_id)
            )
        `);

        db.run(`
            CREATE TABLE IF NOT EXISTS Revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status TEXT,
                detail TEXT,
                issued_by TEXT,
                FOREIGN KEY (inspection_id) REFERENCES Inspection_Header(inspection_id)
            )
        `);
    }

    // Persist the database to IndexedDB
    function persistDatabase() {
        const binaryDb = db.export(); // Export the database to binary format

        // Save it to IndexedDB
        const request = indexedDB.open("sqljsDatabase", 1);
        request.onsuccess = function(event) {
            const db = event.target.result;
            const transaction = db.transaction("database", "readwrite");
            const objectStore = transaction.objectStore("database");
            objectStore.put(binaryDb, "myDatabase");
        };
        request.onerror = function(event) {
            console.error("Error storing the database in IndexedDB.", event);
        };
    }

    // Load the database from IndexedDB if it exists
    function loadDatabaseFromIndexedDB() {
        const request = indexedDB.open("sqljsDatabase", 1);

        request.onsuccess = function(event) {
            const db = event.target.result;
            const transaction = db.transaction("database", "readonly");
            const objectStore = transaction.objectStore("database");
            const getRequest = objectStore.get("myDatabase");

            getRequest.onsuccess = function(event) {
                const binaryDb = event.target.result;
                if (binaryDb) {
                    db = new SQL.Database(new Uint8Array(binaryDb));
                    console.log("Database loaded from IndexedDB.");
                }
            };
        };

        request.onerror = function(event) {
            console.error("Error loading the database from IndexedDB.", event);
        };
    }

    // Fetch local data from the SQL.js database
    async function fetchDataFromLocalDatabase(table) {
        const result = db.exec(`SELECT * FROM ${table}`);
        return result.length > 0 ? result[0].values : [];
    }

    // Store data in the local SQL.js database
    async function storeDataInLocalDatabase(table, data) {
        const insertStatements = data.map(item => {
            const columns = Object.keys(item).join(', ');
            const values = Object.values(item).map(value => `"${value}"`).join(', ');
            return `INSERT OR REPLACE INTO ${table} (${columns}) VALUES (${values})`;
        });

        insertStatements.forEach(statement => {
            db.run(statement);
        });
    }

    // Sync data to the server
    async function syncData() {
        const tables = ['Customer', 'Inspection_Header', 'Inspection_Details', 'Revisions'];

        for (const table of tables) {
            const localData = await fetchDataFromLocalDatabase(table);

            if (localData.length > 0) {
                try {
                    const response = await fetch(`/sync/${table}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(localData),
                    });

                    if (response.ok) {
                        console.log(`${table} synced successfully.`);
                    } else {
                        console.error(`Failed to sync ${table}.`);
                    }
                } catch (error) {
                    console.error(`Error syncing ${table}:`, error);
                }
            }
        }
    }

    // Fetch and store server data locally
    async function fetchAndStoreServerData() {
        const tables = ['Customer', 'Inspection_Header', 'Inspection_Details', 'Revisions'];

        for (const table of tables) {
            try {
                const response = await fetch(`/sync/${table}`);
                if (!response.ok) {
                    console.error(`Failed to fetch data for ${table}`);
                    continue;
                }

                const serverData = await response.json();
                await storeDataInLocalDatabase(table, serverData);
                console.log(`${table} data fetched and stored locally.`);
            } catch (error) {
                console.error(`Error fetching ${table}:`, error);
            }
        }
    }

    // Initialize the database and start syncing
    window.onload = async function () {
        await initializeDB(); // Initialize the database
        await fetchAndStoreServerData();  // Fetch data from the server and store it locally
        await syncData();  // Sync local changes to the server
    };

