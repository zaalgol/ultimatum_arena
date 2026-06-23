"""Tests for OpenAIResponsesClient.

Unit tests mock urllib.request.urlopen, so no API key or network access is
required.
"""

from __future__ import annotations

import json
import os
import unittest.mock as mock

import pytest

from ultimatum_arena.llm.errors import (
    LLMResponseError,
    OpenAIAPIKeyError,
    OpenAIConnectionError,
)
from ultimatum_arena.llm.openai_client import OpenAIResponsesClient
import urllib.error
import urllib.request


def _fake_response(body: dict) -> mock.MagicMock:
    raw = json.dumps(body).encode()
    cm = mock.MagicMock()
    cm.__enter__ = mock.Mock(return_value=cm)
    cm.__exit__ = mock.Mock(return_value=False)
    cm.read = mock.Mock(return_value=raw)
    return cm


class TestOpenAIResponsesClientRequestBody:
    @mock.patch("urllib.request.urlopen")
    def test_posts_to_responses_endpoint(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"output_text": "ok"})
        client = OpenAIResponsesClient(api_key="sk-test")
        client.generate("hello")

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.openai.com/v1/responses"

    @mock.patch("urllib.request.urlopen")
    def test_posts_model_and_input(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"output_text": "ok"})
        client = OpenAIResponsesClient(model="gpt-5.4-mini", api_key="sk-test")
        client.generate("my prompt")

        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["model"] == "gpt-5.4-mini"
        assert body["input"] == "my prompt"

    @mock.patch("urllib.request.urlopen")
    def test_posts_generation_options(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"output_text": "ok"})
        client = OpenAIResponsesClient(
            api_key="sk-test",
            temperature=0.3,
            max_output_tokens=123,
        )
        client.generate("hello")

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body["temperature"] == 0.3
        assert body["max_output_tokens"] == 123

    @mock.patch("urllib.request.urlopen")
    def test_adds_authorization_header(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"output_text": "ok"})
        client = OpenAIResponsesClient(api_key="sk-test")
        client.generate("hello")

        req = mock_urlopen.call_args[0][0]
        assert req.headers["Authorization"] == "Bearer sk-test"


class TestOpenAIResponsesClientApiKey:
    def test_missing_api_key_raises_clear_error(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = OpenAIResponsesClient(api_key=None)

        with pytest.raises(OpenAIAPIKeyError, match="OPENAI_API_KEY"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_reads_api_key_from_environment(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        mock_urlopen.return_value = _fake_response({"output_text": "ok"})
        client = OpenAIResponsesClient()
        client.generate("hello")

        req = mock_urlopen.call_args[0][0]
        assert req.headers["Authorization"] == "Bearer sk-env"


class TestOpenAIResponsesClientResponseParsing:
    @mock.patch("urllib.request.urlopen")
    def test_returns_output_text_field(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"output_text": "hello"})
        client = OpenAIResponsesClient(api_key="sk-test")
        assert client.generate("prompt") == "hello"

    @mock.patch("urllib.request.urlopen")
    def test_extracts_text_from_output_content(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response(
            {
                "output": [
                    {
                        "content": [
                            {"type": "output_text", "text": '{"accept": true}'}
                        ]
                    }
                ]
            }
        )
        client = OpenAIResponsesClient(api_key="sk-test")
        assert client.generate("prompt") == '{"accept": true}'

    @mock.patch("urllib.request.urlopen")
    def test_empty_text_raises_response_error(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"output": []})
        client = OpenAIResponsesClient(api_key="sk-test")

        with pytest.raises(LLMResponseError, match="output text"):
            client.generate("prompt")


class TestOpenAIResponsesClientErrors:
    def _make_http_error(self, body: dict | str, code: int = 400) -> urllib.error.HTTPError:
        raw = (json.dumps(body) if isinstance(body, dict) else body).encode()
        err = urllib.error.HTTPError(
            url="https://api.openai.com/v1/responses",
            code=code,
            msg="Bad Request",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        err.read = mock.Mock(return_value=raw)
        return err

    @mock.patch("urllib.request.urlopen")
    def test_api_key_http_error_maps_to_key_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(
            {"error": {"message": "Incorrect API key provided"}}, code=401
        )
        client = OpenAIResponsesClient(api_key="bad")

        with pytest.raises(OpenAIAPIKeyError, match="API key"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_generic_http_error_maps_to_response_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(
            {"error": {"message": "model not found"}}, code=404
        )
        client = OpenAIResponsesClient(api_key="sk-test")

        with pytest.raises(LLMResponseError, match="model not found"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_url_error_maps_to_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("offline")
        client = OpenAIResponsesClient(api_key="sk-test")

        with pytest.raises(OpenAIConnectionError, match="OpenAI"):
            client.generate("hello")

    @mock.patch("urllib.request.urlopen")
    def test_timeout_maps_to_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")
        client = OpenAIResponsesClient(api_key="sk-test", timeout=1.0)

        with pytest.raises(OpenAIConnectionError, match="timed out"):
            client.generate("hello")
