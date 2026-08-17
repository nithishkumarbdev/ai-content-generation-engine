import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, String, Text, Uuid

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    """
    A single content-generation job: a product goes in, a generated
    image comes out. One table is enough for what this stores — the
    job *is* the unit of work, so job metadata and result live together
    rather than being split across multiple tables.
    """

    __tablename__ = "jobs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    product_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=False)
    reference_image_path = Column(String(512), nullable=False)

    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    generated_prompt = Column(Text, nullable=True)
    result_image_path = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
