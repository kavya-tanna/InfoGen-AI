"""
api/routes_ingest.py
────────────────────
POST /api/ingest — standalone file upload + extraction.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.schemas.responses import IngestResponse, ErrorResponse, ErrorDetail
from app.services.ingestion import ingest_file, ingest_text, is_url, extract_url
from app.services.security import validate_file, sanitize_filename, sanitize_source_text
from app.utils.logging import logger
from app.config import settings
from starlette.concurrency import run_in_threadpool

router = APIRouter()


@router.post("/api/ingest")
async def ingest(
    source_text: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    files: list[UploadFile] = File(default=[]),
):
    """Standalone ingestion endpoint for file upload + text extraction."""
    source_id = str(uuid.uuid4())
    logger.info(f"[{source_id}] Ingest request")

    extracted_parts: list[str] = []
    file_records: list[dict[str, Any]] = []

    # Process files
    for upload_file in (files or []):
        if not upload_file.filename:
            continue

        safe_name = sanitize_filename(upload_file.filename)
        file_bytes = await upload_file.read(settings.max_file_size_mb * 1024 * 1024 + 1)
        await upload_file.close()

        is_valid, err_msg = validate_file(safe_name, upload_file.content_type, len(file_bytes))
        if not is_valid:
            file_records.append({"filename": safe_name, "status": "rejected", "error": err_msg})
            continue

        try:
            source = await run_in_threadpool(ingest_file, file_bytes, safe_name)
            extracted_parts.append(source.raw_text)
            file_records.append({
                "filename": safe_name,
                "status": "extracted",
                "source_type": source.source_type,
                "char_count": len(source.raw_text),
            })
        except Exception as e:
            file_records.append({"filename": safe_name, "status": "failed", "error": str(e)})

    # Process URL
    if source_url:
        try:
            url_source = await run_in_threadpool(extract_url, source_url)
            extracted_parts.append(url_source.raw_text)
            file_records.append({
                "filename": source_url,
                "status": "extracted",
                "source_type": "url",
                "char_count": len(url_source.raw_text),
            })
        except Exception as e:
            file_records.append({"filename": source_url, "status": "failed", "error": str(e)})

    # Process text
    if source_text:
        cleaned = sanitize_source_text(source_text.strip())
        if cleaned:
            extracted_parts.append(cleaned)

    combined = "\n\n".join(extracted_parts)

    if not combined.strip():
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(code="NO_CONTENT", message="No extractable content found.")
            ).model_dump(),
        )

    return IngestResponse(
        success=True,
        source_id=source_id,
        files=file_records,
        extracted_text=combined,
        status="ready",
    ).model_dump()
