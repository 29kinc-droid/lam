last-commit: a61dce2c1c6aa1cdffaf5f4cc756808dd84de121

# LAM 프로토타입 진행 상황

전체 배경/구조는 [`docs/00-overview.md`](docs/00-overview.md) 참고. 이 문서는 커밋 로그 관점의 진행 요약이다.

## 완료 (Phase 0~7, 전체 로드맵 완료)

- **Phase 0**: WSL2 `Ubuntu-24.04` + uv + Docker Desktop(WSL Integration) 환경 구성.
- **Phase 1**: LLM을 Claude API → Ollama(`qwen2.5:7b-instruct`, Windows 네이티브)로 전환, 최소 대화 루프.
- **Phase 2**: 툴콜링(계산기, 파일읽기). 웹검색은 백엔드 미정으로 보류.
- **Phase 3**: Redis 상태 메모리 + Postgres 에피소드 로그.
- **Phase 4**: pgvector + `bge-m3` 벡터 RAG.
- **Phase 5**: Neo4j GraphRAG(엔티티 링킹 + 2홉 순회) + `add_entity_relation` 툴, pgvector와 병행.
- **Phase 6**: 검증기 3종(입력단 툴인자/출력단 환각체크/실행후 인용검사) + 재시도 루프.
- **Phase 7**: pytest 22개(단위+e2e) 전체 통과. `max_rounds=5` 유지.

## Phase 7 이후 안정화 작업

로드맵 완료 후 사용자가 직접 CLI로 써보면서 실제 버그를 다수 발견/수정:

- **RAG 관련성 임계값 추가**: pgvector 검색이 top-k만 보고 무관한 질문에도 문서를 끌고 오던 문제 → 코사인 거리 `< 0.58` 임계값 추가(`rag/vector_store.py`).
- **디버그 모드 추가/개선**: `DEBUG=1`로 매 턴의 시스템 프롬프트·툴 스키마·라운드별 신규 메시지를 출력(`controller/loop.py`). 처음엔 세션 전체 이력을 매 라운드 반복 출력해서 안 쓰던 오래된 대화가 노이즈로 끼었는데, "턴 시작 시 1회 + 라운드마다 신규 메시지만"으로 재설계.
- **심각한 버그 발견 및 수정**: 출력단 검증기가 너무 엄격해서("근거에 없으면 전부 문제") 정상 답변을 계속 거부 → 모델이 검증을 통과하려고 **가짜 근거를 만드는 툴 호출**(`add_entity_relation`에 지어낸 Alice/Bob 관계)을 실제로 실행해 그래프에 영구 기록하는 사고 발생. 조치: (1) 오염 데이터 삭제, (2) 검증기 evidence에 툴 스키마도 포함, (3) 검증 재시도를 1회로 제한 + 재시도 시 툴 비활성화(`MAX_VALIDATION_RETRIES`).
- **Ollama 네이티브 `tools=` 파라미터 버그 발견**: `qwen2.5:7b-instruct` + `tools=` + 특정 자기소개성 질문("네 도구 목록 보여줘") 조합에서 100% 빈 응답. `tools=` 없이 텍스트로만 설명하면 재현 안 됨 → **프롬프트 기반 툴콜링으로 전면 교체**(`llm/client.py`): 시스템 프롬프트에 툴 설명+포맷 지시, `<tool_call>{...}</tool_call>` 패턴을 직접 파싱(닫는 태그 누락 등도 관대하게 처리). 부수적으로 temperature도 0.2로 낮춤.
- **인코딩 크래시 수정**: PowerShell↔WSL pty 인코딩 불일치로 한글 입력이 깨져 `UnicodeEncodeError`로 크래시 → `run_chat.py`에서 stdin/stdout을 `errors="replace"`로 재설정.
- **툴 실행 예외 처리 강화**: `_execute_tool_call`이 `ValueError`만 잡고 있어서 잘못된 툴 인자(빈 계산식 등)로 `SyntaxError` 등이 나면 전체 프로세스가 죽던 문제 → `Exception` 전체를 잡도록 수정.
- 관련 회귀 테스트 추가: `tests/test_llm_client_parsing.py`(7개), `tests/test_vector_store_threshold.py`(2개). 전체 31개 통과.

## 남은 것 / 다음 시작점

- 웹검색 툴 백엔드 미정 (DuckDuckGo 무료 vs 유료 API) — 필요해지면 결정.
- pgvector/그래프 초기 코퍼스가 테스트용 샘플뿐 — 실 데이터 소스 미정.
- 로드맵상 Phase 7까지가 끝. 이후는 사용자 요청에 따라 새 작업(예: 실제 문서/데이터 연동, 웹검색 백엔드 결정, 배포 방식 등) 논의.

## 특이사항

- 세션 초반, `.claude/settings.json`의 Stop 훅(`git add -A`)이 프로젝트 폴더에 같이 있던 무관한 SVN 프로젝트 폴더를 실수로 커밋한 적이 있음. 디스크로 복구 후 `.gitignore`에 등록하고 git 히스토리를 완전히 정리(squash + gc)했다 — 그래서 커밋 로그가 짧고 시작 커밋 메시지가 "chore: squash history..."로 되어 있는 이유.
