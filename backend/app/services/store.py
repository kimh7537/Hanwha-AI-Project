"""인메모리 저장소.

MVP 범위에는 DB 가 없다(docs/00-overview.md). 프로세스 재시작 시 사라지지만
데모와 테스트에는 충분하며, 나중에 파일/DB 로 바꿔도 이 인터페이스만 유지하면 된다.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from app.models.contracts import Chunk, DocumentMeta, GenerateResponse, PageContent


@dataclass
class StoredDocument:
    meta: DocumentMeta
    chunks: list[Chunk] = field(default_factory=list)
    # 파싱한 원본 쪽 그대로. chunk 는 쪽 경계를 넘으므로 원본 대조에는 이쪽이 필요하다.
    pages: list[PageContent] = field(default_factory=list)
    # 원본 PPTX 바이트. export 가 이 파일 위에 결과를 얹어 이미지·표·서식을 살린다.
    # PPTX 가 아닌 입력이면 None 이다. (인메모리라 업로드 상한 30MB 만큼 메모리를 쓴다)
    source: bytes | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(chunk.text for chunk in self.chunks)


class Store:
    def __init__(self) -> None:
        self._documents: dict[str, StoredDocument] = {}
        self._presentations: dict[str, GenerateResponse] = {}
        self._lock = threading.Lock()

    # 문서 ---------------------------------------------------------------

    @staticmethod
    def new_document_id() -> str:
        return f"doc-{uuid.uuid4().hex[:8]}"

    def save_document(self, document: StoredDocument) -> StoredDocument:
        with self._lock:
            self._documents[document.meta.document_id] = document
        return document

    def get_document(self, document_id: str) -> StoredDocument | None:
        return self._documents.get(document_id)

    # 발표 결과 ----------------------------------------------------------

    @staticmethod
    def new_presentation_id() -> str:
        return f"pres-{uuid.uuid4().hex[:8]}"

    def save_presentation(self, response: GenerateResponse) -> GenerateResponse:
        with self._lock:
            self._presentations[response.presentation_id] = response
        return response

    def get_presentation(self, presentation_id: str) -> GenerateResponse | None:
        return self._presentations.get(presentation_id)

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
            self._presentations.clear()


store = Store()
