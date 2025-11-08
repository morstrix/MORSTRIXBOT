const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const CANVAS_SIZE = 600; // фіксований розмір полотна
const BRUSH_SIZE = 8;

// === СТАН ===
let canvas, ctx;
let isDrawing = false;
let currentColor = '#ffffff';
let currentTool = 'pen'; // 'pen' | 'eraser'

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('paint-canvas');
    ctx = canvas.getContext('2d');
    canvas.width = CANVAS_SIZE;
    canvas.height = CANVAS_SIZE;

    // Масштабування під екран
    const container = document.getElementById('canvas-container');
    const maxDim = Math.min(window.innerWidth, window.innerHeight) * 0.8;
    const scale = maxDim / CANVAS_SIZE;
    const scaledSize = CANVAS_SIZE * scale;
    container.style.width = scaledSize + 'px';
    container.style.height = scaledSize + 'px';

    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    loadArt();
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
            ctx.fillStyle = '#222';
            ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
            saveArt();
        }
    };

    document.getElementById('save-btn').onclick = () => {
        saveArt();
        alert('Малюнок збережено!');
    };

    document.getElementById('send-btn').onclick = () => {
        saveArt();
        const dataUrl = canvas.toDataURL('image/png');
        const payload = dataUrl.split(',')[1]; // base64
        const data = `PAINT|${payload}`;
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
    localStorage.setItem('morstrix_paint_art', dataUrl);
}

function loadArt() {
    const saved = localStorage.getItem('morstrix_paint_art');
    if (saved) {
        const img = new Image();
        img.onload = () => {
            ctx.drawImage(img, 0, 0);
        };
        img.src = saved;
    }
}

// === СТАРТ ===
window.addEventListener('load', init);
window.addEventListener('resize', () => setTimeout(init, 100));