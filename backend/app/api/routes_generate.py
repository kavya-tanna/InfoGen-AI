"""
api/routes_generate.py
──────────────────────
POST /api/generate — accepts JSON and multipart/form-data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse, GenerateMetadata, ErrorResponse, ErrorDetail
from app.schemas.outputs import OUTPUT_FORMAT_MAP
from app.services.ingestion import ingest_text, ingest_file, is_url, extract_url, NormalizedSource
from app.services.normalizer import extract_content_intelligence
from app.services.generator import generate_all_formats, build_combined_output
from app.services.security import validate_file, sanitize_filename, sanitize_source_text, detect_prompt_injection
from app.services.ai_provider import get_provider
from app.utils.logging import logger

router = APIRouter()


@router.post("/api/generate")
async def generate(
    request: Request,
    # Form fields for multipart
    source: Optional[str] = Form(None),
    source_text: Optional[str] = Form(None),
    audience: Optional[str] = Form(None),
    tone: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    detail: Optional[str] = Form(None),
    objective: Optional[str] = Form(None),
    output_format: Optional[str] = Form(None),
    files: list[UploadFile] = File(default=[]),
):
    """Generate content deliverables from source input.

    Accepts both JSON and multipart/form-data requests.
    """
    job_id = str(uuid.uuid4())
    logger.info(f"[{job_id}] Generation request received")

    try:
        # ── Determine content type and parse request ─────────────
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # JSON request
            body = await request.json()
            source_val = body.get("source", "")
            audience_val = body.get("audience", "General Public")
            tone_val = body.get("tone", "Professional")
            language_val = body.get("language", "English")
            detail_val = body.get("detail", "Standard")
            objective_val = body.get("objective", "Inform")
            output_format_val = body.get("output_format", "Executive Summary")
            uploaded_files: list[UploadFile] = []
        else:
            # Multipart form-data
            source_val = source or source_text or ""
            audience_val = audience or "General Public"
            tone_val = tone or "Professional"
            language_val = language or "English"
            detail_val = detail or "Standard"
            objective_val = objective or "Inform"
            output_format_val = output_format or "Executive Summary"
            uploaded_files = files or []

        # ── Validate source ──────────────────────────────────────
        source_val = source_val.strip() if source_val else ""
        has_text = bool(source_val)
        has_files = bool(uploaded_files) and any(f.filename for f in uploaded_files)

        if not has_text and not has_files:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=ErrorDetail(code="EMPTY_SOURCE", message="Please provide source content (text or files).")
                ).model_dump(),
            )

        # ── Parse selected formats ───────────────────────────────
        selected_formats = [f.strip() for f in output_format_val.split(",") if f.strip()]
        valid_formats = [f for f in selected_formats if f in OUTPUT_FORMAT_MAP]

        if not valid_formats:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=ErrorDetail(code="NO_VALID_FORMATS", message=f"No valid output formats selected. Available: {', '.join(OUTPUT_FORMAT_MAP.keys())}")
                ).model_dump(),
            )

        logger.info(f"[{job_id}] Formats: {valid_formats}, Audience: {audience_val}, Tone: {tone_val}")

        # ── Ingest source ────────────────────────────────────────
        combined_text = ""

        # Process uploaded files
        if has_files:
            for upload_file in uploaded_files:
                if not upload_file.filename:
                    continue

                safe_name = sanitize_filename(upload_file.filename)
                file_bytes = await upload_file.read()

                # Validate file
                is_valid, err_msg = validate_file(
                    safe_name, upload_file.content_type, len(file_bytes)
                )
                if not is_valid:
                    logger.warning(f"[{job_id}] File rejected: {safe_name} — {err_msg}")
                    continue

                try:
                    file_source = ingest_file(file_bytes, safe_name)
                    combined_text += file_source.raw_text + "\n\n"
                    logger.info(f"[{job_id}] File ingested: {safe_name}, {len(file_source.raw_text)} chars")
                except Exception as e:
                    logger.error(f"[{job_id}] File ingestion failed for {safe_name}: {e}")

        # Process text input
        if has_text:
            source_val = sanitize_source_text(source_val)

            # Check for prompt injection (log but don't block — treat as content)
            if detect_prompt_injection(source_val):
                logger.warning(f"[{job_id}] Potential prompt injection detected in source text")

            # Check if it's a URL
            if is_url(source_val):
                try:
                    url_source = extract_url(source_val)
                    combined_text += url_source.raw_text + "\n\n"
                    logger.info(f"[{job_id}] URL ingested: {len(url_source.raw_text)} chars")
                except Exception as e:
                    logger.error(f"[{job_id}] URL ingestion failed: {e}")
                    combined_text += source_val + "\n\n"
            else:
                combined_text += source_val + "\n\n"

        if not combined_text.strip():
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=ErrorDetail(code="NO_EXTRACTABLE_CONTENT", message="Could not extract any content from the provided source.")
                ).model_dump(),
            )

        # ── Build normalized source ──────────────────────────────
        normalized = NormalizedSource(
            source_type="combined" if has_files else ("url" if is_url(source_val) else "text"),
            raw_text=combined_text.strip(),
        )

        # ── Extract Content Intelligence ─────────────────────────
        logger.info(f"[{job_id}] Extracting content intelligence...")
        content_intelligence = extract_content_intelligence(normalized)
        logger.info(f"[{job_id}] Content intelligence ready: {len(content_intelligence.facts)} facts")

        # ── Generate all selected formats ────────────────────────
        logger.info(f"[{job_id}] Generating {len(valid_formats)} formats...")
        provider = get_provider()

        outputs = generate_all_formats(
            selected_formats=valid_formats,
            content_intelligence=content_intelligence,
            audience=audience_val,
            tone=tone_val,
            language=language_val,
            detail=detail_val,
            objective=objective_val,
        )

        # ── Build combined output text ───────────────────────────
        combined_output = build_combined_output(outputs)

        # ── Build response ───────────────────────────────────────
        response = GenerateResponse(
            success=True,
            job_id=job_id,
            output=combined_output,
            outputs=outputs,
            metadata=GenerateMetadata(
                language=language_val,
                audience=audience_val,
                tone=tone_val,
                detail=detail_val,
                objective=objective_val,
                generated_at=datetime.now(timezone.utc).isoformat(),
                model=provider.model_name,
                provider=provider.name,
            ),
        )

        logger.info(f"[{job_id}] Generation complete: {len(outputs)} formats produced")
        return response.model_dump()

    except Exception as e:
        logger.error(f"[{job_id}] Generation failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="GENERATION_FAILED",
                    message=f"Content generation failed: {str(e)}"
                )
            ).model_dump(),
        )


@router.post("/api/export")
async def export_deliverable(request: Request):
    """Export deliverable to native format (.pptx, .pdf, .html)."""
    from fastapi.responses import Response
    from app.services.exporters import (
        export_presentation_pptx,
        export_advisory_pdf,
        export_summary_pdf,
        export_infographic_html,
    )

    body = await request.json()
    format_type = body.get("format_type", "")
    data = body.get("data", {})

    if not data:
        return JSONResponse(status_code=400, content={"error": "No data provided for export"})

    if format_type in ("presentation_deck", "presentation"):
        buf = export_presentation_pptx(data)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": 'attachment; filename="presentation.pptx"'}
        )
    elif format_type in ("advisory_document", "advisory"):
        buf = export_advisory_pdf(data)
        return Response(
            content=buf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="cyber_advisory.pdf"'}
        )
    elif format_type in ("executive_summary", "summary"):
        buf = export_summary_pdf(data)
        return Response(
            content=buf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="executive_summary.pdf"'}
        )
    elif format_type in ("infographic",):
        html_str = export_infographic_html(data)
        return Response(
            content=html_str,
            media_type="text/html",
            headers={"Content-Disposition": 'attachment; filename="infographic.html"'}
        )

    return JSONResponse(status_code=400, content={"error": f"Unsupported export format: {format_type}"})
