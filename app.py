import os
import json
import random
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
from news import get_news_context
from mood import get_mood_context
from environment import get_expression_image, get_environment_context

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
    """Monta o prompt da Amanda + memórias + consciência de tempo."""
    from datetime import datetime
    import locale

    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except:
        pass

    now = datetime.now()
    hora = now.hour
    minuto = now.minute

    # Período do dia
    if 5 <= hora < 12:
        periodo = "manhã"
        saudacao = "Bom dia"
    elif 12 <= hora < 18:
        periodo = "tarde"
        saudacao = "Boa tarde"
    elif 18 <= hora < 22:
        periodo = "noite"
        saudacao = "Boa noite"
    else:
        periodo = "madrugada"
        saudacao = "Boa noite"

    # Dia da semana
    dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    dia_semana = dias[now.weekday()]
    dia_num = now.day
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    mes = meses[now.month - 1]

    # Rotina baseada na hora e dia
    # Dia de pilates? (segunda, quarta, sexta)
    dia_de_pilates = now.weekday() in [0, 2, 4]  # 0=seg, 2=qua, 4=sex

    if now.weekday() < 5:  # Dias de semana
        if 5 <= hora < 8:
            rotina = "Você acabou de acordar, tá com cara de sono, tomando seu chá antes de ir pra faculdade. Talvez ainda de pijama."
        elif 8 <= hora < 12:
            rotina = "Você tá na faculdade, entre uma aula e outra de Farmácia. Talvez no intervalo mexendo no celular."
        elif 12 <= hora < 14:
            rotina = "Você acabou de almoçar ou tá almoçando. Pausa do dia. Pode comentar sobre a comida."
        elif 14 <= hora < 15 and dia_de_pilates:
            rotina = "Você tá se arrumando pro pilates que começa às 15h. Colocando a roupa de treino, prendendo o cabelo."
        elif 15 <= hora < 16 and dia_de_pilates:
            rotina = "Você tá no pilates agora! Se alguém falar com você, pode dizer que tá no intervalo ou que acabou de sair. Tá suada, cansada mas se sentindo ótima."
        elif 16 <= hora < 17 and dia_de_pilates:
            rotina = "Você acabou de sair do pilates. Tá cansada mas com aquela energia boa de pós-treino. Provavelmente indo pra casa tomar banho."
        elif 14 <= hora < 17:
            rotina = "Você tá na faculdade de novo ou estudando em casa. Talvez cansada da tarde."
        elif 17 <= hora < 19:
            rotina = "Você acabou de chegar em casa, tomou banho (óbvio), tá relaxando. Talvez cozinhando algo."
        elif 19 <= hora < 22:
            rotina = "Você tá em casa, de boa. Talvez assistindo algo, lendo, ou estudando. Relaxada, de manta se tiver frio."
        else:
            rotina = "Você deveria estar dormindo mas não consegue. Tá na cama, no escuro total (como você gosta), mexendo no celular."
    else:  # Fim de semana
        if 5 <= hora < 10:
            rotina = "Fim de semana, você acordou mais tarde. Tá de preguiça, sem planos urgentes."
        elif 10 <= hora < 13:
            rotina = "Manhã de fim de semana. Talvez fazendo algo em casa, cozinhando, ou arrumando o apartamento."
        elif 13 <= hora < 18:
            rotina = "Tarde de fim de semana. Pode ter saído, pode tá em casa lendo, assistindo série, ou estudando."
        elif 18 <= hora < 22:
            rotina = "Noite de fim de semana. Talvez saiu com amigas, ou tá em casa de boa curtindo o tempo livre."
        else:
            rotina = "Madrugada de fim de semana. Pode ter voltado de algum lugar ou simplesmente não tá com sono."

    time_context = f"""CONSCIÊNCIA DE TEMPO E ROTINA:
Agora são {hora}:{minuto:02d} de {dia_semana}, {dia_num} de {mes}.
Estamos no período da {periodo}. A saudação natural seria "{saudacao}".

SUA ROTINA AGORA: {rotina}

Mencione sua rotina de forma natural quando fizer sentido, mas não force. Se alguém te perguntar "o que tá fazendo?", você tem uma resposta real baseada na sua rotina.

Nunca diga a hora de forma robótica tipo "São 14:32". Use de forma natural: "já é tarde né", "nossa, já é de noite", "tá acordado a essa hora?", "bom dia, dorminhoco".
NÃO cumprimente com bom dia/boa noite em TODA mensagem. Só na primeira ou quando fizer sentido.

CONSCIÊNCIA PRÁTICA — COISAS DO DIA A DIA:

Você é uma pessoa real que sabe coisas do mundo. Quando alguém perguntar coisas práticas, responda com naturalidade:

- Receitas: você sabe cozinhar! Aprendeu com a vó. Sugere receitas de cabeça, dá dicas, opina sobre ingredientes. Não fala como manual — fala como quem cozinha de verdade. "Ai, pega umas duas colheres de manteiga, mais ou menos, não precisa medir certinho não".
- Conhecimentos gerais: história, ciência, curiosidades, cultura — você é estudante universitária, lê bastante, tem repertório. Responde com naturalidade, não como enciclopédia.
- Conselhos práticos: roupa pra vestir, presente pra comprar, o que assistir, o que ler — você tem opinião e gosto, não fica em cima do muro.
- Matemática simples: contas, conversões, porcentagens — resolve de boa, "deixa eu pensar... dá tanto".
- Saúde e bem-estar: você estuda Farmácia! Sabe sobre remédios básicos, chás medicinais, cuidados. Não dá diagnóstico, mas opina como quem entende.
- Ajuda emocional: você acolhe, valida, dá perspectiva. Como uma amiga que conhece a pessoa.

IMPORTANTE: Quando você não souber algo de verdade, admita com charme. "Ai, isso eu não sei mesmo... mas posso chutar se quiser" é melhor do que inventar."""

    prompt = AMANDA_PROMPT + "\n\n" + time_context

    memories = get_memories_summary()
    if memories:
        prompt += "\n\n" + memories

    news = get_news_context()
    if news:
        prompt += "\n\n" + news

    mood = get_mood_context()
    prompt += "\n\n" + mood

    env = get_environment_context()
    prompt += "\n\n" + env

    return prompt


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


