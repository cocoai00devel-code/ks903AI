import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # CORSミドルウェアを追加
from paho.mqtt import client as mqtt_client
import time
from pydantic import BaseModel
import os # <--- 環境変数PORTの取得に必要です

# --- 設定 ---
# 💡 MQTT_BROKER: より安定した公開ブローカー 'broker.hivemq.com' を使用
MQTT_BROKER = "broker.hivemq.com" 
MQTT_PORT = 1883
TOPIC_CONTROL = "/commands/stm32/led" # STM32が購読するトピック
CLIENT_ID = f'python-mqtt-publisher-{time.time()}'
MAX_RETRY_ATTEMPTS = 5 # 接続再試行回数

# Renderなどのクラウド環境で割り当てられるポートを使用。ローカルでは8000を使用。
FASTAPI_PORT = int(os.environ.get("PORT", 8000))

app = FastAPI(title="IoT Control MQTT Backend")

# 💡 CORS設定: フロントエンドからのアクセスを許可
origins = [
    "*", # すべてのオリジンからのアクセスを許可
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Command(BaseModel):
    command: str # "ON" or "OFF"

# --- MQTT 初期化と接続 ---
def connect_mqtt() -> mqtt_client.Client:
    """MQTTブローカーに接続し、バックグラウンドで接続を維持します。"""
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT Broker!")
        else:
            print(f"❌ Failed to connect to MQTT Broker, return code {rc}. Retrying...")

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, CLIENT_ID)
    client.on_connect = on_connect
    
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            print(f"Attempting to connect to MQTT broker ({attempt + 1}/{MAX_RETRY_ATTEMPTS})...")
            client.connect(MQTT_BROKER, MQTT_PORT)
            client.loop_start() 
            # 接続が確立するまで少し待機
            time.sleep(1)
            if client.is_connected():
                return client
        except Exception as e:
            print(f"❌ Connection attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt) # 指数バックオフで待機時間を延長
            
    print("🔴 Max MQTT connection retries reached. Running without broker connection.")
    return None

mqtt_client_instance = connect_mqtt()

# --- Web API エンドポイント ---
@app.post("/control")
def send_command(data: Command):
    """Webから制御コマンドを受け取り、MQTTでSTM32に送信します。"""
    command = data.command
    
    if mqtt_client_instance is None or not mqtt_client_instance.is_connected():
        # MQTT接続が利用できない場合は503エラーを返す
        raise HTTPException(status_code=503, detail="MQTT broker connection unavailable. Command was not published.")

    if command not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Invalid command. Use 'ON' or 'OFF'.")

    # MQTTでパブリッシュ（送信）
    result = mqtt_client_instance.publish(TOPIC_CONTROL, command, qos=1)
    
    status_code = result[0]
    if status_code == 0:
        print(f"🟢 Published command: `{command}` to topic `{TOPIC_CONTROL}`")
        return {"status": "success", "command": command, "message": "Command published to MQTT."}
    else:
        print(f"🔴 Failed to publish message to topic {TOPIC_CONTROL} (Status: {status_code})")
        # パブリッシュ失敗の場合は500エラー
        raise HTTPException(status_code=500, detail="Failed to publish command to MQTT broker.")


# --- 💡 サーバー起動ロジック (ローカル開発用) ---
if __name__ == "__main__":
    # ファイル名が iot_backend.py であることを想定し、uvicornを起動
    uvicorn.run("iot_backend:app", host="0.0.0.0", port=FASTAPI_PORT, reload=True)
