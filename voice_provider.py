"""
voice_provider.py — Gerenciador de TTS da Amanda

Mesma lógica do provider.py: faz ping na ordem de prioridade,
conecta no primeiro que responder, rotaciona se cair.

Ordem: ElevenLabs → Edge TTS → gTTS

No .env:
    ELEVENLABS_API_KEY=key1,key2       (suporta múltiplas keys)
    ELEVENLABS_VOICE_ID=zGjIP4SZlMnY9m93k97r

Edge TTS e gTTS não precisam de API key.
"""

import os
import re
import time
import base64
import asyncio
import tempfile
import httpx
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════════════════
# Pool de Keys (reutiliza a mesma lógica)
# ══════════════════════════════════════════════════════════════

class KeyPool:
    """Gerencia múltiplas API keys com rotação."""

    def __init__(self, env_var: str):
        raw = os.getenv(env_var, "")
        self.keys = [k.strip() for k in raw.split(",") if k.strip()]
        self.current_index = 0
        self.total = len(self.keys)

    def has_keys(self) -> bool:
        return self.total > 0

    def current(self) -> str | None:
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate(self) -> str | None:
        if self.total <= 1:
            return None
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % self.total
        if self.current_index == old_index:
            return None
        print(f"   🔑 Rotacionando key TTS: {self.current_index + 1}/{self.total}")
        return self.keys[self.current_index]

    def reset(self):
        self.current_index = 0


# ══════════════════════════════════════════════════════════════
# Configuração
# ══════════════════════════════════════════════════════════════

VOICE_PROVIDERS = {
    "elevenlabs": {"name": "ElevenLabs", "emoji": "🎙️", "needs_key": True},
    "edge_tts":   {"name": "Edge TTS",   "emoji": "🔊", "needs_key": False},
    "gtts":       {"name": "Google TTS",  "emoji": "📢", "needs_key": False},
}

VOICE_PRIORITY = ["elevenlabs", "edge_tts", "gtts"]

# Pool de keys do ElevenLabs
_elevenlabs_pool = KeyPool("ELEVENLABS_API_KEY")
_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "zGjIP4SZlMnY9m93k97r")

# Edge TTS — voz brasileira feminina
_edge_voice = os.getenv("EDGE_TTS_VOICE", "pt-BR-FranciscaNeural")

# Estado global
_active_voice: str | None = None


# ══════════════════════════════════════════════════════════════
# Limpeza de texto (compartilhada)
# ══════════════════════════════════════════════════════════════

def _clean_text(text: str) -> str:
    """Remove emojis, tags de emoção e limpa o texto pro TTS."""
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
    text_clean = re.sub(r'\[([A-Za-z]+)\]\s*', '', text_clean).strip()
    return text_clean


# ══════════════════════════════════════════════════════════════
# Ping — testa se o TTS responde
# ══════════════════════════════════════════════════════════════

def _ping_elevenlabs() -> bool:
    """Testa ElevenLabs verificando se a key acessa as vozes."""
    key = _elevenlabs_pool.current()
    if not key:
        print(f"key vazia", end=" ")
        return False
    try:
        # Usa /v1/voices que funciona com qualquer permissão de key
        response = httpx.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": key},
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            num_voices = len(data.get("voices", []))
            print(f"({num_voices} vozes disponíveis)", end=" ")
            return True
        elif response.status_code == 401:
            print(f"key inválida", end=" ")
        elif response.status_code == 429:
            print(f"rate limited", end=" ")
        else:
            print(f"HTTP {response.status_code}", end=" ")
        return False
    except Exception as e:
        print(f"erro: {e}", end=" ")
        return False


def _ping_edge_tts() -> bool:
    """Testa Edge TTS — apenas verifica se o módulo importa e a voz existe."""
    try:
        import edge_tts
        # No ping, só verifica se o módulo tá instalado
        # O teste real acontece na primeira geração
        return True
    except ImportError:
        print(f"módulo não instalado", end=" ")
        return False
    except Exception as e:
        print(f"erro: {e}", end=" ")
        return False


