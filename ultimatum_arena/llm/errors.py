"""Custom exceptions for the LLM layer."""


class LLMError(Exception):
    """Base class for all LLM-related errors."""


class LLMParseError(LLMError):
    """Raised when the model response cannot be parsed into a valid action."""


class LLMResponseError(LLMError):
    """Raised when the provider returns an unexpected or malformed payload."""


class OllamaConnectionError(LLMError):
    """Raised when the Ollama server cannot be reached."""


class OllamaModelNotFoundError(LLMError):
    """Raised when the requested model is not available in Ollama."""


class OpenAIAPIKeyError(LLMError):
    """Raised when the OpenAI API key is missing or rejected."""


class OpenAIConnectionError(LLMError):
    """Raised when the OpenAI API cannot be reached."""


class ClaudeCLIError(LLMError):
    """Raised when the session-backed Claude Code CLI invocation fails."""
