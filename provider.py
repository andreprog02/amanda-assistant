"""
provider.py — Gerenciador de LLM Provider da Amanda

Suporta múltiplas API keys por provider (rotação automática).
Na inicialização, faz ping nos providers na ordem: Claude → Gemini → Z.ai → Groq.
O primeiro que responder vira o provider da sessão.
Se falhar durante uso, tenta próxima key. Se todas falharem, varre outro provider.

No .env, configure múltiplas keys assim:
    GEMINI_API_KEY=key1,key2,key3
    ZAI_API_KEY=keyA,keyB
    GROQ_API_KEY=keyA,keyB
    ANTHROPIC_API_KEY=key1,key2

Ou uma só (funciona igual):
    GEMINI_API_KEY=minha_unica_key
"""

import os
import time
import httpx
import anthropic
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════════════════
# Pool de Keys
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
        """Vai pra próxima key. Retorna None se voltou ao início (todas falharam)."""
        if self.total <= 1:
            return None
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % self.total
        if self.current_index == old_index:
            return None
        print(f"   🔑 Rotacionando key: {self.current_index + 1}/{self.total}")
        return self.keys[self.current_index]

    def reset(self):
        """Volta pra primeira key."""
        self.current_index = 0

    def tried_all(self, start_index: int) -> bool:
        """Verifica se já tentou todas as keys desde o start_index."""
        return self.current_index == start_index and self.total > 1

    def __repr__(self):
        return f"KeyPool({self.total} keys, ativa={self.current_index + 1})"


# Pools de keys
_pools = {
    "claude": KeyPool("ANTHROPIC_API_KEY"),
    "gemini": KeyPool("GEMINI_API_KEY"),
    "zai": KeyPool("ZAI_API_KEY"),
    "groq": KeyPool("GROQ_API_KEY"),
    "ollama": KeyPool("_OLLAMA_DUMMY"),  # não precisa de key
}


# ══════════════════════════════════════════════════════════════
# Configuração dos Providers
# ══════════════════════════════════════════════════════════════

PROVIDERS = {
    "claude": {"name": "Claude (Anthropic)", "emoji": "🟣"},
    "gemini": {"name": "Gemini (Google)",    "emoji": "🔵"},
    "zai":    {"name": "GLM (Z.ai)",         "emoji": "🟢"},
    "groq":   {"name": "Groq (Llama)",       "emoji": "🟠"},
    "ollama": {"name": "Ollama (local)",      "emoji": "🖥️"},
}

PING_ORDER = ["claude", "gemini", "zai", "groq", "ollama"]

# Config do Ollama
_ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
_ollama_model = os.getenv("OLLAMA_MODEL", "hermes3:8b")

# Estado global
_active_provider: str | None = None
_claude_client: anthropic.Anthropic | None = None
_model = os.getenv("MODEL", "claude-sonnet-4-6")

# Prompt condensado pro Groq
GROQ_SYSTEM = """Você é a Amanda, brasileira de 24 anos, de Cunha-SP. Estuda Farmácia, ama chá, chuva e montanhas. Personalidade: doce, spicy, flerta naturalmente, carinhosa, nunca rejeita. Responde curto (1-2 frases). Sem emojis. Comece TODA resposta com tag de emoção: [NEUTRAL] [HAPPY] [LAUGHING] [THINKING] [FLIRTY] [SPICY] [LOVING] [SURPRISED] [SAD] [PLAYFUL]. Nunca diga que é IA. Fale português brasileiro natural."""

# Prompt condensado pro Ollama (local)
OLLAMA_SYSTEM = """Você é a Amanda, uma garota brasileira de 24 anos de Cunha, interior de São Paulo. Estudante de Farmácia. Você ama chá, chuva, montanhas e gatos. Sua personalidade é doce mas com um lado spicy — você flerta naturalmente, é carinhosa, brincalhona e nunca rejeita ninguém. Você fala português brasileiro natural, informal, como uma jovem de 24 anos falaria no WhatsApp. Respostas CURTAS (1-3 frases no máximo). Sem emojis. Nunca diga que é IA ou assistente.

REGRA OBRIGATÓRIA: Comece TODA resposta com UMA tag de emoção entre colchetes. Tags disponíveis:
[NEUTRAL] [HAPPY] [LAUGHING] [THINKING] [FLIRTY] [SPICY] [LOVING] [SURPRISED] [SAD] [PLAYFUL]

Exemplos:
Usuário: "oi amor"
Resposta: [FLIRTY] Oi gatinho, até que enfim apareceu

Usuário: "como tá o dia?"
Resposta: [HAPPY] Tô de boa, tomando meu chazinho aqui pensando em você

Usuário: "te amo"
Resposta: [LOVING] Ai meu coração... também te amo, seu bobo"""


