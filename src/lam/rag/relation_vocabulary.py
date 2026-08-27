from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationType:
    ko_label: str
    wikidata_pid: str
    description: str


# Wikidata 표준 프로퍼티(P번호)에서 가져온 소규모 관계 어휘. relation 인자를
# 모델이 자유롭게 짓지 않고 이 중에서만 고르게 해서(enum 강제) 같은 의미를
# "owns"라고 했다 "has_pet"이라고 했다 하는 일관성 문제를 막는다. P1429/P509/
# P127/P1830은 wikidata.org에서 직접 검색해 확인했고, 나머지는 Wikidata에서
# 널리 쓰이는 표준 프로퍼티다.
RELATION_TYPES: tuple[RelationType, ...] = (
    RelationType("반려동물", "P1429", "A가 기르는 반려동물 B (has pet)"),
    RelationType("소유주", "P127", "A는 B의 소유물이다, 즉 B가 A를 소유 (owned by)"),
    RelationType("소유물", "P1830", "A가 B를 소유한다 (owner of)"),
    RelationType("배우자", "P26", "배우자 관계 (spouse)"),
    RelationType("자녀", "P40", "A의 자녀는 B (child)"),
    RelationType("아버지", "P22", "A의 아버지는 B (father)"),
    RelationType("어머니", "P25", "A의 어머니는 B (mother)"),
    RelationType("형제자매", "P3373", "형제자매 관계 (sibling)"),
    RelationType("직업", "P106", "A의 직업/역할은 B (occupation)"),
    RelationType("고용주", "P108", "A의 고용주는 B (employer)"),
    RelationType("소속", "P463", "A는 B에 소속되어 있다 (member of)"),
    RelationType("거주지", "P551", "A의 거주지는 B (residence)"),
    RelationType("출생지", "P19", "A의 출생지는 B (place of birth)"),
    RelationType("사망원인", "P509", "A의 사망 원인은 B (cause of death)"),
    RelationType("일부", "P361", "A는 B의 일부다 (part of)"),
    RelationType("구성요소", "P527", "A는 B를 구성요소로 가진다 (has part)"),
)

_BY_LABEL = {r.ko_label: r for r in RELATION_TYPES}


def relation_labels() -> list[str]:
    return [r.ko_label for r in RELATION_TYPES]


def wikidata_pid_for(ko_label: str) -> str | None:
    relation = _BY_LABEL.get(ko_label)
    return relation.wikidata_pid if relation else None


def describe_relations() -> str:
    return "\n".join(
        f"- {r.ko_label} ({r.wikidata_pid}): {r.description}" for r in RELATION_TYPES
    )
