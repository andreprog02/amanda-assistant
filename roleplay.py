"""
roleplay.py — Sistema de Roleplay da Amanda

Substitui o environment.py. Cada roleplay é uma pasta em static/roleplay/
com as imagens de expressão (neutral.png, happy.png, etc).

Adicionar um roleplay novo = criar pasta + adicionar entrada no ROLEPLAYS.

Estrutura:
  static/roleplay/
  ├── sala/
  │   ├── neutral.png
  │   └── happy.png
  ├── morning_tea/
  │   ├── neutral.png
  │   ├── happy.png
  │   └── ...
  ├── pilates/
  ├── faculdade/
  ├── cozinha/
  ├── quarto/
  ├── cafe/
  ├── nail_designer/
  └── uber/
"""

import os
from datetime import datetime
from typing import Optional


ROLEPLAY_DIR = os.path.join("static", "roleplay")
FALLBACK_ROLEPLAY = "main"

# ══════════════════════════════════════════════════════════════
# Definição dos Roleplays
# ══════════════════════════════════════════════════════════════
#
# Cada roleplay tem:
#   folder:      nome da pasta em static/roleplay/
#   description: contexto pro prompt (onde ela tá, o que tá fazendo, como tá vestida)
#   schedule:    lista de regras de agendamento (verificadas em ordem, primeira que bate ganha)
#
# Regras de schedule:
#   days:       lista de dias (0=seg, 6=dom) ou "weekday" / "weekend" / "all"
#   start:      hora de início (float, ex: 6.25 = 6:15)
#   end:        hora de fim (float, ex: 16.5 = 16:30)
#   priority:   quanto maior, mais prioridade se dois roleplays competirem (default=0)
#

ROLEPLAYS = {
    "quarto": {
        "folder": "quarto",
        "description": (
            "Você tá no quarto, na cama, de pijama. "
            "Escuro, só a luz do celular iluminando seu rosto. "
            "Íntimo, aconchegante, silencioso."
        ),
        "schedule": [
            {"days": "all", "start": 22.0, "end": 24.0, "priority": 10},
            {"days": "all", "start": 0.0, "end": 6.0, "priority": 10},
        ],
    },

    "morning_tea": {
        "folder": "morning_tea",
        "description": (
            "Você tá na cozinha de pijama rosa, descalça, tomando seu chá da manhã. "
            "Fim de semana, sem pressa nenhuma. Sol entrando pela janela. "
            "Ambiente quentinho, cheiro de chá. Você tá de boa curtindo o momento."
        ),
        "schedule": [
            {"days": "weekend", "start": 6.25, "end": 16.5, "priority": 5},
        ],
    },

    "faculdade": {
        "folder": "faculdade",
        "description": (
            "Você tá na faculdade, entre uma aula e outra de Farmácia. "
            "Provavelmente no corredor ou no intervalo, mexendo no celular. "
            "Mochila nas costas, cabelo preso."
        ),
        "schedule": [
            {"days": "weekday", "start": 8.0, "end": 12.0, "priority": 5},
            {"days": "weekday", "start": 14.0, "end": 17.0, "priority": 2},
        ],
    },

    "pilates": {
        "folder": "pilates",
        "description": (
            "Você tá no estúdio de pilates, de roupa de treino. "
            "Legging preta, top, cabelo preso. Suada, cansada mas se sentindo ótima. "
            "Ambiente iluminado, cheiro de borracha."
        ),
        "schedule": [
            # seg=0, qua=2, sex=4 das 15h às 16h
            {"days": [0, 2, 4], "start": 15.0, "end": 16.0, "priority": 8},
        ],
    },

    "cozinha": {
        "folder": "cozinha",
        "description": (
            "Você tá na cozinha, provavelmente cozinhando algo. "
            "Ambiente caseiro, cheiroso. Talvez de avental, cabelo preso. "
            "Panela no fogo, música baixinha tocando."
        ),
        "schedule": [
            {"days": "weekday", "start": 17.0, "end": 19.0, "priority": 3},
            {"days": "weekend", "start": 17.0, "end": 19.0, "priority": 3},
        ],
    },

    "cafe": {
        "folder": "cafe",
        "description": (
            "Você tá numa cafeteria aconchegante, estudando ou lendo. "
            "Ambiente tranquilo, cheirinho de café. "
            "Notebook aberto, xícara do lado."
        ),
        "schedule": [
            {"days": "weekend", "start": 16.5, "end": 17.0, "priority": 2},
        ],
    },

    "nail_designer": {
        "folder": "nail_designer",
        "description": (
            "Você tá no salão fazendo as unhas. "
            "Sentada na cadeira, mãos na mesa da manicure. "
            "Conversando com a nail designer, relaxada."
        ),
        "schedule": [
            # Sábado de manhã
            {"days": [5], "start": 17.0, "end": 20.0, "priority": 6},
        ],
    },

    "uber": {
        "folder": "uber",
        "description": (
            "Você tá no carro, indo ou voltando de algum lugar. "
            "No banco de trás, olhando pela janela ou mexendo no celular. "
            "Trânsito, cidade passando."
        ),
        "schedule": [
            # Sem horário fixo — só ativa manualmente ou por evento
        ],
    },

    "sala": {
        "folder": "sala",
        "description": (
            "Você tá em casa, na sala, no sofá. "
            "Ambiente acolhedor, familiar. Talvez de moletom, manta no colo."
        ),
        "schedule": [
            {"days": "weekday", "start": 19.0, "end": 22.0, "priority": 1},
        ],
    },

    "main": {
        "folder": "main",
        "description": (
            "Você tá em casa, de boa. "
            "Sem nada específico acontecendo, só vivendo."
        ),
        "schedule": [
            # Fallback universal — pega tudo que nenhum outro roleplay cobriu
            {"days": "all", "start": 0.0, "end": 24.0, "priority": -1},
        ],
    },
}


