"""화면 라벨의 백엔드 미러.

원본은 `frontend/lib/labels.ts` 하나다. PPTX 는 백엔드에서 만들어지므로 같은 한국어 라벨이
여기에도 필요하다. 두 파일이 어긋나면 tests/test_labels_mirror.py 가 잡는다.
"""

from __future__ import annotations

from app.models.contracts import (
    Audience,
    Interest,
    IssueType,
    Purpose,
    ReportStatus,
    Severity,
    Style,
)

AUDIENCE_LABELS: dict[Audience, str] = {
    Audience.NEWCOMER: "신입사원",
    Audience.PRACTITIONER: "실무자",
    Audience.EXECUTIVE: "임원",
    Audience.CUSTOMER: "고객",
}

# 이해도 1~5. 색이나 숫자만으로 두지 않고 항상 이 라벨을 함께 보여준다.
EXPERTISE_LABELS: dict[int, str] = {
    1: "입문",
    2: "낮음",
    3: "보통",
    4: "높음",
    5: "전문가",
}

INTEREST_LABELS: dict[Interest, str] = {
    Interest.TECHNOLOGY: "기술",
    Interest.PERFORMANCE: "성능",
    Interest.COST: "비용",
    Interest.SAFETY: "안전성",
    Interest.SCHEDULE: "일정",
}

PURPOSE_LABELS: dict[Purpose, str] = {
    Purpose.EDUCATION: "교육",
    Purpose.INTERNAL_REPORT: "내부보고",
    Purpose.TECHNICAL_EXPLANATION: "기술설명",
    Purpose.PROPOSAL: "제안",
}

STYLE_LABELS: dict[Style, str] = {
    Style.PROFESSIONAL: "전문적",
    Style.CONCISE: "간결",
    Style.PERSUASIVE: "설득형",
    Style.FRIENDLY: "친절한 설명형",
}

SEVERITY_LABELS: dict[Severity, str] = {
    Severity.INFO: "정보",
    Severity.WARNING: "주의",
    Severity.CRITICAL: "심각",
}

# 색만으로 상태를 구분하지 않는다. 항상 이 텍스트 라벨을 함께 표시한다.
STATUS_LABELS: dict[ReportStatus, str] = {
    ReportStatus.OK: "확인됨",
    ReportStatus.WARNING: "주의",
    ReportStatus.REVIEW_NEEDED: "검토 필요",
}

ISSUE_TYPE_LABELS: dict[IssueType, str] = {
    IssueType.UNSUPPORTED_CLAIM: "원문에 없는 주장",
    IssueType.NUMBER_ERROR: "숫자·단위 오류",
    IssueType.DISTORTION: "의미 왜곡",
    IssueType.OVERSIMPLIFICATION: "과도한 단순화",
    IssueType.OMISSION: "핵심 내용 누락",
    IssueType.SENSITIVE_INFO: "민감·내부 정보",
}
