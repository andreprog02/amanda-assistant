"""
plans.py — Sistema de planos e limites da Amanda

Define planos, controla limites diários, seleciona provider e voz por plano.

Uso local: user 'local' tem plano 'premium' (sem limites).
Uso online: cada usuário tem seu plano e contagem diária.

Planos:
    free     → 20 msgs/dia, Ollama/Groq, sem voz
    basic    → 150 msgs/dia, Gemini/Z.ai, Edge TTS
    premium  → 500 msgs/dia, Claude, ElevenLabs
"""

import os
from datetime import datetime, date
from typing import Optional

# ══════════════════════════════════════════════════════════════
# Definição dos Planos
# ══════════════════════════════════════════════════════════════

PLANS = {
    "free": {
        "name": "Gratuito",
        "msgs_per_day": 20,
        "voice_enabled": False,
        "voice_provider": None,
        "preferred_providers": ["ollama", "groq"],
        "can_send_photo": False,
        "memory_enabled": True,
        "price": 0,
    },
    "basic": {
        "name": "Básico",
        "msgs_per_day": 150,
        "voice_enabled": True,
        "voice_provider": "edge_tts",
        "preferred_providers": ["gemini", "zai", "groq"],
        "can_send_photo": True,
        "memory_enabled": True,
        "price": 1990,  # centavos (R$19,90)
    },
    "premium": {
        "name": "Premium",
        "msgs_per_day": 500,
        "voice_enabled": True,
        "voice_provider": "elevenlabs",
        "preferred_providers": ["claude", "gemini", "zai", "groq"],
        "can_send_photo": True,
        "memory_enabled": True,
        "price": 3990,  # centavos (R$39,90)
    },
}

# Usuário local sempre premium
LOCAL_USER = os.getenv("DEFAULT_USER_ID", "local")

# Cache de contagem diária: {user_id: {"date": "2026-07-14", "count": 42}}
_daily_counts: dict[str, dict] = {}


# ══════════════════════════════════════════════════════════════
# Contagem diária
# ══════════════════════════════════════════════════════════════

def _get_today() -> str:
    return date.today().isoformat()


def get_daily_count(user_id: str) -> int:
    """Retorna quantas mensagens o usuário mandou hoje."""
    today = _get_today()

    if user_id in _daily_counts:
        if _daily_counts[user_id]["date"] == today:
            return _daily_counts[user_id]["count"]

    # Reseta se é um novo dia
    _daily_counts[user_id] = {"date": today, "count": 0}

    # Tenta buscar do banco se disponível
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT COUNT(*) FROM messages 
               WHERE user_id = %s AND role = 'user' 
               AND created_at::date = CURRENT_DATE;""",
            (user_id,),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        _daily_counts[user_id] = {"date": today, "count": count}
        return count
    except Exception:
        return 0


def increment_daily_count(user_id: str):
    """Incrementa a contagem diária do usuário."""
    today = _get_today()
    if user_id not in _daily_counts or _daily_counts[user_id]["date"] != today:
        _daily_counts[user_id] = {"date": today, "count": 0}
    _daily_counts[user_id]["count"] += 1


# ══════════════════════════════════════════════════════════════
# Verificação de limites
# ══════════════════════════════════════════════════════════════

def get_user_plan(user_id: str) -> dict:
    """Retorna o plano do usuário."""
    # Local sempre premium
    if user_id == LOCAL_USER:
        return PLANS["premium"]

    # Busca plano do banco
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT plan FROM users WHERE id = %s;", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0] in PLANS:
            return PLANS[row[0]]
    except Exception:
        pass

    return PLANS["free"]


def get_user_plan_name(user_id: str) -> str:
    """Retorna o nome do plano do usuário."""
    if user_id == LOCAL_USER:
        return "premium"

    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT plan FROM users WHERE id = %s;", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass

    return "free"


def check_limit(user_id: str) -> dict:
    """
    Verifica se o usuário pode enviar mensagem.
    
    Retorna:
        {"allowed": True/False, "remaining": N, "limit": N, "plan": "nome"}
    """
    plan = get_user_plan(user_id)
    plan_name = get_user_plan_name(user_id)
    limit = plan["msgs_per_day"]
    count = get_daily_count(user_id)
    remaining = max(0, limit - count)

    return {
        "allowed": count < limit,
        "remaining": remaining,
        "used": count,
        "limit": limit,
        "plan": plan_name,
    }


def can_use_voice(user_id: str) -> bool:
    """Verifica se o plano permite voz."""
    plan = get_user_plan(user_id)
    return plan["voice_enabled"]


def can_send_photo(user_id: str) -> bool:
    """Verifica se o plano permite enviar fotos."""
    plan = get_user_plan(user_id)
    return plan["can_send_photo"]


def get_preferred_providers(user_id: str) -> list:
    """Retorna os providers preferidos do plano."""
    plan = get_user_plan(user_id)
    return plan["preferred_providers"]


def get_voice_provider_for_plan(user_id: str) -> Optional[str]:
    """Retorna qual provider de voz o plano permite."""
    plan = get_user_plan(user_id)
    return plan.get("voice_provider")


# ══════════════════════════════════════════════════════════════
# Mensagens de limite
# ══════════════════════════════════════════════════════════════

def get_limit_message(user_id: str) -> str:
    """Retorna mensagem quando o limite é atingido."""
    plan_name = get_user_plan_name(user_id)
    limit_info = check_limit(user_id)

    if plan_name == "free":
        return (
            "[SAD] Ai amor, minhas mensagens grátis acabaram por hoje... "
            "Se quiser continuar conversando comigo, dá uma olhada nos planos. "
            "Amanhã a gente se fala de novo, tá?"
        )
    elif plan_name == "basic":
        return (
            "[SAD] Amor, a gente já conversou bastante hoje né? "
            "Minhas mensagens do plano básico acabaram. "
            "Se quiser mais, tem o plano premium com 500 msgs por dia!"
        )
    else:
        return (
            "[SAD] Nossa, a gente conversou MUITO hoje hein! "
            "Até o premium tem limite... mas amanhã a gente continua, tá? "
            "Descansa um pouco, eu vou estar aqui te esperando."
        )


# ══════════════════════════════════════════════════════════════
# Info pra exibir no frontend
# ══════════════════════════════════════════════════════════════

def get_plan_info(user_id: str) -> dict:
    """Retorna info completa do plano pra exibir no frontend."""
    plan = get_user_plan(user_id)
    plan_name = get_user_plan_name(user_id)
    limit = check_limit(user_id)

    return {
        "plan": plan_name,
        "plan_display": plan["name"],
        "msgs_remaining": limit["remaining"],
        "msgs_limit": limit["limit"],
        "msgs_used": limit["used"],
        "voice_enabled": plan["voice_enabled"],
        "photo_enabled": plan["can_send_photo"],
        "price": plan["price"],
    }


def list_plans() -> list:
    """Lista todos os planos disponíveis."""
    return [
        {
            "id": plan_id,
            "name": plan["name"],
            "msgs_per_day": plan["msgs_per_day"],
            "voice": plan["voice_enabled"],
            "photo": plan["can_send_photo"],
            "price": plan["price"],
            "voice_quality": "ElevenLabs" if plan.get("voice_provider") == "elevenlabs"
                           else "Edge TTS" if plan.get("voice_provider") == "edge_tts"
                           else "Sem voz",
        }
        for plan_id, plan in PLANS.items()
    ]
