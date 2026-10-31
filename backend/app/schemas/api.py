from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(examples=["reviewer@actionloop.demo"])
    password: str = Field(min_length=1, examples=["ActionLoop@2026"])


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department: str
    organization: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class StartWorkflowRequest(BaseModel):
    document_id: str


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "request_correction"]
    comment: str | None = Field(default=None, max_length=2000)
    corrections: dict[str, str] | None = Field(default=None, description="field name -> corrected value")

    @field_validator("comment")
    @classmethod
    def strip(cls, v):
        return v.strip() if v else v


class VerifyRequest(BaseModel):
    workflow_id: str | None = None
    simulate_tamper_event_id: str | None = Field(
        default=None, description="Demo only: recompute with an in-memory altered copy of this event. The DB is never changed.")


class WalletSubmissionRequest(BaseModel):
    tx_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")


class SubmitterRequest(BaseModel):
    address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    authorized: bool = True


class RuleUpdate(BaseModel):
    enabled: bool | None = None
    severity: Literal["failed", "warning"] | None = None
    params: dict | None = None


class ErrorOut(BaseModel):
    detail: str

