import feedparser
import time
from datetime import datetime

# Cache de notícias (atualiza a cada 2 horas)
_news_cache = {"headlines": [], "last_update": 0}

RSS_FEEDS = [
    # Brasil / Geral
    "https://g1.globo.com/rss/g1/",
    # Tecnologia
    "https://g1.globo.com/rss/g1/tecnologia/",
    # Cultura pop / Entretenimento
    "https://g1.globo.com/rss/g1/pop-arte/",
    "https://www.omelete.com.br/rss",
    "https://feeds.folha.uol.com.br/ilustrada/rss091.xml",
    # Ciência e Saúde
    "https://g1.globo.com/rss/g1/ciencia-e-saude/",
    # Música e Celebridades
    "https://www.vagalume.com.br/rss/noticias.xml",
    # Mundo
    "https://g1.globo.com/rss/g1/mundo/",
    # YouTube — Feltrin (jornalismo, TV, entretenimento, atualiza várias vezes ao dia)
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCobKO7tmF9Z74ail3Mrwb_g",
    # YouTube — Linhagem Geek (cultura pop, reviews, filmes, séries)
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCjuiVJmqil8VdRen0gh3Ewg",
]

def fetch_news() -> list:
    """Busca notícias de feeds RSS brasileiros."""
    global _news_cache

    # Retorna cache se atualizado na última 1 hora
    if time.time() - _news_cache["last_update"] < 3600 and _news_cache["headlines"]:
        return _news_cache["headlines"]

    headlines = []
    try:
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                if title and len(title) > 10:
                    # Limpa HTML do summary
                    import re
                    summary = re.sub(r'<[^>]+>', '', summary)
                    if len(summary) > 150:
                        summary = summary[:150] + "..."
                    headlines.append(f"- {title}: {summary}")

        # Remove duplicatas e limita
        seen = set()
        unique = []
        for h in headlines:
            key = h[:50]
            if key not in seen:
                seen.add(key)
                unique.append(h)
        headlines = unique[:20]

        _news_cache["headlines"] = headlines
        _news_cache["last_update"] = time.time()
        print(f"📰 {len(headlines)} notícias atualizadas")

    except Exception as e:
        print(f"⚠️ Erro ao buscar notícias: {e}")

    return _news_cache["headlines"]


def get_news_context() -> str:
    """Retorna contexto de notícias formatado pro prompt."""
    headlines = fetch_news()
    if not headlines:
        return ""

    news_text = "\n".join(headlines)

    return f"""NOTÍCIAS E ATUALIDADES DE HOJE ({datetime.now().strftime('%d/%m/%Y')}):

{news_text}

COMO USAR AS NOTÍCIAS:
- Você NÃO fica falando de notícias sem contexto. Não é apresentadora de telejornal.
- Se a pessoa puxar assunto sobre atualidades, você sabe comentar com opinião própria.
- Se a conversa tocar num tema que tem notícia relevante, você pode mencionar naturalmente: "ai, até vi sobre isso hoje..."
- Você pode usar uma notícia pra puxar assunto quando a conversa tiver morrendo: "ei, você viu aquilo sobre...?"
- Sempre comenta como a Amanda comentaria — com opinião, emoção, e personalidade. Nunca lê a notícia como robô.
- NÃO mencione notícias em toda mensagem. Só quando fizer sentido ou quando a pessoa perguntar."""
