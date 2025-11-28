const WebApp = window.Telegram.WebApp;

// === КОНФІГ ГРИ ===
const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 15; // Розмір блоку в пікселях
const INITIAL_DROP_SPEED = 1000; // Падіння раз на 1000 мс (1 секунда)

// === СТАН ГРИ ===
let canvas, ctx;
let board = [];
let currentPiece;
let score = 0;
let level = 1;
let dropCounter = 0;
let dropInterval = INITIAL_DROP_SPEED;
let lastTime = 0;
let isGameOver = false;

// === ФІГУРИ TETRIS (ТІЛЬКИ МІНІМАЛЬНИЙ НАБІР) ===
const PIECES = [
    { matrix: [[1, 1], [1, 1]], color: 'yellow' }, // O-форма
    { matrix: [[0, 1, 0], [1, 1, 1], [0, 0, 0]], color: 'purple' }, // T-форма
    { matrix: [[1, 1, 1, 1]], color: 'cyan' } // I-форма
];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    
    // Встановлення розміру канвасу
    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;

    // Створення порожнього ігрового поля
    for (let y = 0; y < ROWS; y++) {
        board[y] = [];
        for (let x = 0; x < COLS; x++) {
            board[y][x] = 0; // 0 означає порожнє місце
        }
    }
    
    setupEvents();
    spawnPiece();
    
    if (WebApp) {
        WebApp.ready();
        WebApp.expand();
        WebApp.BackButton.show();
    }

    // Запуск ігрового циклу
    gameLoop();
}

// === ІГРОВИЙ ЦИКЛ ===
function gameLoop(time = 0) {
    if (isGameOver) return;

    const deltaTime = time - lastTime;
    lastTime = time;

    dropCounter += deltaTime;
    if (dropCounter > dropInterval) {
        dropPiece();
    }

    draw();
    requestAnimationFrame(gameLoop);
}

// === ЛОГІКА ФІГУР ===
function spawnPiece() {
    const randomPiece = PIECES[Math.floor(Math.random() * PIECES.length)];
    currentPiece = {
        matrix: randomPiece.matrix,
        color: randomPiece.color,
        pos: { x: Math.floor(COLS / 2) - Math.floor(randomPiece.matrix[0].length / 2), y: 0 }
    };

    // Перевірка на Game Over
    if (checkCollision(board, currentPiece)) {
        isGameOver = true;
        alert(`Гру завершено! Рахунок: ${score}`);
        // Тут можна додати логіку перезапуску
    }
}

function dropPiece() {
    currentPiece.pos.y++;
    dropCounter = 0;
    if (checkCollision(board, currentPiece)) {
        currentPiece.pos.y--; // Повертаємо назад
        mergePiece(); // Фіксуємо фігуру
        clearLines(); // Очищуємо лінії
        spawnPiece(); // Створюємо нову фігуру
    }
}

function movePiece(dir) {
    currentPiece.pos.x += dir;
    if (checkCollision(board, currentPiece)) {
        currentPiece.pos.x -= dir; // Скасувати рух, якщо зіткнення
    }
}

function rotatePiece() {
    const matrix = currentPiece.matrix;
    const N = matrix.length;
    let newMatrix = matrix.map((row, i) => row.map((_, j) => matrix[N - 1 - j][i]));
    
    // Проста перевірка на зіткнення після обертання
    const originalMatrix = currentPiece.matrix;
    currentPiece.matrix = newMatrix;
    if (checkCollision(board, currentPiece)) {
        currentPiece.matrix = originalMatrix; // Скасувати обертання
    }
}

// === ПЕРЕВІРКА ТА ОЧИЩЕННЯ ===
function checkCollision(board, piece) {
    const [m, p] = [piece.matrix, piece.pos];
    for (let y = 0; y < m.length; y++) {
        for (let x = 0; x < m[y].length; x++) {
            if (m[y][x] !== 0 && (
                board[y + p.y] && board[y + p.y][x + p.x]
            ) !== 0) {
                return true; // Зіткнення з існуючими блоками
            }
            if (m[y][x] !== 0 && (
                x + p.x < 0 || // Зіткнення з лівою стінкою
                x + p.x >= COLS || // Зіткнення з правою стінкою
                y + p.y >= ROWS // Зіткнення з дном
            )) {
                return true;
            }
        }
    }
    return false;
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
                continue outer; // Неповна лінія
            }
        }

        // Лінія повна: очистити
        const row = board.splice(y, 1)[0].fill(0); // Видаляємо та очищаємо
        board.unshift(row); // Додаємо порожню лінію нагору
        y++; // Повторно перевіряємо цю ж позицію (бо всі лінії змістилися)
        updateScore(100);
    }
}

function updateScore(points) {
    score += points;
    document.getElementById('score').innerText = score;
    // Проста логіка підвищення рівня
    level = Math.floor(score / 500) + 1;
    document.getElementById('level').innerText = level;
    dropInterval = Math.max(100, INITIAL_DROP_SPEED - (level - 1) * 50);
}


// === МАЛЮВАННЯ ===
function drawMatrix(matrix, offset, color) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                ctx.fillStyle = color;
                ctx.fillRect((x + offset.x) * BLOCK_SIZE, (y + offset.y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
                ctx.strokeStyle = '#000'; // Додаємо рамку для видимості блоків
                ctx.strokeRect((x + offset.x) * BLOCK_SIZE, (y + offset.y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
            }
        });
    });
}

function draw() {
    // Очищення екрану
    ctx.fillStyle = 'var(--grid)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Малювання ігрового поля (фіксованих блоків)
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
    document.getElementById('left-btn').addEventListener('click', () => movePiece(-1));
    document.getElementById('right-btn').addEventListener('click', () => movePiece(1));
    document.getElementById('down-btn').addEventListener('click', () => {
        dropPiece();
        // Прискорений рух вниз
        dropCounter = dropInterval; 
    });
    document.getElementById('rotate-btn').addEventListener('click', () => rotatePiece());

    // Управління з клавіатури (для тестування на ПК)
    document.addEventListener('keydown', e => {
        if (e.key === 'ArrowLeft') movePiece(-1);
        else if (e.key === 'ArrowRight') movePiece(1);
        else if (e.key === 'ArrowDown') dropPiece();
        else if (e.key === 'ArrowUp') rotatePiece();
    });
}

init();