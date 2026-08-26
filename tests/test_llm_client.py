"""Tests for LLMClient — model initialization and response generation."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.services.llm_client import LLMClient


@pytest.fixture
def client_no_key(monkeypatch):
    """LLMClient with no API key."""
    monkeypatch.setattr("app.services.llm_client.GEMINI_API_KEY", "")
    return LLMClient()


@pytest.fixture
def client_with_mock():
    """LLMClient with a mocked genai.Client."""
    with patch("app.services.llm_client.genai.Client") as MockClient:
        fake_response = MagicMock()
        fake_response.text = '{"status": "ok"}'
        MockClient.return_value.models.generate_content.return_value = fake_response

        import app.services.llm_client as mod
        orig_key = mod.GEMINI_API_KEY
        mod.GEMINI_API_KEY = "fake-key"
        client = LLMClient()
        yield client, MockClient
        mod.GEMINI_API_KEY = orig_key


class TestLLMClientInit:
    def test_default_model_name(self, client_with_mock):
        client, _ = client_with_mock
        assert client.model_name == "gemini-3.5-flash"

    def test_custom_model_from_config(self, monkeypatch):
        monkeypatch.setattr("app.services.llm_client.GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr("app.services.llm_client.GEMINI_MODEL", "gemini-custom-model")
        with patch("app.services.llm_client.genai.Client"):
            client = LLMClient()
            assert client.model_name == "gemini-custom-model"

    def test_no_api_key(self, client_no_key):
        assert client_no_key.client is None
        assert client_no_key.model_name is None
        with pytest.raises(ValueError, match="Missing API key"):
            client_no_key.generate_json("test prompt")


class TestLLMClientGeneration:
    def test_generate_json_success(self, client_with_mock):
        client, mock_genai = client_with_mock
        result = client.generate_json("test prompt")
        assert result == {"status": "ok"}
        mock_genai.return_value.models.generate_content.assert_called_once()
        call_kwargs = mock_genai.return_value.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-3.5-flash"

    def test_generate_json_strips_markdown(self, client_with_mock):
        client, mock_genai = client_with_mock
        mock_resp = MagicMock()
        mock_resp.text = '```json\n{"relevant": true}\n```'
        mock_genai.return_value.models.generate_content.return_value = mock_resp

        result = client.generate_json("check relevance")
        assert result == {"relevant": True}

    def test_is_job_relevant(self, client_with_mock):
        client, mock_genai = client_with_mock
        mock_resp = MagicMock()
        mock_resp.text = '{"relevant": true}'
        mock_genai.return_value.models.generate_content.return_value = mock_resp

        assert client.is_job_relevant("Software Engineer", "Develop Python APIs") is True