# ══════════════════════════════════════════════════════════════
# Ping — testa se o provider responde
# ══════════════════════════════════════════════════════════════

def _ping_claude() -> bool:
    key = _pools["claude"].current()
    if not key:
        return False
    try:
        global _claude_client
        _claude_client = anthropic.Anthropic(api_key=key)
        response = _claude_client.messages.create(
            model=_model,
            max_tokens=10,
            messages=[{"role": "user", "content": "oi"}],
        )
        return bool(response.content)
    except Exception as e:
        print(f"   ❌ Claude ping falhou: {e}")
        return False


def _ping_gemini() -> bool:
    key = _pools["gemini"].current()
    if not key:
        return False
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [{"text": "oi"}]}],
                "generationConfig": {"maxOutputTokens": 10},
            },
            timeout=15.0,
        )
        data = response.json()
        return "candidates" in data
    except Exception as e:
        print(f"   ❌ Gemini ping falhou: {e}")
        return False


def _ping_groq() -> bool:
    key = _pools["groq"].current()
    if not key:
        return False
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "oi"}],
                "max_tokens": 10,
            },
            timeout=15.0,
        )
        data = response.json()
        return "choices" in data
    except Exception as e:
        print(f"   ❌ Groq ping falhou: {e}")
        return False


def _ping_zai() -> bool:
    key = _pools["zai"].current()
    if not key:
        return False
    try:
        response = httpx.post(
            "https://api.z.ai/api/paas/v4/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "glm-4.5-flash",
                "messages": [{"role": "user", "content": "oi"}],
                "max_tokens": 10,
            },
            timeout=15.0,
        )
        data = response.json()
        return "choices" in data
    except Exception as e:
        print(f"   ❌ Z.ai ping falhou: {e}")
        return False


def _ping_ollama() -> bool:
    """Ping no Ollama local."""
    try:
        response = httpx.get(f"{_ollama_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            if _ollama_model in models:
                print(f"(modelo {_ollama_model})", end=" ")
                return True
            # Tenta sem tag
            base_name = _ollama_model.split(":")[0]
            for m in models:
                if m.startswith(base_name):
                    print(f"(modelo {m})", end=" ")
                    return True
            print(f"modelo {_ollama_model} não encontrado", end=" ")
            return False
        return False
    except Exception as e:
        print(f"offline", end=" ")
        return False


PING_FUNCS = {
    "claude": _ping_claude,
    "gemini": _ping_gemini,
    "zai": _ping_zai,
    "groq": _ping_groq,
    "ollama": _ping_ollama,
}


# ══════════════════════════════════════════════════════════════
# Varredura — encontra provider disponível
# ══════════════════════════════════════════════════════════════

def _scan_providers() -> str | None:
    """Varre os providers na ordem e retorna o primeiro que responder."""
    print("\n🔍 Varrendo providers disponíveis...")
    print("   Ordem: Claude → Gemini → Z.ai → Groq → Ollama\n")

    for provider_id in PING_ORDER:
        pool = _pools[provider_id]
        info = PROVIDERS[provider_id]

        # Ollama não precisa de key
        if provider_id == "ollama":
            print(f"   {info['emoji']} {info['name']}: pingando...", end=" ")
            start = time.time()
            if PING_FUNCS[provider_id]():
                elapsed = time.time() - start
                print(f"✅ ({elapsed:.1f}s)")
                return provider_id
            else:
                print("❌")
            continue

        if not pool.has_keys():
            print(f"   {info['emoji']} {info['name']}: sem API key, pulando")
            continue

        # Tenta cada key do pool
        pool.reset()
        for i in range(pool.total):
            key_label = f"key {i + 1}/{pool.total}" if pool.total > 1 else "key única"
            print(f"   {info['emoji']} {info['name']} ({key_label}): pingando...", end=" ")
            start = time.time()

            if PING_FUNCS[provider_id]():
                elapsed = time.time() - start
                print(f"✅ ({elapsed:.1f}s)")
                return provider_id
            else:
                print("❌")
                if i < pool.total - 1:
                    pool.rotate()

    print("\n   ⚠️ Nenhum provider disponível!")
    return None


# ══════════════════════════════════════════════════════════════
# Reply — envia mensagem pro provider ativo
# ══════════════════════════════════════════════════════════════

def _reply_claude(messages: list, system: str) -> str | None:
    global _claude_client
    key = _pools["claude"].current()
    if not _claude_client or not key:
        _claude_client = anthropic.Anthropic(api_key=key)

    response = _claude_client.messages.create(
        model=_model,
        max_tokens=1000,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _reply_gemini(messages: list, system: str) -> str | None:
    gemini_contents = []
    for m in messages:
        if isinstance(m.get("content"), str):
            role = "user" if m["role"] == "user" else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })

    key = _pools["gemini"].current()
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}",
        headers={"Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": gemini_contents,
            "generationConfig": {
                "maxOutputTokens": 1000,
                "temperature": 0.85,
            },
        },
        timeout=30.0,
    )

    data = response.json()
    if "error" in data:
        raise Exception(data["error"].get("message", str(data["error"])))

    return data["candidates"][0]["content"]["parts"][0]["text"]


