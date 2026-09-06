"""Tests for health endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "provider" in data
    assert "version" in data

def test_health_has_required_fields():
    response = client.get("/api/health")
    data = response.json()
    assert "demo_mode" in data
    assert "model" in data
