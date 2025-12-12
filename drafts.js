const WebApp = window.Telegram ? window.Telegram.WebApp : null;

// === КОНФІГ ГРИ ===
const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE = 25;
let DROP_SPEED = 1000;
const HARD_DROP_SPEED = 50;

// === ТЕМНІ БЕНЗИНОВІ КОЛЬОРИ ===
const PIECE_COLORS = [
    '#1a3a3a', '#2a2a4a', '#3a2a1a', '#1a2a3a',
    '#2a3a2a', '#3a1a2a', '#2a1a3a'
];

// === СТАН ГРИ ===
let canvas, ctx, nextCanvas, nextCtx, mobileNextCanvas, mobileNextCtx;
let board = [];
let currentPiece, nextPiece;
let dropCounter = 0;
let lastTime = 0;
let isGameOver = false;
let score = 0;
let lines = 0;
let level = 1;
let gameSpeed = DROP_SPEED;
let isMobile = window.innerWidth <= 768;

// === ФІГУРИ TETRIS ===
const PIECES = [
    { matrix: [[1, 1], [1, 1]] },
    { matrix: [[0, 1, 0], [1, 1, 1], [0, 0, 0]] },
    { matrix: [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]] },
    { matrix: [[0, 1, 0], [0, 1, 0], [0, 1, 1]] },
    { matrix: [[0, 1, 0], [0, 1, 0], [1, 1, 0]] },
    { matrix: [[0, 1, 1], [1, 1, 0], [0, 0, 0]] },
    { matrix: [[1, 1, 0], [0, 1, 1], [0, 0, 0]] }
];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    
    nextCanvas = document.getElementById('next-piece-canvas');
    nextCtx = nextCanvas.getContext('2d');
    
    mobileNextCanvas = document.getElementById('mobile-next-canvas');
    mobileNextCtx = mobileNextCanvas.getContext('2d');
    
    // Определяем размер блока
    const availableWidth = window.innerWidth * (isMobile ? 0.9 : 0.4);
    const availableHeight = window.innerHeight * (isMobile ? 0.5 : 0.7);
    BLOCK_SIZE = Math.floor(Math.min(availableWidth, availableHeight) / COLS);
    
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;
    
    // Инициализация поля
    for (let y = 0; y < ROWS; y++) {
        board[y] = Array(COLS).fill(0);
    }
    
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
    gameLoop();
    
    // Обработка изменения размера
    window.addEventListener('resize', handleResize);
}

function handleResize() {
    isMobile = window.innerWidth <= 768;
    
    const availableWidth = window.innerWidth * (isMobile ? 0.9 : 0.4);
    const availableHeight = window.innerHeight * (isMobile ? 0.5 : 0.7);
    BLOCK_SIZE = Math.floor(Math.min(availableWidth, availableHeight) / COLS);
    
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;
}

// === УТИЛІТИ ===
function createRandomPiece() {
    const piece = PIECES[Math.floor(Math.random() * PIECES.length)];
    const colorIndex = Math.floor(Math.random() * PIECE_COLORS.length);
    
    return {
        matrix: piece.matrix,
        color: PIECE_COLORS[colorIndex],
        pos: { x: 0, y: 0 }
    };
}

function rotate(matrix) {
    const N = matrix.length - 1;
    return matrix.map((row, i) =>
        row.map((val, j) => matrix[N - j][i])
    );
}

function checkCollision(board, piece) {
    const [m, p] = [piece.matrix, piece.pos];
    for (let y = 0; y < m.length; y++) {
        for (let x = 0; x < m[y].length; x++) {
            if (m[y][x] !== 0) {
                if (
                    x + p.x < 0 ||
                    x + p.x >= COLS ||
                    y + p.y >= ROWS ||
                    (board[y + p.y] && board[y + p.y][x + p.x] !== 0)
                ) {
                    return true;
                }
            }
        }
    }
    return false;
}

// === ІГРОВА ЛОГІКА ===
function spawnPiece() {
    currentPiece = nextPiece;
    nextPiece = createRandomPiece();
    
    currentPiece.pos = {
        x: Math.floor(COLS / 2) - Math.floor(currentPiece.matrix[0].length / 2),
        y: 0
    };
    
    drawNextPiece();
    
    if (checkCollision(board, currentPiece)) {
        isGameOver = true;
        setTimeout(() => {
            alert('ГРУ ЗАВЕРШЕНО! РЕЗУЛЬТАТ: ' + score);
            location.reload();
        }, 300);
    }
}