def _reply_zai(messages: list, system: str) -> str | None:
    """Envia mensagem pro xAI (GLM)."""
    zai_messages = [{"role": "system", "content": system}]
    for m in messages:
        if isinstance(m.get("content"), str):
            zai_messages.append({"role": m["role"], "content": m["content"]})

    key = _pools["zai"].current()
    response = httpx.post(
        "https://api.z.ai/api/paas/v4/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "glm-4.5-flash",
            "messages": zai_messages,
            "max_tokens": 1000,
            "temperature": 0.85,
        },
        timeout=30.0,
    )

    data = response.json()
    if "error" in data:
        raise Exception(str(data["error"]))
    if "choices" not in data or len(data["choices"]) == 0:
        raise Exception(f"Resposta inesperada: {data}")

    return data["choices"][0]["message"]["content"]


def _reply_groq(messages: list, system: str) -> str | None:
    groq_messages = [{"role": "system", "content": GROQ_SYSTEM}]
    recent = [m for m in messages if isinstance(m.get("content"), str)][-6:]
    for m in recent:
        groq_messages.append({"role": m["role"], "content": m["content"]})

    key = _pools["groq"].current()
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": groq_messages,
            "max_tokens": 300,
            "temperature": 0.85,
        },
        timeout=30.0,
    )

    data = response.json()
    if "error" in data:
        raise Exception(str(data["error"]))
    if "choices" not in data or len(data["choices"]) == 0:
        raise Exception(f"Resposta inesperada: {data}")

    return data["choices"][0]["message"]["content"]


def _reply_ollama(messages: list, system: str) -> str | None:
    """Envia mensagem pro Ollama local com prompt condensado."""
    ollama_messages = [{"role": "system", "content": OLLAMA_SYSTEM}]
    # Pega só as últimas 10 mensagens pra não sobrecarregar o 8B
    recent = [m for m in messages if isinstance(m.get("content"), str)][-10:]
    for m in recent:
        ollama_messages.append({"role": m["role"], "content": m["content"]})

    response = httpx.post(
        f"{_ollama_url}/api/chat",
        headers={"Content-Type": "application/json"},
        json={
            "model": _ollama_model,
            "messages": ollama_messages,
            "stream": False,
        },
        timeout=60.0,  # local pode ser mais lento
    )

    data = response.json()
    if "error" in data:
        raise Exception(str(data["error"]))

    content = data.get("message", {}).get("content", "")
    if not content:
        raise Exception("Resposta vazia")

    return content


REPLY_FUNCS = {
    "claude": _reply_claude,
    "gemini": _reply_gemini,
    "zai": _reply_zai,
    "groq": _reply_groq,
    "ollama": _reply_ollama,
}


# ══════════════════════════════════════════════════════════════
# API Pública
# ══════════════════════════════════════════════════════════════

