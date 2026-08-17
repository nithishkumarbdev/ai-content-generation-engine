from app.config import settings
from app.services.image.base import ImageProvider
from app.services.image.comfyui_provider import ComfyUIImageProvider
from app.services.image.mock_provider import MockImageProvider
from app.services.llm.base import LLMProvider
from app.services.llm.groq_provider import GroqLLMProvider


def get_llm_provider() -> LLMProvider:
    return GroqLLMProvider()


def get_image_provider() -> ImageProvider:
    if settings.IMAGE_PROVIDER == "comfyui":
        return ComfyUIImageProvider()
    return MockImageProvider()
