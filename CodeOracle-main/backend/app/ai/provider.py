"""
AI provider abstraction layer.

All Gemini API access happens through GeminiProvider only.
The API key is read from environment variables and never exposed externally.
Features dynamic model discovery, unavailable model pruning, resilient fallback cascade, and explicit startup diagnostics.
"""
import os
import time
import logging
from typing import Optional, List, Set, Dict, Any
from app.core.config import settings

logger = logging.getLogger("codeoracle.ai")
logging.basicConfig(level=logging.INFO)


class AIProviderError(Exception):
    """Base class for provider errors."""
    def __init__(self, message: str, stage: str = "ai", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.retryable = retryable


class AIKeyMissingError(AIProviderError):
    def __init__(self, detail: str = ""):
        msg = "GEMINI_API_KEY is not configured. Set it as an environment variable."
        if detail:
            msg = f"{msg} ({detail})"
        super().__init__(msg, stage="ai_config", retryable=False)


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
    Provider implementation for Google Gemini API with dynamic model discovery,
    unavailable model pruning, and robust multi-tier fallback cascade.
    """

    DEFAULT_FALLBACK_ORDER: List[str] = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.7-flash",
        "gemini-3.1-flash-lite",
    ]

    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 2

    def __init__(self):
        self._client = None
        self._selected_model: Optional[str] = None
        self._discovered_models: Optional[List[str]] = None
        self._unavailable_models: Set[str] = set()

    @property
    def MODEL_NAME(self) -> str:
        """Returns the currently active or configured Gemini model name."""
        if self._selected_model:
            return self._selected_model
        return settings.GEMINI_MODEL or self.DEFAULT_FALLBACK_ORDER[0]

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

    def discover_models(self, force_refresh: bool = False) -> List[str]:
        """
        Queries the Gemini API to list all available models and filter text generation models.
        Logs discovered models during startup.
        """
        if self._discovered_models is not None and not force_refresh:
            return self._discovered_models

        client = self._get_client()
        try:
            models_list = list(client.models.list())
            discovered: List[str] = []

            for m in models_list:
                raw_name = getattr(m, "name", "")
                short_name = raw_name.replace("models/", "").strip()
                if not short_name:
                    continue

                # Filter out non-text models (audio-only, image generation, video, embeddings)
                skip_keywords = ["imagen", "veo", "embedding", "tts", "aqa", "robotics", "live", "clip"]
                if any(k in short_name.lower() for k in skip_keywords):
                    continue

                discovered.append(short_name)

            self._discovered_models = discovered
            logger.info(f"Discovered {len(discovered)} Gemini text models from API: {discovered}")
            return self._discovered_models

        except AIProviderError:
            raise
        except Exception as exc:
            err_str = str(exc).lower()
            if "invalid" in err_str and "key" in err_str:
                raise AIKeyMissingError(str(exc))
            if "429" in err_str or "quota" in err_str:
                raise AIQuotaError(str(exc))
            logger.warning(f"Could not list Gemini models from API: {exc}")
            return []

    def get_candidate_models(self) -> List[str]:
        """
        Builds the candidate fallback order starting with active selected model (if any),
        followed by user-configured model, standard fallback cascade, and discovered API models,
        excluding any models known to return 404/unavailable.
        """
        candidates: List[str] = []

        # 1. Active selected model first
        if self._selected_model and self._selected_model not in self._unavailable_models:
            candidates.append(self._selected_model)

        # 2. User-specified model if set
        if settings.GEMINI_MODEL and settings.GEMINI_MODEL not in self._unavailable_models:
            candidates.append(settings.GEMINI_MODEL)

        # 3. Standard fallback order
        for m in self.DEFAULT_FALLBACK_ORDER:
            if m not in self._unavailable_models:
                candidates.append(m)

        # 4. Discovered models from API
        if self._discovered_models:
            for m in self._discovered_models:
                if m not in self._unavailable_models and m not in candidates:
                    candidates.append(m)

        return list(dict.fromkeys(candidates))

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Sends a prompt to Gemini with automatic model discovery and multi-tier fallback.
        Handles quota, timeout, and service failures with appropriate error types.
        """
        client = self._get_client()
        candidate_models = self.get_candidate_models()

        last_error = None
        attempted_models: List[str] = []

        for model_name in candidate_models:
            attempted_models.append(model_name)
            attempt = 0

            while attempt <= self.MAX_RETRIES:
                try:
                    from google.genai import types as genai_types
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=8192,
                        )
                    )

                    # Validate response text
                    if not response or not response.text:
                        raise AIResponseError("Empty text in Gemini response.")

                    # Successfully generated content — cache active model
                    if self._selected_model != model_name:
                        self._selected_model = model_name
                        logger.info(f"Successfully selected active Gemini model: {model_name}")

                    return response.text.strip()

                except AIProviderError:
                    raise
                except Exception as exc:
                    err_str = str(exc).lower()
                    last_error = exc

                    # 404 NOT_FOUND / no longer available -> prune model and move to next in cascade
                    if "not_found" in err_str or "404" in err_str or "no longer available" in err_str or "not supported" in err_str:
                        logger.warning(f"Model '{model_name}' is unavailable ({exc}). Pruning from candidates...")
                        self._unavailable_models.add(model_name)
                        if self._selected_model == model_name:
                            self._selected_model = None
                        break

                    # 429 Rate Limit / Quota Exceeded -> exponential backoff then try next model or raise
                    if "429" in err_str or "quota" in err_str or "rate" in err_str or "resource_exhausted" in err_str:
                        if attempt < self.MAX_RETRIES:
                            time.sleep(2 ** attempt)
                            attempt += 1
                            continue
                        logger.warning(f"Quota exceeded for '{model_name}'. Trying next fallback model...")
                        break

                    # Timeout -> retry once then move to next
                    if "timeout" in err_str or "deadline" in err_str or "timed out" in err_str:
                        if attempt < self.MAX_RETRIES:
                            attempt += 1
                            continue
                        break

                    # Invalid API key -> fail immediately
                    if ("invalid" in err_str and "key" in err_str) or ("api_key" in err_str and "invalid" in err_str):
                        raise AIKeyMissingError(str(exc))

                    # 500/503 Service temporary errors
                    if "500" in err_str or "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
                        if attempt < self.MAX_RETRIES:
                            time.sleep(1)
                            attempt += 1
                            continue
                        logger.warning(f"Service error on '{model_name}' ({exc}). Trying next model...")
                        break

                    logger.warning(f"Error on model '{model_name}': {exc}. Trying fallback...")
                    break

        # If all candidates exhausted, query available models from API for actionable diagnostics
        try:
            available = self.discover_models()
        except Exception:
            available = []

        if not available and last_error and ("quota" in str(last_error).lower() or "429" in str(last_error)):
            raise AIQuotaError(str(last_error))

        raise AIServiceError(
            f"No suitable Gemini model found. Attempted fallback order: {attempted_models}. "
            f"Available models from API: {available if available else 'None'}. Last error: {last_error}"
        )


# Global singleton — the rest of the application uses this
gemini_provider = GeminiProvider()
