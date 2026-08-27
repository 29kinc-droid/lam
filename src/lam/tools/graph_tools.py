from __future__ import annotations

from typing import Any

from lam.rag.graph_store import GraphStore
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
        )
        return f"지식그래프에 추가함: {source_name} -[{relation}]-> {target_name}"

    return Tool(
        name="add_entity_relation",
        description=(
            "지식그래프에 새로운 엔티티와 사실(관계)을 추가할 때 사용한다. "
            "사용자가 알려준 사람·동물·사물·개념에 대한 새로운 사실이면 업무 관계뿐 "
            "아니라 나이, 소유·반려동물, 소속, 사망 원인 등 어떤 종류든 이 툴로 "
            "저장한다 (예: 'A는 B의 담당자다', 'A는 30살이다', 'A는 B라는 개를 "
            "키운다', 'B는 노환으로 죽었다'). 한 이야기에 여러 사실이 섞여 있으면 "
            "사실마다 이 툴을 한 번씩 나눠서 여러 번 호출해라(<tool_call> 블록을 "
            "여러 개 연달아 쓰면 된다). 단순 질문 응답에는 사용하지 않는다."
        ),
        fn=add_entity_relation,
        parameters={
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "출발 엔티티 이름"},
                "source_type": {
                    "type": "string",
                    "description": "출발 엔티티 타입 (예: person, tool, concept)",
                },
                "target_name": {"type": "string", "description": "도착 엔티티 이름"},
                "target_type": {"type": "string", "description": "도착 엔티티 타입"},
                "relation": {
                    "type": "string",
                    "description": "관계를 설명하는 라벨 (예: 'created_by', 'part_of')",
                },
            },
            "required": ["source_name", "target_name", "relation"],
        },
    )
