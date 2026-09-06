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
            timeout=35.0,
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

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
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
                    max_tokens=2200,
                )
                content = response.choices[0].message.content or ""
                # Strip thinking blocks if model emitted them
                content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                logger.info(f"NVIDIA generation complete: {len(content)} chars with model={m}")
                return content
            except Exception as e:
                last_err = e
                logger.warning(f"NVIDIA model {m} failed or timed out: {e}. Trying fallback...")

        raise RuntimeError(f"All NVIDIA NIM models failed. Last error: {last_err}")


# ═══════════════════════════════════════════════════════════════════════
# OPENAI PROVIDER
# ═══════════════════════════════════════════════════════════════════════

class OpenAIProvider(AIProvider):
    """OpenAI provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
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

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        from openai import OpenAI
        self._client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key,
        )
        self._model = model
        logger.info(f"Gemini provider initialized: model={model}")

    @property
    def name(self) -> str:
        return "gemini"

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
# ANTHROPIC PROVIDER
# ═══════════════════════════════════════════════════════════════════════

class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
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
    """Deterministic mock provider for demo/testing when no API key is configured."""

    @property
    def name(self) -> str:
        return "demo"

    @property
    def model_name(self) -> str:
        return "demo-mock-v1"

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
        logger.info("DemoProvider: generating mock output")

        # Detect which output format is being requested
        prompt_lower = prompt.lower()

        if "video" in prompt_lower and "scene" in prompt_lower:
            return json.dumps({
                "type": "video_package",
                "title": "InfoGen AI Demo — Video Package",
                "objective": "Demonstrate video package generation capability",
                "target_audience": "General",
                "duration_seconds": 60,
                "script": "This is a demonstration of the InfoGen AI video generation pipeline. The system extracts key information from your source content and structures it into a production-ready video package with narration, visual prompts, and subtitle data.",
                "scenes": [
                    {"scene_number": 1, "start_time": "00:00", "end_time": "00:15", "title": "Introduction", "narration": "Welcome to this briefing generated by InfoGen AI.", "visual": "Title card with clean typography and brand colors", "camera": "Static wide shot", "on_screen_text": "InfoGen AI — Content Intelligence"},
                    {"scene_number": 2, "start_time": "00:15", "end_time": "00:35", "title": "Key Findings", "narration": "The source content has been analyzed and key findings extracted for your target audience.", "visual": "Animated infographic showing key data points", "camera": "Slow zoom with metric overlays", "on_screen_text": "Key Intelligence Findings"},
                    {"scene_number": 3, "start_time": "00:35", "end_time": "00:50", "title": "Analysis", "narration": "Our analysis highlights the most critical elements requiring attention.", "visual": "Split-screen comparison with highlighted sections", "camera": "Pan across data visualization", "on_screen_text": "Critical Analysis"},
                    {"scene_number": 4, "start_time": "00:50", "end_time": "01:00", "title": "Call to Action", "narration": "Connect your API key to see real AI-generated content from your source material.", "visual": "Clean closing frame with CTA", "camera": "Static closing shot", "on_screen_text": "Get Started — Configure Your API Key"},
                ],
                "vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:15.000\nWelcome to this briefing generated by InfoGen AI.\n\n00:00:15.000 --> 00:00:35.000\nThe source content has been analyzed and key findings extracted.\n\n00:00:35.000 --> 00:00:50.000\nOur analysis highlights the most critical elements.\n\n00:00:50.000 --> 00:01:00.000\nConnect your API key to see real AI-generated content.",
                "cta": "Configure your API key to unlock real AI generation.",
                "production_notes": "[DEMO MODE] This is mock output. Configure NVIDIA_API_KEY in .env for real generation."
            })

        if "linkedin" in prompt_lower:
            return json.dumps({
                "type": "linkedin_post",
                "hook": "🔍 Just processed critical intelligence through InfoGen AI — here's what every professional needs to know:",
                "post": "The future of content transformation is here.\n\nInfoGen AI takes a single source — whether it's a threat report, news article, research paper, or raw data — and transforms it into 7 different communication formats simultaneously.\n\n✅ Video Packages\n✅ Advisory Documents\n✅ Executive Summaries\n✅ Presentation Decks\n✅ Social Media Posts\n✅ Infographics\n\nAll from ONE source. All factually consistent. All audience-tailored.\n\nThis is what source-grounded AI looks like in practice.\n\n[DEMO MODE — Connect your API key for real content generation]",
                "key_insights": ["Multi-format content generation from single source", "Source-grounded AI prevents hallucination", "Audience-adaptive output customization", "7 simultaneous deliverable formats"],
                "cta": "Try InfoGen AI with your own content →",
                "hashtags": ["#AIContentTransformation", "#InfoGenAI", "#ContentIntelligence", "#GenerativeAI", "#SIH2024"],
                "carousel_slides": [
                    {"slide_number": 1, "headline": "One Source → Seven Formats", "body": "Transform any content into multiple deliverables simultaneously"},
                    {"slide_number": 2, "headline": "Source-Grounded AI", "body": "Every claim traces back to your original content — zero hallucination"},
                    {"slide_number": 3, "headline": "Audience-Adaptive", "body": "Tailor tone, detail level, and language for any audience"},
                    {"slide_number": 4, "headline": "Get Started", "body": "Configure your API key and transform your first source today"}
                ]
            })

        if "twitter" in prompt_lower or "x post" in prompt_lower:
            return json.dumps({
                "type": "twitter_post",
                "primary_post": "🚀 InfoGen AI transforms ONE source into 7 deliverables simultaneously — video, advisory, exec summary, slides, social posts, infographics. All source-grounded. Zero hallucination. #InfoGenAI #AI",
                "thread": [
                    "1/ The problem: You have critical intel, but need it in 7 different formats for 7 different audiences. Manual reformatting takes hours.",
                    "2/ The solution: InfoGen AI extracts structured intelligence from your source and generates all formats from the SAME grounded context.",
                    "3/ Key features: ✅ Multi-modal ingestion (PDF, DOCX, text, URL) ✅ 7 output formats ✅ Source grounding ✅ Multi-language support",
                    "4/ Built for SIH 2024 — and ready for production. Try it with your own content today. [DEMO MODE]"
                ],
                "key_indicators": ["7 output formats", "Source-grounded generation", "Multi-modal input", "5 languages supported"],
                "cta": "Connect your API key to generate real content →",
                "hashtags": ["#InfoGenAI", "#AI", "#ContentTransformation", "#SIH2024", "#GenerativeAI"]
            })

        if "advisory" in prompt_lower:
            return json.dumps({
                "type": "advisory_document",
                "title": "InfoGen AI — Demo Advisory Document",
                "severity": "INFORMATIONAL",
                "executive_overview": "This is a demonstration advisory generated by InfoGen AI in demo mode. Connect an API key (NVIDIA NIM, OpenAI, Gemini, or Anthropic) to generate real advisory documents from your source content.",
                "affected_systems": ["Not available in source."],
                "threat_description": "No threat data available — this is a demo output. Real advisory generation extracts threat intelligence directly from your source material.",
                "indicators": ["Not available in source."],
                "impact": "Demo mode — no real impact assessment available.",
                "technical_analysis": "Technical analysis requires real source content and an AI provider.",
                "risk_assessment": "Risk assessment requires real source content.",
                "immediate_actions": ["Configure your AI provider API key in .env", "Provide real source content for analysis"],
                "mitigation": ["Enable real AI generation by setting NVIDIA_API_KEY"],
                "long_term_recommendations": ["Integrate with your threat intelligence feeds", "Configure automated advisory generation"],
                "references": ["InfoGen AI Documentation"],
                "confidence_level": "LOW"
            })

        if "infographic" in prompt_lower:
            return json.dumps({
                "type": "infographic",
                "title": "InfoGen AI — Content Intelligence at a Glance",
                "subtitle": "Transform any source into 7 deliverables",
                "key_statistics": [
                    {"value": "7", "label": "Output Formats", "source_reference": "Platform specification"},
                    {"value": "5", "label": "Languages Supported", "source_reference": "Platform specification"},
                    {"value": "6", "label": "Audience Profiles", "source_reference": "Platform specification"}
                ],
                "key_messages": ["One source, many outputs", "Source-grounded AI", "Zero hallucination"],
                "sections": [
                    {"section_title": "Input", "content": "PDF, DOCX, TXT, URL, Image, Audio, Video", "visual_element": "icon", "data_points": ["Multi-modal ingestion"]},
                    {"section_title": "Processing", "content": "Content Intelligence extraction and normalization", "visual_element": "diagram", "data_points": ["Entity extraction", "Fact verification"]},
                    {"section_title": "Output", "content": "7 simultaneous deliverable formats", "visual_element": "metric_card", "data_points": ["Video", "LinkedIn", "Twitter", "Advisory", "Infographic", "Summary", "Deck"]}
                ],
                "information_hierarchy": ["Input Sources", "AI Processing", "Output Deliverables"],
                "layout": "Vertical flow with three main sections connected by arrows",
                "color_recommendations": {"primary": "#26354a", "secondary": "#50627a", "accent": "#5b7cfa", "rationale": "Professional, trustworthy palette matching the InfoGen AI brand"},
                "icon_recommendations": ["Document icon for input", "Brain/AI icon for processing", "Grid icon for outputs"]
            })

        if "executive" in prompt_lower or "summary" in prompt_lower:
            return json.dumps({
                "type": "executive_summary",
                "headline": "InfoGen AI — Demo Executive Summary",
                "key_takeaways": [
                    "This is a demonstration output from InfoGen AI running in demo mode",
                    "Connect an AI provider API key to generate real executive summaries",
                    "The platform supports 7 output formats from a single source",
                    "All outputs are source-grounded to prevent hallucination"
                ],
                "context": "InfoGen AI is a Gen AI platform for automated content transformation. This demo output demonstrates the structure and format of executive summaries generated by the platform.",
                "major_findings": ["Multi-format generation from single source is operational", "Source grounding architecture prevents hallucinated content"],
                "business_impact": "Reduces content creation time for multi-channel communication by automating the transformation of raw intelligence into audience-tailored deliverables.",
                "risks": ["Demo mode provides mock output — configure API key for real intelligence"],
                "decisions_required": ["Select and configure an AI provider (NVIDIA NIM recommended)"],
                "recommended_actions": [{"action": "Configure NVIDIA_API_KEY in .env file", "priority": "HIGH", "timeline": "immediate"}, {"action": "Test with real source content", "priority": "HIGH", "timeline": "immediate"}],
                "priority": "MEDIUM",
                "conclusion": "InfoGen AI demonstrates a functional content transformation pipeline. Configure an AI provider to unlock full capabilities."
            })

        if "presentation" in prompt_lower or "slide" in prompt_lower:
            return json.dumps({
                "type": "presentation_deck",
                "title": "InfoGen AI — Demo Presentation",
                "slides": [
                    {"slide_number": 1, "title": "InfoGen AI", "purpose": "Title slide", "key_points": ["Gen AI Platform for Automated Content Transformation"], "body_content": "Transform raw content into powerful communication deliverables", "visual_recommendation": "Clean title card with brand logo", "speaker_notes": "Welcome everyone. Today I'll demonstrate InfoGen AI."},
                    {"slide_number": 2, "title": "The Problem", "purpose": "Context setting", "key_points": ["Manual content reformatting is time-consuming", "Multiple audiences need different formats", "Consistency across channels is difficult"], "body_content": "Organizations need to communicate the same intelligence across multiple channels and audiences.", "visual_recommendation": "Pain point diagram showing fragmented communication", "speaker_notes": "Organizations face a critical challenge..."},
                    {"slide_number": 3, "title": "Our Solution", "purpose": "Solution overview", "key_points": ["One source, seven outputs", "Source-grounded AI", "Audience-adaptive generation"], "body_content": "InfoGen AI processes any source once and generates all deliverables from the same grounded context.", "visual_recommendation": "Architecture flow diagram", "speaker_notes": "InfoGen AI solves this with a unified pipeline..."},
                    {"slide_number": 4, "title": "Demo", "purpose": "Live demonstration", "key_points": ["Configure API key to see real generation", "Multi-modal input supported", "Real-time content transformation"], "body_content": "[DEMO MODE] Connect your AI provider to see real output.", "visual_recommendation": "Live demo screenshot", "speaker_notes": "Let me show you the platform in action..."},
                    {"slide_number": 5, "title": "Next Steps", "purpose": "Call to action", "key_points": ["Configure NVIDIA NIM API key", "Test with real content", "Deploy for production use"], "body_content": "Get started by configuring your API key and providing real source content.", "visual_recommendation": "Clean CTA slide", "speaker_notes": "To get started, you need to configure your API key..."}
                ]
            })

        # Generic fallback
        return json.dumps({
            "type": "generic",
            "title": "Demo Output",
            "content": "This is a demo output from InfoGen AI. Configure an AI provider (NVIDIA_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY) in your .env file to generate real content.",
            "note": "[DEMO MODE] No API key configured."
        })


# ═══════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════

_provider_instance: AIProvider | None = None


def get_provider() -> AIProvider:
    """Get or create the AI provider based on configuration."""
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    effective = settings.effective_provider()
    logger.info(f"Initializing AI provider: {effective}")

    if effective == "nvidia":
        _provider_instance = NvidiaProvider(
            api_key=settings.nvidia_api_key,
            model=settings.model_name,
        )
    elif effective == "openai":
        _provider_instance = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.model_name if "gpt" in settings.model_name else "gpt-4o-mini",
        )
    elif effective == "gemini":
        _provider_instance = GeminiProvider(
            api_key=settings.google_api_key,
            model=settings.model_name if "gemini" in settings.model_name else "gemini-2.0-flash",
        )
    elif effective == "anthropic":
        _provider_instance = AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.model_name if "claude" in settings.model_name else "claude-sonnet-4-20250514",
        )
    else:
        _provider_instance = DemoProvider()

    return _provider_instance


def reset_provider() -> None:
    """Reset cached provider (useful for testing)."""
    global _provider_instance
    _provider_instance = None


def safe_parse_json(raw: str) -> dict:
    """Parse JSON from AI response, stripping markdown fences if present."""
    cleaned = raw.strip()
    # Remove markdown code fences
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
