"""Read and normalize source data."""
from pathlib import Path
import re
import unicodedata
import pypdf
from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFKC), reconnect hyphens across lines, and preserve paragraphs."""
    if not text:
        return ""
    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # 2. Reconnect hyphenated words split across lines (e.g. mathema-\nticians -> mathematicians)
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # 3. Clean line by line and preserve paragraph breaks (\n\n)
    lines = [line.strip() for line in text.split("\n")]
    paragraphs = []
    curr = []
    for line in lines:
        if not line:
            if curr:
                paragraphs.append(" ".join(curr))
                curr = []
        else:
            curr.append(line)
    if curr:
        paragraphs.append(" ".join(curr))

    result = "\n\n".join(paragraphs)
    # Collapse multiple inline spaces
    result = re.sub(r"[ \t]+", " ", result).strip()
    return result


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page; keep page number, source, and section metadata.

    Detect and record pages with no text or non-content pages.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {path}")

    reader = pypdf.PdfReader(str(path))
    pages: list[DocumentPage] = []
    current_section = "Preface"

    for idx, pdf_page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = pdf_page.extract_text() or ""
        normalized = normalize_text(raw_text)

        # Determine section
        if page_num < 4:
            sec = "Front Matter"
        elif page_num == 4:
            sec = "Preface"
            current_section = "Preface"
        elif page_num >= 55:
            sec = "Note"
            current_section = "Note"
        else:
            # Drop the first line (book pagination number)
            lines = raw_text.split("\n")
            body_text = "\n".join(lines[1:])
            sec_matches = re.findall(r"^\s*(\d{1,2})\s*$", body_text, re.MULTILINE)
            if sec_matches:
                for s in sec_matches:
                    num = int(s)
                    if 1 <= num <= 29:
                        current_section = f"Section {num}"
            sec = current_section

        is_content_page = (page_num >= 4) and (len(normalized) > 50)

        metadata = {
            "section": sec,
            "char_count": len(normalized),
            "is_content_page": is_content_page,
            "has_text": len(normalized) > 0,
        }

        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_num,
                text=normalized,
                metadata=metadata,
            )
        )

    return pages
