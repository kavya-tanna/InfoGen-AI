"""Application configuration via pydantic-settings."""
from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    # AI Provider
    ai_provider: str = Field(default="nvidia", description="AI provider: nvidia|openai|gemini|anthropic|demo")
    nvidia_api_key: str = Field(default="", description="NVIDIA NIM API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    google_api_key: str = Field(default="", description="Google Gemini API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    model_name: str = Field(default="", description="Model identifier from the configured provider")
    ai_timeout_seconds: int = Field(default=150, ge=5, le=180, description="Total per-format generation deadline including fallback")
    primary_timeout_seconds: int = Field(default=90, ge=5, le=150)
    fallback_provider: str = Field(default="", description="Optional fallback: gemini")
    gemini_model_name: str = Field(default="gemini-3.6-flash")
    fast_model_name: str = Field(default="deepseek-ai/deepseek-v4-flash", description="Fast model for extraction")
    
    # Application
    demo_mode: bool = Field(default=False, description="Enable demo mode with mock outputs")
    max_file_size_mb: int = Field(default=25, description="Max upload file size in MB")
    database_url: str = Field(default="sqlite:///./infogen.db", description="Database URL")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Security
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    rate_limit_per_minute: int = Field(default=30, description="Rate limit per minute")
    
    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    prompts_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent / "prompts")
    uploads_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "uploads")
    
    model_config = {"env_file": str(Path(__file__).resolve().parent.parent / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}
    
    def has_ai_key(self) -> bool:
        """Check whether any AI provider API key is configured."""
        return bool(self.nvidia_api_key or self.openai_api_key or self.google_api_key or self.anthropic_api_key)
    
    def effective_provider(self) -> str:
        """Resolve the effective AI provider name based on configuration and available keys."""
        if self.demo_mode or self.ai_provider == "demo":
            return "demo"
        if self.ai_provider == "nvidia" and self.nvidia_api_key:
            return "nvidia"
        if self.ai_provider == "openai" and self.openai_api_key:
            return "openai"
        if self.ai_provider == "gemini" and self.google_api_key:
            return "gemini"
        if self.ai_provider == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        return self.ai_provider

    def configuration_error(self) -> str:
        provider = self.effective_provider()
        if provider == "demo":
            return ""
        key_fields = {"nvidia": "nvidia_api_key", "openai": "openai_api_key",
                      "gemini": "google_api_key", "anthropic": "anthropic_api_key"}
        if provider not in key_fields:
            return "Select a supported AI_PROVIDER in backend/.env."
        field = key_fields[provider]
        if not getattr(self, field):
            return f"Set {field.upper()} in backend/.env, then restart the server."
        if not self.model_name:
            return "Set MODEL_NAME in backend/.env, then restart the server."
        return ""

settings = Settings()

# Ensure uploads directory exists
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
