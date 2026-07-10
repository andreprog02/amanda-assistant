import os
import json
import tempfile
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import anthropic
from prompt import AMANDA_PROMPT
from database import (
    init_db, create_conversation, get_latest_conversation,
    save_message, get_conversation_messages, get_all_memories,
    get_memories_summary, save_memory,
)

load_dotenv()

app = FastAPI()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("MODEL", "claude-sonnet-4-6")

# Inicializa banco na startup
@app.on_event("startup")
def startup():
    init_db()

# Conversa atual
current_conversation_id = None

def get_or_create_conversation() -> int:
    global current_conversation_id
    if current_conversation_id is None:
        current_conversation_id = create_conversation()
        print(f"📝 Nova conversa #{current_conversation_id}")
    return current_conversation_id

# Whisper
whisper_model = None
def get_whisper():
    global whisper_model
    if whisper_model is None:
        import whisper
        print("🎤 Carregando modelo Whisper...")
        whisper_model = whisper.load_model("base")
        print("✅ Whisper pronto!")
    return whisper_model


def build_system_prompt() -> str:
    """Monta o prompt da Amanda + memórias do usuário."""
    memories = get_memories_summary()
    if memories:
        return AMANDA_PROMPT + "\n\n" + memories
    return AMANDA_PROMPT


def get_claude_reply(messages: list) -> str:
    """Manda mensagens pro Claude com memórias incluídas."""
    system = build_system_prompt()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def extract_memories(user_text: str, msg_id: int):
    """Usa o Claude pra extrair fatos importantes da mensagem do usuário."""
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system="""Você é um extrator de informações. Analise a mensagem do usuário e extraia APENAS fatos concretos e pessoais sobre ele.

Responda APENAS em JSON, sem markdown, sem explicação. Formato:
[{"category": "categoria", "content": "fato", "importance": 1-10}]

Categorias possíveis: nome, idade, trabalho, estudo, hobbies, gostos, familia, relacionamento, humor_do_dia, sonhos, rotina, saude, localizacao, pets, comida_favorita, musica, filmes, outros

Exemplos:
- "Meu nome é João" → [{"category": "nome", "content": "Se chama João", "importance": 10}]
- "Tô estudando pra prova de matemática" → [{"category": "estudo", "content": "Está estudando matemática, tem prova", "importance": 6}]
- "Oi tudo bem?" → []

Se não houver fatos pessoais, retorne: []
NÃO invente informações. Extraia APENAS o que está explícito.""",
            messages=[{"role": "user", "content": user_text}],
        )

        text = "".join(b.text for b in response.content if b.type == "text").strip()
        text = text.replace("```json", "").replace("```", "").strip()

        facts = json.loads(text)
        for fact in facts:
            if fact.get("content"):
                save_memory(
                    category=fact.get("category", "outros"),
                    content=fact["content"],
                    source_message_id=msg_id,
                    importance=fact.get("importance", 5),
                )
                print(f"💾 Memória salva: [{fact.get('category')}] {fact['content']}")

    except Exception as e:
        print(f"⚠️ Erro ao extrair memórias: {e}")


async def generate_tts(text: str) -> str:
    """Gera áudio com ElevenLabs e retorna base64."""
    import re
    import httpx

    text_clean = re.sub(
        r'[\U00002702-\U000027B0'
        r'\U0000FE00-\U0000FE0F'
        r'\U0001F000-\U0001FFFF'
        r'\U00002600-\U000027BF'
        r'\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F'
        r'\U0001FA70-\U0001FAFF'
        r'\U00002934-\U00002935'
        r'\U0000231A-\U0000231B'
        r'\u200d\ufe0f]+',
        '', text
    ).strip()

    if not text_clean:
        return None

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "tnSpp4vdxKPjI9w0GnoV")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    async with httpx.AsyncClient(timeout=30.0) as client_http:
        response = await client_http.post(
            url,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text_clean,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.75,
                    "style": 0.6,
                    "use_speaker_boost": True,
                },
            },
        )

        if response.status_code != 200:
            print(f"⚠️ ElevenLabs erro {response.status_code}: {response.text}")
            return None

        audio_b64 = base64.b64encode(response.content).decode()
        return audio_b64


# ── Endpoint: chat por texto ──
@app.post("/api/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        messages = body.get("messages", [])
        conv_id = get_or_create_conversation()

        # Salva mensagem do usuário
        user_content = messages[-1]["content"] if messages else ""
        user_msg_id = save_message(conv_id, "user", user_content)

        # Extrai memórias em background
        if user_content:
            extract_memories(user_content, user_msg_id)

        # Pega resposta com memórias injetadas
        try:
            reply = get_claude_reply(messages)
        except Exception as e:
            print(f"❌ Erro no Claude: {e}")
            return JSONResponse(
                {"reply": "Hmm, algo deu errado... tenta de novo?", "audio": None},
                status_code=500,
            )

        # Salva resposta da Amanda
        save_message(conv_id, "assistant", reply)

        # Gera áudio
        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        return JSONResponse({"reply": reply, "audio": audio_b64})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"reply": "Hmm, algo deu errado... me perdoa?", "audio": None},
            status_code=500,
        )


# ── Endpoint: chat por voz ──
@app.post("/api/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    history: str = Form(default="[]"),
):
    try:
        conv_id = get_or_create_conversation()

        # 1. Transcreve
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            content = await audio.read()
            f.write(content)
            temp_path = f.name

        model = get_whisper()
        result = model.transcribe(temp_path, language="pt")
        user_text = result["text"].strip()
        os.unlink(temp_path)

        if not user_text:
            return JSONResponse({"user_text": "", "reply": "Não consegui ouvir... fala de novo?", "audio": None})

        # 2. Salva mensagem e extrai memórias
        user_msg_id = save_message(conv_id, "user", user_text)
        extract_memories(user_text, user_msg_id)

        # 3. Monta histórico + resposta
        messages = json.loads(history)
        messages.append({"role": "user", "content": user_text})
        reply = get_claude_reply(messages)

        # 4. Salva resposta
        save_message(conv_id, "assistant", reply)

        # 5. Gera áudio
        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        return JSONResponse({
            "user_text": user_text,
            "reply": reply,
            "audio": audio_b64,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"user_text": "", "reply": "Ai, deu um probleminha... tenta de novo?", "audio": None},
            status_code=500,
        )


# ── Endpoint: ver memórias (debug) ──
@app.get("/api/memories")
async def list_memories():
    memories = get_all_memories()
    return JSONResponse({"memories": memories})


# Frontend
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
