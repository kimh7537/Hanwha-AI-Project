---
name: evidence-audit
description: 생성 결과 JSON의 원문 근거 무결성을 감사한다. 모든 슬라이드가 source_refs를 갖는지, refs가 실제 존재하는 chunk id인지, 슬라이드·스크립트의 숫자가 원문에 있는지 검사한다. 파이프라인 결과를 만든 직후, 데모 리허설 전, 또는 "근거가 제대로 붙었나" 확인할 때 사용한다.
---

# 원문 근거 감사

이 프로젝트의 핵심 주장은 **"모든 문장에 원문 근거가 있다"**이다.
데모에서 이 주장이 깨지면 평가 항목 두 개(산출물 퀄리티, 현업 적용 가능성)가 함께 무너진다.

## 실행

```powershell
backend\.venv\Scripts\python.exe .claude\skills\evidence-audit\audit.py <결과JSON경로>
```

결과 JSON은 `POST /api/presentations/generate` 응답을 그대로 저장한 파일이거나,
`source_analysis` / `slide_deck` / `presentation_support` 키를 가진 객체면 된다.

## 검사 항목

1. **근거 보유** — 모든 슬라이드에 `source_refs`가 1개 이상 (데모 성공 기준 4번)
2. **근거 유효성** — 모든 `source_refs`가 `source_analysis.source_evidence`의 id에 존재
3. **숫자 대조** — 슬라이드·스크립트의 숫자 토큰이 참조된 chunk 원문에 존재
4. **미검증 항목** — `unverified` 배열이 비어 있지 않으면 그 내용을 표시

## 판정 후 행동

- 1·2번 실패 → `slide-planner` 또는 `doc-analyzer` 서브에이전트에 수정을 위임한다.
- 3번 실패 → `verifier`가 `number_error`로 잡아야 하는 케이스다. 검증 모듈이 놓쳤다면 규칙을 보강한다.
- 4번은 실패가 아니다. 근거를 못 찾은 항목이 **정직하게 표시되고 있다**는 뜻이며 데모에서 강점으로 설명한다.

감사 결과를 요약해 보고하고, 통과하지 못한 항목은 어느 모듈이 고쳐야 하는지 명시하라.
