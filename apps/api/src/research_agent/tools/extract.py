from dataclasses import dataclass
from datetime import datetime
from io import BytesIO


@dataclass(frozen=True)
class ExtractedDocument:
    title: str | None
    text: str
    published_at: datetime | None


def extract_document(body: bytes, content_type: str) -> ExtractedDocument:
    if content_type == "application/pdf":
        return ExtractedDocument(title=None, text=_pdf_text(body), published_at=None)
    html = body.decode("utf-8", errors="replace")
    title, text, published = _html_text(html)
    return ExtractedDocument(title=title, text=text, published_at=published)


def chunk_text(text: str, size: int = 1200, overlap: int = 200) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _pdf_text(body: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(body))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _html_text(html: str) -> tuple[str | None, str, datetime | None]:
    try:
        import trafilatura

        text = trafilatura.extract(html, include_comments=False) or ""
        metadata = trafilatura.extract_metadata(html)
        title = metadata.title if metadata is not None else None
        published = None
        if metadata is not None and metadata.date:
            try:
                published = datetime.fromisoformat(metadata.date)
            except ValueError:
                published = None
        if text:
            return title, text, published
    except Exception:
        pass
    title = None
    lower = html.lower()
    if "<title>" in lower:
        start = lower.index("<title>") + len("<title>")
        end = lower.find("</title>", start)
        title = html[start:end].strip() if end > start else None
    text = _strip_tags(html)
    return title, text, None


def _strip_tags(html: str) -> str:
    out: list[str] = []
    skip = False
    for char in html:
        if char == "<":
            skip = True
            continue
        if char == ">":
            skip = False
            out.append(" ")
            continue
        if not skip:
            out.append(char)
    return " ".join("".join(out).split())
