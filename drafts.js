const WebApp = window.Telegram ? window.Telegram.WebApp : null;

// === КОНФИГ ===
const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE = 25;
let DROP_SPEED = 1000;

// === ТЕМНЫЕ ЦВЕТА ===
const PIECE_COLORS = [
    '#1a3a1a', '#2a2a4a', '#3a2a1a', '#1a2a3a',
    '#2a3a2a', '#3a1a2a', '#2a1a3a'
];

// === СОСТОЯНИЕ ===
let canvas, ctx, nextCanvas, nextCtx;
let board = [];
let currentPiece, nextPiece;
let dropCounter = 0;
let lastTime = 0;
let isGameOver = false;
let isPaused = false;
let score = 0;
let lines = 0;
let level = 1;
let gameSpeed = DROP_SPEED;
let isMobile = false;

// === ФИГУРЫ ===
const PIECES = [
    [[1, 1], [1, 1]],
    [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
    [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    [[0, 1, 0], [0, 1, 0], [0, 1, 1]],
    [[0, 1, 0], [0, 1, 0], [1, 1, 0]],
    [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
    [[1, 1, 0], [0, 1, 1], [0, 0, 0]]
];

// === ИНИЦИАЛИЗАЦИЯ ===
function init() {
    console.log("🚀 Тетрис запускается...");
    
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    
    nextCanvas = document.getElementById('next-piece-canvas');
    nextCtx = nextCanvas.getContext('2d');
    
    isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    console.log("📱 Мобильный:", isMobile);
    
    // Сразу создаем поле
    for (let y = 0; y < ROWS; y++) {
        board[y] = Array(COLS).fill(0);
    }
    
    calculateCanvasSize();
    setupEvents();
    nextPiece = createRandomPiece();
    spawnPiece();
    
    if (WebApp) {
        WebApp.ready();
        WebApp.expand();
        WebApp.BackButton.show();
        WebApp.BackButton.onClick(() => WebApp.close());
    }
    
    updateUI();
    
    // Запускаем игру
    requestAnimationFrame(gameLoop);
    
    window.addEventListener('resize', calculateCanvasSize);
}

function calculateCanvasSize() {
    const gameArea = document.querySelector('.game-area');
    if (!gameArea) return;
    
    const maxWidth = gameArea.clientWidth - 20;
    const maxHeight = gameArea.clientHeight - 20;
    
    const blockByWidth = Math.floor(maxWidth / COLS);
    const blockByHeight = Math.floor(maxHeight / ROWS);
    BLOCK_SIZE = Math.min(blockByWidth, blockByHeight);
    
    console.log("📐 Размер блока:", BLOCK_SIZE, "maxW:", maxWidth, "maxH:", maxHeight);
    
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;
    
    // Принудительная отрисовка
    draw();
}

function createRandomPiece() {
    const matrix = PIECES[Math.floor(Math.random() * PIECES.length)];
    const color = PIECE_COLORS[Math.floor(Math.random() * PIECE_COLORS.length)];
    
    return { matrix, color, pos: { x: 0, y: 0 } };
}

function rotate(matrix) {
    const N = matrix.length - 1;
    return matrix.map((row, i) =>
        row.map((val, j) => matrix[N - j][i])
    );
}

function checkCollision(piece) {
    if (!piece) return true;
    
    for (let y = 0; y < piece.matrix.length; y++) {
        for (let x = 0; x < piece.matrix[y].length; x++) {
            if (piece.matrix[y][x]) {
                const boardX = piece.pos.x + x;
                const boardY = piece.pos.y + y;
                
                if (boardX < 0 || boardX >= COLS || 
                    boardY >= ROWS || 
                    (boardY >= 0 && board[boardY] && board[boardY][boardX])) {
                    return true;
                }
            }
        }
    }
    return false;
}

// === ИГРОВАЯ ЛОГИКА ===
function spawnPiece() {
    if (isGameOver) return;
    
    currentPiece = nextPiece;
    nextPiece = createRandomPiece();
    
    currentPiece.pos = {
        x: Math.floor(COLS / 2) - Math.floor(currentPiece.matrix[0].length / 2),
        y: 0
    };
    
    drawNextPiece();
    
    if (checkCollision(currentPiece)) {
        isGameOver = true;
        console.log("💀 Game Over!");
        setTimeout(() => {
            alert(`GAME OVER!\nSCORE: ${score}\nLINES: ${lines}\nLEVEL: ${level}`);
            location.reload();
        }, 500);
    }
}

function dropPiece() {
    if (isPaused || isGameOver) return;
    
    if (!currentPiece) {
        spawnPiece();
        return;
    }
    
    currentPiece.pos.y++;
    if (checkCollision(currentPiece)) {
        currentPiece.pos.y--;
        mergePiece();
        clearLines();
        spawnPiece();
    }
    dropCounter = 0;
}

function hardDrop() {
    if (isPaused || isGameOver || !currentPiece) return;
    
    let dropDistance = 0;
    while (!checkCollision(currentPiece)) {
        currentPiece.pos.y++;
        dropDistance++;
    }
    currentPiece.pos.y--;
    
    score += dropDistance * 2;
    mergePiece();
    clearLines();
    spawnPiece();
    updateUI();
}

function movePiece(dir) {
    if (isPaused || isGameOver || !currentPiece) return;
    
    currentPiece.pos.x += dir;
    if (checkCollision(currentPiece)) {
        currentPiece.pos.x -= dir;
    }
}

function rotatePiece() {
    if (isPaused || isGameOver || !currentPiece) return;
    
    const original = currentPiece.matrix;
    currentPiece.matrix = rotate(currentPiece.matrix);
    
    const kicks = [0, 1, -1, 2, -2];
    const originalX = currentPiece.pos.x;
    
    for (const kick of kicks) {
        currentPiece.pos.x = originalX + kick;
        if (!checkCollision(currentPiece)) return;
    }
    
    currentPiece.matrix = original;
    currentPiece.pos.x = originalX;
}

function togglePause() {
    isPaused = !isPaused;
    const pauseBtn = document.getElementById('pause-btn');
    
    if (isPaused) {
        pauseBtn.textContent = '▶';
        pauseBtn.querySelector('.pause-label').textContent = 'PLAY';
    } else {
        pauseBtn.textContent = '⏸';
        pauseBtn.querySelector('.pause-label').textContent = 'PAUSE';
    }
}

function mergePiece() {
    if (!currentPiece) return;
    
    currentPiece.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                const boardY = y + currentPiece.pos.y;
                const boardX = x + currentPiece.pos.x;
                if (boardY >= 0 && boardY < ROWS && boardX >= 0 && boardX < COLS) {
                    board[boardY][boardX] = currentPiece.color;
                }
            }
        });
    });
}

