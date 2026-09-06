"""
services/validator.py
─────────────────────
Output validation: schema validation, grounding checks, repair attempts.
"""
from __future__ import annotations

import re
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from app.schemas.outputs import OUTPUT_FORMAT_MAP
from app.utils.logging import logger


# ═══════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════

def validate_output(data: dict[str, Any], model_cls: Type[BaseModel]) -> tuple[BaseModel, list[str]]:
    """Validate AI output against a Pydantic schema.

    Returns (validated_model, list_of_warnings).
    Raises ValueError if validation completely fails.
    """
    warnings: list[str] = []

    try:
        result = model_cls(**data)
        return result, warnings
    except ValidationError as e:
        # Attempt repair
        logger.warning(f"Validation failed for {model_cls.__name__}, attempting repair: {e}")
        warnings.append(f"Output required repair: {str(e)[:200]}")

        repaired = _attempt_repair(data, model_cls, e)
        if repaired is not None:
            warnings.append("Output was automatically repaired")
            return repaired, warnings

        raise ValueError(f"Output validation failed for {model_cls.__name__}: {e}")


def _attempt_repair(data: dict[str, Any], model_cls: Type[BaseModel], error: ValidationError) -> BaseModel | None:
    """Try to repair common validation issues."""
    repaired_data = dict(data)

    for err in error.errors():
        field_path = err.get("loc", ())
        err_type = err.get("type", "")

        if not field_path:
            continue

        field_name = field_path[0] if field_path else ""

        # Missing required field → set default
        if err_type == "missing":
            field_info = model_cls.model_fields.get(str(field_name))
            if field_info and field_info.default is not None:
                repaired_data[str(field_name)] = field_info.default
            elif err_type == "missing":
                # Set sensible defaults based on type
                repaired_data[str(field_name)] = ""

        # Wrong type for list → wrap in list
        elif err_type == "list_type" and field_name in repaired_data:
            val = repaired_data[str(field_name)]
            if isinstance(val, str):
                repaired_data[str(field_name)] = [val]
            elif not isinstance(val, list):
                repaired_data[str(field_name)] = []

        # Wrong type for string → convert
        elif err_type == "string_type" and field_name in repaired_data:
            repaired_data[str(field_name)] = str(repaired_data[str(field_name)])

        # Wrong type for int → convert
        elif err_type == "int_type" and field_name in repaired_data:
            try:
                repaired_data[str(field_name)] = int(repaired_data[str(field_name)])
            except (ValueError, TypeError):
                repaired_data[str(field_name)] = 0

    try:
        return model_cls(**repaired_data)
    except ValidationError:
        return None


# ═══════════════════════════════════════════════════════════════════════
# GROUNDING CHECK
# ═══════════════════════════════════════════════════════════════════════

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HASH_RE = re.compile(r"\b[a-fA-F0-9]{32,64}\b")
_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|net|org|io|gov|edu|info|xyz|ru|cn|de|uk|co)\b"
)


def _extract_indicators(text: str) -> set[str]:
    """Extract CVEs, IPs, hashes, and domains from text."""
    indicators: set[str] = set()
    indicators.update(m.group().upper() for m in _CVE_RE.finditer(text))
    indicators.update(m.group() for m in _IP_RE.finditer(text))
    indicators.update(m.group().lower() for m in _HASH_RE.finditer(text))
    indicators.update(m.group().lower() for m in _DOMAIN_RE.finditer(text))
    return indicators


def check_grounding(source_text: str, generated_text: str) -> dict[str, Any]:
    """Check if generated output is grounded in source text.

    Returns a grounding report with:
    - score: 0-100% indicating IOC preservation
    - hallucinated_indicators: IOCs in output but NOT in source
    - missing_indicators: IOCs in source but NOT in output
    """
    source_iocs = _extract_indicators(source_text)
    generated_iocs = _extract_indicators(generated_text)

    if not source_iocs and not generated_iocs:
        return {"score": 100.0, "hallucinated_indicators": [], "missing_indicators": [], "status": "clean"}

    # Hallucinated = in generated but NOT in source
    hallucinated = generated_iocs - source_iocs
    # Missing = in source but NOT in generated (not necessarily bad)
    missing = source_iocs - generated_iocs

    if not source_iocs:
        # No source IOCs; check if output invented any
        score = 0.0 if hallucinated else 100.0
    else:
        preserved = source_iocs & generated_iocs
        score = round(len(preserved) / len(source_iocs) * 100, 1)

    result = {
        "score": score,
        "hallucinated_indicators": sorted(hallucinated),
        "missing_indicators": sorted(missing),
        "source_ioc_count": len(source_iocs),
        "generated_ioc_count": len(generated_iocs),
        "status": "warning" if hallucinated else "clean",
    }

    if hallucinated:
        logger.warning(f"Grounding check: {len(hallucinated)} potentially hallucinated indicators detected")

    return result
