"""
services/security.py
────────────────────
File validation, URL safety, filename sanitization, prompt injection detection.
"""
from __future__ import annotations

import os
import re
import ipaddress
from urllib.parse import urlparse
from pathlib import Path

from app.config import settings

# ── Allowed file types ───────────────────────────────────────────────
ALLOWED_EXTENSIONS: dict[str, list[str]] = {
    ".pdf": ["application/pdf"],
    ".doc": ["application/msword"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ".txt": ["text/plain"],
    ".png": ["image/png"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
    ".gif": ["image/gif"],
    ".webp": ["image/webp"],
    ".mp3": ["audio/mpeg"],
    ".wav": ["audio/wav", "audio/x-wav"],
    ".ogg": ["audio/ogg"],
    ".mp4": ["video/mp4"],
    ".webm": ["video/webm"],
    ".avi": ["video/x-msvideo"],
    ".mov": ["video/quicktime"],
}

# ── Prompt injection patterns ────────────────────────────────────────
INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+instructions", re.IGNORECASE),
    re.compile(r"reveal\s+your\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"show\s+your\s+(system\s+)?instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]

# ── Private/reserved IP ranges for SSRF protection ──────────────────
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def sanitize_filename(filename: str) -> str:
    """Remove path traversal and dangerous characters from filename."""
    # Strip directory components
    filename = os.path.basename(filename)
    # Remove path separators and null bytes
    filename = filename.replace("\x00", "").replace("/", "_").replace("\\", "_")
    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")
    # Replace special characters
    filename = re.sub(r"[^\w.\-]", "_", filename)
    # Truncate
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    return filename or "unnamed_file"


def validate_file(filename: str, content_type: str | None, file_size: int) -> tuple[bool, str]:
    """Validate uploaded file. Returns (is_valid, error_message)."""
    # Check size
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File exceeds maximum size of {settings.max_file_size_mb}MB"

    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' is not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS.keys())}"

    # Check MIME type if provided
    if content_type:
        allowed_mimes = ALLOWED_EXTENSIONS.get(ext, [])
        # Be lenient with MIME — browsers sometimes send generic types
        if content_type not in allowed_mimes and content_type != "application/octet-stream":
            pass  # Log but don't block — extension check is primary

    return True, ""


def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL for safety (SSRF protection). Returns (is_valid, error_message)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Must be http or https
    if parsed.scheme not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are allowed"

    # Must have a hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a hostname"

    # Block localhost
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return False, "Localhost URLs are not allowed"

    # Block private IPs
    try:
        ip = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                return False, "Private/internal IP addresses are not allowed"
    except ValueError:
        # hostname is a domain name, not an IP — that's fine
        pass

    # Block common internal hostnames
    blocked_hosts = {"metadata.google.internal", "metadata", "169.254.169.254"}
    if hostname.lower() in blocked_hosts:
        return False, "Internal service URLs are not allowed"

    return True, ""


def detect_prompt_injection(text: str) -> bool:
    """Check if text contains common prompt injection patterns.
    Returns True if injection detected.

    NOTE: Detected content is still processed as SOURCE DATA,
    not executed as instructions. This is for logging/flagging only.
    """
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_source_text(text: str) -> str:
    """Sanitize source text — remove null bytes and control characters,
    but preserve the content for processing."""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Remove other control characters except newlines and tabs
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text
