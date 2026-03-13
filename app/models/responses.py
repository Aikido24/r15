from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ParsedFieldsResponse(BaseModel):
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    detected_amounts: list[float] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class RuleCheckResponse(BaseModel):
    rule: str
    passed: bool
    message: str


HandwrittenConfidence = Literal["high", "medium", "low"]
HandwrittenLegibility = Literal["clear", "unclear", "illegible"]
DetectedNumberKind = Literal["handwritten", "printed", "unknown"]
DetectedFieldName = Literal["subtotal", "tax", "total", "other"]


class HandwrittenNumberResponse(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    value: str = ""
    region_description: str = ""
    confidence: HandwrittenConfidence = "low"
    legibility: HandwrittenLegibility = "unclear"
    reasoning: str = ""


class DetectedNumberResponse(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    value: str = ""
    field_name: DetectedFieldName = "other"
    number_kind: DetectedNumberKind = "unknown"
    region_description: str = ""
    confidence: HandwrittenConfidence = "low"
    legibility: HandwrittenLegibility = "unclear"
    reasoning: str = ""


class VisualChecksResponse(BaseModel):
    strikeouts_detected: bool = False
    corrections_detected: bool = False
    overwrites_detected: bool = False
    handwritten_numbers_detected: bool = False
    handwritten_numbers: list[HandwrittenNumberResponse] = Field(default_factory=list)
    detected_numbers: list[DetectedNumberResponse] = Field(default_factory=list)
    suspicious_areas: list[str] = Field(default_factory=list)
    summary: str = ""


class FindingResponse(BaseModel):
    type: str
    severity: str
    message: str


class PageDimensionsResponse(BaseModel):
    original_width: int
    original_height: int
    normalized_width: int
    normalized_height: int
    resized: bool


class PageAnalysisResponse(BaseModel):
    page_number: int
    image_path: str
    raw_text: str = ""
    detected_lines: list[str] = Field(default_factory=list)
    dimensions: PageDimensionsResponse | None = None
    visual_checks: VisualChecksResponse | None = None
    findings: list[FindingResponse] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    ok: bool
    message: str
    summary: str = ""
    document_url: str
    image_url: str
    document_kind: str = "image"
    page_count: int = 0
    file_name: str | None = None
    file_path: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    raw_text: str | None = None
    detected_lines: list[str] | None = None
    parsed_fields: ParsedFieldsResponse | None = None
    rule_checks: list[RuleCheckResponse] = Field(default_factory=list)
    visual_checks: VisualChecksResponse | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    pages: list[PageAnalysisResponse] = Field(default_factory=list)


JobStatus = Literal["queued", "running", "completed", "failed"]


class JobProgressResponse(BaseModel):
    job_id: str
    status: JobStatus = "queued"
    stage: str = "queued"
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: str = ""
    current_page: int | None = Field(default=None, ge=1)
    total_pages: int | None = Field(default=None, ge=1)
    result: AnalyzeResponse | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisJobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus = "queued"
    stage: str = "queued"
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: str = ""
