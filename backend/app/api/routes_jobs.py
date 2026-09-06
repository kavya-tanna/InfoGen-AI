"""Read completed jobs and their persisted outputs."""
from fastapi import APIRouter, HTTPException
from app.models.database import SessionLocal, GenerationJob

router = APIRouter()


@router.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    with SessionLocal() as db:
        job = db.get(GenerationJob, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return {"job_id": job.id, "status": job.status, "provider": job.ai_provider}


@router.get("/api/outputs/{job_id}")
def job_outputs(job_id: str):
    with SessionLocal() as db:
        job = db.get(GenerationJob, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return {"job_id": job.id, "outputs": {o.format_type: o.content_json for o in job.outputs}}
