"""PDF ingestion with page-level traceability and legal-structure metadata."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage
from .event_log import logged, operation, record_event

CHAPTER_RE = re.compile(r"(?im)^\s*(Chương\s+[IVXLCDM]+)\b")
SECTION_RE = re.compile(r"(?im)^\s*(Mục\s+\d+)\b")
ARTICLE_RE = re.compile(r"(?im)^\s*(Điều\s+\d+)\s*[.:-]")


def normalize_text(text: str) -> str:
    """Normalize Unicode and line whitespace while retaining paragraph structure."""
    text = unicodedata.normalize("NFC", text or "").replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t\f\v ]+", " ", line).strip() for line in text.split("\n")]
    out: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if out and not blank:
                out.append("")
            blank = True
        else:
            out.append(line)
            blank = False
    # Rejoin PDF line wraps; preserve headings and numbered legal clauses.
    paragraphs = []
    for line in out:
        if not line or re.fullmatch(r'\d+', line):
            continue
        if not paragraphs or re.match(r'^(Chương\b|Mục\b|Điều\s+\d+|\d+\.|[a-zđ]\))', line):
            paragraphs.append(line)
        else:
            paragraphs[-1] += ' ' + line
    return '\n\n'.join(paragraphs).strip()


@logged('ingestion.load_pdf')
def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical PDF page and carry chapter/section context forward."""
    reader = PdfReader(str(path))
    pages: list[DocumentPage] = []
    chapter: str | None = None
    section: str | None = None
    for page_num, page in enumerate(reader.pages, start=1):
        with operation('ingestion.extract_page', document_id=document_id, page=page_num):
            text = normalize_text(page.extract_text() or "")
        prior_chapter = chapter
        chapter_match = CHAPTER_RE.search(text)
        section_match = SECTION_RE.search(text)
        if chapter_match:
            chapter = chapter_match.group(1).title()
            section = None
        if section_match:
            section = section_match.group(1).title()
        metadata = {"document_id": document_id, "source": source, "page": page_num, "chapter_before": prior_chapter, "year": 2005}
        if chapter:
            metadata["chapter"] = chapter
        if section:
            metadata["section"] = section
        pages.append(DocumentPage(document_id, source, page_num, text, metadata))
        if list(CHAPTER_RE.finditer(text)):
            chapter = list(CHAPTER_RE.finditer(text))[-1].group(1).title()
        if len(text) < 100:
            record_event('ingestion.extract_page', 'low_text', level='warning',
                         document_id=document_id, page=page_num, characters=len(text))
            print(f"WARN: page {page_num} has only {len(text)} extracted characters")
    return pages


def chunk_metadata(text: str, inherited: dict) -> dict:
    metadata = dict(inherited)
    chapter = CHAPTER_RE.search(text)
    section = SECTION_RE.search(text)
    article = ARTICLE_RE.search(text)
    if chapter:
        metadata["chapter"] = chapter.group(1).title()
    if section:
        metadata["section"] = section.group(1).title()
    if article:
        metadata["article"] = article.group(1).title()
    return metadata
