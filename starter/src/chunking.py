"""Fixed-window and paragraph-aware chunking."""
from __future__ import annotations

import hashlib
import re

from .ingestion import chunk_metadata
from .models import Chunk, DocumentPage

def regions(page):
    """Common chapter boundaries for A/B, so no chunk receives a wrong chapter."""
    from .ingestion import CHAPTER_RE
    matches = list(CHAPTER_RE.finditer(page.text))
    starts = sorted(set([0] + [m.start() for m in matches]))
    chapter = page.metadata.get('chapter_before')
    result = []
    for i, start in enumerate(starts):
        end = starts[i+1] if i+1 < len(starts) else len(page.text)
        text = page.text[start:end].strip()
        heading = CHAPTER_RE.match(text)
        if heading:
            chapter = heading.group(1).title()
        metadata = dict(page.metadata)
        metadata.pop('chapter_before', None)
        metadata.pop('section', None)
        if chapter:
            metadata['chapter'] = chapter
        else:
            metadata.pop('chapter', None)
        if text:
            result.append(DocumentPage(page.document_id, page.source, page.page, text, metadata))
    return result


def _make_chunk(page: DocumentPage, text: str, strategy: str, ordinal: int) -> Chunk:
    digest = hashlib.sha1(
        f"{page.document_id}|{page.page}|{strategy}|{ordinal}|{text}".encode("utf-8")
    ).hexdigest()[:16]
    return Chunk(
        chunk_id=f"{page.document_id}-p{page.page}-{strategy}-{digest}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text,
        metadata=chunk_metadata(text, page.metadata),
    )


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split a page into overlapping character windows, retaining page metadata."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("size must be positive and 0 <= overlap < size")
    text = page.text.strip()
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(_make_chunk(page, piece, f"fixed-{size}-{overlap}", len(chunks)))
        if end == len(text):
            break
        start = end - overlap
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs up to max_size; split a single oversized paragraph."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page.text) if p.strip()]
    groups: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_size:
            if current:
                groups.append(current)
                current = ""
            # Preserve an oversized paragraph as contiguous bounded pieces.
            for offset in range(0, len(paragraph), max_size):
                groups.append(paragraph[offset:offset + max_size].strip())
        elif not current:
            current = paragraph
        elif len(current) + 2 + len(paragraph) <= max_size:
            current += "\n\n" + paragraph
        else:
            groups.append(current)
            current = paragraph
    if current:
        groups.append(current)
    return [_make_chunk(page, text, f"paragraph-{max_size}", i)
            for i, text in enumerate(groups) if text]
