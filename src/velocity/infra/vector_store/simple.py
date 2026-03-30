"""
Simple In-Memory Vector Store for Local Development.
Uses basic list-based search with cosine similarity. 
Not performant for large datasets but sufficient for unit tests and scaffolding.
"""

import math
from typing import Any

from velocity.infra import IVectorStore


class SimpleVectorStore(IVectorStore):
    """
    Naive vector store that holds all data in memory.
    """
    
    def __init__(self) -> None:
        # collection_name -> list of {id, vector, payload}
        self.collections: dict[str, list[dict[str, Any]]] = {}

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
        magnitude_v1 = math.sqrt(sum(a * a for a in v1))
        magnitude_v2 = math.sqrt(sum(b * b for b in v2))
        
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0.0
            
        return dot_product / (magnitude_v1 * magnitude_v2)

    async def upsert(
        self, collection: str, vector_id: str, vector: list[float], payload: dict[str, Any]
    ) -> None:
        if collection not in self.collections:
            self.collections[collection] = []
        
        # Check if ID already exists and update it
        for item in self.collections[collection]:
            if item["id"] == vector_id:
                item["vector"] = vector
                item["payload"] = payload
                return
        
        # Otherwise append new
        self.collections[collection].append({
            "id": vector_id,
            "vector": vector,
            "payload": payload
        })

    async def search(
        self, collection: str, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        if collection not in self.collections:
            return []
        
        # Calculate similarities
        scored_results = []
        for item in self.collections[collection]:
            score = self._cosine_similarity(query_vector, item["vector"])
            scored_results.append({
                "score": score,
                "payload": item["payload"]
            })
            
        # Sort by score descending
        sorted_results = sorted(scored_results, key=lambda x: x["score"], reverse=True)
        
        # Return top_k payloads
        return [res["payload"] for res in sorted_results[:top_k]]

    async def health_check(self) -> bool:
        return True
