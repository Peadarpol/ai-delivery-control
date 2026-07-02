"""
Tests for src/scripts/providers.py — LLM provider abstraction (T1-E-02).

Tests provider ABC, factory function, availability checks, and
audit trail logging.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest


# ── Provider instantiation and properties ─────────────────────────────────────


class TestAnthropicProvider:
    def test_name(self, providers_mod):
        p = providers_mod.AnthropicProvider()
        assert p.name == "anthropic"

    def test_default_model(self, providers_mod):
        p = providers_mod.AnthropicProvider()
        assert "claude" in p.model or "sonnet" in p.model

    def test_custom_model(self, providers_mod):
        p = providers_mod.AnthropicProvider(model="claude-3-haiku")
        assert p.model == "claude-3-haiku"

    def test_is_available_with_key(self, providers_mod):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            p = providers_mod.AnthropicProvider()
            assert p.is_available() is True

    def test_is_available_without_key(self, providers_mod):
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            p = providers_mod.AnthropicProvider()
            assert p.is_available() is False

    def test_review_raises_without_key(self, providers_mod):
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            p = providers_mod.AnthropicProvider()
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                p.review("system", "user content")


class TestOpenAIProvider:
    def test_name(self, providers_mod):
        p = providers_mod.OpenAIProvider()
        assert p.name == "openai"

    def test_default_model(self, providers_mod):
        env = os.environ.copy()
        env.pop("AI_REVIEW_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            p = providers_mod.OpenAIProvider()
            assert p.model == "gpt-4o"

    def test_custom_base_url(self, providers_mod):
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://my-azure.openai.azure.com/v1"}):
            p = providers_mod.OpenAIProvider()
            assert "azure" in p._base_url

    def test_is_available_with_key(self, providers_mod):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            p = providers_mod.OpenAIProvider()
            assert p.is_available() is True

    def test_is_available_without_key(self, providers_mod):
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            p = providers_mod.OpenAIProvider()
            assert p.is_available() is False


class TestOllamaProvider:
    def test_name(self, providers_mod):
        p = providers_mod.OllamaProvider()
        assert p.name == "ollama"

    def test_default_model(self, providers_mod):
        env = os.environ.copy()
        env.pop("AI_REVIEW_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            p = providers_mod.OllamaProvider()
            assert "llama" in p.model

    def test_is_available_when_running(self, providers_mod):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock()
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            p = providers_mod.OllamaProvider()
            assert p.is_available() is True

    def test_is_available_when_not_running(self, providers_mod):
        with patch("urllib.request.urlopen", side_effect=ConnectionError):
            p = providers_mod.OllamaProvider()
            assert p.is_available() is False


# ── Factory function ──────────────────────────────────────────────────────────


class TestGetProvider:
    def test_default_is_anthropic(self, providers_mod):
        env = os.environ.copy()
        env.pop("AI_REVIEW_PROVIDER", None)
        env["ANTHROPIC_API_KEY"] = "sk-test"
        with patch.dict(os.environ, env, clear=True):
            p = providers_mod.get_provider()
            assert p.name == "anthropic"

    def test_env_var_override(self, providers_mod):
        with patch.dict(os.environ, {
            "AI_REVIEW_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test"
        }):
            p = providers_mod.get_provider()
            assert p.name == "openai"

    def test_explicit_arg_override(self, providers_mod):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            p = providers_mod.get_provider(provider_name="openai")
            assert p.name == "openai"

    def test_unknown_provider_raises(self, providers_mod):
        with pytest.raises(RuntimeError, match="Unknown"):
            providers_mod.get_provider(provider_name="deepseek")

    def test_unavailable_provider_raises(self, providers_mod):
        """SEC-02: Unavailable provider must raise, not silently skip."""
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="not available"):
                providers_mod.get_provider(provider_name="anthropic")


# ── Retry logic ───────────────────────────────────────────────────────────────


class TestCallApiWithRetry:
    def test_succeeds_on_first_try(self, providers_mod):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        req = MagicMock()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = providers_mod.call_api_with_retry(req, timeout=5)
        assert json.loads(result)["ok"] is True

    def test_retries_on_transient_error(self, providers_mod):
        import urllib.error

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        # Fail twice, succeed on third
        with patch("urllib.request.urlopen", side_effect=[
            urllib.error.URLError("transient"),
            urllib.error.URLError("transient"),
            mock_resp,
        ]), patch("time.sleep"):  # Skip actual delays
            result = providers_mod.call_api_with_retry(req=MagicMock(), timeout=5)
        assert json.loads(result)["ok"] is True


class TestReviewProviderCallLlm:
    def test_call_llm_routes_to_raw_completion(self, providers_mod):
        # Create a dummy provider subclass since ReviewProvider is an ABC
        class DummyProvider(providers_mod.ReviewProvider):
            def review(self, system: str, user_content: str):
                return {}

            def raw_completion(self, system: str, user_content: str) -> str:
                self.last_token_usage = {"input_tokens": 10, "output_tokens": 20}
                return f"Response to {user_content} under {system}"

            @property
            def name(self) -> str:
                return "dummy"

            @property
            def model(self) -> str:
                return "dummy-model"

            def is_available(self) -> bool:
                return True

        p = DummyProvider()
        res_true, input_tok_true, output_tok_true = p.call_llm(
            system_prompt="sys-prompt",
            user_prompt="user-prompt",
            max_tokens=1000,
            json_mode=True
        )
        res_false, input_tok_false, output_tok_false = p.call_llm(
            system_prompt="sys-prompt",
            user_prompt="user-prompt",
            max_tokens=1000,
            json_mode=False
        )
        assert res_true == "Response to user-prompt under sys-prompt"
        assert input_tok_true == 10
        assert output_tok_true == 20

        # Verify that json_mode is a no-op (outputs are identical for both calls)
        assert res_true == res_false
        assert input_tok_true == input_tok_false
        assert output_tok_true == output_tok_false

