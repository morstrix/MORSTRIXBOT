const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const BRUSH_SIZES = [4, 8, 12, 16, 24];
const ERASER_SIZES = [12, 20, 30, 40, 60];
const DEFAULT_BRUSH = 8;
const DEFAULT_ERASER = 20;
const MAX_LAYERS = 5;

// === СТАН ===
let canvas, ctx;
let layers = [];
let activeLayerIndex = 0;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen';
let currentSize = DEFAULT_BRUSH;
let lastX = 0, lastY = 0;
let undoStack = [];
let redoStack = [];
let layersPanelVisible = true; // ← НОВЕ: стан панелі

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('paint-canvas');
    ctx = canvas.getContext('2d');
    resizeCanvas();

    createLayer('Фон');
    setActiveLayer(0);

    loadArt();
    setupEvents();
    updateSizeDisplay();
    updateLayersUI();
    updateLayersPanelVisibility();

    if (WebApp) {
        WebApp.ready();
        WebApp.expand();
        WebApp.BackButton.show();
    }
}

function resizeCanvas() {
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.putImageData(imgData, 0, 0);

    layers.forEach(layer => {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = layer.canvas.width;
        tempCanvas.height = layer.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(layer.canvas, 0, 0);
        layer.canvas.width = canvas.width;
        layer.canvas.height = canvas.height;
        layer.ctx = layer.canvas.getContext('2d');
        layer.ctx.drawImage(tempCanvas, 0, 0, canvas.width, canvas.height);
    });
}

function createLayer(name = 'Шар') {
    if (layers.length >= MAX_LAYERS) return;

    const layerCanvas = document.createElement('canvas');
    layerCanvas.width = canvas.width;
    layerCanvas.height = canvas.height;
    const layerCtx = layerCanvas.getContext('2d');

    if (layers.length === 0) {
        layerCtx.fillStyle = '#222';
        layerCtx.fillRect(0, 0, layerCanvas.width, layerCanvas.height);
    }

    layers.push({
        canvas: layerCanvas,
        ctx: layerCtx,
        visible: true,
        name: `${name} ${layers.length + 1}`
    });

    updateLayersUI();
    renderAll();
}

function setActiveLayer(index) {
    if (index < 0 || index >= layers.length) return;
    activeLayerIndex = index;
    updateLayersUI();
}

function toggleLayerVisibility(index) {
    if (index >= 0 && index < layers.length) {
        layers[index].visible = !layers[index].visible;
        updateLayersUI();
        renderAll();
    }
}

function deleteLayer(index) {
    if (layers.length <= 1 || index < 0 || index >= layers.length) return;
    layers.splice(index, 1);
    if (activeLayerIndex >= layers.length) {
        activeLayerIndex = layers.length - 1;
    }
    updateLayersUI();
    renderAll();
}

function moveLayerUp(index) {
    if (index < layers.length - 1) {
        [layers[index], layers[index + 1]] = [layers[index + 1], layers[index]];
        if (activeLayerIndex === index) activeLayerIndex++;
        else if (activeLayerIndex === index + 1) activeLayerIndex--;
        updateLayersUI();
        renderAll();
    }
}

function moveLayerDown(index) {
    if (index > 0) {
        [layers[index], layers[index - 1]] = [layers[index - 1], layers[index]];
        if (activeLayerIndex === index) activeLayerIndex--;
        else if (activeLayerIndex === index - 1) activeLayerIndex++;
        updateLayersUI();
        renderAll();
    }
}

function getActiveLayer() {
    return layers[activeLayerIndex];
}

function renderAll() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    layers.forEach(layer => {
        if (layer.visible) {
            ctx.drawImage(layer.canvas, 0, 0);
        }
    });
}

