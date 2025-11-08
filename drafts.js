const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const BRUSH_SIZE = 12;
const ERASER_SIZE = 30;
const COLORS = [
    '#ffffff','#000000','#ff0000','#00ff00','#0000ff','#ffff00','#ff00ff','#00ffff',
    '#ff8800','#88ff00','#0088ff','#ff0088','#8800ff','#00ff88','#888888','#444444'
];

// === СТАН ===
let canvas, ctx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen';
let lastX = 0, lastY = 0;
let points = [];

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
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');
    document.getElementById('palette-btn').onclick = () => {
        document.getElementById('palette-grid').classList.toggle('show');
    };
    document.getElementById('save-btn').onclick = saveToGallery;

    canvas.addEventListener('pointerdown', startDrawing);
    canvas.addEventListener('pointermove', draw);
    canvas.addEventListener('pointerup', stopDrawing);
    canvas.addEventListener('pointerleave', stopDrawing);

    window.addEventListener('resize', () => {
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        resizeCanvas();
        ctx.putImageData(imgData, 0, 0);
        redrawFromPoints(); // відновлення ліній
    });
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('#tool-pen,#tool-eraser').forEach(b => b.classList.remove('active'));
    document.getElementById('tool-' + tool).classList.add('active');
}

function startDrawing(e) {
    isDrawing = true;
    points = [];
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    points.push({ x, y });
    lastX = x; lastY = y;
}

function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    points.push({ x, y });

    // Малюємо плавно
    ctx.globalCompositeOperation = currentTool === 'eraser' ? 'destination-out' : 'source-over';
    ctx.lineWidth = currentTool === 'eraser' ? ERASER_SIZE : BRUSH_SIZE;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = currentTool === 'pen' ? currentColor : '#222';

    if (points.length >= 3) {
        const mid = {
            x: (points[points.length-2].x + points[points.length-1].x) / 2,
            y: (points[points.length-2].y + points[points.length-1].y) / 2
        };
        ctx.beginPath();
        ctx.moveTo(points[points.length-3].x, points[points.length-3].y);
        ctx.quadraticCurveTo(points[points.length-2].x, points[points.length-2].y, mid.x, mid.y);
        ctx.stroke();
    }

    lastX = x; lastY = y;
    saveArt();
}

function stopDrawing() {
    if (!isDrawing) return;
    isDrawing = false;

    // Дорисовуємо останню частину
    if (points.length > 1) {
        ctx.beginPath();
        ctx.moveTo(points[points.length-2].x, points[points.length-2].y);
        ctx.lineTo(points[points.length-1].x, points[points.length-1].y);
        ctx.stroke();
    }
}

// === ВІДНОВЛЕННЯ ЛІНІЙ ПРИ RESIZE ===
function redrawFromPoints() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // (тут можна зберегти points, але для простоти — лише localStorage)
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
    saveArt();

    const dataUrl = canvas.toDataURL('image/png');
    const blob = await (await fetch(dataUrl)).blob();

    // 1. Android Chrome — File System Access
    if ('showSaveFilePicker' in window) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: `morstrix_${Date.now()}.png`,
                types: [{ description: 'PNG', accept: { 'image/png': ['.png'] } }]
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            alert('Збережено в галерею!');
            return;
        } catch (e) { console.warn(e); }
    }

    // 2. iOS / резерв — копіювання в буфер
    if (navigator.clipboard && navigator.clipboard.write) {
        try {
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
            alert('Зображення в буфері обміну!\nУтримуй на фото → "Зберегти в галерею"');
            return;
        } catch (e) { console.warn(e); }
    }

    // 3. Резервний download
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = `morstrix_${Date.now()}.png`;
    a.click();
    alert('Завантажено! Перевір "Завантаження"');
}

// === СТАРТ ===
window.addEventListener('load', init);