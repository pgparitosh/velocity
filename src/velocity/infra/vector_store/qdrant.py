"""
Qdrant Vector Store Backend.
Connects to a remote Qdrant cluster for production-grade semantic storage.
"""

from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from velocity.infra import IVectorStore


class QdrantBackend(IVectorStore):
    """
    Production implementation of IVectorStore using Qdrant.
    """
    
    def __init__(self, url: str, api_key: str | None = None):
        self.client = AsyncQdrantClient(url=url, api_key=api_key)
        self.vector_name = "content"

    async def upsert(
        self, collection: str, vector_id: str, vector: list[float], payload: dict[str, Any]
    ) -> None:
        """
        Ensures a record is indexed, creating the collection if it doesn't exist.
        """
        # (Simplified) Check collection before use; for prod we might do this in a boot method
        try:
           await self.client.get_collection(collection_name=collection)
        except Exception:
           # Defaulting to 1536 for OpenAI if not provided; in prod we'd pass this in config
           await self.client.create_collection(
               collection_name=collection,
               vectors_config=models.VectorParams(size=len(vector), distance=models.Distance.COSINE)
           )

        await self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=vector_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

    async def search(
        self, collection: str, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Executes a semantic similarity search against the indexed points.
        """
        try:
            results = await self.client.search(  # type: ignore[attr-defined]
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True
            )
            return [res.payload for res in results if res.payload]
        except Exception:
            return []

    async def health_check(self) -> bool:
        """Lightweight collections check to verify connectivity."""
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False
