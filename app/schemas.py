from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Literal

class RecipientInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    course: str = Field(min_length=1, max_length=200)

class JobCreate(BaseModel):
    recipients: list[RecipientInput] = Field(min_length=1, max_length=1000)

class RecipientResult(BaseModel):
    id: int
    name: str
    email: str
    course: str
    certificate_id: str
    status: Literal["pending", "processing", "succeeded", "failed"]
    error: str | None = None
    download_url: str | None = None
    model_config = ConfigDict(from_attributes=True)

class JobResult(BaseModel):
    id: int
    status: str
    total: int
    succeeded: int
    failed: int
    progress_percent: float
    recipients: list[RecipientResult]
