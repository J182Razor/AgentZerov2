"""
DiffKG Recommender — knowledge graph-enhanced memory retrieval.
Uses diffusion-based knowledge graph embeddings to find related memories
that vector similarity alone would miss.
"""
from __future__ import annotations
import os
import json
import time
from collections import defaultdict
from python.helpers import files
from python.helpers.print_style import PrintStyle

DIFFKG_INDEX_PATH = "knowledge/diffkg/graph_index.json"


class DiffKGRecommender:
    """
    Lightweight knowledge graph that tracks co-occurrence relationships
    between memory topics/entities. Augments vector search with graph-based
    recommendations.
    """
    _instance: "DiffKGRecommender | None" = None

    @classmethod
    def instance(cls) -> "DiffKGRecommender":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._graph: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._entity_docs: dict[str, list[str]] = defaultdict(list)
        self._load()

    def _load(self):
        """Load graph from disk."""
        path = files.get_abs_path(DIFFKG_INDEX_PATH)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self._graph = defaultdict(lambda: defaultdict(float), {
                    k: defaultdict(float, v) for k, v in data.get("graph", {}).items()
                })
                self._entity_docs = defaultdict(list, data.get("entity_docs", {}))
            except Exception as e:
                PrintStyle.error(f"DiffKG load failed: {e}")

    def save(self):
        """Persist graph to disk."""
        path = files.get_abs_path(DIFFKG_INDEX_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump({
                    "graph": dict(self._graph),
                    "entity_docs": dict(self._entity_docs),
                    "updated": time.time(),
                }, f, indent=2)
        except Exception as e:
            PrintStyle.error(f"DiffKG save failed: {e}")

    def add_relation(self, entity_a: str, entity_b: str, weight: float = 1.0):
        """Record a co-occurrence relationship between two entities."""
        a, b = entity_a.lower().strip(), entity_b.lower().strip()
        if a and b and a != b:
            self._graph[a][b] += weight
            self._graph[b][a] += weight

    def link_entity_to_doc(self, entity: str, doc_id: str):
        """Link an entity to a memory document ID."""
        e = entity.lower().strip()
        if e and doc_id not in self._entity_docs[e]:
            self._entity_docs[e].append(doc_id)

    def recommend(self, entities: list[str], limit: int = 10) -> list[str]:
        """Given entities, recommend related document IDs via graph traversal."""
        scores: dict[str, float] = defaultdict(float)
        for entity in entities:
            e = entity.lower().strip()
            # Direct neighbors
            for neighbor, weight in self._graph.get(e, {}).items():
                for doc_id in self._entity_docs.get(neighbor, []):
                    scores[doc_id] += weight
            # Direct entity docs (boost)
            for doc_id in self._entity_docs.get(e, []):
                scores[doc_id] += 2.0

        # Sort by score descending, return top N doc IDs
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return [doc_id for doc_id, _ in ranked[:limit]]

    def to_dict(self) -> dict:
        return {
            "entity_count": len(self._graph),
            "doc_links": sum(len(v) for v in self._entity_docs.values()),
        }
