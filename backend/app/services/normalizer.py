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
    title: str = ""
    content_type: str = "Free-form Text"
    source_text: str = ""
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
    """Extract source passages; do not infer recommendations from line positions."""
    import re
    text = source.raw_text.strip()
    passages = [p.strip() for p in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z])", text) if p.strip()]
    passages = list(dict.fromkeys(passages))
    title = source.metadata.get("title") or passages[0][:120]
    facts = [{"claim": p, "evidence": p} for p in passages
             if len(p) > 25 and p != passages[0]
             and not re.match(r"(synthetic |this is a fictional|date:|all times)", p, re.I)][:24]
    if not facts:
        facts = [{"claim": p, "evidence": p} for p in passages if len(p) > 15]
    recommendations = [p for p in passages if re.search(
        r"\b(recommend\w*|mitigation|remediation|should|must|action[s]?|patch|upgrade|disable)\b", p, re.I)]
    risks = [p for p in passages if re.search(
        r"\b(risk[s]?|impact|limitation[s]?|vulnerab\w*|outage|root cause|affected)\b", p, re.I)]
    # Only explicit measured quantities become statistics, not dates, CVEs or versions.
    numbers = []
    for p in passages:
        for m in re.finditer(r"\b\d+(?:\.\d+)?(?:%|\s+(?:users|minutes|hours|participants|devices|schools|records|incidents|accounts))(?=\s|[.,;:]|$)", p, re.I):
            numbers.append({"value": m.group(), "context": p})
    return ContentIntelligence(
        title=title,
        content_type=source.metadata.get("content_type", "Free-form Text"),
        source_text=text,
        summary=" ".join(p["claim"] for p in facts[:3]) or text,
        facts=facts,
        numbers=numbers[:6],
        recommendations=recommendations[:6],
        risks=risks[:6],
        source_evidence=[{"text": p["claim"]} for p in facts],
        uncertainties=["Information absent from the supplied source is unavailable. "
                       "Source statements have not been independently verified."],
    )
