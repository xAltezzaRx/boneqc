from uuid import UUID

from pydantic import BaseModel


class DeadLetterEntry(BaseModel):
    job_id: UUID
    study_id: UUID
    attempts: int
    error_message: str
    failure_type: str


class DeadLetterListResponse(BaseModel):
    count: int
    items: list[DeadLetterEntry]


class DeadLetterCountResponse(BaseModel):
    count: int
