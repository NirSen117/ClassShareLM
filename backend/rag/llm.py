from google import genai

from ..config import GOOGLE_API_KEY, GEMINI_MODEL


class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            # Fallback keeps the demo usable without an API key.
            return (
                "GOOGLE_API_KEY not set. Returning context-grounded fallback output.\n\n"
                + user_prompt[:1800]
            )

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config={
                "temperature": 0.2,
            },
        )
        return response.text or "No response returned by the model."
