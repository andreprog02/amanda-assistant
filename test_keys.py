"""
test_keys.py — Testa todas as API keys do projeto

Roda: python test_keys.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 50)
print("🔑 TESTE DE API KEYS")
print("=" * 50)


# ── ElevenLabs ──
print("\n🎙️ ElevenLabs:")
key = os.getenv("ELEVENLABS_API_KEY", "")
if not key:
    print("   ❌ ELEVENLABS_API_KEY não encontrada no .env")
else:
    # Mostra os primeiros e últimos caracteres
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key[:4] + "..."
    print(f"   Key encontrada: {masked} ({len(key)} chars)")
    
    import httpx
    
    # Teste 1: endpoint /v1/user
    print(f"   Testando /v1/user...", end=" ")
    try:
        r = httpx.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": key},
            timeout=10.0,
        )
        print(f"HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            sub = data.get("subscription", {})
            print(f"   ✅ Plano: {sub.get('tier', '?')}")
            print(f"   ✅ Chars usados: {sub.get('character_count', '?')}/{sub.get('character_limit', '?')}")
            remaining = sub.get('character_limit', 0) - sub.get('character_count', 0)
            print(f"   ✅ Restantes: {remaining:,}")
        elif r.status_code == 401:
            print(f"   ❌ Key inválida! Resposta: {r.text[:200]}")
        else:
            print(f"   ⚠️ Resposta: {r.text[:200]}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    # Teste 2: gerar áudio
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "zGjIP4SZlMnY9m93k97r")
    print(f"\n   Testando geração de áudio (voice: {voice_id})...", end=" ")
    try:
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": key,
                "Content-Type": "application/json",
            },
            json={
                "text": "oi, tudo bem?",
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.75,
                },
            },
            timeout=15.0,
        )
        print(f"HTTP {r.status_code}")
        if r.status_code == 200:
            print(f"   ✅ Áudio gerado! ({len(r.content):,} bytes)")
        else:
            print(f"   ❌ Resposta: {r.text[:300]}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")


# ── Claude ──
print("\n\n🟣 Claude (Anthropic):")
key = os.getenv("ANTHROPIC_API_KEY", "")
if not key:
    print("   ❌ ANTHROPIC_API_KEY não encontrada no .env")
else:
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key[:4] + "..."
    print(f"   Key encontrada: {masked} ({len(key)} chars)")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        model = os.getenv("MODEL", "claude-sonnet-4-6")
        print(f"   Testando modelo {model}...", end=" ")
        r = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "oi"}],
        )
        print(f"✅ Respondeu!")
    except Exception as e:
        print(f"❌ {e}")


# ── Gemini ──
print("\n\n🔵 Gemini (Google):")
key = os.getenv("GEMINI_API_KEY", "")
if not key:
    print("   ❌ GEMINI_API_KEY não encontrada no .env")
else:
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key[:4] + "..."
    print(f"   Key encontrada: {masked} ({len(key)} chars)")
    import httpx
    print(f"   Testando...", end=" ")
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [{"text": "oi"}]}],
                "generationConfig": {"maxOutputTokens": 10},
            },
            timeout=15.0,
        )
        data = r.json()
        if "candidates" in data:
            print(f"✅ Respondeu!")
        elif "error" in data:
            print(f"❌ {data['error'].get('message', data['error'])}")
        else:
            print(f"⚠️ Resposta inesperada: {data}")
    except Exception as e:
        print(f"❌ {e}")


# ── Z.ai (GLM) ──
print("\n\n🟢 Z.ai (GLM):")
key = os.getenv("ZAI_API_KEY", "")
if not key:
    print("   ❌ ZAI_API_KEY não encontrada no .env")
else:
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key[:4] + "..."
    print(f"   Key encontrada: {masked} ({len(key)} chars)")
    import httpx
    print(f"   Testando glm-4.5-flash...", end=" ")
    try:
        r = httpx.post(
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
        data = r.json()
        if "choices" in data:
            print(f"✅ Respondeu!")
        elif "error" in data:
            print(f"❌ {data['error']}")
        else:
            print(f"⚠️ Resposta inesperada: {data}")
    except Exception as e:
        print(f"❌ {e}")


# ── Groq ──
print("\n\n🟠 Groq:")
key = os.getenv("GROQ_API_KEY", "")
if not key:
    print("   ❌ GROQ_API_KEY não encontrada no .env")
else:
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key[:4] + "..."
    print(f"   Key encontrada: {masked} ({len(key)} chars)")
    import httpx
    print(f"   Testando...", end=" ")
    try:
        r = httpx.post(
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
        data = r.json()
        if "choices" in data:
            print(f"✅ Respondeu!")
        else:
            print(f"❌ {data}")
    except Exception as e:
        print(f"❌ {e}")


# ── Resumo ──
print("\n" + "=" * 50)
print("📋 RESUMO DO .env:")
print("=" * 50)
env_vars = [
    "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "ZAI_API_KEY", "GROQ_API_KEY",
    "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
    "EDGE_TTS_VOICE", "MODEL",
]
for var in env_vars:
    val = os.getenv(var, "")
    if val:
        if "KEY" in var:
            # Conta quantas keys (separadas por vírgula)
            keys = [k.strip() for k in val.split(",") if k.strip()]
            if len(keys) > 1:
                print(f"   ✅ {var}: {len(keys)} keys configuradas")
            else:
                masked = val[:8] + "..." + val[-4:] if len(val) > 12 else val
                print(f"   ✅ {var}: {masked}")
        else:
            print(f"   ✅ {var}: {val}")
    else:
        print(f"   ⬚  {var}: não configurada")