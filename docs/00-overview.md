# LAM 프로토타입 개요

> 출처: [Notion — LAM 가상환경 구현 계획](https://app.notion.com/p/3c8df6bcc5de8153927dc8b7abc1cc59). 이 문서는 그 문서의 파이프라인/구조 결정을 로컬 스펙으로 옮긴 것이며, **실제 구현 상태를 반영하는 살아있는 요약 문서**다. Phase가 끝날 때마다 이 문서(특히 파이프라인/기술 결정/진행 상황)를 갱신한다. 각 Phase의 세부 설계는 `docs/0N-*.md`에 따로 적고, 여기서는 그 결과만 요약·링크한다.

## 스코프

- 단일 에이전트 + 툴 몇 개 수준의 최소 기능 LAM 프로토타입
- 프레임워크 없이 커스텀 오케스트레이션(ReAct 루프)
- 목표: 파이프라인 전체(RAG→툴콜링→검증→응답)가 도는 것을 확인

## 진행 상황

| Phase | 상태 | 비고 |
|---|---|---|
| 0. 환경(Windows 네이티브 + Docker) | 완료 | 최초엔 WSL2 Ubuntu로 구성했다가, 툴이 읽기/그래프쓰기로 제한적이라 격리 효용이 낮다고 판단해 Windows 네이티브로 재이전(8단계 참고) |
| 1. 최소 대화 루프 | 완료 | LLM을 Claude API→Ollama로 전환 |
| 2. 툴콜링 | 완료 | 계산기, 파일읽기. 웹검색은 백엔드 미정으로 보류 |
| 3. 상태·에피소드 메모리 | 완료 | Redis(상태), Postgres(에피소드) |
| 4. 벡터 RAG | 완료 | pgvector + `bge-m3` |
| 5. GraphRAG | 완료 | Neo4j, 상세: [`05-graphrag.md`](05-graphrag.md) |
| 6. 검증기 3종 | 완료 | 상세: [`06-validators.md`](06-validators.md) |
| 7. 통합 테스트 | 완료 | `tests/` 22개(단위+e2e) 전체 통과, `max_rounds=5` 유지 |
| 8. Windows 네이티브 재이전 | 완료 | WSL2 Ubuntu 제거, 컨트롤러를 Windows 네이티브 Python으로 이전 |

## 전체 파이프라인 (실제 구현 기준)

Notion 원안의 "LLM 호출 #1(의도파악+쿼리재작성)"은 프로토타입 단순화를 위해 구현하지 않았다 — 단일 LLM 호출로 RAG/그래프 컨텍스트를 시스템 프롬프트에 실어 바로 응답을 생성한다. 입력단 검증도 그에 맞춰 "재작성된 쿼리 검사"가 아니라 "툴 호출 인자 검사"로 대상이 바뀌었다(자세한 이유는 [`06-validators.md`](06-validators.md)).

```
사용자입력
  → [컨트롤러] 상태(Redis) 로드 + 대화이력 로드
  → [RAG] pgvector 벡터 검색 + [GraphRAG] 엔티티 링킹 → 2홉 순회 → 서브그래프
  → [컨트롤러] 시스템 프롬프트 + RAG/그래프 결과 + 툴스키마 조립
  → [LLM 호출] 응답 생성
  → 응답이 tool_calls인가?
      ├─ Yes → [검증 – 입력단] 툴 인자 유효성 검사(규칙 기반)
      │        → [컨트롤러] 실행부 호출 → 결과를 tool 메시지로 추가
      │        → LLM 호출로 회귀(반복, max_rounds=5 제한)
      └─ No(텍스트) → [검증 – 출력단] 근거 기반 사실 일관성(동일 모델 재호출)
               → [검증 – 실행후] 인용 출처 일치 검사(규칙 기반)
               → 문제 있고 라운드 남으면 피드백과 함께 재시도, 아니면
               → 사용자에게 반환 + 상태/에피소드 메모리 기록 후 종료
```

## 시스템 구조도

```
[Windows 호스트]
   ├── Ollama (LLM 서버, 네이티브 실행) ── http://localhost:11434
   │     ├── qwen2.5:7b-instruct (대화·툴콜링·검증용, 전부 동일 모델)
   │     └── bge-m3 (임베딩)
   ├── Docker Desktop ── Redis / Postgres+pgvector / Neo4j (모두 localhost 포트로 노출)
   └── [컨트롤러] ─── 오케스트레이션 루프(파이썬 프로세스, 프레임워크 미사용, Windows 네이티브 uv/venv)
          ├── LLM 클라이언트 (Ollama HTTP API, 같은 머신 localhost)
          ├── 툴 레지스트리 — 계산기, 파일읽기, (그래프 저장) add_entity_relation, (보류) 웹검색
          ├── 상태 저장소 클라이언트 (Redis)
          ├── 에피소드 저장소 클라이언트 (Postgres)
          ├── 벡터 검색 클라이언트 (pgvector)
          ├── 지식그래프 클라이언트 (Neo4j)
          └── 검증기 (규칙 함수 + 동일 Ollama 모델 재사용 호출)
```

Ollama와 Docker 컨테이너는 컨트롤러 입장에서 "외부 서비스"다(전부 localhost 포트). **8단계에서 WSL2 Ubuntu를 완전히 제거하고 컨트롤러를 Windows 네이티브로 재이전**했다 — 이유: 툴 세트가 읽기 전용(`read_file`은 프로젝트 루트 밖 경로 차단) + 스코프 제한된 그래프 쓰기(`add_entity_relation`)뿐이고 쉘 실행/파일 쓰기·삭제 툴이 없어서, OS 격리가 주는 안전 이득이 거의 없는데 인코딩·PATH·네트워킹 문제로 마찰 비용만 컸다. **원칙: 쉘 실행이나 무제한 파일 쓰기/삭제 같은 위험한 툴을 추가하게 되면 그때 격리 방식을 다시 검토한다.**

## 확정된 기술 결정

| 항목 | 결정 |
|---|---|
| LLM | Ollama(Windows 네이티브 실행), 모델 `qwen2.5:7b-instruct` — Anthropic API는 무료 플랜이 없어 오픈웨이트로 전환 |
| 툴콜링 방식 | Ollama 네이티브 `tools=` 파라미터 대신 **프롬프트 기반 툴콜링**(ReAct 원조 방식) 사용 — `tools=`가 특정 자기소개성 질문("네 도구 목록 보여줘" 등)과 결합될 때 빈 응답을 내는 모델 버그를 발견해서 우회. 시스템 프롬프트에 툴 설명 + `<tool_call>{...}</tool_call>` 형식 지시를 텍스트로 넣고, `llm/client.py`가 응답을 직접 파싱(닫는 태그 누락·태그 없이 JSON만 내는 경우 등도 관대하게 처리). temperature도 0.8→0.2로 낮춰 변동성 완화 |
| 임베딩 | `bge-m3` (Ollama) |
| 검증용 소형 LLM | 메인과 동일 모델(`qwen2.5:7b-instruct`), 프롬프트만 다르게 |
| 패키지 매니저 | uv (Windows 네이티브) |
| Python | 3.12 |
| 실행 환경 | 컨트롤러/에이전트 코드는 Windows 네이티브 Python으로 실행. LLM·DB는 같은 머신의 `127.0.0.1` 포트로 접근하는 외부 서비스 (WSL2 Ubuntu는 8단계에서 완전히 제거) |
| 인프라 실행 | Docker Compose (Redis, Postgres+pgvector, Neo4j), Docker Desktop이 Windows에 포트를 직접 노출 |
| 서비스 접속 주소 | 모든 기본 URL(`config.py`)에 `localhost` 대신 `127.0.0.1` 사용 — Windows에서 `localhost`는 IPv6(`::1`)부터 시도하는데 Docker Desktop의 IPv6 포트 매핑이 응답하지 않아 연결이 통째로 멈추는 문제를 실측(psycopg 기준 무한 행 vs `127.0.0.1`은 0.02초)해서 발견 |
| 툴 | 계산기, 파일읽기, `add_entity_relation`(그래프 저장). 웹검색은 백엔드 미정으로 보류 |
| 그래프 온톨로지 | `Entity{name,type}` 노드 + 고정 `RELATES_TO{label}` 관계 (동적 관계 타입은 인젝션 위험으로 배제). 상세: [`05-graphrag.md`](05-graphrag.md) |
| pgvector ↔ GraphRAG | 교체 아닌 **병행** — 두 검색 결과를 시스템 프롬프트에 각각 별도 블록으로 첨부 |
| pgvector 관련성 임계값 | 코사인 거리 `< 0.58`만 채택(`rag/vector_store.py`). 원래 top-k만으로 걸러서 무관한 질문(예: "3+4는?")에도 문서가 매번 끼어드는 문제가 있어 실측 후 추가 |
| RAG 청크 크기 | `chunk_size=100`, `overlap=15`(단어 기준, `rag/chunking.py`) — iGPU(Vulkan) 환경은 입력 컨텍스트 길이에 매우 민감(실측: ~1000자 추가만으로 응답 16배 지연)해서 200→100으로 축소. `top_k=3`은 유지 |
| 빈 응답 재시도 | `qwen2.5:7b-instruct`가 텍스트도 tool_calls도 없는 완전 빈 응답을 내는 경우가 있어(특정 질문+파라미터 조합에서 재현), 빈 응답이면 피드백 메시지와 함께 최대 2회 자동 재시도(`MAX_EMPTY_RETRIES`, `controller/loop.py`). 그래도 안 되면 `EMPTY_RESPONSE_MESSAGE` 반환 |
| 코드 구조 | 기능별 파일 분리 + type hints 필수 (`strict`) |
| 버전관리 | git, GitHub 원격 [`29kinc-droid/lam`](https://github.com/29kinc-droid/lam)(공개), `c:\dev\lam`에 위치. Stop 훅은 로컬 커밋만 하고 자동 푸시는 안 함 |

## 디버그 모드

`.env`에 `DEBUG=1`을 설정하면(또는 `DEBUG=1 uv run python scripts/run_chat.py`처럼 실행 시 지정), 매 LLM 호출 직전에 그 시점의 시스템 프롬프트(RAG/그래프 컨텍스트 포함)와 전체 메시지 이력을 콘솔에 그대로 찍는다(`controller/loop.py`의 `_debug_print`). 학습·디버깅용으로, 라운드가 진행될수록 프롬프트/이력이 어떻게 바뀌는지 확인할 때 쓴다.

## 미확정 — 필요해지면 재확인

- 웹검색 툴의 실제 백엔드 (DuckDuckGo 무료 vs 유료 API) — Phase 2에서 보류 결정
- pgvector/그래프 초기 코퍼스가 지금은 테스트용 샘플(`docs/knowledge/`, 수동으로 넣은 사실 몇 개)뿐 — 실 데이터 소스는 미정

## 구현 로드맵

전체 단계와 파일 구조는 `C:\Users\USER\.claude\plans\lovely-purring-dahl.md`의 Phase 0~7 참조.
