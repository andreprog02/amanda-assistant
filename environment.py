import os
from datetime import datetime


# Ambientes disponíveis e suas imagens
ENVIRONMENTS = {
    "home": "",           # Padrão — sem prefixo (neutral.png, happy.png, etc.)
    "pilates": "pilates_",
    "university": "university_",
    "kitchen": "kitchen_",
    "bedroom": "bedroom_",
    "cafe": "cafe_",
}

EXPRESSIONS_DIR = os.path.join("static", "expressions")


def get_current_environment() -> str:
    """Determina onde a Amanda está baseado na hora e dia."""
    now = datetime.now()
    hora = now.hour
    dia_semana = now.weekday()  # 0=seg, 6=dom

    # Madrugada/noite tarde — quarto
    if hora >= 22 or hora < 6:
        return "bedroom"

    # Fim de semana
    if dia_semana >= 5:
        if 10 <= hora < 13 or 17 <= hora < 19:
            return "kitchen"
        if 14 <= hora < 17:
            return "cafe"
        return "home"

    # Dias de semana
    dia_de_pilates = dia_semana in [0, 2, 4]  # seg, qua, sex

    # Pilates (seg/qua/sex 15h-16h)
    if dia_de_pilates and 15 <= hora < 16:
        return "pilates"

    # Faculdade (seg a sex, apenas manhã 8h-12h)
    if 8 <= hora < 12:
        return "university"

    # Cozinha (fim de tarde)
    if 17 <= hora < 19:
        return "kitchen"

    # Noite em casa
    if 19 <= hora < 22:
        return "home"

    # Resto — casa
    return "home"


def get_expression_image(emotion: str) -> str:
    """Retorna o caminho da imagem de expressão, com fallback pra sala."""
    environment = get_current_environment()
    prefix = ENVIRONMENTS.get(environment, "")

    # Tenta imagem do ambiente específico
    specific_file = f"{prefix}{emotion}.png"
    specific_path = os.path.join(EXPRESSIONS_DIR, specific_file)

    if os.path.exists(specific_path):
        return f"/static/expressions/{specific_file}"

    # Fallback: imagem padrão da sala
    default_file = f"{emotion}.png"
    default_path = os.path.join(EXPRESSIONS_DIR, default_file)

    if os.path.exists(default_path):
        return f"/static/expressions/{default_file}"

    # Fallback final: neutral da sala
    return "/static/expressions/neutral.png"


def get_environment_context() -> str:
    """Retorna contexto do ambiente pra injetar no prompt."""
    env = get_current_environment()

    descriptions = {
        "home": "Você está em casa, na sua sala, sentada na poltrona. Ambiente acolhedor e familiar.",
        "pilates": "Você está no estúdio de pilates, de roupa de treino. Ambiente energético e iluminado.",
        "university": "Você está na faculdade, entre uma aula e outra de Farmácia. Ambiente acadêmico.",
        "kitchen": "Você está na cozinha, provavelmente preparando algo. Ambiente caseiro e cheiroso.",
        "bedroom": "Você está no quarto, na cama, de pijama. Escuro, íntimo, aconchegante. Luz só do celular.",
        "cafe": "Você está numa cafeteria aconchegante, estudando ou lendo. Ambiente tranquilo com cheirinho de café.",
    }

    desc = descriptions.get(env, descriptions["home"])
    return f"ONDE VOCÊ ESTÁ AGORA: {desc}"
