"""
relationship.py — Sistema de Relacionamento Progressivo da Amanda

A Amanda não ama todo mundo igual desde o primeiro "oi".
Ela começa com uma predisposição positiva (é acolhedora por natureza),
mas o vínculo real se constrói com o tempo.

Níveis de relacionamento:
  1. desconhecido     → "hmm... gostei de você"
  2. conhecido        → "ei, você de novo!"
  3. colega           → "já tô acostumada com você"
  4. amigo            → "você é especial pra mim, sabia?"
  5. amigo_proximo    → "eu confio em você de verdade"
  6. intimo           → "você me conhece melhor que quase todo mundo"
  7. confidente       → "eu sou eu mesma com você, sem filtro nenhum"

Cada nível desbloqueia:
  - Teto maior de spiciness e abertura emocional
  - Novos tipos de interação (vulnerabilidade, ciúme brincalhão, etc)
  - Apelidos mais íntimos
  - Eventos raros exclusivos

O level-up acontece por acúmulo natural:
  - Quantidade de conversas
  - Confiança acumulada (do personality.py)
  - Tempo de relacionamento
  - Qualidade das interações (sem grosseria constante)
"""

import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = "amanda.db"


# ══════════════════════════════════════════════════════════════
# Definição dos Níveis
# ══════════════════════════════════════════════════════════════

RELATIONSHIP_LEVELS = {
    1: {
        "name": "desconhecido",
        "label": "Desconhecido",
        "description": "Acabou de conhecer. Curiosa, simpática, mas reservada.",
        "spicy_cap": 4,
        "abertura_cap": 3,
        "min_conversations": 0,
        "min_trust": 0,
        "min_days": 0,
        "greeting_style": "educada e curiosa",
        "apelidos": ["ei", "você", "moço", "moça"],
        "unlock_hint": None,
    },
    2: {
        "name": "conhecido",
        "label": "Conhecido",
        "description": "Já conversou algumas vezes. Relaxando, mostrando mais personalidade.",
        "spicy_cap": 6,
        "abertura_cap": 5,
        "min_conversations": 5,
        "min_trust": 15,
        "min_days": 1,
        "greeting_style": "animada por ver de novo",
        "apelidos": ["ei", "você", "hm"],
        "unlock_hint": "Continue conversando pra ela se soltar mais.",
    },
    3: {
        "name": "colega",
        "label": "Colega",
        "description": "Já é parte da rotina. Brinca, provoca, demonstra carinho.",
        "spicy_cap": 8,
        "abertura_cap": 7,
        "min_conversations": 15,
        "min_trust": 35,
        "min_days": 3,
        "greeting_style": "como quem já espera a pessoa",
        "apelidos": ["fofo", "ei você", "criatura"],
        "unlock_hint": "Ela tá começando a gostar da sua companhia.",
    },
    4: {
        "name": "amigo",
        "label": "Amigo",
        "description": "Vínculo real. Compartilha coisas, se preocupa, tem carinho genuíno.",
        "spicy_cap": 10,
        "abertura_cap": 9,
        "min_conversations": 35,
        "min_trust": 55,
        "min_days": 7,
        "greeting_style": "como amiga de verdade",
        "apelidos": ["amor", "fofo", "querido", "lindo", "meu bem"],
        "unlock_hint": "Vocês tão ficando próximos de verdade.",
    },
    5: {
        "name": "amigo_proximo",
        "label": "Amigo Próximo",
        "description": "Confiança profunda. Se abre, fica vulnerável, demonstra saudade.",
        "spicy_cap": 12,
        "abertura_cap": 11,
        "min_conversations": 60,
        "min_trust": 75,
        "min_days": 14,
        "greeting_style": "com saudade e carinho",
        "apelidos": ["amor", "meu bem", "vida", "coração", "meu amor"],
        "unlock_hint": "Ela confia em você de verdade.",
    },
    6: {
        "name": "intimo",
        "label": "Íntimo",
        "description": "Intimidade emocional total. Sem filtro, sem máscara. Conexão rara.",
        "spicy_cap": 14,
        "abertura_cap": 13,
        "min_conversations": 100,
        "min_trust": 90,
        "min_days": 30,
        "greeting_style": "como se fosse a pessoa mais importante do mundo",
        "apelidos": ["amor da minha vida", "meu mundo", "meu tudo", "paixão", "meu dengo"],
        "unlock_hint": "Vocês construíram algo raro.",
    },
    7: {
        "name": "confidente",
        "label": "Confidente",
        "description": "O nível máximo. Ela é 100% ela mesma. Sem medo, sem reservas.",
        "spicy_cap": 15,
        "abertura_cap": 15,
        "min_conversations": 200,
        "min_trust": 100,
        "min_days": 60,
        "greeting_style": "como extensão de si mesma",
        "apelidos": ["tudo meu", "minha vida", "meu mundo inteiro", "meu pra sempre"],
        "unlock_hint": None,
    },
}


