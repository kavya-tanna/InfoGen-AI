"""
core_engine.py
──────────────
Domain models (Pydantic v2), text extraction, LLM transformation chains,
and fact-checking / grounding-score utilities for the Gen AI Content
Transformation platform.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# ── LangChain ───────────────────────────────────────────────────────────
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════
# 1.  PYDANTIC  DOMAIN  MODELS
# ═══════════════════════════════════════════════════════════════════════

class MasterContext(BaseModel):
    """Canonical intermediate representation extracted from raw source."""
    title: str = ""
    summary: str = ""
    entities: list[str] = Field(default_factory=list)
    cve_iocs: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    severity: str = "UNKNOWN"


class AdvisoryArtifact(BaseModel):
    title: str = ""
    severity: str = "UNKNOWN"
    date: str = ""
    summary: str = ""
    iocs: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


class ExecSummaryArtifact(BaseModel):
    title: str = ""
    audience: str = "Executive"
    summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    business_impact: str = ""
    recommended_actions: list[str] = Field(default_factory=list)


class SlideItem(BaseModel):
    title: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    speaker_notes: str = ""


class SlidesArtifact(BaseModel):
    slides: list[SlideItem] = Field(default_factory=list)


class StoryboardScene(BaseModel):
    scene_number: int = 1
    visual_description: str = ""
    narration: str = ""
    duration_seconds: float = 5.0


class VideoStoryboardArtifact(BaseModel):
    title: str = ""
    scenes: list[StoryboardScene] = Field(default_factory=list)


class SocialPostItem(BaseModel):
    platform: str = "Twitter/X"
    content: str = ""
    hashtags: list[str] = Field(default_factory=list)


class SocialPostsArtifact(BaseModel):
    posts: list[SocialPostItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# 2.  TEXT  EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

def extract_text(file_bytes: bytes, file_name: str) -> str:
    """Return plain-text from .txt, .docx, or .pdf uploads."""
    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".txt":
        return file_bytes.decode("utf-8", errors="replace")

    if ext == ".docx":
        import docx
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            doc = docx.Document(tmp_path)
            return "\n".join(p.text for p in doc.paragraphs)
        finally:
            os.unlink(tmp_path)

    if ext == ".pdf":
        import fitz  # PyMuPDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            text_parts: list[str] = []
            with fitz.open(tmp_path) as pdf:
                for page in pdf:
                    text_parts.append(page.get_text())
            return "\n".join(text_parts)
        finally:
            os.unlink(tmp_path)

    raise ValueError(f"Unsupported file type: {ext}")


# ═══════════════════════════════════════════════════════════════════════
# 3.  LLM  HELPER
# ═══════════════════════════════════════════════════════════════════════

def _get_llm():
    """Return the best available LangChain chat model.

    Priority: Google Gemini (free) → OpenAI → Anthropic.
    Raises RuntimeError when no key found.
    """
    google_key = os.getenv("GOOGLE_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if google_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            temperature=0.3,
            google_api_key=google_key,
        )
    if openai_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=openai_key)
    if anthropic_key:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.3, api_key=anthropic_key)
    raise RuntimeError(
        "No LLM API key found. Set GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in your .env file."
    )


# ═══════════════════════════════════════════════════════════════════════
# 4.  TRANSFORMATION  CHAINS
# ═══════════════════════════════════════════════════════════════════════

_MASTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert cyber-defense intelligence analyst.  "
            "Extract structured intelligence from the source text below.  "
            "Return ONLY valid JSON matching the schema – no markdown fences, no commentary.\n\n"
            "Schema:\n"
            '{{"title": "...", "summary": "...", "entities": ["..."], '
            '"cve_iocs": ["CVE-...", "IP/hash/domain..."], '
            '"actions": ["..."], "severity": "CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN"}}',
        ),
        ("human", "SOURCE TEXT:\n{source_text}"),
    ]
)

_ARTIFACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a cyber-defense content transformation engine.\n"
            "AUDIENCE : {audience}\n"
            "TONE     : {tone}\n"
            "ARTIFACT : {artifact_type}\n\n"
            "Using the master context below, produce the requested artifact.  "
            "Return ONLY valid JSON matching the schema – no markdown fences, no commentary.\n\n"
            "SCHEMA:\n{schema}\n\n"
            "RULES:\n"
            "- Preserve every CVE ID, IP address, hash, and domain from the source.\n"
            "- Do NOT invent data not present in the source.\n"
            "- Tailor depth and vocabulary to the audience.\n",
        ),
        ("human", "MASTER CONTEXT:\n{master_json}"),
    ]
)

# Map artifact type name → (Pydantic model, JSON schema string)
_ARTIFACT_REGISTRY: dict[str, tuple[type[BaseModel], str]] = {
    "Advisory": (AdvisoryArtifact, AdvisoryArtifact.model_json_schema().__repr__()),
    "Exec Summary": (ExecSummaryArtifact, ExecSummaryArtifact.model_json_schema().__repr__()),
    "PPT Deck": (SlidesArtifact, SlidesArtifact.model_json_schema().__repr__()),
    "Video Storyboard": (VideoStoryboardArtifact, VideoStoryboardArtifact.model_json_schema().__repr__()),
    "Social Posts": (SocialPostsArtifact, SocialPostsArtifact.model_json_schema().__repr__()),
}


def _safe_parse_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON, with fallback."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    return json.loads(cleaned)


def extract_master_context(source_text: str) -> MasterContext:
    """Run the extraction chain and return a MasterContext."""
    llm = _get_llm()
    chain = _MASTER_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({"source_text": source_text[:12000]})  # trim for context window
    data = _safe_parse_json(raw)
    return MasterContext(**data)


def transform_artifact(
    master: MasterContext,
    artifact_type: str,
    audience: str = "Analyst",
    tone: str = "Authoritative",
) -> BaseModel:
    """Generate a single artifact from the master context."""
    model_cls, schema_str = _ARTIFACT_REGISTRY[artifact_type]
    llm = _get_llm()
    chain = _ARTIFACT_PROMPT | llm | StrOutputParser()
    raw = chain.invoke(
        {
            "audience": audience,
            "tone": tone,
            "artifact_type": artifact_type,
            "schema": schema_str,
            "master_json": master.model_dump_json(),
        }
    )
    data = _safe_parse_json(raw)
    return model_cls(**data)


# ═══════════════════════════════════════════════════════════════════════
# 5.  FACT-CHECK  /  GROUNDING  SCORE
# ═══════════════════════════════════════════════════════════════════════

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
_IP_RE  = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HASH_RE = re.compile(r"\b[a-fA-F0-9]{32,64}\b")
_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|gov|edu|info|xyz|ru|cn|de|uk|co)\b"
)


def _extract_indicators(text: str) -> set[str]:
    """Pull CVEs, IPs, hashes, and domains from arbitrary text."""
    indicators: set[str] = set()
    indicators.update(m.group().upper() for m in _CVE_RE.finditer(text))
    indicators.update(m.group() for m in _IP_RE.finditer(text))
    indicators.update(m.group().lower() for m in _HASH_RE.finditer(text))
    indicators.update(m.group().lower() for m in _DOMAIN_RE.finditer(text))
    return indicators


def compute_grounding_score(source_text: str, generated_text: str) -> float:
    """Return 0-100 % indicating how many source IOCs are preserved in output."""
    source_iocs = _extract_indicators(source_text)
    if not source_iocs:
        return 100.0  # nothing to verify
    generated_iocs = _extract_indicators(generated_text)
    matched = source_iocs & generated_iocs
    return round(len(matched) / len(source_iocs) * 100, 1)


def compute_entity_grounding(source_text: str, generated_text: str) -> float:
    """Supplementary check: what fraction of capitalised named entities
    from the source appear in the generated text?"""
    # Simple heuristic: 2+ word capitalised sequences
    entity_re = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
    source_ents = set(entity_re.findall(source_text))
    if not source_ents:
        return 100.0
    gen_lower = generated_text.lower()
    matched = sum(1 for e in source_ents if e.lower() in gen_lower)
    return round(matched / len(source_ents) * 100, 1)


def overall_grounding(source_text: str, generated_text: str) -> float:
    """Weighted average of IOC grounding (60 %) and entity grounding (40 %)."""
    ioc_score = compute_grounding_score(source_text, generated_text)
    ent_score = compute_entity_grounding(source_text, generated_text)
    return round(ioc_score * 0.6 + ent_score * 0.4, 1)
