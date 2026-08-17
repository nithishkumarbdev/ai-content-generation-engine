"""App configuration, loaded from environment variables. One place to look
when something needs to change between local dev and a deployment."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/glitrai"
    )

    # LLM provider (OpenAI-compatible chat completions API).
    # Defaults to Groq's free-tier endpoint; swap the base URL/model to use
    # any other OpenAI-compatible provider without touching application code.
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    # Image generation provider: "mock" or "comfyui"
    IMAGE_PROVIDER: str = os.getenv("IMAGE_PROVIDER", "mock")
    COMFYUI_BASE_URL: str = os.getenv("COMFYUI_BASE_URL", "")

    # Where uploaded/generated images are written and served from
    STATIC_DIR: str = os.getenv("STATIC_DIR", "static")
    UPLOADS_SUBDIR: str = "uploads"
    GENERATED_SUBDIR: str = "generated"

    # Public base URL of this service, used to build absolute image URLs
    # in API responses. Falls back to a relative path if unset.
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "")


settings = Settings()
