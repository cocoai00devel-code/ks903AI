import asyncio
import websockets
import json
import numpy as np
import io
import whisper

# サーバー設定 (HTMLのWHISPER_WS_URLと一致させる)
HOST = "localhost"
PORT = 8765

# Whisperモデルのロード (例: 'base.en' または 日本語対応の 'medium' など)
# 初回実行時にダウンロードが行われます
print("Loading Whisper model...")
model = whisper.load_model("small") # small モデルを使用

# 録音データのバッファ
# クライアントが音声データを送ってくる間、ここにデータを溜めます
audio_buffer = []

def process_audio(audio_data):
    """
    溜まった音声データをWhisperモデルで認識する関数
    """
    if not audio_data:
        return ""
    
    # 1. 16bit PCMバイトをfloat32のnumpy配列に変換
    # クライアント側で16-bit PCMが送られていることを想定
    audio_bytes = b"".join(audio_data)
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # 2. 認識処理の実行
    print(f"Recognizing {len(audio_np)/16000:.2f} seconds of audio...")
    # Whisperは16kHzのモノラル音声入力を想定
    result = model.transcribe(audio_np, language="ja") 
    
    return result["text"]

async def handler(websocket, path):
    """
    WebSocketの接続処理を行うメインのハンドラー
    """
    global audio_buffer
    audio_buffer = []
    print(f"Client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # クライアントから音声データ（バイナリ）を受け取った場合
                audio_buffer.append(message)
                
                # 💡 ここで 'partial' 結果をリアルタイムで返すロジックを追加することも可能だが、
                # 今回はシンプルに 'commit' が来るまでバッファリングする
                
            elif isinstance(message, str):
                # クライアントからテキストメッセージを受け取った場合
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
                            print("No speech detected in the buffered audio.")
                            
                except json.JSONDecodeError:
                    # シンプルなテキストメッセージの場合は無視またはログ出力
                    print(f"Received simple string: {message}")
            
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client disconnected gracefully: {websocket.remote_address}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 接続が切れた場合もバッファをクリア
        audio_buffer = []
        print(f"Client handler finished for {websocket.remote_address}")

# async def main():
#     """
#     サーバー起動関数
#     """
#     async with websockets.serve(handler, HOST, PORT):
#         print(f"Whisper WebSocket Server started at ws://{HOST}:{PORT}")
#         await asyncio.Future() # サーバーを永久に実行

# # サーバーは ws://localhost:8765 で起動
async def main():
    # ...
    async with websockets.serve(handler, "localhost", 8765):
        print("Whisper WebSocket Server started at ws://localhost:8765")
        await asyncio.Future() 
# ...

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutting down.")