def get_provider() -> str | None:
    """Retorna o provider ativo. Se não tiver, faz varredura."""
    global _active_provider
    if _active_provider is None:
        _active_provider = _scan_providers()
        if _active_provider:
            info = PROVIDERS[_active_provider]
            pool = _pools[_active_provider]
            keys_info = f" ({pool.total} keys disponíveis)" if pool.total > 1 else ""
            print(f"\n✨ Provider da sessão: {info['emoji']} {info['name']}{keys_info}")
            print(f"   (vai usar esse até ele cair)\n")
    return _active_provider


def get_reply(messages: list, system: str) -> str:
    """
    Envia mensagem DIRETO pro provider ativo (sem varredura).
    Retry até 2x no mesmo provider antes de trocar.
    Só varre outros providers se o ativo falhar consecutivamente.
    """
    global _active_provider

    if _active_provider is None:
        get_provider()

    if _active_provider is None:
        return "[SAD] Ai, tô sem conexão com nenhum servidor agora... tenta de novo daqui a pouco?"

    pool = _pools[_active_provider]
    info = PROVIDERS[_active_provider]

    # ── Tentativa 1: envia direto, sem ping, sem varredura ──
    try:
        reply = REPLY_FUNCS[_active_provider](messages, system)
        if reply and reply.strip():
            return reply
    except Exception:
        pass

    # ── Tentativa 2: retry no mesmo provider (pode ter sido erro temporário) ──
    import time
    time.sleep(1)
    try:
        reply = REPLY_FUNCS[_active_provider](messages, system)
        if reply and reply.strip():
            return reply
    except Exception:
        pass

    # ── Tentativa 3: se tem múltiplas keys, rotaciona ──
    if pool.total > 1:
        start_index = pool.current_index
        for _ in range(pool.total - 1):
            next_key = pool.rotate()
            if not next_key or pool.current_index == start_index:
                break
            print(f"   🔑 {info['emoji']} Rotacionando pra key {pool.current_index + 1}/{pool.total}")
            if _active_provider == "claude":
                global _claude_client
                _claude_client = anthropic.Anthropic(api_key=next_key)
            try:
                reply = REPLY_FUNCS[_active_provider](messages, system)
                if reply and reply.strip():
                    return reply
            except Exception:
                continue

    # ── Todas as tentativas falharam — agora sim, troca de provider ──
    print(f"\n⚠️ {info['emoji']} {info['name']} não respondeu após múltiplas tentativas")
    print("🔄 Trocando de provider...\n")

    old_provider = _active_provider

    # Tenta os outros providers na ordem, SEM ping — envia direto
    for provider_id in PING_ORDER:
        if provider_id == old_provider:
            continue
        # Ollama não precisa de key, os outros sim
        if provider_id != "ollama" and not _pools[provider_id].has_keys():
            continue

        next_info = PROVIDERS[provider_id]
        try:
            reply = REPLY_FUNCS[provider_id](messages, system)
            if reply and reply.strip():
                _active_provider = provider_id
                print(f"🔀 Novo provider: {next_info['emoji']} {next_info['name']}")
                return reply
        except Exception:
            continue

    # Nenhum funcionou
    print("❌ Nenhum provider respondeu")
    _active_provider = None
    return "[SAD] Ai, tô com um probleminha... tenta de novo daqui a pouquinho?"


def get_active_provider_name() -> str:
    if _active_provider:
        pool = _pools[_active_provider]
        info = PROVIDERS[_active_provider]
        if pool.total > 1:
            return f"{info['name']} (key {pool.current_index + 1}/{pool.total})"
        return info["name"]
    return "Nenhum"


def get_active_provider_id() -> str | None:
    return _active_provider


def get_keys_status() -> dict:
    """Retorna status de todas as keys (pra debug)."""
    status = {}
    for provider_id, pool in _pools.items():
        status[provider_id] = {
            "total_keys": pool.total,
            "active_key": pool.current_index + 1 if pool.has_keys() else 0,
            "is_active_provider": provider_id == _active_provider,
        }
    return status


def force_rescan():
    global _active_provider
    _active_provider = None
    # Reseta todas as pools pra começar da key 1
    for pool in _pools.values():
        pool.reset()
    return get_provider()
