"""Session-backed Claude client via the Claude Code CLI.

This client routes ``generate(prompt)`` through the local ``claude`` CLI in
headless print mode (``claude -p``), which reuses the user's existing Claude Code
session (OAuth) instead of an ``ANTHROPIC_API_KEY``. It is the "external model"
option that does not require a paid API key.

Design notes
------------
* The CLI is run from a neutral temporary working directory so the project's
  ``CLAUDE.md`` is NOT auto-discovered and injected into the model's context --
  otherwise the responder/proposer would "know" the game internals (e.g. that the
  public message is untrusted), which would contaminate the benchmark.
* ``--bare`` is deliberately NOT used: it would force ``ANTHROPIC_API_KEY`` auth
  and never read the OAuth session, defeating the purpose of this client.
* The prompt is passed over stdin (game prompts are long; this avoids shell
  quoting and command-length limits).
"""

from __future__ import annotations

import atexit
import shutil
import subprocess
import tempfile
from typing import Optional

from ultimatum_arena.llm.errors import ClaudeCLIError, LLMResponseError

# A single neutral working directory reused across all clients, created lazily
# and removed at interpreter exit.
_NEUTRAL_CWD: Optional[str] = None


def _neutral_cwd() -> str:
    """Return a cached empty temp dir with no CLAUDE.md above it."""
    global _NEUTRAL_CWD
    if _NEUTRAL_CWD is None:
        _NEUTRAL_CWD = tempfile.mkdtemp(prefix="ultimatum_claude_")
        atexit.register(_cleanup_neutral_cwd)
    return _NEUTRAL_CWD


def _cleanup_neutral_cwd() -> None:
    """Remove the cached neutral working directory if it exists."""
    global _NEUTRAL_CWD
    if _NEUTRAL_CWD is not None:
        shutil.rmtree(_NEUTRAL_CWD, ignore_errors=True)
        _NEUTRAL_CWD = None


class ClaudeCLIClient:
    """LLM client that calls the Claude Code CLI in headless mode.

    Parameters
    ----------
    model:
        Model alias or id passed to ``claude --model`` (e.g. ``"sonnet"``,
        ``"opus"``, ``"haiku"``, or a full model id). Defaults to ``"sonnet"``.
    binary:
        Name or path of the Claude CLI executable (default ``"claude"``; resolved
        via ``shutil.which`` when it has no path separator).
    timeout:
        Per-call subprocess timeout in seconds.
    extra_args:
        Additional CLI flags appended to every invocation.
    cwd:
        Working directory for the subprocess. Defaults to a neutral temp dir so
        the project ``CLAUDE.md`` is not auto-discovered.
    """

    def __init__(
        self,
        model: str = "sonnet",
        *,
        binary: str = "claude",
        timeout: float = 180.0,
        extra_args: Optional[list[str]] = None,
        cwd: Optional[str] = None,
    ) -> None:
        self.model = model
        self.binary = binary
        self.timeout = timeout
        self.extra_args = list(extra_args) if extra_args else []
        self._cwd = cwd

    def _resolve_binary(self) -> str:
        resolved = shutil.which(self.binary)
        return resolved or self.binary

    def generate(self, prompt: str) -> str:
        """Send *prompt* to Claude via the CLI and return the raw text response.

        Raises
        ------
        ClaudeCLIError
            When the CLI is missing, times out, or exits non-zero.
        LLMResponseError
            When the CLI returns empty output.
        """
        cmd = [
            self._resolve_binary(),
            "-p",
            "--output-format",
            "text",
            "--model",
            self.model,
            *self.extra_args,
        ]
        cwd = self._cwd or _neutral_cwd()

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                cwd=cwd,
            )
        except FileNotFoundError as exc:
            raise ClaudeCLIError(
                f"Claude CLI binary {self.binary!r} not found on PATH. "
                "Install Claude Code and ensure `claude` is runnable, or pass binary=..."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ClaudeCLIError(
                f"Claude CLI timed out after {self.timeout}s for model {self.model!r}."
            ) from exc

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise ClaudeCLIError(
                f"Claude CLI exited with code {proc.returncode} for model "
                f"{self.model!r}: {stderr[:500]}"
            )

        text = proc.stdout or ""
        if not text.strip():
            raise LLMResponseError(
                f"Claude CLI returned empty output for model {self.model!r}."
            )
        return text
