from __future__ import annotations

from dataclasses import dataclass

from neo4j import GraphDatabase

MAX_MATCHED_ENTITIES = 5
MAX_NEIGHBORS_PER_ENTITY = 10
MAX_SUBGRAPH_TRIPLES = 30

MATCH_ENTITIES_QUERY = """
MATCH (e:Entity)
WHERE toLower($search_text) CONTAINS toLower(e.name)
RETURN e.name AS name
LIMIT $limit
"""

SUBGRAPH_QUERY = """
MATCH (start:Entity {name: $name})
MATCH path = (start)-[:RELATES_TO*1..2]-(:Entity)
UNWIND relationships(path) AS rel
RETURN DISTINCT startNode(rel).name AS source, rel.label AS label, endNode(rel).name AS target
LIMIT $limit
"""

MERGE_ENTITY_RELATION_QUERY = """
MERGE (a:Entity {name: $source_name})
  ON CREATE SET a.type = $source_type
MERGE (b:Entity {name: $target_name})
  ON CREATE SET b.type = $target_type
MERGE (a)-[:RELATES_TO {label: $relation}]->(b)
"""


@dataclass(frozen=True)
class Triple:
    source: str
    label: str
    target: str


class GraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def _matched_entities(self, search_text: str) -> list[str]:
        with self._driver.session() as session:
            result = session.run(
                MATCH_ENTITIES_QUERY,
                search_text=search_text,
                limit=MAX_MATCHED_ENTITIES,
            )
            return [str(record["name"]) for record in result]

    def search(self, query: str) -> list[Triple]:
        triples: list[Triple] = []
        seen: set[tuple[str, str, str]] = set()
        with self._driver.session() as session:
            for name in self._matched_entities(query):
                result = session.run(
                    SUBGRAPH_QUERY, name=name, limit=MAX_NEIGHBORS_PER_ENTITY
                )
                for record in result:
                    key = (record["source"], record["label"], record["target"])
                    if key in seen:
                        continue
                    seen.add(key)
                    triples.append(Triple(*key))
                    if len(triples) >= MAX_SUBGRAPH_TRIPLES:
                        return triples
        return triples

    def add_relation(
        self,
        source_name: str,
        source_type: str,
        target_name: str,
        target_type: str,
        relation: str,
    ) -> None:
        with self._driver.session() as session:
            session.run(
                MERGE_ENTITY_RELATION_QUERY,
                source_name=source_name,
                source_type=source_type,
                target_name=target_name,
                target_type=target_type,
                relation=relation,
            )
