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
    model_name: str = Field(default="deepseek-ai/deepseek-v4-pro", description="Primary model")
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
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
    
    def has_ai_key(self) -> bool:
        """Check whether any AI provider API key is configured."""
        return bool(self.nvidia_api_key or self.openai_api_key or self.google_api_key or self.anthropic_api_key)
    
    def effective_provider(self) -> str:
        """Resolve the effective AI provider name based on configuration and available keys."""
        if self.demo_mode and not self.has_ai_key():
            return "demo"
        if self.ai_provider == "nvidia" and self.nvidia_api_key:
            return "nvidia"
        if self.ai_provider == "openai" and self.openai_api_key:
            return "openai"
        if self.ai_provider == "gemini" and self.google_api_key:
            return "gemini"
        if self.ai_provider == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        # Auto-detect from available keys
        if self.nvidia_api_key: return "nvidia"
        if self.openai_api_key: return "openai"
        if self.google_api_key: return "gemini"
        if self.anthropic_api_key: return "anthropic"
        if self.demo_mode: return "demo"
        return "demo"  # fallback

settings = Settings()

# Ensure uploads directory exists
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
