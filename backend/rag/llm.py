from openai import OpenAI

from ..config import OPENAI_API_KEY, OPENAI_MODEL


class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            # Fallback keeps the demo usable without an API key.
            return (
                "OPENAI_API_KEY not set. Returning context-grounded fallback output.\n\n"
                + user_prompt[:1800]
            )

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or "No response returned by the model."
