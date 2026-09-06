"""
services/exporters.py
─────────────────────
Modular export helpers converting generated deliverable JSON into native binary formats:
- Presentation Deck  -> .pptx (PowerPoint via python-pptx)
- Advisory Document  -> .pdf  (PDF via ReportLab)
- Executive Summary  -> .pdf  (PDF via ReportLab)
- Infographic        -> .html (Visual responsive infographic document)
- Video Package      -> .vtt / .srt / .txt
"""
from __future__ import annotations

import io
import os
import textwrap
import html
import re
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable, Table, TableStyle


def _escaped_content(value):
    if isinstance(value, str):
        return html.escape(value)
    if isinstance(value, list):
        return [_escaped_content(v) for v in value]
    if isinstance(value, dict):
        return {k: _escaped_content(v) for k, v in value.items()}
    return value

# ═══════════════════════════════════════════════════════════════════════
# 1. PPTX SLIDE VISUAL GENERATOR & EXPORTER
# ═══════════════════════════════════════════════════════════════════════

def _get_diagram_fonts():
    try:
        f_title = ImageFont.truetype("arialbd.ttf", 22)
        f_sub = ImageFont.truetype("arialbd.ttf", 15)
        f_body = ImageFont.truetype("arial.ttf", 13)
        f_big = ImageFont.truetype("arialbd.ttf", 34)
        f_pill = ImageFont.truetype("arialbd.ttf", 11)
    except Exception:
        try:
            f_title = ImageFont.truetype("arial.ttf", 22)
            f_sub = ImageFont.truetype("arial.ttf", 15)
            f_body = ImageFont.truetype("arial.ttf", 13)
            f_big = ImageFont.truetype("arial.ttf", 34)
            f_pill = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            f_title = f_sub = f_body = f_big = f_pill = ImageFont.load_default()
    return f_title, f_sub, f_body, f_big, f_pill


