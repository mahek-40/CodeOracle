"""
Unit tests for GeminiProvider:
- Valid model found and selected
- Fallback cascade across multiple models
- No models found with detailed model list error
- Invalid API key
- Quota exceeded (429)
- Discovery logic
"""
import pytest
from unittest.mock import MagicMock, patch
from app.ai.provider import (
    GeminiProvider,
    AIKeyMissingError,
    AIQuotaError,
    AITimeoutError,
    AIServiceError,
    AIResponseError,
)
from app.core.config import settings


def test_provider_raises_key_missing_when_no_key():
    """Verify AIKeyMissingError when GEMINI_API_KEY is unset."""
    provider = GeminiProvider()
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True):
            with pytest.raises(AIKeyMissingError):
                provider._get_client()


def test_valid_model_found_and_selected():
    """Verify provider successfully generates content and records selected model."""
    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Here is the explanation."
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.generate("Explain this code")
        assert result == "Here is the explanation."
        assert provider.MODEL_NAME is not None
        assert mock_client.models.generate_content.called


def test_fallback_order_when_first_model_404():
    """Verify provider falls back to subsequent model when primary model returns 404."""
    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Fallback output"

    def side_effect(model, contents, config=None):
        if "2.5-flash" in model and "lite" not in model:
            raise Exception("404 NOT_FOUND. Model is no longer available.")
        return mock_response

    mock_client.models.generate_content.side_effect = side_effect

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.generate("Explain")
        assert result == "Fallback output"
        assert provider._selected_model is not None
        assert provider._selected_model != "gemini-2.5-flash"


def test_no_models_found_raises_ai_service_error_with_model_list():
    """Verify AIServiceError is raised with candidate order and available models when all fail."""
    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("404 NOT_FOUND for all models")

    mock_m1 = MagicMock()
    mock_m1.name = "models/gemini-custom-1"
    mock_m2 = MagicMock()
    mock_m2.name = "models/gemini-custom-2"
    mock_client.models.list.return_value = [mock_m1, mock_m2]

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(AIServiceError) as exc_info:
            provider.generate("Explain")
        err_msg = str(exc_info.value)
        assert "No suitable Gemini model found" in err_msg
        assert "gemini-custom-1" in err_msg or "gemini-custom-2" in err_msg


def test_invalid_api_key_raises_key_missing_error():
    """Verify provider translates invalid key API error to AIKeyMissingError."""
    provider = GeminiProvider()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API_KEY_INVALID: API key not valid. Please pass a valid API key.")

    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(AIKeyMissingError):
            provider.generate("Explain")


def test_quota_exceeded_raises_ai_quota_error():
    """Verify provider raises AIQuotaError on 429 / resource exhausted."""
    provider = GeminiProvider()
    provider.MAX_RETRIES = 1
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for quota group.")

    with patch.object(provider, "_get_client", return_value=mock_client):
        with patch.object(provider, "discover_models", return_value=[]):
            with pytest.raises(AIQuotaError):
                provider.generate("Explain")


def test_model_discovery_filters_non_text_models():
    """Verify discover_models filters out images/audio/video models."""
    provider = GeminiProvider()
    mock_client = MagicMock()

    m_text = MagicMock()
    m_text.name = "models/gemini-flash-latest"

    m_image = MagicMock()
    m_image.name = "models/imagen-3.0-generate-001"

    m_embed = MagicMock()
    m_embed.name = "models/gemini-embedding-001"

    mock_client.models.list.return_value = [m_text, m_image, m_embed]

    with patch.object(provider, "_get_client", return_value=mock_client):
        discovered = provider.discover_models(force_refresh=True)
        assert "gemini-flash-latest" in discovered
        assert "imagen-3.0-generate-001" not in discovered
        assert "gemini-embedding-001" not in discovered
