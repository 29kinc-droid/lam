# Phase 5 — GraphRAG(Neo4j) 스펙

## 온톨로지 (단순화된 범용 스키마)

프로토타입 단계라 도메인을 고정하지 않고 범용 스키마로 시작한다.

- 노드: 단일 라벨 `Entity { name: string (고유키), type: string, description?: string }`
- 관계: 단일 타입 `RELATES_TO { label: string }` — 관계의 구체적 의미는 `label` 속성으로 표현(예: `created_by`, `part_of`, `depends_on`). Cypher에서 동적 관계 타입 파라미터화는 안전하지 않으므로(인젝션 위험) 고정 타입 + 속성 방식을 택함.

## 엔티티 링킹

NER 모델 없이 규칙 기반으로 시작: 사용자 쿼리 문자열에 그래프에 이미 존재하는 엔티티 `name`이 부분 문자열로 포함되는지 검사해서 매칭한다(대소문자 무시). 정교한 NER은 필요해지면 나중에 추가.

## 그래프 순회 및 안전장치

- 매칭된 엔티티에서 `RELATES_TO*1..2`(양방향)로 depth=2까지 순회.
- 안전장치: 매칭 엔티티 최대 5개, 엔티티당 이웃 관계 최대 10개, 전체 서브그래프 트리플 최대 30개로 제한.
- 서브그래프 → 텍스트: `"{source} -[{label}]-> {target}"` 형태의 트리플 나열.

## pgvector RAG와의 관계

Notion 문서는 "교체/병행"으로 열어뒀는데, 이번엔 **병행**으로 결정 — 기존에 동작 확인된 pgvector 검색 결과와 그래프 서브그래프 결과를 시스템 프롬프트에 각각 별도 블록으로 함께 첨부한다. 필요 이상으로 되돌리기 어려운 변경(기존 RAG 제거)을 피하고, 두 검색 결과를 비교하기도 쉬워짐.

## 그래프 툴

`add_entity_relation` 툴: LLM이 사용자로부터 새 사실을 들으면(`"A는 B의 담당자다"` 등) 그래프에 엔티티/관계를 MERGE로 추가한다. 인자: `source_name`, `source_type`(선택), `target_name`, `target_type`(선택), `relation`.

## 인프라

`docker-compose.yml`에 `neo4j:5-community` 추가, Bolt 포트(7687)로 `neo4j` 파이썬 드라이버 연결. 인증은 `.env`의 `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD`.
