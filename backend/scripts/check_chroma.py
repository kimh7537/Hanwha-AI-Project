"""Chroma Cloud 연결과 검색 순위를 실제 자격증명으로 점검한다.

`.env` 의 `CHROMA_*` 세 값을 읽어 실제 코드 경로(`retrieval.ChromaRetriever`)를 그대로 돌린다.
테스트는 conftest 가 `CHROMA_*` 를 비우기 때문에 이 경로를 절대 타지 않는다 — 실물 확인은 여기서 한다.

사용:
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\check_chroma.py
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\check_chroma.py --list
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\check_chroma.py --cleanup

키 값은 절대 출력하지 않는다. 설정 여부만 표시한다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Windows 콘솔 기본 코드페이지(cp949)로는 한글과 기호를 못 찍고 UnicodeEncodeError 로 죽는다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except AttributeError:  # pragma: no cover - 파이프로 넘어간 경우
        pass

from app.config import get_settings  # noqa: E402
from app.models.contracts import Chunk  # noqa: E402
from app.services import retrieval  # noqa: E402

SELFTEST_NAMESPACE = "selftest"

# 마지막 chunk 에만 질의와 맞는 내용이 있다. 임베딩이 실제로 동작하면 이것이 1위여야 한다.
SELFTEST_CHUNKS = [
    Chunk(id="chunk-01", index=0, page=1, text="회사 소개와 조직 구성에 대한 배경 설명이다."),
    Chunk(id="chunk-02", index=1, page=1, text="사무실 위치와 근무 환경을 안내하는 문단이다."),
    Chunk(id="chunk-03", index=2, page=2, text="도입 효과로 담당자의 문서 확인 시간이 크게 줄었다."),
]
SELFTEST_QUERY = "도입 효과 시간 단축"
EXPECTED_TOP = "chunk-03"


def _report_settings() -> bool:
    settings = get_settings()
    print("[설정]")
    for name, value in (
        ("CHROMA_API_KEY", settings.chroma_api_key),
        ("CHROMA_TENANT", settings.chroma_tenant),
        ("CHROMA_DATABASE", settings.chroma_database),
    ):
        print(f"  {name}: {'설정됨' if value else '비어 있음'}")
    if not settings.chroma_enabled:
        print("\n세 값이 모두 있어야 임베딩 검색이 켜진다. 지금은 keyword 검색으로 동작한다.")
        return False
    return True


def _list_collections() -> int:
    client = retrieval.build_cloud_client(get_settings())
    names = [
        name
        for name in (_collection_names(client))
        if name.startswith(retrieval.COLLECTION_PREFIX)
    ]
    print(f"\n[컬렉션] {len(names)}개")
    for name in names:
        print(f"  {name}")
    return 0


def _collection_names(client: object) -> list[str]:
    """chromadb 버전에 따라 문자열 또는 객체 목록을 돌려준다."""
    result = client.list_collections()  # type: ignore[attr-defined]
    return [item if isinstance(item, str) else getattr(item, "name", str(item)) for item in result]


def _cleanup() -> int:
    """`audiencedeck-` 컬렉션을 모두 지운다.

    문서마다 컬렉션이 하나 생기고 파이프라인은 지우지 않는다. 저장 요금은 미미하지만
    쌓이는 것은 사실이라, 정리는 이 스크립트로 명시적으로 한다.
    """
    client = retrieval.build_cloud_client(get_settings())
    names = [n for n in _collection_names(client) if n.startswith(retrieval.COLLECTION_PREFIX)]
    if not names:
        print("\n지울 컬렉션이 없다.")
        return 0
    for name in names:
        client.delete_collection(name)  # type: ignore[attr-defined]
        print(f"  삭제: {name}")
    print(f"\n{len(names)}개 삭제했다.")
    return 0


def _selftest(keep: bool) -> int:
    settings = get_settings()
    print("\n[연결]")
    client = retrieval.build_cloud_client(settings)
    print("  Chroma Cloud 연결 성공")
    try:
        print(f"  최대 배치 크기: {client.get_max_batch_size()}")  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        print(f"  최대 배치 크기: 확인 불가 ({exc})")

    print("\n[색인·검색]")
    retriever = retrieval.ChromaRetriever(settings, client=client)
    ranked = retriever.rank(SELFTEST_CHUNKS, SELFTEST_QUERY, SELFTEST_NAMESPACE)
    print(f"  질의: {SELFTEST_QUERY}")
    print(f"  순위: {' > '.join(ranked)}")

    ok = ranked[0] == EXPECTED_TOP
    if ok:
        print(f"  판정: 통과 — 질의와 맞는 {EXPECTED_TOP} 이 1위다.")
    else:
        print(f"  판정: 실패 — {EXPECTED_TOP} 이 1위여야 하는데 {ranked[0]} 이 나왔다.")

    print("\n[재색인 생략 확인]")
    collection = client.get_or_create_collection(  # type: ignore[attr-defined]
        name=retrieval._collection_name(SELFTEST_NAMESPACE)
    )
    print(f"  컬렉션 보관 개수: {collection.count()} (chunk {len(SELFTEST_CHUNKS)}개와 같아야 한다)")

    if not keep:
        client.delete_collection(  # type: ignore[attr-defined]
            retrieval._collection_name(SELFTEST_NAMESPACE)
        )
        print("\n점검용 컬렉션을 삭제했다.")

    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Chroma Cloud 연결·검색 점검")
    parser.add_argument("--list", action="store_true", help="audiencedeck-* 컬렉션 목록만 출력")
    parser.add_argument("--cleanup", action="store_true", help="audiencedeck-* 컬렉션을 모두 삭제")
    parser.add_argument("--keep", action="store_true", help="점검용 컬렉션을 지우지 않는다")
    args = parser.parse_args()

    if not _report_settings():
        return 1

    try:
        if args.list:
            return _list_collections()
        if args.cleanup:
            return _cleanup()
        return _selftest(keep=args.keep)
    except retrieval.RetrievalError as exc:
        print(f"\n실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
