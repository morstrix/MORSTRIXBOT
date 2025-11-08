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
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
}

function buildPalette() {
    const grid = document.getElementById('palette-grid');
    COLORS.forEach(c => {
        const btn = document.createElement('button');
        btn.style.background = c;
        btn.dataset.color = c;
        btn.title = c;
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
    document.getElementById('save-btn').onclick = saveImage;

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
    e.preventDefault();
    isDrawing = true;
    draw(e);
}

function draw(e) {
    if (!isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.globalCompositeOperation = currentTool === 'eraser' ? 'destination-out' : 'source-over';
    ctx.fillStyle = currentTool === 'pen' ? currentColor : '#222';

    ctx.beginPath();
    ctx.arc(x, y, BRUSH_SIZE / 2, 0, Math.PI * 2);
    ctx.fill();

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
        img.onload = () => ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        img.src = saved;
    }
}

async function saveImage() {
    saveArt(); // спочатку в localStorage
    const dataUrl = canvas.toDataURL('image/png');

    // --- КОПІЮВАННЯ В БУФЕР (десктоп) ---
    if (navigator.clipboard && navigator.clipboard.write) {
        try {
            const blob = await (await fetch(dataUrl)).blob();
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
            alert('Зображення скопійовано в буфер обмена!');
            return;
        } catch (e) { console.warn('Clipboard API не спрацював', e); }
    }

    // --- ЗАВАНТАЖЕННЯ НА ТЕЛЕФОН ---
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = `morstrix_paint_${Date.now()}.png`;
    a.click();
    alert('Зображення завантажено на пристрій!');
}

// === СТАРТ ===
window.addEventListener('load', init);