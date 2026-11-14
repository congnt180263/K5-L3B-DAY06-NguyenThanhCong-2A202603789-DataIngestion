"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split text into overlapping fixed-size windows and retain page metadata."""
    text = page.text.strip()
    if not text:
        return []

    if len(text) <= size:
        return [
            Chunk(
                chunk_id=f"{page.document_id}_p{page.page}_f0",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text,
                metadata=dict(page.metadata),
            )
        ]

    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    idx = 0
    start = 0

    while start < len(text):
        end = min(start + size, len(text))
        window_text = text[start:end].strip()
        if window_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_f{idx}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=window_text,
                    metadata=dict(page.metadata),
                )
            )
            idx += 1
        if end >= len(text):
            break
        start += step

    return chunks


def _split_long_paragraph(text: str, max_size: int) -> list[str]:
    """Split an oversized paragraph by sentence boundaries or punctuation."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sub_chunks: list[str] = []
    current_sentences: list[str] = []
    current_length = 0

    for sent in sentences:
        sent_len = len(sent)
        if current_length + sent_len + 1 > max_size and current_sentences:
            sub_chunks.append(" ".join(current_sentences))
            current_sentences = [sent]
            current_length = sent_len
        else:
            current_sentences.append(sent)
            current_length += sent_len + 1

    if current_sentences:
        sub_chunks.append(" ".join(current_sentences))

    # If any sub-chunk is still oversized (e.g. no punctuation), hard split by words
    final_sub_chunks: list[str] = []
    for chunk in sub_chunks:
        if len(chunk) <= max_size:
            final_sub_chunks.append(chunk)
        else:
            words = chunk.split()
            w_curr: list[str] = []
            w_len = 0
            for w in words:
                if w_len + len(w) + 1 > max_size and w_curr:
                    final_sub_chunks.append(" ".join(w_curr))
                    w_curr = [w]
                    w_len = len(w)
                else:
                    w_curr.append(w)
                    w_len += len(w) + 1
            if w_curr:
                final_sub_chunks.append(" ".join(w_curr))

    return final_sub_chunks


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Group paragraphs naturally, split oversized paragraphs and retain metadata."""
    text = page.text.strip()
    if not text:
        return []

    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not raw_paragraphs:
        return []

    # Merge small consecutive paragraphs, split large paragraphs
    refined_paragraphs: list[str] = []
    current_buf: list[str] = []
    current_len = 0

    for para in raw_paragraphs:
        para_len = len(para)
        if para_len > max_size:
            # Flush current buffer first
            if current_buf:
                refined_paragraphs.append("\n\n".join(current_buf))
                current_buf = []
                current_len = 0
            # Split the oversized paragraph
            split_parts = _split_long_paragraph(para, max_size)
            refined_paragraphs.extend(split_parts)
        elif current_len + para_len + 2 > max_size and current_buf:
            refined_paragraphs.append("\n\n".join(current_buf))
            current_buf = [para]
            current_len = para_len
        else:
            current_buf.append(para)
            current_len += para_len + 2

    if current_buf:
        refined_paragraphs.append("\n\n".join(current_buf))

    chunks: list[Chunk] = []
    for idx, chunk_text in enumerate(refined_paragraphs):
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}_p{page.page}_p{idx}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=dict(page.metadata),
            )
        )

    return chunks