function dropPiece() {
    currentPiece.pos.y++;
    dropCounter = 0;
    
    if (checkCollision(board, currentPiece)) {
        currentPiece.pos.y--;
        mergePiece();
        clearLines();
        spawnPiece();
    }
}

function hardDrop() {
    let dropDistance = 0;
    
    while (!checkCollision(board, currentPiece)) {
        currentPiece.pos.y++;
        dropDistance++;
    }
    
    currentPiece.pos.y--;
    score += dropDistance * 2;
    
    mergePiece();
    clearLines();
    dropCounter = gameSpeed;
    spawnPiece();
    
    updateUI();
}

function movePiece(dir) {
    const originalPos = currentPiece.pos.x;
    currentPiece.pos.x += dir;
    if (checkCollision(board, currentPiece)) {
        currentPiece.pos.x = originalPos;
    }
}

function rotatePiece() {
    const originalMatrix = currentPiece.matrix;
    currentPiece.matrix = rotate(currentPiece.matrix);
    
    const kicks = [0, 1, -1, 2, -2];
    const originalX = currentPiece.pos.x;
    
    for (const kick of kicks) {
        currentPiece.pos.x = originalX + kick;
        if (!checkCollision(board, currentPiece)) {
            return;
        }
    }
    
    currentPiece.matrix = originalMatrix;
    currentPiece.pos.x = originalX;
}

function mergePiece() {
    currentPiece.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                board[y + currentPiece.pos.y][x + currentPiece.pos.x] = currentPiece.color;
            }
        });
    });
}

function clearLines() {
    let linesCleared = 0;
    
    outer: for (let y = ROWS - 1; y >= 0; y--) {
        for (let x = 0; x < COLS; x++) {
            if (board[y][x] === 0) {
                continue outer;
            }
        }
        
        const row = board.splice(y, 1)[0].fill(0);
        board.unshift(row);
        linesCleared++;
        y++;
    }
    
    if (linesCleared > 0) {
        updateScore(linesCleared);
        updateUI();
    }
}

function updateScore(linesCleared) {
    lines += linesCleared;
    
    const points = [0, 100, 300, 500, 800];
    score += points[linesCleared] * level;
    
    level = Math.floor(lines / 10) + 1;
    gameSpeed = Math.max(50, DROP_SPEED - (level - 1) * 100);
}

function updateUI() {
    // Обновляем десктопную панель
    document.getElementById('score').textContent = score;
    document.getElementById('lines').textContent = lines;
    document.getElementById('level').textContent = level;
    
    // Обновляем мобильный хедер
    document.getElementById('mobile-score').textContent = score;
    document.getElementById('mobile-lines').textContent = lines;
    document.getElementById('mobile-level').textContent = level;
}

// === МАЛЮВАННЯ ===
function drawNextPiece() {
    // Для десктопной панели
    nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
    
    if (!nextPiece) return;
    
    const pieceSize = Math.max(nextPiece.matrix.length, nextPiece.matrix[0].length);
    const blockSize = Math.min(80 / pieceSize, 20);
    const offsetX = (80 - nextPiece.matrix[0].length * blockSize) / 2;
    const offsetY = (80 - nextPiece.matrix.length * blockSize) / 2;
    
    drawPieceOnCanvas(nextCtx, nextPiece.matrix, nextPiece.color, blockSize, offsetX, offsetY);
    
    // Для мобильного хедера
    mobileNextCtx.clearRect(0, 0, mobileNextCanvas.width, mobileNextCanvas.height);
    
    const mobileBlockSize = Math.min(40 / pieceSize, 10);
    const mobileOffsetX = (40 - nextPiece.matrix[0].length * mobileBlockSize) / 2;
    const mobileOffsetY = (40 - nextPiece.matrix.length * mobileBlockSize) / 2;
    
    drawPieceOnCanvas(mobileNextCtx, nextPiece.matrix, nextPiece.color, mobileBlockSize, mobileOffsetX, mobileOffsetY);
}

function drawPieceOnCanvas(context, matrix, color, blockSize, offsetX, offsetY) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                context.fillStyle = color;
                context.fillRect(
                    offsetX + x * blockSize,
                    offsetY + y * blockSize,
                    blockSize,
                    blockSize
                );
                
                context.strokeStyle = '#444';
                context.lineWidth = 1;
                context.strokeRect(
                    offsetX + x * blockSize,
                    offsetY + y * blockSize,
                    blockSize,
                    blockSize
                );
            }
        });
    });
}

