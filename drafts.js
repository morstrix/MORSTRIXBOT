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
let bufferCanvas, bufferCtx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen';
let path = [];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('paint-canvas');
    ctx = canvas.getContext('2d');
    
    // Буферний canvas
    bufferCanvas = document.createElement('canvas');
    bufferCtx = bufferCanvas.getContext('2d');

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
    bufferCanvas.width = canvas.width;
    bufferCanvas.height = canvas.height;
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
    canvas.addEventListener('pointermove', drawPreview);
    canvas.addEventListener('pointerup', commitPath);
    canvas.addEventListener('pointerleave', commitPath);

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
    bufferCtx.clearRect(0, 0, bufferCanvas.width, bufferCanvas.height);
}

function drawPreview(e) {
    if (!isDrawing) return;
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    path.push({ x, y });

    // Прев’ю в буфері
    bufferCtx.clearRect(0, 0, bufferCanvas.width, bufferCanvas.height);
    drawPath(bufferCtx, path, true);

    // Показуємо буфер на основному canvas
    ctx.drawImage(bufferCanvas, 0, 0);
}

function commitPath() {
    if (!isDrawing || path.length < 2) {
        isDrawing = false;
        return;
    }

    // Рендеримо остаточно на основний canvas
    drawPath(ctx, path, false);
    bufferCtx.clearRect(0, 0, bufferCanvas.width, bufferCanvas.height);
    saveArt();
    isDrawing = false;
}

function drawPath(context, points, isPreview) {
    if (points.length < 2) return;

    const size = currentTool === 'eraser' ? ERASER_SIZE : BRUSH_SIZE;
    context.globalCompositeOperation = currentTool === 'eraser' ? 'destination-out' : 'source-over';
    context.lineWidth = size;
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.strokeStyle = currentTool === 'pen' ? currentColor : '#222';

    context.beginPath();
    context.moveTo(points[0].x, points[0].y);

    for (let i = 1; i < points.length - 2; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        context.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }

    // Останній сегмент
    if (points.length > 1) {
        context.quadraticCurveTo(
            points[points.length - 2].x,
            points[points.length - 2].y,
            points[points.length - 1].x,
            points[points.length - 1].y
        );
    }

    context.stroke();
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

        // 1. Web Share API — Android/iOS
        if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
            try {
                await navigator.share({ files: [file], title: 'MORSTRIX Paint' });
                alert('Збережено!');
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