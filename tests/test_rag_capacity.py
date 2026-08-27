from __future__ import annotations

from threading import Event, Thread
from time import sleep
from uuid import UUID

import pytest

from portproject_rag import api
from portproject_rag.capacity import (
    CapacityBusyError,
    HeavyInferenceGate,
    gate_for_settings,
)
from portproject_rag.generation import GenerationResult
from portproject_rag.retrieval import RetrievalResult, RetrievalTimings, RetrievedChunk
from portproject_rag.settings import Settings


def test_gate_bounds_waiters_and_releases_in_order() -> None:
    gate = HeavyInferenceGate(limit=1, queue_capacity=1, wait_timeout_seconds=1)
    first = gate.acquire()
    ready = Event()
    acquired: list[object] = []

    def waiter() -> None:
        ready.set()
        acquired.append(gate.acquire())

    thread = Thread(target=waiter)
    thread.start()
    assert ready.wait(timeout=1)
    for _ in range(100):
        if gate.snapshot()["queue_length"] == 1:
            break
        sleep(0.005)
    assert gate.snapshot()["queue_length"] == 1
    with pytest.raises(CapacityBusyError, match="queue_full"):
        gate.acquire()
    first.release()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert len(acquired) == 1
    acquired[0].release()  # type: ignore[union-attr]
    assert gate.snapshot() == {"inference_active": 0, "inference_limit": 1, "queue_length": 0, "queue_capacity": 1}


def test_gate_timeout_does_not_leave_a_queued_or_active_slot() -> None:
    gate = HeavyInferenceGate(limit=1, queue_capacity=1, wait_timeout_seconds=0.02)
    first = gate.acquire()
    with pytest.raises(CapacityBusyError) as captured:
        gate.acquire()
    assert captured.value.reason == "queue_timeout"
    assert gate.snapshot()["queue_length"] == 0
    first.release()
    assert gate.snapshot()["inference_active"] == 0


def test_local_capacity_defaults_are_bounded() -> None:
    settings = Settings(database_url="postgresql://test@127.0.0.1:9/test")
    assert settings.heavy_rag_concurrency == 1
    assert settings.heavy_rag_queue_capacity == 1
    assert settings.heavy_rag_queue_timeout_seconds == 60


def test_api_releases_capacity_slot_when_pipeline_fails(monkeypatch) -> None:
    settings = type("CapacitySettings", (), {"heavy_rag_concurrency": 1, "heavy_rag_queue_capacity": 0, "heavy_rag_queue_timeout_seconds": 1})()
    monkeypatch.setattr(api, "_selected_local_model", lambda *_args: "test-model")
    monkeypatch.setattr(api, "retrieve", lambda *_args: (_ for _ in ()).throw(RuntimeError("probe")))
    with pytest.raises(RuntimeError, match="probe"):
        api._answer_payload(settings, "What is the policy?", None, "authority")
    assert gate_for_settings(settings).snapshot()["inference_active"] == 0


def test_api_reports_capacity_telemetry_without_changing_evidence(monkeypatch) -> None:
    chunk = RetrievedChunk(
        source_id="S1",
        document_id=UUID("00000000-0000-0000-0000-000000000001"),
        chunk_id=UUID("00000000-0000-0000-0000-000000000002"),
        document_title="Policy",
        filename="policy.pdf",
        page_number=1,
        chunk_index=1,
        chunk_text="A policy clause.",
        context_text="A policy clause.",
        section_title=None,
        clause_number=None,
        lexical_rank=1,
        dense_rank=1,
        fused_score=1.0,
        rerank_score=1.0,
    )
    settings = type("CapacitySettings", (), {"heavy_rag_concurrency": 1, "heavy_rag_queue_capacity": 0, "heavy_rag_queue_timeout_seconds": 1})()
    monkeypatch.setattr(api, "_selected_local_model", lambda *_args: "test-model")
    monkeypatch.setattr(api, "retrieve", lambda *_args: RetrievalResult([chunk], RetrievalTimings(1, 2, 3, 4, 5), 1))
    monkeypatch.setattr(api, "generate_grounded_answer", lambda *_args: GenerationResult("Grounded [S1]", 1, 1, True, None))
    payload = api._answer_payload(settings, "What is the policy?", None, "authority")
    assert payload["sources"][0]["source_id"] == "S1"
    assert payload["capacity"] == {"queue_wait_ms": 0, "inference_active": 1, "inference_limit": 1, "capacity_rejected": False}
    assert gate_for_settings(settings).snapshot()["inference_active"] == 0


def test_query_maps_capacity_rejection_to_safe_busy_response(monkeypatch) -> None:
    user = type("User", (), {"role": "authority", "principal_id": "DO:1", "user_id": 1})()
    api.app.state.settings = object()
    monkeypatch.setattr(api, "validate_query", lambda *_args: type("Guardrail", (), {"allowed": True, "cleaned_text": "What is the policy?"})())
    monkeypatch.setattr(api, "_answer_payload", lambda *_args: (_ for _ in ()).throw(CapacityBusyError("queue_full", 0)))
    monkeypatch.setattr(api, "_log", lambda *_args, **_kwargs: None)
    with pytest.raises(api.HTTPException) as captured:
        api.query(api.QueryRequest(question="What is the policy?"), user)
    assert captured.value.status_code == 503
    assert captured.value.detail["code"] == "RAG_CAPACITY_BUSY"
    assert captured.value.detail["message"] == "AI processing capacity is currently busy. Please try again shortly."
    assert "password" not in str(captured.value.detail).casefold()
