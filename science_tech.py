"""
science_tech.py — Sintetiza conteúdo de ciência e tecnologia pro contexto da Amanda

Extrai transcrições de vídeos do YouTube (Olhar Digital, Space Today, Schwarza),
analisa com LLM e gera um perfil de conhecimento.

Uso:
    python science_tech.py update    → atualiza conhecimento dos últimos vídeos
    python science_tech.py show      → mostra o perfil atual

No app, importa:
    from science_tech import get_science_tech_context
"""

import os
import json
import time
from datetime import datetime

OPINIONS_FILE = "science_tech_opinions.json"

# Canais com peso de relevância
CHANNELS = [
    {
        "name": "Olhar Digital",
        "url": "https://www.youtube.com/@OlharDigital",
        "channel_id": "UCGV72aVJuWP0QPNGH4YgIww",
        "weight": "alta",
        "focus": "tecnologia, IA, gadgets, big techs",
    },
    {
        "name": "Space Today",
        "url": "https://www.youtube.com/@SpaceToday",
        "channel_id": "UC_Fk7hHbl7vv_7K8tYqJd5A",
        "weight": "alta",
        "focus": "astronomia, missões espaciais, NASA, SpaceX",
    },
    {
        "name": "Canal do Schwarza",
        "url": "https://www.youtube.com/@CanaldoSchwarza",
        "channel_id": "UCWq1xltHB2fDe6YkYoOrryg",
        "weight": "média",
        "focus": "ciência geral, curiosidades, universo",
    },
]


def extract_recent_transcripts(max_videos_per_channel: int = 5) -> list[dict]:
    """Extrai transcrições dos últimos vídeos dos canais."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print("❌ Instale yt-dlp: pip install yt-dlp")
        return []

    all_transcripts = []

    for channel in CHANNELS:
        print(f"\n📺 {channel['name']} (relevância: {channel['weight']})...")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': max_videos_per_channel,
        }

        videos = []
        try:
            with YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(f"{channel['url']}/videos", download=False)
                entries = result.get('entries', [])
                for entry in entries:
                    video_id = entry.get('id', '')
                    title = entry.get('title', '')
                    if video_id and title:
                        videos.append({'id': video_id, 'title': title})

            print(f"   {len(videos)} vídeos encontrados")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            continue

        for v in videos:
            print(f"   📝 {v['title'][:55]}...", end=" ")
            try:
                sub_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['pt', 'pt-BR'],
                    'skip_download': True,
                }

                with YoutubeDL(sub_opts) as ydl:
                    info = ydl.extract_info(
                        f"https://www.youtube.com/watch?v={v['id']}",
                        download=False
                    )

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
                        if len(text) > 2500:
                            text = text[:2500] + "..."
                        all_transcripts.append({
                            'title': v['title'],
                            'id': v['id'],
                            'channel': channel['name'],
                            'weight': channel['weight'],
                            'text': text,
                        })
                        print("✅")
                    else:
                        print("⚠️ sem legenda")

            except Exception as e:
                print(f"❌ {str(e)[:40]}")

    print(f"\n📊 Total: {len(all_transcripts)} transcrições extraídas")
    return all_transcripts


def synthesize_knowledge(transcripts: list[dict]) -> dict:
    """Usa LLM pra sintetizar o conhecimento dos vídeos."""
    if not transcripts:
        return {}

    all_text = ""
    for t in transcripts:
        all_text += f"\n\n[{t['channel']} - relevância {t['weight']}] {t['title']}\n{t['text']}"

    if len(all_text) > 15000:
        all_text = all_text[:15000]

    prompt = f"""Analise as transcrições abaixo de canais brasileiros de ciência e tecnologia.
Extraia o CONHECIMENTO e OPINIÕES sobre os seguintes temas.
Responda APENAS em JSON, sem markdown.

Temas:
- inteligencia_artificial (novidades, opinião sobre IA, impactos)
- espaco (missões recentes, descobertas, SpaceX, NASA)
- celulares_gadgets (lançamentos, o que vale a pena)
- big_techs (Apple, Google, Meta, Microsoft — o que estão fazendo)
- ciencia_geral (descobertas científicas recentes interessantes)
- futuro (previsões e tendências tecnológicas)
- curiosidades (fatos interessantes que podem render conversa)
- visao_geral (visão resumida sobre o momento atual da tecnologia em 2-3 frases)

Formato — cada campo deve ser 1-2 frases CURTAS como uma pessoa jovem comentaria:
{{
  "inteligencia_artificial": "opinião curta",
  "espaco": "...",
  ...
}}

TRANSCRIÇÕES:
{all_text}"""

    try:
        import httpx
        from dotenv import load_dotenv
        load_dotenv()

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

        # Tenta Claude
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            model = os.getenv("MODEL", "claude-sonnet-4-6")
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in response.content if b.type == "text")
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


def update_knowledge():
    """Atualiza o conhecimento extraindo dos últimos vídeos."""
    from dotenv import load_dotenv
    load_dotenv()

    transcripts = extract_recent_transcripts(max_videos_per_channel=5)
    if not transcripts:
        print("❌ Nenhuma transcrição obtida")
        return

    print("\n🧠 Sintetizando conhecimento com LLM...")
    knowledge = synthesize_knowledge(transcripts)

    if knowledge:
        knowledge["_meta"] = {
            "updated": datetime.now().isoformat(),
            "videos_analyzed": len(transcripts),
            "channels": [c["name"] for c in CHANNELS],
        }

        with open(OPINIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Conhecimento salvo em {OPINIONS_FILE}")
        print("\nResumo:")
        for k, v in knowledge.items():
            if k != "_meta":
                print(f"   {k}: {v}")
    else:
        print("❌ Falha ao sintetizar")


def load_knowledge() -> dict:
    """Carrega conhecimento do arquivo."""
    if os.path.exists(OPINIONS_FILE):
        with open(OPINIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_science_tech_context() -> str:
    """Retorna contexto de ciência e tecnologia pro prompt."""
    knowledge = load_knowledge()
    if not knowledge:
        return ""

    lines = []
    for k, v in knowledge.items():
        if k == "_meta":
            continue
        label = k.replace("_", " ").title()
        lines.append(f"- {label}: {v}")

    text = "\n".join(lines)

    return f"""SEU CONHECIMENTO SOBRE CIÊNCIA E TECNOLOGIA (o que você acompanha):

{text}

COMO USAR:
- Você acompanha canais de tecnologia e ciência. Sabe das novidades.
- Quando alguém tocar nesses assuntos, você comenta com interesse genuíno.
- Você não é nerd hardcore — é uma mina curiosa que acha espaço fascinante e gosta de tecnologia.
- Fala de ciência com empolgação mas de forma simples, nunca acadêmica.
- Pode puxar assunto: "tu viu que a SpaceX lançou..." ou "saiu um celular novo que..."
- NÃO force esses temas. Só quando fizer sentido na conversa."""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        update_knowledge()
    elif len(sys.argv) > 1 and sys.argv[1] == "show":
        knowledge = load_knowledge()
        if knowledge:
            for k, v in knowledge.items():
                if k != "_meta":
                    print(f"{k}: {v}")
        else:
            print("Nenhum conhecimento salvo. Rode: python science_tech.py update")
    else:
        print("Uso:")
        print("  python science_tech.py update   → atualiza conhecimento dos últimos vídeos")
        print("  python science_tech.py show     → mostra perfil atual")