def _ping_gtts() -> bool:
    """Testa gTTS — verifica se o módulo importa."""
    try:
        from gtts import gTTS
        # Só verifica se importa — gTTS depende de internet
        # mas não tem rate limit agressivo
        return True
    except ImportError:
        print(f"módulo não instalado", end=" ")
        return False
    except Exception as e:
        print(f"erro: {e}", end=" ")
        return False


PING_FUNCS = {
    "elevenlabs": _ping_elevenlabs,
    "edge_tts": _ping_edge_tts,
    "gtts": _ping_gtts,
}


# ══════════════════════════════════════════════════════════════
# Varredura
# ══════════════════════════════════════════════════════════════

def _scan_voice_providers() -> str | None:
    """Varre os providers de voz na ordem e retorna o primeiro que responder."""
    print("\n🔍 Varrendo providers de voz...")
    print("   Ordem: ElevenLabs → Edge TTS → gTTS\n")

    for provider_id in VOICE_PRIORITY:
        info = VOICE_PROVIDERS[provider_id]

        if provider_id == "elevenlabs" and not _elevenlabs_pool.has_keys():
            print(f"   {info['emoji']} {info['name']}: sem API key, pulando")
            continue

        if provider_id == "elevenlabs" and _elevenlabs_pool.total > 1:
            # Tenta cada key
            _elevenlabs_pool.reset()
            for i in range(_elevenlabs_pool.total):
                key_label = f"key {i + 1}/{_elevenlabs_pool.total}"
                print(f"   {info['emoji']} {info['name']} ({key_label}): pingando...", end=" ")
                start = time.time()
                if _ping_elevenlabs():
                    elapsed = time.time() - start
                    print(f"✅ ({elapsed:.1f}s)")
                    return provider_id
                else:
                    print("❌")
                    if i < _elevenlabs_pool.total - 1:
                        _elevenlabs_pool.rotate()
        else:
            print(f"   {info['emoji']} {info['name']}: pingando...", end=" ")
            start = time.time()
            if PING_FUNCS[provider_id]():
                elapsed = time.time() - start
                print(f"✅ ({elapsed:.1f}s)")
                return provider_id
            else:
                print("❌")

    print("\n   ⚠️ Nenhum provider de voz disponível!")
    return None


# ══════════════════════════════════════════════════════════════
# Geração de áudio
# ══════════════════════════════════════════════════════════════

async def _tts_elevenlabs(text: str) -> str | None:
    """Gera áudio com ElevenLabs."""
    key = _elevenlabs_pool.current()
    if not key:
        raise Exception("Sem API key")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{_voice_id}",
            headers={
                "xi-api-key": key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.75,
                    "style": 0.6,
                    "use_speaker_boost": True,
                },
            },
        )

        if response.status_code == 401:
            raise Exception("API key inválida")
        if response.status_code == 429:
            raise Exception("Rate limit / quota exceeded")
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        return base64.b64encode(response.content).decode()


async def _tts_edge(text: str) -> str | None:
    """Gera áudio com Edge TTS (grátis, Microsoft)."""
    import edge_tts
    import uuid

    # Windows não permite abrir tempfile enquanto outro processo usa
    # Então criamos um path manual na pasta temp
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"amanda_edge_{uuid.uuid4().hex[:8]}.mp3")

    try:
        communicate = edge_tts.Communicate(text, _edge_voice)
        await communicate.save(temp_path)

        with open(temp_path, "rb") as f:
            audio_bytes = f.read()

        if len(audio_bytes) == 0:
            raise Exception("Áudio vazio")

        return base64.b64encode(audio_bytes).decode()
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


async def _tts_gtts(text: str) -> str | None:
    """Gera áudio com gTTS (grátis, Google)."""
    from gtts import gTTS
    import uuid

    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"amanda_gtts_{uuid.uuid4().hex[:8]}.mp3")

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: gTTS(text, lang="pt", tld="com.br").save(temp_path))

        with open(temp_path, "rb") as f:
            audio_bytes = f.read()

        if len(audio_bytes) == 0:
            raise Exception("Áudio vazio")

        return base64.b64encode(audio_bytes).decode()
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


