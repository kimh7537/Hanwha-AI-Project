"""Anthropic(Claude) provider — 공식 anthropic SDK 사용.

호출이 실패하면 예외를 던진다. 예외를 잡아 휴리스틱으로 되돌리는 책임은 RunContext 에 있다
(docs/08-api-and-env.md: 키가 없거나 실패해도 데모는 멈추지 않는다).
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.llm.base import LLMProvider, LLMUnavailable

DEFAULT_MODEL = "claude-opus-5"

# JSON 하나만 받으면 되지만, 상한을 낮게 잡으면 응답이 중간에 잘려 파싱이 실패한다.
# max_tokens 는 상한일 뿐 실제 과금은 생성된 토큰 기준이므로 넉넉히 둔다.
MAX_OUTPUT_TOKENS = 16000


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    available = True

    def __init__(self, settings: Settings) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - 설치 환경 문제
            raise LLMUnavailable(
                "anthropic 패키지가 설치되어 있지 않습니다. requirements.txt 를 설치하세요."
            ) from exc

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=settings.llm_api_key)
        self._model = settings.llm_model or DEFAULT_MODEL

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
        anthropic = self._anthropic
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.AuthenticationError as exc:
            raise LLMUnavailable("Anthropic API 키가 올바르지 않습니다.") from exc
        except anthropic.NotFoundError as exc:
            raise LLMUnavailable(f"모델을 찾을 수 없습니다: {self._model}") from exc
        except anthropic.RateLimitError as exc:
            raise LLMUnavailable("Anthropic API 호출 한도를 초과했습니다.") from exc
        except anthropic.APIStatusError as exc:
            raise LLMUnavailable(f"Anthropic API 오류({exc.status_code})") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMUnavailable("Anthropic API 에 연결하지 못했습니다.") from exc

        if response.stop_reason == "refusal":
            raise LLMUnavailable("모델이 응답을 거부했습니다.")
        if response.stop_reason == "max_tokens":
            raise LLMUnavailable("응답이 최대 길이에서 잘렸습니다.")

        text = next((block.text for block in response.content if block.type == "text"), "")
        return self.parse_json(text)
