"""
AI provider abstraction layer.

All Gemini API access happens through GeminiProvider only.
The API key is read from environment variables and never exposed externally.
Other provider classes can implement the same interface in the future.
"""
import os
import time
import json
from typing import Optional
from app.core.config import settings


class AIProviderError(Exception):
    """Base class for provider errors."""
    def __init__(self, message: str, stage: str = "ai", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.retryable = retryable


class AIKeyMissingError(AIProviderError):
    def __init__(self):
        super().__init__(
            "GEMINI_API_KEY is not configured. Set it as an environment variable.",
            stage="ai_config",
            retryable=False
        )


class AIQuotaError(AIProviderError):
    def __init__(self, detail: str = ""):
        super().__init__(
            f"Gemini API quota or rate limit exceeded. {detail}".strip(),
            stage="ai_quota",
            retryable=True
        )


class AITimeoutError(AIProviderError):
    def __init__(self):
        super().__init__(
            "Gemini API request timed out.",
            stage="ai_timeout",
            retryable=True
        )


class AIResponseError(AIProviderError):
    def __init__(self, detail: str = ""):
        super().__init__(
            f"Gemini returned an unexpected or malformed response. {detail}".strip(),
            stage="ai_response",
            retryable=False
        )


class AIServiceError(AIProviderError):
    def __init__(self, detail: str = ""):
        super().__init__(
            f"Gemini service error. {detail}".strip(),
            stage="ai_service",
            retryable=True
        )


class GeminiProvider:
    """
    Provider implementation for Google Gemini API.
    Uses the google-genai SDK. API key comes from environment only.
    """

    MODEL_NAME = "gemini-2.0-flash"
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 2

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-initialise the Gemini client. Raises AIKeyMissingError if key absent."""
        if self._client is not None:
            return self._client

        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise AIKeyMissingError()

        try:
            from google import genai as genai_sdk
            self._client = genai_sdk.Client(api_key=api_key)
        except ImportError:
            raise AIServiceError("google-genai package is not installed. Run: pip install google-genai")

        return self._client

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Sends a single prompt to Gemini and returns the text response.
        Handles quota, timeout, and service failures with appropriate error types.
        """
        client = self._get_client()

        attempt = 0
        while attempt <= self.MAX_RETRIES:
            try:
                from google.genai import types as genai_types
                response = client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=8192,
                    )
                )

                # Validate response
                if not response or not response.text:
                    raise AIResponseError("Empty text in Gemini response.")

                return response.text.strip()

            except AIProviderError:
                raise
            except Exception as exc:
                err_str = str(exc).lower()

                if "429" in err_str or "quota" in err_str or "rate" in err_str:
                    if attempt < self.MAX_RETRIES:
                        time.sleep(2 ** attempt)
                        attempt += 1
                        continue
                    raise AIQuotaError(str(exc))

                if "timeout" in err_str or "deadline" in err_str or "timed out" in err_str:
                    raise AITimeoutError()

                if "invalid" in err_str and "key" in err_str:
                    raise AIKeyMissingError()

                if "500" in err_str or "503" in err_str or "unavailable" in err_str:
                    if attempt < self.MAX_RETRIES:
                        time.sleep(1)
                        attempt += 1
                        continue
                    raise AIServiceError(str(exc))

                raise AIServiceError(str(exc))

        raise AIServiceError("Max retries exhausted.")


# Global singleton — the rest of the application uses this
gemini_provider = GeminiProvider()
