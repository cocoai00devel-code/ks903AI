// hd_tetris/handtracker.js (正しいトラッキングロジック)

// --- 定数と状態変数 ---
const MOVEMENT_THRESHOLD = 0.05; 
const MOVEMENT_COOLDOWN_MS = 150; // 左右移動用のクールダウン
let lastMoveTime = 0;
let lastHandX = 0; 
let isHandClosed = false; 
let isHardDropTriggered = false;

// Cameraの起動とトラッキング開始を関数化
window.startHandTracking = () => {
    const videoElement = document.getElementById('camera-video');

    // MediaPipe Handsの初期化
    const hands = new Hands({locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
    }});

    hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
    });

    hands.onResults((results) => {
        const now = Date.now();
        
        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            const landmarks = results.multiHandLandmarks[0];
            
            // --- A. ブロックの左右移動判定 (クールダウン適用) ---
            const currentHandX = landmarks[0].x; 
            
            // Gameオブジェクトがロードされているか確認
            if (!window.Game) return; 

            if (lastHandX !== 0 && now - lastMoveTime > MOVEMENT_COOLDOWN_MS) {
                const diffX = currentHandX - lastHandX;
                
                if (diffX > MOVEMENT_THRESHOLD) {
                    Game.moveRight(); 
                    lastMoveTime = now;
                } else if (diffX < -MOVEMENT_THRESHOLD) {
                    Game.moveLeft(); 
                    lastMoveTime = now;
                }
            }
            lastHandX = currentHandX;

            // --- B. ブロックの回転判定（グー） ---
            const isIndexFingerDown = landmarks[8].y > landmarks[6].y;
            const isMiddleFingerDown = landmarks[12].y > landmarks[10].y;
            const isNewHandClosed = isIndexFingerDown && isMiddleFingerDown; 

            if (isNewHandClosed && !isHandClosed) {
                Game.rotate();
            }
            isHandClosed = isNewHandClosed;

            // --- C. ハードドロップ判定（ピンチ） ---
            const thumbTip = landmarks[4];
            const indexTip = landmarks[8];
            const distance = Math.sqrt(Math.pow(thumbTip.x - indexTip.x, 2) + Math.pow(thumbTip.y - indexTip.y, 2));
            
            if (distance < 0.05 && !isHardDropTriggered) {
                 Game.hardDrop();
                 isHardDropTriggered = true; 
            } else if (distance >= 0.08) {
                 isHardDropTriggered = false; 
            }

        } else {
            // 手が検出されない場合のリセット
            lastHandX = 0;
            isHardDropTriggered = false;
        }
    });

    // カメラの起動
    const camera = new Camera(videoElement, {
        onFrame: async () => {
            await hands.send({image: videoElement});
        },
        width: 640,
        height: 480
    });
    camera.start();
};