# ══════════════════════════════════════════════════════════════
# Motor de resolução
# ══════════════════════════════════════════════════════════════

def _matches_day(rule_days, weekday: int) -> bool:
    """Verifica se o dia bate com a regra."""
    if rule_days == "all":
        return True
    if rule_days == "weekday":
        return weekday < 5
    if rule_days == "weekend":
        return weekday >= 5
    if isinstance(rule_days, list):
        return weekday in rule_days
    return False


def get_active_roleplay(now: Optional[datetime] = None) -> str:
    """Determina qual roleplay tá ativo baseado na hora e dia."""
    if now is None:
        now = datetime.now()

    weekday = now.weekday()
    hora_decimal = now.hour + now.minute / 60

    best_match = FALLBACK_ROLEPLAY
    best_priority = -999

    for rp_name, rp_config in ROLEPLAYS.items():
        for rule in rp_config.get("schedule", []):
            if not _matches_day(rule.get("days", "all"), weekday):
                continue

            start = rule.get("start", 0)
            end = rule.get("end", 24)
            priority = rule.get("priority", 0)

            if start <= hora_decimal < end and priority > best_priority:
                best_match = rp_name
                best_priority = priority

    return best_match


def get_roleplay_image(emotion: str, roleplay: Optional[str] = None) -> str:
    """Retorna o caminho da imagem pra emoção no roleplay ativo."""
    if roleplay is None:
        roleplay = get_active_roleplay()

    rp_config = ROLEPLAYS.get(roleplay, ROLEPLAYS[FALLBACK_ROLEPLAY])
    folder = rp_config["folder"]

    # Tenta: pasta/emotion.png
    path1 = os.path.join(ROLEPLAY_DIR, folder, f"{emotion}.png")
    if os.path.exists(path1):
        return f"/static/roleplay/{folder}/{emotion}.png"

    # Tenta: pasta/folder_emotion.png (nome com prefixo)
    path2 = os.path.join(ROLEPLAY_DIR, folder, f"{folder}_{emotion}.png")
    if os.path.exists(path2):
        return f"/static/roleplay/{folder}/{folder}_{emotion}.png"

    # Fallback: neutral do mesmo roleplay (ambos padrões)
    for name in [f"neutral.png", f"{folder}_neutral.png"]:
        path = os.path.join(ROLEPLAY_DIR, folder, name)
        if os.path.exists(path):
            return f"/static/roleplay/{folder}/{name}"

    # Fallback: main
    fallback = FALLBACK_ROLEPLAY
    for name in [f"{emotion}.png", f"{fallback}_{emotion}.png", "neutral.png", f"{fallback}_neutral.png"]:
        path = os.path.join(ROLEPLAY_DIR, fallback, name)
        if os.path.exists(path):
            return f"/static/roleplay/{fallback}/{name}"

    return f"/static/roleplay/{fallback}/neutral.png"


def get_roleplay_context(roleplay: Optional[str] = None) -> str:
    """Retorna o contexto do roleplay ativo pro prompt."""
    if roleplay is None:
        roleplay = get_active_roleplay()

    rp_config = ROLEPLAYS.get(roleplay, ROLEPLAYS[FALLBACK_ROLEPLAY])
    desc = rp_config["description"]

    return f"ONDE VOCÊ ESTÁ AGORA: {desc}"


def list_available_roleplays() -> list[dict]:
    """Lista todos os roleplays e quais têm imagens."""
    result = []
    for name, config in ROLEPLAYS.items():
        folder_path = os.path.join(ROLEPLAY_DIR, config["folder"])
        has_images = os.path.exists(folder_path)
        image_count = 0
        if has_images:
            image_count = len([f for f in os.listdir(folder_path) if f.endswith(".png")])

        result.append({
            "name": name,
            "folder": config["folder"],
            "has_images": has_images,
            "image_count": image_count,
            "schedule_rules": len(config.get("schedule", [])),
        })
    return result


# ══════════════════════════════════════════════════════════════
# Roleplay manual (forçar um roleplay específico)
# ══════════════════════════════════════════════════════════════

_forced_roleplay: Optional[str] = None

def force_roleplay(name: Optional[str]):
    """Força um roleplay específico (None = voltar ao automático)."""
    global _forced_roleplay
    if name and name in ROLEPLAYS:
        _forced_roleplay = name
        print(f"🎭 Roleplay forçado: {name}")
    else:
        _forced_roleplay = None
        print("🎭 Roleplay: modo automático")


def get_current_roleplay() -> str:
    """Retorna o roleplay atual (forçado ou automático)."""
    if _forced_roleplay:
        return _forced_roleplay
    return get_active_roleplay()
