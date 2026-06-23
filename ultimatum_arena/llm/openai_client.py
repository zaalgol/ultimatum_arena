"""OpenAI Responses API client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ultimatum_arena.llm.errors import (
    LLMResponseError,
    OpenAIAPIKeyError,
    OpenAIConnectionError,
)


class OpenAIResponsesClient:
    """LLM client that calls OpenAI's Responses API.

    The API key is read from ``OPENAI_API_KEY`` unless provided explicitly.
    """

    def __init__(
        self,
        model: str = "gpt-5.4-mini",
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        temperature: float | None = 0.2,
        max_output_tokens: int = 512,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """Send *prompt* to OpenAI and return the raw text response."""
        if not self.api_key:
            raise OpenAIAPIKeyError(
                "OPENAI_API_KEY is not set. Set it in PowerShell with: "
                '$env:OPENAI_API_KEY="..." or persist it with setx OPENAI_API_KEY "..."'
            )

        url = f"{self.base_url}/responses"
        payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                pass
            self._raise_from_error_body(body, exc)
        except urllib.error.URLError as exc:
            raise OpenAIConnectionError(
                f"Cannot reach OpenAI API at {self.base_url}."
            ) from exc
        except TimeoutError as exc:
            raise OpenAIConnectionError(
                f"OpenAI request timed out after {self.timeout}s."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"OpenAI returned non-JSON response: {raw!r}"
            ) from exc

        text = self._extract_text(data)
        if not text.strip():
            raise LLMResponseError(
                f"OpenAI response did not contain output text: {data!r}"
            )
        return text

    def _extract_text(self, data: dict[str, Any]) -> str:
        """Extract text from common Responses API payload shapes."""
        output_text = data.get("output_text")
        if isinstance(output_text, str):
            return output_text

        parts: list[str] = []
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str):
                        parts.append(text)

        return "\n".join(parts)

    def _raise_from_error_body(self, body: str, cause: Exception | None) -> None:
        error_msg = body or "Unknown OpenAI API error"
        try:
            parsed = json.loads(body)
            error_obj = parsed.get("error", {})
            if isinstance(error_obj, dict):
                error_msg = str(error_obj.get("message", error_msg))
            elif isinstance(error_obj, str):
                error_msg = error_obj
        except (json.JSONDecodeError, AttributeError):
            pass

        lower = error_msg.lower()
        if "api key" in lower or "incorrect api key" in lower or "unauthorized" in lower:
            raise OpenAIAPIKeyError(f"OpenAI API key error: {error_msg}") from cause

        raise LLMResponseError(f"OpenAI API error: {error_msg}") from cause
