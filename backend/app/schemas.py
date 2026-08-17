import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import JobStatus


class JobCreateResponse(BaseModel):
    """Returned immediately by POST /generate, before work is done."""

    id: uuid.UUID
    status: JobStatus


class JobResponse(BaseModel):
    """Full job state, returned by GET /jobs/:id and GET /jobs."""

    id: uuid.UUID
    product_name: str
    product_description: str
    reference_image_url: str
    status: JobStatus
    generated_prompt: str | None = None
    result_image_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str = "ok"
