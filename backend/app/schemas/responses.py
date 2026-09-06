"""Response schemas for API endpoints."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime, timezone

class ErrorDetail(BaseModel):
    """Error detail information."""
    code: str
    message: str

class ErrorResponse(BaseModel):
    """Standard error response payload."""
    success: bool = False
    error: ErrorDetail

class GenerateMetadata(BaseModel):
    """Metadata regarding content generation parameters and runtime."""
    language: str = ""
    audience: str = ""
    tone: str = ""
    detail: str = ""
    objective: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model: str = ""
    provider: str = ""

class GenerateResponse(BaseModel):
    """Content generation response."""
    success: bool = True
    job_id: str = ""
    output: str = ""  # Combined readable text for backward compat
    outputs: dict[str, Any] = Field(default_factory=dict)  # Per-format structured data
    metadata: GenerateMetadata = Field(default_factory=GenerateMetadata)

class HealthResponse(BaseModel):
    """Service health response."""
    status: str = "healthy"
    provider: str = ""
    demo_mode: bool = False
    model: str = ""
    version: str = "1.0.0"

class IngestResponse(BaseModel):
    """Document ingestion response."""
    success: bool = True
    source_id: str = ""
    files: list[dict[str, Any]] = Field(default_factory=list)
    extracted_text: str = ""
    status: str = "ready"
