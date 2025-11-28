const WebApp = window.Telegram.WebApp;

// === КОНФІГ ГРИ ===
const COLS = 10;
const ROWS = 20;
let BLOCK_SIZE; // Розмір блоку буде розрахований динамічно
const INITIAL_DROP_SPEED = 1000; // Падіння раз на 1000 мс (1 секунда)
const PIECE_COLOR = '#00ff00'; // Єдиний зелений колір для всіх фігур

// === СТАН ГРИ ===
let canvas, ctx;
let board = [];
let currentPiece;
let dropCounter = 0;
let dropInterval = INITIAL_DROP_SPEED;
let lastTime = 0;
let isGameOver = false;

// === ФІГУРИ TETRIS (тепер усі обертаються коректно) ===
// Матриці та інформація про їхню форму
const PIECES = [
    // O-форма (не обертається, або обертається сама в себе)
    { matrix: [[1, 1], [1, 1]], color: PIECE_COLOR },
    // T-форма
    { matrix: [[0, 1, 0], [1, 1, 1], [0, 0, 0]], color: PIECE_COLOR },
    // I-форма (паличка)
    { matrix: [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]], color: PIECE_COLOR },
    // L-форма
    { matrix: [[0, 1, 0], [0, 1, 0], [0, 1, 1]], color: PIECE_COLOR },
    // J-форма
    { matrix: [[0, 1, 0], [0, 1, 0], [1, 1, 0]], color: PIECE_COLOR },
    // S-форма
    { matrix: [[0, 1, 1], [1, 1, 0], [0, 0, 0]], color: PIECE_COLOR },
    // Z-форма
    { matrix: [[1, 1, 0], [0, 1, 1], [0, 0, 0]], color: PIECE_COLOR }
];

// === ІНІЦІАЛІЗАЦІЯ ===
function init() {
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');

    // Динамічний розрахунок BLOCK_SIZE
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas); // Адаптація при зміні розміру вікна

    // Створення порожнього ігрового поля
    for (let y = 0; y < ROWS; y++) {
        board[y] = Array(COLS).fill(0); // 0 означає порожнє місце
    }

    setupEvents();
    spawnPiece();

    if (WebApp) {
        WebApp.ready();
        WebApp.expand();
        WebApp.BackButton.show();
        // Встановлюємо колір фону Telegram Web App
        WebApp.setBackgroundColor(WebApp.themeParams.bg_color || '#000000');
    }

    // Запуск ігрового циклу
    gameLoop();
}

// === ДИНАМІЧНИЙ РОЗМІР КАНВАСУ ===
function resizeCanvas() {
    const controlsHeight = document.querySelector('.controls').offsetHeight;
    const availableHeight = window.innerHeight - controlsHeight - 20; // 20px - невеликий відступ
    const availableWidth = window.innerWidth - 20;

    // Визначаємо BLOCK_SIZE на основі меншої сторони для збереження пропорцій
    // Ігрове поле COLS x ROWS
    const blockSizeFromWidth = Math.floor(availableWidth / COLS);
    const blockSizeFromHeight = Math.floor(availableHeight / ROWS);

    BLOCK_SIZE = Math.min(blockSizeFromWidth, blockSizeFromHeight);

    canvas.width = COLS * BLOCK_SIZE;
    canvas.height = ROWS * BLOCK_SIZE;

    draw(); // Перемалювати після зміни розміру
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
        // Можна вивести повідомлення через WebApp.showAlert або просто alert
        if (WebApp) {
             WebApp.showAlert('Гру завершено!');
             WebApp.BackButton.hide(); // Приховати кнопку назад, можливо, показати кнопку перезапуску
        } else {
             alert('Гру завершено!');
        }
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
    const originalPos = currentPiece.pos.x;
    currentPiece.pos.x += dir;
    if (checkCollision(board, currentPiece)) {
        currentPiece.pos.x = originalPos; // Скасувати рух, якщо зіткнення
    }
}

function rotate(matrix) {
    const N = matrix.length - 1;
    const result = matrix.map((row, i) =>
        row.map((val, j) => matrix[N - j][i])
    );
    return result;
}

function rotatePiece() {
    const originalMatrix = currentPiece.matrix;
    const originalPos = currentPiece.pos.x;
    currentPiece.matrix = rotate(currentPiece.matrix);

    // Логіка "wall kick" (проста реалізація)
    // Якщо після обертання є зіткнення, спробувати трохи змістити фігуру
    const kicks = [0, 1, -1, 2, -2]; // Спробувати змістити на 0, 1, -1, 2, -2 блоки
    for (const kick of kicks) {
        currentPiece.pos.x = originalPos + kick;
        if (!checkCollision(board, currentPiece)) {
            return; // Знайшли коректну позицію
        }
    }

    // Якщо нічого не допомогло, повертаємося до початкового стану
    currentPiece.matrix = originalMatrix;
    currentPiece.pos.x = originalPos;
}

// === ПЕРЕВІРКА ТА ОЧИЩЕННЯ ===
function checkCollision(board, piece) {
    const [m, p] = [piece.matrix, piece.pos];
    for (let y = 0; y < m.length; y++) {
        for (let x = 0; x < m[y].length; x++) {
            if (m[y][x] !== 0) { // Якщо це блок фігури
                // Перевірка на вихід за межі поля або зіткнення з іншими блоками
                if (
                    x + p.x < 0 || // Ліва межа
                    x + p.x >= COLS || // Права межа
                    y + p.y >= ROWS || // Нижня межа
                    (board[y + p.y] && board[y + p.y][x + p.x] !== 0) // Зіткнення з існуючим блоком на полі
                ) {
                    return true;
                }
            }
        });
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
    let linesCleared = 0;
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
        linesCleared++;
    }
    // Рахунок та рівень видалено
}


// === МАЛЮВАННЯ ===
function drawMatrix(matrix, offset, color) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value !== 0) {
                ctx.fillStyle = color;
                ctx.fillRect((x + offset.x) * BLOCK_SIZE, (y + offset.y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
                ctx.strokeStyle = '#000'; // Чорна рамка для контрасту
                ctx.lineWidth = 1;
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

    // Управління з клавіатури (для тестування на ПК, якщо запускаєте окремо)
    document.addEventListener('keydown', e => {
        if (isGameOver) return;
        if (e.key === 'ArrowLeft') movePiece(-1);
        else if (e.key === 'ArrowRight') movePiece(1);
        else if (e.key === 'ArrowDown') dropPiece();
        else if (e.key === 'ArrowUp') rotatePiece();
    });

    // Обробка кнопки "Назад" у Telegram Web App
    if (WebApp && WebApp.BackButton) {
        WebApp.BackButton.onClick(() => {
            WebApp.close();
        });
    }
}

init();