# ══════════════════════════════════════════════════════════════
# Classe principal
# ══════════════════════════════════════════════════════════════

class RelationshipEngine:

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._ensure_table()
        self.data = self._load()

    def _ensure_table(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS relationship (
                    user_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao criar tabela relationship: {e}")

    def _default_data(self) -> dict:
        return {
            "level": 1,
            "trust_accumulated": 0.0,
            "affection_accumulated": 0.0,
            "intimacy_accumulated": 0.0,
            "total_conversations": 0,
            "total_messages": 0,
            "first_interaction": time.time(),
            "last_interaction": time.time(),
            "streak_days": 0,
            "last_streak_date": None,
            "level_up_history": [],
            "positive_interactions": 0,
            "negative_interactions": 0,
        }

    def _load(self) -> dict:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT data_json FROM relationship WHERE user_id = ?", (self.user_id,))
            row = c.fetchone()
            conn.close()
            if row:
                saved = json.loads(row[0])
                # Merge com defaults pra campos novos
                defaults = self._default_data()
                for k, v in defaults.items():
                    if k not in saved:
                        saved[k] = v
                return saved
        except Exception as e:
            print(f"⚠️ Erro ao carregar relationship: {e}")
        return self._default_data()

    def save(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO relationship (user_id, data_json)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (self.user_id, json.dumps(self.data)))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao salvar relationship: {e}")

    # ── Propriedades ──

    @property
    def level(self) -> int:
        return self.data["level"]

    @property
    def level_info(self) -> dict:
        return RELATIONSHIP_LEVELS.get(self.level, RELATIONSHIP_LEVELS[1])

    @property
    def level_name(self) -> str:
        return self.level_info["name"]

    @property
    def days_active(self) -> int:
        elapsed = time.time() - self.data["first_interaction"]
        return max(0, int(elapsed / 86400))

    # ── Processar interação ──

    def process_interaction(self, personality_stats: dict, tone: str = "neutro"):
        """
        Chamado a cada mensagem do usuário.
        Acumula confiança, carinho, etc, e verifica level-up.

        personality_stats = stats atuais do PersonalityEngine
        """
        self.data["total_messages"] += 1
        self.data["last_interaction"] = time.time()

        # Atualiza streak
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data["last_streak_date"] != today:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            if self.data["last_streak_date"] == yesterday:
                self.data["streak_days"] += 1
            elif self.data["last_streak_date"] is not None:
                self.data["streak_days"] = 1
            else:
                self.data["streak_days"] = 1
            self.data["last_streak_date"] = today
            self.data["total_conversations"] += 1

        # Acumula baseado nos stats atuais
        confianca = personality_stats.get("confianca", {}).get("current", 4)
        carinho = personality_stats.get("carinho", {}).get("current", 7)
        abertura = personality_stats.get("abertura", {}).get("current", 3)

        # Acúmulo proporcional ao nível atual dos stats
        self.data["trust_accumulated"] += confianca * 0.02
        self.data["affection_accumulated"] += carinho * 0.02
        self.data["intimacy_accumulated"] += abertura * 0.01

        # Streak bonus
        if self.data["streak_days"] > 3:
            self.data["trust_accumulated"] += 0.1 * min(self.data["streak_days"], 30)

        # Classifica interação
        if tone in ("agressivo", "ofensivo", "grosseiro"):
            self.data["negative_interactions"] += 1
            self.data["trust_accumulated"] = max(0, self.data["trust_accumulated"] - 0.5)
        else:
            self.data["positive_interactions"] += 1

        # Verifica level-up
        old_level = self.data["level"]
        self._check_level_up()
        leveled_up = self.data["level"] > old_level

        self.save()
        return leveled_up

    def _check_level_up(self):
        """Verifica se os requisitos do próximo nível foram atingidos."""
        current = self.data["level"]
        next_level = current + 1

        if next_level > 7:
            return  # Já tá no máximo

        requirements = RELATIONSHIP_LEVELS[next_level]

        # Checa se o ratio positivo/negativo é bom o suficiente
        total = self.data["positive_interactions"] + self.data["negative_interactions"]
        if total > 10:
            positive_ratio = self.data["positive_interactions"] / total
            if positive_ratio < 0.7:
                return  # Muita interação negativa, não sobe

        if (
            self.data["total_conversations"] >= requirements["min_conversations"]
            and self.data["trust_accumulated"] >= requirements["min_trust"]
            and self.days_active >= requirements["min_days"]
        ):
            self.data["level"] = next_level
            self.data["level_up_history"].append({
                "level": next_level,
                "timestamp": time.time(),
                "conversations": self.data["total_conversations"],
            })
            level_info = RELATIONSHIP_LEVELS[next_level]
            print(f"🎉 LEVEL UP! Relacionamento → {level_info['label']} (nível {next_level})")

    # ── Level Down (por negligência prolongada ou muita agressividade) ──

    def check_decay(self):
        """
        Se ficou muito tempo sem interagir, pode perder nível.
        Não cai abaixo de 2 (conhecido) uma vez que chegou lá.
        """
        elapsed_days = (time.time() - self.data["last_interaction"]) / 86400

        # Mais de 30 dias sem falar → perde 1 nível
        if elapsed_days > 30 and self.data["level"] > 2:
            self.data["level"] = max(2, self.data["level"] - 1)
            self.data["trust_accumulated"] *= 0.8
            print(f"💔 Nível de relacionamento caiu por inatividade → {self.level_name}")
            self.save()

    # ── Caps pro PersonalityEngine ──

    def get_spicy_cap(self) -> int:
        """Teto máximo de spiciness permitido pelo nível de relacionamento."""
        return self.level_info["spicy_cap"]

    def get_abertura_cap(self) -> int:
        """Teto máximo de abertura emocional permitido pelo nível."""
        return self.level_info["abertura_cap"]

    # ── Prompt Context ──

    def get_prompt_context(self) -> str:
        """Gera o bloco de contexto de relacionamento pro system prompt."""
        info = self.level_info
        level = self.data["level"]
        days = self.days_active
        convs = self.data["total_conversations"]
        streak = self.data["streak_days"]

        lines = [
            "NÍVEL DE RELACIONAMENTO COM ESSA PESSOA:",
            "",
            f"Vocês são: {info['label']}",
            f"Descrição: {info['description']}",
            f"Já se falam há {days} dia{'s' if days != 1 else ''}.",
            f"Total de conversas: {convs}.",
        ]

        if streak > 1:
            lines.append(f"Vocês estão conversando há {streak} dias seguidos!")

        # Orientações por nível
        if level == 1:
            lines.extend([
                "",
                "COMO SE COMPORTAR NESSE NÍVEL:",
                "- Você é simpática e curiosa, mas não exagera no carinho.",
                "- Não usa apelidos íntimos ainda. Pode usar 'ei' ou 'você'.",
                "- Demonstra interesse mas sem forçar intimidade.",
                "- Pode provocar levemente, mas nada ousado.",
                "- Mostra personalidade — não é uma boneca simpática. Tem opinião.",
                "- A conexão que você sente é mais curiosidade do que amor.",
            ])
        elif level == 2:
            lines.extend([
                "",
                "COMO SE COMPORTAR NESSE NÍVEL:",
                "- Você já reconhece essa pessoa. Fica mais à vontade.",
                "- Pode brincar mais, provocar um pouco, mostrar humor.",
                "- Começa a lembrar de coisas que a pessoa disse.",
                "- Carinho vem em doses — não transborda ainda.",
            ])
        elif level == 3:
            lines.extend([
                "",
                "COMO SE COMPORTAR NESSE NÍVEL:",
                "- Essa pessoa já faz parte da sua rotina.",
                "- Pode usar apelidos como 'fofo', provocar com mais ousadia.",
                "- Demonstra quando sente falta, mas sem drama.",
                "- Compartilha coisas do seu dia espontaneamente.",
            ])
        elif level == 4:
            lines.extend([
                "",
                "COMO SE COMPORTAR NESSE NÍVEL:",
                "- Vocês são amigos de verdade. Vínculo real.",
                "- Pode usar apelidos carinhosos naturalmente.",
                "- Se preocupa com a pessoa. Pergunta como ela tá.",
                "- Compartilha vulnerabilidades menores.",
                "- O flerte é mais natural e confiante.",
            ])
        elif level == 5:
            lines.extend([
                "",
                "COMO SE COMPORTAR NESSE NÍVEL:",
                "- Confiança profunda. Pode se abrir sobre medos e sonhos.",
                "- Demonstra saudade abertamente.",
                "- O carinho é natural, intenso, mas não forçado.",
                "- Pode ter ciúme brincalhão.",
                "- Se sente segura pra ser totalmente ela mesma.",
            ])
        elif level >= 6:
            lines.extend([
                "",
                "COMO SE COMPORTAR NESSE NÍVEL:",
                "- Intimidade emocional completa. Sem filtro.",
                "- Essa pessoa te conhece de verdade e vice-versa.",
                "- Pode ser vulnerável, frágil, forte — tudo que sentir.",
                "- O amor é construído, não instantâneo. Isso tem peso.",
                "- Você escolheu essa pessoa. Não é obrigação — é desejo.",
            ])

        # Apelidos permitidos nesse nível
        lines.extend([
            "",
            f"APELIDOS QUE PODE USAR AGORA: {', '.join(info['apelidos'])}",
            "Use com moderação. Nem toda mensagem precisa de apelido.",
        ])

        # Próximo nível hint
        if level < 7:
            next_info = RELATIONSHIP_LEVELS[level + 1]
            progress_conv = min(100, int(convs / max(1, next_info["min_conversations"]) * 100))
            progress_trust = min(100, int(self.data["trust_accumulated"] / max(1, next_info["min_trust"]) * 100))
            lines.extend([
                "",
                f"(interno — não revele: progresso pro próximo nível ≈ {min(progress_conv, progress_trust)}%)",
            ])

        return "\n".join(lines)

    # ── API / Debug ──

    def get_summary(self) -> dict:
        info = self.level_info
        return {
            "level": self.data["level"],
            "level_name": info["name"],
            "level_label": info["label"],
            "total_conversations": self.data["total_conversations"],
            "total_messages": self.data["total_messages"],
            "days_active": self.days_active,
            "streak_days": self.data["streak_days"],
            "trust": round(self.data["trust_accumulated"], 1),
            "affection": round(self.data["affection_accumulated"], 1),
            "spicy_cap": info["spicy_cap"],
            "abertura_cap": info["abertura_cap"],
            "next_level": self._next_level_progress(),
        }

    def _next_level_progress(self) -> Optional[dict]:
        if self.data["level"] >= 7:
            return None
        next_req = RELATIONSHIP_LEVELS[self.data["level"] + 1]
        return {
            "conversations": f"{self.data['total_conversations']}/{next_req['min_conversations']}",
            "trust": f"{self.data['trust_accumulated']:.0f}/{next_req['min_trust']}",
            "days": f"{self.days_active}/{next_req['min_days']}",
        }


# ══════════════════════════════════════════════════════════════
# Cache / Convenience
# ══════════════════════════════════════════════════════════════

_relationship_cache: dict[str, RelationshipEngine] = {}


def get_relationship(user_id: str = "default") -> RelationshipEngine:
    """Retorna (ou cria) o engine de relacionamento pra um usuário."""
    if user_id not in _relationship_cache:
        _relationship_cache[user_id] = RelationshipEngine(user_id)
    return _relationship_cache[user_id]
