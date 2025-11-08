const WebApp = window.Telegram.WebApp;

// === КОНФИГ ===
const BRUSH_SIZE = 14;
const ERASER_SIZE = 40;
const COLORS = [
    '#ffffff','#000000','#ff0000','#00ff00','#0000ff','#ffff00','#ff00ff','#00ffff',
    '#ff8800','#88ff00','#0088ff','#ff0088','#8800ff','#00ff88','#888888','#444444'
];

// === СОСТОЯНИЕ ===
let canvas, ctx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen';
let lastX = 0, lastY = 0;

// === ИНИЦИАЛИЗАЦИЯ ===
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
    // Инструменты
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');
    document.getElementById('palette-btn').onclick = () => {
        document.getElementById('palette-grid').classList.toggle('show');
    };
    document.getElementById('save-btn').onclick = saveToGallery;

    // Малювання
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
    ctx.strokeStyle = currentTool === 'pen' ? currentColor : '#222';

    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(x, y);
    ctx.stroke();

    lastX = x;
    lastY = y;

    saveArt();
}

function stopDrawing() {
    isDrawing = false;
}

// === СОХРАНЕНИЕ ===
function saveArt() {
    const dataUrl = canvas.toDataURL('image/png');
    localStorage.setItem('morstrix_paint', dataUrl);
}

function loadArt() {
    const saved = localStorage.getItem('morstrix_paint');
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

// === СОХРАНЕНИЕ В ГАЛЕРЕЮ ===
async function saveToGallery() {
    saveArt();

    canvas.toBlob(async (blob) => {
        const file = new File([blob], `morstrix_${Date.now()}.png`, { type: 'image/png' });

        // 1. Android/iOS — share
        if (navigator.share && navigator.canShare?.({ files: [file] })) {
            try {
                await navigator.share({ files: [file], title: 'Paint' });
                alert('Збережено в галерею!');
                return;
            } catch (e) {}
        }

        // 2. Копіювання в буфер
        if (navigator.clipboard?.write) {
            try {
                await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
                alert('В буфері! Утримуй → Зберегти');
                return;
            } catch (e) {}
        }

        // 3. Download
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.name;
        a.click();
        URL.revokeObjectURL(url);
        alert('Завантажено!');
    }, 'image/png');
}

// === СТАРТ ===
window.addEventListener('load', init);