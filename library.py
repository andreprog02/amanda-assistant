"""
library.py — Biblioteca da Amanda

Lê livros EPUB da pasta 'biblioteca/', separa por capítulos,
e fornece trechos pra Amanda ler (inteiro ou em partes).

Uso:
  from library import Library
  lib = Library()
  livros = lib.list_books()
  capitulos = lib.list_chapters("gente_pobre")
  texto = lib.get_chapter("gente_pobre", 1)
  parte = lib.get_part("gente_pobre", 1, 1)  # cap 1, parte 1
"""

import os
import re
import glob
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import Optional


BIBLIOTECA_DIR = "biblioteca"

# Tamanho máximo de cada "parte" (em caracteres) pra leitura parcial
# ~800 chars ≈ 1-2 parágrafos ≈ bom pra TTS sem ficar longo demais
PART_SIZE = 800


def _clean_html(html: str) -> str:
    """Remove tags HTML e limpa o texto."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Limpa linhas em branco excessivas
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)

    return "\n\n".join(lines)


def _slugify(name: str) -> str:
    """Converte nome do arquivo em slug simples."""
    name = os.path.splitext(name)[0]
    name = name.lower().strip()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s-]+', '_', name)
    return name


class Book:
    """Representa um livro carregado."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.slug = _slugify(self.filename)

        self._book = epub.read_epub(filepath, options={"ignore_ncx": True})
        self.title = self._book.get_metadata("DC", "title")
        self.title = self.title[0][0] if self.title else self.slug.replace("_", " ").title()

        self.author = self._book.get_metadata("DC", "creator")
        self.author = self.author[0][0] if self.author else "Autor desconhecido"

        self.chapters: list[dict] = []
        self._load_chapters()

    def _load_chapters(self):
        """Extrai capítulos do EPUB."""
        chapter_num = 0

        for item in self._book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content().decode("utf-8", errors="ignore")
            text = _clean_html(content)

            # Ignora páginas muito curtas (capa, copyright, etc.)
            if len(text.strip()) < 100:
                continue

            chapter_num += 1

            # Tenta extrair título do capítulo
            soup = BeautifulSoup(content, "html.parser")
            heading = soup.find(["h1", "h2", "h3"])
            chapter_title = heading.get_text().strip() if heading else f"Capítulo {chapter_num}"

            # Divide em partes pra leitura parcial
            parts = self._split_into_parts(text)

            self.chapters.append({
                "number": chapter_num,
                "title": chapter_title,
                "text": text,
                "parts": parts,
                "total_parts": len(parts),
                "char_count": len(text),
            })

    def _split_into_parts(self, text: str) -> list[str]:
        """Divide texto em partes de ~PART_SIZE chars, respeitando parágrafos."""
        paragraphs = text.split("\n\n")
        parts = []
        current_part = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Se adicionar esse parágrafo estoura o limite, fecha a parte atual
            if current_part and len(current_part) + len(para) + 2 > PART_SIZE:
                parts.append(current_part.strip())
                current_part = para
            else:
                current_part = current_part + "\n\n" + para if current_part else para

        # Última parte
        if current_part.strip():
            parts.append(current_part.strip())

        return parts if parts else [text]


