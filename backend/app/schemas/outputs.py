"""Pydantic v2 schemas for all 7 output deliverable formats."""
from __future__ import annotations
import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from typing import Literal

class DeliverableOutput(BaseModel):
    generation_mode: str = "ai"
    provider: str = ""
    model: str = ""
    warnings: list[str] = Field(default_factory=list)

# ── Video Package ──
class VideoScene(BaseModel):
    """Scene detail for video package script."""
    scene_number: int = 1
    start_time: str = "00:00"
    end_time: str = "00:15"
    title: str = ""
    narration: str = ""
    visual: str = ""
    camera: str = ""
    on_screen_text: str = ""

class VideoPackageOutput(DeliverableOutput):
    """Complete video package deliverable schema."""
    type: str = "video_package"
    title: str = ""
    objective: str = ""
    target_audience: str = ""
    duration_seconds: int = 90
    script: str = ""
    scenes: list[VideoScene] = Field(default_factory=list)
    vtt: str = ""
    cta: str = ""
    production_notes: str = ""

# ── LinkedIn Post ──
class CarouselSlide(BaseModel):
    """Slide specification for LinkedIn carousel."""
    slide_number: int = 1
    headline: str = ""
    body: str = ""

class LinkedInPostOutput(DeliverableOutput):
    """LinkedIn post deliverable schema."""
    type: str = "linkedin_post"
    hook: str = ""
    post: str = ""
    key_insights: list[str] = Field(default_factory=list)
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)
    carousel_slides: list[CarouselSlide] = Field(default_factory=list)

    @field_validator("post", mode="before")
    @classmethod
    def coerce_linkedin_post(cls, v):
        return str(v) if v is not None else ""

    @field_validator("hashtags", mode="before")
    @classmethod
    def coerce_hashtags(cls, v):
        if isinstance(v, str):
            tags = re.findall(r"#\w+", v)
            if tags:
                return tags
            return [t.strip() for t in v.split(",") if t.strip()]
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

    @field_validator("key_insights", mode="before")
    @classmethod
    def coerce_key_insights(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            return [v_str] if v_str else []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

# ── Twitter / X Post ──
class TwitterPostOutput(DeliverableOutput):
    """Twitter / X post and thread deliverable schema."""
    type: str = "twitter_post"
    primary_post: str = ""
    thread: list[str] = Field(default_factory=list)
    key_indicators: list[str] = Field(default_factory=list)
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)

    @field_validator("primary_post", mode="before")
    @classmethod
    def coerce_primary_post(cls, v):
        return str(v) if v is not None else ""

    @field_validator("thread", "key_indicators", "hashtags", mode="before")
    @classmethod
    def coerce_twitter_lists(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            return [v_str] if v_str else []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

# ── Advisory Document ──
class AdvisoryDocumentOutput(DeliverableOutput):
    """Formal cybersecurity advisory document deliverable schema."""
    type: str = "advisory_document"
    document_kind: Literal["security", "informational"] = "informational"
    title: str = ""
    severity: str = "INFORMATIONAL"
    executive_overview: str = ""
    affected_systems: list[str] = Field(default_factory=list)
    threat_description: str = ""
    indicators: list[str] = Field(default_factory=list)
    impact: str = ""
    technical_analysis: str = ""
    risk_assessment: str = ""
    immediate_actions: list[str] = Field(default_factory=list)
    mitigation: list[str] = Field(default_factory=list)
    long_term_recommendations: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    confidence_level: str = "UNSPECIFIED"

    @field_validator("affected_systems", "indicators", "immediate_actions", "mitigation", "long_term_recommendations", "references", mode="before")
    @classmethod
    def coerce_advisory_lists(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            return [v_str] if v_str else []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

    @field_validator("executive_overview", "threat_description", "impact", "technical_analysis", "risk_assessment", mode="before")
    @classmethod
    def coerce_advisory_strings(cls, v):
        if isinstance(v, list):
            return " ".join(str(x) for x in v if x)
        return str(v) if v is not None else ""

# ── Infographic ──
class InfographicStatistic(BaseModel):
    """Data statistic callout in infographic."""
    value: str = ""
    label: str = ""
    source_reference: str = ""

class InfographicSection(BaseModel):
    """Section breakdown for visual infographic."""
    section_title: str = ""
    content: str = ""
    visual_element: str = "icon"  # chart|icon|diagram|metric_card|timeline|comparison
    data_points: list[str] = Field(default_factory=list)

    @field_validator("data_points", mode="before")
    @classmethod
    def coerce_data_points(cls, v):
        if not isinstance(v, list):
            return []
        res = []
        for item in v:
            if isinstance(item, dict):
                res.append(" | ".join(f"{k}: {val}" for k, val in item.items() if val))
            elif item is not None:
                res.append(str(item))
        return res

class ColorRecommendation(BaseModel):
    """Color palette recommendation for visual infographic."""
    primary: str = "#1a365d"
    secondary: str = "#2d3748"
    accent: str = "#3182ce"
    rationale: str = ""

class InfographicOutput(DeliverableOutput):
    """Infographic deliverable design specification schema."""
    type: str = "infographic"
    title: str = ""
    subtitle: str = ""
    key_statistics: list[InfographicStatistic] = Field(default_factory=list)
    key_messages: list[str] = Field(default_factory=list)
    sections: list[InfographicSection] = Field(default_factory=list)
    information_hierarchy: list[str] = Field(default_factory=list)
    layout: str = ""
    color_recommendations: ColorRecommendation = Field(default_factory=ColorRecommendation)
    icon_recommendations: list[str] = Field(default_factory=list)

    @field_validator("icon_recommendations", mode="before")
    @classmethod
    def coerce_icon_recommendations(cls, v):
        if not isinstance(v, list):
            return []
        res = []
        for item in v:
            if isinstance(item, dict):
                res.append(" | ".join(f"{k}: {val}" for k, val in item.items() if val))
            elif item is not None:
                res.append(str(item))
        return res

    @field_validator("information_hierarchy", "key_messages", mode="before")
    @classmethod
    def coerce_infographic_lists(cls, v):
        if isinstance(v, str):
            if ">" in v:
                return [s.strip() for s in v.split(">") if s.strip()]
            if "," in v:
                return [s.strip() for s in v.split(",") if s.strip()]
            v_str = v.strip()
            return [v_str] if v_str else []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

    @field_validator("color_recommendations", mode="before")
    @classmethod
    def coerce_color_recommendations(cls, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            hexes = re.findall(r"#[0-9a-fA-F]{3,8}", v)
            return {
                "primary": hexes[0] if len(hexes) > 0 else "#1a365d",
                "secondary": hexes[1] if len(hexes) > 1 else "#2d3748",
                "accent": hexes[2] if len(hexes) > 2 else "#3182ce",
                "rationale": v
            }
        return {"primary": "#1a365d", "secondary": "#2d3748", "accent": "#3182ce", "rationale": ""}

# ── Executive Summary ──
class RecommendedAction(BaseModel):
    """Action item with priority and timeline."""
    action: str = ""
    priority: str = "UNSPECIFIED"
    timeline: str = "UNSPECIFIED"

class ExecutiveSummaryOutput(DeliverableOutput):
    """Executive summary deliverable schema."""
    type: str = "executive_summary"
    headline: str = ""
    key_takeaways: list[str] = Field(default_factory=list)
    context: str = ""
    major_findings: list[str] = Field(default_factory=list)
    business_impact: str = ""
    risks: list[str] = Field(default_factory=list)
    decisions_required: list[str] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    priority: str = "UNSPECIFIED"
    conclusion: str = ""

    @field_validator("business_impact", "context", "headline", "conclusion", mode="before")
    @classmethod
    def coerce_summary_strings(cls, v):
        if isinstance(v, list):
            return " ".join(str(x) for x in v if x)
        return str(v) if v is not None else ""

    @field_validator("key_takeaways", "major_findings", "risks", "decisions_required", mode="before")
    @classmethod
    def coerce_summary_lists(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            return [v_str] if v_str else []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

    @field_validator("recommended_actions", mode="before")
    @classmethod
    def coerce_recommended_actions(cls, v):
        if not isinstance(v, list):
            if isinstance(v, str) and v.strip():
                return [{"action": v.strip(), "priority": "UNSPECIFIED", "timeline": "UNSPECIFIED"}]
            return []
        res = []
        for item in v:
            if isinstance(item, str) and item.strip():
                res.append({"action": item.strip(), "priority": "UNSPECIFIED", "timeline": "UNSPECIFIED"})
            elif isinstance(item, dict):
                res.append(item)
            elif hasattr(item, "action"):
                res.append(item)
        return res

# ── Presentation Deck ──
class PresentationSlide(BaseModel):
    """Slide breakdown with visual notes and speaker notes."""
    slide_number: int = 1
    layout: Literal["auto", "cover", "editorial", "metrics", "process", "comparison", "closing"] = "auto"
    title: str = ""
    category: str = ""
    purpose: str = ""
    key_points: list[str] = Field(default_factory=list)
    body_content: str = Field(default="", description="Narrative only when key_points is empty; otherwise leave empty to avoid duplication")
    takeaway: str = ""
    key_metrics: list[str] = Field(default_factory=list)
    visual_recommendation: str = ""
    speaker_notes: str = ""

    @field_validator("key_points", "key_metrics", mode="before")
    @classmethod
    def coerce_slide_lists(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            return [v_str] if v_str else []
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, dict):
                    res.append(" | ".join(f"{k}: {val}" for k, val in item.items() if val))
                elif item is not None:
                    res.append(str(item))
            return res
        return []

    @field_validator("body_content", "takeaway", "visual_recommendation", "speaker_notes", mode="before")
    @classmethod
    def coerce_slide_strings(cls, v):
        if isinstance(v, list):
            return " ".join(str(x) for x in v if x)
        return str(v) if v is not None else ""

class PresentationDeckOutput(DeliverableOutput):
    """Presentation deck deliverable schema."""
    type: str = "presentation_deck"
    title: str = ""
    slides: list[PresentationSlide] = Field(default_factory=list)

    @field_validator("slides", mode="before")
    @classmethod
    def coerce_slides(cls, v):
        if not isinstance(v, list):
            return []
        res = []
        for s in v:
            if isinstance(s, dict):
                res.append(s)
            elif isinstance(s, str) and s.strip():
                res.append({"title": s.strip(), "key_points": [s.strip()]})
            elif hasattr(s, "title"):
                res.append(s)
        return res

# ── Format name → Model class mapping ──
OUTPUT_FORMAT_MAP: dict[str, type[BaseModel]] = {
    "Video Package": VideoPackageOutput,
    "LinkedIn Post": LinkedInPostOutput,
    "Twitter / X Post": TwitterPostOutput,
    "Advisory Document": AdvisoryDocumentOutput,
    "Infographic": InfographicOutput,
    "Executive Summary": ExecutiveSummaryOutput,
    "Presentation Deck": PresentationDeckOutput,
}

# Maps format names to response keys
OUTPUT_KEY_MAP: dict[str, str] = {
    "Video Package": "video_package",
    "LinkedIn Post": "linkedin_post",
    "Twitter / X Post": "twitter_post",
    "Advisory Document": "advisory_document",
    "Infographic": "infographic",
    "Executive Summary": "executive_summary",
    "Presentation Deck": "presentation_deck",
}
