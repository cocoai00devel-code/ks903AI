# iot_backend.py
import uvicorn
from fastapi import FastAPI, HTTPException
from paho.mqtt import client as mqtt_client
import time
from pydantic import BaseModel

# --- 設定 ---
# 💡 MQTT_BROKER: 公開テストブローカーの例。本番環境では独自のブローカーを使用してください。
MQTT_BROKER = "mqtt.eclipseprojects.io"  
MQTT_PORT = 1883
TOPIC_CONTROL = "/commands/stm32/led"  # STM32が購読するトピック
CLIENT_ID = f'python-mqtt-publisher-{time.time()}'

app = FastAPI()

class Command(BaseModel):
    command: str # "ON" or "OFF"

# --- MQTT 初期化と接続 ---
def connect_mqtt() -> mqtt_client.Client:
    """MQTTブローカーに接続し、バックグラウンドで接続を維持します。"""
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT Broker!")
        else:
            print(f"❌ Failed to connect to MQTT Broker, return code {rc}")

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, CLIENT_ID)
    client.on_connect = on_connect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_start() 
        return client
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

mqtt_client_instance = connect_mqtt()

# --- Web API エンドポイント ---
@app.post("/control")
def send_command(data: Command):
    """Webから制御コマンドを受け取り、MQTTでSTM32に送信します。"""
    command = data.command
    
    if mqtt_client_instance is None or not mqtt_client_instance.is_connected():
        raise HTTPException(status_code=503, detail="MQTT broker connection unavailable.")

    if command not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Invalid command. Use 'ON' or 'OFF'.")

    # MQTTでパブリッシュ（送信）
    # QoS 1 (少なくとも一度は届く) を使用すると確実性が増します
    result = mqtt_client_instance.publish(TOPIC_CONTROL, command, qos=1)
    
    status_code = result[0]
    if status_code == 0:
        print(f"🟢 Published command: `{command}` to topic `{TOPIC_CONTROL}`")
        return {"status": "success", "command": command, "message": "Command published to MQTT."}
    else:
        print(f"🔴 Failed to publish message to topic {TOPIC_CONTROL} (Status: {status_code})")
        raise HTTPException(status_code=500, detail="Failed to publish command to MQTT.")

# --- サーバー起動方法 ---
# ターミナルで以下を実行してください:
# uvicorn iot_backend:app --reload --port 8000