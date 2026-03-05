"""Pydantic request/response schemas."""

from pydantic import BaseModel


class SessionCreate(BaseModel):
    content_type: str = "email"
    audience: str = "hcp"
    campaign_goal: str = "awareness"
    tone: str = "clinical"


class SessionResp(BaseModel):
    session_id: str
    content_type: str
    audience: str
    campaign_goal: str
    tone: str


class ChatReq(BaseModel):
    session_id: str
    role: str = "user"
    content: str


class ChatResp(BaseModel):
    assistant_message: str


class GenerateReq(BaseModel):
    session_id: str
    claim_ids: list[str]
    selected_asset_ids: list[str] | None = None


class GenerateResp(BaseModel):
    html: str
    revision_number: int


class EditReq(BaseModel):
    session_id: str
    current_html: str
    instruction: str


class EditResp(BaseModel):
    html: str
    revision_number: int


class ClaimOut(BaseModel):
    id: str
    text: str
    citation: str
    source: str
    category: str
    compliance_status: str
    approved_date: str | None = None


class VersionOut(BaseModel):
    id: str
    created_at: str
    html_preview: str
    revision_number: int
    content_type: str


class VersionDetail(BaseModel):
    id: str
    created_at: str
    html: str
    revision_number: int


class ReviewItem(BaseModel):
    check: str
    status: str  # "pass", "warn", "fail"
    detail: str


class ComplianceReviewResp(BaseModel):
    overall: str  # "pass", "warn", "fail"
    can_export: bool
    items: list[ReviewItem]


class ExportResp(BaseModel):
    html: str
    metadata: dict
    compliance_report: dict


class ValidateHtmlReq(BaseModel):
    html: str