// === ПОДІЇ ===
function setupEvents() {
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');
    document.getElementById('tool-clear').onclick = clearActiveLayer;
    document.getElementById('tool-undo').onclick = undo;
    document.getElementById('tool-redo').onclick = redo;
    document.getElementById('color-picker').addEventListener('input', changeColor);
    document.getElementById('size-minus').onclick = () => changeSize(-1);
    document.getElementById('size-plus').onclick = () => changeSize(1);
    document.getElementById('add-layer').onclick = () => createLayer();
    document.getElementById('toggle-layers').onclick = toggleLayersPanel; // ← НОВЕ

    canvas.addEventListener('pointerdown', startDrawing);
    canvas.addEventListener('pointermove', draw);
    canvas.addEventListener('pointerup', stopDrawing);
    canvas.addEventListener('pointerleave', stopDrawing);

    window.addEventListener('resize', () => {
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        resizeCanvas();
        ctx.putImageData(imgData, 0, 0);
        renderAll();
    });

    document.body.style.touchAction = 'none';
    canvas.style.touchAction = 'none';

    if (WebApp) {
        WebApp.onEvent('backButtonClicked', sendArtAndClose);
    }

    window.addEventListener('beforeunload', () => {
        if (WebApp && !WebApp.isClosing) {
            sendArtAndClose();
        }
    });
}

function toggleLayersPanel() {
    layersPanelVisible = !layersPanelVisible;
    updateLayersPanelVisibility();
}

function updateLayersPanelVisibility() {
    const panel = document.querySelector('.layers-panel');
    const toggleBtn = document.getElementById('toggle-layers');
    if (layersPanelVisible) {
        panel.style.transform = 'translateX(0)';
        toggleBtn.innerHTML = '◀';
    } else {
        panel.style.transform = 'translateX(100%)';
        toggleBtn.innerHTML = '▶';
    }
}

function sendArtAndClose() {
    saveArt();
    renderAll();
    const dataUrl = canvas.toDataURL('image/png');
    const payload = dataUrl.split(',')[1];
    const data = `ART|morstrix_art_${Date.now()}|${payload}`;
    WebApp.sendData(data);
    WebApp.close();
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('#tool-pen,#tool-eraser').forEach(b => b.classList.remove('active'));
    document.getElementById('tool-' + tool).classList.add('active');
    currentSize = currentTool === 'pen' ? DEFAULT_BRUSH : DEFAULT_ERASER;
    updateSizeDisplay();
}

function changeSize(delta) {
    const sizes = currentTool === 'pen' ? BRUSH_SIZES : ERASER_SIZES;
    const currentIndex = sizes.indexOf(currentSize);
    const newIndex = Math.max(0, Math.min(sizes.length - 1, currentIndex + delta));
    currentSize = sizes[newIndex];
    updateSizeDisplay();
}

function updateSizeDisplay() {
    const display = document.getElementById('size-value');
    display.textContent = currentSize;
    display.style.fontSize = `${Math.min(20, currentSize / 2)}px`;
}

function startDrawing(e) {
    e.preventDefault();
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    lastX = e.clientX - rect.left;
    lastY = e.clientY - rect.top;
    saveState();
}

function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const layer = getActiveLayer();
    const lctx = layer.ctx;

    if (currentTool === 'eraser') {
        lctx.globalCompositeOperation = 'destination-out';
    } else {
        lctx.globalCompositeOperation = 'source-over';
        lctx.strokeStyle = currentColor;
    }

    lctx.lineWidth = currentSize;
    lctx.lineCap = 'round';
    lctx.lineJoin = 'round';

    lctx.beginPath();
    lctx.moveTo(lastX, lastY);
    lctx.lineTo(x, y);
    lctx.stroke();

    lastX = x;
    lastY = y;

    renderAll();
}

function stopDrawing() {
    if (isDrawing) {
        isDrawing = false;
        saveState();
    }
}

function changeColor(e) {
    currentColor = e.target.value;
    if (currentTool === 'eraser') {
        setTool('pen');
    }
}

