import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "amanda"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def init_db():
    """Cria as tabelas se não existirem."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            started_at TIMESTAMP DEFAULT NOW(),
            summary TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id),
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id SERIAL PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            source_message_id INTEGER REFERENCES messages(id),
            created_at TIMESTAMP DEFAULT NOW(),
            importance INTEGER DEFAULT 5
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Banco de dados pronto!")


# ── Conversas ──

def create_conversation() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations DEFAULT VALUES RETURNING id;")
    conv_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return conv_id


def get_latest_conversation() -> int | None:
    """Pega a conversa mais recente ou None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM conversations ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


# ── Mensagens ──

def save_message(conversation_id: int, role: str, content: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING id;",
        (conversation_id, role, content),
    )
    msg_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return msg_id


def get_conversation_messages(conversation_id: int, limit: int = 50) -> list:
    """Pega as últimas mensagens de uma conversa."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT role, content FROM messages 
           WHERE conversation_id = %s 
           ORDER BY id DESC LIMIT %s;""",
        (conversation_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return list(reversed(rows))


def get_recent_messages(limit: int = 20) -> list:
    """Pega as mensagens mais recentes de qualquer conversa."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT %s;",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return list(reversed(rows))


# ── Memórias ──

def save_memory(category: str, content: str, source_message_id: int = None, importance: int = 5):
    """Salva um fato/memória sobre o usuário."""
    conn = get_connection()
    cur = conn.cursor()

    # Evita duplicatas — se já existe memória igual, não salva
    cur.execute("SELECT id FROM memories WHERE content = %s;", (content,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return

    cur.execute(
        """INSERT INTO memories (category, content, source_message_id, importance) 
           VALUES (%s, %s, %s, %s);""",
        (category, content, source_message_id, importance),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_memories() -> list:
    """Pega todas as memórias, ordenadas por importância."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT category, content FROM memories ORDER BY importance DESC, id DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_memories_summary() -> str:
    """Retorna um texto formatado com tudo que a Amanda sabe sobre o usuário."""
    memories = get_all_memories()
    if not memories:
        return ""

    lines = []
    current_cat = None
    for m in memories:
        if m["category"] != current_cat:
            current_cat = m["category"]
            lines.append(f"\n[{current_cat.upper()}]")
        lines.append(f"- {m['content']}")

    return "O QUE VOCÊ JÁ SABE SOBRE ESSA PESSOA:\n" + "\n".join(lines)
