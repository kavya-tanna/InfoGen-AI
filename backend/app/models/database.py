"""
models/database.py
──────────────────
SQLAlchemy models for persistent storage:
- users
- projects
- generation_jobs
- sources
- source_files
- normalized_sources
- generation_parameters
- generated_outputs
- generation_errors
- usage_logs

Compatible with PostgreSQL (production) and SQLite (local SIH demo).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import settings

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── 1. Users ──────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("GenerationJob", back_populates="user")


# ── 2. Projects ───────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="projects")
    jobs = relationship("GenerationJob", back_populates="project", cascade="all, delete-orphan")


# ── 3. Sources ────────────────────────────────────────────────────────
class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_type = Column(String(50), nullable=False)  # text, pdf, docx, image, audio, video, url
    raw_text = Column(Text, nullable=True)
    url = Column(String(2048), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    files = relationship("SourceFile", back_populates="source", cascade="all, delete-orphan")
    normalized = relationship("NormalizedSourceRecord", back_populates="source", uselist=False)
    jobs = relationship("GenerationJob", back_populates="source")


# ── 4. Source Files ───────────────────────────────────────────────────
class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_path = Column(String(1024), nullable=True)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    source = relationship("Source", back_populates="files")


# ── 5. Normalized Sources ─────────────────────────────────────────────
class NormalizedSourceRecord(Base):
    __tablename__ = "normalized_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=True)
    facts = Column(JSON, default=list)
    entities = Column(JSON, default=list)
    timeline = Column(JSON, default=list)
    numbers = Column(JSON, default=list)
    risks = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    quotes = Column(JSON, default=list)
    source_evidence = Column(JSON, default=list)
    uncertainties = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)

    source = relationship("Source", back_populates="normalized")


# ── 6. Generation Parameters ──────────────────────────────────────────
class GenerationParameter(Base):
    __tablename__ = "generation_parameters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("generation_jobs.id"), nullable=False, index=True)
    audience = Column(String(100), nullable=False)
    tone = Column(String(100), nullable=False)
    language = Column(String(50), nullable=False)
    detail = Column(String(100), nullable=False)
    objective = Column(String(100), nullable=False)
    output_formats = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)

    job = relationship("GenerationJob", back_populates="parameters")


# ── 7. Generation Jobs ────────────────────────────────────────────────
class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=True, index=True)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    model_name = Column(String(100), nullable=True)
    ai_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="jobs")
    project = relationship("Project", back_populates="jobs")
    source = relationship("Source", back_populates="jobs")
    parameters = relationship("GenerationParameter", back_populates="job", uselist=False, cascade="all, delete-orphan")
    outputs = relationship("GeneratedOutput", back_populates="job", cascade="all, delete-orphan")
    errors = relationship("GenerationError", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("UsageLog", back_populates="job", cascade="all, delete-orphan")


# ── 8. Generated Outputs ──────────────────────────────────────────────
class GeneratedOutput(Base):
    __tablename__ = "generated_outputs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("generation_jobs.id"), nullable=False, index=True)
    format_type = Column(String(50), nullable=False)  # video_package, advisory_document, etc.
    content_json = Column(JSON, nullable=False)
    grounding_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    job = relationship("GenerationJob", back_populates="outputs")


# ── 9. Generation Errors ──────────────────────────────────────────────
class GenerationError(Base):
    __tablename__ = "generation_errors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("generation_jobs.id"), nullable=False, index=True)
    error_code = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    stage = Column(String(100), nullable=True)  # ingestion, extraction, generation, validation
    occurred_at = Column(DateTime, default=utc_now)

    job = relationship("GenerationJob", back_populates="errors")


# ── 10. Usage Logs ────────────────────────────────────────────────────
class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("generation_jobs.id"), nullable=True, index=True)
    ai_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)

    job = relationship("GenerationJob", back_populates="logs")


# ── Engine and Session Factory ────────────────────────────────────────
def get_engine():
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(settings.database_url, connect_args=connect_args)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
