"""
file_exporters.py
─────────────────
Export helpers that convert structured artifact dicts into downloadable
binary files (.pptx, .pdf, .srt).  Every function returns the path of the
generated file so Streamlit can serve it via st.download_button.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any

# ── PowerPoint ──────────────────────────────────────────────────────────
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── PDF (ReportLab) ────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


# ═══════════════════════════════════════════════════════════════════════
# 1.  PPTX  GENERATION
# ═══════════════════════════════════════════════════════════════════════

def generate_pptx(slides_data: list[dict[str, Any]], filename: str = "deck.pptx") -> str:
    """Create a .pptx presentation from a list of slide dicts.

    Each dict in *slides_data* must contain:
        title        – str
        bullet_points – list[str]
        speaker_notes – str  (optional)

    Returns the absolute path of the written file.
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for idx, slide_info in enumerate(slides_data):
        slide_layout = prs.slide_layouts[1]  # Title + Content
        slide = prs.slides.add_slide(slide_layout)

        # ── Title ───────────────────────────────────────────────────
        title_ph = slide.shapes.title
        if title_ph is not None:
            title_ph.text = slide_info.get("title", f"Slide {idx + 1}")
            for run in title_ph.text_frame.paragraphs[0].runs:
                run.font.color.rgb = RGBColor(0x06, 0xB6, 0xD4)
                run.font.size = Pt(32)
                run.font.bold = True

        # ── Bullet points ──────────────────────────────────────────
        body_ph = slide.placeholders.get(1)
        if body_ph is not None:
            tf = body_ph.text_frame
            tf.clear()
            for i, bullet in enumerate(slide_info.get("bullet_points", [])):
                para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                para.text = bullet
                para.font.size = Pt(18)
                para.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
                para.alignment = PP_ALIGN.LEFT

        # ── Speaker notes ──────────────────────────────────────────
        notes = slide_info.get("speaker_notes", "")
        if notes:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = notes

        # ── Dark background ────────────────────────────────────────
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0x0B, 0x0F, 0x17)

    prs.save(filename)
    return os.path.abspath(filename)


# ═══════════════════════════════════════════════════════════════════════
# 2.  ADVISORY  PDF  GENERATION
# ═══════════════════════════════════════════════════════════════════════

_DARK_BG = HexColor("#0B0F17")
_CYAN    = HexColor("#06B6D4")
_WHITE   = HexColor("#E2E8F0")
_GREY    = HexColor("#94A3B8")


def _build_pdf_styles() -> dict[str, ParagraphStyle]:
    """Return a dict of custom ParagraphStyles for the advisory PDF."""
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}

    styles["adv_title"] = ParagraphStyle(
        "adv_title",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=_CYAN,
        spaceAfter=10,
    )
    styles["adv_heading"] = ParagraphStyle(
        "adv_heading",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=_CYAN,
        spaceBefore=14,
        spaceAfter=6,
    )
    styles["adv_body"] = ParagraphStyle(
        "adv_body",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        textColor=_WHITE,
        leading=15,
        spaceAfter=6,
    )
    styles["adv_meta"] = ParagraphStyle(
        "adv_meta",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        textColor=_GREY,
        spaceAfter=4,
    )
    return styles


def generate_advisory_pdf(advisory_data: dict[str, Any], filename: str = "advisory.pdf") -> str:
    """Render a cyber-advisory PDF from *advisory_data*.

    Expected keys:
        title       – str
        severity    – str  (e.g. "CRITICAL", "HIGH")
        date        – str
        summary     – str
        iocs        – list[str]
        actions     – list[str]
        references  – list[str]   (optional)

    Returns the absolute path of the written file.
    """
    styles = _build_pdf_styles()
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    story: list[Any] = []

    # ── Title + severity badge ──────────────────────────────────────
    story.append(Paragraph(advisory_data.get("title", "Cyber Advisory"), styles["adv_title"]))
    severity = advisory_data.get("severity", "UNKNOWN")
    sev_color = {"CRITICAL": "#EF4444", "HIGH": "#F59E0B", "MEDIUM": "#FBBF24"}.get(
        severity.upper(), "#94A3B8"
    )
    story.append(
        Paragraph(
            f'<font color="{sev_color}"><b>Severity: {severity.upper()}</b></font>'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;Date: {advisory_data.get("date", "N/A")}',
            styles["adv_meta"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=_CYAN))
    story.append(Spacer(1, 10))

    # ── Summary ─────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", styles["adv_heading"]))
    story.append(Paragraph(advisory_data.get("summary", "—"), styles["adv_body"]))

    # ── IOCs table ──────────────────────────────────────────────────
    iocs = advisory_data.get("iocs", [])
    if iocs:
        story.append(Paragraph("Indicators of Compromise", styles["adv_heading"]))
        table_data = [[Paragraph(f"<font color='#E2E8F0'>{ioc}</font>", styles["adv_body"])] for ioc in iocs]
        t = Table(table_data, colWidths=[doc.width])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#111827")),
                    ("BOX", (0, 0), (-1, -1), 0.5, _CYAN),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, HexColor("#1E293B")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(t)

    # ── Recommended actions ─────────────────────────────────────────
    actions = advisory_data.get("actions", [])
    if actions:
        story.append(Paragraph("Recommended Actions", styles["adv_heading"]))
        for i, action in enumerate(actions, 1):
            story.append(Paragraph(f"{i}. {action}", styles["adv_body"]))

    # ── References ──────────────────────────────────────────────────
    refs = advisory_data.get("references", [])
    if refs:
        story.append(Paragraph("References", styles["adv_heading"]))
        for ref in refs:
            story.append(Paragraph(ref, styles["adv_body"]))

    doc.build(story)
    return os.path.abspath(filename)


# ═══════════════════════════════════════════════════════════════════════
# 3.  SRT  SUBTITLE  GENERATION
# ═══════════════════════════════════════════════════════════════════════

def _seconds_to_srt_time(seconds: float) -> str:
    """Convert a float seconds value to SRT timecode HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def generate_srt(subtitles_data: list[dict[str, Any]], filename: str = "storyboard.srt") -> str:
    """Create a valid .srt subtitle file.

    Each dict in *subtitles_data* must contain:
        start   – float  (seconds)
        end     – float  (seconds)
        text    – str

    Returns the absolute path of the written file.
    """
    lines: list[str] = []
    for idx, sub in enumerate(subtitles_data, 1):
        start_tc = _seconds_to_srt_time(sub["start"])
        end_tc = _seconds_to_srt_time(sub["end"])
        text = sub.get("text", "").strip()
        # Wrap long lines at 42 chars for readability
        wrapped = "\n".join(textwrap.wrap(text, width=42)) if text else ""
        lines.append(f"{idx}\n{start_tc} --> {end_tc}\n{wrapped}\n")
    content = "\n".join(lines)
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(content)
    return os.path.abspath(filename)
