const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const BRUSH_SIZE = 6;   // маленька кисть
const ERASER_SIZE = 20;

// ❌ КОНСТАНТА COLORS (ВИДАЛЕНО), ТЕПЕР ВИКОРИСТОВУЄТЬСЯ <input type="color">
// const COLORS = [ ... ];

// === СТАН ===
let canvas, ctx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen';
let lastX = 0, lastY = 0;

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('paint-canvas');
    ctx = canvas.getContext('2d');
    resizeCanvas();

    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    loadArt();
    setupEvents();
    // ❌ ВИДАЛЕНО buildPalette();
}

function resizeCanvas() {
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.putImageData(imgData, 0, 0);
}

// ❌ ФУНКЦІЯ buildPalette() (ВИДАЛЕНО)
// function buildPalette() { ... }

function setupEvents() {
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');
    
    // ✅ НОВА КНОПКА: Очистити
    document.getElementById('tool-clear').onclick = clearAll;

    // ✅ НОВА ПАЛІТРА: <input type="color">
    document.getElementById('color-picker').addEventListener('input', changeColor);
    
    // ❌ СТАРА ПАЛІТРА (ВИДАЛЕНО)
    // document.getElementById('palette-btn').onclick = () => { ... };
    
    document.getElementById('send-btn').onclick = sendToBot;

    canvas.addEventListener('pointerdown', startDrawing);
    canvas.addEventListener('pointermove', draw);
    canvas.addEventListener('pointerup', stopDrawing);
    canvas.addEventListener('pointerleave', stopDrawing);

    window.addEventListener('resize', () => {
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        resizeCanvas();
        ctx.putImageData(imgData, 0, 0);
    });
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('#tool-pen,#tool-eraser').forEach(b => b.classList.remove('active'));
    document.getElementById('tool-' + tool).classList.add('active');
}

function startDrawing(e) {
    e.preventDefault();
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    lastX = e.clientX - rect.left;
    lastY = e.clientY - rect.top;
}

function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const size = currentTool === 'eraser' ? ERASER_SIZE : BRUSH_SIZE;

    ctx.globalCompositeOperation = currentTool === 'eraser' ? 'destination-out' : 'source-over';
    ctx.lineWidth = size;
    ctx.lineCap = 'round';

    // ✅ ФІКС: Стирачка тепер не малює кольором фону,
    // а використовує 'destination-out' для справжнього стирання.
    // 'strokeStyle' тепер завжди бере 'currentColor'.
    ctx.strokeStyle = currentColor; 
    
    // ❌ СТАРИЙ КОД:
    // ctx.strokeStyle = currentTool === 'pen' ? currentColor : '#222';

    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(x, y);
    ctx.stroke();

    lastX = x;
    lastY = y;

    saveArt(); // автозбереження
}

function stopDrawing() {
    isDrawing = false;
}

// === ✅ НОВІ ФУНКЦІЇ ===

/**
 * Обробляє вибір кольору з <input type="color">
 */
function changeColor(e) {
    currentColor = e.target.value;
    // Якщо обрали колір, автоматично вмикаємо пензель
    if (currentTool === 'eraser') {
        setTool('pen');
    }
}

/**
 * Очищує все полотно з підтвердженням
 */
function clearAll() {
    const doClear = () => {
        ctx.fillStyle = '#222';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        saveArt();
    };

    // Використовуємо нативне підтвердження Telegram, якщо доступно
    if (WebApp && WebApp.platform !== 'unknown') {
        WebApp.showConfirm('Очистити все полотно? Цю дію не можна скасувати.', (isOk) => {
            if (isOk) doClear();
        });
    } else {
        // Fallback для звичайного браузера
        if (confirm('Очистити все полотно? Цю дію не можна скасувати.')) {
            doClear();
        }
    }
}


// === ЗБЕРЕЖЕННЯ ===
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
        };
        img.src = saved;
    }
}

// === ВІДПРАВКА У БОТ ===
function sendToBot() {
    saveArt();
    const dataUrl = canvas.toDataURL('image/png');
    const payload = dataUrl.split(',')[1]; // base64
    const data = `PAINT|${payload}`;
    if (WebApp) {
        WebApp.sendData(data);
        WebApp.close();
    } else {
        alert('Відправлено: ' + data.substring(0, 50) + '...');
    }
}

// === СТАРТ ===
window.addEventListener('load', init);