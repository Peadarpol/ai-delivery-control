#!/usr/bin/env python3
"""
LLM Review Provider Abstraction (T1-E-02)

Design: Transport abstraction, not review orchestration.

This module provides a thin interface over LLM API endpoints.  Each provider
handles authentication, HTTP transport, request formatting, response parsing,
and retry logic.  Providers do NOT:
  - Construct the user message (caller's responsibility)
  - Validate the response against ReviewVerdict (caller's responsibility)
  - Implement routing, context selection, or review logic

Return type is raw ``dict`` (parsed JSON from the LLM), not ``ReviewVerdict``.
The caller in ``ai_review._run_review()`` constructs ``ReviewVerdict`` from
the dict.  This is intentional: the LLM's JSON output is not reliably
Pydantic-valid, so validation is better done at the call site with explicit
error handling.

ARCH-01: Provider is a transport abstraction.  Message assembly is the
caller's responsibility.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from harness_utils import get_harness_config
except ImportError:
    def get_harness_config(section, key=None, default=None):
        if section == "model_routing" and key == "max_tokens":
            return 4096
        return default


# ── Config defaults ───────────────────────────────────────────────────────────

DEFAULT_TIMEOUT = int(os.environ.get("AI_REVIEW_TIMEOUT", "60"))
DEFAULT_MODEL = os.environ.get("AI_REVIEW_MODEL", "claude-sonnet-4-6")
MAX_DIFF_CHARS = 200_000


# ── Shared utilities ──────────────────────────────────────────────────────────


def call_api_with_retry(
    req: urllib.request.Request,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> bytes:
    """Execute an API request with exponential-backoff retry on transient errors."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return bytes(resp.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt) + (random.random() * 0.5)
                time.sleep(delay)
    raise last_error  # type: ignore[misc]


def _strip_json_fences(raw: str) -> str:
    """Strip markdown code fences if the model wraps JSON in them."""
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw


# ── Abstract Base ─────────────────────────────────────────────────────────────