function saveState() {
    const layer = getActiveLayer();
    undoStack.push(layer.ctx.getImageData(0, 0, canvas.width, canvas.height));
    redoStack = [];
    updateUndoRedoButtons();
}

function undo() {
    if (undoStack.length > 1) {
        const layer = getActiveLayer();
        redoStack.push(undoStack.pop());
        layer.ctx.putImageData(undoStack[undoStack.length - 1], 0, 0);
        renderAll();
        updateUndoRedoButtons();
    }
}

function redo() {
    if (redoStack.length > 0) {
        const layer = getActiveLayer();
        const state = redoStack.pop();
        undoStack.push(state);
        layer.ctx.putImageData(state, 0, 0);
        renderAll();
        updateUndoRedoButtons();
    }
}

function updateUndoRedoButtons() {
    document.getElementById('tool-undo').disabled = undoStack.length <= 1;
    document.getElementById('tool-redo').disabled = redoStack.length === 0;
}

function clearActiveLayer() {
    const doClear = () => {
        saveState();
        const layer = getActiveLayer();
        layer.ctx.clearRect(0, 0, canvas.width, canvas.height);
        renderAll();
    };

    if (WebApp && WebApp.platform !== 'unknown') {
        WebApp.showConfirm('Очистити активний шар?', (isOk) => {
            if (isOk) doClear();
        });
    } else {
        if (confirm('Очистити активний шар?')) doClear();
    }
}

function updateLayersUI() {
    const container = document.getElementById('layers-list');
    container.innerHTML = '';

    layers.forEach((layer, i) => {
        const item = document.createElement('div');
        item.className = 'layer-item';
        if (i === activeLayerIndex) item.classList.add('active');

        const visibilityBtn = document.createElement('button');
        visibilityBtn.className = 'layer-btn';
        visibilityBtn.innerHTML = layer.visible ? '👁' : '👁‍🗨';
        visibilityBtn.onclick = () => toggleLayerVisibility(i);

        const nameSpan = document.createElement('span');
        nameSpan.textContent = layer.name;
        nameSpan.onclick = () => setActiveLayer(i);

        const controls = document.createElement('div');
        controls.className = 'layer-controls';

        const upBtn = document.createElement('button');
        upBtn.className = 'layer-btn';
        upBtn.innerHTML = '↑';
        upBtn.onclick = () => moveLayerUp(i);

        const downBtn = document.createElement('button');
        downBtn.className = 'layer-btn';
        downBtn.innerHTML = '↓';
        downBtn.onclick = () => moveLayerDown(i);

        const delBtn = document.createElement('button');
        delBtn.className = 'layer-btn';
        delBtn.innerHTML = '×';
        delBtn.onclick = () => deleteLayer(i);

        controls.appendChild(upBtn);
        controls.appendChild(downBtn);
        if (layers.length > 1) controls.appendChild(delBtn);

        item.appendChild(visibilityBtn);
        item.appendChild(nameSpan);
        item.appendChild(controls);
        container.appendChild(item);
    });
}

function saveArt() {
    const saved = layers.map(layer => ({
        dataUrl: layer.canvas.toDataURL('image/png'),
        visible: layer.visible,
        name: layer.name
    }));
    localStorage.setItem('morstrix_layers', JSON.stringify(saved));
}

function loadArt() {
    const saved = localStorage.getItem('morstrix_layers');
    if (saved) {
        const data = JSON.parse(saved);
        layers = [];
        data.forEach((item, i) => {
            createLayer(item.name.replace(/\s\d+$/, ''));
            const layer = layers[i];
            layer.visible = item.visible;
            const img = new Image();
            img.onload = () => {
                layer.ctx.drawImage(img, 0, 0);
                if (i === data.length - 1) {
                    setActiveLayer(0);
                    renderAll();
                }
            };
            img.src = item.dataUrl;
        });
    } else {
        saveState();
    }
}

window.addEventListener('load', init);