# app.py (Gradio/GPT-2 Text Generator)

import gradio as gr
from transformers import pipeline

# Hugging Faceのモデルをロード
# gpt2 モデルは多言語に対応していますが、日本語の応答品質はそれほど高くありません。
# より高品質な日本語応答が必要な場合は、rinna/japanese-gpt2-medium などにモデル名を変更してください。
generator = pipeline("text-generation", model="gpt2")

# GradioでAPI関数を定義
def generate_text(prompt, max_length):
    # GPT-2によるテキスト生成を実行
    result = generator(
        prompt, 
        max_length=max_length, 
        num_return_sequences=1,
        # 応答にプロンプトを再表示させないための設定 (モデルによっては完全に機能しない場合があります)
        return_full_text=False 
    )
    
    # 結果のリストから生成されたテキストを抽出
    generated_text = result[0]['generated_text']
    
    # 応答から元のプロンプトが冒頭に含まれている場合、その部分を削除する処理
    # generated_textはプロンプトの続きとして生成されるため、この処理が必要です。
    
    # 応答からプロンプト部分を削除する処理 (より厳密な処理)
    if generated_text.startswith(prompt):
        # generated_textがプロンプトで始まる場合、プロンプトの長さ以降を返す
        return generated_text[len(prompt):].strip()
        
    # generated_textがプロンプトで始まらない場合、そのまま返す
    return generated_text.strip()

# Gradioインターフェースを設定
iface = gr.Interface(
    fn=generate_text,
    inputs=[
        gr.Textbox(label="Prompt"),
        # Webフロントエンド (JavaScript) は Max Length = 80 を送信します
        gr.Slider(minimum=10, maximum=100, label="Max Length", value=80) 
    ],
    outputs="text",
    title="GPT-2 Text Generator",
    # 💡 GradioをAPIとして利用可能にする
    allow_flagging='never' 
)

# 💡 server_nameとserver_portを明示的に指定し、JavaScriptのURLと一致させる
# ターミナルでこのファイルを実行してください: python app.py
iface.launch(server_name="127.0.0.1", server_port=7860)