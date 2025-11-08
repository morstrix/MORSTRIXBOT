const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const BRUSH_SIZE = 12;
const COLORS = [
    '#ffffff','#000000','#ff0000','#00ff00','#0000ff','#ffff00','#ff00ff','#00ffff',
    '#ff8800','#88ff00','#0088ff','#ff0088','#8800ff','#00ff88','#888888','#444444'
];

// === СТАН ===
let canvas, ctx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen'; // 'pen' | 'eraser'
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
    buildPalette();
}

function resizeCanvas() {
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.putImageData(imageData, 0, 0);
}

function buildPalette() {
    const grid = document.getElementById('palette-grid');
    COLORS.forEach(c => {
        const btn = document.createElement('button');
        btn.style.background = c;
        btn.dataset.color = c;
        btn.onclick = () => {
            currentColor = c;
            grid.classList.remove('show');
            if (currentTool === 'eraser') setTool('pen');
        };
        grid.appendChild(btn);
    });
}

function setupEvents() {
    // інструменти
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');

    // палітра
    document.getElementById('palette-btn').onclick = () => {
        document.getElementById('palette-grid').classList.toggle('show');
    };

    // збереження
    document.getElementById('save-btn').onclick = saveToGallery;

    // малювання
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
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    lastX = e.clientX - rect.left;
    lastY = e.clientY - rect.top;
    draw(e);
}

function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.globalCompositeOperation = currentTool === 'eraser' ? 'destination-out' : 'source-over';
    ctx.strokeStyle = currentTool === 'pen' ? currentColor : '#222';
    ctx.lineWidth = BRUSH_SIZE;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

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

// === ЗБЕРЕЖЕННЯ ===
function saveArt() {
    const dataUrl = canvas.toDataURL('image/png');
    localStorage.setItem('morstrix_paint', dataUrl);
}

function loadArt() {
    const saved = localStorage.getItem('morstrix_paint');
    if (saved) {
        const img = new Image();
        img.onload = () => {
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
        img.src = saved;
    }
}

// === ЗБЕРЕЖЕННЯ В ГАЛЕРЕЮ ===
async function saveToGallery() {
    saveArt(); // спочатку в localStorage

    const dataUrl = canvas.toDataURL('image/png');
    const blob = await (await fetch(dataUrl)).blob();

    // 1. Спроба: File System Access API (Chrome/Edge Android)
    if ('showSaveFilePicker' in window) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: `morstrix_paint_${Date.now()}.png`,
                types: [{ description: 'PNG Image', accept: { 'image/png': ['.png'] } }]
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            alert('Збережено в галерею!');
            return;
        } catch (e) { console.warn('File System API не спрацював', e); }
    }

    // 2. Резерв: завантаження через <a>
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = `morstrix_paint_${Date.now()}.png`;
    a.click();
    alert('Зображення завантажено! Перевір "Завантаження" або галерею.');

    // 3. Додатково: спроба через Telegram WebApp (якщо підтримує)
    if (WebApp && WebApp.saveFile) {
        WebApp.saveFile(blob, `morstrix_paint_${Date.now()}.png`);
    }
}

// === СТАРТ ===
window.addEventListener('load', init);