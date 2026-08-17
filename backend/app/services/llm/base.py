from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Turns raw product info into a usable image-generation prompt.

    Any provider (Groq, OpenAI, Gemini, ...) can implement this without
    the rest of the app knowing which one is in use.
    """

    @abstractmethod
    def build_image_prompt(self, product_name: str, product_description: str) -> str:
        ...
