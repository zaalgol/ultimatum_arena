"""Ollama LLM client using the local HTTP API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ultimatum_arena.llm.errors import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    LLMResponseError,
)


class OllamaLLMClient:
    """LLM client that calls a locally-running Ollama server.

    Parameters
    ----------
    model:
        Ollama model tag, e.g. ``"gemma3"`` or ``"llama3.2"``.
    base_url:
        Base URL of the Ollama server (no trailing slash).
    temperature:
        Sampling temperature passed to the model.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        model: str = "gemma3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """Send *prompt* to Ollama and return the text response.

        Raises
        ------
        OllamaConnectionError
            When the Ollama server cannot be reached.
        OllamaModelNotFoundError
            When Ollama reports the requested model is not available.
        LLMResponseError
            When the server returns an unexpected or malformed payload.
        """
        url = f"{self.base_url}/api/generate"
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature},
            }
        ).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode()
            except Exception:
                pass
            self._raise_from_error_body(body, exc)
        except urllib.error.URLError as exc:
            raise OllamaConnectionError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from exc
        except TimeoutError as exc:
            raise OllamaConnectionError(
                f"Ollama request timed out after {self.timeout}s. "
                "The model may be loading or the prompt is too long. "
                "Try increasing the timeout or rerunning."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"Ollama returned non-JSON response: {raw!r}"
            ) from exc

        if "error" in data:
            self._raise_from_error_body(json.dumps(data), None)

        if "response" not in data:
            raise LLMResponseError(
                f"Ollama response missing 'response' field: {data!r}"
            )

        response = data["response"]
        if not isinstance(response, str) or not response.strip():
            raise LLMResponseError(
                f"Ollama returned an empty or non-string response: {response!r}"
            )

        return response

    def _raise_from_error_body(self, body: str, cause: Exception | None) -> None:
        """Parse *body* and raise the most specific error type."""
        error_msg = body
        try:
            parsed = json.loads(body)
            error_msg = parsed.get("error", body)
        except (json.JSONDecodeError, AttributeError):
            pass

        lower = error_msg.lower()
        if "not found" in lower or "pull" in lower:
            raise OllamaModelNotFoundError(
                f"Model '{self.model}' not found in Ollama. "
                f"Run: ollama pull {self.model}"
            ) from cause
        raise LLMResponseError(
            f"Ollama error: {error_msg}"
        ) from cause
