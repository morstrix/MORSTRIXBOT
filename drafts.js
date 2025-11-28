const WebApp = window.Telegram ? window.Telegram.WebApp : null;

// === КОНФІГ ГРИ ===
const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE = 25; 
const DROP_SPEED = 1000;
const PIECE_COLOR = '#00ff00'; 

// === СТАН ГРИ ===
let canvas, ctx;
let board = [];
let currentPiece;
let dropCounter = 0;
let lastTime = 0;
let isGameOver = false;

// === ФІГУРИ TETRIS ===
const PIECES = [
    { matrix: [[1, 1], [1, 1]] }, // O
    { matrix: [[0, 1, 0], [1, 1, 1], [0, 0, 0]] }, // T
    { matrix: [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]] }, // I
    { matrix: [[0, 1, 0], [0, 1, 0], [0, 1, 1]] }, // L
    { matrix: [[0, 1, 0], [0, 1, 0], [1, 1, 0]] }, // J
    { matrix: [[0, 1, 1], [1, 1, 0], [0, 0, 0]] }, // S
    { matrix: [[1, 1, 0], [0, 1, 1], [0, 0, 0]] }  // Z
];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    
    // Встановлюємо розмір блоку для локального тестування (якщо resizeCanvas не працює)
    BLOCK_SIZE = Math.floor(Math.min(window.innerWidth * 0.9, window.innerHeight * 0.8) / COLS);
    
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;

    // Створення порожнього ігрового поля
    for (let y = 0; y < ROWS; y++) {
        board[y] = Array(COLS).fill(0); 
    }
    
    setupEvents();
    spawnPiece();
    
    if (WebApp) {
        WebApp.ready();
        WebApp.expand();
        WebApp.BackButton.show();
        WebApp.BackButton.onClick(() => WebApp.close());
    }

    gameLoop();
}

// === УТИЛІТИ ===
function rotate(matrix) {
    // Коректне обертання матриці на 90 градусів за годинниковою стрілкою
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
    const randomPiece = PIECES[Math.floor(Math.random() * PIECES.length)];
    currentPiece = {
        matrix: randomPiece.matrix,
        color: PIECE_COLOR, // Завжди зелений
        pos: { x: Math.floor(COLS / 2) - Math.floor(randomPiece.matrix[0].length / 2), y: 0 }
    };
    if (checkCollision(board, currentPiece)) {
        isGameOver = true;
        alert('Гру завершено!');
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

function movePiece(dir) {
    const originalPos = currentPiece.pos.x;
    currentPiece.pos.x += dir;
    if (checkCollision(board, currentPiece)) {
        currentPiece.pos.x = originalPos; 
    }
}

function rotatePiece() {
    const originalMatrix = currentPiece.matrix;
    const originalPos = currentPiece.pos.x;
    currentPiece.matrix = rotate(currentPiece.matrix);

    // Проста перевірка для уникнення застрягання на стінах (Wall Kick)
    const kicks = [0, 1, -1]; 
    for (const kick of kicks) {
        currentPiece.pos.x = originalPos + kick;
        if (!checkCollision(board, currentPiece)) {
            return; 
        }
    }

    // Якщо не вдалося змістити, повертаємося
    currentPiece.matrix = originalMatrix;
    currentPiece.pos.x = originalPos;
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
    outer: for (let y = ROWS - 1; y >= 0; y--) {
        for (let x = 0; x < COLS; x++) {
            if (board[y][x] === 0) {
                continue outer; 
            }
        }
        const row = board.splice(y, 1)[0].fill(0); 
        board.unshift(row); 
        y++; 
    }
}

// === МАЛЮВАННЯ ===
function drawMatrix(matrix, offset, color) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                ctx.fillStyle = color;
                ctx.fillRect((x + offset.x) * BLOCK_SIZE, (y + offset.y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
                ctx.strokeStyle = '#000'; 
                ctx.lineWidth = 1;
                ctx.strokeRect((x + offset.x) * BLOCK_SIZE, (y + offset.y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
            }
        });
    });
}

function draw() {
    ctx.fillStyle = '#111'; // Колір сітки
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Малювання фіксованих блоків
    board.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                drawMatrix([[1]], { x: x, y: y }, value);
            }
        });
    });

    // Малювання поточної фігури
    if (currentPiece) {
        drawMatrix(currentPiece.matrix, currentPiece.pos, currentPiece.color);
    }
}

// === ОБРОБКА ПОДІЙ ===
function setupEvents() {
    // Всі кнопки:
    document.getElementById('left-btn').addEventListener('click', () => movePiece(-1));
    document.getElementById('right-btn').addEventListener('click', () => movePiece(1));
    document.getElementById('down-btn').addEventListener('click', dropPiece);
    document.getElementById('rotate-btn').addEventListener('click', rotatePiece);

    // Клавіатура
    document.addEventListener('keydown', e => {
        if (isGameOver) return;
        if (e.key === 'ArrowLeft') movePiece(-1);
        else if (e.key === 'ArrowRight') movePiece(1);
        else if (e.key === 'ArrowDown') dropPiece();
        else if (e.key === 'ArrowUp' || e.key === ' ') rotatePiece();
    });
}

// === ЦИКЛ ===
function gameLoop(time = 0) {
    if (isGameOver) return;
    const deltaTime = time - lastTime;
    lastTime = time;
    dropCounter += deltaTime;
    if (dropCounter > DROP_SPEED) {
        dropPiece();
    }
    draw();
    requestAnimationFrame(gameLoop);
}

init();