function drawMatrix(matrix, offset, color) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                ctx.fillStyle = color;
                ctx.fillRect(
                    (x + offset.x) * BLOCK_SIZE,
                    (y + offset.y) * BLOCK_SIZE,
                    BLOCK_SIZE,
                    BLOCK_SIZE
                );
                
                ctx.fillStyle = darkenColor(color, 0.3);
                ctx.fillRect(
                    (x + offset.x) * BLOCK_SIZE,
                    (y + offset.y) * BLOCK_SIZE,
                    BLOCK_SIZE - 1,
                    2
                );
                ctx.fillRect(
                    (x + offset.x) * BLOCK_SIZE,
                    (y + offset.y) * BLOCK_SIZE,
                    2,
                    BLOCK_SIZE - 1
                );
                
                ctx.fillStyle = lightenColor(color, 0.3);
                ctx.fillRect(
                    (x + offset.x) * BLOCK_SIZE + BLOCK_SIZE - 2,
                    (y + offset.y) * BLOCK_SIZE + 2,
                    2,
                    BLOCK_SIZE - 2
                );
                ctx.fillRect(
                    (x + offset.x) * BLOCK_SIZE + 2,
                    (y + offset.y) * BLOCK_SIZE + BLOCK_SIZE - 2,
                    BLOCK_SIZE - 2,
                    2
                );
            }
        });
    });
}

function darkenColor(color, amount) {
    let r = parseInt(color.substr(1, 2), 16);
    let g = parseInt(color.substr(3, 2), 16);
    let b = parseInt(color.substr(5, 2), 16);
    
    r = Math.floor(r * (1 - amount));
    g = Math.floor(g * (1 - amount));
    b = Math.floor(b * (1 - amount));
    
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function lightenColor(color, amount) {
    let r = parseInt(color.substr(1, 2), 16);
    let g = parseInt(color.substr(3, 2), 16);
    let b = parseInt(color.substr(5, 2), 16);
    
    r = Math.min(255, Math.floor(r * (1 + amount)));
    g = Math.min(255, Math.floor(g * (1 + amount)));
    b = Math.min(255, Math.floor(b * (1 + amount)));
    
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function drawGrid() {
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 0.5;
    
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
}

function drawGhostPiece() {
    if (!currentPiece) return;
    
    const ghost = {
        matrix: currentPiece.matrix,
        color: currentPiece.color,
        pos: { ...currentPiece.pos }
    };
    
    while (!checkCollision(board, ghost)) {
        ghost.pos.y++;
    }
    ghost.pos.y--;
    
    ctx.globalAlpha = 0.2;
    drawMatrix(ghost.matrix, ghost.pos, ghost.color);
    ctx.globalAlpha = 1.0;
}

function draw() {
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    drawGrid();
    
    board.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                drawMatrix([[1]], { x: x, y: y }, value);
            }
        });
    });
    
    drawGhostPiece();
    
    if (currentPiece) {
        drawMatrix(currentPiece.matrix, currentPiece.pos, currentPiece.color);
    }
}

// === ОБРОБКА ПОДІЙ ===
function setupEvents() {
    document.getElementById('left-btn').addEventListener('click', () => movePiece(-1));
    document.getElementById('right-btn').addEventListener('click', () => movePiece(1));
    document.getElementById('rotate-btn').addEventListener('click', rotatePiece);
    document.getElementById('hard-drop-btn').addEventListener('click', hardDrop);
    
    document.addEventListener('keydown', e => {
        if (isGameOver) return;
        
        switch(e.key) {
            case 'ArrowLeft': movePiece(-1); break;
            case 'ArrowRight': movePiece(1); break;
            case 'ArrowDown': dropPiece(); break;
            case 'ArrowUp': rotatePiece(); break;
            case ' ': hardDrop(); break;
        }
    });
    
    document.addEventListener('touchmove', e => e.preventDefault(), { passive: false });
}

// === ГЛАВНИЙ ЦИКЛ ===
function gameLoop(time = 0) {
    if (isGameOver) return;
    
    const deltaTime = time - lastTime;
    lastTime = time;
    
    dropCounter += deltaTime;
    
    if (dropCounter > gameSpeed) {
        dropPiece();
    }
    
    draw();
    requestAnimationFrame(gameLoop);
}

init();