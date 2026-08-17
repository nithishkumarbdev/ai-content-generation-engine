import logging
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Job, JobStatus
from app.schemas import JobResponse
from app.services.providers import get_image_provider, get_llm_provider
from app.utils.files import save_generated_bytes, save_upload, to_public_url

logger = logging.getLogger(__name__)


def create_job(db: Session, product_name: str, product_description: str, image: UploadFile) -> Job:
    """Persist a new job in PENDING state. Does not run the pipeline itself."""
    reference_path = save_upload(image)

    job = Job(
        product_name=product_name,
        product_description=product_description,
        reference_image_path=reference_path,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: uuid.UUID) -> Job | None:
    return db.get(Job, job_id)


def list_jobs(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.created_at.desc()).all()


def process_job(job_id: uuid.UUID) -> None:
    """
    Runs the generation pipeline for a job: LLM prompt -> image generation
    -> persist result. Runs in a background task after the API has already
    responded, so it opens its own DB session rather than reusing a
    request-scoped one.
    """
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("process_job called for missing job %s", job_id)
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        try:
            prompt = get_llm_provider().build_image_prompt(
                job.product_name, job.product_description
            )
            job.generated_prompt = prompt
            db.commit()

            image_bytes = get_image_provider().generate(prompt, job.reference_image_path)
            job.result_image_path = save_generated_bytes(image_bytes)
            job.status = JobStatus.COMPLETED
            db.commit()

        except Exception as exc:  # noqa: BLE001 - any pipeline failure lands here
            logger.exception("Job %s failed", job_id)
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()

    finally:
        db.close()


def job_to_response(job: Job) -> JobResponse:
    """Map the ORM model to the API schema, turning file paths into URLs."""
    return JobResponse(
        id=job.id,
        product_name=job.product_name,
        product_description=job.product_description,
        reference_image_url=to_public_url(job.reference_image_path),
        status=job.status,
        generated_prompt=job.generated_prompt,
        result_image_url=to_public_url(job.result_image_path) if job.result_image_path else None,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
