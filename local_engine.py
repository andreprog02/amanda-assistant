"""
local_engine.py — Motor de respostas local da Amanda
Roda sem nenhuma dependência de IA.
"""

import re
import random
import time
from datetime import datetime
from local_rules import RULES


class EmotionalState:
    EMOTIONS = ["neutral", "happy", "sad", "flirty", "annoyed", "sleepy"]
    DECAY_RATE = 0.005

    def __init__(self):
        self.values = {e: 0.0 for e in self.EMOTIONS}
        self.values["neutral"] = 0.5
        self.last_update = time.time()

    @property
    def current(self) -> str:
        self._apply_decay()
        return max(self.values, key=self.values.get)

    @property
    def intensity(self) -> float:
        return self.values[self.current]

    def shift(self, changes: dict):
        self._apply_decay()
        for emotion, delta in changes.items():
            if emotion in self.values:
                self.values[emotion] = max(0.0, min(1.0, self.values[emotion] + delta))

    def force(self, emotion: str, value: float = 0.7):
        if emotion in self.values:
            for e in self.values:
                self.values[e] *= 0.3
            self.values[emotion] = value

    def _apply_decay(self):
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        decay = self.DECAY_RATE * elapsed
        for e in self.EMOTIONS:
            if e == "neutral":
                self.values[e] = min(1.0, self.values[e] + decay * 0.5)
            else:
                self.values[e] = max(0.0, self.values[e] - decay)

    def summary(self) -> dict:
        self._apply_decay()
        return {e: round(v, 2) for e, v in self.values.items()}


class LocalEngine:
    def __init__(self):
        self.mood = EmotionalState()
        self.interaction_count = 0
        self.last_matched_rule = None
        self.repeat_count = {}
        self._apply_time_mood()

    def try_respond(self, user_input: str) -> dict | None:
        text = user_input.strip().lower()
        text = re.sub(r'\s+', ' ', text).strip()

        if not text:
            return None

        self._nudge_time_mood()

        matches = []
        for rule in RULES:
            if self._triggers_match(rule, text) and self._conditions_match(rule):
                matches.append(rule)

        if not matches:
            return None

        matches.sort(key=lambda r: r.get("priority", 0), reverse=True)
        best = matches[0]

        rule_id = best["id"]
        if self.last_matched_rule == rule_id:
            self.repeat_count[rule_id] = self.repeat_count.get(rule_id, 0) + 1
            if self.repeat_count[rule_id] >= 3 and len(matches) > 1:
                best = matches[1]
                rule_id = best["id"]
        else:
            self.repeat_count = {}

        self.last_matched_rule = rule_id

        current_mood = self.mood.current
        pools = best.get("responses", {})
        pool = pools.get(current_mood) or pools.get("neutral") or []

        if not pool:
            return None

        response_text = random.choice(pool)

        shift = best.get("emotion_shift", {})
        if shift:
            self.mood.shift(shift)

        self.interaction_count += 1
        emotion = self._mood_to_emotion(self.mood.current)

        return {
            "text": response_text,
            "emotion": emotion,
            "rule_id": rule_id,
            "mood_debug": self.mood.summary(),
        }

    def _mood_to_emotion(self, mood: str) -> str:
        mapping = {
            "neutral": "neutral",
            "happy": "happy",
            "sad": "sad",
            "flirty": "flirty",
            "annoyed": "neutral",
            "sleepy": "neutral",
        }
        return mapping.get(mood, "neutral")

    def sync_cloud_emotion(self, cloud_emotion: str):
        """Sincroniza humor local com a emoção que veio da nuvem."""
        emotion_map = {
            "happy": {"happy": 0.3},
            "sad": {"sad": 0.3},
            "flirty": {"flirty": 0.3},
            "laughing": {"happy": 0.4},
            "loving": {"flirty": 0.3, "happy": 0.2},
            "surprised": {"happy": 0.2},
            "playful": {"happy": 0.2, "flirty": 0.1},
            "spicy": {"flirty": 0.4},
        }
        shift = emotion_map.get(cloud_emotion, {})
        if shift:
            self.mood.shift(shift)

    def _triggers_match(self, rule: dict, text: str) -> bool:
        for pattern in rule.get("triggers", []):
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _conditions_match(self, rule: dict) -> bool:
        cond = rule.get("conditions", {})
        if not cond:
            return True

        now = datetime.now()
        hour = now.hour

        if "hour_range" in cond:
            start, end = cond["hour_range"]
            if start < end:
                if not (start <= hour < end):
                    return False
            else:
                if not (hour >= start or hour < end):
                    return False

        if "weekday" in cond:
            is_weekday = now.weekday() < 5
            if cond["weekday"] != is_weekday:
                return False

        if "weekday_in" in cond:
            if now.weekday() not in cond["weekday_in"]:
                return False

        return True

    def _apply_time_mood(self):
        hour = datetime.now().hour
        if 0 <= hour < 6:
            self.mood.force("sleepy", 0.7)
        elif 6 <= hour < 8:
            self.mood.force("sleepy", 0.4)
        elif 18 <= hour < 22:
            self.mood.force("happy", 0.4)
        elif hour >= 22:
            self.mood.force("sleepy", 0.5)
        else:
            self.mood.force("neutral", 0.5)

    def _nudge_time_mood(self):
        hour = datetime.now().hour
        if 0 <= hour < 6:
            self.mood.shift({"sleepy": 0.05})
        elif 18 <= hour < 22:
            self.mood.shift({"happy": 0.02})