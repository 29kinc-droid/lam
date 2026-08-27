from __future__ import annotations

from typing import Any

from lam.rag.graph_store import GraphStore
from lam.rag.relation_vocabulary import describe_relations, relation_labels, wikidata_pid_for
from lam.tools.registry import Tool

UNKNOWN_TYPE = "unknown"


def build_graph_tool(store: GraphStore) -> Tool:
    def add_entity_relation(args: dict[str, Any]) -> str:
        source_name = str(args["source_name"])
        target_name = str(args["target_name"])
        relation = str(args["relation"])
        store.add_relation(
            source_name=source_name,
            source_type=str(args.get("source_type", UNKNOWN_TYPE)),
            target_name=target_name,
            target_type=str(args.get("target_type", UNKNOWN_TYPE)),
            relation=relation,
            wikidata_pid=wikidata_pid_for(relation),
        )
        return f"지식그래프에 추가함: {source_name} -[{relation}]-> {target_name}"

    return Tool(
        name="add_entity_relation",
        description=(
            "지식그래프에 새로운 엔티티와 사실(관계)을 추가할 때 사용한다. "
            "사용자가 알려준 사람·동물·사물·개념에 대한 새로운 사실이면 아래 관계 "
            "종류 중 하나로 저장한다 (예: 'A는 B라는 반려동물을 키운다' → 반려동물, "
            "'B는 노환으로 죽었다' → 사망원인). 한 이야기에 여러 사실이 섞여 있으면 "
            "사실마다 이 툴을 한 번씩 나눠서 여러 번 호출해라(<tool_call> 블록을 "
            "여러 개 연달아 쓰면 된다). 목록에 맞는 관계가 없으면 이 툴을 쓰지 "
            "않는다. 단순 질문 응답에는 사용하지 않는다.\n\n"
            "사용 가능한 관계 종류(Wikidata 표준 프로퍼티 기반):\n" + describe_relations()
        ),
        fn=add_entity_relation,
        parameters={
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "출발 엔티티 이름"},
                "source_type": {
                    "type": "string",
                    "description": "출발 엔티티 타입 (예: person, animal, organization)",
                },
                "target_name": {"type": "string", "description": "도착 엔티티 이름"},
                "target_type": {"type": "string", "description": "도착 엔티티 타입"},
                "relation": {
                    "type": "string",
                    "enum": relation_labels(),
                    "description": "관계 종류 (아래 목록 중에서만 선택)",
                },
            },
            "required": ["source_name", "target_name", "relation"],
        },
    )
