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


class Interest(str, Enum):
    """청중이 이 발표에서 듣고 싶어 하는 축. 같은 원문에서 무엇을 앞으로 당길지를 정한다."""

    TECHNOLOGY = "technology"
    PERFORMANCE = "performance"
    COST = "cost"
    SAFETY = "safety"
    SCHEDULE = "schedule"


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


class AudienceProfile(BaseModel):
    """`Audience` 가 '누구'라면 이쪽은 '어느 정도로, 무엇에 관심 있는 사람'이다.

    청중 하나만으로는 같은 '고객사'라도 기술 이해도와 관심 축이 전혀 다른 자리를 구분할 수
    없다. 이 값들은 사실을 바꾸지 않고, 어떤 사실을 앞으로 당기고 얼마나 풀어 쓸지를 정한다.
    """

    #: 기술 이해도 1(낮음) ~ 5(높음). 용어 풀이 개수와 설명 깊이를 정한다.
    expertise: int = Field(default=3, ge=1, le=5)
    #: 관심 영역. 비어 있으면 청중 기본 구성만 따른다.
    interests: list[Interest] = Field(default_factory=list)
    #: 이미 알고 있는 것. 아는 내용을 다시 설명하지 않도록 순위를 낮추는 데 쓴다.
    prior_knowledge: str = ""


class MessageControl(BaseModel):
    """발표자가 발표의 의도를 직접 통제한다.

    `emphasize`(강조)에 해당하는 값은 `PresentationRequest.keywords` 다. 그 필드는 이미
    "덱에 최소 1회 등장하고 검증에서 확인한다"는 뜻으로 분석·검색·검증에 물려 있어서,
    이름만 이쪽으로 옮기면 그 배선을 전부 끊게 된다. 화면에서는 둘을 한 묶음으로 보여준다.

    여기의 어떤 값도 원문에 없는 사실을 만들지 않는다. 순위를 올리고 내릴 뿐이고,
    지켜지지 않은 것은 검증 리포트가 잡는다.
    """

    #: 이 발표로 반드시 남겨야 할 한 문장. 사실이 아니라 의도다.
    must_convey: str = ""
    #: 덜 다루고 싶은 주제. 삭제가 아니라 뒤로 민다 — 사실을 지우지는 않는다.
    minimize: list[str] = Field(default_factory=list)
    #: 쓰지 말아야 할 표현. 고르는 단계에서 피하고, 남으면 검증이 경고한다.
    banned: list[str] = Field(default_factory=list)


class PresentationRequest(BaseModel):
    audience: Audience
    purpose: Purpose
    duration_minutes: Literal[3, 5, 10] = 5
    #: 강조 키워드. 덱에 최소 1회 등장해야 하고 검증에서 확인한다 (`MessageControl` 참고).
    keywords: list[str] = Field(default_factory=list)
    style: Style = Style.PROFESSIONAL
    preserve_original_terms: bool = True
    slide_count: Optional[int] = None
    profile: AudienceProfile = Field(default_factory=AudienceProfile)
    message: MessageControl = Field(default_factory=MessageControl)


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


class PageContent(BaseModel):
    """원본 한 쪽(PPTX 는 슬라이드 한 장)의 글. 화면의 원본 대조에 쓴다.

    chunk 는 쪽 경계를 넘어 묶이므로 chunk 로는 "원본 슬라이드 N 장"을 복원할 수 없다.
    """

    page: int = 0
    text: str = ""


class DocumentResponse(BaseModel):
    document: DocumentMeta
    chunks: list[Chunk] = Field(default_factory=list)
    pages: list[PageContent] = Field(default_factory=list)


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
