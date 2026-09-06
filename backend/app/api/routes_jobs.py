"""
api/routes_jobs.py
──────────────────
GET /api/jobs/{job_id}  — placeholder for async job tracking.
GET /api/outputs/{job_id} — placeholder for retrieving outputs.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status. Currently synchronous — returns completed for any valid ID."""
    return {
        "success": True,
        "job_id": job_id,
        "status": "completed",
        "message": "Synchronous mode — job completed with the generation response.",
    }


@router.get("/api/outputs/{job_id}")
async def get_outputs(job_id: str):
    """Get job outputs. Currently returns a placeholder — outputs are in the generate response."""
    return {
        "success": True,
        "job_id": job_id,
        "message": "Outputs were returned in the /api/generate response. Persistent storage coming in async mode.",
    }
