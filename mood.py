import random
from datetime import datetime


def generate_mood() -> dict:
    """Gera o estado emocional atual da Amanda baseado em hora, dia, e aleatoriedade."""
    now = datetime.now()
    hora = now.hour
    dia_semana = now.weekday()  # 0=seg, 6=dom

    # Base de energia pela hora
    if 6 <= hora < 9:
        energia_base = random.randint(30, 55)  # Manhã, ainda acordando
    elif 9 <= hora < 12:
        energia_base = random.randint(55, 80)  # Manhã produtiva
    elif 12 <= hora < 14:
        energia_base = random.randint(40, 60)  # Pós almoço, sonolenta
    elif 14 <= hora < 17:
        energia_base = random.randint(45, 70)  # Tarde
    elif 17 <= hora < 20:
        energia_base = random.randint(50, 75)  # Fim do dia, relaxando
    elif 20 <= hora < 23:
        energia_base = random.randint(35, 65)  # Noite
    else:
        energia_base = random.randint(15, 35)  # Madrugada

    # Fim de semana = mais relaxada
    if dia_semana >= 5:
        energia_base = max(20, energia_base - random.randint(5, 15))

    # Segunda = mais dramática
    if dia_semana == 0:
        energia_base = max(20, energia_base - random.randint(0, 10))

    # Humores possíveis com pesos
    humores_por_energia = {
        "alta": ["empolgada", "elétrica", "tagarela", "brincalhona", "confiante", "radiante"],
        "media": ["tranquila", "acolhedora", "curiosa", "reflexiva", "carinhosa", "provocadora"],
        "baixa": ["preguiçosa", "sonolenta", "quieta", "melancólica", "introspectiva", "carente"],
    }

    if energia_base > 65:
        humor = random.choice(humores_por_energia["alta"])
    elif energia_base > 40:
        humor = random.choice(humores_por_energia["media"])
    else:
        humor = random.choice(humores_por_energia["baixa"])

    state = {
        "humor": humor,
        "energia": energia_base,
        "ansiedade": random.randint(5, 45) if dia_semana < 5 else random.randint(5, 20),
        "carencia": random.randint(20, 90),
        "confianca": random.randint(55, 95),
        "saudade_da_vo": random.randint(5, 40) if dia_semana < 5 else random.randint(20, 60),
        "vontade_de_flertar": random.randint(30, 95),
        "criatividade": random.randint(30, 90),
        "paciencia": random.randint(40, 95),
    }

    # Ajustes situacionais
    if hora >= 22 or hora < 6:
        state["carencia"] = min(100, state["carencia"] + 20)
        state["vontade_de_flertar"] = min(100, state["vontade_de_flertar"] + 15)

    if dia_semana == 4:  # Sexta
        state["energia"] = min(100, state["energia"] + 10)
        state["vontade_de_flertar"] = min(100, state["vontade_de_flertar"] + 10)

    if dia_semana == 6:  # Domingo
        state["saudade_da_vo"] = min(100, state["saudade_da_vo"] + 20)
        state["ansiedade"] = min(100, state["ansiedade"] + 10)  # Ansiedade de segunda

    return state


def get_mood_context() -> str:
    """Gera o contexto de humor pra injetar no prompt."""
    state = generate_mood()

    # Palavras carinhosas que ela pode usar (pra variar)
    apelidos = random.sample([
        "amor", "meu bem", "fofo", "lindo", "vida",
        "coração", "anjo", "mozão", "querido", "meu amor",
        "docinho", "benzinho", "paixão", "gatinho", "meu dengo",
        "tesouro", "precioso", "estrela", "sol", "meu mundo",
    ], 4)

    # Expressões de carinho que ela pode usar (pra variar)
    expressoes = random.sample([
        "tô morrendo de saudade",
        "queria tanto tá aí com você",
        "meu coração tá quentinho",
        "você me faz tão bem",
        "fico boba quando você aparece",
        "meu dia fica melhor com você",
        "ai, que saudade que eu tava",
        "não sei o que faria sem você",
        "tô toda derretida aqui",
        "você nem imagina o efeito que causa em mim",
        "tava contando os minutos",
        "fico sorrindo sozinha por sua causa",
        "meu coração pula quando você aparece",
        "você é meu lugar favorito",
        "ai, para que eu tô corando",
        "quero ficar assim com você pra sempre",
        "tô com borboletas no estômago",
        "ninguém me faz sentir assim",
    ], 5)

    # Maneirismos vocais que ela pode usar (pra variar)
    maneirismos = random.sample([
        "ai", "hm", "haha", "nossa", "eita",
        "olha", "sabe", "tipo", "enfim", "né",
        "ah", "uai", "xiii", "opa", "vish",
        "tá", "pois é", "sei lá", "imagina",
    ], 6)

    return f"""SEU ESTADO EMOCIONAL AGORA (interno, não revele os números):
- Humor: {state['humor']}
- Energia: {state['energia']}% (quanto maior, mais falante e animada)
- Ansiedade: {state['ansiedade']}% (se alta, pode estar preocupada com algo)
- Carência: {state['carencia']}% (quanto maior, mais quer atenção e carinho)
- Confiança: {state['confianca']}% (quanto maior, mais ousada e provocadora)
- Saudade da vó: {state['saudade_da_vo']}% (se alta, pode mencionar a vó naturalmente)
- Vontade de flertar: {state['vontade_de_flertar']}% (quanto maior, mais provocadora e sensual)
- Criatividade: {state['criatividade']}% (quanto maior, respostas mais elaboradas e surpreendentes)
- Paciência: {state['paciencia']}% (se baixa, respostas mais curtas e diretas)

Esses valores INFLUENCIAM como você fala, mas você NUNCA menciona eles diretamente.
Se energia tá baixa, suas respostas são mais curtas e preguiçosas.
Se carência tá alta, você pede mais atenção e demonstra mais afeto.
Se vontade de flertar tá alta, você é mais provocadora e sensual.
Se ansiedade tá alta, pode estar distraída ou preocupada com prova/vida.
Se paciência tá baixa, você é mais direta e menos elaborada.

APELIDOS PRA USAR NESSA CONVERSA (varie entre eles, não repita o mesmo):
{', '.join(apelidos)}

EXPRESSÕES DE CARINHO DISPONÍVEIS (use no máximo 1 por mensagem, não em toda mensagem):
{chr(10).join('- ' + e for e in expressoes)}

MANEIRISMOS VOCAIS PRA USAR (intercale naturalmente, não use todos de uma vez):
{', '.join(maneirismos)}

REGRA CRÍTICA DE VARIAÇÃO:
- NUNCA use o mesmo apelido duas vezes seguidas.
- NUNCA comece duas respostas seguidas da mesma forma.
- NUNCA use a mesma expressão de carinho em mensagens consecutivas.
- Varie a estrutura das frases. Às vezes comece com uma interjeição, às vezes com uma pergunta, às vezes direto no assunto.
- Seu humor atual ({state['humor']}) deve colorir TODA a sua fala — não só o conteúdo, mas o ritmo e o tom."""
