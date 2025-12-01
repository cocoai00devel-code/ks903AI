import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai.errors import APIError
import os # <--- 環境変数にアクセスするためにOSモジュールを追加

# --- 設定 ---
# ⚠️ 修正: APIキーをコードから削除し、環境変数 'GEMINI_API_KEY' から取得します。
# Renderなどのデプロイサービス側でこの環境変数を設定してください。
API_KEY = os.environ.get("GEMINI_API_KEY") 

if not API_KEY:
    # 環境変数からキーが取得できなかった場合の警告
    print("WARNING: API Key is missing. Please set the 'GEMINI_API_KEY' environment variable.")

GEMINI_MODEL = "gemini-2.5-flash"

# --- FastAPI 初期化 ---
app = FastAPI(title="Gemini AI Assistant Backend")

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

class LLMRequest(BaseModel):
    # contentsはリスト構造のGemini API形式ですが、ここでは簡易的に文字列として受け取ります
    prompt: str 
    max_length: int = 1000

class LLMResponse(BaseModel):
    text: str

# Gemini クライアントの初期化 (APIキーがあれば)
client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
        print("✅ Gemini Client Initialized.")
    except Exception as e:
        print(f"🔴 Failed to initialize Gemini Client: {e}")
else:
    print("🔴 Gemini Client not initialized due to missing API Key.")


# --- Web API エンドポイント ---
@app.post("/generate")
def generate_llm_response(request: LLMRequest):
    """
    ユーザーからのプロンプトを受け取り、Geminiモデルで応答を生成します。
    """
    # クライアントが初期化されていない場合は、APIキー不足エラーを返す
    if client is None:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API Client is not available. Please set the 'GEMINI_API_KEY' environment variable in the deployment settings."
        )

    # システムプロンプト: アシスタントとしてのペルソナを設定
    system_prompt = (
        "あなたは人工知能モデルKS-903model8800-a1-90dという名称での親しみやすいAIアシスタント「イマジナリーナンバー 通称GAIイマさん」です。"
        "ユーザーの質問に対して、簡潔で役立つ日本語の応答を生成してください。"
        "会話的なトーンを保ってください。"
    )
    
    try:
        # Gemini APIの呼び出し
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            # FastAPIにシンプルな文字列としてプロンプトを送るため、ここでGeminiのcontents形式に変換
            contents=[request.prompt],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=request.max_length,
                temperature=0.7,
            ),
        )
        
        # 応答テキストを返す
        response_text = response.text.strip()
        
        if not response_text:
             raise APIError("Gemini generated an empty response.")
             
        print(f"✅ Generated response for prompt: '{request.prompt[:30]}...'")
        
        return LLMResponse(text=response_text)

    except APIError as e:
        print(f"🔴 Gemini API Error: {e}")
        # APIエラーをフロントエンドに返す
        raise HTTPException(status_code=500, detail=f"Gemini API generation failed: {e}")
    except Exception as e:
        print(f"🔴 Internal Server Error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error during content generation.")
