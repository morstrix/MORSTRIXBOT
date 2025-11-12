const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const BRUSH_SIZES = [4, 8, 12, 16, 24];
const ERASER_SIZES = [12, 20, 30, 40, 60];
const DEFAULT_BRUSH = 8;
const DEFAULT_ERASER = 20;

// === СТАН ===
let canvas, ctx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen';
let currentSize = DEFAULT_BRUSH;
let lastX = 0, lastY = 0;
let undoStack = [];
let redoStack = [];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('paint-canvas');
    ctx = canvas.getContext('2d');
    resizeCanvas();

    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    loadArt();
    setupEvents();
    updateSizeDisplay();

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
}

function setupEvents() {
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');
    document.getElementById('tool-clear').onclick = clearAll;
    document.getElementById('tool-undo').onclick = undo;
    document.getElementById('tool-redo').onclick = redo;
    document.getElementById('color-picker').addEventListener('input', changeColor);

    document.getElementById('size-minus').onclick = () => changeSize(-1);
    document.getElementById('size-plus').onclick = () => changeSize(1);

    canvas.addEventListener('pointerdown', startDrawing);
    canvas.addEventListener('pointermove', draw);
    canvas.addEventListener('pointerup', stopDrawing);
    canvas.addEventListener('pointerleave', stopDrawing);

    window.addEventListener('resize', () => {
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        resizeCanvas();
        ctx.putImageData(imgData, 0, 0);
    });

    document.body.style.touchAction = 'none';
    canvas.style.touchAction = 'none';

    // Автозакриття при натисканні "Назад"
    if (WebApp) {
        WebApp.onEvent('backButtonClicked', () => {
            sendArtAndClose();
        });
    }

    // Автозакриття при закритті вікна
    window.addEventListener('beforeunload', () => {
        if (WebApp && !WebApp.isClosing) {
            sendArtAndClose();
        }
    });
}

function sendArtAndClose() {
    saveArt();
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

    if (currentTool === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
    } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = currentColor;
    }

    ctx.lineWidth = currentSize;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(x, y);
    ctx.stroke();

    lastX = x;
    lastY = y;
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
    undoStack.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    redoStack = [];
    updateUndoRedoButtons();
}

function undo() {
    if (undoStack.length > 1) {
        redoStack.push(undoStack.pop());
        ctx.putImageData(undoStack[undoStack.length - 1], 0, 0);
        updateUndoRedoButtons();
    }
}

function redo() {
    if (redoStack.length > 0) {
        const state = redoStack.pop();
        undoStack.push(state);
        ctx.putImageData(state, 0, 0);
        updateUndoRedoButtons();
    }
}

function updateUndoRedoButtons() {
    document.getElementById('tool-undo').disabled = undoStack.length <= 1;
    document.getElementById('tool-redo').disabled = redoStack.length === 0;
}

function clearAll() {
    const doClear = () => {
        saveState();
        ctx.fillStyle = '#222';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    };

    if (WebApp && WebApp.platform !== 'unknown') {
        WebApp.showConfirm('Очистити все? Дію можна скасувати (Undo).', (isOk) => {
            if (isOk) doClear();
        });
    } else {
        if (confirm('Очистити все?')) doClear();
    }
}

function saveArt() {
    const dataUrl = canvas.toDataURL('image/png');
    localStorage.setItem('morstrix_draw', dataUrl);
}

function loadArt() {
    const saved = localStorage.getItem('morstrix_draw');
    if (saved) {
        const img = new Image();
        img.onload = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#222';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            saveState();
        };
        img.src = saved;
    } else {
        saveState();
    }
}

window.addEventListener('load', init);