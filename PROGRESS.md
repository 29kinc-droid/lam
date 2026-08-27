last-commit: 90f96e32623c3ad02ea34b8832a5037fd6b22c84

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

## RAG 테스트 코퍼스 확장 + 성능 튜닝

- `docs/knowledge/`에 한국어 위키백과 발췌 5개(인공지능/축구/커피/블록체인/광합성) 추가 → 서로 다른 주제 질문마다 정확히 해당 문서만 검색되는 것 확인.
- **GPU 관련 정정**: 이 머신은 디스크리트 GPU가 없지만, Ollama가 실제로는 Intel Iris Xe 내장 GPU를 **Vulkan 백엔드로 사용 중**이었다(`ollama ps` → `100% GPU`, 서버 로그에 `offloaded 25/25 layers to GPU`). "CPU 전용"이라고 말한 이전 설명은 부정확했음.
- **응답 속도 실측**: 입력 컨텍스트 길이가 iGPU 환경에서 응답 속도에 매우 큰 영향을 준다(출력 길이를 고정하고 컨텍스트만 ~1000자 추가 → 2.67초에서 43.66초로, 약 16배 지연). 이에 따라 `rag/chunking.py`의 `DEFAULT_CHUNK_SIZE`를 200→100단어로 축소(`top_k=3`은 유지).
- 별도로 확인된 점: 검증 재시도가 걸리면 LLM 호출이 2번(때로 그 이상)으로 늘어 총 응답 시간에 청크 크기보다 더 큰 영향을 줌 — 특히 `qwen2.5:7b-instruct`가 과학/전문용어 설명 시 한국어 강제 지시에도 중국어를 섞어 써서 검증기가 이를 잡아내고 재시도가 도는 경우가 있음(모델 자체의 한계, 미해결 — 필요시 정규식 기반 언어 감지로 느린 LLM 검증 없이 빠르게 재시도시키는 방법 검토 가능).

## Windows 네이티브 재이전

- 현재 툴 세트가 읽기 전용(`read_file`, 프로젝트 루트 밖 경로 차단) + 스코프 제한된 그래프 쓰기(`add_entity_relation`)뿐이고 쉘 실행·파일 쓰기/삭제 툴이 없어서, WSL2 Ubuntu 격리가 주는 안전 이득이 거의 없다고 판단. 반면 이 세션 내내 인코딩(PowerShell↔WSL pty), PATH 소싱, `.wslconfig` 미러링 네트워킹 설정 등 마찰 비용은 컸음.
- 컨트롤러를 Windows 네이티브 Python(uv)으로 재이전: `.venv`를 Linux용에서 Windows용으로 재생성, ruff/mypy/pytest 전부 재확인.
- WSL Ubuntu-24.04 배포판 완전 제거(`wsl --unregister`), `.wslconfig`(미러링 네트워킹) 삭제로 시스템 설정 원복. Docker Desktop/Ollama는 원래도 Windows 네이티브라 변경 없음 — Docker 컨테이너가 Windows에 포트를 직접 노출하므로 WSL 경유 자체가 불필요해짐.
- **원칙**: 쉘 실행이나 무제한 파일 쓰기/삭제 같은 위험한 툴을 나중에 추가하게 되면, 그 시점에 격리 방식(VM/컨테이너 샌드박스 등)을 다시 검토한다.
- **마이그레이션 중 발견한 버그**: Windows 네이티브에서 `psycopg`가 `postgresql://...@localhost:5432/...`로 연결 시 무한정 멈춤(TCP 자체는 `Test-NetConnection`으로 즉시 연결됨에도). 원인은 Windows가 `localhost`를 IPv6(`::1`)부터 시도하는데, Docker Desktop이 `docker ps`에 `[::]:5432->5432/tcp`로 광고는 하지만 실제로는 응답하지 않아 거기서 멈추는 것 — `127.0.0.1`로 바꾸면 0.02초에 즉시 연결됨. `config.py`의 모든 기본 서비스 URL(`OLLAMA_HOST`/`REDIS_URL`/`DATABASE_URL`/`NEO4J_URI`)을 `localhost`→`127.0.0.1`로 변경, `.env.example`도 갱신. 테스트 31개 재통과 확인.

## 그래프 저장 툴 개선 + 빈 응답 재시도

- **실사용 중 발견**: `add_entity_relation` 툴 설명 예시가 "A는 B의 담당자다" 같은 업무 관계로 좁아서, "사람 이름+나이+반려동물 사연" 같은 개인적 사실은 모델이 저장 대상으로 인식하지 못하고 그냥 텍스트로만 응답(검증기가 그 텍스트를 걸어서 재시도만 낭비) → 툴 설명을 넓히고 "여러 사실은 tool_call을 여러 번 나눠 호출"하도록 명시(`tools/graph_tools.py`). 개선 후 재현 테스트: 모델이 스스로 이야기를 2개 트리플로 쪼개서 정확히 그래프에 저장하는 것 확인.
- 그래프 스키마(Entity + 관계 하나)가 나이 같은 스칼라 속성은 자연스럽게 표현 못 하는 한계는 남아있음 — 필요해지면 Entity에 property 지원 추가 검토(보류 결정).
- **빈 응답 재시도 추가**: `qwen2.5:7b-instruct`가 텍스트도 tool_calls도 없는 완전 빈 응답을 내는 경우(그래프 저장 후 확인 메시지 생성 등에서 재현)를 위해, 빈 응답이면 피드백과 함께 최대 2회 자동 재시도하도록 `controller/loop.py`에 추가. 결정적 단위 테스트(`test_loop_empty_response_retry.py`) 2개 추가, 전체 33개 통과.

## 남은 것 / 다음 시작점

- 웹검색 툴 백엔드 미정 (DuckDuckGo 무료 vs 유료 API) — 필요해지면 결정.
- `qwen2.5:7b-instruct`가 전문용어 설명 시 중국어를 섞어 쓰는 문제 미해결 — 발생 시 검증 재시도로 응답이 느려짐. 필요해지면 정규식 기반 언어 감지 추가 검토.
- pgvector/그래프 초기 코퍼스가 테스트용 샘플뿐 — 실 데이터 소스 미정.
- 로드맵상 Phase 7까지가 끝. 이후는 사용자 요청에 따라 새 작업(예: 실제 문서/데이터 연동, 웹검색 백엔드 결정, 배포 방식 등) 논의.

## 특이사항

- 세션 초반, `.claude/settings.json`의 Stop 훅(`git add -A`)이 프로젝트 폴더에 같이 있던 무관한 SVN 프로젝트 폴더를 실수로 커밋한 적이 있음. 디스크로 복구 후 `.gitignore`에 등록하고 git 히스토리를 완전히 정리(squash + gc)했다 — 그래서 커밋 로그가 짧고 시작 커밋 메시지가 "chore: squash history..."로 되어 있는 이유.
