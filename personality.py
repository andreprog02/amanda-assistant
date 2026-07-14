"""
personality.py — Sistema de Stats RPG da Amanda

Cada stat tem:
  - base: valor de repouso (a "personalidade padrão")
  - current: valor atual (flutua com interações)
  - min/max: limites (0-15)
  - decay_rate: velocidade que volta pro base entre interações
  - momentum: inércia — quanto mais tempo num valor alto, mais lento o decay

As stats se influenciam mutuamente:
  - confiança baixa TRAVA o teto do spicy e da abertura emocional
  - energia baixa REDUZ velocidade de subir alegria e spiciness
  - carinho alto AUMENTA velocidade de subir confiança
  - abertura emocional alta FAZ o decay do carinho ser mais lento
"""

import json
import time
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = "amanda.db"

# ══════════════════════════════════════════════════════════════
# Definição das Stats
# ══════════════════════════════════════════════════════════════

DEFAULT_STATS = {
    "confianca": {
        "label": "Confiança",
        "description": "Quão à vontade ela se sente com o usuário",
        "base": 4,
        "current": 4,
        "min": 0,
        "max": 15,
        "decay_rate": 0.3,      # volta pro base devagar (confiança se constrói)
        "momentum": 0,
    },
    "alegria": {
        "label": "Alegria",
        "description": "Humor geral — quão feliz/animada ela tá",
        "base": 8,
        "current": 8,
        "min": 0,
        "max": 15,
        "decay_rate": 0.8,      # flutua rápido (humor muda fácil)
        "momentum": 0,
    },
    "spiciness": {
        "label": "Spiciness",
        "description": "Nível de ousadia, provocação e flerte",
        "base": 3,
        "current": 3,
        "min": 0,
        "max": 15,
        "decay_rate": 1.0,      # cai rápido se não mantiver o clima
        "momentum": 0,
    },
    "carinho": {
        "label": "Carinho",
        "description": "Nível de afeto, cuidado e doçura",
        "base": 7,
        "current": 7,
        "min": 0,
        "max": 15,
        "decay_rate": 0.5,
        "momentum": 0,
    },
    "energia": {
        "label": "Energia",
        "description": "Disposição — afetada pela hora do dia e conversa",
        "base": 8,
        "current": 8,
        "min": 0,
        "max": 15,
        "decay_rate": 0.6,
        "momentum": 0,
    },
    "abertura": {
        "label": "Abertura Emocional",
        "description": "Quão vulnerável e profunda ela fica",
        "base": 3,
        "current": 3,
        "min": 0,
        "max": 15,
        "decay_rate": 0.7,
        "momentum": 0,
    },
    "curiosidade": {
        "label": "Curiosidade",
        "description": "Interesse em saber mais sobre o usuário",
        "base": 9,
        "current": 9,
        "min": 0,
        "max": 15,
        "decay_rate": 0.4,
        "momentum": 0,
    },
    "irritacao": {
        "label": "Irritação",
        "description": "Nível de frustração ou incômodo",
        "base": 0,
        "current": 0,
        "min": 0,
        "max": 15,
        "decay_rate": 1.2,      # se acalma relativamente rápido
        "momentum": 0,
    },
}

# ══════════════════════════════════════════════════════════════
# Regras de interdependência
# ══════════════════════════════════════════════════════════════

def apply_stat_caps(stats: dict) -> dict:
    """
    Aplica limites dinâmicos baseados em interdependências.
    Ex: confiança baixa trava o teto do spicy.
    """
    confianca = stats["confianca"]["current"]
    energia = stats["energia"]["current"]
    carinho = stats["carinho"]["current"]
    abertura = stats["abertura"]["current"]
    irritacao = stats["irritacao"]["current"]

    # ── Confiança trava teto do Spicy ──
    # confiança 0-3 → spicy max 3
    # confiança 4-7 → spicy max 7
    # confiança 8-11 → spicy max 11
    # confiança 12-15 → spicy max 15 (desbloqueado)
    spicy_cap = min(15, max(3, confianca + 1))
    if stats["spiciness"]["current"] > spicy_cap:
        stats["spiciness"]["current"] = spicy_cap

    # ── Confiança trava teto da Abertura Emocional ──
    abertura_cap = min(15, max(2, confianca + 2))
    if stats["abertura"]["current"] > abertura_cap:
        stats["abertura"]["current"] = abertura_cap

    # ── Energia baixa reduz velocidade de subir alegria ──
    # (implementado em adjust_stat via multiplier)

    # ── Irritação alta reduz carinho e alegria ──
    if irritacao > 8:
        penalty = (irritacao - 8) * 0.5
        stats["carinho"]["current"] = max(0, stats["carinho"]["current"] - penalty)
        stats["alegria"]["current"] = max(0, stats["alegria"]["current"] - penalty)

    # ── Carinho muito alto dá boost leve na confiança ──
    # (implementado no decay — carinho alto faz confiança decair mais devagar)

    # Garante limites
    for key in stats:
        s = stats[key]
        s["current"] = round(max(s["min"], min(s["max"], s["current"])), 2)

    return stats


