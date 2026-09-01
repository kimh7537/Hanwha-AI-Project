"""LLM provider 어댑터의 공통 인터페이스.

핵심 규칙(docs/08-api-and-env.md):
  - LLM 을 쓸 수 없거나 호출이 실패하면 각 모듈은 규칙 기반 휴리스틱으로 계속 진행한다.
  - 그 사실은 RunContext 에 기록되어 응답 meta 의 fallback_used 로 화면에 노출된다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


class LLMUnavailable(RuntimeError):
    """LLM 을 호출할 수 없거나 응답이 쓸 수 없는 형태일 때."""


class LLMProvider:
    """모든 provider 의 기반 클래스. 기본 구현은 '사용 불가'다."""

    name: str = "mock"
    available: bool = False

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
        raise LLMUnavailable("LLM provider 를 사용할 수 없습니다 (mock 모드).")

    # 하위 클래스가 공통으로 쓰는 유틸 ------------------------------------

    @staticmethod
    def parse_json(text: str) -> dict[str, Any]:
        """모델 응답에서 JSON 객체를 뽑아낸다. 코드펜스/서두 설명을 견딘다."""
        if not text:
            raise LLMUnavailable("LLM 이 빈 응답을 반환했습니다.")

        fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        candidate = fenced.group(1) if fenced else text

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMUnavailable("LLM 응답에서 JSON 을 찾지 못했습니다.")

        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"LLM 응답 JSON 파싱 실패: {exc}") from exc

        if not isinstance(parsed, dict):
            raise LLMUnavailable("LLM 응답이 JSON 객체가 아닙니다.")
        return parsed


class MockProvider(LLMProvider):
    """LLM 없이 동작하는 기본 provider. 각 모듈이 휴리스틱 경로를 타게 만든다."""

    name = "mock"
    available = False


@dataclass
class RunContext:
    """한 번의 파이프라인 실행에 대한 provider 상태와 fallback 기록."""

    provider: LLMProvider = field(default_factory=MockProvider)
    fallback_used: bool = False
    fallback_reason: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def llm_enabled(self) -> bool:
        return self.provider.available

    def note_fallback(self, stage: str, reason: str) -> None:
        message = f"{stage}: {reason}"
        self.notes.append(message)
        if not self.fallback_used:
            self.fallback_used = True
            self.fallback_reason = message

    def call_json(
        self,
        stage: str,
        system: str,
        user: str,
        max_tokens: int = 2000,
    ) -> Optional[dict[str, Any]]:
        """LLM 호출을 시도하고, 불가능하거나 실패하면 None 을 돌려준다.

        None 을 받은 모듈은 반드시 휴리스틱 경로로 계속 진행해야 한다.
        """
        if not self.provider.available:
            return None
        try:
            return self.provider.complete_json(system=system, user=user, max_tokens=max_tokens)
        except Exception as exc:  # noqa: BLE001 - 어떤 실패든 데모를 멈추면 안 된다
            self.note_fallback(stage, f"{type(exc).__name__}: {exc}")
            return None