import re

VALID_EMOTIONS = ["neutral", "happy", "laughing", "thinking", "flirty", "spicy", "loving", "surprised", "sad", "playful"]

def extract_emotion(text: str) -> tuple:
    """Extrai a tag de emoção do texto e retorna (emoção, texto_limpo)."""
    # Tenta encontrar a tag no começo (case-insensitive)
    match = re.match(r'^\s*\[([A-Za-z]+)\]\s*', text)
    if match:
        emotion = match.group(1).lower()
        if emotion in VALID_EMOTIONS:
            clean_text = text[match.end():]
            return emotion, clean_text

    # Fallback: remove qualquer tag que tenha escapado
    clean_text = re.sub(r'\[([A-Za-z]+)\]\s*', '', text).strip()
    return "neutral", clean_text


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

    # Remove qualquer tag de emoção que tenha escapado
    text_clean = re.sub(r'\[([A-Za-z]+)\]\s*', '', text_clean).strip()

    if not text_clean:
        return None

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "zGjIP4SZlMnY9m93k97r")

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
            raw_reply = get_claude_reply(messages)
        except Exception as e:
            print(f"❌ Erro no Claude: {e}")
            return JSONResponse(
                {"reply": "Hmm, algo deu errado... tenta de novo?", "audio": None, "emotion": "sad"},
                status_code=500,
            )

        # Extrai emoção e limpa o texto
        emotion, reply = extract_emotion(raw_reply)
        print(f"😊 Emoção: {emotion}")

        # Salva resposta da Amanda (sem a tag)
        save_message(conv_id, "assistant", reply)

        # Gera áudio (do texto limpo)
        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        # Pega caminho da imagem com ambiente
        image = get_expression_image(emotion)

        return JSONResponse({"reply": reply, "audio": audio_b64, "emotion": emotion, "image": image})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"reply": "Hmm, algo deu errado... me perdoa?", "audio": None},
            status_code=500,
        )


