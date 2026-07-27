from datetime import datetime

from pydantic import BaseModel


class MtgoJobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    session_id: int | None = None
    mtgo_username: str | None = None
    params: dict | None = None
    result: dict | None = None
    error_message: str | None = None
    log_output: str
    requested_by: str | None = None
    retry_of_job_id: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {
        "from_attributes": True,
    }


class TriggerGiveRequest(BaseModel):
    requested_by: str | None = None


class TriggerReturnRequest(BaseModel):
    mtgo_username: str
    requested_by: str | None = None


class TriggerIntegrityCheckRequest(BaseModel):
    requested_by: str | None = None


class TriggerGiveBackRequest(BaseModel):
    mtgo_username: str
    cards: dict[str, int]
    requested_by: str | None = None
    retry_of_job_id: int | None = None


class RetryJobRequest(BaseModel):
    requested_by: str | None = None
