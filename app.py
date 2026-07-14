import os
import json
import random
import tempfile
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from library import get_library, get_library_context
from prompt import AMANDA_PROMPT
from database import (
    init_db, create_conversation, get_latest_conversation,
    save_message, get_conversation_messages, get_all_memories,
    get_memories_summary, save_memory, get_stats,
)
from news import get_news_context
from mood import get_mood_context
from weather import get_weather_context
from pop_culture import get_pop_culture_context
from science_tech import get_science_tech_context
from roleplay import get_roleplay_image, get_roleplay_context
from personality import get_engine, quick_analyze, analyze_user_message
from provider import get_provider, get_reply, get_active_provider_name, get_active_provider_id, force_rescan
from plans import check_limit, increment_daily_count, get_limit_message, can_use_voice, get_plan_info, list_plans
from voice_provider import get_voice_provider, generate_tts, get_active_voice_name, force_voice_rescan




load_dotenv()

app = FastAPI()

# Inicializa banco direto (fora do evento de startup)
db_available = False
try:
    init_db()
    db_available = True
except Exception:
    pass

# Conecta ao melhor provider disponível
print("\n🚀 Iniciando Amanda...")
get_provider()
get_voice_provider()

# Conversa atual
current_conversation_id = None

def get_or_create_conversation() -> int:
    global current_conversation_id
    if not db_available:
        return 0
    if current_conversation_id is None:
        current_conversation_id = create_conversation()
        print(f"📝 Nova conversa #{current_conversation_id}")
    return current_conversation_id


def safe_save_message(conv_id, role, content, provider=None):
    """Salva mensagem se o banco estiver disponível."""
    if db_available and conv_id:
        try:
            return save_message(conv_id, role, content, provider=provider)
        except:
            pass
    return None

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

    # Stats de personalidade (sistema RPG)
    try:
        engine = get_engine()
        personality_context = engine.get_prompt_context()
        prompt += "\n\n" + personality_context
    except Exception as e:
        print(f"⚠️ Erro ao carregar personality stats: {e}")

    if db_available:
        memories = get_memories_summary()
        if memories:
            prompt += "\n\n" + memories

    news = get_news_context()
    if news:
        prompt += "\n\n" + news

    weather = get_weather_context()
    if weather:
        prompt += "\n\n" + weather

    pop = get_pop_culture_context()
    if pop:
        prompt += "\n\n" + pop

    scitech = get_science_tech_context()
    if scitech:
        prompt += "\n\n" + scitech

    mood = get_mood_context()
    prompt += "\n\n" + mood

    env = get_roleplay_context()
    prompt += "\n\n" + env

    return prompt


def get_llm_reply(messages: list) -> str:
    """Envia mensagem pro provider ativo da sessão."""
    system = build_system_prompt()
    return get_reply(messages, system)


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
    """Usa o provider ativo pra extrair fatos importantes da mensagem do usuário."""
    if not db_available:
        return
    try:
        memory_system = """Você é um extrator de informações. Analise a mensagem do usuário e extraia APENAS fatos concretos e pessoais sobre ele.

Responda APENAS em JSON, sem markdown, sem explicação. Formato:
[{"category": "categoria", "content": "fato", "importance": 1-10}]

Categorias possíveis: nome, idade, trabalho, estudo, hobbies, gostos, familia, relacionamento, humor_do_dia, sonhos, rotina, saude, localizacao, pets, comida_favorita, musica, filmes, outros

Exemplos:
- "Meu nome é João" → [{"category": "nome", "content": "Se chama João", "importance": 10}]
- "Tô estudando pra prova de matemática" → [{"category": "estudo", "content": "Está estudando matemática, tem prova", "importance": 6}]
- "Oi tudo bem?" → []

Se não houver fatos pessoais, retorne: []
NÃO invente informações. Extraia APENAS o que está explícito."""

        raw = get_reply(
            [{"role": "user", "content": user_text}],
            memory_system,
        )

        text = raw.strip()
        # Remove tags de emoção que o provider pode ter adicionado
        text = re.sub(r'^\s*\[([A-Za-z]+)\]\s*', '', text)
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




