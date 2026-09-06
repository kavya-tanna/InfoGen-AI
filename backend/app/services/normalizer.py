"""
services/normalizer.py
──────────────────────
Builds ContentIntelligence from NormalizedSource via AI extraction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.ai_provider import get_provider, safe_parse_json
from app.services.ingestion import NormalizedSource
from app.utils.logging import logger


@dataclass
class ContentIntelligence:
    """Structured intelligence extracted from source content."""
    summary: str = ""
    facts: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, str]] = field(default_factory=list)
    numbers: list[dict[str, str]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    quotes: list[dict[str, str]] = field(default_factory=list)
    source_evidence: list[dict[str, str]] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Serialize to a string suitable for inclusion in prompts."""
        parts = [f"SUMMARY:\n{self.summary}"]

        if self.facts:
            facts_str = "\n".join(
                f"- {f.get('claim', '')} [confidence: {f.get('confidence', 'N/A')}]"
                for f in self.facts[:8]
            )
            parts.append(f"\nKEY FACTS:\n{facts_str}")

        if self.entities:
            ent_str = "\n".join(
                f"- {e.get('name', '')} ({e.get('type', '')}): {e.get('context', '')}"
                for e in self.entities[:8]
            )
            parts.append(f"\nENTITIES:\n{ent_str}")

        if self.timeline:
            tl_str = "\n".join(f"- {t.get('date', '')}: {t.get('event', '')}" for t in self.timeline[:5])
            parts.append(f"\nTIMELINE:\n{tl_str}")

        if self.numbers:
            num_str = "\n".join(
                f"- {n.get('value', '')}: {n.get('context', '')}" for n in self.numbers[:6]
            )
            parts.append(f"\nKEY NUMBERS:\n{num_str}")

        if self.risks:
            parts.append(f"\nRISKS:\n" + "\n".join(f"- {r}" for r in self.risks[:5]))

        if self.recommendations:
            parts.append(f"\nRECOMMENDATIONS:\n" + "\n".join(f"- {r}" for r in self.recommendations[:5]))

        if self.quotes:
            q_str = "\n".join(f'- "{q.get("text", "")}" — {q.get("attribution", "")}' for q in self.quotes[:3])
            parts.append(f"\nQUOTES:\n{q_str}")

        if self.uncertainties:
            parts.append(f"\nUNCERTAINTIES:\n" + "\n".join(f"- {u}" for u in self.uncertainties[:3]))

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "facts": self.facts,
            "entities": self.entities,
            "timeline": self.timeline,
            "numbers": self.numbers,
            "risks": self.risks,
            "recommendations": self.recommendations,
            "quotes": self.quotes,
            "source_evidence": self.source_evidence,
            "uncertainties": self.uncertainties,
        }


def _load_prompt(relative_path: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = settings.prompts_dir / relative_path
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found: {prompt_path}")
        return ""
    return prompt_path.read_text(encoding="utf-8")


def extract_content_intelligence(source: NormalizedSource) -> ContentIntelligence:
    """Extract ContentIntelligence from a NormalizedSource using instant heuristics."""
    source_text = source.raw_text.strip()

    # Pre-build instant heuristic intelligence
    lines = [line.strip() for line in source_text.splitlines() if line.strip() and len(line.strip()) > 15]
    facts = [{"claim": l[:160], "confidence": 0.9} for l in lines[:8]]
    recs = [l[:160] for l in lines[8:13]]
    import re
    numbers = []
    for match in re.finditer(r'\b\d+(?:\.\d+)?%?\b', source_text[:2000]):
        val = match.group(0)
        if len(val) <= 10 and not val.startswith("00"):
            numbers.append({"value": val, "context": source_text[max(0, match.start()-20):min(len(source_text), match.end()+20)].strip()})
        if len(numbers) >= 5:
            break

    entities = []
    for ent_match in re.finditer(r'\b[A-Z][a-zA-Z0-9_\-\.]{2,}\b', source_text[:2000]):
        ename = ent_match.group(0)
        if ename not in ["The", "And", "For", "With", "This", "Topic", "Scene", "Step"]:
            entities.append({"name": ename, "type": "term", "context": "Source entity"})
        if len(entities) >= 6:
            break

    ci = ContentIntelligence(
        summary=source_text[:800],
        facts=facts or [{"claim": source_text[:200], "confidence": 0.85}],
        entities=entities,
        numbers=numbers,
        recommendations=recs,
        uncertainties=[],
    )
    logger.info(f"Instant content intelligence ready: {len(ci.facts)} facts, {len(ci.entities)} entities")
    return ci
