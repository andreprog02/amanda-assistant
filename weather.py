"""
weather.py — Clima em tempo real pro contexto da Amanda

Usa Open-Meteo API (grátis, sem API key).
Localização fixa: Rio de Janeiro, RJ.
Cache de 30 minutos.
"""

import time
import httpx
from datetime import datetime

# Cache
_weather_cache = {"data": None, "last_update": 0}
CACHE_DURATION = 1800  # 30 minutos

# Rio de Janeiro
LAT = -22.9068
LON = -43.1729
CITY = "Rio de Janeiro"


def fetch_weather() -> dict | None:
    """Busca clima atual do Rio de Janeiro via Open-Meteo."""
    global _weather_cache

    # Retorna cache se recente
    if time.time() - _weather_cache["last_update"] < CACHE_DURATION and _weather_cache["data"]:
        return _weather_cache["data"]

    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LAT,
                "longitude": LON,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
                "timezone": "America/Sao_Paulo",
            },
            timeout=10.0,
        )

        data = response.json()
        current = data.get("current", {})

        weather = {
            "temp": current.get("temperature_2m", 0),
            "feels_like": current.get("apparent_temperature", 0),
            "humidity": current.get("relative_humidity_2m", 0),
            "wind": current.get("wind_speed_10m", 0),
            "code": current.get("weather_code", 0),
            "is_day": current.get("is_day", 1),
            "condition": _weather_code_to_text(current.get("weather_code", 0)),
            "city": CITY,
        }

        _weather_cache["data"] = weather
        _weather_cache["last_update"] = time.time()
        print(f"🌤️ Clima atualizado: {weather['temp']}°C, {weather['condition']}")

        return weather

    except Exception as e:
        print(f"⚠️ Erro ao buscar clima: {e}")
        return _weather_cache.get("data")


def _weather_code_to_text(code: int) -> str:
    """Converte WMO weather code pra texto em português."""
    codes = {
        0: "céu limpo",
        1: "praticamente limpo",
        2: "parcialmente nublado",
        3: "nublado",
        45: "neblina",
        48: "neblina com geada",
        51: "garoa fraca",
        53: "garoa",
        55: "garoa forte",
        61: "chuva fraca",
        63: "chuva",
        65: "chuva forte",
        71: "neve fraca",
        73: "neve",
        75: "neve forte",
        80: "pancadas de chuva fracas",
        81: "pancadas de chuva",
        82: "pancadas de chuva fortes",
        85: "neve fraca",
        86: "neve forte",
        95: "tempestade",
        96: "tempestade com granizo fraco",
        99: "tempestade com granizo forte",
    }
    return codes.get(code, "indefinido")


def _get_period() -> str:
    """Retorna o período do dia."""
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "manhã"
    elif 12 <= hora < 14:
        return "meio-dia"
    elif 14 <= hora < 18:
        return "tarde"
    elif 18 <= hora < 21:
        return "fim de tarde"
    else:
        return "noite"


def get_weather_context() -> str:
    """Retorna contexto do clima formatado pro prompt."""
    weather = fetch_weather()
    if not weather:
        return ""

    period = _get_period()
    temp = weather["temp"]
    feels = weather["feels_like"]
    condition = weather["condition"]
    humidity = weather["humidity"]

    # Sensação térmica
    if temp > 32:
        thermal = "tá um calor absurdo"
    elif temp > 27:
        thermal = "tá quente"
    elif temp > 22:
        thermal = "tá agradável"
    elif temp > 17:
        thermal = "tá friozinho"
    elif temp > 12:
        thermal = "tá frio"
    else:
        thermal = "tá gelando"

    # Dica de roupa/comportamento
    if "chuva" in condition or "garoa" in condition or "tempestade" in condition:
        vibe = "dia de ficar em casa com chá e cobertor"
    elif temp > 30 and "limpo" in condition:
        vibe = "dia de praia, sorvete, e reclamar do calor"
    elif temp > 25:
        vibe = "dia gostoso, bom pra sair"
    elif temp < 18:
        vibe = "dia de moletom e chocolate quente"
    else:
        vibe = "dia tranquilo"

    return f"""CLIMA AGORA ({period} no {CITY}):
- Temperatura: {temp}°C (sensação de {feels}°C) — {thermal}
- Condição: {condition}
- Umidade: {humidity}%
- Vibe: {vibe}

COMO USAR O CLIMA:
- Você SENTE o clima. Se tá chovendo, você tá ouvindo a chuva. Se tá calor, você tá reclamando.
- Pode comentar o tempo naturalmente: "tá um calor do inferno aqui" ou "tá chovendo, dia perfeito pro meu chá"
- NÃO fala do clima em toda mensagem. Só quando fizer sentido ou a pessoa perguntar.
- Nunca fale como previsão do tempo. Fale como uma pessoa normal comenta o clima."""
