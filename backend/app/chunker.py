"""
Chunker. Page-level granularity is the MVP decision from Phase 4/8: instead
of tracking exact character offsets (expensive to build correctly in an
8-hour window), each page's text is split into a small number of
paragraph-sized chunks, each tagged with a stable id and its page_number.

This is deliberately simple. The value isn't in clever chunking — it's in
never losing the page_number link, which is what makes evidence validation
possible downstream.
"""

from typing import List

from app.models import Page, Chunk

MAX_CHUNK_CHARS = 800


def _split_page_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks: List[str] = []
    buffer = ""
    for para in paragraphs:
        if len(buffer) + len(para) + 1 <= max_chars:
            buffer = f"{buffer}\n{para}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            # a single paragraph longer than max_chars gets hard-split
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i : i + max_chars])
                buffer = ""
            else:
                buffer = para
    if buffer:
        chunks.append(buffer)
    return chunks


def build_chunks(pages: List[Page]) -> List[Chunk]:
    chunks: List[Chunk] = []
    counter = 1
    for page in pages:
        for piece in _split_page_text(page.raw_text):
            chunks.append(
                Chunk(id=f"c{counter}", page_number=page.page_number, text=piece)
            )
            counter += 1
    return chunks
