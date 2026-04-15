// ─── Helpers ────────────────────────────────────────────────────────────────

const _colLabel = (col) =>
    col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const _loadImage = (imageId, imgElement) => {
    let id = imageId;
    if (typeof id === 'string' && id.startsWith('https://')) {
        try { id = new URL(id).pathname.split('/').pop(); } catch (e) { return; }
    }
    if (!isNaN(id) && id !== '') id = parseInt(id);
    renderImage('Images', id, imgElement).catch(() => { imgElement.alt = 'No image'; });
};

// ─── Image loader from IndexedDB ─────────────────────────────────────────────

const renderImage = (storeName, imageId, imgElement) => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HV-storage');
        request.onsuccess = (event) => {
            const db = event.target.result;
            const store = db.transaction(storeName, 'readonly').objectStore(storeName);
            let lookupId = imageId;
            if (typeof lookupId === 'string' && lookupId.startsWith('https://')) {
                try { lookupId = new URL(lookupId).pathname.split('/').pop(); }
                catch (e) { return reject('Invalid URL'); }
            }
            if (!isNaN(lookupId) && lookupId !== '') lookupId = Number(lookupId);
            const req = store.get(lookupId);
            req.onsuccess = (e) => {
                const record = e.target.result;
                if (record && record.blob) {
                    const url = URL.createObjectURL(new Blob([record.blob], { type: 'image/jpeg' }));
                    imgElement.src = url;
                    resolve(url);
                } else {
                    reject(`No image for: ${lookupId}`);
                }
            };
            req.onerror = () => reject('IndexedDB read error');
        };
        request.onerror = () => reject('IndexedDB open error');
    });
};

// ─── Main entry point ─────────────────────────────────────────────────────────

const generateTable = (dbName, storeName, containerId, columns = [], query = null, onRowClick = null) => {
    const request = indexedDB.open(dbName);
    request.onsuccess = (event) => {
        const db = event.target.result;
        const store = db.transaction(storeName, 'readonly').objectStore(storeName);
        const getAllRequest = store.getAll();
        getAllRequest.onsuccess = (event) => {
            let records = event.target.result;
            if (query) {
                records = records.filter(r =>
                    r[query.index] !== undefined && String(r[query.index]) === String(query.value)
                );
            }
            const container = document.getElementById(containerId);
            if (records.length === 0) {
                container.innerHTML = '<p class="empty-msg">No records found.</p>';
                return;
            }
            _initToggle(records, columns, containerId, onRowClick);
        };
    };
};

// ─── Toggle UI ───────────────────────────────────────────────────────────────

const _initToggle = (records, columns, containerId, onRowClick) => {
    const container = document.getElementById(containerId);
    const parent = container.parentElement;

    // Remove existing toggle if re-rendered
    parent.querySelector('.view-toggle')?.remove();

    const toggle = document.createElement('div');
    toggle.classList.add('view-toggle');

    const tableBtn = document.createElement('button');
    tableBtn.classList.add('toggle-btn');
    tableBtn.innerHTML = '<i class="fas fa-table"></i> Table';

    const cardBtn = document.createElement('button');
    cardBtn.classList.add('toggle-btn');
    cardBtn.innerHTML = '<i class="fas fa-th-large"></i> Cards';

    toggle.appendChild(tableBtn);
    toggle.appendChild(cardBtn);
    parent.insertBefore(toggle, container);

    const switchView = (view) => {
        localStorage.setItem('preferred_view', view);
        tableBtn.classList.toggle('active', view === 'table');
        cardBtn.classList.toggle('active', view === 'card');
        if (view === 'table') {
            createTable(records, columns, containerId, onRowClick);
        } else {
            createCards(records, columns, containerId, onRowClick);
        }
    };

    tableBtn.onclick = () => switchView('table');
    cardBtn.onclick  = () => switchView('card');
    switchView(localStorage.getItem('preferred_view') || 'table');
};

