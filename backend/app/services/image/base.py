from abc import ABC, abstractmethod


class ImageProvider(ABC):
    """
    Generates an image from a prompt and a reference image.

    Swappable by design: the mock provider and the ComfyUI provider are
    interchangeable from the job service's point of view, and either can
    be replaced by a different provider (e.g. a hosted diffusion API)
    later without touching job orchestration logic.
    """

    @abstractmethod
    def generate(self, prompt: str, reference_image_path: str) -> bytes:
        """Return the generated image as raw bytes."""
        ...
