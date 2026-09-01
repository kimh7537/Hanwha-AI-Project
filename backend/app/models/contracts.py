"""공통 데이터 계약.

이 파일은 docs/01-contracts.md 의 구현이며, frontend/lib/types.ts 와 의미상 동일해야 한다.
필드를 바꾸면 4곳(Pydantic / TypeScript / fixtures / docs)을 함께 고친다. -> contract-sync 스킬
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# enum : wire 값은 영문 snake_case, 화면 라벨은 frontend/lib/labels.ts 에서만 관리
# --------------------------------------------------------------------------


class Audience(str, Enum):
    NEWCOMER = "newcomer"
    PRACTITIONER = "practitioner"
    EXECUTIVE = "executive"
    CUSTOMER = "customer"


class Purpose(str, Enum):
    EDUCATION = "education"
    INTERNAL_REPORT = "internal_report"
    TECHNICAL_EXPLANATION = "technical_explanation"
    PROPOSAL = "proposal"


class Style(str, Enum):
    PROFESSIONAL = "professional"
    CONCISE = "concise"
    PERSUASIVE = "persuasive"
    FRIENDLY = "friendly"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ReportStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    REVIEW_NEEDED = "review_needed"


class IssueType(str, Enum):
    UNSUPPORTED_CLAIM = "unsupported_claim"
    NUMBER_ERROR = "number_error"
    DISTORTION = "distortion"
    OVERSIMPLIFICATION = "oversimplification"
    OMISSION = "omission"
    SENSITIVE_INFO = "sensitive_info"


# --------------------------------------------------------------------------
# 입력
# --------------------------------------------------------------------------


class PresentationRequest(BaseModel):
    audience: Audience
    purpose: Purpose
    duration_minutes: Literal[3, 5, 10] = 5
    keywords: list[str] = Field(default_factory=list)
    style: Style = Style.PROFESSIONAL
    preserve_original_terms: bool = True
    slide_count: Optional[int] = None


# --------------------------------------------------------------------------
# 문서 / chunk
# --------------------------------------------------------------------------


class Chunk(BaseModel):
    id: str
    index: int
    page: int
    text: str


class DocumentMeta(BaseModel):
    document_id: str
    filename: str
    page_count: int
    char_count: int
    chunk_count: int


class DocumentResponse(BaseModel):
    document: DocumentMeta
    chunks: list[Chunk] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 모듈 A : SourceAnalysis
# --------------------------------------------------------------------------


class SourceEvidence(BaseModel):
    id: str
    text: str
    page: int


class EvidenceItem(BaseModel):
    text: str
    source_refs: list[str] = Field(default_factory=list)


class NumberFact(BaseModel):
    value: str
    unit: str = ""
    meaning: str = ""
    source_refs: list[str] = Field(default_factory=list)


class TermFact(BaseModel):
    term: str
    definition: str = ""
    source_refs: list[str] = Field(default_factory=list)


class SourceAnalysis(BaseModel):
    core_message: str = ""
    technical_points: list[EvidenceItem] = Field(default_factory=list)
    key_features: list[EvidenceItem] = Field(default_factory=list)
    numbers: list[NumberFact] = Field(default_factory=list)
    terms: list[TermFact] = Field(default_factory=list)
    must_keep: list[EvidenceItem] = Field(default_factory=list)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    unverified: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 모듈 B : AudienceContent
# --------------------------------------------------------------------------


class AudienceExplanation(BaseModel):
    topic: str
    text: str
    source_refs: list[str] = Field(default_factory=list)


class GlossaryItem(BaseModel):
    term: str
    plain_definition: str = ""
    source_refs: list[str] = Field(default_factory=list)


class AudienceContent(BaseModel):
    audience: Audience
    tone_note: str = ""
    explanations: list[AudienceExplanation] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    emphasis: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 모듈 C : SlideDeck
# --------------------------------------------------------------------------


class Slide(BaseModel):
    id: str
    title: str = ""
    takeaway: str = ""
    bullets: list[str] = Field(default_factory=list)
    visual_suggestion: str = ""
    speaker_notes: str = ""
    source_refs: list[str] = Field(default_factory=list)


class SlideDeck(BaseModel):
    title: str = ""
    # 이 덱을 왜 이 순서·이 분량으로 짰는지. 청중이 바뀌면 이 문장도 함께 바뀐다.
    # 표현만 바꾼 것이 아니라 구성을 다시 설계했다는 근거라서 화면에 그대로 노출한다.
    strategy: str = ""
    slides: list[Slide] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 모듈 D : PresentationSupport
# --------------------------------------------------------------------------


class SlideScript(BaseModel):
    slide_id: str
    script: str = ""
    must_say: str = ""
    duration_seconds: int = 0


class QAItem(BaseModel):
    question: str
    answer: str = ""
    source_refs: list[str] = Field(default_factory=list)
    asked_by: Audience


class RehearsalCard(BaseModel):
    question: str
    why: str = ""
    recommended_slide: str = ""


class PresentationSupport(BaseModel):
    scripts: list[SlideScript] = Field(default_factory=list)
    qa: list[QAItem] = Field(default_factory=list)
    rehearsal_cards: list[RehearsalCard] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 모듈 E : VerificationReport
# --------------------------------------------------------------------------


class VerificationItem(BaseModel):
    severity: Severity
    slide_id: str = ""
    type: IssueType
    message: str
    source_refs: list[str] = Field(default_factory=list)
    suggested_fix: str = ""


class VerificationReport(BaseModel):
    summary: str = ""
    status: ReportStatus = ReportStatus.OK
    items: list[VerificationItem] = Field(default_factory=list)
    checked_slides: int = 0


# --------------------------------------------------------------------------
# 파이프라인 응답
# --------------------------------------------------------------------------


class PipelineMeta(BaseModel):
    provider: str = "mock"
    fallback_used: bool = False
    fallback_reason: str = ""
    elapsed_ms: int = 0


class GenerateRequest(BaseModel):
    document_id: str
    request: PresentationRequest


class GenerateResponse(BaseModel):
    presentation_id: str
    document: DocumentMeta
    request: PresentationRequest
    source_analysis: SourceAnalysis
    audience_content: AudienceContent
    slide_deck: SlideDeck
    presentation_support: PresentationSupport
    verification_report: Optional[VerificationReport] = None
    meta: PipelineMeta = Field(default_factory=PipelineMeta)


class VerifyRequest(BaseModel):
    presentation_id: Optional[str] = None
    document_id: Optional[str] = None
    request: Optional[PresentationRequest] = None
    slide_deck: Optional[SlideDeck] = None
    presentation_support: Optional[PresentationSupport] = None
