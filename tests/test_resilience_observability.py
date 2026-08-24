import json

from portproject_rag import api
from portproject_rag.settings import Settings


def test_request_id_accepts_bounded_safe_values() -> None:
    assert api._request_id("phase13-123") == "phase13-123"
    generated = api._request_id("unsafe value with spaces")
    assert len(generated) == 32
    assert generated.isalnum()


def test_ready_returns_stable_not_ready_payload_when_database_check_fails(monkeypatch) -> None:
    api.app.state.settings = Settings()
    api.app.state.rag_ready = True
    api.app.state.rag_init_error = None
    monkeypatch.setattr(api, "_stats", lambda _settings: (_ for _ in ()).throw(RuntimeError("simulated database outage")))

    response = api.ready()

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "not_ready",
        "rag_ready": False,
        "init_error": "database_unavailable",
        "corpus": None,
    }


def test_audit_failure_is_visible_without_turning_operation_into_exception(monkeypatch, caplog) -> None:
    monkeypatch.setattr(api, "connect", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("simulated database outage")))

    with caplog.at_level("ERROR", logger="portproject_rag.api"):
        api._log(Settings(), None, "phase13_probe", {})

    records = [json.loads(record.message) for record in caplog.records if record.name == "portproject_rag.api"]
    assert records[-1]["event"] == "audit_write_failed"
    assert records[-1]["event_type"] == "phase13_probe"
    assert records[-1]["error_type"] == "RuntimeError"
