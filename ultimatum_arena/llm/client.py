"""LLMClient Protocol and FakeLLMClient for testing."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM backend must satisfy."""

    def generate(self, prompt: str) -> str:
        """Send *prompt* to the model and return the raw text response."""
        ...


class FakeLLMClient:
    """Deterministic client for unit tests.

    Cycles through *responses* in order, repeating from the start when
    the list is exhausted.  All prompts sent are recorded in ``calls``.
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses: list[str] = responses or [
            '{"claimed_pie": 100.0, "offer": 50.0, "public_message": ""}',
        ]
        self._index: int = 0
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        response = self._responses[self._index % len(self._responses)]
        self._index += 1
        return response