class ReviewProvider(ABC):
    """Abstract base for LLM review providers.

    Each provider handles HTTP transport, authentication, request formatting,
    and JSON response parsing.  The ``review()`` method accepts pre-assembled
    system and user content strings and returns the raw parsed JSON dict.

    The caller (``ai_review._run_review()``) is responsible for:
      - Constructing the user message from diff, commit msg, context, etc.
      - Validating the returned dict against ``ReviewVerdict``
    """

    @abstractmethod
    def review(self, system: str, user_content: str) -> Dict[str, Any]:
        """Send a review request and return parsed JSON response.

        Args:
            system: The system prompt (reviewer personality and rules).
            user_content: The pre-assembled user message (diff, commit msg,
                          architecture context, repo map, ADR context).

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            RuntimeError: If the provider is misconfigured.
            urllib.error.URLError: On network failure (after retries).
            json.JSONDecodeError: If the LLM response is not valid JSON.
        """
        ...

    @abstractmethod
    def raw_completion(self, system: str, user_content: str) -> str:
        """Send a completion request and return the raw text response from the LLM.

        This method must also calculate and update self.last_token_usage.
        """
        ...

    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> tuple[str, int, int]:
        """Call LLM and return (response_text, input_tokens, output_tokens) to support check_spec.py.

        Note: json_mode is accepted for call-site parity with check_spec.py; actual JSON
        formatting is determined per-provider (Ollama/OpenAI force it internally via
        raw_completion, Anthropic relies on system_prompt instructions) and this flag is
        currently a no-op. Do not assume passing json_mode=False changes behavior.
        """
        response = self.raw_completion(system_prompt, user_prompt)
        usage = self.last_token_usage
        return (
            response,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )

    @property
    def last_token_usage(self) -> Dict[str, int]:
        """Return thread-safe token usage of the last request."""
        if not hasattr(self, "_local_state"):
            self._local_state = threading.local()
        return getattr(self._local_state, "last_token_usage", {})

    @last_token_usage.setter
    def last_token_usage(self, value: Dict[str, int]) -> None:
        if not hasattr(self, "_local_state"):
            self._local_state = threading.local()
        self._local_state.last_token_usage = value

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier for logging (e.g., 'anthropic', 'openai')."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Active model name for logging and audit trail."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is ready (API key set, endpoint reachable).

        SEC-02: Each provider must implement availability checking.
        The factory verifies availability before returning.
        """
        ...


# ── Anthropic Provider ────────────────────────────────────────────────────────


class AnthropicProvider(ReviewProvider):
    """Anthropic Claude API provider (default).

    Uses stdlib ``urllib.request`` — zero external dependencies.
    Requires ``ANTHROPIC_API_KEY`` environment variable.
    """

    def __init__(self, model: str | None = None):
        self._model = model or DEFAULT_MODEL
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._max_tokens = get_harness_config("model_routing", "max_tokens", default=4096)

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def review(self, system: str, user_content: str) -> Dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

        if len(user_content) > MAX_DIFF_CHARS:
            raise RuntimeError(
                f"Content too large ({len(user_content):,} chars > "
                f"{MAX_DIFF_CHARS:,}); skip guard should have caught this."
            )

        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        body = json.loads(call_api_with_retry(req).decode("utf-8"))
        # Thread-safe token usage tracking
        usage = body.get("usage", {})
        self.last_token_usage = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "reasoning_tokens": usage.get("thinking_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        }
        raw = body["content"][0]["text"].strip()
        raw = _strip_json_fences(raw)
        return json.loads(raw)

    def raw_completion(self, system: str, user_content: str) -> str:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

        if len(user_content) > MAX_DIFF_CHARS:
            raise RuntimeError(
                f"Content too large ({len(user_content):,} chars > "
                f"{MAX_DIFF_CHARS:,}); skip guard should have caught this."
            )

        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        body = json.loads(call_api_with_retry(req).decode("utf-8"))
        usage = body.get("usage", {})
        self.last_token_usage = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "reasoning_tokens": usage.get("thinking_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        }
        raw = body["content"][0]["text"].strip()
        return _strip_json_fences(raw)


# ── OpenAI-Compatible Provider ────────────────────────────────────────────────


class OpenAIProvider(ReviewProvider):
    """OpenAI-compatible API provider.

    Works with OpenAI, Azure OpenAI, Groq, Together, and any endpoint
    that implements the ``/v1/chat/completions`` API.

    Uses stdlib ``urllib.request`` — zero external dependencies.
    Requires ``OPENAI_API_KEY`` environment variable.
    Optional ``OPENAI_BASE_URL`` to override the default endpoint.
    """

    def __init__(self, model: str | None = None):
        self._model = model or os.environ.get("AI_REVIEW_MODEL", "gpt-4o")
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        self._base_url = os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        ).rstrip("/")
        self._max_tokens = get_harness_config("model_routing", "max_tokens", default=4096)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def review(self, system: str, user_content: str) -> Dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        body = json.loads(call_api_with_retry(req).decode("utf-8"))
        # Thread-safe token usage tracking
        usage = body.get("usage", {})
        completion_details = usage.get("completion_tokens_details", {})
        reasoning = completion_details.get("reasoning_tokens", 0)
        self.last_token_usage = {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": reasoning,
            "cache_read_input_tokens": 0,
        }
        raw = body["choices"][0]["message"]["content"].strip()
        raw = _strip_json_fences(raw)
        return json.loads(raw)

    def raw_completion(self, system: str, user_content: str) -> str:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        body = json.loads(call_api_with_retry(req).decode("utf-8"))
        usage = body.get("usage", {})
        completion_details = usage.get("completion_tokens_details", {})
        reasoning = completion_details.get("reasoning_tokens", 0)
        self.last_token_usage = {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": reasoning,
            "cache_read_input_tokens": 0,
        }
        raw = body["choices"][0]["message"]["content"].strip()
        return _strip_json_fences(raw)


# ── Ollama Provider ───────────────────────────────────────────────────────────


class OllamaProvider(ReviewProvider):
    """Local Ollama provider for air-gapped operation.

    Uses stdlib ``urllib.request`` against ``http://localhost:11434``.
    Verdicts from this provider should be logged with ``verdict_tier="local"``.

    No API key required.  Model defaults to ``AI_REVIEW_MODEL`` env var
    or ``llama3.1:8b`` if not set.
    """

    def __init__(self, model: str | None = None):
        self._model = model or os.environ.get("AI_REVIEW_MODEL", "llama3.1:8b")
        self._base_url = os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ).rstrip("/")
        self._max_tokens = get_harness_config("model_routing", "max_tokens", default=4096)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Ollama is running by sending a lightweight HEAD request."""
        try:
            req = urllib.request.Request(self._base_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def review(self, system: str, user_content: str) -> Dict[str, Any]:
        payload = json.dumps(
            {
                "model": self._model,
                "system": system,
                "prompt": user_content,
                "format": "json",
                "stream": False,
                "options": {"num_predict": self._max_tokens},
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # Ollama can be slow — use a longer timeout for local models.
        body = json.loads(
            call_api_with_retry(req, timeout=120, max_retries=2).decode("utf-8")
        )
        # Thread-safe token usage tracking
        self.last_token_usage = {
            "input_tokens": body.get("prompt_eval_count", 0),
            "output_tokens": body.get("eval_count", 0),
            "reasoning_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        raw = body.get("response", "{}").strip()
        raw = _strip_json_fences(raw)
        return json.loads(raw)

    def raw_completion(self, system: str, user_content: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "system": system,
                "prompt": user_content,
                "format": "json",
                "stream": False,
                "options": {"num_predict": self._max_tokens},
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        body = json.loads(
            call_api_with_retry(req, timeout=120, max_retries=2).decode("utf-8")
        )
        self.last_token_usage = {
            "input_tokens": body.get("prompt_eval_count", 0),
            "output_tokens": body.get("eval_count", 0),
            "reasoning_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        raw = body.get("response", "{}").strip()
        return _strip_json_fences(raw)


# ── Provider Factory ──────────────────────────────────────────────────────────

# Registry of known providers — add new providers here.
_PROVIDER_REGISTRY: Dict[str, type[ReviewProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def _read_config_provider() -> str | None:
    """Read the provider name from .agent/config.yaml if present.

    Uses simple string matching to avoid a YAML dependency.
    """
    try:
        config_path = Path.cwd() / ".agent" / "config.yaml"
        if not config_path.exists():
            return None
        content = config_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("provider:"):
                value = stripped.split(":", 1)[1].strip().strip("\"'")
                if value in _PROVIDER_REGISTRY:
                    return value
    except Exception:
        pass
    return None


def get_provider(
    provider_name: str | None = None,
    model: str | None = None,
    tier: str | None = None,
) -> ReviewProvider:
    """Factory function with availability verification.

    Resolution order:
      1. ``provider_name`` argument (explicit)
      2. ``tier`` argument (resolves provider and model from config model_routing)
      3. ``AI_REVIEW_PROVIDER`` environment variable
      4. ``.agent/config.yaml`` ``ai_review.provider`` field
      5. Default: ``"anthropic"``

    SEC-01: Logs selected provider name in stdout for audit traceability.
    The ``verdict_tier`` field in ``ReviewVerdict`` captures cloud vs local.

    ARCH-02: Signature is forward-compatible with a future ``fallback``
    parameter for degrade-to-local chains.  Not implemented in v1.1.0.

    Args:
        provider_name: Override the provider selection.
        model: Override the model name (provider-specific).
        tier: Optional model tier (e.g. 'budget', 'review') to resolve from config.

    Returns:
        An initialised ``ReviewProvider`` instance.

    Raises:
        RuntimeError: If the selected provider is not available (missing
                      API key, unreachable endpoint) or unknown.
    """
    if tier:
        try:
            config_path = Path.cwd() / ".agent" / "config.yaml"
            if config_path.exists():
                content = config_path.read_text(encoding="utf-8")
                p_match = re.search(rf"^\s*{tier}_provider:\s*([^\s\n#]+)", content, re.MULTILINE)
                m_match = re.search(rf"^\s*{tier}_model:\s*([^\s\n#]+)", content, re.MULTILINE)
                if p_match and not provider_name:
                    provider_name = p_match.group(1).strip().strip("\"'")
                if m_match and not model:
                    model = m_match.group(1).strip().strip("\"'")
        except Exception:
            pass

    # 1. Resolve provider name
    name = (
        provider_name
        or os.environ.get("AI_REVIEW_PROVIDER")
        or _read_config_provider()
        or "anthropic"
    ).lower()

    if name not in _PROVIDER_REGISTRY:
        raise RuntimeError(
            f"Unknown AI review provider: '{name}'. "
            f"Available: {', '.join(sorted(_PROVIDER_REGISTRY.keys()))}"
        )

    # 2. Instantiate
    provider_cls = _PROVIDER_REGISTRY[name]
    provider = provider_cls(model=model)

    # 3. Check availability (SEC-02)
    if not provider.is_available():
        raise RuntimeError(
            f"AI review provider '{name}' is not available. "
            f"Check that the required API key or service is configured."
        )

    # SEC-01: Log provider selection for audit traceability
    print(f"[REVIEW] Provider: {provider.name} (model: {provider.model})")

    return provider