TTS_FUNCS = {
    "elevenlabs": _tts_elevenlabs,
    "edge_tts": _tts_edge,
    "gtts": _tts_gtts,
}


# ══════════════════════════════════════════════════════════════
# API Pública
# ══════════════════════════════════════════════════════════════

def get_voice_provider() -> str | None:
    """Retorna o provider de voz ativo. Se não tiver, faz varredura."""
    global _active_voice
    if _active_voice is None:
        _active_voice = _scan_voice_providers()
        if _active_voice:
            info = VOICE_PROVIDERS[_active_voice]
            extra = ""
            if _active_voice == "elevenlabs" and _elevenlabs_pool.total > 1:
                extra = f" ({_elevenlabs_pool.total} keys)"
            print(f"\n🎵 Voz da sessão: {info['emoji']} {info['name']}{extra}\n")
    return _active_voice


async def generate_tts(text: str) -> str | None:
    """
    Gera áudio com o provider de voz ativo.
    Se falhar, rotaciona key (ElevenLabs) ou troca de provider.
    """
    global _active_voice

    text_clean = _clean_text(text)
    if not text_clean:
        return None

    if _active_voice is None:
        get_voice_provider()

    if _active_voice is None:
        print("⚠️ Sem provider de voz disponível")
        return None

    info = VOICE_PROVIDERS[_active_voice]

    # Se for ElevenLabs, tenta rotacionar keys
    if _active_voice == "elevenlabs":
        start_index = _elevenlabs_pool.current_index
        for attempt in range(_elevenlabs_pool.total):
            try:
                result = await TTS_FUNCS["elevenlabs"](text_clean)
                if result:
                    return result
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = any(term in error_msg for term in [
                    "rate limit", "quota", "429", "exceeded"
                ])

                if is_rate_limit and _elevenlabs_pool.total > 1:
                    print(f"   ⚠️ {info['emoji']} Key {_elevenlabs_pool.current_index + 1} esgotada, rotacionando...")
                    next_key = _elevenlabs_pool.rotate()
                    if next_key and _elevenlabs_pool.current_index != start_index:
                        continue

                print(f"⚠️ {info['emoji']} {info['name']} falhou: {e}")
                break
    else:
        # Edge TTS ou gTTS — tenta direto
        try:
            result = await TTS_FUNCS[_active_voice](text_clean)
            if result:
                return result
        except Exception as e:
            print(f"⚠️ {info['emoji']} {info['name']} falhou: {e}")

    # Provider atual falhou — tenta o próximo na lista
    print(f"🔄 Procurando outro provider de voz...")
    old_provider = _active_voice
    _active_voice = None

    for provider_id in VOICE_PRIORITY:
        if provider_id == old_provider:
            continue

        info_next = VOICE_PROVIDERS[provider_id]

        if provider_id == "elevenlabs" and not _elevenlabs_pool.has_keys():
            continue

        print(f"   {info_next['emoji']} Tentando {info_next['name']}...", end=" ")
        try:
            result = await TTS_FUNCS[provider_id](text_clean)
            if result:
                _active_voice = provider_id
                print(f"✅")
                print(f"🎵 Nova voz: {info_next['emoji']} {info_next['name']}")
                return result
        except Exception as e:
            print(f"❌ ({e})")

    print("❌ Nenhum provider de voz funcionou")
    return None


def get_active_voice_name() -> str:
    """Retorna o nome do provider de voz ativo."""
    if _active_voice:
        info = VOICE_PROVIDERS[_active_voice]
        if _active_voice == "elevenlabs" and _elevenlabs_pool.total > 1:
            return f"{info['name']} (key {_elevenlabs_pool.current_index + 1}/{_elevenlabs_pool.total})"
        return info["name"]
    return "Nenhum"


def force_voice_rescan():
    """Força nova varredura de voz."""
    global _active_voice
    _active_voice = None
    _elevenlabs_pool.reset()
    return get_voice_provider()
