const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const GRID = 16;
const CELL = 20; // розмір пікселя в UI
const CANVAS_SIZE = GRID * CELL;

// === СТАН ===
let canvas, ctx;
let pixelGrid = Array(GRID).fill().map(() => Array(GRID).fill(null));
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen'; // 'pen' | 'eraser'

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('pixel-canvas');
    ctx = canvas.getContext('2d');
    canvas.width = CANVAS_SIZE;
    canvas.height = CANVAS_SIZE;

    // Масштабування під екран
    const container = document.getElementById('canvas-container');
    const scale = Math.min(
        (window.innerWidth * 0.9) / CANVAS_SIZE,
        (window.innerHeight * 0.7) / CANVAS_SIZE
    );
    const scaledSize = CANVAS_SIZE * scale;
    container.style.width = scaledSize + 'px';
    container.style.height = scaledSize + 'px';

    loadArt();
    drawGrid();
    setupEvents();
}

function setupEvents() {
    // Інструменти
    document.getElementById('tool-pen').onclick = () => setTool('pen');
    document.getElementById('tool-eraser').onclick = () => setTool('eraser');

    // Кольори
    document.querySelectorAll('.color-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentColor = btn.dataset.color;
            if (currentTool === 'eraser') setTool('pen');
        };
    });

    // Кнопки
    document.getElementById('clear-btn').onclick = () => {
        if (confirm('Очистити полотно?')) {
            pixelGrid = Array(GRID).fill().map(() => Array(GRID).fill(null));
            redraw();
            saveArt();
        }
    };

    document.getElementById('save-btn').onclick = () => {
        saveArt();
        alert('Арт збережено локально!');
    };

    document.getElementById('send-btn').onclick = () => {
        saveArt();
        const artData = localStorage.getItem('morstrix_pixel_art');
        if (!artData || isEmptyArt()) {
            alert('Намалюй щось!');
            return;
        }
        const data = `PIXELART|${artData}`;
        if (WebApp) {
            WebApp.sendData(data);
            WebApp.close();
        } else {
            alert('Відправлено (тест): ' + data.substring(0, 50) + '...');
        }
    };

    // Малювання
    canvas.addEventListener('pointerdown', startDrawing);
    canvas.addEventListener('pointermove', draw);
    canvas.addEventListener('pointerup', stopDrawing);
    canvas.addEventListener('pointerleave', stopDrawing);
}

function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('[id^="tool-"]').forEach(b => b.classList.remove('active'));
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
    const x = Math.floor((e.clientX - rect.left) / CELL);
    const y = Math.floor((e.clientY - rect.top) / CELL);
    if (x >= 0 && x < GRID && y >= 0 && y < GRID) {
        const color = currentTool === 'pen' ? currentColor : null;
        if (pixelGrid[y][x] !== color) {
            pixelGrid[y][x] = color;
            drawPixel(x, y, color);
            saveArt(); // автозбереження
        }
    }
}

function stopDrawing() {
    isDrawing = false;
}

function drawPixel(x, y, color) {
    ctx.fillStyle = color || '#222222';
    ctx.fillRect(x * CELL, y * CELL, CELL, CELL);
    ctx.strokeStyle = '#2d2d2d';
    ctx.lineWidth = 1;
    ctx.strokeRect(x * CELL, y * CELL, CELL, CELL);
}

function drawGrid() {
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    for (let y = 0; y < GRID; y++) {
        for (let x = 0; x < GRID; x++) {
            const color = pixelGrid[y][x];
            if (color) {
                drawPixel(x, y, color);
            } else {
                ctx.fillStyle = '#222222';
                ctx.fillRect(x * CELL, y * CELL, CELL, CELL);
                ctx.strokeStyle = '#2d2d2d';
                ctx.strokeRect(x * CELL, y * CELL, CELL, CELL);
            }
        }
    }
}

function redraw() {
    drawGrid();
}

function isEmptyArt() {
    return pixelGrid.every(row => row.every(cell => cell === null));
}

// === ЗБЕРЕЖЕННЯ ===
function saveArt() {
    localStorage.setItem('morstrix_pixel_art', JSON.stringify(pixelGrid));
}

function loadArt() {
    const saved = localStorage.getItem('morstrix_pixel_art');
    if (saved) {
        try {
            pixelGrid = JSON.parse(saved);
        } catch (e) {
            console.error("Помилка завантаження арту:", e);
            pixelGrid = Array(GRID).fill().map(() => Array(GRID).fill(null));
        }
    }
    redraw();
}

// === СТАРТ ===
window.addEventListener('load', init);
window.addEventListener('resize', () => setTimeout(init, 100));