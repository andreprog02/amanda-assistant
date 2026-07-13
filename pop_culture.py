"""
pop_culture.py — Sintetiza opiniões de cultura pop pro contexto da Amanda

Extrai transcrições de vídeos do YouTube, analisa com LLM,
e gera um perfil de opiniões que é injetado no prompt.

Uso:
    python pop_culture.py update    → atualiza opiniões dos últimos vídeos
    python pop_culture.py show      → mostra o perfil atual

No app, importa:
    from pop_culture import get_pop_culture_context
"""

import os
import json
import time
from datetime import datetime

# Arquivo onde salva as opiniões sintetizadas
OPINIONS_FILE = "pop_culture_opinions.json"
CHANNEL_URL = "https://www.youtube.com/@LinhagemGeekTV"


def extract_recent_transcripts(max_videos: int = 10) -> list[dict]:
    """Extrai transcrições dos últimos vídeos do canal."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print("❌ Instale yt-dlp: pip install yt-dlp")
        return []

    print(f"📺 Buscando últimos {max_videos} vídeos do canal...")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_videos,
    }

    videos = []
    try:
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"{CHANNEL_URL}/videos", download=False)
            entries = result.get('entries', [])

            for entry in entries:
                video_id = entry.get('id', '')
                title = entry.get('title', '')
                if video_id and title:
                    videos.append({'id': video_id, 'title': title})

        print(f"   Encontrados {len(videos)} vídeos")
    except Exception as e:
        print(f"❌ Erro ao buscar vídeos: {e}")
        return []

    # Extrai legendas de cada vídeo
    transcripts = []
    for v in videos:
        print(f"   📝 Extraindo: {v['title'][:60]}...", end=" ")
        try:
            sub_opts = {
                'quiet': True,
                'no_warnings': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['pt', 'pt-BR'],
                'skip_download': True,
                'outtmpl': f"/tmp/yt_{v['id']}",
            }

            with YoutubeDL(sub_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={v['id']}", download=False)

                # Tenta pegar legendas automáticas
                subs = info.get('automatic_captions', {})
                if not subs:
                    subs = info.get('subtitles', {})

                text = ""
                for lang in ['pt', 'pt-BR', 'pt-br']:
                    if lang in subs:
                        for sub_info in subs[lang]:
                            if sub_info.get('ext') == 'json3':
                                import httpx
                                r = httpx.get(sub_info['url'], timeout=10)
                                data = r.json()
                                events = data.get('events', [])
                                segments = []
                                for event in events:
                                    segs = event.get('segs', [])
                                    for seg in segs:
                                        t = seg.get('utf8', '').strip()
                                        if t and t != '\n':
                                            segments.append(t)
                                text = ' '.join(segments)
                                break
                        break

                if text and len(text) > 200:
                    # Limita a 3000 chars por vídeo pra não estourar
                    if len(text) > 3000:
                        text = text[:3000] + "..."
                    transcripts.append({
                        'title': v['title'],
                        'id': v['id'],
                        'text': text,
                    })
                    print("✅")
                else:
                    print("⚠️ sem legenda")

        except Exception as e:
            print(f"❌ {str(e)[:50]}")

    print(f"\n📊 {len(transcripts)} transcrições extraídas")
    return transcripts


def synthesize_opinions(transcripts: list[dict]) -> dict:
    """Usa LLM pra sintetizar as opiniões dos vídeos."""
    if not transcripts:
        return {}

    # Monta o texto pra análise
    all_text = ""
    for t in transcripts:
        all_text += f"\n\nVÍDEO: {t['title']}\n{t['text']}"

    # Limita o total
    if len(all_text) > 15000:
        all_text = all_text[:15000]

    prompt = f"""Analise as transcrições abaixo de um canal de cultura pop brasileiro.
Extraia as OPINIÕES e VISÃO DE MUNDO do canal sobre os seguintes temas.
Responda APENAS em JSON, sem markdown.

Temas pra analisar:
- marvel (opinião sobre fase atual da Marvel)
- dc (opinião sobre DC/James Gunn)
- star_wars (opinião sobre Star Wars atual)
- disney (opinião sobre Disney)
- hollywood (opinião sobre Hollywood em geral)
- series (séries que gostam/não gostam)
- animes (opinião sobre animes)
- games (opinião sobre jogos)
- cinema_classico (filmes/diretores que admiram)
- tendencias (o que acham das tendências atuais do entretenimento)
- visao_geral (visão de mundo sobre cultura pop em 2-3 frases)

Formato do JSON:
{{
  "marvel": "opinião curta em 1-2 frases como uma pessoa falaria",
  "dc": "...",
  ...
}}

TRANSCRIÇÕES:
{all_text}"""

    # Tenta usar o provider disponível
    try:
        import httpx

        # Tenta Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={gemini_key}",
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2000},
                },
                timeout=60.0,
            )
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)

        # Tenta Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            r = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                },
                timeout=60.0,
            )
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)

    except Exception as e:
        print(f"❌ Erro ao sintetizar: {e}")

    return {}


def update_opinions():
    """Atualiza as opiniões extraindo dos últimos vídeos."""
    from dotenv import load_dotenv
    load_dotenv()

    transcripts = extract_recent_transcripts(max_videos=10)
    if not transcripts:
        print("❌ Nenhuma transcrição obtida")
        return

    print("\n🧠 Sintetizando opiniões com LLM...")
    opinions = synthesize_opinions(transcripts)

    if opinions:
        opinions["_meta"] = {
            "updated": datetime.now().isoformat(),
            "videos_analyzed": len(transcripts),
            "source": CHANNEL_URL,
        }

        with open(OPINIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(opinions, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Opiniões salvas em {OPINIONS_FILE}")
        print("\nResumo:")
        for k, v in opinions.items():
            if k != "_meta":
                print(f"   {k}: {v}")
    else:
        print("❌ Falha ao sintetizar opiniões")


def load_opinions() -> dict:
    """Carrega opiniões do arquivo."""
    if os.path.exists(OPINIONS_FILE):
        with open(OPINIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_pop_culture_context() -> str:
    """Retorna contexto de cultura pop formatado pro prompt."""
    opinions = load_opinions()
    if not opinions:
        return ""

    lines = []
    for k, v in opinions.items():
        if k == "_meta":
            continue
        label = k.replace("_", " ").title()
        lines.append(f"- {label}: {v}")

    opinions_text = "\n".join(lines)

    return f"""SUAS OPINIÕES SOBRE CULTURA POP (o que você realmente pensa):

{opinions_text}

COMO USAR ESSAS OPINIÕES:
- Essas são as SUAS opiniões genuínas. Você acredita nelas de verdade.
- Quando alguém tocar nesses assuntos, você opina com convicção e personalidade.
- Você não força opinião — só fala quando o assunto aparece na conversa.
- Você argumenta com exemplos concretos (filmes, cenas, personagens).
- Você tem humor e sarcasmo ao falar desses temas.
- NÃO recite as opiniões como lista. Fale naturalmente, como numa conversa."""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        update_opinions()
    elif len(sys.argv) > 1 and sys.argv[1] == "show":
        opinions = load_opinions()
        if opinions:
            for k, v in opinions.items():
                if k != "_meta":
                    print(f"{k}: {v}")
        else:
            print("Nenhuma opinião salva. Rode: python pop_culture.py update")
    else:
        print("Uso:")
        print("  python pop_culture.py update   → atualiza opiniões dos últimos vídeos")
        print("  python pop_culture.py show     → mostra perfil atual")
