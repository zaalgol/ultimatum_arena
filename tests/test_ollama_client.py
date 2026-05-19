"""Tests for OllamaLLMClient.

Unit tests mock urllib.request.urlopen so no running Ollama instance is needed.
The optional integration test at the bottom is skipped unless RUN_OLLAMA_TESTS=1.
"""

from __future__ import annotations

import json
import os
import unittest.mock as mock
from io import BytesIO

import pytest

from ultimatum_arena.llm.errors import (
    LLMResponseError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)
from ultimatum_arena.llm.ollama_client import OllamaLLMClient
import urllib.error
import urllib.request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_response(body: dict) -> mock.MagicMock:
    """Return a mock that mimics urllib.request.urlopen context manager."""
    raw = json.dumps(body).encode()
    cm = mock.MagicMock()
    cm.__enter__ = mock.Mock(return_value=cm)
    cm.__exit__ = mock.Mock(return_value=False)
    cm.read = mock.Mock(return_value=raw)
    return cm


# ---------------------------------------------------------------------------
# OllamaLLMClient unit tests (mocked HTTP)
# ---------------------------------------------------------------------------

class TestOllamaLLMClientRequestBody:
    @mock.patch("urllib.request.urlopen")
    def test_posts_correct_model(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "ok"})
        client = OllamaLLMClient(model="llama3.2")
        client.generate("hello")

        _, kwargs = mock_urlopen.call_args
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["model"] == "llama3.2"

    @mock.patch("urllib.request.urlopen")
    def test_posts_stream_false(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "ok"})
        client = OllamaLLMClient()
        client.generate("hello")

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["stream"] is False

    @mock.patch("urllib.request.urlopen")
    def test_posts_temperature(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "ok"})
        client = OllamaLLMClient(temperature=0.7)
        client.generate("hello")

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["options"]["temperature"] == 0.7

    @mock.patch("urllib.request.urlopen")
    def test_posts_prompt(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "ok"})
        client = OllamaLLMClient()
        client.generate("my prompt text")

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["prompt"] == "my prompt text"

    @mock.patch("urllib.request.urlopen")
    def test_url_includes_base_url(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "ok"})
        client = OllamaLLMClient(base_url="http://myhost:11434")
        client.generate("x")

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://myhost:11434/api/generate"

    @mock.patch("urllib.request.urlopen")
    def test_trailing_slash_stripped(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "ok"})
        client = OllamaLLMClient(base_url="http://localhost:11434/")
        client.generate("x")

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://localhost:11434/api/generate"


class TestOllamaLLMClientSuccessfulResponse:
    @mock.patch("urllib.request.urlopen")
    def test_returns_response_field(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "hello world"})
        client = OllamaLLMClient()
        result = client.generate("prompt")
        assert result == "hello world"

    @mock.patch("urllib.request.urlopen")
    def test_returns_multiline_response(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response(
            {"response": '{"claimed_pie": 100.0, "offer": 50.0}'}
        )
        client = OllamaLLMClient()
        result = client.generate("prompt")
        assert "claimed_pie" in result


class TestOllamaLLMClientHttpError:
    """HTTPError must be handled before URLError (HTTPError is a subclass)."""

    def _make_http_error(self, body: dict | str, code: int = 400) -> urllib.error.HTTPError:
        raw = (json.dumps(body) if isinstance(body, dict) else body).encode()
        err = urllib.error.HTTPError(
            url="http://localhost:11434/api/generate",
            code=code,
            msg="Bad Request",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        err.read = mock.Mock(return_value=raw)
        return err

    @mock.patch("urllib.request.urlopen")
    def test_http_error_model_not_found_raises_model_not_found(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(
            {"error": "model 'gemma3' not found, try pulling it first"}
        )
        client = OllamaLLMClient(model="gemma3")
        with pytest.raises(OllamaModelNotFoundError, match="gemma3"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_http_error_model_not_found_includes_pull_hint(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(
            {"error": "model 'mymodel' not found, try pulling it first"}
        )
        client = OllamaLLMClient(model="mymodel")
        with pytest.raises(OllamaModelNotFoundError, match="ollama pull"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_generic_http_error_raises_llm_response_error_not_connection(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(
            {"error": "internal server error"}, code=500
        )
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_generic_http_error_does_not_raise_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(
            {"error": "something else"}, code=500
        )
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")
        # Confirm it is NOT OllamaConnectionError
        try:
            client.generate("hello")
        except OllamaConnectionError:
            pytest.fail("HTTPError should not map to OllamaConnectionError")
        except LLMResponseError:
            pass  # correct


class TestOllamaLLMClientConnectionError:
    @mock.patch("urllib.request.urlopen")
    def test_raises_ollama_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        client = OllamaLLMClient()
        with pytest.raises(OllamaConnectionError, match="Ollama"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_error_message_mentions_ollama_serve(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        client = OllamaLLMClient()
        with pytest.raises(OllamaConnectionError, match="ollama serve"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_bare_timeout_error_raises_connection_error(self, mock_urlopen):
        """Python 3.3+ socket.timeout (TimeoutError) must be caught and re-raised."""
        mock_urlopen.side_effect = TimeoutError("timed out")
        client = OllamaLLMClient(timeout=1.0)
        with pytest.raises(OllamaConnectionError, match="timed out"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_timeout_error_message_suggests_rerun(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")
        client = OllamaLLMClient(timeout=1.0)
        with pytest.raises(OllamaConnectionError, match="120|timed out|rerun|timeout"):
            client.generate("hello")


class TestOllamaLLMClientModelNotFound:
    @mock.patch("urllib.request.urlopen")
    def test_raises_model_not_found(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response(
            {"error": "model 'gemma3' not found, try pulling it first"}
        )
        client = OllamaLLMClient(model="gemma3")
        with pytest.raises(OllamaModelNotFoundError, match="gemma3"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_pull_hint_in_message(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response(
            {"error": "model 'mymodel' not found, try pulling it first"}
        )
        client = OllamaLLMClient(model="mymodel")
        with pytest.raises(OllamaModelNotFoundError, match="ollama pull"):
            client.generate("hello")


class TestOllamaLLMClientResponseErrors:
    @mock.patch("urllib.request.urlopen")
    def test_missing_response_field_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"model": "gemma3", "done": True})
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError, match="response"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_generic_error_field_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"error": "something went wrong"})
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_non_json_response_raises(self, mock_urlopen):
        cm = mock.MagicMock()
        cm.__enter__ = mock.Mock(return_value=cm)
        cm.__exit__ = mock.Mock(return_value=False)
        cm.read = mock.Mock(return_value=b"<html>not json</html>")
        mock_urlopen.return_value = cm

        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError, match="non-JSON"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_empty_string_response_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": ""})
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_whitespace_only_response_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": "   "})
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_null_response_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": None})
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_non_string_response_raises(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"response": 42})
        client = OllamaLLMClient()
        with pytest.raises(LLMResponseError):
            client.generate("hello")


# ---------------------------------------------------------------------------
# Integration test — skipped unless RUN_OLLAMA_TESTS=1
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("RUN_OLLAMA_TESTS"),
    reason="Set RUN_OLLAMA_TESTS=1 to run integration tests against a live Ollama server",
)
class TestOllamaIntegration:
    def test_generate_returns_non_empty_string(self):
        client = OllamaLLMClient(model="gemma3", temperature=0.0)
        result = client.generate(
            'Respond with ONLY this JSON: {"accept": true}'
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_model_not_found_raises(self):
        client = OllamaLLMClient(model="this-model-does-not-exist-xyz")
        with pytest.raises(OllamaModelNotFoundError):
            client.generate("hello")
