import httpx

from app.config import settings
from app.services.llm.base import LLMProvider

SYSTEM_PROMPT = (
    "You write concise, vivid prompts for AI image generators. Given a "
    "product name and description, respond with a single image-generation "
    "prompt (one paragraph, no preamble, no quotes) that describes an "
    "attractive lifestyle or product photo for it."
)


class GroqLLMProvider(LLMProvider):
    """
    Calls Groq's OpenAI-compatible chat completions endpoint. Swapping to
    another OpenAI-compatible provider (OpenAI, Together, etc.) only
    requires changing LLM_BASE_URL / LLM_MODEL / LLM_API_KEY in the
    environment — no code changes.
    """

    def __init__(self) -> None:
        self.base_url = settings.LLM_BASE_URL
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    def build_image_prompt(self, product_name: str, product_description: str) -> str:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is not configured")

        user_message = f"Product: {product_name}\nDescription: {product_description}"

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            },
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
