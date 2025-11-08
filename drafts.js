const WebApp = window.Telegram.WebApp;
let currentCatalogId = null;
let currentItemId = null;
let dataStore = { catalogs: {} };
let canvas, ctx, colorPicker;
let pixelGrid = [];
let isDrawing = false;
let currentDrawColor = '#ffffff';
let currentTool = 'pen';
const GRID_DIMENSION = 16;
const CELL_SIZE = 15;
const CANVAS_WIDTH = GRID_DIMENSION * CELL_SIZE;
const CANVAS_HEIGHT = CANVAS_WIDTH;

// === ПОКАЗ В'ЮШОК ===
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

// === КАТАЛОГИ ===
function showCatalogList() {
    showView('catalog-list-view');
    renderCatalogs();
}

function showCatalogCreator() {
    showView('catalog-editor-view');
    document.getElementById('catalog-name-input').value = '';
    currentCatalogId = null; // Новий каталог
}

function saveCatalog() {
    const name = document.getElementById('catalog-name-input').value.trim();
    if (!name) return alert("Введіть назву каталогу");

    if (!currentCatalogId) {
        // Створення нового
        currentCatalogId = Date.now().toString();
        dataStore.catalogs[currentCatalogId] = { name, items: {} };
    } else {
        // Редагування
        dataStore.catalogs[currentCatalogId].name = name;
    }

    saveDataStore();
    showCatalogList();
}

function editCatalog(id) {
    currentCatalogId = id;
    const cat = dataStore.catalogs[id];
    document.getElementById('catalog-name-input').value = cat.name;
    showView('catalog-editor-view');
}

function deleteCatalog(id) {
    if (confirm("Видалити каталог і всі елементи?")) {
        delete dataStore.catalogs[id];
        saveDataStore();
        renderCatalogs();
    }
}

function renderCatalogs() {
    const container = document.getElementById('catalogs-container');
    container.innerHTML = '';
    for (const [id, cat] of Object.entries(dataStore.catalogs)) {
        const btn = document.createElement('button');
        btn.className = 'item-button';
        btn.innerHTML = `
            ${cat.name} 
            <span>${Object.keys(cat.items).length}</span>
            <small style="float:right; opacity:0.6; margin-left:5px;">✏️</small>
        `;
        btn.onclick = (e) => {
            if (e.target.tagName === 'SMALL') {
                editCatalog(id);
            } else {
                openCatalog(id);
            }
        };
        container.appendChild(btn);

        // Кнопка видалення
        const delBtn = document.createElement('button');
        delBtn.textContent = '🗑️';
        delBtn.style.cssText = 'float:right; background:none; border:none; font-size:12px; cursor:pointer;';
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteCatalog(id);
        };
        btn.appendChild(delBtn);
    }
}

function openCatalog(id) {
    currentCatalogId = id;
    showView('item-list-view');
    renderItems();
}

// === ЕЛЕМЕНТИ ===
function showItemCreator() {
    showView('item-creator-view');
}

function showItemList() {
    showView('item-list-view');
    renderItems();
}

function renderItems() {
    const container = document.getElementById('items-container');
    container.innerHTML = '';
    const items = dataStore.catalogs[currentCatalogId]?.items || {};
    for (const [id, item] of Object.entries(items)) {
        const btn = document.createElement('button');
        btn.className = 'item-button';
        btn.innerHTML = `${item.name} <span>${item.type}</span>`;
        btn.onclick = () => openItem(id);
        container.appendChild(btn);
    }
}

function openItem(id) {
    currentItemId = id;
    const item = dataStore.catalogs[currentCatalogId].items[id];
    if (item.type === 'note') showNoteEditor();
    else if (item.type === 'push') showPushEditor();
    else if (item.type === 'art') showArtEditor();
}

// === ЗАМІТКА ===
function showNoteEditor() {
    showView('note-editor-view');
    if (currentItemId) {
        const item = dataStore.catalogs[currentCatalogId].items[currentItemId];
        document.getElementById('note-name-input').value = item.name;
        document.getElementById('note-text-input').value = item.text || '';
    } else {
        document.getElementById('note-name-input').value = '';
        document.getElementById('note-text-input').value = '';
    }
}

