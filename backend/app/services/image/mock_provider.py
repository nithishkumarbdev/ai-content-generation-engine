import io
import textwrap

from PIL import Image, ImageDraw, ImageFont

from app.services.image.base import ImageProvider

CANVAS_SIZE = (768, 768)
BACKGROUND_COLOR = (245, 240, 230)
TEXT_COLOR = (40, 40, 40)


class MockImageProvider(ImageProvider):
    """
    Stand-in for a real image model.
    """

    def generate(self, prompt: str, reference_image_path: str) -> bytes:
        canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND_COLOR)

        try:
            reference = Image.open(reference_image_path).convert("RGB")
            reference.thumbnail((CANVAS_SIZE[0] - 80, 420))
            offset_x = (CANVAS_SIZE[0] - reference.width) // 2
            canvas.paste(reference, (offset_x, 40))
        except (FileNotFoundError, OSError):
            pass  # fall back to a text-only placeholder

        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        wrapped = textwrap.fill(prompt, width=60)
        draw.multiline_text((40, 500), wrapped, fill=TEXT_COLOR, font=font, spacing=6)
        draw.text((40, CANVAS_SIZE[1] - 30), "[mocked generation]", fill=(150, 150, 150), font=font)

        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        return buffer.getvalue()
