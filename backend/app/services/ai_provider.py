"""
services/ai_provider.py
───────────────────────
AI provider abstraction layer.
Supports: NVIDIA NIM, OpenAI, Google Gemini, Anthropic, Demo (mock).
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from app.config import settings
from app.utils.logging import logger


class AIProvider(ABC):
    """Abstract base for AI providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
        """Generate text completion. Returns raw string response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


# ═══════════════════════════════════════════════════════════════════════
# NVIDIA NIM PROVIDER (OpenAI-compatible API)
# ═══════════════════════════════════════════════════════════════════════

class NvidiaProvider(AIProvider):
    """NVIDIA NIM provider using OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, model: str = "meta/llama-3.2-11b-vision-instruct"):
        from openai import OpenAI
        self._client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            timeout=float(settings.ai_timeout_seconds),
            max_retries=0,
        )
        self._model = model
        self._fallback_models = []
        logger.info(f"NVIDIA NIM provider initialized: model={model}")

    @property
    def name(self) -> str:
        return "nvidia"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout_seconds: float | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Try primary model, then fallbacks
        models_to_try = [self._model] + [m for m in self._fallback_models if m != self._model]

        last_err = None
        for m in models_to_try:
            try:
                logger.info(f"Calling NVIDIA NIM with model: {m}")
                response = self._client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=6000,
                    timeout=timeout_seconds or float(settings.ai_timeout_seconds),
                    response_format={"type": "json_object"},
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}} if "nemotron" in m else {},
                )
                if response.choices[0].finish_reason == "length":
                    raise ValueError("The model response exceeded the output token limit.")
                content = response.choices[0].message.content or ""
                # Strip thinking blocks if model emitted them
                content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                logger.info(f"NVIDIA generation complete: {len(content)} chars with model={m}")
                return content
            except Exception as e:
                last_err = e
                err_str = str(e)
                logger.warning("NVIDIA request failed: %s (%s)", type(e).__name__, err_str[:120])
                if "429" in err_str or "Too Many Requests" in err_str or "RateLimit" in type(e).__name__:
                    import time
                    logger.info("NVIDIA rate limit encountered, backing off for 2.0s...")
                    time.sleep(2.0)
                    try:
                        response = self._client.chat.completions.create(
                            model=m,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=6000,
                            timeout=timeout_seconds or float(settings.ai_timeout_seconds),
                            response_format={"type": "json_object"},
                            extra_body={"chat_template_kwargs": {"enable_thinking": False}} if "nemotron" in m else {},
                        )
                        content = response.choices[0].message.content or ""
                        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                        logger.info(f"NVIDIA generation complete after retry: {len(content)} chars with model={m}")
                        return content
                    except Exception as retry_err:
                        last_err = retry_err
                        logger.warning("NVIDIA retry failed: %s", type(retry_err).__name__)

        raise RuntimeError("NVIDIA request failed. Check the configured model, credentials and provider availability.") from last_err


# ═══════════════════════════════════════════════════════════════════════
# OPENAI PROVIDER
# ═══════════════════════════════════════════════════════════════════════

class OpenAIProvider(AIProvider):
    """OpenAI provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, timeout=35.0, max_retries=0)
        self._model = model
        logger.info(f"OpenAI provider initialized: model={model}")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=8192,
        )
        return response.choices[0].message.content or ""


# ═══════════════════════════════════════════════════════════════════════
# GEMINI PROVIDER
# ═══════════════════════════════════════════════════════════════════════

class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str, model: str = "gemini-3.6-flash"):
        from openai import OpenAI
        self._client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key,
            timeout=float(settings.ai_timeout_seconds),
            max_retries=0,
        )
        self._model = model
        logger.info(f"Gemini provider initialized: model={model}")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3, timeout_seconds: float | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=8192,
            timeout=timeout_seconds or float(settings.ai_timeout_seconds),
            response_format={"type": "json_object"},
            reasoning_effort="none" if self._model.startswith("gemini-2.5-flash") else "low",
        )
        if not response.choices or response.choices[0].finish_reason == "length":
            raise ValueError("Gemini returned an incomplete response.")
        return response.choices[0].message.content or ""


# ═══════════════════════════════════════════════════════════════════════
# ANTHROPIC PROVIDER
# ═══════════════════════════════════════════════════════════════════════

class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key, timeout=35.0, max_retries=0)
        self._model = model
        logger.info(f"Anthropic provider initialized: model={model}")

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._client.messages.create(**kwargs)
        text_parts = [block.text for block in response.content if hasattr(block, "text")]
        return "\n".join(text_parts)


# ═══════════════════════════════════════════════════════════════════════
# DEMO PROVIDER (deterministic mock output)
# ═══════════════════════════════════════════════════════════════════════

class DemoProvider(AIProvider):
    """Explicit offline mode; the generator builds excerpts from the real source."""

    @property
    def name(self) -> str:
        return "demo"

    @property
    def model_name(self) -> str:
        return "extractive-v1"

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
        raise RuntimeError("Offline generation requires source passages through build_grounded().")

# ═══════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════

_provider_instance: AIProvider | None = None
_fallback_instance: AIProvider | None = None


def get_fallback_provider(primary_name: str) -> AIProvider | None:
    """An explicit Gemini fallback; never auto-switch models or expose keys."""
    global _fallback_instance
    if (settings.demo_mode or settings.ai_provider == "demo" or primary_name == "gemini"
            or settings.fallback_provider != "gemini" or not settings.google_api_key):
        return None
    if _fallback_instance is None:
        _fallback_instance = GeminiProvider(settings.google_api_key, settings.gemini_model_name)
    return _fallback_instance


def get_provider() -> AIProvider:
    """Get or create the AI provider based on configuration."""
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    effective = settings.effective_provider()
    if effective != "demo" and not settings.model_name:
        raise ValueError("Set MODEL_NAME in backend/.env to enable the selected AI provider.")
    logger.info(f"Initializing AI provider: {effective}")

    if effective == "nvidia":
        _provider_instance = NvidiaProvider(
            api_key=settings.nvidia_api_key,
            model=settings.model_name,
        )
    elif effective == "openai":
        _provider_instance = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.model_name or "gpt-4o-mini",
        )
    elif effective == "gemini":
        _provider_instance = GeminiProvider(
            api_key=settings.google_api_key,
            model=settings.model_name or "gemini-2.0-flash",
        )
    elif effective == "anthropic":
        _provider_instance = AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.model_name or "claude-sonnet-4-20250514",
        )
    else:
        _provider_instance = DemoProvider()

    return _provider_instance


def reset_provider() -> None:
    """Reset cached provider (useful for testing)."""
    global _provider_instance, _fallback_instance
    _provider_instance = None
    _fallback_instance = None


def safe_parse_json(raw: str) -> dict:
    """Parse JSON from AI response, stripping markdown fences if present."""
    cleaned = raw.strip()
    # Check if there is a ```json ... ``` block anywhere in the text
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Remove edge markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse JSON from AI response: {cleaned[:200]}...")