# ── Endpoint: chat por texto ──
@app.post("/api/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        messages = body.get("messages", [])
        user_id = body.get("user_id", "local")
        conv_id = get_or_create_conversation()

        # ── Verifica limite do plano ──
        limit = check_limit(user_id)
        if not limit["allowed"]:
            limit_reply = get_limit_message(user_id)
            emotion, reply = extract_emotion(limit_reply)
            image = get_roleplay_image(emotion)
            return JSONResponse({
                "reply": reply,
                "emotion": emotion,
                "audio": None,
                "image": image,
                "limit_reached": True,
                "plan_info": get_plan_info(user_id),
            })

        user_content = messages[-1]["content"] if messages else ""
        user_msg_id = safe_save_message(conv_id, "user", user_content)
        increment_daily_count(user_id)

        # ── Processar stats de personalidade ──
        try:
            engine = get_engine()
            analysis = quick_analyze(user_content)
            engine.process_interaction(analysis)
        except Exception as e:
            print(f"⚠️ Erro nos stats: {e}")

        # Extrai memórias em background
        if user_content:
            extract_memories(user_content, user_msg_id)

        # Pega resposta
        raw_reply = get_llm_reply(messages)

        emotion, reply = extract_emotion(raw_reply)
        safe_save_message(conv_id, "assistant", reply, provider=get_active_provider_id())

        # TTS — só se o plano permite
        audio_b64 = None
        if can_use_voice(user_id):
            try:
                audio_b64 = await generate_tts(reply)
            except Exception as e:
                print(f"⚠️ Erro no TTS: {e}")

        image = get_roleplay_image(emotion)

        # Monta response com stats se disponível
        response_data = {
            "reply": reply,
            "audio": audio_b64,
            "emotion": emotion,
            "image": image,
        }
        try:
            engine = get_engine()
            response_data["stats"] = engine.get_stats_summary()
        except:
            pass

        return JSONResponse(response_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"reply": "Hmm, algo deu errado... me perdoa?", "audio": None},
            status_code=500,


        )




@app.get("/api/stats")
async def personality_stats():
    engine = get_engine()
    engine.apply_decay()
    engine.sync_energy_to_time()
    return JSONResponse({
        "stats": engine.get_stats_summary(),
        "prompt_context": engine.get_prompt_context(),
    })

@app.post("/api/stats/reset")
async def reset_stats():
    """Reseta stats pro padrão (útil pra debug)."""
    engine = get_engine()
    from personality import DEFAULT_STATS
    engine.stats = {k: dict(v) for k, v in DEFAULT_STATS.items()}
    engine.save()
    return JSONResponse({"message": "Stats resetados", "stats": engine.get_stats_summary()})

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
        safe_save_message(conv_id, "user", f"[enviou uma foto] {user_text}")

        if user_text:
            extract_memories(user_text, None)

        messages = json.loads(history)

        # Tenta responder sobre a foto via provider ativo
        system = build_system_prompt()
        text_messages = list(messages)
        text_messages.append({"role": "user", "content": f"(a pessoa enviou uma foto) {user_text}"})
        raw_reply = get_reply(text_messages, system)
        if not raw_reply:
            raw_reply = "[NEUTRAL] Ai, não consegui ver a foto agora... me descreve o que tem nela?"

        emotion, reply = extract_emotion(raw_reply)
        print(f"📸 Foto recebida | Emoção: {emotion}")

        safe_save_message(conv_id, "assistant", reply, provider=get_active_provider_id())

        audio_b64_reply = None
        try:
            audio_b64_reply = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        expr_image = get_roleplay_image(emotion)

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
        user_msg_id = safe_save_message(conv_id, "user", user_text)
        extract_memories(user_text, user_msg_id)

        # 3. Monta histórico + resposta
        messages = json.loads(history)
        messages.append({"role": "user", "content": user_text})
        raw_reply = get_llm_reply(messages)

        # Extrai emoção
        emotion, reply = extract_emotion(raw_reply)
        print(f"😊 Emoção: {emotion}")

        # 4. Salva resposta (sem tag)
        safe_save_message(conv_id, "assistant", reply, provider=get_active_provider_id())

        # 5. Gera áudio
        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except Exception as e:
            print(f"⚠️ Erro no TTS: {e}")

        image = get_roleplay_image(emotion)

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


