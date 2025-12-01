// hd_tetris/tetris.js

// --- 定数と設定 ---
const COLS = 10;        
const ROWS = 20;        
const BLOCK_SIZE = 20;  
const canvas = document.getElementById('tetris-board');
const ctx = canvas.getContext('2d');
canvas.width = COLS * BLOCK_SIZE;
canvas.height = ROWS * BLOCK_SIZE;

// --- ゲーム状態変数 ---
let board = [];
let currentPiece;
let score = 0;
let gameOver = false;
let lastTime = 0;
const dropInterval = 1000; 

// ブロックの定義
const PIECES = [
    { shape: [[1,1,1,1]], color: 'cyan' }, 
    { shape: [[1,1],[1,1]], color: 'yellow' }, 
    { shape: [[0,1,0],[1,1,1]], color: 'purple' }, 
    { shape: [[1,0,0],[1,1,1]], color: 'blue' }, 
    { shape: [[0,0,1],[1,1,1]], color: 'orange' }, 
    { shape: [[0,1,1],[1,1,0]], color: 'green' }, 
    { shape: [[1,1,0],[0,1,1]], color: 'red' }, 
];

// --- ヘルパー関数 ---

function initializeBoard() {
    board = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
    currentPiece = generateRandomPiece();
}

function draw() {
    ctx.fillStyle = '#0d0d1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawBlocks(board); 
    if (currentPiece) {
        drawBlocks(currentPiece.shape, currentPiece.x, currentPiece.y, currentPiece.color);
    }
}

function drawBlocks(shapeOrBoard, offsetX = 0, offsetY = 0, color = null) {
    shapeOrBoard.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                // boardの要素は直接色文字列が入っていると仮定
                ctx.fillStyle = color || (typeof value === 'string' ? value : PIECES[value - 1].color); 
                ctx.fillRect((x + offsetX) * BLOCK_SIZE, (y + offsetY) * BLOCK_SIZE, BLOCK_SIZE - 1, BLOCK_SIZE - 1);
            }
        });
    });
}

function isValidMove(piece, dx, dy, newShape = piece.shape) {
    for (let y = 0; y < newShape.length; y++) {
        for (let x = 0; x < newShape[y].length; x++) {
            if (newShape[y][x]) {
                const newX = piece.x + x + dx;
                const newY = piece.y + y + dy;

                if (newX < 0 || newX >= COLS || newY >= ROWS) return false;
                
                if (newY >= 0 && newY < ROWS && newX >= 0 && newX < COLS && board[newY][newX]) return false;
            }
        }
    }
    return true;
}

function rotateMatrix(matrix) { 
    const N = matrix.length - 1;
    const result = matrix.map((row, i) => row.map((val, j) => matrix[N - j][i]));
    return result;
}

function lockPiece() {
    currentPiece.shape.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) {
                // 盤面にブロックの色を保存
                if (currentPiece.y + y >= 0 && currentPiece.y + y < ROWS) {
                    board[currentPiece.y + y][currentPiece.x + x] = currentPiece.color;
                }
            }
        });
    });
}

function clearLines() { 
    let linesCleared = 0;
    for (let y = ROWS - 1; y >= 0; y--) {
        if (board[y].every(value => value)) {
            board.splice(y, 1); 
            board.unshift(Array(COLS).fill(0)); 
            linesCleared++;
            y++;
        }
    }
    if (linesCleared > 0) Game.updateScore(linesCleared);
}

function generateRandomPiece() {
    const typeId = Math.floor(Math.random() * PIECES.length);
    const piece = PIECES[typeId];
    return {
        shape: piece.shape,
        color: piece.color,
        x: Math.floor(COLS / 2) - Math.floor(piece.shape[0].length / 2),
        y: -piece.shape.length // 上端から出現させる
    };
}

// --- メインループ ---
function dropPiece() {
    if (!isValidMove(currentPiece, 0, 1)) {
        lockPiece();
        clearLines();
        currentPiece = generateRandomPiece();
        
        // ゲームオーバー判定
        if (!isValidMove(currentPiece, 0, 0)) {
            gameOver = true;
            if (window.AudioModule && AudioModule.stopBGM) AudioModule.stopBGM();
            console.log("GAME OVER");
            // ... ゲームオーバー表示 ...
        }
        return;
    }
    currentPiece.y++;
}

function gameLoop(time = 0) {
    if (gameOver) return;
    
    const deltaTime = time - lastTime;
    if (deltaTime > dropInterval) {
        dropPiece();
        lastTime = time;
    }

    draw();
    requestAnimationFrame(gameLoop);
}

// --- ハンドトラッキング操作とゲーム開始 (Gameオブジェクト) ---
window.Game = { 
    score: 0,
    
    updateScore: (linesCleared) => {
        if (linesCleared > 0) {
            score += linesCleared * 100;
            if (window.AudioModule) AudioModule.playSound('lineClear'); 
        }
        document.getElementById('score').innerText = score;
    },

    moveLeft: () => {
        if (gameOver || !currentPiece) return;
        if (!isValidMove(currentPiece, -1, 0)) return;
        currentPiece.x--;
    },
    
    moveRight: () => {
        if (gameOver || !currentPiece) return;
        if (!isValidMove(currentPiece, 1, 0)) return;
        currentPiece.x++;
    },

    rotate: () => {
        if (gameOver || !currentPiece) return;
        const rotatedShape = rotateMatrix(currentPiece.shape);
        if (isValidMove({ ...currentPiece, shape: rotatedShape }, 0, 0)) {
            currentPiece.shape = rotatedShape;
            if (window.AudioModule) AudioModule.playSound('rotate');
        }
    },

    hardDrop: () => {
        if (gameOver || !currentPiece) return;
        while (isValidMove(currentPiece, 0, 1)) {
            currentPiece.y++;
        }
        lockPiece(); 
        clearLines();
        currentPiece = generateRandomPiece();
        if (window.AudioModule) AudioModule.playSound('hardDrop');
    },

    start: () => {
        initializeBoard();
        score = 0;
        gameOver = false;
        lastTime = 0;
        gameLoop();
    }
};