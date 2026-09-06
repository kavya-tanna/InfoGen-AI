"""
services/ingestion.py
─────────────────────
Multi-modal content extraction: PDF, DOCX, TXT, URL, images, audio, video.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.services.security import sanitize_filename, sanitize_source_text, validate_url
from app.utils.logging import logger


# ═══════════════════════════════════════════════════════════════════════
# NORMALIZED SOURCE
# ═══════════════════════════════════════════════════════════════════════

class NormalizedSource:
    """Canonical internal representation of any ingested source."""

    def __init__(
        self,
        source_type: str = "text",
        filename: str = "",
        raw_text: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        self.source_id: str = str(uuid.uuid4())
        self.source_type: str = source_type
        self.filename: str = filename
        self.raw_text: str = raw_text
        self.metadata: dict[str, Any] = metadata or {}
        self.extracted_content: dict[str, Any] = {}
        self.media: list[dict[str, Any]] = []
        self.language: str = ""
        self.entities: list[str] = []
        self.facts: list[str] = []
        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "filename": self.filename,
            "raw_text": self.raw_text[:500] + "..." if len(self.raw_text) > 500 else self.raw_text,
            "metadata": self.metadata,
            "language": self.language,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# FILE EXTRACTORS
# ═══════════════════════════════════════════════════════════════════════

def extract_pdf(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Extract text from PDF using PyMuPDF."""
    import fitz

    source = NormalizedSource(source_type="pdf", filename=filename)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        text_parts: list[str] = []
        page_count = 0
        with fitz.open(tmp_path) as pdf:
            page_count = len(pdf)
            for page_num, page in enumerate(pdf):
                page_text = page.get_text()
                text_parts.append(page_text)

        source.raw_text = "\n\n".join(text_parts)
        source.metadata = {
            "page_count": page_count,
            "extraction_method": "PyMuPDF",
        }
        logger.info(f"PDF extracted: {filename}, {page_count} pages, {len(source.raw_text)} chars")
    finally:
        os.unlink(tmp_path)

    return source


def extract_docx(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Extract text from DOCX using python-docx."""
    import docx

    source = NormalizedSource(source_type="docx", filename=filename)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = docx.Document(tmp_path)

        paragraphs: list[str] = []
        headings: list[str] = []
        for para in doc.paragraphs:
            if para.style and para.style.name and para.style.name.startswith("Heading"):
                headings.append(para.text)
            paragraphs.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                paragraphs.append(" | ".join(cell.text for cell in row.cells))

        source.raw_text = "\n".join(paragraphs)
        source.metadata = {
            "paragraph_count": len(paragraphs),
            "headings": headings[:20],
            "extraction_method": "python-docx",
        }
        logger.info(f"DOCX extracted: {filename}, {len(paragraphs)} paragraphs, {len(source.raw_text)} chars")
    finally:
        os.unlink(tmp_path)

    return source


def extract_txt(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Extract text from plain text file."""
    source = NormalizedSource(source_type="txt", filename=filename)
    try:
        source.raw_text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("TXT files must use UTF-8 encoding.")
    if "\x00" in source.raw_text:
        raise ValueError("This file contains binary data, not plain text.")
    source.metadata = {"extraction_method": "direct", "byte_size": len(file_bytes)}
    logger.info(f"TXT extracted: {filename}, {len(source.raw_text)} chars")
    return source


def extract_url(url: str) -> NormalizedSource:
    """Fetch and extract readable content from a URL."""
    import requests
    from bs4 import BeautifulSoup
    import socket
    import ipaddress
    from urllib.parse import urlparse

    is_valid, err = validate_url(url)
    if not is_valid:
        raise ValueError(f"URL validation failed: {err}")
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise ValueError("URLs with credentials are not supported.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Only public internet URLs are supported.")
    except OSError:
        raise ValueError("Could not resolve this URL. Paste the article text instead.")

    source = NormalizedSource(source_type="url", filename=url)

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "InfoGenAI/1.0 (Content Extraction Bot)",
                "Accept": "text/html,application/xhtml+xml,text/plain",
            },
            allow_redirects=False,
            stream=True,
        )
        if 300 <= response.status_code < 400:
            response.close()
            raise ValueError("This URL redirects. Paste the final public article URL or its text.")
        response.raise_for_status()
        chunks = []
        size = 0
        try:
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    raise ValueError("Webpage exceeds 2 MB. Paste a shorter excerpt.")
                chunks.append(chunk)
        finally:
            response.close()
        response._content = b"".join(chunks)
    except requests.Timeout:
        raise ValueError("URL request timed out after 15 seconds")
    except requests.RequestException:
        raise ValueError("Could not fetch this public page. Paste the article text instead.")

    content_type = response.headers.get("content-type", "")

    if "text/html" in content_type or "application/xhtml" in content_type:
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "noscript", "form", "button", "svg"]):
            tag.decompose()

        # Try to find main content
        main = soup.find("article") or soup.find("main") or soup.find("div", {"role": "main"})
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        source.raw_text = "\n".join(lines)

        source.metadata = {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "extraction_method": "BeautifulSoup",
            "content_length": len(source.raw_text),
        }
    elif "text/plain" in content_type:
        source.raw_text = response.text
        source.metadata = {"url": url, "extraction_method": "plain_text"}
    else:
        raise ValueError(f"Unsupported content type from URL: {content_type}")

    logger.info(f"URL extracted: {url}, {len(source.raw_text)} chars")
    return source