function clearLines() {
    let linesCleared = 0;
    
    for (let y = ROWS - 1; y >= 0; y--) {
        if (board[y].every(cell => cell)) {
            board.splice(y, 1);
            board.unshift(Array(COLS).fill(0));
            linesCleared++;
            y++;
        }
    }
    
    if (linesCleared) {
        lines += linesCleared;
        score += [0, 100, 300, 500, 800][linesCleared] * level;
        level = Math.floor(lines / 10) + 1;
        gameSpeed = Math.max(200, DROP_SPEED - (level - 1) * 100);
        updateUI();
    }
}

function updateUI() {
    document.getElementById('score').textContent = score;
    document.getElementById('lines').textContent = lines;
    document.getElementById('level').textContent = level;
}

// === ОТРИСОВКА ===
function drawNextPiece() {
    nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
    if (!nextPiece) return;
    
    const size = Math.min(40 / nextPiece.matrix.length, 12);
    const offsetX = (40 - nextPiece.matrix[0].length * size) / 2;
    const offsetY = (40 - nextPiece.matrix.length * size) / 2;
    
    nextCtx.fillStyle = '#0a0a0a';
    nextCtx.fillRect(0, 0, 40, 40);
    
    nextPiece.matrix.forEach((row, y) => {
        row.forEach((cell, x) => {
            if (cell) {
                nextCtx.fillStyle = nextPiece.color;
                nextCtx.fillRect(offsetX + x * size, offsetY + y * size, size, size);
                
                nextCtx.strokeStyle = '#666';
                nextCtx.lineWidth = 1;
                nextCtx.strokeRect(offsetX + x * size, offsetY + y * size, size, size);
            }
        });
    });
}