def generate_slide_visual_image(slide_data: dict[str, Any], slide_idx: int, total_slides: int) -> io.BytesIO:
    """Render actual slide excerpts, without invented chart values or risk ratings."""
    img = Image.new("RGB", (960, 680), color=(245, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font, _, _, _, _ = _get_diagram_fonts()
    draw.text((38, 35), "SOURCE BRIEFING", font=title_font, fill=(52, 105, 78))
    draw.line((38, 82, 920, 82), fill=(170, 191, 178), width=2)
    try:
        body_font = ImageFont.truetype("arial.ttf", 23)
    except OSError:
        body_font = ImageFont.load_default(size=23)
    points = slide_data.get("key_points") or [slide_data.get("title", "Source overview")]
    y = 110
    for index, point in enumerate(points[:3], 1):
        wrapped = textwrap.wrap(str(point), width=68)[:5]
        label = f"{index:02}"
        draw.text((38, y), label, font=title_font, fill=(161, 57, 88))
        for line in wrapped:
            draw.text((95, y), line, font=body_font, fill=(38, 53, 74))
            y += 29
        y += 20
        if y > 570:
            break
    draw.text((38, 625), "Statements from the supplied source; not independently verified.",
              font=body_font, fill=(89, 107, 96))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def export_presentation_pptx(deck_data: dict[str, Any]) -> io.BytesIO:
    """Export the AI's complete slide list with varied, editable 16:9 layouts."""
    import math

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    ink, muted, teal, coral, paper = "182827", "586A68", "007F73", "CB5945", "F7FAF9"
    slides = deck_data.get("slides", [])
    if not slides:
        raise ValueError("The presentation has no slides.")

    def rect(slide, x, y, w, h, color):
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(color)
        shape.line.fill.background()
        return shape

    def text(slide, value, x, y, w, h, size=22, color=ink, bold=False):
        value = str(value or "")
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = Inches(0.03)
        frame.margin_top = frame.margin_bottom = Inches(0.02)
        # Estimate wrapped line height before export, instead of clipping long source text.
        while size > 10:
            try:
                font = ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", round(size * 96 / 72))
            except OSError:
                font = ImageFont.load_default(size=round(size * 96 / 72))
            lines = 0
            for paragraph in value.split("\n"):
                width = 0
                for word in paragraph.split():
                    word_width = font.getlength(word + " ")
                    if width and width + word_width > (w - 0.1) * 96:
                        lines += 1
                        width = 0
                    lines += max(0, math.ceil(word_width / ((w - 0.1) * 96)) - 1)
                    width += min(word_width, (w - 0.1) * 96)
                lines += 1
            if lines * size * 1.22 <= (h - 0.08) * 72:
                break
            size -= 1
        for i, line in enumerate(value.split("\n")):
            p = frame.paragraphs[0] if not i else frame.add_paragraph()
            p.text = line
            p.font.name = "Arial"
            p.font.size = Pt(size)
            p.font.bold = bold
            p.font.color.rgb = RGBColor.from_string(color)
            p.line_spacing = 1.12
            p.space_after = Pt(4)
        return box

    def points(slide, values, x, y, w, h, dark=False):
        values = [str(v) for v in values if str(v).strip()]
        if not values:
            return
        row = h / len(values)
        for j, value in enumerate(values):
            text(slide, f"{j + 1:02}", x, y + row*j, 0.5, min(row, 0.45), 14, "7CD8BD" if dark else teal, True)
            text(slide, value, x+0.7, y + row*j, w-0.7, row-0.1, 23, "FFFFFF" if dark else ink)
            if j < len(values)-1:
                rect(slide, x+0.7, y+row*(j+1)-0.1, w-0.7, 0.012, "36524D" if dark else "D7E3E0")

    for index, item in enumerate(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        layout = item.get("layout", "auto")
        metrics = [str(m) for m in item.get("key_metrics", []) if str(m).strip()]
        bullets = list(item.get("key_points") or [])
        body = item.get("body_content", "")
        if body and not bullets:
            bullets.append(body)
        if layout == "auto":
            layout = "cover" if index == 0 else ("metrics" if metrics else "editorial")
        if layout == "metrics" and not metrics:
            layout = "editorial"
        if layout in ("process", "comparison") and len(bullets) < 2:
            layout = "editorial"
        dark = layout in ("cover", "closing")
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(ink if dark else paper)
        accent = "7CD8BD" if dark else teal
        text_color = "FFFFFF" if dark else ink
        rect(slide, 0.65, 0.55, 0.42, 0.055, coral)
        text(slide, item.get("category") or deck_data.get("title", ""), 1.18, 0.37, 10.6, 0.38, 11, accent, True)
        text(slide, f"{index+1:02}", 12.0, 0.37, 0.55, 0.38, 13, accent, True)
        title = item.get("title", "")
        takeaway = item.get("takeaway", "")

        if layout == "cover":
            text(slide, title, 0.8, 1.25, 11.7, 2.15, 44, text_color, True)
            rect(slide, 0.85, 3.65, 2.0, 0.055, coral)
            points(slide, bullets, 0.85, 4.0, 11.55, 1.85, dark=True)
        elif layout == "closing":
            text(slide, title, 0.8, 1.1, 11.7, 1.35, 36, text_color, True)
            points(slide, bullets, 0.85, 2.85, 11.55, 3.0, dark=True)
        else:
            text(slide, title, 0.8, 1.05, 11.7, 1.05, 30, text_color, True)
            rect(slide, 0.85, 2.75, 11.6, 0.012, "CEDDD8")
            if layout == "metrics" and len(metrics) <= 2:
                for j, metric in enumerate(metrics):
                    y = 3.0 + j*1.5
                    match = re.match(r"^([\d,.]+(?:%)?)\s*(.*)$", metric)
                    if match:
                        text(slide, match[1], 0.95, y, 3.35, 0.95, 68, teal, True)
                        text(slide, match[2].lstrip(" -:"), 1.0, y+0.97, 3.25, 0.45, 21, muted)
                    else:
                        text(slide, metric, 0.95, y, 3.35, 1.3, 32, teal, True)
                rect(slide, 4.55, 3.05, 0.015, 2.95, "CEDDD8")
                points(slide, bullets, 4.9, 3.05, 7.45, 2.97)
            elif layout == "metrics":
                cols = min(len(metrics), 3)
                rows = math.ceil(len(metrics)/cols)
                width = 11.55/cols
                for j, metric in enumerate(metrics):
                    x, y = 0.85 + (j % cols)*width, 2.98 + (j//cols)*(1.8/rows)
                    match = re.match(r"^([\d,.]+(?:%|\s*(?:million|billion))?)\s*(.*)$", metric)
                    if match:
                        text(slide, match[1], x+0.1, y, width-0.3, 0.85/rows, 42, teal, True)
                        text(slide, match[2], x+0.1, y+0.9/rows, width-0.3, 0.75/rows, 17, muted)
                    else:
                        text(slide, metric, x+0.1, y, width-0.3, 1.65/rows, 28, teal, True)
                points(slide, bullets, 0.85, 4.83, 11.55, 1.4)
            elif layout == "process":
                cols = min(len(bullets), 4)
                rows = math.ceil(len(bullets)/cols)
                width, height = 11.55/cols, 3.1/rows
                for j, value in enumerate(bullets):
                    x, y = 0.85 + (j % cols)*width, 3.0+(j//cols)*height
                    rect(slide, x+0.06, y+0.08, width-0.22, 0.045, teal if j%2 == 0 else coral)
                    text(slide, f"{j+1:02}", x+0.08, y+0.22, width-0.3, 0.5, 26, teal, True)
                    text(slide, value, x+0.08, y+0.85, width-0.32, height-0.95, 20)
            elif layout == "comparison":
                midpoint = math.ceil(len(bullets)/2)
                rect(slide, 6.6, 3.0, 0.018, 3.05, "BCD2CC")
                points(slide, bullets[:midpoint], 0.85, 3.0, 5.45, 3.05)
                points(slide, bullets[midpoint:], 7.0, 3.0, 5.35, 3.05)
            else:
                points(slide, bullets, 0.85, 3.03, 11.55, 3.03)
        if takeaway and takeaway not in bullets:
            rect(slide, 0.85, 6.32, 0.045, 0.42, coral)
            text(slide, takeaway, 1.05, 6.28, 11.25, 0.5, 15, accent, True)
        text(slide, "InfoGen AI  |  Source-based draft", 0.85, 7.05, 10.5, 0.22, 9, "91B5AC" if dark else muted)
        text(slide, f"{index+1} / {len(slides)}", 11.6, 7.02, 0.85, 0.28, 10, accent)
        notes = item.get("speaker_notes", "")
        if body and item.get("key_points"):
            notes += "\n\nSupporting context: " + body
        if item.get("purpose"):
            notes += "\n\nPurpose: " + item["purpose"]
        if item.get("visual_recommendation"):
            notes += "\n\nProduction direction: " + item["visual_recommendation"]
        slide.notes_slide.notes_text_frame.text = notes.strip()
    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out

# ═══════════════════════════════════════════════════════════════════════
# 2. ADVISORY PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════

def export_advisory_pdf(data: dict[str, Any]) -> io.BytesIO:
    """Generate a high-quality Cyber Advisory PDF."""
    data = _escaped_content(data)
    security = data.get("document_kind") == "security"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    base = getSampleStyleSheet()
    primary = HexColor("#26354a")
    accent = HexColor("#b05d77")
    subtle = HexColor("#718096")

    title_style = ParagraphStyle(
        "AdvTitle",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=primary,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "AdvMeta",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=subtle,
        spaceAfter=10,
    )
    h2_style = ParagraphStyle(
        "AdvH2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=primary,
        spaceBefore=12,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "AdvBody",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#2d3748"),
        leading=14,
        spaceAfter=6,
    )

    story: list[Any] = []

    # Title & Badge
    story.append(Paragraph(data.get("title", "Cyber Security Advisory"), title_style))
    severity = str(data.get("severity", "INFORMATIONAL")).upper()
    confidence = data.get("confidence_level", "MEDIUM")

    story.append(Paragraph(
        f"<b>SEVERITY:</b> <font color='{accent.hexval()}'><b>{severity}</b></font> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>CONFIDENCE:</b> {confidence} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>PLATFORM:</b> InfoGen AI Advisory Engine",
        meta_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e5e9ef"), spaceAfter=10))

    # Executive Overview
    if data.get("executive_overview"):
        story.append(Paragraph("Executive Overview", h2_style))
        story.append(Paragraph(data["executive_overview"], body_style))

    # Threat Description
    if data.get("threat_description"):
        story.append(Paragraph("Threat Description" if security else "Issue Description", h2_style))
        story.append(Paragraph(data["threat_description"], body_style))

    # Affected Systems
    if data.get("affected_systems"):
        story.append(Paragraph("Affected Systems & Entities", h2_style))
        for sys in data["affected_systems"]:
            story.append(Paragraph(f"• {sys}", body_style))

    # Indicators of Compromise (IOCs)
    indicators = data.get("indicators", [])
    if indicators:
        story.append(Paragraph("Technical Indicators & IOCs" if security else "Source Indicators", h2_style))
        ioc_rows = [[Paragraph(f"<code>{ioc}</code>", body_style)] for ioc in indicators]
        t = Table(ioc_rows, colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f7f9fb")),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)

    # Impact
    if data.get("impact"):
        story.append(Paragraph("Potential Impact", h2_style))
        story.append(Paragraph(data["impact"], body_style))

    # Immediate Actions
    if data.get("immediate_actions"):
        story.append(Paragraph("Immediate Actions", h2_style))
        for i, act in enumerate(data["immediate_actions"], 1):
            story.append(Paragraph(f"<b>{i}.</b> {act}", body_style))

    # Mitigation
    if data.get("mitigation"):
        story.append(Paragraph("Mitigation Strategy", h2_style))
        for i, mit in enumerate(data["mitigation"], 1):
            story.append(Paragraph(f"<b>{i}.</b> {mit}", body_style))

    for field, heading in [
        ("technical_analysis", "Evidence and Analysis"), ("risk_assessment", "Risk Assessment"),
        ("long_term_recommendations", "Longer-term Recommendations"), ("references", "References"),
    ]:
        value = data.get(field)
        if value:
            story.append(Paragraph(heading, h2_style))
            for item in value if isinstance(value, list) else [value]:
                story.append(Paragraph(str(item), body_style))
    doc.build(story)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════
# 3. EXECUTIVE SUMMARY PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════

def export_summary_pdf(data: dict[str, Any]) -> io.BytesIO:
    """Generate a clean Executive Briefing PDF."""
    data = _escaped_content(data)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SumTitle",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=HexColor("#26354a"),
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "SumH2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=HexColor("#26354a"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "SumBody",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#2d3748"),
        leading=14,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "SumMeta",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=HexColor("#718096"),
        spaceAfter=10,
    )

    story: list[Any] = []
    headline = data.get("headline", "Executive Briefing")
    story.append(Paragraph(headline, title_style))
    priority = data.get("priority")
    label = f"Priority: <b>{priority}</b> | " if priority and priority != "UNSPECIFIED" else ""
    story.append(Paragraph(label + "Prepared by InfoGen AI", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e5e9ef"), spaceAfter=10))

    # Takeaways
    takeaways = data.get("key_takeaways", [])
    if takeaways:
        story.append(Paragraph("Key Takeaways", h2_style))
        for t in takeaways:
            story.append(Paragraph(f"•  {t}", body_style))

    # Situation & Context
    if data.get("context"):
        story.append(Paragraph("Situation & Context", h2_style))
        story.append(Paragraph(data["context"], body_style))

    # Business Impact
    if data.get("business_impact"):
        story.append(Paragraph("Business & Organizational Impact", h2_style))
        story.append(Paragraph(data["business_impact"], body_style))

    for field, heading in [
        ("major_findings", "Findings and Evidence"), ("risks", "Risks and Limitations"),
        ("decisions_required", "Decisions Required"),
    ]:
        if data.get(field):
            story.append(Paragraph(heading, h2_style))
            for value in data[field]:
                story.append(Paragraph(value, body_style))

    # Recommended Actions
    actions = data.get("recommended_actions", [])
    if actions:
        story.append(Paragraph("Prioritized Actions", h2_style))
        for i, a in enumerate(actions, 1):
            act_text = a.get("action", a) if isinstance(a, dict) else str(a)
            prio = a.get("priority", "") if isinstance(a, dict) else ""
            prio_str = f" [{prio}]" if prio and prio != "UNSPECIFIED" else ""
            timeline = a.get("timeline", "") if isinstance(a, dict) else ""
            timing = f" Timing: {timeline}." if timeline and timeline != "UNSPECIFIED" else ""
            story.append(Paragraph(f"<b>{i}.{prio_str}</b> {act_text}{timing}", body_style))

    # Conclusion
    if data.get("conclusion"):
        story.append(Paragraph("Conclusion", h2_style))
        story.append(Paragraph(data["conclusion"], body_style))

    doc.build(story)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════
# 4. INFOGRAPHIC HTML / SVG EXPORT
# ═══════════════════════════════════════════════════════════════════════

def export_infographic_html(data: dict[str, Any]) -> str:
    """Generate a standalone visual responsive HTML infographic."""
    data = _escaped_content(data)
    title = data.get("title", "Infographic Specification")
    subtitle = data.get("subtitle", "")
    stats = data.get("key_statistics", [])
    sections = data.get("sections", [])
    colors = data.get("color_recommendations", {})
    primary_color = colors.get("primary", "#26354a")
    accent_color = colors.get("accent", "#5b7cfa")
    primary_color = primary_color if re.fullmatch(r"#[0-9a-fA-F]{6}", primary_color) else "#26354a"
    accent_color = accent_color if re.fullmatch(r"#[0-9a-fA-F]{6}", accent_color) else "#48755b"

    stats_html = "".join([
        f"""<div class="stat-card">
            <div class="stat-val">{s.get('value', '')}</div>
            <div class="stat-label">{s.get('label', '')}</div>
            <p class="source-ref">{s.get('source_reference', '')}</p>
        </div>"""
        for s in stats
    ])

    sections_html = "".join([
        f"""<div class="section-card">
            <h3>{sec.get('section_title', '')}</h3>
            <p>{sec.get('content', '')}</p>
            <ol class="{'timeline' if sec.get('visual_element') == 'timeline' else 'points'}">{"".join("<li>" + point + "</li>" for point in sec.get('data_points', []))}</ol>
        </div>"""
        for sec in sections
    ])

    messages_html = "".join("<li>" + message + "</li>" for message in data.get("key_messages", []))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:'Segoe UI',sans-serif;background:#f7f8fa;color:#26354a;padding:30px;max-width:960px;margin:0 auto}}
.header{{text-align:center;margin-bottom:30px}}
h1{{color:{primary_color};font-size:32px;margin-bottom:8px}}
.subtitle{{color:#718096;font-size:16px}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:30px}}
.stat-card{{background:#fff;border:1px solid #e5e9ef;border-radius:12px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(0,0,0,0.03)}}
.stat-val{{font-size:36px;font-weight:700;color:{accent_color};margin-bottom:4px}}
.stat-label{{font-size:13px;color:#718096}}
.sections-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}}
.section-card{{background:#fff;border:1px solid #e5e9ef;border-radius:12px;padding:24px;position:relative}}
h3{{color:{primary_color};margin-bottom:10px}}
p{{font-size:13px;line-height:1.6;color:#4a5568}}
.tag{{display:inline-block;background:#eef2f6;color:{primary_color};font-size:10px;padding:4px 8px;border-radius:6px;margin-top:12px;font-weight:600}}
*{{box-sizing:border-box;overflow-wrap:anywhere;letter-spacing:0}}
body{{background:#fff;color:#182827;padding:24px}}
.header{{text-align:left;border-bottom:3px solid #007f73;padding-bottom:20px}}
.stats-grid{{gap:24px}}.stat-card{{border:0;border-bottom:3px solid #cb5945;border-radius:0;box-shadow:none;text-align:left;padding:12px 0}}
.stat-val{{color:#007f73}}.section-card{{border:0;border-top:1px solid #d7e3e0;border-radius:0;padding:20px 0}}
.source-ref{{font-size:11px;color:#586a68}}li{{font-size:14px;line-height:1.6;margin-bottom:8px}}
.timeline{{border-left:2px solid #007f73;padding-left:24px}}
@media(max-width:600px){{body{{padding:16px}}h1{{font-size:25px}}.sections-grid{{grid-template-columns:minmax(0,1fr)}}}}
</style>
</head>
<body>
<div class="header">
    <h1>{title}</h1>
    <div class="subtitle">{subtitle}</div>
</div>
<div class="stats-grid">{stats_html}</div>
<div class="sections-grid">{sections_html}</div>
{('<section><h2>What this means</h2><ul>' + messages_html + '</ul></section>') if messages_html else ''}
</body>
</html>"""
