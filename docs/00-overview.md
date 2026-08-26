# LAM 프로토타입 개요

> 출처: [Notion — LAM 가상환경 구현 계획](https://app.notion.com/p/3c8df6bcc5de8153927dc8b7abc1cc59). 이 문서는 그 문서의 파이프라인/구조 결정을 로컬 스펙으로 옮긴 것이며, **실제 구현 상태를 반영하는 살아있는 요약 문서**다. Phase가 끝날 때마다 이 문서(특히 파이프라인/기술 결정/진행 상황)를 갱신한다. 각 Phase의 세부 설계는 `docs/0N-*.md`에 따로 적고, 여기서는 그 결과만 요약·링크한다.

## 스코프

- 단일 에이전트 + 툴 몇 개 수준의 최소 기능 LAM 프로토타입
- 프레임워크 없이 커스텀 오케스트레이션(ReAct 루프)
- 목표: 파이프라인 전체(RAG→툴콜링→검증→응답)가 도는 것을 확인

## 진행 상황

| Phase | 상태 | 비고 |
|---|---|---|
| 0. 환경(WSL2 Ubuntu + Docker) | 완료 | |
| 1. 최소 대화 루프 | 완료 | LLM을 Claude API→Ollama로 전환 |
| 2. 툴콜링 | 완료 | 계산기, 파일읽기. 웹검색은 백엔드 미정으로 보류 |
| 3. 상태·에피소드 메모리 | 완료 | Redis(상태), Postgres(에피소드) |
| 4. 벡터 RAG | 완료 | pgvector + `bge-m3` |
| 5. GraphRAG | 완료 | Neo4j, 상세: [`05-graphrag.md`](05-graphrag.md) |
| 6. 검증기 3종 | 완료 | 상세: [`06-validators.md`](06-validators.md) |
| 7. 통합 테스트 | 완료 | `tests/` 22개(단위+e2e) 전체 통과, `max_rounds=5` 유지 |

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
   └── Docker Desktop (WSL2 백엔드) ── Redis / Postgres+pgvector / Neo4j

[WSL2 Ubuntu-24.04] ─── /mnt/c/dev/lam 마운트
        │
        ▼
[컨트롤러] ─── 오케스트레이션 루프(파이썬 프로세스, 프레임워크 미사용)
   ├── LLM 클라이언트 (Ollama HTTP API, WSL 미러링 네트워킹으로 Windows 접근)
   ├── 툴 레지스트리 — 계산기, 파일읽기, (그래프 저장) add_entity_relation, (보류) 웹검색
   ├── 상태 저장소 클라이언트 (Redis)
   ├── 에피소드 저장소 클라이언트 (Postgres)
   ├── 벡터 검색 클라이언트 (pgvector)
   ├── 지식그래프 클라이언트 (Neo4j)
   └── 검증기 (규칙 함수 + 동일 Ollama 모델 재사용 호출)
```

LLM(Ollama)과 Docker 컨테이너는 "외부 서비스"로 취급한다 — Ubuntu 안에서 돌리는 건 컨트롤러(에이전트 코드)뿐이다. WSL은 `.wslconfig`에 `networkingMode=mirrored`가 설정되어 있어 `localhost`를 Windows와 공유한다.

## 확정된 기술 결정

| 항목 | 결정 |
|---|---|
| LLM | Ollama(Windows 네이티브 실행), 모델 `qwen2.5:7b-instruct` — Anthropic API는 무료 플랜이 없어 오픈웨이트로 전환 |
| 임베딩 | `bge-m3` (Ollama) |
| 검증용 소형 LLM | 메인과 동일 모델(`qwen2.5:7b-instruct`), 프롬프트만 다르게 |
| 패키지 매니저 | uv (WSL Ubuntu 안에 별도 설치, Windows uv와 별개) |
| Python | 3.12 |
| 실행 환경 | 컨트롤러/에이전트 코드는 WSL2 Ubuntu-24.04 안에서 실행, LLM·DB는 Windows/Docker Desktop의 외부 서비스로 접근 |
| 네트워킹 | WSL 미러링 네트워킹(`.wslconfig`) — WSL에서 `http://localhost:11434`(Ollama), Docker 포트를 그대로 접근 |
| 인프라 실행 | Docker Compose (Redis, Postgres+pgvector, Neo4j), Docker Desktop WSL Integration으로 Ubuntu-24.04에서 `docker`/`docker compose` 사용 |
| 툴 | 계산기, 파일읽기, `add_entity_relation`(그래프 저장). 웹검색은 백엔드 미정으로 보류 |
| 그래프 온톨로지 | `Entity{name,type}` 노드 + 고정 `RELATES_TO{label}` 관계 (동적 관계 타입은 인젝션 위험으로 배제). 상세: [`05-graphrag.md`](05-graphrag.md) |
| pgvector ↔ GraphRAG | 교체 아닌 **병행** — 두 검색 결과를 시스템 프롬프트에 각각 별도 블록으로 첨부 |
| 코드 구조 | 기능별 파일 분리 + type hints 필수 (`strict`) |
| 버전관리 | git 로컬 저장소 (원격 없음), `c:\dev\lam`에 위치 |

## 미확정 — 필요해지면 재확인

- 웹검색 툴의 실제 백엔드 (DuckDuckGo 무료 vs 유료 API) — Phase 2에서 보류 결정
- pgvector/그래프 초기 코퍼스가 지금은 테스트용 샘플(`docs/knowledge/`, 수동으로 넣은 사실 몇 개)뿐 — 실 데이터 소스는 미정

## 구현 로드맵

전체 단계와 파일 구조는 `C:\Users\USER\.claude\plans\lovely-purring-dahl.md`의 Phase 0~7 참조.