function saveNote() {
    const name = document.getElementById('note-name-input').value.trim();
    const text = document.getElementById('note-text-input').value;
    if (!name) return alert("Введіть назву");
    
    if (!currentItemId) {
        currentItemId = Date.now().toString();
        dataStore.catalogs[currentCatalogId].items[currentItemId] = { type: 'note', name };
    }
    dataStore.catalogs[currentCatalogId].items[currentItemId].text = text;
    saveDataStore();
    showItemList();
}

// === НАГАДУВАННЯ ===
function showPushEditor() {
    showView('push-editor-view');
    if (currentItemId) {
        const item = dataStore.catalogs[currentCatalogId].items[currentItemId];
        document.getElementById('push-name-input').value = item.name;
        document.getElementById('push-datetime-input').value = item.datetime || '';
        document.getElementById('push-text-input').value = item.text || '';
    } else {
        document.getElementById('push-name-input').value = '';
        document.getElementById('push-datetime-input').value = '';
        document.getElementById('push-text-input').value = '';
    }
}

function savePush() {
    const name = document.getElementById('push-name-input').value.trim();
    const datetime = document.getElementById('push-datetime-input').value;
    const text = document.getElementById('push-text-input').value;
    if (!name || !datetime) return alert("Заповніть усі поля");
    
    if (!currentItemId) {
        currentItemId = Date.now().toString();
        dataStore.catalogs[currentCatalogId].items[currentItemId] = { type: 'push', name, datetime };
    }
    dataStore.catalogs[currentCatalogId].items[currentItemId].text = text;
    saveDataStore();

    const payload = JSON.stringify({ text, datetime });
    const data = `PUSH|${currentCatalogId}_${currentItemId}|${payload}`;
    if (WebApp) {
        WebApp.sendData(data);
        WebApp.close();
    }
    showItemList();
}

// === ПІКСЕЛЬ-АРТ ===
function showArtEditor() {
    showView('art-editor-view');
    initArtEditor();
    if (currentItemId) {
        document.getElementById('art-name-input').value = dataStore.catalogs[currentCatalogId].items[currentItemId].name;
        loadArt(currentItemId);
    } else {
        document.getElementById('art-name-input').value = '';
        initPixelGrid();
        redrawCanvas();
    }
}

function saveArtItem() {
    const name = document.getElementById('art-name-input').value.trim();
    if (!name) return alert("Введіть назву арту");
    
    if (!currentItemId) {
        currentItemId = Date.now().toString();
        dataStore.catalogs[currentCatalogId].items[currentItemId] = { type: 'art', name };
    } else {
        dataStore.catalogs[currentCatalogId].items[currentItemId].name = name;
    }
    saveArt(currentItemId);
    saveDataStore();
    alert("Арт збережено!");
}

function sendArt() {
    saveArtItem(); 
    if (!currentItemId) return alert("Спочатку збережіть арт.");
    const artData = localStorage.getItem(`morstrix_art_${currentItemId}`);
    if (!artData || artData === JSON.stringify(Array(GRID_DIMENSION).fill().map(() => Array(GRID_DIMENSION).fill(null))))) {
        return alert("Арт пустий.");
    }
    const data = `ART|${currentCatalogId}_${currentItemId}|${artData}`;
    if (WebApp) {
        WebApp.sendData(data);
        WebApp.close();
    } else {
        alert(`ART Data Sent (debug): ${data.substring(0, 100)}...`);
    }
}

function initArtEditor() {
    canvas = document.getElementById('pixel-canvas');
    ctx = canvas.getContext('2d');
    colorPicker = document.getElementById('color-picker');
    canvas.width = CANVAS_WIDTH;
    canvas.height = CANVAS_HEIGHT;
    
    initPixelGrid();
    redrawCanvas();

    // Очищаємо попередні обробники
    const newCanvas = canvas.cloneNode(true);
    canvas.parentNode.replaceChild(newCanvas, canvas);
    canvas = newCanvas;
    ctx = canvas.getContext('2d');

    canvas.addEventListener('mousedown', handlePointerStart);
    canvas.addEventListener('mousemove', handlePointerMove);
    document.addEventListener('mouseup', handlePointerEnd);
    canvas.addEventListener('touchstart', handlePointerStart, { passive: false });
    canvas.addEventListener('touchmove', handlePointerMove, { passive: false });
    canvas.addEventListener('touchend', handlePointerEnd);

    colorPicker.addEventListener('input', (e) => { 
        currentDrawColor = e.target.value; 
        if (currentTool === 'eraser') {
            currentTool = 'pen';
            document.getElementById('toggle-tool-btn').innerHTML = 'Ластик';
        }
    });
}