def extract_image(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Process image — returns description placeholder.
    Vision model integration can be added here.
    """
    source = NormalizedSource(source_type="image", filename=filename)
    source.raw_text = f"[Image uploaded: {filename}. Image content analysis requires a vision model.]"
    source.metadata = {
        "extraction_method": "metadata_only",
        "byte_size": len(file_bytes),
        "note": "Vision model integration available via NVIDIA NIM"
    }
    source.media = [{"type": "image", "filename": filename, "size": len(file_bytes)}]
    logger.info(f"Image registered: {filename}")
    return source


def extract_audio(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Process audio — returns metadata.
    Whisper/transcription integration can be added here.
    """
    source = NormalizedSource(source_type="audio", filename=filename)
    source.raw_text = f"[Audio uploaded: {filename}. Transcription requires a speech-to-text model.]"
    source.metadata = {
        "extraction_method": "metadata_only",
        "byte_size": len(file_bytes),
        "note": "Whisper transcription can be configured"
    }
    source.media = [{"type": "audio", "filename": filename, "size": len(file_bytes)}]
    logger.info(f"Audio registered: {filename}")
    return source


def extract_video(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Process video — returns metadata.
    Audio extraction + transcription can be added here.
    """
    source = NormalizedSource(source_type="video", filename=filename)
    source.raw_text = f"[Video uploaded: {filename}. Transcription requires video processing pipeline.]"
    source.metadata = {
        "extraction_method": "metadata_only",
        "byte_size": len(file_bytes),
        "note": "Video processing pipeline can be configured"
    }
    source.media = [{"type": "video", "filename": filename, "size": len(file_bytes)}]
    logger.info(f"Video registered: {filename}")
    return source


# ═══════════════════════════════════════════════════════════════════════
# MAIN INGESTION DISPATCHER
# ═══════════════════════════════════════════════════════════════════════

_EXTRACTOR_MAP = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".txt": extract_txt,
}

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
_VIDEO_EXTENSIONS = {".mp4", ".webm", ".avi", ".mov", ".mkv"}


def ingest_file(file_bytes: bytes, filename: str) -> NormalizedSource:
    """Route file to appropriate extractor based on extension."""
    ext = os.path.splitext(filename)[1].lower()

    if ext in _EXTRACTOR_MAP:
        return _EXTRACTOR_MAP[ext](file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def ingest_text(text: str) -> NormalizedSource:
    """Create NormalizedSource from raw text input."""
    text = sanitize_source_text(text)
    source = NormalizedSource(source_type="text", raw_text=text)
    source.metadata = {"char_count": len(text)}
    logger.info(f"Text ingested: {len(text)} chars")
    return source


def is_url(text: str) -> bool:
    """Check if text appears to be a URL."""
    text = text.strip()
    return (
        text.startswith("http://") or text.startswith("https://")
    ) and " " not in text and len(text) < 2000
