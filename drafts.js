const WebApp = window.Telegram ? window.Telegram.WebApp : null;

// === КОНФИГ ===
const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE = 25;
let DROP_SPEED = 1000;

// === ТЕМНЫЕ ЦВЕТА ===
const PIECE_COLORS = [
    '#1a3a3a', '#2a2a4a', '#3a2a1a', '#1a2a3a',
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
let isMobile = window.innerWidth <= 768;

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
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    
    nextCanvas = document.getElementById('next-piece-canvas');
    nextCtx = nextCanvas.getContext('2d');
    
    isMobile = window.innerWidth <= 768;
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
    requestAnimationFrame(gameLoop);
    window.addEventListener('resize', () => {
        isMobile = window.innerWidth <= 768;
        calculateCanvasSize();
    });
}

function calculateCanvasSize() {
    const gameArea = document.querySelector('.game-area');
    const maxWidth = gameArea.clientWidth - 16;
    const maxHeight = gameArea.clientHeight - 16;
    
    const blockByWidth = Math.floor(maxWidth / COLS);
    const blockByHeight = Math.floor(maxHeight / ROWS);
    BLOCK_SIZE = Math.min(blockByWidth, blockByHeight);
    
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;
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
    for (let y = 0; y < piece.matrix.length; y++) {
        for (let x = 0; x < piece.matrix[y].length; x++) {
            if (piece.matrix[y][x]) {
                const boardX = piece.pos.x + x;
                const boardY = piece.pos.y + y;
                
                if (boardX < 0 || boardX >= COLS || 
                    boardY >= ROWS || 
                    (boardY >= 0 && board[boardY][boardX])) {
                    return true;
                }
            }
        }
    }
    return false;
}

// === ИГРОВАЯ ЛОГИКА ===
function spawnPiece() {
    currentPiece = nextPiece;
    nextPiece = createRandomPiece();
    
    currentPiece.pos = {
        x: Math.floor(COLS / 2) - Math.floor(currentPiece.matrix[0].length / 2),
        y: 0
    };
    
    drawNextPiece();
    
    if (checkCollision(currentPiece)) {
        isGameOver = true;
        setTimeout(() => {
            alert(`GAME OVER!\nSCORE: ${score}\nLINES: ${lines}\nLEVEL: ${level}`);
            location.reload();
        }, 300);
    }
}

function dropPiece() {
    if (isPaused) return;
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
    if (isPaused) return;
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
    if (isPaused) return;
    currentPiece.pos.x += dir;
    if (checkCollision(currentPiece)) {
        currentPiece.pos.x -= dir;
    }
}

function rotatePiece() {
    if (isPaused) return;
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
    const pauseIcon = pauseBtn;
    const pauseLabel = pauseBtn.querySelector('.pause-label');
    
    if (isPaused) {
        pauseBtn.textContent = '▶';
        pauseLabel.textContent = 'PLAY';
    } else {
        pauseBtn.textContent = '⏸';
        pauseLabel.textContent = 'PAUSE';
    }
}

function mergePiece() {
    currentPiece.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                const boardY = y + currentPiece.pos.y;
                const boardX = x + currentPiece.pos.x;
                if (boardY >= 0) {
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
        gameSpeed = Math.max(100, DROP_SPEED - (level - 1) * 100);
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
    
    const size = isMobile ? 8 : 10;
    const offsetX = (40 - nextPiece.matrix[0].length * size) / 2;
    const offsetY = (40 - nextPiece.matrix.length * size) / 2;
    
    nextPiece.matrix.forEach((row, y) => {
        row.forEach((cell, x) => {
            if (cell) {
                nextCtx.fillStyle = nextPiece.color;
                nextCtx.fillRect(offsetX + x * size, offsetY + y * size, size, size);
                nextCtx.strokeStyle = '#666';
                nextCtx.strokeRect(offsetX + x * size, offsetY + y * size, size, size);
            }
        });
    });
}

function drawBlock(x, y, color, isGhost = false) {
    if (isGhost) {
        const ghostAlpha = isMobile ? 0.35 : 0.25;
        const lineWidth = isMobile ? 2 : 1;
        
        ctx.fillStyle = color;
        ctx.globalAlpha = ghostAlpha;
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        ctx.globalAlpha = 1.0;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.strokeRect(
            x * BLOCK_SIZE + lineWidth/2, 
            y * BLOCK_SIZE + lineWidth/2, 
            BLOCK_SIZE - lineWidth, 
            BLOCK_SIZE - lineWidth
        );
        
        if (isMobile) {
            ctx.fillStyle = color;
            ctx.fillRect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + 2, 3, 3);
            ctx.fillRect(x * BLOCK_SIZE + BLOCK_SIZE - 5, y * BLOCK_SIZE + 2, 3, 3);
            ctx.fillRect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + BLOCK_SIZE - 5, 3, 3);
            ctx.fillRect(x * BLOCK_SIZE + BLOCK_SIZE - 5, y * BLOCK_SIZE + BLOCK_SIZE - 5, 3, 3);
        }
    } else {
        ctx.fillStyle = color;
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        
        ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, 3);
        ctx.fillRect(x * BLOCK_SIZE, y * BLOCK_SIZE, 3, BLOCK_SIZE);
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.fillRect(x * BLOCK_SIZE + BLOCK_SIZE - 3, y * BLOCK_SIZE + 3, 3, BLOCK_SIZE - 3);
        ctx.fillRect(x * BLOCK_SIZE + 3, y * BLOCK_SIZE + BLOCK_SIZE - 3, BLOCK_SIZE - 3, 3);
    }
}

