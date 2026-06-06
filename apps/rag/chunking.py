"""
Lightweight, dependency-free text chunking for RAG ingestion.

Splits long documents into overlapping, paragraph-aware chunks small enough
for bge-small (512-token limit). Char-based sizing keeps it simple and is a
good proxy: ~900 chars ≈ 200 tokens, comfortably under the limit.
"""
import re

DEFAULT_CHUNK_SIZE = 900     # characters
DEFAULT_OVERLAP = 150        # characters carried into the next chunk


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE,
               overlap: int = DEFAULT_OVERLAP) -> list[str]:
    """Return a list of overlapping chunks, split on paragraph/sentence
    boundaries where possible so a chunk doesn't cut mid-sentence."""
    text = (text or '').strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    # Prefer splitting on blank lines (paragraphs), then sentences.
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    chunks: list[str] = []
    buf = ''
    for para in paragraphs:
        if len(para) > chunk_size:
            # Paragraph itself too big -> fall back to sentence packing.
            for sentence in re.split(r'(?<=[.!?])\s+', para):
                if len(buf) + len(sentence) + 1 > chunk_size and buf:
                    chunks.append(buf.strip())
                    buf = _tail(buf, overlap)
                buf += (' ' if buf else '') + sentence
        else:
            if len(buf) + len(para) + 2 > chunk_size and buf:
                chunks.append(buf.strip())
                buf = _tail(buf, overlap)
            buf += ('\n\n' if buf else '') + para

    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def _tail(text: str, overlap: int) -> str:
    """Return the last `overlap` chars of text, trimmed to a word boundary,
    to seed the next chunk with context."""
    if overlap <= 0 or len(text) <= overlap:
        return ''
    tail = text[-overlap:]
    # Avoid starting mid-word.
    space = tail.find(' ')
    return tail[space + 1:] if space != -1 else tail
