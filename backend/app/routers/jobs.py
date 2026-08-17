import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JobCreateResponse, JobResponse
from app.services import job_service

router = APIRouter(tags=["jobs"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/generate", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def generate(
    background_tasks: BackgroundTasks,
    product_name: str = Form(...),
    product_description: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    if not product_name.strip() or not product_description.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "product_name and product_description are required")

    if image is None or image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A product reference image (jpeg/png/webp) is required",
        )

    job = job_service.create_job(db, product_name.strip(), product_description.strip(), image)
    background_tasks.add_task(job_service.process_job, job.id)

    return JobCreateResponse(id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobResponse:
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job_service.job_to_response(job)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)) -> list[JobResponse]:
    jobs = job_service.list_jobs(db)
    return [job_service.job_to_response(job) for job in jobs]
