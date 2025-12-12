const WebApp = window.Telegram ? window.Telegram.WebApp : null;

// === КОНФІГ ГРИ ===
const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE = 25;
let DROP_SPEED = 1000;
const HARD_DROP_SPEED = 50; // Швидкість при швидкому опусканні

// === ТЕМНІ БЕНЗИНОВІ КОЛЬОРИ ===
const PIECE_COLORS = [
    '#1a3a3a', // Темний бензиновий зелений
    '#2a2a4a', // Темний фіолетовий
    '#3a2a1a', // Темний коричневий
    '#1a2a3a', // Темний синій
    '#2a3a2a', // Темний оливковий
    '#3a1a2a', // Темний бордовий
    '#2a1a3a'  // Темний індиго
];

// === СТАН ГРИ ===
let canvas, ctx, nextCanvas, nextCtx;
let board = [];
let currentPiece, nextPiece;
let dropCounter = 0;
let lastTime = 0;
let isGameOver = false;
let isHardDrop = false;
let score = 0;
let lines = 0;
let level = 1;
let gameSpeed = DROP_SPEED;

// === ФІГУРИ TETRIS ===
const PIECES = [
    { matrix: [[1, 1], [1, 1]], name: 'O' }, // O
    { matrix: [[0, 1, 0], [1, 1, 1], [0, 0, 0]], name: 'T' }, // T
    { matrix: [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]], name: 'I' }, // I
    { matrix: [[0, 1, 0], [0, 1, 0], [0, 1, 1]], name: 'L' }, // L
    { matrix: [[0, 1, 0], [0, 1, 0], [1, 1, 0]], name: 'J' }, // J
    { matrix: [[0, 1, 1], [1, 1, 0], [0, 0, 0]], name: 'S' }, // S
    { matrix: [[1, 1, 0], [0, 1, 1], [0, 0, 0]], name: 'Z' }  // Z
];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    
    nextCanvas = document.getElementById('next-piece-canvas');
    nextCtx = nextCanvas.getContext('2d');
    
    // Розмір блоку
    BLOCK_SIZE = Math.floor(Math.min(window.innerWidth * 0.4, window.innerHeight * 0.7) / COLS);
    
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;
    
    // Ініціалізація поля
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
}

// === УТИЛІТИ ===
function createRandomPiece() {
    const piece = PIECES[Math.floor(Math.random() * PIECES.length)];
    const colorIndex = Math.floor(Math.random() * PIECE_COLORS.length);
    
    return {
        matrix: piece.matrix,
        color: PIECE_COLORS[colorIndex],
        name: piece.name,
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
        alert('ГРУ ЗАВЕРШЕНО! РЕЗУЛЬТАТ: ' + score);
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
        isHardDrop = false;
    }
}

function hardDrop() {
    isHardDrop = true;
    let dropDistance = 0;
    
    while (!checkCollision(board, currentPiece)) {
        currentPiece.pos.y++;
        dropDistance++;
    }
    
    currentPiece.pos.y--;
    dropCounter = 0;
    
    // Бонуси за швидке опускання
    score += dropDistance * 2;
    mergePiece();
    clearLines();
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
        
        // Видалити заповнену лінію
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
    
    // Бали за лінії
    const points = [0, 100, 300, 500, 800];
    score += points[linesCleared] * level;
    
    // Оновлення рівня
    level = Math.floor(lines / 10) + 1;
    
    // Збільшення швидкості
    gameSpeed = Math.max(50, DROP_SPEED - (level - 1) * 100);
}

function updateUI() {
    document.getElementById('score').textContent = score;
    document.getElementById('lines').textContent = lines;
    document.getElementById('level').textContent = level;
}

// === МАЛЮВАННЯ ===
function drawMatrix(matrix, offset, color) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                // Основний блок
                ctx.fillStyle = color;
                ctx.fillRect(
                    (x + offset.x) * BLOCK_SIZE,
                    (y + offset.y) * BLOCK_SIZE,
                    BLOCK_SIZE,
                    BLOCK_SIZE
                );
                
                // Темніша тінь зверху/зліва
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
                
                // Світліший край знизу/справа
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
    
    // Вертикальні лінії
    for (let x = 0; x <= COLS; x++) {
        ctx.beginPath();
        ctx.moveTo(x * BLOCK_SIZE, 0);
        ctx.lineTo(x * BLOCK_SIZE, canvas.height);
        ctx.stroke();
    }
    
    // Горизонтальні лінії
    for (let y = 0; y <= ROWS; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * BLOCK_SIZE);
        ctx.lineTo(canvas.width, y * BLOCK_SIZE);
        ctx.stroke();
    }
}

function drawGhostPiece() {
    if (!currentPiece || isHardDrop) return;
    
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

function drawNextPiece() {
    nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
    
    if (!nextPiece) return;
    
    // Центрування фігури
    const pieceSize = Math.max(nextPiece.matrix.length, nextPiece.matrix[0].length);
    const blockSize = Math.min(80 / pieceSize, 20);
    const offsetX = (80 - nextPiece.matrix[0].length * blockSize) / 2;
    const offsetY = (80 - nextPiece.matrix.length * blockSize) / 2;
    
    nextPiece.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                nextCtx.fillStyle = nextPiece.color;
                nextCtx.fillRect(
                    offsetX + x * blockSize,
                    offsetY + y * blockSize,
                    blockSize,
                    blockSize
                );
                
                // Рамка
                nextCtx.strokeStyle = '#444';
                nextCtx.lineWidth = 1;
                nextCtx.strokeRect(
                    offsetX + x * blockSize,
                    offsetY + y * blockSize,
                    blockSize,
                    blockSize
                );
            }
        });
    });
}

function draw() {
    // Фон
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    drawGrid();
    
    // Малювання фіксованих блоків
    board.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                drawMatrix([[1]], { x: x, y: y }, value);
            }
        });
    });
    
    // Привид фігури
    drawGhostPiece();
    
    // Поточна фігура
    if (currentPiece) {
        drawMatrix(currentPiece.matrix, currentPiece.pos, currentPiece.color);
    }
}

// === ОБРОБКА ПОДІЙ ===
function setupEvents() {
    // Кнопки управління
    document.getElementById('left-btn').addEventListener('click', () => movePiece(-1));
    document.getElementById('right-btn').addEventListener('click', () => movePiece(1));
    document.getElementById('rotate-btn').addEventListener('click', rotatePiece);
    document.getElementById('hard-drop-btn').addEventListener('click', hardDrop);
    
    // Клавіатура
    document.addEventListener('keydown', e => {
        if (isGameOver) return;
        
        switch(e.key) {
            case 'ArrowLeft': movePiece(-1); break;
            case 'ArrowRight': movePiece(1); break;
            case 'ArrowDown': dropPiece(); break;
            case 'ArrowUp': rotatePiece(); break;
            case ' ': hardDrop(); break; // Пробіл для швидкого опускання
        }
    });
    
    // Заборона прокрутки при свайпах
    document.addEventListener('touchmove', e => e.preventDefault(), { passive: false });
}

// === ГЛАВНИЙ ЦИКЛ ===
function gameLoop(time = 0) {
    if (isGameOver) return;
    
    const deltaTime = time - lastTime;
    lastTime = time;
    
    dropCounter += deltaTime;
    
    const speed = isHardDrop ? HARD_DROP_SPEED : gameSpeed;
    
    if (dropCounter > speed) {
        dropPiece();
    }
    
    draw();
    requestAnimationFrame(gameLoop);
}

init();