function drawBlock(x, y, color, isGhost = false) {
    if (isGhost) {
        // ПРИЗРАК - БОЛЕЕ ЗАМЕТНЫЙ
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.3;
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        ctx.globalAlpha = 1.0;
        
        // Контур призрака
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(
            x * BLOCK_SIZE + 1, 
            y * BLOCK_SIZE + 1, 
            BLOCK_SIZE - 2, 
            BLOCK_SIZE - 2
        );
        
        // Точки по углам для видимости
        ctx.fillStyle = color;
        const dotSize = Math.max(2, BLOCK_SIZE / 8);
        ctx.fillRect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + 2, dotSize, dotSize);
        ctx.fillRect(x * BLOCK_SIZE + BLOCK_SIZE - dotSize - 2, y * BLOCK_SIZE + 2, dotSize, dotSize);
        ctx.fillRect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + BLOCK_SIZE - dotSize - 2, dotSize, dotSize);
        ctx.fillRect(x * BLOCK_SIZE + BLOCK_SIZE - dotSize - 2, y * BLOCK_SIZE + BLOCK_SIZE - dotSize - 2, dotSize, dotSize);
    } else {
        // Обычный блок
        ctx.fillStyle = color;
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        
        // Тень
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, 3);
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, 3, BLOCK_SIZE);
        
        // Свет
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fillRect(x * BLOCK_SIZE + BLOCK_SIZE - 3, y * BLOCK_SIZE + 3, 3, BLOCK_SIZE - 3);
        ctx.fillRect(x * BLOCK_SIZE + 3, y * BLOCK_SIZE + BLOCK_SIZE - 3, BLOCK_SIZE - 3, 3);
    }
}

function drawGhostPiece() {
    if (!currentPiece || isPaused || isGameOver) return;
    
    const ghost = {
        matrix: currentPiece.matrix,
        color: currentPiece.color,
        pos: { ...currentPiece.pos }
    };
    
    // Находим нижнюю позицию
    while (!checkCollision(ghost)) {
        ghost.pos.y++;
    }
    ghost.pos.y--; // Возвращаем на последнюю валидную
    
    // Рисуем только если есть куда падать
    if (ghost.pos.y > currentPiece.pos.y) {
        ghost.matrix.forEach((row, y) => {
            row.forEach((cell, x) => {
                if (cell) {
                    drawBlock(x + ghost.pos.x, y + ghost.pos.y, ghost.color, true);
                }
            });
        });
    }
}

function drawGrid() {
    // Яркая сетка для мобильных
    ctx.strokeStyle = isMobile ? '#3a3a3a' : '#2a2a2a';
    ctx.lineWidth = isMobile ? 1 : 0.5;
    
    // Вертикальные линии
    for (let x = 0; x <= COLS; x++) {
        ctx.beginPath();
        ctx.moveTo(x * BLOCK_SIZE, 0);
        ctx.lineTo(x * BLOCK_SIZE, canvas.height);
        ctx.stroke();
    }
    
    // Горизонтальные линии
    for (let y = 0; y <= ROWS; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * BLOCK_SIZE);
        ctx.lineTo(canvas.width, y * BLOCK_SIZE);
        ctx.stroke();
    }
}

