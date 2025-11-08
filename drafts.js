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
let path = [];

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
    });
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('#tool-pen,#tool-eraser').forEach(b => b.classList.remove('active'));
    document.getElementById('tool-' + tool).classList.add('active');
}

function startDrawing(e) {
    isDrawing = true;
    path = [];
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    path.push({ x, y });
}

function draw(e) {
    if (!isDrawing || path.length === 0) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    path.push({ x, y });

    const size = currentTool === 'eraser' ? ERASER_SIZE : BRUSH_SIZE;

    ctx.globalCompositeOperation = currentTool === 'eraser' ? 'destination-out' : 'source-over';
    ctx.lineWidth = size;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = currentTool === 'pen' ? currentColor : '#222';

    ctx.beginPath();
    ctx.moveTo(path[path.length - 2].x, path[path.length - 2].y);
    ctx.lineTo(path[path.length - 1].x, path[path.length - 1].y);
    ctx.stroke();

    saveArt();
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
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#222';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
        img.src = saved;
    }
}

// === ЗБЕРЕЖЕННЯ В ГАЛЕРЕЮ ===
async function saveToGallery() {
    saveArt();

    canvas.toBlob(async (blob) => {
        const file = new File([blob], `morstrix_${Date.now()}.png`, { type: 'image/png' });

        // 1. Web Share API (Android/iOS) — ЗБЕРЕГТИ В ГАЛЕРЕЮ
        if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
            try {
                await navigator.share({
                    files: [file],
                    title: 'Малюнок з MORSTRIX',
                    text: 'Збережено з Paint'
                });
                alert('Збережено в галерею!');
                return;
            } catch (e) { console.warn('Share API не спрацював', e); }
        }

        // 2. Копіювання в буфер (iOS)
        if (navigator.clipboard && navigator.clipboard.write) {
            try {
                await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
                alert('В буфері обміну!\nУтримуй → "Зберегти в Фото"');
                return;
            } catch (e) { console.warn(e); }
        }

        // 3. Резервний download
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