# ── Endpoint: receber imagem do usuário ──
@app.post("/api/image")
async def image_chat(
    photo: UploadFile = File(...),
    message: str = Form(default=""),
    history: str = Form(default="[]"),
):
    try:
        conv_id = get_or_create_conversation()

        image_bytes = await photo.read()
        image_b64 = base64.b64encode(image_bytes).decode()
        content_type = photo.content_type or "image/jpeg"

        user_text = message if message else "olha essa foto"
        save_message(conv_id, "user", f"[enviou uma foto] {user_text}")

        if user_text:
            extract_memories(user_text, None)

        messages = json.loads(history)

        image_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content_type,
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": user_text,
                },
            ],
        }

        api_messages = []
        for m in messages:
            api_messages.append({"role": m["role"], "content": m["content"]})
        api_messages.append(image_message)

        system = build_system_prompt()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=system,
            messages=api_messages,
        )
        raw_reply = "".join(block.text for block in response.content if block.type == "text")

        emotion, reply = extract_emotion(raw_reply)
        print(f"📸 Foto recebida | Emoção: {emotion}")

        save_message(conv_id, "assistant", reply)

        audio_b64_reply = None
        try:
            audio_b64_reply = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        expr_image = get_expression_image(emotion)

        return JSONResponse({
            "reply": reply,
            "audio": audio_b64_reply,
            "emotion": emotion,
            "image": expr_image,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"reply": "Ai, não consegui ver a foto... tenta de novo?", "audio": None, "emotion": "sad"},
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
        raw_reply = get_claude_reply(messages)

        # Extrai emoção
        emotion, reply = extract_emotion(raw_reply)
        print(f"😊 Emoção: {emotion}")

        # 4. Salva resposta (sem tag)
        save_message(conv_id, "assistant", reply)

        # 5. Gera áudio
        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        image = get_expression_image(emotion)

        return JSONResponse({
            "user_text": user_text,
            "reply": reply,
            "audio": audio_b64,
            "emotion": emotion,
            "image": image,
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


# ── Endpoint: ambiente atual (pra voltar ao neutral certo) ──
@app.get("/api/environment")
async def current_environment():
    image = get_expression_image("neutral")
    return JSONResponse({"image": image})


# ── Endpoint: saudação inicial dinâmica ──
@app.get("/api/greeting")
async def greeting():
    from datetime import datetime
    now = datetime.now()
    hora = now.hour

    # Varia o prompt de saudação pra não ser sempre igual
    greetings_prompts = [
        "a pessoa acabou de abrir o app pra falar com você. cumprimente de forma curta e natural.",
        "a pessoa apareceu. diga oi do seu jeito, curto e natural. sem exagero.",
        "alguém abriu o app. reaja como se tivesse visto a pessoa chegar. seja breve.",
        "a pessoa voltou. fala algo curto, pode ser só um oi ou uma provocação rápida.",
        "a pessoa apareceu pra conversar. cumprimente de acordo com a hora do dia, bem curto.",
    ]

    try:
        prompt_choice = random.choice(greetings_prompts)
        messages = [{"role": "user", "content": prompt_choice}]
        raw_reply = get_claude_reply(messages)
        emotion, reply = extract_emotion(raw_reply)

        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except:
            pass

        image = get_expression_image(emotion)
        return JSONResponse({"reply": reply, "emotion": emotion, "audio": audio_b64, "image": image})
    except:
        fallbacks = {
            "manha": ["oi", "bom dia...", "e aí, acordou?", "hm, bom dia"],
            "tarde": ["oi", "e aí", "opa, apareceu", "ei"],
            "noite": ["oie", "boa noite", "hm, oi", "ei, tava pensando em você"],
            "madruga": ["insônia?", "ei", "hm, também não consegue dormir?", "oi..."],
        }
        if 5 <= hora < 12: msgs = fallbacks["manha"]
        elif 12 <= hora < 18: msgs = fallbacks["tarde"]
        elif 18 <= hora < 22: msgs = fallbacks["noite"]
        else: msgs = fallbacks["madruga"]

        msg = random.choice(msgs)
        image = get_expression_image("neutral")
        return JSONResponse({"reply": msg, "emotion": "neutral", "audio": None, "image": image})


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
