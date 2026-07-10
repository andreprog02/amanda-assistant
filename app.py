import os
import tempfile
import base64
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import anthropic
from prompt import AMANDA_PROMPT

load_dotenv()

app = FastAPI()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("MODEL", "claude-sonnet-4-6")

# Whisper — carrega o modelo na primeira vez (demora um pouco no 1o boot)
whisper_model = None

def get_whisper():
    global whisper_model
    if whisper_model is None:
        import whisper
        print("🎤 Carregando modelo Whisper (primeira vez pode demorar)...")
        whisper_model = whisper.load_model("base")
        print("✅ Whisper pronto!")
    return whisper_model


def get_claude_reply(messages: list) -> str:
    """Manda mensagens pro Claude e retorna a resposta."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=AMANDA_PROMPT,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


async def generate_tts(text: str) -> str:
    """Gera áudio com Edge TTS e retorna base64."""
    import edge_tts
    import re

    # Remove emojis antes de mandar pro TTS
    text_clean = re.sub(
        r'[\U00002702-\U000027B0'
        r'\U0000FE00-\U0000FE0F'
        r'\U0001F000-\U0001FFFF'
        r'\U00002600-\U000027BF'
        r'\U0000FE00-\U0000FE0F'
        r'\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F'
        r'\U0001FA70-\U0001FAFF'
        r'\U00002702-\U000027B0'
        r'\U0000231A-\U0000231B'
        r'\U00002328'
        r'\U000023CF'
        r'\U000023E9-\U000023F3'
        r'\U000023F8-\U000023FA'
        r'\U00002934-\U00002935'
        r'\U000025AA-\U000025AB'
        r'\U000025B6'
        r'\U000025C0'
        r'\U000025FB-\U000025FE'
        r'\U00002B05-\U00002B07'
        r'\U00002B1B-\U00002B1C'
        r'\U00002B50'
        r'\U00002B55'
        r'\U00003030'
        r'\U0000303D'
        r'\U00003297'
        r'\U00003299'
        r'\u200d'
        r'\ufe0f]+',
        '', text
    ).strip()

    if not text_clean:
        return None

    voice = "pt-BR-FranciscaNeural"

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        audio_path = f.name

    communicate = edge_tts.Communicate(text_clean, voice)
    await communicate.save(audio_path)

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    os.unlink(audio_path)
    return audio_b64


# ── Endpoint: chat por texto (mantém compatibilidade) ──
@app.post("/api/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        messages = body.get("messages", [])

        # 1. Pega resposta do Claude
        try:
            reply = get_claude_reply(messages)
        except Exception as e:
            print(f"❌ Erro no Claude: {e}")
            return JSONResponse(
                {"reply": "Hmm, algo deu errado com meu cérebro... tenta de novo? 💕", "audio": None},
                status_code=500,
            )

        # 2. Gera áudio (se falhar, retorna só texto)
        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS (retornando só texto): {e}")

        return JSONResponse({"reply": reply, "audio": audio_b64})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"reply": "Hmm, algo deu errado... me perdoa? Tenta mais uma vez 💕", "audio": None},
            status_code=500,
        )


# ── Endpoint: chat por voz ──
@app.post("/api/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    history: str = Form(default="[]"),
):
    try:
        import json

        # 1. Salva o áudio recebido
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            content = await audio.read()
            f.write(content)
            temp_path = f.name

        # 2. Transcreve com Whisper
        model = get_whisper()
        result = model.transcribe(temp_path, language="pt")
        user_text = result["text"].strip()
        os.unlink(temp_path)

        if not user_text:
            return JSONResponse({"user_text": "", "reply": "Não consegui ouvir... fala de novo? 🥺", "audio": None})

        # 3. Monta histórico + nova mensagem
        messages = json.loads(history)
        messages.append({"role": "user", "content": user_text})

        # 4. Pega resposta do Claude
        reply = get_claude_reply(messages)

        # 5. Gera áudio da resposta
        audio_b64 = await generate_tts(reply)

        return JSONResponse({
            "user_text": user_text,
            "reply": reply,
            "audio": audio_b64,
        })

    except Exception as e:
        print(f"Erro no voice: {e}")
        return JSONResponse(
            {"user_text": "", "reply": "Ai, deu um probleminha... tenta de novo? 🥺", "audio": None},
            status_code=500,
        )


# Serve o frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    import threading
    import webview

    def start_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("\n✨ Amanda tá online!\n")

    webview.create_window(
        "Amanda",
        "http://127.0.0.1:8000",
        width=420,
        height=720,
        resizable=True,
        min_size=(360, 500),
        x=None,
        y=30,
    )
    webview.start()
