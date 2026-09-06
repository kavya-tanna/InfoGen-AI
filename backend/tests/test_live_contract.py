"""Live-provider contracts using stubs; these tests never call NVIDIA."""
import json

from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings, settings

client = TestClient(app)


def test_missing_live_credentials_do_not_silently_use_demo(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "ai_provider", "nvidia")
    for field in ("nvidia_api_key", "openai_api_key", "google_api_key", "anthropic_api_key"):
        monkeypatch.setattr(settings, field, "")
    result = client.post("/api/generate", json={"source": "A library announced a new reading room."})
    assert result.status_code == 503
    assert result.json()["error"]["code"] == "AI_NOT_CONFIGURED"
    assert client.get("/api/health").json()["demo_mode"] is False


def test_live_video_derives_subtitles_and_script(monkeypatch):
    class Provider:
        name = "nvidia"

        def generate(self, *args, **kwargs):
            return json.dumps({
                "title": "Library update", "script": "Draft text", "duration_seconds": 999,
                "scenes": [
                    {"scene_number": 9, "start_time": "00:00", "end_time": "00:15", "narration": "A new reading room opened."},
                    {"scene_number": 4, "start_time": "00:15", "end_time": "00:30", "narration": "The room serves students."},
                ],
            })
    monkeypatch.setattr("app.services.generator.get_provider", lambda: Provider())
    result = client.post("/api/generate", json={
        "source": "A new reading room opened. The room serves students.", "output_format": "Video Package",
    })
    output = result.json()["outputs"]["video_package"]
    assert output["generation_mode"] == "ai"
    assert output["duration_seconds"] == 30
    assert [s["scene_number"] for s in output["scenes"]] == [1, 2]
    assert "00:00:15.000 --> 00:00:30.000" in output["vtt"]
    assert output["script"] == "A new reading room opened.\n\nThe room serves students."


def test_health_never_returns_credentials():
    body = client.get("/api/health").text
    assert "nvapi-" not in body
    assert "NVIDIA_API_KEY=" not in body
