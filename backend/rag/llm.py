import logging
import time

from google import genai
from google.genai import errors as genai_errors

from ..config import GOOGLE_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_BASE_DELAY = 5  # seconds


class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            # Fallback keeps the demo usable without an API key.
            return (
                "⚠️ GOOGLE_API_KEY not set. Returning context-grounded fallback output.\n\n"
                + user_prompt[:1800]
            )

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"{system_prompt}\n\n{user_prompt}",
                    config={
                        "temperature": 0.2,
                    },
                )
                return response.text or "No response returned by the model."

            except genai_errors.ClientError as exc:
                last_error = exc
                status = getattr(exc, "status_code", None)
                if status == 429:
                    if attempt < MAX_RETRIES:
                        wait = RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(
                            "Gemini rate-limited (429). Retrying in %ds (attempt %d/%d).",
                            wait, attempt + 1, MAX_RETRIES,
                        )
                        time.sleep(wait)
                        continue
                    # All retries exhausted — return friendly message
                    logger.error("Gemini quota exhausted after %d retries.", MAX_RETRIES)
                    return (
                        "⚠️ **API Rate Limit Reached**\n\n"
                        "The Gemini API free-tier quota has been exceeded. "
                        "Please wait a minute and try again, or check your API key billing at "
                        "[Google AI Studio](https://aistudio.google.com/).\n\n"
                        "In the meantime, here is the retrieved context:\n\n"
                        + user_prompt[:2000]
                    )
                # Non-rate-limit client error
                logger.error("Gemini ClientError (%s): %s", status, exc)
                return (
                    f"⚠️ **API Error** (code {status})\n\n"
                    "The AI model returned an error. Please try again later.\n\n"
                    "Retrieved context:\n\n" + user_prompt[:2000]
                )

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.error("Unexpected LLM error: %s", exc)
                return (
                    "⚠️ **Generation Error**\n\n"
                    "An unexpected error occurred while generating a response. "
                    "Please try again.\n\n"
                    "Retrieved context:\n\n" + user_prompt[:1500]
                )

        # Should not reach here, but just in case
        return f"⚠️ Generation failed after retries: {last_error}"
