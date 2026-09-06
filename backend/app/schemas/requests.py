"""Request schemas for API endpoints."""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class GenerateRequest(BaseModel):
    """JSON request body for POST /api/generate."""
    source: str = Field(..., min_length=1, max_length=50000, description="Source text content")
    audience: str = Field(default="General Public", description="Target audience")
    tone: str = Field(default="Professional", description="Tone of voice")
    language: str = Field(default="English", description="Target language")
    detail: str = Field(default="Standard", description="Level of detail")
    objective: str = Field(default="Inform", description="Primary objective")
    output_format: str = Field(default="Executive Summary", description="Comma-separated output formats")
    
    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        """Validate that source is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("Source content cannot be empty")
        return v.strip()
    
    def selected_formats(self) -> list[str]:
        """Parse output_format string into list of format names."""
        return [f.strip() for f in self.output_format.split(",") if f.strip()]

class IngestRequest(BaseModel):
    """Request for standalone ingestion."""
    source_text: Optional[str] = Field(default=None, description="Optional text content")
    source_url: Optional[str] = Field(default=None, description="Optional URL to fetch")
