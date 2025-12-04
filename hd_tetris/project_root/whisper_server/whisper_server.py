import asyncio
import websockets
import json
import numpy as np
import os # 環境変数にアクセスするために追加
import whisper

# --- サーバー設定 ---
# 修正: HOSTを0.0.0.0に設定し、外部からの接続を許可
HOST = "0.0.0.0" 
# 修正: PORTを環境変数から取得。クラウドデプロイに対応。ローカルでは8765をデフォルトとする
PORT = int(os.environ.get("PORT", 8765))

# Whisperモデルのロード
# 'small'モデルは速度と精度のバランスが取れていますが、リソース消費に注意。
print("Loading Whisper model...")
# 💡 クラウドの無料環境でクラッシュする場合は、"tiny" や "base" を試してください。
# model = whisper.load_model("small") 
# 💡 クラウドの無料環境でクラッシュする場合は、"tiny" や "base" を試してください。の都合上とレスポンス動作を早くするため"tiny"を推奨とする。
model = whisper.load_model("tiny") 
def process_audio(audio_data):
    """
    溜まった音声データをWhisperモデルで認識する関数
    """
    if not audio_data:
        return ""
    
    # 1. 16bit PCMバイトをfloat32のnumpy配列に変換
    # クライアント側で16-bit PCMが送られていることを想定
    audio_bytes = b"".join(audio_data)
    # NumPy配列に変換し、±1の範囲に正規化
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # 2. 認識処理の実行
    audio_duration = len(audio_np) / 16000
    if audio_duration < 0.5:
        print(f"Skipping short audio: {audio_duration:.2f} seconds.")
        return ""

    print(f"Recognizing {audio_duration:.2f} seconds of audio...")
    # Whisperは16kHzのモノラル音声入力を想定。言語は "ja" (日本語) を指定。
    result = model.transcribe(audio_np, language="ja") 
    
    return result["text"]

async def handler(websocket, path):
    """
    WebSocketの接続処理を行うメインのハンドラー。
    接続ごとに独立したオーディオバッファを管理します。
    """
    # 接続ごとのバッファをローカルに初期化
    audio_buffer = [] 
    print(f"Client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # クライアントから音声データ（バイナリ）を受け取った場合
                audio_buffer.append(message)
                
            elif isinstance(message, str):
                # クライアントからテキストメッセージ（commit信号）を受け取った場合
                try:
                    data = json.loads(message)
                    if data.get("type") == "commit":
                        # VAD（無音検出）により、クライアントが認識完了を通知した場合
                        print("Commit signal received. Starting transcription...")
                        
                        # 認識処理を実行
                        final_text = process_audio(audio_buffer)
                        audio_buffer = [] # バッファをクリア
                        
                        if final_text:
                            # 最終結果をクライアントにJSON形式で送信
                            response = {"type": "final", "text": final_text}
                            await websocket.send(json.dumps(response))
                            print(f"Sent final result: {final_text}")
                        else:
                            print("No significant speech detected in the buffered audio.")
                            
                except json.JSONDecodeError:
                    print(f"Received non-JSON string: {message}")
            
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client disconnected gracefully: {websocket.remote_address}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 接続が切れた場合もバッファをクリア（念のため）
        audio_buffer = []
        print(f"Client handler finished for {websocket.remote_address}")

async def main():
    """
    サーバー起動関数
    """
    # websockets.serve関数を使用して、指定されたホストとポートでサーバーを起動
    async with websockets.serve(handler, HOST, PORT):
        print(f"✅ Whisper WebSocket Server started at ws://{HOST}:{PORT}")
        await asyncio.Future() # サーバーを永久に実行

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutting down.")

