"""
Módulo de ambiente — gerencia expressões/imagens da Amanda
e contexto de ambiente (clima, local, etc).
"""

# Mapeamento de emoção → caminho da imagem
# Ajuste os caminhos para suas imagens reais
EXPRESSION_IMAGES = {
    "neutral": "/static/expressions/neutral.png",
    "happy": "/static/expressions/happy.png",
    "laughing": "/static/expressions/laughing.png",
    "thinking": "/static/expressions/thinking.png",
    "flirty": "/static/expressions/flirty.png",
    "spicy": "/static/expressions/spicy.png",
    "loving": "/static/expressions/loving.png",
    "surprised": "/static/expressions/surprised.png",
    "sad": "/static/expressions/sad.png",
    "playful": "/static/expressions/playful.png",
}


def get_expression_image(emotion: str) -> str:
    """Retorna o caminho da imagem para a emoção dada."""
    return EXPRESSION_IMAGES.get(emotion, EXPRESSION_IMAGES["neutral"])


def get_environment_context() -> str:
    """Retorna contexto de ambiente para o system prompt."""
    from datetime import datetime

    now = datetime.now()
    hora = now.hour

    if 5 <= hora < 12:
        ambiente = "Manhã, luz natural entrando pela janela."
    elif 12 <= hora < 18:
        ambiente = "Tarde, luz do dia."
    elif 18 <= hora < 21:
        ambiente = "Entardecer, luz mais quente."
    else:
        ambiente = "Noite, luzes baixas, ambiente aconchegante."

    return f"AMBIENTE ATUAL: {ambiente}"
