import json

import pytest

from app.services import notification_service
from app.services.llm_provider import MockLLMProvider
from app.services.tool_registry import SalesTool, ToolRegistry


def test_tool_registry_rejects_unknown_malformed_and_extra_arguments():
    registry = ToolRegistry()
    registry.register(SalesTool(
        name="echo",
        description="Echo a value",
        parameters={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=lambda *, context, value: {"value": value},
    ))

    assert registry.execute("echo", json.dumps({"value": "ok"}), {}) == {"value": "ok"}
    with pytest.raises(ValueError, match="Unknown"):
        registry.execute("missing", "{}", {})
    with pytest.raises(ValueError, match="valid JSON"):
        registry.execute("echo", "broken", {})
    with pytest.raises(ValueError, match="unsupported"):
        registry.execute("echo", {"value": "ok", "extra": True}, {})


def test_notification_provider_selection_and_webhook(monkeypatch):
    monkeypatch.setenv("SMS_PROVIDER", "unsupported")
    assert isinstance(notification_service.get_sms_provider(), notification_service.DisabledSMSProvider)
    monkeypatch.setenv("EMAIL_PROVIDER", "unsupported")
    assert isinstance(notification_service.get_email_provider(), notification_service.DisabledEmailProvider)

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("SMS_PROVIDER", "webhook")
    monkeypatch.setenv("SMS_WEBHOOK_URL", "https://sms.example.test/hook")
    monkeypatch.setattr(notification_service.urllib_request, "urlopen", fake_urlopen)
    notification_service.get_sms_provider().send(phone="0912", message="hello")
    assert captured == {"body": {"to": "0912", "message": "hello"}, "timeout": 10}


def test_mock_llm_returns_safe_answer_without_context():
    provider = MockLLMProvider()
    answer = provider.complete(
        "system",
        "Customer question:\nhello\n\nResponse guidance:\nDirect answer.\n\nRetrieved store data:\nNo matching information was found.",
    )
    assert "پیدا نشد" in answer