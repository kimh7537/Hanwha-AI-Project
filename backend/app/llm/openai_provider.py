"""OpenAI provider — Chat Completions REST 호출.

Anthropic provider 와 동일한 계약(complete_json)을 만족시키는 대체 경로다.
실패 시 LLMUnavailable 을 던지고, 되돌리기는 RunContext 가 담당한다.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.llm.base import LLMProvider, LLMUnavailable

API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o"
TIMEOUT_SECONDS = 90.0


class OpenAIProvider(LLMProvider):
    name = "openai"
    available = True

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model or DEFAULT_MODEL

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # 프롬프트가 이미 "JSON 객체 하나만 출력" 을 요구하므로 JSON 모드를 함께 건다
            "response_format": {"type": "json_object"},
        }

        try:
            response = httpx.post(
                API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"OpenAI API 에 연결하지 못했습니다: {exc}") from exc

        if response.status_code == 401:
            raise LLMUnavailable("OpenAI API 키가 올바르지 않습니다.")
        if response.status_code == 429:
            raise LLMUnavailable("OpenAI API 호출 한도를 초과했습니다.")
        if response.status_code >= 400:
            raise LLMUnavailable(f"OpenAI API 오류({response.status_code})")

        try:
            choice = response.json()["choices"][0]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable("OpenAI 응답 형식을 해석하지 못했습니다.") from exc

        if choice.get("finish_reason") == "length":
            raise LLMUnavailable("응답이 최대 길이에서 잘렸습니다.")

        return self.parse_json(choice.get("message", {}).get("content", ""))