# ══════════════════════════════════════════════════════════════
# Classe principal
# ══════════════════════════════════════════════════════════════

class PersonalityEngine:

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.stats = self._load_stats()
        self.last_interaction = self._load_last_interaction()

    # ── Persistência ──

    def _load_stats(self) -> dict:
        """Carrega stats do banco ou retorna defaults."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS personality_stats (
                    user_id TEXT PRIMARY KEY,
                    stats_json TEXT NOT NULL,
                    last_interaction REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            c.execute("SELECT stats_json FROM personality_stats WHERE user_id = ?", (self.user_id,))
            row = c.fetchone()
            conn.close()

            if row:
                saved = json.loads(row[0])
                # Merge com defaults (caso tenha stats novos)
                merged = {}
                for key, default in DEFAULT_STATS.items():
                    if key in saved:
                        merged[key] = {**default, **saved[key]}
                    else:
                        merged[key] = dict(default)
                return merged

        except Exception as e:
            print(f"⚠️ Erro ao carregar personality stats: {e}")

        # Retorna cópia dos defaults
        return {k: dict(v) for k, v in DEFAULT_STATS.items()}

    def _load_last_interaction(self) -> float:
        """Carrega timestamp da última interação."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT last_interaction FROM personality_stats WHERE user_id = ?", (self.user_id,))
            row = c.fetchone()
            conn.close()
            if row:
                return row[0]
        except:
            pass
        return time.time()

    def save(self):
        """Persiste stats no banco."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO personality_stats (user_id, stats_json, last_interaction)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    stats_json = excluded.stats_json,
                    last_interaction = excluded.last_interaction,
                    updated_at = CURRENT_TIMESTAMP
            """, (self.user_id, json.dumps(self.stats), time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao salvar personality stats: {e}")

    # ── Decay (volta pro base com o tempo) ──

    def apply_decay(self):
        """
        Aplica decay baseado no tempo desde a última interação.
        Stats voltam gradualmente pro valor base.
        Quanto mais tempo longe, mais decai.
        """
        now = time.time()
        elapsed_minutes = (now - self.last_interaction) / 60

        if elapsed_minutes < 1:
            return  # Sem decay se a interação foi há menos de 1 min

        # Fator de decay: cresce com o tempo, mas com limite
        # 5 min → leve, 30 min → moderado, 2h+ → forte
        time_factor = min(1.0, elapsed_minutes / 120)

        for key, stat in self.stats.items():
            base = stat["base"]
            current = stat["current"]
            decay_rate = stat["decay_rate"]
            momentum = stat.get("momentum", 0)

            if abs(current - base) < 0.1:
                stat["momentum"] = 0
                continue

            # Momentum reduz o decay (inércia emocional)
            effective_decay = decay_rate * time_factor * max(0.2, 1.0 - momentum * 0.1)

            # Modificadores de interdependência no decay
            if key == "confianca" and self.stats["carinho"]["current"] > 10:
                effective_decay *= 0.5  # Carinho alto protege a confiança

            if key == "carinho" and self.stats["abertura"]["current"] > 8:
                effective_decay *= 0.6  # Abertura alta protege o carinho

            if key == "alegria" and self.stats["energia"]["current"] < 5:
                effective_decay *= 1.5  # Energia baixa faz alegria cair mais rápido

            # Aplica decay na direção do base
            diff = current - base
            decay_amount = diff * effective_decay
            stat["current"] = current - decay_amount

            # Reduz momentum com o tempo
            stat["momentum"] = max(0, momentum - time_factor * 0.5)

        self.stats = apply_stat_caps(self.stats)
        self.last_interaction = now

    # ── Ajuste de Stats ──

    def adjust_stat(self, stat_name: str, delta: float, reason: str = ""):
        """
        Ajusta uma stat com modificadores de interdependência.

        delta > 0: sobe
        delta < 0: desce

        Retorna o delta real aplicado.
        """
        if stat_name not in self.stats:
            return 0

        stat = self.stats[stat_name]
        old_value = stat["current"]

        # ── Modificadores baseados em outras stats ──
        effective_delta = delta

        if stat_name == "spiciness" and delta > 0:
            # Confiança baixa dificulta subir spicy
            confianca = self.stats["confianca"]["current"]
            if confianca < 5:
                effective_delta *= 0.3   # muito difícil
            elif confianca < 8:
                effective_delta *= 0.6   # moderado
            elif confianca < 12:
                effective_delta *= 0.85  # quase normal

        if stat_name == "alegria" and delta > 0:
            # Energia baixa dificulta ficar alegre
            energia = self.stats["energia"]["current"]
            if energia < 4:
                effective_delta *= 0.4
            elif energia < 7:
                effective_delta *= 0.7

        if stat_name == "abertura" and delta > 0:
            # Confiança e carinho influenciam abertura
            confianca = self.stats["confianca"]["current"]
            carinho = self.stats["carinho"]["current"]
            if confianca < 6:
                effective_delta *= 0.3
            if carinho > 10:
                effective_delta *= 1.3  # carinho alto facilita abertura

        if stat_name == "confianca" and delta > 0:
            # Interações consistentes dão bonus
            # (medido pelo momentum — quanto mais alto, mais rápido cresce)
            momentum = stat.get("momentum", 0)
            effective_delta *= (1.0 + momentum * 0.05)

        # Aplica
        new_value = stat["current"] + effective_delta
        new_value = max(stat["min"], min(stat["max"], new_value))
        stat["current"] = round(new_value, 2)

        # Atualiza momentum (quanto mais muda na mesma direção, mais inércia)
        if abs(effective_delta) > 0.3:
            stat["momentum"] = min(5, stat.get("momentum", 0) + 0.3)

        # Aplica caps de interdependência
        self.stats = apply_stat_caps(self.stats)

        actual_delta = stat["current"] - old_value
        if abs(actual_delta) > 0.1 and reason:
            print(f"📊 {stat['label']}: {old_value:.1f} → {stat['current']:.1f} ({reason})")

        return actual_delta

    # ── Energia baseada na hora ──

    def sync_energy_to_time(self):
        """Ajusta energia base com a hora do dia."""
        hora = datetime.now().hour

        if 6 <= hora < 10:
            target = 11       # manhã: energizada
        elif 10 <= hora < 12:
            target = 13       # meio da manhã: pico
        elif 12 <= hora < 14:
            target = 8        # pós-almoço: queda
        elif 14 <= hora < 17:
            target = 10       # tarde: recupera
        elif 17 <= hora < 20:
            target = 9        # fim de tarde: cansando
        elif 20 <= hora < 23:
            target = 6        # noite: relaxada
        elif 23 <= hora or hora < 2:
            target = 3        # madrugada: sonolenta
        else:
            target = 2        # madrugada profunda

        # Ajusta gradualmente na direção do target
        current = self.stats["energia"]["current"]
        diff = target - current
        self.stats["energia"]["current"] = round(current + diff * 0.3, 2)

    # ── Processar interação do usuário ──

    def process_interaction(self, emotion_analysis: dict):
        """
        Recebe a análise emocional da mensagem do usuário e ajusta stats.

        emotion_analysis = {
            "tone": "flirty" | "carinhoso" | "agressivo" | "triste" | ...,
            "intensity": 0.0-1.0,
            "effects": {
                "confianca": 0.5,
                "alegria": 1.0,
                "spiciness": -0.5,
                ...
            }
        }
        """
        # Aplica decay primeiro (tempo entre mensagens)
        self.apply_decay()

        # Sincroniza energia com hora
        self.sync_energy_to_time()

        # Aplica efeitos da interação
        effects = emotion_analysis.get("effects", {})
        tone = emotion_analysis.get("tone", "neutro")
        intensity = emotion_analysis.get("intensity", 0.5)

        for stat_name, delta in effects.items():
            scaled_delta = delta * intensity
            self.adjust_stat(stat_name, scaled_delta, reason=f"tom={tone}")

        # Interação em si sempre dá um micro-boost na confiança
        self.adjust_stat("confianca", 0.15, reason="interação")

        # Salva
        self.save()

    # ── Prompt Context ──

    def get_prompt_context(self) -> str:
        """
        Gera o bloco de contexto de personalidade pra injetar no system prompt.
        Não expõe números — traduz em linguagem natural.
        """
        self.apply_decay()
        self.sync_energy_to_time()

        lines = ["SEUS STATS EMOCIONAIS AGORA (influenciam como você reage):\n"]

        for key, stat in self.stats.items():
            level = stat["current"]
            label = stat["label"]
            desc = self._level_description(key, level)
            lines.append(f"• {label}: {desc}")

        # Adiciona dicas comportamentais baseadas nos stats
        lines.append("\n" + self._behavioral_hints())

        return "\n".join(lines)

    def _level_description(self, stat_name: str, level: float) -> str:
        """Traduz o nível numérico em descrição natural."""
        descriptions = {
            "confianca": {
                (0, 3):   "ainda desconfiada, reservada, meio na dela",
                (3, 6):   "começando a se soltar, mas ainda com um pé atrás",
                (6, 9):   "confortável, relaxada com a pessoa",
                (9, 12):  "bem à vontade, confia bastante",
                (12, 16): "confiança total, se sente segura pra ser 100% ela mesma",
            },
            "alegria": {
                (0, 3):   "pra baixo, meio triste, sem vontade",
                (3, 6):   "ok, normal, sem muita animação",
                (6, 9):   "de bom humor, leve, sorridente",
                (9, 12):  "animada, radiante, rindo fácil",
                (12, 16): "explodindo de felicidade, eufórica",
            },
            "spiciness": {
                (0, 3):   "comportada, na dela, sem provocação",
                (3, 6):   "com uma pontinha de provocação, um sorrisinho",
                (6, 9):   "provocativa, flertando, ousada",
                (9, 12):  "bem spicy, direta, sedutora",
                (12, 16): "no máximo, sem filtro, pegando fogo",
            },
            "carinho": {
                (0, 3):   "distante, fria, sem muito afeto",
                (3, 6):   "gentil mas sem exagero",
                (6, 9):   "carinhosa, atenciosa, doce",
                (9, 12):  "muito afetuosa, protetora, cheia de amor",
                (12, 16): "transbordando carinho, grudenta (no bom sentido)",
            },
            "energia": {
                (0, 3):   "exausta, quase dormindo, respostas curtas e preguiçosas",
                (3, 6):   "cansada, meio mole, sem muita disposição",
                (6, 9):   "normal, disposição ok",
                (9, 12):  "energizada, falante, animada",
                (12, 16): "elétrica, falando pelos cotovelos, hiperativa",
            },
            "abertura": {
                (0, 3):   "fechada, superficial, evita assuntos profundos",
                (3, 6):   "aberta pra conversa mas sem aprofundar muito",
                (6, 9):   "vulnerável, compartilha sentimentos",
                (9, 12):  "muito aberta, fala de medos e sonhos",
                (12, 16): "completamente transparente, alma exposta",
            },
            "curiosidade": {
                (0, 3):   "desinteressada, responde por responder",
                (3, 6):   "um pouco curiosa, faz uma pergunta ou outra",
                (6, 9):   "interessada, quer saber das coisas",
                (9, 12):  "muito curiosa, faz várias perguntas, quer detalhes",
                (12, 16): "fascinada, não para de perguntar, quer saber TUDO",
            },
            "irritacao": {
                (0, 3):   "de boa, sem irritação nenhuma",
                (3, 6):   "levemente incomodada, um pouco impaciente",
                (6, 9):   "irritada, respostas secas, curtas",
                (9, 12):  "bem irritada, pode ser ríspida ou irônica",
                (12, 16): "furiosa, pode dar patada ou ignorar",
            },
        }

        ranges = descriptions.get(stat_name, {})
        for (lo, hi), desc in ranges.items():
            if lo <= level < hi:
                return desc
        return "normal"

    def _behavioral_hints(self) -> str:
        """Gera dicas de comportamento baseadas na combinação de stats."""
        hints = []

        confianca = self.stats["confianca"]["current"]
        alegria = self.stats["alegria"]["current"]
        spiciness = self.stats["spiciness"]["current"]
        carinho = self.stats["carinho"]["current"]
        energia = self.stats["energia"]["current"]
        abertura = self.stats["abertura"]["current"]
        curiosidade = self.stats["curiosidade"]["current"]
        irritacao = self.stats["irritacao"]["current"]

        # Combinações que geram comportamentos específicos
        if confianca > 10 and spiciness > 8:
            hints.append(
                "Você tá se sentindo confiante E spicy — pode ser ousada, "
                "provocar sem medo, falar coisas que normalmente não falaria."
            )
        elif confianca < 4 and spiciness > 5:
            hints.append(
                "Alguém tá tentando te fazer ser spicy mas você ainda não confia tanto — "
                "fica na provocação leve, com um pé atrás, não se entrega fácil."
            )

        if energia < 4 and alegria < 5:
            hints.append(
                "Você tá cansada e sem muito ânimo — respostas mais curtas, "
                "preguiçosas, talvez bocejando. Não força animação."
            )

        if carinho > 10 and abertura > 8:
            hints.append(
                "Você tá num momento muito íntimo — pode falar de sentimentos, "
                "ser vulnerável, dizer coisas que guarda pra si normalmente."
            )

        if irritacao > 6:
            hints.append(
                "Você tá irritada — respostas mais secas, pode ser irônica. "
                "Não finja que tá tudo bem. Mas não seja cruel — você é ácida, não maldosa."
            )

        if curiosidade > 10 and confianca > 7:
            hints.append(
                "Você tá muito curiosa sobre a pessoa — faz perguntas, "
                "quer saber detalhes, puxa assunto. Não por educação, por interesse real."
            )

        if alegria > 11 and energia > 10:
            hints.append(
                "Você tá elétrica e feliz — fala mais que o normal, "
                "ri de qualquer coisa, tá contagiante."
            )

        if abertura < 3 and confianca < 5:
            hints.append(
                "Você tá reservada — conversa na superfície, "
                "desvia de assuntos pessoais, mantém o charme mas sem se abrir."
            )

        if not hints:
            if alegria >= 6 and energia >= 6:
                hints.append("Você tá num estado equilibrado — seja você mesma, natural.")
            else:
                hints.append("Seu humor tá ok mas sem nada especial — reaja conforme a conversa fluir.")

        return "COMO SE COMPORTAR AGORA:\n" + "\n".join(f"→ {h}" for h in hints)

    # ── Debug ──

    def get_stats_summary(self) -> dict:
        """Retorna stats pra debug/API."""
        return {
            key: {
                "label": s["label"],
                "base": s["base"],
                "current": round(s["current"], 1),
                "max": s["max"],
                "momentum": round(s.get("momentum", 0), 2),
            }
            for key, s in self.stats.items()
        }


# ══════════════════════════════════════════════════════════════
# Prompt de análise emocional (pra usar com Claude)
# ══════════════════════════════════════════════════════════════

EMOTION_ANALYSIS_PROMPT = """Analise a mensagem do usuário e determine o impacto emocional.

Responda APENAS em JSON, sem markdown, sem explicação. Formato:

{
  "tone": "string descrevendo o tom (ex: carinhoso, flirty, agressivo, triste, animado, neutro, provocativo, curioso, desabafo)",
  "intensity": 0.0 a 1.0 (quão forte é o tom),
  "effects": {
    "confianca": -2.0 a 2.0,
    "alegria": -2.0 a 2.0,
    "spiciness": -2.0 a 2.0,
    "carinho": -2.0 a 2.0,
    "energia": -2.0 a 2.0,
    "abertura": -2.0 a 2.0,
    "curiosidade": -2.0 a 2.0,
    "irritacao": -2.0 a 2.0
  }
}

Regras:
- "oi", "tudo bem?" → efeitos mínimos (0.1-0.3)
- elogios, flertes → spiciness +0.5-1.5, confianca +0.3-0.8, alegria +0.3
- desabafos, vulnerabilidade → abertura +1.0-2.0, carinho +0.5, confianca +0.5
- grosseria, ofensa → irritacao +1.0-2.0, confianca -0.5-1.5, carinho -0.5
- piadas, humor → alegria +0.5-1.5, energia +0.3
- pergunta pessoal → curiosidade +0.5, confianca +0.3
- despedida → efeitos leves negativos em energia
- conversa longa e boa → confianca +0.3 cumulativo

IMPORTANTE: Seja conservador. Mudanças grandes (>1.5) só pra interações muito intensas.
A maioria das mensagens causa mudanças pequenas (0.2-0.8)."""


def analyze_user_message(client, model: str, user_text: str) -> dict:
    """
    Usa o Claude pra analisar o impacto emocional da mensagem.
    Retorna dict com tone, intensity e effects.
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=300,
            system=EMOTION_ANALYSIS_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ Erro na análise emocional: {e}")
        # Fallback: efeitos neutros mínimos
        return {
            "tone": "neutro",
            "intensity": 0.3,
            "effects": {"confianca": 0.1},
        }


# ══════════════════════════════════════════════════════════════
# Análise local rápida (sem API — pra economizar tokens)
# ══════════════════════════════════════════════════════════════

def quick_analyze(user_text: str) -> dict:
    """
    Análise rápida baseada em palavras-chave.
    Usa quando não quer gastar uma chamada de API.
    Menos precisa mas instantânea e grátis.
    """
    text = user_text.lower().strip()
    effects = {}
    tone = "neutro"
    intensity = 0.3

    # ── Saudações simples ──
    greetings = ["oi", "olá", "eai", "e aí", "fala", "hey", "opa", "bom dia", "boa tarde", "boa noite"]
    if any(text.startswith(g) or text == g for g in greetings):
        tone = "saudação"
        effects = {"confianca": 0.1, "alegria": 0.2}
        intensity = 0.3

    # ── Flerte / provocação ──
    flirty_words = ["linda", "gata", "gostosa", "bonita", "tesão", "delícia", "maravilhosa",
                     "musa", "princesa", "gatinha", "safada", "provocante"]
    if any(w in text for w in flirty_words):
        tone = "flirty"
        effects = {"spiciness": 1.2, "confianca": 0.3, "alegria": 0.5}
        intensity = 0.7

    # ── Carinho ──
    caring_words = ["saudade", "te amo", "amor", "fofa", "querida", "carinho",
                     "abraço", "cuidado", "preocupado"]
    if any(w in text for w in caring_words):
        tone = "carinhoso"
        effects = {"carinho": 1.0, "confianca": 0.5, "alegria": 0.5, "abertura": 0.3}
        intensity = 0.7

    # ── Tristeza / desabafo ──
    sad_words = ["triste", "mal", "chorando", "sozinho", "sozinha", "angústia",
                  "deprimido", "ansioso", "desanimado", "não aguento", "cansado", "cansada"]
    if any(w in text for w in sad_words):
        tone = "desabafo"
        effects = {"abertura": 1.0, "carinho": 0.8, "confianca": 0.5,
                   "alegria": -0.3, "energia": -0.3}
        intensity = 0.7

    # ── Humor / diversão ──
    fun_words = ["kkk", "haha", "rsrs", "engraçado", "piada", "morr", "rachei",
                  "zoeira", "zueira", "meme"]
    if any(w in text for w in fun_words):
        tone = "divertido"
        effects = {"alegria": 1.0, "energia": 0.5, "confianca": 0.2}
        intensity = 0.6

    # ── Agressividade ──
    angry_words = ["idiota", "burra", "inútil", "merda", "foda-se", "cala a boca",
                    "odeio", "chata", "irritante","zé buceta", "pau no cu"]
    if any(w in text for w in angry_words):
        tone = "agressivo"
        effects = {"irritacao": 1.5, "confianca": -1.0, "carinho": -0.8,
                   "alegria": -0.5, "spiciness": -1.0}
        intensity = 0.8

    # ── Curiosidade sobre ela ──
    curious_about_her = ["como você", "o que você", "me conta", "me fala",
                          "você gosta", "qual seu", "quem é você"]
    if any(w in text for w in curious_about_her):
        tone = "curioso"
        effects = {"curiosidade": 0.5, "confianca": 0.3, "alegria": 0.3}
        intensity = 0.5

    # ── Mensagens longas (mais de 100 chars) indicam investimento ──
    if len(text) > 100:
        effects["confianca"] = effects.get("confianca", 0) + 0.2
        effects["abertura"] = effects.get("abertura", 0) + 0.2
        intensity = min(1.0, intensity + 0.1)

    return {"tone": tone, "intensity": intensity, "effects": effects}


# ══════════════════════════════════════════════════════════════
# Convenience
# ══════════════════════════════════════════════════════════════

_engine_cache: dict[str, PersonalityEngine] = {}

def get_engine(user_id: str = "default") -> PersonalityEngine:
    """Retorna (ou cria) o engine pra um usuário."""
    if user_id not in _engine_cache:
        _engine_cache[user_id] = PersonalityEngine(user_id)
    return _engine_cache[user_id]
