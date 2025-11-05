import os
import random

import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google.cloud import speech, texttospeech

from prompt import create_prompt  # プロンプトを別ファイルから読み込み

# 環境変数の読み込みとAPIクライアントの初期化
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

app = Flask(__name__)

# 会話履歴をサーバー側で保持（プロトタイプのため簡易的に）
conversation_history = []


@app.route("/translate", methods=["POST"])
def translate():
    jp_text = request.json.get("jp_text", "")
    if not jp_text:
        return jsonify({"error": "日本語が入力されていません"}), 400

    # Gemini APIで英訳を生成
    prompt = (
        "あなたは英会話の先生です。以下の日本語を、会話文における自然な英語に翻訳してください。翻訳結果以外を出力する必要はありません。フォーマルなものとカジュアルなものの2パターンのみを出力してください。\n"
        f"日本語: {jp_text}\n"
    )
    model = genai.GenerativeModel("gemini-1.5-flash")
    gemini_response = model.generate_content(prompt)
    en_text = gemini_response.text.strip()

    return jsonify({"en_text": en_text})


# エンドポイント1: 会話開始
@app.route("/start", methods=["POST"])
def start_conversation():
    # 会話履歴をリセット
    conversation_history.clear()

    # テーマ候補をリスト化
    themes = [
        "Let's talk about your favorite movie. What is it?",
        "What country would you like to visit and why?",
        "Tell me about a memorable experience you had.",
        "Do you prefer cats or dogs? Why?",
        "What is your favorite food?",
        "Describe your dream job.",
        "What do you like to do on weekends?",
        "If you could have any superpower, what would it be?",
        "What is a book you recommend?",
        "How do you usually spend your holidays?",
    ]
    selected_theme = random.choice(themes)
    initial_text = f"Hi there! I'm your AI Friend,and your partner for English Speaking. {selected_theme}"

    conversation_history.append({"role": "model", "parts": [initial_text]})

    # 音声合成
    synthesis_input = texttospeech.SynthesisInput(text=initial_text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Standard-C",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return jsonify(
        {
            "text": initial_text,
            "audio_content": response.audio_content.hex(),
        }
    )


# エンドポイント2: ユーザーの音声を受け取り、AIの応答を返す
@app.route("/chat", methods=["POST"])
def chat():
    # 1. 音声データを取得
    audio_file = request.files["audio"]
    audio_content = audio_file.read()

    # 2. Speech-to-Textで文字起こし
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        language_code="en-US",
        model="default",
    )

    # long_running_recognize を使う
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    stt_response = operation.result(timeout=90)

    user_text = (
        stt_response.results[0].alternatives[0].transcript
        if stt_response.results
        else ""
    )

    if not user_text:
        return jsonify({"error": "Could not understand audio"}), 400

    # 会話履歴にユーザーの発言を追加
    conversation_history.append({"role": "user", "parts": [user_text]})

    # 3. Gemini APIで応答と添削を生成
    prompt = create_prompt(conversation_history, user_text)  # プロンプトを生成
    model = genai.GenerativeModel("gemini-1.5-flash")
    gemini_response = model.generate_content(prompt)

    # Geminiからの応答をパースして、応答と添削に分ける
    response_text = gemini_response.text
    ai_reply_text = (
        response_text.split("[CORRECTION]")[0].replace("AI_RESPONSE:", "").strip()
    )
    correction_block = (
        response_text.split("[CORRECTION]")[1].strip()
        if "[CORRECTION]" in response_text
        else ""
    )

    # 添削内容を分割して抽出
    original = corrected = explanation = ""
    for line in correction_block.splitlines():
        if line.startswith("Original:"):
            original = line.replace("Original:", "").strip()
        elif line.startswith("Corrected:"):
            corrected = line.replace("Corrected:", "").strip()
        elif line.startswith("Explanation:"):
            explanation = line.replace("Explanation:", "").strip()

    # 会話履歴にAIの応答を追加
    conversation_history.append({"role": "model", "parts": [ai_reply_text]})

    # 4. Text-to-SpeechでAIの応答を音声化
    synthesis_input = texttospeech.SynthesisInput(text=ai_reply_text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Standard-C",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    tts_response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # 5. フロントエンドに必要な情報をまとめて返す
    return jsonify(
        {
            "user_text": user_text,
            "ai_text": ai_reply_text,
            "correction": {
                "original": original,
                "corrected": corrected,
                "explanation": explanation,
            },
            "audio_content": tts_response.audio_content.hex(),
        }
    )


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":

    app.run(debug=True)
