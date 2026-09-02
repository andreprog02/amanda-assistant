"""
router.py — Decide se responde local ou manda pra nuvem.
"""

import random
from local_engine import LocalEngine


THINKING_PHRASES = {
    "neutral":  ["hm, deixa eu pensar...", "peraí...", "hm..."],
    "happy":    ["opa, espera...", "hm, boa pergunta!", "deixa eu ver..."],
    "flirty":   ["hm... boa pergunta...", "espera, bonito...", "peraí..."],
    "sleepy":   ["hm... peraí que tô pensando...", "ai, espera..."],
    "sad":      ["hm...", "deixa eu pensar..."],
    "annoyed":  ["tá, peraí.", "espera."],
}


class AmandaRouter:

    def __init__(self):
        self.engine = LocalEngine()
        self.local_count = 0
        self.cloud_count = 0

    def try_local(self, user_input: str) -> dict | None:
        """
        Tenta responder localmente.
        Retorna {"text", "emotion", "source"} ou None (= manda pra nuvem).
        """
        result = self.engine.try_respond(user_input)
        if result:
            self.local_count += 1
            return {
                "text": result["text"],
                "emotion": result["emotion"],
                "source": "local",
            }
        return None

    def get_thinking_phrase(self) -> str:
        mood = self.engine.mood.current
        pool = THINKING_PHRASES.get(mood, THINKING_PHRASES["neutral"])
        return random.choice(pool)

    def notify_cloud_response(self, emotion: str):
        """Sincroniza humor local com a emoção da nuvem."""
        self.cloud_count += 1
        self.engine.sync_cloud_emotion(emotion)

    def stats(self) -> dict:
        total = self.local_count + self.cloud_count
        return {
            "local": self.local_count,
            "cloud": self.cloud_count,
            "total": total,
            "local_pct": round(self.local_count / total * 100) if total else 0,
            "mood": self.engine.mood.summary(),
        }