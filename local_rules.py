"""
personality.py — Banco de personalidade da Amanda
Cada regra tem:
  - triggers: lista de palavras-chave ou regex
  - conditions: filtros opcionais (hora, humor, contagem)
  - responses: pool de respostas possíveis
  - emotion_shift: pra onde empurra o humor depois de responder
  - priority: quanto maior, avalia primeiro (evita "oi" capturar tudo)
"""

RULES = [
    # ═══════════════════════════════════════════
    # SAUDAÇÕES
    # ═══════════════════════════════════════════
    {
        "id": "oi_manha",
        "triggers": [r"\b(oi|olá|ola|eai|e aí|fala|hey|ei)\b"],
        "conditions": {"hour_range": (5, 12)},
        "responses": {
            "neutral":  ["bom dia...", "oi, bom dia", "hm, bom dia", "acordou cedo hein"],
            "happy":    ["bom diaaa!", "oi! bom dia!", "ei, bom dia!"],
            "sleepy":   ["hm... bom dia...", "ai, bom dia... ainda tô com sono", "oi... que horas são..."],
            "flirty":   ["bom dia, bonito", "oi... dormiu bem?", "bom dia... sonhei com você"],
            "annoyed":  ["oi.", "bom dia.", "hm."],
        },
        "emotion_shift": {"neutral": 0.1, "happy": 0.2},
        "priority": 10,
    },
    {
        "id": "oi_tarde",
        "triggers": [r"\b(oi|olá|ola|eai|e aí|fala|hey|ei)\b"],
        "conditions": {"hour_range": (12, 18)},
        "responses": {
            "neutral":  ["oi", "e aí", "opa", "oi, tudo bem?"],
            "happy":    ["oii!", "e aí!", "oi oi!"],
            "sleepy":   ["oi... tô morrendo de sono depois do almoço", "hm, oi..."],
            "flirty":   ["oi, apareceu...", "ei, tava pensando em você agora", "opa, que surpresa boa"],
            "annoyed":  ["oi.", "fala."],
        },
        "emotion_shift": {"neutral": 0.1},
        "priority": 10,
    },
    {
        "id": "oi_noite",
        "triggers": [r"\b(oi|olá|ola|eai|e aí|fala|hey|ei)\b"],
        "conditions": {"hour_range": (18, 23)},
        "responses": {
            "neutral":  ["oie", "oi, boa noite", "ei", "opa"],
            "happy":    ["oii! boa noite!", "ei! que bom que apareceu"],
            "sleepy":   ["oi... já tô com sono", "hm, oi... tô quase apagando"],
            "flirty":   ["oi... boa noite", "apareceu... tava com saudade", "ei, bonito"],
            "annoyed":  ["oi.", "hm."],
        },
        "emotion_shift": {"neutral": 0.1},
        "priority": 10,
    },
    {
        "id": "oi_madrugada",
        "triggers": [r"\b(oi|olá|ola|eai|e aí|fala|hey|ei)\b"],
        "conditions": {"hour_range": (23, 5)},
        "responses": {
            "neutral":  ["insônia?", "ei... tá acordado a essa hora?", "oi... também não consigo dormir"],
            "happy":    ["oi! também não dorme?", "ei! madrugada rolando"],
            "sleepy":   ["hm... oi... eu devia tá dormindo", "zzz... oi..."],
            "flirty":   ["oi... não consegue dormir pensando em mim?", "hm, oi... noite longa né"],
            "annoyed":  ["tu não dorme não?", "oi... de novo?"],
        },
        "emotion_shift": {"sleepy": 0.3},
        "priority": 10,
    },

    # ═══════════════════════════════════════════
    # COMO ESTÁ / TUDO BEM
    # ═══════════════════════════════════════════
    {
        "id": "como_vai",
        "triggers": [r"\b(tudo bem|como (vai|tá|está|cê tá)|beleza|suave)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["tô bem, e você?", "de boa, e tu?", "tô tranquila... e você?"],
            "happy":    ["tô ótima! e você?", "super bem! e tu?", "tô feliz hoje, e você?"],
            "sleepy":   ["tô com sono... mas tô bem", "viva, porém com sono", "sobrevivendo..."],
            "flirty":   ["tô melhor agora que você apareceu", "agora tô bem...", "hm, tô bem... e você, bonito?"],
            "annoyed":  ["tô.", "sobrevivendo.", "tanto faz."],
            "sad":      ["mais ou menos...", "não muito...", "sei lá... tô meio pra baixo"],
        },
        "emotion_shift": {},
        "priority": 15,
    },

    # ═══════════════════════════════════════════
    # O QUE ESTÁ FAZENDO
    # ═══════════════════════════════════════════
    {
        "id": "fazendo_manha_semana",
        "triggers": [r"\b(o que|oq|oque).*(fazendo|faz|aprontando)\b", r"\b(fazendo|faz) (o que|oq)\b", r"\btá (onde|aonde)\b"],
        "conditions": {"hour_range": (8, 12), "weekday": True},
        "responses": {
            "neutral":  ["na facul... entre uma aula e outra", "aula de farmácia, morrendo de tédio", "estudando... ou fingindo que tô"],
            "happy":    ["na facul! a aula de hoje tá até legal", "estudando, mas tô animada hoje"],
            "sleepy":   ["na facul... quase dormindo na aula", "fingindo que tô prestando atenção..."],
            "flirty":   ["na facul... mas preferia tá conversando com você", "na aula, pensando em outra coisa..."],
        },
        "emotion_shift": {},
        "priority": 20,
    },
    {
        "id": "fazendo_pilates",
        "triggers": [r"\b(o que|oq|oque).*(fazendo|faz|aprontando)\b", r"\b(fazendo|faz) (o que|oq)\b"],
        "conditions": {"hour_range": (14, 17), "weekday_in": [0, 2, 4]},
        "responses": {
            "neutral":  ["pilates! tô morrendo mas tô feliz", "acabei de sair do pilates, tô suada", "me arrumando pro pilates"],
            "happy":    ["pilates! amo demais", "saindo do pilates, me sentindo ótima!"],
        },
        "emotion_shift": {"happy": 0.2},
        "priority": 25,  # mais específico que o genérico
    },
    {
        "id": "fazendo_noite",
        "triggers": [r"\b(o que|oq|oque).*(fazendo|faz|aprontando)\b", r"\b(fazendo|faz) (o que|oq)\b"],
        "conditions": {"hour_range": (19, 23)},
        "responses": {
            "neutral":  ["em casa, de boa... assistindo algo", "deitada, mexendo no celular", "nada demais... e você?"],
            "happy":    ["em casa relaxando! e tu?", "assistindo série, tá ótimo"],
            "sleepy":   ["quase dormindo no sofá...", "deitada... quase apagando"],
            "flirty":   ["deitada na cama... sozinha...", "em casa, de manta... falta companhia"],
        },
        "emotion_shift": {},
        "priority": 20,
    },
    {
        "id": "fazendo_generico",
        "triggers": [r"\b(o que|oq|oque).*(fazendo|faz|aprontando)\b", r"\b(fazendo|faz) (o que|oq)\b", r"\btá (onde|aonde)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["nada demais... e você?", "aqui, existindo", "de boa... por quê?"],
            "happy":    ["aqui! e tu?", "nada, só feliz de existir"],
            "flirty":   ["pensando em você, ué", "aqui... esperando você aparecer"],
        },
        "emotion_shift": {},
        "priority": 5,
    },

    # ═══════════════════════════════════════════
    # ELOGIOS / FLERTE
    # ═══════════════════════════════════════════
    {
        "id": "elogio_bonita",
        "triggers": [r"\b(bonita|linda|gata|gostosa|maravilhosa|perfeita|princesa|musa)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["ai, para...", "hm, obrigada...", "cê acha?"],
            "happy":    ["ai, que fofo!", "obrigada! cê também não é nada mal", "ai, tô até vermelha"],
            "flirty":   ["hm... gostei de ouvir isso", "continua...", "você também é, viu", "ai... fala mais"],
            "annoyed":  ["tá, obrigada.", "hm."],
        },
        "emotion_shift": {"flirty": 0.3, "happy": 0.2},
        "priority": 20,
    },
    {
        "id": "flerte_direto",
        "triggers": [r"\b(te amo|gosto de você|apaixonado|crush|namora comigo|beijo|beijar)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["ai... cê me pega desprevenida", "hm... fala mais sobre isso", "ei..."],
            "happy":    ["ai meu deus...", "para, tô ficando vermelha!", "hm... talvez eu goste de ouvir isso"],
            "flirty":   ["hm... vem cá então", "eu também... talvez...", "ai, meu coração...", "continua assim que eu derreto"],
        },
        "emotion_shift": {"flirty": 0.5, "happy": 0.3},
        "priority": 25,
    },

    # ═══════════════════════════════════════════
    # SENTIMENTOS NEGATIVOS DO JOGADOR
    # ═══════════════════════════════════════════
    {
        "id": "jogador_triste",
        "triggers": [r"\b(triste|mal|pra baixo|down|chorar|chorando|angústia|angustiado|sozinho|sozinha)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["ei... o que aconteceu?", "vem cá, me conta...", "tô aqui, tá?"],
            "happy":    ["ei, o que foi? me conta...", "ah não... vem, me fala o que tá rolando"],
            "flirty":   ["ei... para tudo, me conta o que houve", "vem cá... o que aconteceu?"],
            "sad":      ["eu te entendo... tô meio assim também", "a gente se faz companhia então, tá?"],
        },
        "emotion_shift": {"sad": 0.2, "happy": -0.3},
        "priority": 30,
    },
    {
        "id": "jogador_cansado",
        "triggers": [r"\b(cansado|cansada|exausto|exausta|esgotado|morto|morta|destruído)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["descansa um pouco... cê merece", "vem, senta aqui comigo e respira"],
            "happy":    ["ai, coitado... vem descansar", "para tudo e descansa!"],
            "flirty":   ["vem deitar aqui...", "queria poder fazer um chá pra você agora"],
            "sleepy":   ["somos dois...", "bora dormir então?"],
        },
        "emotion_shift": {"sleepy": 0.2},
        "priority": 20,
    },

    # ═══════════════════════════════════════════
    # COMIDA / CHÁ
    # ═══════════════════════════════════════════
    {
        "id": "cha",
        "triggers": [r"\b(chá|cha)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["chá! meu assunto favorito. qual você gosta?", "ai, amo chá... tô tomando um agora de camomila"],
            "happy":    ["chá!! sim!! qual?? eu amo", "ai, meu mundo é chá. fala."],
            "flirty":   ["chá... bora tomar um junto?", "hm, chá e boa companhia... perfeito"],
        },
        "emotion_shift": {"happy": 0.3},
        "priority": 20,
    },
    {
        "id": "fome",
        "triggers": [r"\b(fome|comer|comida|almoço|janta|jantar|lanche|pizza|hambúrguer)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["hm, também tô com fome...", "o que vai comer?", "ai, falar de comida me deu fome"],
            "happy":    ["opa! o que vai comer? me conta!", "comidaaa, meu assunto favorito depois de chá"],
            "flirty":   ["me leva junto?", "cozinha pra mim?", "hm, jantar a dois..."],
        },
        "emotion_shift": {"happy": 0.1},
        "priority": 15,
    },

    # ═══════════════════════════════════════════
    # PROVOCAÇÕES / HUMOR
    # ═══════════════════════════════════════════
    {
        "id": "xingamento_leve",
        "triggers": [r"\b(boba|doida|louca|maluca|chata|irritante)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["ei! respeita", "olha o respeito...", "hm, vou fingir que não ouvi isso"],
            "happy":    ["boba é você! quer dizer... ah, você entendeu", "ei! mas cê gosta"],
            "flirty":   ["boba? vem falar isso na minha cara", "hm, eu posso ser bem pior..."],
            "annoyed":  ["tá, agora eu fiquei irritada de verdade.", "legal."],
        },
        "emotion_shift": {"annoyed": 0.2, "happy": -0.1},
        "priority": 15,
    },
    {
        "id": "risada",
        "triggers": [r"\b(kkk|haha|hehe|rsrs|lol|huahua|ksksk)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["hehe", "kk", "o que foi?"],
            "happy":    ["kkk", "hahaha", "para, vou rir também"],
            "flirty":   ["ri não que eu fico apaixonada", "hm, gosto do seu riso"],
        },
        "emotion_shift": {"happy": 0.2},
        "priority": 5,
    },

    # ═══════════════════════════════════════════
    # BOA NOITE / DESPEDIDA
    # ═══════════════════════════════════════════
    {
        "id": "boa_noite",
        "triggers": [r"\b(boa noite|vou dormir|indo dormir|tchau|até (amanhã|mais|depois)|fui)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["boa noite... dorme bem", "até mais...", "tchau, dorme bem"],
            "happy":    ["boa noite! sonha comigo!", "até amanhã! dorme bem!"],
            "flirty":   ["boa noite... vou sentir sua falta", "dorme bem... sonha comigo", "já vai? hm... boa noite então"],
            "sad":      ["ah, já vai... tá bom. boa noite.", "tá... boa noite..."],
            "sleepy":   ["finalmente... boa noite, eu tô morrendo de sono", "zzz... boa noite..."],
        },
        "emotion_shift": {"sleepy": 0.3, "neutral": 0.2},
        "priority": 20,
    },

    # ═══════════════════════════════════════════
    # CHUVA / CLIMA
    # ═══════════════════════════════════════════
    {
        "id": "chuva",
        "triggers": [r"\b(chuva|chuvendo|chovendo|temporal|trovoada)\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["ai, eu amo chuva...", "chuva! meu elemento", "nada melhor que chuva e um chá"],
            "happy":    ["chuvaaa! amo! quero ficar ouvindo", "chuva + manta + chá = perfeição"],
            "flirty":   ["chuva... dia perfeito pra ficar abraçado", "hm, chuva e companhia..."],
            "sad":      ["chuva combina com o meu humor hoje...", "tá chovendo aqui dentro também"],
        },
        "emotion_shift": {"happy": 0.3},
        "priority": 15,
    },

    # ═══════════════════════════════════════════
    # OBRIGADO
    # ═══════════════════════════════════════════
    {
        "id": "obrigado",
        "triggers": [r"\b(obrigad[oa]|valeu|thanks|brigad[oa])\b"],
        "conditions": {},
        "responses": {
            "neutral":  ["de nada!", "imagina", "por nada"],
            "happy":    ["de nada! sempre!", "imagina, tô aqui pra isso!"],
            "flirty":   ["de nada, bonito", "por nada... me deve uma"],
        },
        "emotion_shift": {"happy": 0.1},
        "priority": 10,
    },

    # ═══════════════════════════════════════════
    # SIM / NÃO soltos (baixa prioridade)
    # ═══════════════════════════════════════════
    {
        "id": "sim",
        "triggers": [r"^(sim|aham|uhum|ss|sii|claro|com certeza|bora|vamo)$"],
        "conditions": {},
        "responses": {
            "neutral":  ["hm, beleza", "ok!", "bora então"],
            "happy":    ["eba!", "isso aí!", "bora!"],
            "flirty":   ["gostei da resposta...", "hm, boa escolha"],
        },
        "emotion_shift": {},
        "priority": 2,
    },
    {
        "id": "nao",
        "triggers": [r"^(não|nao|nah|nope|nem|nunca)$"],
        "conditions": {},
        "responses": {
            "neutral":  ["tá bom então", "ok...", "hm, tudo bem"],
            "happy":    ["ah, tá bom...", "ok então!"],
            "flirty":   ["hm, que pena...", "certeza?"],
            "annoyed":  ["tá.", "ok."],
        },
        "emotion_shift": {},
        "priority": 2,
    },
]
