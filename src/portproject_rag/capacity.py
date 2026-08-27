"""Bounded local RAG capacity control.

The local CPU deployment owns one process-local gate around the complete
retrieval/rerank/generation pipeline.  It deliberately uses a bounded waiter
count rather than an unbounded executor queue: a request either gets a slot,
waits for a configured interval, or receives a safe capacity response.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from threading import Condition
from time import monotonic
from typing import Any

CAPACITY_BUSY_MESSAGE = "AI processing capacity is currently busy. Please try again shortly."


class CapacityBusyError(RuntimeError):
    """Raised when a bounded local RAG gate cannot accept a request."""

    def __init__(self, reason: str, queue_wait_ms: int) -> None:
        self.reason = reason
        self.queue_wait_ms = queue_wait_ms
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class CapacityLease:
    """A process-local heavy-inference slot and its safe telemetry."""

    queue_wait_ms: int
    active_at_acquire: int
    limit: int
    _gate: "HeavyInferenceGate"
    _released: bool = False

    def release(self) -> None:
        # A finally block should release exactly once.  The guard makes the
        # operation harmless for defensive cleanup and cancellation paths.
        if not self._released:
            self._gate.release()
            object.__setattr__(self, "_released", True)

    def __enter__(self) -> "CapacityLease":
        return self

    def __exit__(self, _exc_type: Any, _exc_value: Any, _traceback: Any) -> None:
        self.release()


class HeavyInferenceGate:
    """A bounded FIFO-like condition gate for one process.

    The local evidence supports a limit of one active pipeline.  The class
    accepts a limit up to two for controlled experiments, while keeping both
    active slots and waiting requests explicitly bounded.
    """

    def __init__(self, limit: int = 1, queue_capacity: int = 1, wait_timeout_seconds: float = 30.0) -> None:
        if limit < 1 or limit > 2:
            raise ValueError("heavy inference limit must be between 1 and 2")
        if queue_capacity < 0:
            raise ValueError("queue capacity cannot be negative")
        if wait_timeout_seconds <= 0:
            raise ValueError("queue wait timeout must be positive")
        self.limit = limit
        self.queue_capacity = queue_capacity
        self.wait_timeout_seconds = wait_timeout_seconds
        self._condition = Condition()
        self._active = 0
        self._queued = 0

    def snapshot(self) -> dict[str, int]:
        with self._condition:
            return {
                "inference_active": self._active,
                "inference_limit": self.limit,
                "queue_length": self._queued,
                "queue_capacity": self.queue_capacity,
            }

    def acquire(self) -> CapacityLease:
        started = monotonic()
        with self._condition:
            if self._active >= self.limit:
                if self._queued >= self.queue_capacity:
                    raise CapacityBusyError("queue_full", 0)
                self._queued += 1
                deadline = started + self.wait_timeout_seconds
                try:
                    while self._active >= self.limit:
                        remaining = deadline - monotonic()
                        if remaining <= 0:
                            raise CapacityBusyError("queue_timeout", round((monotonic() - started) * 1000))
                        self._condition.wait(timeout=remaining)
                except CapacityBusyError:
                    raise
                finally:
                    self._queued -= 1
            self._active += 1
            return CapacityLease(
                queue_wait_ms=round((monotonic() - started) * 1000),
                active_at_acquire=self._active,
                limit=self.limit,
                _gate=self,
            )

    def release(self) -> None:
        with self._condition:
            if self._active <= 0:
                raise RuntimeError("heavy inference gate released without an active slot")
            self._active -= 1
            self._condition.notify_all()


@lru_cache(maxsize=8)
def _cached_gate(limit: int, queue_capacity: int, wait_timeout_seconds: int) -> HeavyInferenceGate:
    return HeavyInferenceGate(limit, queue_capacity, wait_timeout_seconds)


def gate_for_settings(settings: object) -> HeavyInferenceGate:
    """Return the stable gate for this process and settings tuple.

    ``getattr`` defaults keep small unit-test settings doubles compatible with
    the API helper without weakening real ``Settings`` validation.
    """

    limit = int(getattr(settings, "heavy_rag_concurrency", 1))
    queue_capacity = int(getattr(settings, "heavy_rag_queue_capacity", 1))
    wait_timeout_seconds = int(getattr(settings, "heavy_rag_queue_timeout_seconds", 30))
    return _cached_gate(limit, queue_capacity, wait_timeout_seconds)