class Library:
    """Gerencia a biblioteca de livros da Amanda."""

    def __init__(self, directory: str = BIBLIOTECA_DIR):
        self.directory = directory
        self.books: dict[str, Book] = {}
        self._load_books()

    def _load_books(self):
        """Carrega todos os EPUBs da pasta."""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)
            print(f"📚 Pasta '{self.directory}' criada. Coloque seus EPUBs lá!")
            return

        epub_files = glob.glob(os.path.join(self.directory, "*.epub"))

        for filepath in epub_files:
            try:
                book = Book(filepath)
                self.books[book.slug] = book
                print(f"📖 Livro carregado: {book.title} ({book.author}) — {len(book.chapters)} capítulos")
            except Exception as e:
                print(f"⚠️ Erro ao carregar {filepath}: {e}")

        if not epub_files:
            print(f"📚 Nenhum EPUB encontrado em '{self.directory}/'")

    def reload(self):
        """Recarrega a biblioteca (se adicionar livros novos)."""
        self.books.clear()
        self._load_books()

    def list_books(self) -> list[dict]:
        """Lista todos os livros disponíveis."""
        return [
            {
                "slug": slug,
                "title": book.title,
                "author": book.author,
                "chapters": len(book.chapters),
            }
            for slug, book in self.books.items()
        ]

    def find_book(self, query: str) -> Optional[Book]:
        """Busca um livro por slug, título parcial ou autor."""
        query_lower = query.lower().strip()

        # Busca por slug exato
        if query_lower in self.books:
            return self.books[query_lower]

        # Busca por título parcial
        for slug, book in self.books.items():
            if query_lower in book.title.lower() or query_lower in slug:
                return book

        # Busca por autor
        for slug, book in self.books.items():
            if query_lower in book.author.lower():
                return book

        return None

    def list_chapters(self, book_query: str) -> Optional[list[dict]]:
        """Lista capítulos de um livro."""
        book = self.find_book(book_query)
        if not book:
            return None

        return [
            {
                "number": ch["number"],
                "title": ch["title"],
                "total_parts": ch["total_parts"],
                "chars": ch["char_count"],
            }
            for ch in book.chapters
        ]

    def get_chapter(self, book_query: str, chapter_num: int) -> Optional[dict]:
        """Retorna o texto completo de um capítulo."""
        book = self.find_book(book_query)
        if not book:
            return None

        for ch in book.chapters:
            if ch["number"] == chapter_num:
                return {
                    "book_title": book.title,
                    "chapter_title": ch["title"],
                    "chapter_number": ch["number"],
                    "text": ch["text"],
                    "total_parts": ch["total_parts"],
                    "total_chapters": len(book.chapters),
                }
        return None

    def get_part(self, book_query: str, chapter_num: int, part_num: int) -> Optional[dict]:
        """Retorna uma parte específica de um capítulo."""
        book = self.find_book(book_query)
        if not book:
            return None

        for ch in book.chapters:
            if ch["number"] == chapter_num:
                if 1 <= part_num <= ch["total_parts"]:
                    return {
                        "book_title": book.title,
                        "chapter_title": ch["title"],
                        "chapter_number": ch["number"],
                        "part_number": part_num,
                        "total_parts": ch["total_parts"],
                        "total_chapters": len(book.chapters),
                        "text": ch["parts"][part_num - 1],
                        "has_next": part_num < ch["total_parts"],
                    }
        return None


# ══════════════════════════════════════════════════════════════
# Contexto pro prompt da Amanda
# ══════════════════════════════════════════════════════════════

def get_library_context(library: Library) -> str:
    """Gera contexto da biblioteca pra injetar no system prompt."""
    books = library.list_books()
    if not books:
        return ""

    lines = ["SEUS LIVROS (sua estante pessoal):"]
    for b in books:
        lines.append(f'• "{b["title"]}" de {b["author"]} ({b["chapters"]} capítulos)')

    lines.append("")
    lines.append(
        "Quando alguém perguntar sobre seus livros, fale com carinho sobre eles como se fossem seus. "
        "Você pode listar o que tem, opinar sobre eles, e se pedirem, ler em voz alta. "
        "Se pedirem pra ler, você lê o trecho como se estivesse lendo em voz alta pro interlocutor, "
        "com naturalidade, sem explicar que está 'acessando o arquivo'. "
        "Você pode ler o capítulo inteiro ou em partes — pergunte como a pessoa prefere. "
        "Depois de ler uma parte, pergunte naturalmente se quer que continue."
    )

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Instância global (carrega ao importar)
# ══════════════════════════════════════════════════════════════

_library_instance: Optional[Library] = None


def get_library() -> Library:
    """Retorna a instância global da biblioteca."""
    global _library_instance
    if _library_instance is None:
        _library_instance = Library()
    return _library_instance
