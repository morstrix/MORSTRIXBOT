const WebApp = window.Telegram.WebApp;

// === КОНФІГ ===
const BRUSH_SIZE = 6;
const ERASER_SIZE = 20;

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
    document.getElementById('color-picker').addEventListener('input', changeColor);
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

    // Запобігаємо скролінню на iOS
    document.body.style.touchAction = 'none';
    canvas.style.touchAction = 'none';
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

    // Тільки при pen встановлюємо колір
    if (currentTool === 'pen') {
        ctx.strokeStyle = currentColor;
    }

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

function changeColor(e) {
    currentColor = e.target.value;
    if (currentTool === 'eraser') {
        setTool('pen');
    }
}

function clearAll() {
    const doClear = () => {
        ctx.fillStyle = '#222';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        saveArt();
    };

    if (WebApp && WebApp.platform !== 'unknown') {
        WebApp.showConfirm('Очистити все полотно? Цю дію не можна скасувати.', (isOk) => {
            if (isOk) doClear();
        });
    } else {
        if (confirm('Очистити все полотно? Цю дію не можна скасувати.')) {
            doClear();
        }
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
        };
        img.src = saved;
    }
}

function sendToBot() {
    saveArt();
    const dataUrl = canvas.toDataURL('image/png');
    const payload = dataUrl.split(',')[1];

    // Формат: ART|ключ|base64
    const data = `ART|morstrix_art_${Date.now()}|${payload}`;

    if (WebApp) {
        WebApp.sendData(data);
        WebApp.close();
    } else {
        alert('Відправлено: ' + data.substring(0, 50) + '...');
    }
}

window.addEventListener('load', init);