function drawPauseScreen() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${BLOCK_SIZE * 1.2}px 'Courier New'`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2);
}

function draw() {
    // Фон
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // СЕТКА
    drawGrid();
    
    // Старые блоки
    for (let y = 0; y < ROWS; y++) {
        for (let x = 0; x < COLS; x++) {
            if (board[y][x]) {
                drawBlock(x, y, board[y][x]);
            }
        }
    }
    
    // Призрачная фигура
    drawGhostPiece();
    
    // Текущая фигура
    if (currentPiece) {
        currentPiece.matrix.forEach((row, y) => {
            row.forEach((cell, x) => {
                if (cell) {
                    drawBlock(x + currentPiece.pos.x, y + currentPiece.pos.y, currentPiece.color);
                }
            });
        });
    }
    
    // Экран паузы
    if (isPaused) {
        drawPauseScreen();
    }
}

// === СОБЫТИЯ ===
function setupEvents() {
    console.log("🎮 Настройка управления...");
    
    // 4 кнопки
    document.getElementById('left-btn').addEventListener('click', () => {
        console.log("← Left pressed");
        movePiece(-1);
        draw();
    });
    
    document.getElementById('rotate-btn').addEventListener('click', () => {
        console.log("↻ Rotate pressed");
        rotatePiece();
        draw();
    });
    
    document.getElementById('right-btn').addEventListener('click', () => {
        console.log("→ Right pressed");
        movePiece(1);
        draw();
    });
    
    document.getElementById('down-btn').addEventListener('click', () => {
        console.log("↓ Hard drop pressed");
        hardDrop();
        draw();
    });
    
    // Пауза
    document.getElementById('pause-btn').addEventListener('click', togglePause);
    
    // Свайпы для мобильных
    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartTime = 0;
    
    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touchStartTime = Date.now();
    }, { passive: false });
    
    canvas.addEventListener('touchend', (e) => {
        e.preventDefault();
        if (isPaused || isGameOver) return;
        
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const touchTime = Date.now() - touchStartTime;
        
        const dx = touchEndX - touchStartX;
        const dy = touchEndY - touchStartY;
        
        // Минимальное расстояние для свайпа
        const minSwipe = 30;
        
        // Быстрый тап (менее 200ms) = хард дроп
        if (touchTime < 200 && Math.abs(dx) < 10 && Math.abs(dy) < 10) {
            hardDrop();
            return;
        }
        
        if (Math.abs(dx) > Math.abs(dy)) {
            // Горизонтальный свайп
            if (dx > minSwipe) movePiece(1);
            else if (dx < -minSwipe) movePiece(-1);
        } else {
            // Вертикальный свайп
            if (dy > minSwipe) dropPiece();
            else if (dy < -minSwipe) rotatePiece();
        }
        
        draw();
    }, { passive: false });
    
    // Клавиатура
    document.addEventListener('keydown', e => {
        if (isGameOver) return;
        
        switch(e.key) {
            case 'ArrowLeft': 
                movePiece(-1); 
                draw();
                break;
            case 'ArrowRight': 
                movePiece(1); 
                draw();
                break;
            case 'ArrowDown': 
                dropPiece(); 
                draw();
                break;
            case 'ArrowUp': 
                rotatePiece(); 
                draw();
                break;
            case ' ': 
                hardDrop(); 
                draw();
                break;
            case 'p':
            case 'P':
            case 'Escape': 
                togglePause(); 
                break;
        }
    });
    
    console.log("✅ Управление настроено");
}

// === ГЛАВНЫЙ ЦИКЛ ===
function gameLoop(time) {
    if (isGameOver) return;
    
    const delta = time - (lastTime || time);
    lastTime = time;
    
    if (!isPaused) {
        dropCounter += delta;
        if (dropCounter > gameSpeed) {
            dropPiece();
            draw(); // Перерисовываем после падения
        }
    }
    
    requestAnimationFrame(gameLoop);
}

// === ЗАПУСК ===
// Ждем полной загрузки страницы
window.addEventListener('DOMContentLoaded', () => {
    console.log("📄 DOM загружен, запускаем игру...");
    setTimeout(init, 100); // Небольшая задержка для стабильности
});