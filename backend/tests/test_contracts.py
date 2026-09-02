"""계약과 fixture 정합성 (docs/01-contracts.md)."""

from __future__ import annotations

import pytest

from app.models.contracts import (
    AudienceContent,
    PresentationRequest,
    PresentationSupport,
    SlideDeck,
    SourceAnalysis,
    VerificationReport,
)

from tests.conftest import load_fixture


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("presentation_request.json", PresentationRequest),
        ("source_analysis.json", SourceAnalysis),
        ("audience_content.json", AudienceContent),
        ("slide_deck.json", SlideDeck),
        ("presentation_support.json", PresentationSupport),
        ("verification_report.json", VerificationReport),
    ],
)
def test_fixture_matches_contract(filename: str, model: type) -> None:
    """fixture 가 계약과 어긋나면 팀원 모듈 간 연결이 깨진다."""
    model(**load_fixture(filename))


def test_slide_count_defaults_to_none() -> None:
    request = PresentationRequest(audience="customer", purpose="proposal")
    assert request.slide_count is None
    assert request.duration_minutes == 5


def test_invalid_duration_is_rejected() -> None:
    with pytest.raises(ValueError):
        PresentationRequest(audience="customer", purpose="proposal", duration_minutes=7)


def test_invalid_audience_is_rejected() -> None:
    with pytest.raises(ValueError):
        PresentationRequest(audience="intern", purpose="proposal")
