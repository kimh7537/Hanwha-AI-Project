"""청중별 설계 규칙을 화면에 알려 준다.

조건 화면은 생성을 누르기 전에 "이 청중이면 어떤 순서로, 몇 장으로 짜인다"를 보여준다.
그 값을 프론트엔드에 한 벌 더 적어 두면 규칙을 고칠 때 조용히 갈라져서, 화면이 실제로
일어나지 않는 일을 예고하게 된다. 그래서 규칙을 소유한 모듈(services/audience,
services/planner)에서 그대로 읽어 내보낸다.

계약(SourceAnalysis 등 6개)이 아니라 이 엔드포인트 전용 응답이므로 models/contracts.py 가
아니라 여기에 둔다.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.contracts import Audience, PresentationRequest
from app.services import audience as audience_service
from app.services import labels, planner, profile

router = APIRouter(prefix="/api/audiences", tags=["audiences"])


class AudiencePlan(BaseModel):
    """청중 하나의 설계 규칙."""

    audience: Audience
    label: str
    #: 이 청중일 때 만들어지는 설명의 순서. 덱의 뼈대다.
    storyline: list[str] = Field(default_factory=list)
    #: 무엇을 앞세우는가
    leads: str = ""
    #: 무엇을 덜어내는가
    trims: str = ""
    #: 용어 풀이 최대 개수. None 은 전부.
    glossary_limit: int | None = None
    #: 같은 시간이라도 이 청중이면 장수가 몇 장 움직이는가
    slide_delta: int = 0


class AudiencePlansResponse(BaseModel):
    audiences: list[AudiencePlan] = Field(default_factory=list)
    #: 발표 시간(분) -> 기본 장수. 키는 JSON 이라 문자열이다.
    duration_slides: dict[str, int] = Field(default_factory=dict)
    min_slides: int = planner.MIN_SLIDES
    max_slides: int = planner.MAX_SLIDES


@router.get("")
def list_audience_plans() -> AudiencePlansResponse:
    return AudiencePlansResponse(
        audiences=[
            AudiencePlan(
                audience=member,
                label=labels.AUDIENCE_LABELS[member],
                storyline=audience_service.AUDIENCE_STORYLINE[member],
                leads=audience_service.AUDIENCE_LEADS[member],
                trims=audience_service.AUDIENCE_TRIMS[member],
                glossary_limit=audience_service.AUDIENCE_GLOSSARY_LIMIT[member],
                slide_delta=planner.AUDIENCE_SLIDE_DELTA[member],
            )
            for member in Audience
        ],
        duration_slides={str(minutes): count for minutes, count in planner.DURATION_SLIDES.items()},
    )


class PlanPreview(BaseModel):
    """이번 조건으로 지금 생성하면 나올 구성. 생성 전에 화면이 보여준다."""

    audience: Audience
    label: str
    storyline: list[str] = Field(default_factory=list)
    leads: str = ""
    trims: str = ""
    #: 청중 기본에 기술 이해도까지 반영한 최종 용어 풀이 개수. None 은 전부.
    glossary_limit: int | None = None
    #: 실제로 쓰일 장수 (사용자가 직접 지정했으면 그 값).
    slide_count: int = 0
    #: 프로파일·메시지 통제가 이번 구성에 무엇을 했는지.
    notes: list[str] = Field(default_factory=list)


@router.post("/preview")
def preview_plan(request: PresentationRequest) -> PlanPreview:
    """조건을 그대로 받아 '지금 생성하면 이렇게 됩니다'를 돌려준다.

    규칙을 화면에 한 벌 더 적지 않으려고 만든 경로다. 이해도가 용어 풀이 개수를 움직이고
    메시지 통제가 순위를 바꾸는 규칙이 늘어난 뒤로는, 화면이 그 계산을 따라 하면 실제 결과와
    어긋나기 쉽다. 생성 경로와 같은 함수를 부른다.
    """
    return PlanPreview(
        audience=request.audience,
        label=labels.AUDIENCE_LABELS[request.audience],
        storyline=audience_service.AUDIENCE_STORYLINE[request.audience],
        leads=audience_service.AUDIENCE_LEADS[request.audience],
        trims=audience_service.AUDIENCE_TRIMS[request.audience],
        glossary_limit=audience_service.resolved_glossary_limit(request),
        slide_count=planner.resolve_slide_count(request),
        notes=profile.describe(request),
    )