// ─── Table view ───────────────────────────────────────────────────────────────

const createTable = (records, columns, containerId, onRowClick = null) => {
    const table = document.createElement('table');
    table.id = `${containerId}Table`;
    table.classList.add('styled-table');

    // Header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = _colLabel(col);
        headerRow.appendChild(th);
    });
    const actionTh = document.createElement('th');
    actionTh.textContent = 'Actions';
    headerRow.appendChild(actionTh);
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    records.forEach(record => {
        const row = document.createElement('tr');
        if (onRowClick) {
            row.classList.add('clickable-row');
            row.addEventListener('click', (e) => {
                if (!e.target.closest('button')) onRowClick(record);
            });
        }

        columns.forEach(col => {
            const cell = document.createElement('td');
            cell.setAttribute('data-label', _colLabel(col));
            if (col === 'image_url' && record.image_url) {
                const img = document.createElement('img');
                img.alt = 'Loading...';
                cell.appendChild(img);
                _loadImage(record.image_url, img);
            } else {
                cell.textContent = record[col] !== undefined ? record[col] : '—';
            }
            row.appendChild(cell);
        });

        const editCell = document.createElement('td');
        editCell.setAttribute('data-label', 'Actions');
        const editBtn = document.createElement('button');
        editBtn.textContent = 'Edit';
        editBtn.classList.add('edit-btn');
        editBtn.onclick = (e) => { e.stopPropagation(); editRecord(record); };
        editCell.appendChild(editBtn);
        row.appendChild(editCell);

        tbody.appendChild(row);
    });

    table.appendChild(tbody);

    const container = document.getElementById(containerId);
    container.innerHTML = '';
    container.appendChild(table);
};

// ─── Card view ────────────────────────────────────────────────────────────────

const createCards = (records, columns, containerId, onRowClick = null) => {
    const grid = document.createElement('div');
    grid.classList.add('card-grid');

    records.forEach(record => {
        const card = document.createElement('div');
        card.classList.add('record-card');
        if (onRowClick) {
            card.classList.add('clickable-card');
            card.addEventListener('click', (e) => {
                if (!e.target.closest('button')) onRowClick(record);
            });
        }

        // Image thumbnail
        if (columns.includes('image_url') && record.image_url) {
            const imgWrapper = document.createElement('div');
            imgWrapper.classList.add('card-img-wrapper');
            const img = document.createElement('img');
            img.alt = 'Loading...';
            imgWrapper.appendChild(img);
            card.appendChild(imgWrapper);
            _loadImage(record.image_url, img);
        }

        // Fields
        const fields = document.createElement('div');
        fields.classList.add('card-fields');
        columns.forEach(col => {
            if (col === 'image_url') return;
            const value = (record[col] !== undefined && record[col] !== '') ? record[col] : '—';
            const field = document.createElement('div');
            field.classList.add('card-field');
            const label = document.createElement('span');
            label.classList.add('card-label');
            label.textContent = _colLabel(col);
            const val = document.createElement('span');
            val.classList.add('card-value');
            val.textContent = value;
            field.appendChild(label);
            field.appendChild(val);
            fields.appendChild(field);
        });
        card.appendChild(fields);

        // Footer with edit button
        const footer = document.createElement('div');
        footer.classList.add('card-footer');
        const editBtn = document.createElement('button');
        editBtn.textContent = 'Edit';
        editBtn.classList.add('edit-btn');
        editBtn.onclick = (e) => { e.stopPropagation(); editRecord(record); };
        footer.appendChild(editBtn);
        card.appendChild(footer);

        grid.appendChild(card);
    });

    const container = document.getElementById(containerId);
    container.innerHTML = '';
    container.appendChild(grid);
};

// ─── Edit record ─────────────────────────────────────────────────────────────

const editRecord = (record) => {
    localStorage.setItem('edit_record', JSON.stringify(record));
    window.location.href = window.location.href + '/edit';
};
