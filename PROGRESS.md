last-commit: 1e9efc0059daa88ca46646a01aa4d70537ad8311

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

## 남은 것 / 다음 시작점

- 웹검색 툴 백엔드 미정 (DuckDuckGo 무료 vs 유료 API) — 필요해지면 결정.
- pgvector/그래프 초기 코퍼스가 테스트용 샘플뿐 — 실 데이터 소스 미정.
- 로드맵상 Phase 7까지가 끝. 이후는 사용자 요청에 따라 새 작업(예: 실제 문서/데이터 연동, 웹검색 백엔드 결정, 배포 방식 등) 논의.

## 특이사항

- 세션 초반, `.claude/settings.json`의 Stop 훅(`git add -A`)이 프로젝트 폴더에 같이 있던 무관한 SVN 프로젝트 폴더를 실수로 커밋한 적이 있음. 디스크로 복구 후 `.gitignore`에 등록하고 git 히스토리를 완전히 정리(squash + gc)했다 — 그래서 커밋 로그가 짧고 시작 커밋 메시지가 "chore: squash history..."로 되어 있는 이유.
