# app.py (Gradio/GPT-2 Text Generator)

import gradio as gr
from transformers import pipeline

# Hugging Faceのモデルをロード
generator = pipeline("text-generation", model="gpt2")

# GradioでAPI関数を定義
def generate_text(prompt, max_length):
    # GPT-2の応答に、元のプロンプトが含まれるのを避けるために、
    # シンプルな応答だけを抽出する処理を加えても良いですが、ここではシンプルに結果全体を返します。
    result = generator(prompt, max_length=max_length, num_return_sequences=1)
    # 応答からプロンプト部分を削除する処理 (任意)
    generated_text = result[0]['generated_text']
    if generated_text.startswith(prompt):
        return generated_text[len(prompt):].strip()
    return generated_text

# Gradioインターフェースを設定 (APIモードで動作させるために launch() を使用)
gr.Interface(
    fn=generate_text,
    inputs=[
        gr.Textbox(label="Prompt"),
        gr.Slider(minimum=10, maximum=100, label="Max Length")
    ],
    outputs="text",
    title="GPT-2 Text Generator",
    # 💡 GradioをAPIとして利用可能にする
    allow_flagging='never' 
).launch(server_name="127.0.0.1", server_port=7860) 
# 💡 server_nameとserver_portを明示的に指定し、JavaScriptのURLと一致させる