function initPixelGrid() {
    pixelGrid = Array(GRID_DIMENSION).fill().map(() => Array(GRID_DIMENSION).fill(null));
}

function redrawCanvas() {
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    ctx.imageSmoothingEnabled = false;

    for (let y = 0; y < GRID_DIMENSION; y++) {
        for (let x = 0; x < GRID_DIMENSION; x++) {
            const color = pixelGrid[y][x];
            if (color) {
                ctx.fillStyle = color;
                ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            }
        }
    }

    ctx.strokeStyle = '#2d2d2d';
    ctx.lineWidth = 1;
    for (let i = 0; i <= GRID_DIMENSION; i++) {
        ctx.beginPath();
        ctx.moveTo(i * CELL_SIZE, 0);
        ctx.lineTo(i * CELL_SIZE, CANVAS_HEIGHT);
        ctx.moveTo(0, i * CELL_SIZE);
        ctx.lineTo(CANVAS_WIDTH, i * CELL_SIZE);
        ctx.stroke();
    }
}

function drawSinglePixel(x, y) {
    if (x < 0 || x >= GRID_DIMENSION || y < 0 || y >= GRID_DIMENSION) return;
    
    const color = currentTool === 'pen' ? currentDrawColor : null;
    const changed = pixelGrid[y][x] !== color;
    pixelGrid[y][x] = color;

    if (changed) {
        ctx.fillStyle = color || '#222222';
        ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        ctx.strokeStyle = '#2d2d2d';
        ctx.lineWidth = 1;
        ctx.strokeRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
    }
}

function getMousePos(event) {
    const rect = canvas.getBoundingClientRect();
    const clientX = event.touches ? event.touches[0].clientX : event.clientX;
    const clientY = event.touches ? event.touches[0].clientY : event.clientY;
    const x = Math.floor((clientX - rect.left) / CELL_SIZE);
    const y = Math.floor((clientY - rect.top) / CELL_SIZE);
    return { x, y };
}

function handlePointerStart(event) {
    event.preventDefault();
    isDrawing = true;
    const pos = getMousePos(event);
    drawSinglePixel(pos.x, pos.y);
}

function handlePointerMove(event) {
    if (!isDrawing) return;
    event.preventDefault();
    const pos = getMousePos(event);
    drawSinglePixel(pos.x, pos.y);
}

function handlePointerEnd() {
    if (!isDrawing) return;
    isDrawing = false;
    saveArt(currentItemId);
}

function toggleTool() {
    currentTool = currentTool === 'pen' ? 'eraser' : 'pen';
    document.getElementById('toggle-tool-btn').innerHTML = currentTool === 'pen' ? 'Ластик' : 'Кисть';
}

function saveArt(key) {
    if (key) {
        localStorage.setItem(`morstrix_art_${key}`, JSON.stringify(pixelGrid));
    }
}

function loadArt(key) {
    if (!key) return initPixelGrid();
    const saved = localStorage.getItem(`morstrix_art_${key}`);
    if (saved) {
        try {
            pixelGrid = JSON.parse(saved);
        } catch (e) {
            console.error("Помилка парсингу арту:", e);
            initPixelGrid();
        }
    } else {
        initPixelGrid();
    }
    redrawCanvas();
}

// === ЗБЕРЕЖЕННЯ ===
function saveDataStore() {
    localStorage.setItem('morstrix_drafts', JSON.stringify(dataStore));
}

function loadDataStore() {
    const saved = localStorage.getItem('morstrix_drafts');
    if (saved) {
        try {
            dataStore = JSON.parse(saved);
        } catch (e) {
            console.error("Помилка парсингу dataStore:", e);
            dataStore = { catalogs: {} };
        }
    }
}

// === ІНІЦІАЛІЗАЦІЯ ===
function initApp() {
    loadDataStore();
    showCatalogList();
}

window.addEventListener('load', initApp);