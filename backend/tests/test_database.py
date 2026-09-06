"""Tests for database models and initialization."""
import pytest
from app.models.database import (
    init_db,
    SessionLocal,
    User,
    Project,
    Source,
    SourceFile,
    NormalizedSourceRecord,
    GenerationParameter,
    GenerationJob,
    GeneratedOutput,
    GenerationError,
    UsageLog,
)


def test_init_db_creates_tables():
    init_db()
    session = SessionLocal()
    try:
        # Create a user
        user = User(email="test@infogen.ai", full_name="Test User")
        session.add(user)
        session.commit()

        # Query user
        queried = session.query(User).filter_by(email="test@infogen.ai").first()
        assert queried is not None
        assert queried.full_name == "Test User"
        assert len(queried.id) == 36  # UUID

        # Create a job with parameters and output
        job = GenerationJob(
            user_id=user.id,
            status="completed",
            model_name="deepseek-ai/deepseek-v4-pro",
            ai_provider="nvidia",
        )
        session.add(job)
        session.commit()

        params = GenerationParameter(
            job_id=job.id,
            audience="Executives",
            tone="Professional",
            language="English",
            detail="Standard",
            objective="Inform",
            output_formats=["executive_summary"],
        )
        session.add(params)

        output = GeneratedOutput(
            job_id=job.id,
            format_type="executive_summary",
            content_json={"headline": "Test Headline", "key_takeaways": ["Point 1"]},
            grounding_score=98.5,
        )
        session.add(output)

        usage = UsageLog(
            job_id=job.id,
            ai_provider="nvidia",
            model_name="deepseek-ai/deepseek-v4-pro",
            prompt_tokens=500,
            completion_tokens=250,
            latency_ms=1250.0,
        )
        session.add(usage)
        session.commit()

        # Query job with relationships
        queried_job = session.query(GenerationJob).filter_by(id=job.id).first()
        assert queried_job is not None
        assert len(queried_job.outputs) == 1
        assert queried_job.outputs[0].format_type == "executive_summary"
        assert queried_job.parameters.audience == "Executives"
        assert len(queried_job.logs) == 1
        assert queried_job.logs[0].prompt_tokens == 500

        # Clean up
        session.delete(user)
        session.commit()
    finally:
        session.close()
