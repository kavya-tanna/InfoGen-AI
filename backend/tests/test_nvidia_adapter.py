from types import SimpleNamespace
from app.services.ai_provider import NvidiaProvider


def test_nvidia_passes_json_and_deadline_options():
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="stop", message=SimpleNamespace(content='{"headline":"Source summary"}'))])

    provider = object.__new__(NvidiaProvider)
    provider._model = "nvidia/nemotron-3.5-lightning-30b-a3b"
    provider._fallback_models = []
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    output = provider.generate("Synthetic source", timeout_seconds=42)
    assert output == '{"headline":"Source summary"}'
    assert captured["timeout"] == 42
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False