# ── Endpoint: expressão do roleplay atual ──
@app.get("/api/environment")
async def current_environment(emotion: str = "neutral"):
    image = get_roleplay_image(emotion)
    return JSONResponse({"image": image})


# ── Endpoint: lista expressões disponíveis (pra preload de vídeos) ──
@app.get("/api/expressions")
async def list_expressions():
    """Retorna todas as expressões disponíveis no roleplay ativo com seus paths."""
    from roleplay import get_current_roleplay, ROLEPLAYS, ROLEPLAY_DIR

    rp_name = get_current_roleplay()
    rp_config = ROLEPLAYS.get(rp_name, ROLEPLAYS["main"])
    folder = rp_config["folder"]
    folder_path = os.path.join(ROLEPLAY_DIR, folder)

    expressions = {}
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            name = os.path.splitext(f)[0]
            ext = os.path.splitext(f)[1].lower()
            emotion = name.replace(f"{folder}_", "")
            if ext in ('.mp4', '.webm', '.png'):
                if emotion not in expressions:
                    expressions[emotion] = {}
                if ext in ('.mp4', '.webm'):
                    expressions[emotion]['video'] = f"/static/roleplay/{folder}/{f}"
                elif ext == '.png':
                    expressions[emotion]['image'] = f"/static/roleplay/{folder}/{f}"

    # Fallback: se roleplay ativo não tem nada, usa main
    if not expressions and rp_name != "main":
        main_folder = ROLEPLAYS["main"]["folder"]
        main_path = os.path.join(ROLEPLAY_DIR, main_folder)
        if os.path.exists(main_path):
            for f in os.listdir(main_path):
                name = os.path.splitext(f)[0]
                ext = os.path.splitext(f)[1].lower()
                emotion = name.replace(f"{main_folder}_", "")
                if ext in ('.mp4', '.webm', '.png'):
                    if emotion not in expressions:
                        expressions[emotion] = {}
                    if ext in ('.mp4', '.webm'):
                        expressions[emotion]['video'] = f"/static/roleplay/{main_folder}/{f}"
                    elif ext == '.png':
                        expressions[emotion]['image'] = f"/static/roleplay/{main_folder}/{f}"
        folder = main_folder

    return JSONResponse({
        "roleplay": rp_name,
        "folder": folder,
        "expressions": expressions,
    })


# ── Endpoint: status do provider ativo ──
@app.get("/api/provider")
async def provider_status():
    return JSONResponse({
        "llm": get_active_provider_name(),
        "voice": get_active_voice_name(),
    })


# ── Endpoint: forçar nova varredura de providers ──
@app.post("/api/provider/rescan")
async def provider_rescan():
    llm_result = force_rescan()
    voice_result = force_voice_rescan()
    return JSONResponse({
        "llm": get_active_provider_name(),
        "voice": get_active_voice_name(),
        "connected": llm_result is not None,
    })


# ── Endpoint: info do plano do usuário ──
@app.get("/api/plan")
async def plan_info(user_id: str = "local"):
    return JSONResponse(get_plan_info(user_id))


# ── Endpoint: listar planos disponíveis ──
@app.get("/api/plans")
async def plans_list():
    return JSONResponse({"plans": list_plans()})


# ── Endpoint: estatísticas do banco ──
@app.get("/api/stats")
async def db_stats():
    try:
        stats = get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
        raw_reply = get_llm_reply(messages)
        emotion, reply = extract_emotion(raw_reply)

        audio_b64 = None
        try:
            audio_b64 = await generate_tts(reply)
        except:
            pass

        image = get_roleplay_image(emotion)
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
        image = get_roleplay_image("neutral")
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
    import ctypes
    from ctypes import wintypes

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    def start_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("\n✨ Amanda tá online!\n")

    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    work_h = rect.bottom - rect.top

    webview.create_window(
        "Amanda",
        "http://127.0.0.1:8000",
        width=420,
        height=work_h,
        resizable=False,
        min_size=(360, 500),
        x=0,
        y=0,
    )
    webview.start()