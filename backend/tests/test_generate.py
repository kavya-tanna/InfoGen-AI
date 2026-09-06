"""Tests for generation endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_SOURCE = """Critical Security Advisory: A new zero-day vulnerability CVE-2024-12345 has been discovered 
in Apache HTTP Server versions 2.4.49 through 2.4.51. The vulnerability allows remote code execution 
via path traversal attacks. Affected IP ranges include 192.168.1.0/24 and 10.0.0.0/8. 
The threat actor group APT-29 has been observed exploiting this vulnerability in the wild. 
Immediate patching is recommended. Contact security@example.com for assistance."""

def test_generate_text_input():
    response = client.post("/api/generate", json={
        "source": SAMPLE_SOURCE,
        "audience": "Technical Team & IT Admins",
        "tone": "Urgent Advisory",
        "language": "English",
        "detail": "Standard",
        "objective": "Risk Mitigation & Action",
        "output_format": "Executive Summary"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "output" in data
    assert "outputs" in data
    assert "metadata" in data
    assert data["metadata"]["language"] == "English"

def test_generate_empty_source():
    response = client.post("/api/generate", json={
        "source": "",
        "output_format": "Executive Summary"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False

def test_generate_whitespace_source():
    response = client.post("/api/generate", json={
        "source": "   ",
        "output_format": "Executive Summary"
    })
    assert response.status_code == 400

def test_generate_invalid_format():
    response = client.post("/api/generate", json={
        "source": SAMPLE_SOURCE,
        "output_format": "Invalid Format That Does Not Exist"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "NO_VALID_FORMATS" in data["error"]["code"]

def test_generate_multiple_formats():
    response = client.post("/api/generate", json={
        "source": SAMPLE_SOURCE,
        "output_format": "Executive Summary, Advisory Document, LinkedIn Post"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "outputs" in data

def test_generate_all_seven_formats():
    response = client.post("/api/generate", json={
        "source": SAMPLE_SOURCE,
        "output_format": "Video Package, LinkedIn Post, Twitter / X Post, Advisory Document, Infographic, Executive Summary, Presentation Deck"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    outputs = data.get("outputs", {})
    # At least some outputs should be present
    assert len(outputs) > 0

def test_generate_has_job_id():
    response = client.post("/api/generate", json={
        "source": SAMPLE_SOURCE,
        "output_format": "Executive Summary"
    })
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) > 0

def test_generate_metadata_populated():
    response = client.post("/api/generate", json={
        "source": SAMPLE_SOURCE,
        "audience": "Executives",
        "tone": "Professional",
        "language": "English",
        "detail": "Concise",
        "objective": "Inform",
        "output_format": "Executive Summary"
    })
    data = response.json()
    meta = data.get("metadata", {})
    assert meta["audience"] == "Executives"
    assert meta["tone"] == "Professional"
    assert meta["detail"] == "Concise"
    assert "generated_at" in meta
    assert "provider" in meta
