"""Validated ingestion, generation, persistence and exports."""
import json
import uuid
from types import SimpleNamespace
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from app.config import settings
from app.schemas.requests import GenerateRequest
from app.schemas.outputs import OUTPUT_FORMAT_MAP, OUTPUT_KEY_MAP
from app.services.ingestion import ingest_file, ingest_text, extract_url, is_url, NormalizedSource
from app.services.security import validate_file, sanitize_filename
from app.services.normalizer import extract_content_intelligence
from app.services.generator import generate_all_formats, build_combined_output
from app.services.ai_provider import get_provider
from app.models.database import SessionLocal, GenerationJob, GeneratedOutput
from app.utils.logging import logger

router = APIRouter()


def error(code, message, status=400):
    return JSONResponse(status_code=status, content={"success": False, "error": {"code": code, "message": message}})


@router.post("/api/generate")
async def generate(request: Request):
    files = []
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
        elif "multipart/form-data" in content_type:
            form = await request.form(max_files=4, max_fields=20)
            files = [f for f in form.getlist("files") if isinstance(f, UploadFile) and f.filename]
            body = {k: v for k, v in form.items() if isinstance(v, str)}
            body["source"] = body.pop("source_text", "") or body.get("source", "")
        else:
            return error("INVALID_REQUEST", "Send JSON or upload TXT, PDF or DOCX files.")
        if not isinstance(body, dict):
            return error("INVALID_REQUEST", "Request must be a JSON object.")
        source_text = body.get("source", "")
        if not isinstance(source_text, str):
            return error("INVALID_REQUEST", "Source must be text.")
        if not source_text.strip() and not files:
            return error("EMPTY_SOURCE", "Please provide source content (text or files).")
        params = GenerateRequest.model_validate({**body, "source": source_text or "Uploaded documents"})
        formats = list(dict.fromkeys(params.selected_formats()))
        if not formats or any(f not in OUTPUT_FORMAT_MAP for f in formats):
            return error("NO_VALID_FORMATS", "Select supported deliverable formats.")
        configuration_error = settings.configuration_error()
        if configuration_error:
            return error("AI_NOT_CONFIGURED", configuration_error, 503)
        sources = []
        for upload in files:
            name = sanitize_filename(upload.filename)
            data = await upload.read(settings.max_file_size_mb * 1024 * 1024 + 1)
            valid, message = validate_file(name, upload.content_type, len(data))
            if not valid:
                return error("INVALID_FILE", f"{name}: {message}")
            try:
                extracted = await run_in_threadpool(ingest_file, data, name)
            except Exception:
                return error("INVALID_FILE", f"Could not read {name}. Upload a valid TXT, text-based PDF or DOCX.")
            if not extracted.raw_text.strip():
                return error("NO_EXTRACTABLE_CONTENT", f"{name} has no readable text. Paste the text of scanned PDFs instead.")
            sources.append(extracted)
        if source_text.strip():
            if is_url(source_text.strip()):
                try:
                    sources.append(await run_in_threadpool(extract_url, source_text.strip()))
                except ValueError as exc:
                    return error("URL_EXTRACTION_FAILED", str(exc))
            else:
                sources.append(ingest_text(source_text))
        text = "\n\n".join(s.raw_text for s in sources).strip()
        if not text:
            return error("NO_EXTRACTABLE_CONTENT", "The input contains no readable text.")
        if len(text) > 50000:
            return error("SOURCE_TOO_LONG", "Combined content exceeds 50,000 characters. Use a shorter excerpt.")
        normalized = NormalizedSource(
            source_type=sources[0].source_type if len(sources) == 1 else "combined", raw_text=text,
            metadata={"title": params.title or sources[0].metadata.get("title", ""),
                      "content_type": params.content_type, "sources": [s.to_dict() for s in sources]},
        )
        ci = extract_content_intelligence(normalized)
        outputs = await run_in_threadpool(generate_all_formats, formats, ci, params.audience,
                                         params.tone, params.language, params.detail, params.objective)
        if len(outputs) != len(formats):
            return error("GENERATION_FAILED", "Some outputs could not be generated. Please retry.", 503)
        provider = SimpleNamespace(name=settings.effective_provider(),
                                   model_name="extractive-v1" if settings.effective_provider() == "demo" else settings.model_name)
        job_id = str(uuid.uuid4())
        warnings = list(dict.fromkeys(w for output in outputs.values() for w in output["warnings"]))
        persisted = True
        try:
            await run_in_threadpool(save_job, job_id, provider, outputs)
        except Exception:
            persisted = False
            warnings.append("Results are ready but could not be saved. Download them before leaving.")
            logger.warning("Unable to persist generation job")
        return {
            "success": True, "job_id": job_id, "output": build_combined_output(outputs), "outputs": outputs,
            "metadata": {**params.model_dump(exclude={"source", "output_format"}),
                         "title": ci.title, "provider": provider.name, "model": provider.model_name,
                         "generated_at": datetime.now(timezone.utc).isoformat(), "persisted": persisted,
                         "source_type": normalized.source_type, "source_characters": len(text),
                         "generation_mode": "ai" if all(o["generation_mode"] == "ai" for o in outputs.values()) else "extractive",
                         "warnings": warnings},
        }
    except (ValidationError, json.JSONDecodeError, ValueError):
        return error("INVALID_REQUEST", "Invalid input. Use text up to 50,000 characters and valid generation options.")
    except Exception:
        logger.exception("Generation request failed")
        return error("GENERATION_FAILED", "Processing failed. Please retry with a shorter text excerpt.", 503)
    finally:
        for upload in files:
            await upload.close()


def save_job(job_id, provider, outputs):
    with SessionLocal.begin() as db:
        db.add(GenerationJob(id=job_id, status="completed", ai_provider=provider.name,
                             model_name=provider.model_name, completed_at=datetime.now(timezone.utc)))
        db.flush()
        for key, data in outputs.items():
            db.add(GeneratedOutput(job_id=job_id, format_type=key, content_json=data))


@router.post("/api/export")
async def export_deliverable(request: Request):
    from app.services.exporters import export_presentation_pptx, export_advisory_pdf, export_summary_pdf, export_infographic_html
    exporters = {
        "presentation_deck": (export_presentation_pptx, "application/vnd.openxmlformats-officedocument.presentationml.presentation", "presentation.pptx"),
        "advisory_document": (export_advisory_pdf, "application/pdf", "advisory.pdf"),
        "executive_summary": (export_summary_pdf, "application/pdf", "summary.pdf"),
        "infographic": (export_infographic_html, "text/html", "infographic.html"),
    }
    try:
        body = await request.json()
        key, data = body.get("format_type"), body.get("data")
        if key not in exporters or not isinstance(data, dict) or not data:
            return error("INVALID_EXPORT", "Select a generated PDF, presentation or infographic to export.")
        if len(json.dumps(data)) > 200000:
            return error("INVALID_EXPORT", "Export content is too large.")
        name = next(n for n, k in OUTPUT_KEY_MAP.items() if k == key)
        data = OUTPUT_FORMAT_MAP[name](**data).model_dump()
        exporter, media, filename = exporters[key]
        result = await run_in_threadpool(exporter, data)
        return Response(content=result if isinstance(result, str) else result.getvalue(), media_type=media,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except (ValueError, TypeError, AttributeError):
        return error("INVALID_EXPORT", "Invalid export content.")
    except Exception:
        logger.exception("Export failed")
        return error("EXPORT_FAILED", "Export failed. Try downloading the text version.", 503)
