"""청킹: 페이지 텍스트를 근거 단위(chunk)로 자른다 (docs/02-document-analysis.md).

chunk id 는 `chunk-01` 형식(1-based, 2자리 zero-pad)이며 모든 source_refs 가 이 id 를 가리킨다.
페이지 번호를 잃지 않는다 — UI 가 "페이지 N"을 보여줘야 하기 때문이다.
"""

from __future__ import annotations

from app.models.contracts import Chunk
from app.services.document_parser import PageText

# 근거 배지를 클릭했을 때 "읽을 수 있는 한 덩어리"가 나와야 하므로 작게 유지한다.
TARGET_CHARS = 450
MAX_CHARS = 700
OVERLAP_CHARS = 80
MIN_CHARS = 40


def make_chunk_id(index: int) -> str:
    return f"chunk-{index + 1:02d}"


def _split_long_block(block: str) -> list[str]:
    """문단 하나가 MAX_CHARS 를 넘으면 줄 단위로 쪼갠다."""
    if len(block) <= MAX_CHARS:
        return [block]

    parts: list[str] = []
    current: list[str] = []
    length = 0
    for line in block.splitlines():
        if current and length + len(line) > TARGET_CHARS:
            parts.append("\n".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line) + 1
    if current:
        parts.append("\n".join(current))
    return parts


def build_chunks(pages: list[PageText]) -> list[Chunk]:
    """페이지 목록을 chunk 목록으로 변환한다. 문단 경계를 우선한다."""
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_len = 0
    buffer_page = 1

    def flush() -> None:
        nonlocal buffer, buffer_len
        text = "\n\n".join(buffer).strip()
        if len(text) >= MIN_CHARS:
            chunks.append(
                Chunk(
                    id=make_chunk_id(len(chunks)),
                    index=len(chunks),
                    page=buffer_page,
                    text=text,
                )
            )
        elif text and chunks:
            # 너무 짧은 꼬리는 직전 chunk 에 붙인다 (근거가 조각나지 않게)
            chunks[-1].text = f"{chunks[-1].text}\n\n{text}"
        buffer, buffer_len = [], 0

    for page in pages:
        blocks = [b.strip() for b in page.text.split("\n\n") if b.strip()]
        for block in blocks:
            for part in _split_long_block(block):
                if buffer and buffer_len + len(part) > TARGET_CHARS:
                    tail = buffer[-1][-OVERLAP_CHARS:] if buffer else ""
                    flush()
                    buffer_page = page.page
                    if tail:
                        buffer.append(tail)
                        buffer_len = len(tail)
                if not buffer:
                    buffer_page = page.page
                buffer.append(part)
                buffer_len += len(part)

    flush()

    if not chunks and pages:
        # 아주 짧은 문서라도 근거 하나는 있어야 한다
        text = "\n\n".join(p.text.strip() for p in pages if p.text.strip())
        if text:
            chunks.append(Chunk(id=make_chunk_id(0), index=0, page=pages[0].page, text=text))

    return chunks
