import time
import uuid

import httpx

from app.config import settings
from app.services.image.base import ImageProvider


class ComfyUIImageProvider(ImageProvider):
    """
    Calls a deployed ComfyUI instance's HTTP API instead of a real model
    provider.
    """

    def __init__(self) -> None:
        self.base_url = settings.COMFYUI_BASE_URL.rstrip("/")

    def generate(self, prompt: str, reference_image_path: str) -> bytes:
        if not self.base_url:
            raise RuntimeError("COMFYUI_BASE_URL is not configured")

        with open(reference_image_path, "rb") as f:
            upload = httpx.post(
                f"{self.base_url}/upload/image",
                files={"image": (uuid.uuid4().hex + ".png", f, "image/png")},
                timeout=30.0,
            )
        upload.raise_for_status()
        uploaded_filename = upload.json()["name"]

        prompt_graph = self._fill_workflow(prompt, uploaded_filename)
        queued = httpx.post(
            f"{self.base_url}/prompt", json={"prompt": prompt_graph}, timeout=30.0
        )
        queued.raise_for_status()
        prompt_id = queued.json()["prompt_id"]

        return self._poll_for_result(prompt_id)

    def _fill_workflow(self, prompt: str, uploaded_filename: str) -> dict:
        # Load your exported ComfyUI workflow (Save (API Format) in the UI),
        # then set the prompt text and uploaded_filename on the matching
        # nodes by their node ID before returning the graph. Node IDs are
        # specific to whatever checkpoint/upscaler you wired up in your
        # own workflow, so this can't be filled in generically.
        raise NotImplementedError(
            "Load your exported ComfyUI workflow JSON here and map the "
            "prompt/image inputs to its node IDs."
        )

    def _poll_for_result(self, prompt_id: str, timeout_seconds: int = 120) -> bytes:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            history = httpx.get(f"{self.base_url}/history/{prompt_id}", timeout=15.0)
            history.raise_for_status()
            data = history.json()

            if prompt_id in data:
                outputs = data[prompt_id]["outputs"]
                for node_output in outputs.values():
                    for image in node_output.get("images", []):
                        image_response = httpx.get(
                            f"{self.base_url}/view",
                            params={
                                "filename": image["filename"],
                                "subfolder": image.get("subfolder", ""),
                                "type": image.get("type", "output"),
                            },
                            timeout=30.0,
                        )
                        image_response.raise_for_status()
                        return image_response.content

            time.sleep(2)

        raise TimeoutError(f"ComfyUI job {prompt_id} did not complete in time")
