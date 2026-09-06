"""Pydantic v2 schemas for all 7 output deliverable formats."""
from __future__ import annotations
from pydantic import BaseModel, Field
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

# ── Twitter / X Post ──
class TwitterPostOutput(DeliverableOutput):
    """Twitter / X post and thread deliverable schema."""
    type: str = "twitter_post"
    primary_post: str = ""
    thread: list[str] = Field(default_factory=list)
    key_indicators: list[str] = Field(default_factory=list)
    cta: str = ""
    hashtags: list[str] = Field(default_factory=list)

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

class PresentationDeckOutput(DeliverableOutput):
    """Presentation deck deliverable schema."""
    type: str = "presentation_deck"
    title: str = ""
    slides: list[PresentationSlide] = Field(default_factory=list)

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