function drawGhostPiece() {
    if (!currentPiece || isPaused) return;
    
    const ghost = {
        matrix: currentPiece.matrix,
        color: currentPiece.color,
        pos: { ...currentPiece.pos }
    };
    
    while (!checkCollision(ghost)) {
        ghost.pos.y++;
    }
    ghost.pos.y--;
    
    ghost.matrix.forEach((row, y) => {
        row.forEach((cell, x) => {
            if (cell) {
                drawBlock(x + ghost.pos.x, y + ghost.pos.y, ghost.color, true);
            }
        });
    });
}

function drawPauseScreen() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${BLOCK_SIZE * 1.5}px 'Courier New'`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2 - BLOCK_SIZE);
    
    ctx.font = `${BLOCK_SIZE * 0.8}px 'Courier New'`;
    ctx.fillStyle = '#aaa';
    ctx.fillText('Tap PAUSE to continue', canvas.width / 2, canvas.height / 2 + BLOCK_SIZE);
}

function draw() {
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.strokeStyle = isMobile ? '#333' : '#222';
    ctx.lineWidth = isMobile ? 0.7 : 0.5;
    
    for (let x = 0; x <= COLS; x++) {
        ctx.beginPath();
        ctx.moveTo(x * BLOCK_SIZE, 0);
        ctx.lineTo(x * BLOCK_SIZE, canvas.height);
        ctx.stroke();
    }
    for (let y = 0; y <= ROWS; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * BLOCK_SIZE);
        ctx.lineTo(canvas.width, y * BLOCK_SIZE);
        ctx.stroke();
    }
    
    board.forEach((row, y) => {
        row.forEach((color, x) => {
            if (color) drawBlock(x, y, color);
        });
    });
    
    drawGhostPiece();
    
    if (currentPiece) {
        currentPiece.matrix.forEach((row, y) => {
            row.forEach((cell, x) => {
                if (cell) {
                    drawBlock(x + currentPiece.pos.x, y + currentPiece.pos.y, currentPiece.color);
                }
            });
        });
    }
    
    if (isPaused) {
        drawPauseScreen();
    }
}

// === СОБЫТИЯ ===
function setupEvents() {
    // 4 кнопки
    document.getElementById('left-btn').onclick = () => movePiece(-1);
    document.getElementById('rotate-btn').onclick = rotatePiece;
    document.getElementById('right-btn').onclick = () => movePiece(1);
    document.getElementById('down-btn').onclick = hardDrop; // Быстрое падение
    
    // Пауза
    document.getElementById('pause-btn').onclick = togglePause;
    
    // Свайпы
    let touchStartX = 0;
    let touchStartY = 0;
    
    canvas.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        e.preventDefault();
    }, { passive: false });
    
    canvas.addEventListener('touchend', (e) => {
        if (isPaused) return;
        
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        
        const dx = touchEndX - touchStartX;
        const dy = touchEndY - touchStartY;
        
        const minSwipe = 30;
        
        if (Math.abs(dx) > Math.abs(dy)) {
            if (dx > minSwipe) movePiece(1);
            else if (dx < -minSwipe) movePiece(-1);
        } else {
            if (dy > minSwipe) dropPiece(); // Обычное падение
            else if (dy < -minSwipe) rotatePiece();
        }
        
        e.preventDefault();
    }, { passive: false });
    
    // Клавиатура
    document.addEventListener('keydown', e => {
        if (isGameOver) return;
        
        switch(e.key) {
            case 'ArrowLeft': movePiece(-1); break;
            case 'ArrowRight': movePiece(1); break;
            case 'ArrowDown': dropPiece(); break;
            case 'ArrowUp': rotatePiece(); break;
            case ' ': hardDrop(); break;
            case 'p':
            case 'P':
            case 'Escape': togglePause(); break;
        }
    });
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
        }
    }
    
    draw();
    requestAnimationFrame(gameLoop);
}

// === ИНИЦИАЛИЗАЦИЯ ДОСКИ ===
for (let y = 0; y < ROWS; y++) {
    board[y] = Array(COLS).fill(0);
}

init();