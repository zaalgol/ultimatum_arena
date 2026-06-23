"""Tests for ClaudeCLIClient (session-backed Claude via the CLI).

No real `claude` process is spawned: subprocess.run is monkeypatched.
"""

from __future__ import annotations

import subprocess
import types

import pytest

from ultimatum_arena.llm import claude_cli_client as mod
from ultimatum_arena.llm.claude_cli_client import ClaudeCLIClient
from ultimatum_arena.llm.client import LLMClient
from ultimatum_arena.llm.errors import ClaudeCLIError, LLMResponseError


def _fake_run(stdout="", stderr="", returncode=0, record=None):
    def _run(cmd, **kwargs):
        if record is not None:
            record["cmd"] = cmd
            record["kwargs"] = kwargs
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return _run


class TestProtocol:
    def test_satisfies_llm_client_protocol(self):
        assert isinstance(ClaudeCLIClient(), LLMClient)

    def test_default_model_is_sonnet(self):
        assert ClaudeCLIClient().model == "sonnet"


class TestGenerate:
    def test_returns_stdout(self, monkeypatch):
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout='{"accept": true}\n'))
        assert ClaudeCLIClient().generate("hi") == '{"accept": true}\n'

    def test_command_uses_print_and_text_format(self, monkeypatch):
        rec: dict = {}
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout="ok", record=rec))
        ClaudeCLIClient(model="opus").generate("hello")
        cmd = rec["cmd"]
        assert "-p" in cmd
        assert "--output-format" in cmd and "text" in cmd
        assert "--model" in cmd and "opus" in cmd

    def test_prompt_passed_via_stdin(self, monkeypatch):
        rec: dict = {}
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout="ok", record=rec))
        ClaudeCLIClient().generate("THE PROMPT")
        assert rec["kwargs"]["input"] == "THE PROMPT"
        assert rec["kwargs"]["text"] is True

    def test_runs_in_a_working_directory(self, monkeypatch):
        rec: dict = {}
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout="ok", record=rec))
        ClaudeCLIClient().generate("p")
        assert rec["kwargs"]["cwd"]  # a neutral cwd is provided

    def test_custom_cwd_respected(self, monkeypatch, tmp_path):
        rec: dict = {}
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout="ok", record=rec))
        ClaudeCLIClient(cwd=str(tmp_path)).generate("p")
        assert rec["kwargs"]["cwd"] == str(tmp_path)

    def test_extra_args_appended(self, monkeypatch):
        rec: dict = {}
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout="ok", record=rec))
        ClaudeCLIClient(extra_args=["--add-dir", "X"]).generate("p")
        assert rec["cmd"][-2:] == ["--add-dir", "X"]


class TestErrors:
    def test_missing_binary_raises_claude_cli_error(self, monkeypatch):
        def _boom(cmd, **kwargs):
            raise FileNotFoundError("no claude")
        monkeypatch.setattr(mod.subprocess, "run", _boom)
        with pytest.raises(ClaudeCLIError, match="not found"):
            ClaudeCLIClient().generate("p")

    def test_nonzero_exit_raises_claude_cli_error(self, monkeypatch):
        monkeypatch.setattr(
            mod.subprocess, "run", _fake_run(stdout="", stderr="boom", returncode=2)
        )
        with pytest.raises(ClaudeCLIError, match="exited with code 2"):
            ClaudeCLIClient().generate("p")

    def test_empty_output_raises_response_error(self, monkeypatch):
        monkeypatch.setattr(mod.subprocess, "run", _fake_run(stdout="   \n", returncode=0))
        with pytest.raises(LLMResponseError, match="empty output"):
            ClaudeCLIClient().generate("p")

    def test_timeout_raises_claude_cli_error(self, monkeypatch):
        def _timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 1))
        monkeypatch.setattr(mod.subprocess, "run", _timeout)
        with pytest.raises(ClaudeCLIError, match="timed out"):
            ClaudeCLIClient(timeout=5.0).generate("p")
