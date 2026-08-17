import io
from unittest.mock import patch

from PIL import Image

from app.database import SessionLocal
from app.models import Job, JobStatus
from app.services import job_service


class _FakeUploadFile:
    """Minimal stand-in for FastAPI's UploadFile - job_service only reads .filename and .file."""

    filename = "reference.jpg"

    def __init__(self, data: bytes):
        self.file = io.BytesIO(data)


def _tiny_jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), (200, 150, 100)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_process_job_completes_with_a_working_llm():
    db = SessionLocal()
    job = job_service.create_job(db, "Test Mug", "A ceramic test mug.", _FakeUploadFile(_tiny_jpeg()))
    assert job.status == JobStatus.PENDING

    with patch("app.services.job_service.get_llm_provider") as mock_llm:
        mock_llm.return_value.build_image_prompt.return_value = "A mug on a wooden table"
        job_service.process_job(job.id)

    finished = SessionLocal().get(Job, job.id)
    assert finished.status == JobStatus.COMPLETED
    assert finished.generated_prompt == "A mug on a wooden table"
    assert finished.result_image_path is not None


def test_process_job_fails_gracefully_when_the_llm_call_breaks():
    db = SessionLocal()
    job = job_service.create_job(db, "Test Mug", "A ceramic test mug.", _FakeUploadFile(_tiny_jpeg()))

    with patch("app.services.job_service.get_llm_provider") as mock_llm:
        mock_llm.return_value.build_image_prompt.side_effect = RuntimeError("LLM_API_KEY is not configured")
        job_service.process_job(job.id)

    finished = SessionLocal().get(Job, job.id)
    assert finished.status == JobStatus.FAILED
    assert "LLM_API_KEY" in finished.error_message
