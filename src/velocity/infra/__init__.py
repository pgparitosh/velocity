"""
Infrastructure abstractions for the Velocity platform.
Allows swapping of underlying data stores via configuration with zero code changes.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ICacheBackend(Protocol):
    """Abstraction for caching mechanisms (e.g., Redis, In-Memory)."""

    async def get(self, key: str) -> str | None:
        """Retrieve a value by key."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """Store a value by key, optionally with a time-to-live."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        ...

    async def health_check(self) -> bool:
        """Check if the cache backend is reachable."""
        ...


@runtime_checkable
class IDatabaseBackend(Protocol):
    """Abstraction for persistent relational storage (e.g., PostgreSQL, SQLite)."""

    async def execute(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        """Execute a write query (INSERT/UPDATE/DELETE)."""
        ...

    async def fetch_one(self, query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Execute a read query returning a single row as a dictionary."""
        ...

    async def fetch_all(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a read query returning multiple rows as dictionaries."""
        ...

    async def health_check(self) -> bool:
        """Check if the database backend is reachable."""
        ...


@runtime_checkable
class IObjectStore(Protocol):
    """Abstraction for blob/document storage (e.g., S3, Local FS)."""

    async def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Upload raw data to object storage."""
        ...

    async def get_object(self, key: str) -> bytes | None:
        """Retrieve raw data from object storage."""
        ...

    async def delete_object(self, key: str) -> bool:
        """Delete an object by key."""
        ...

    async def health_check(self) -> bool:
        """Check if the object storage backend is reachable."""
        ...


@runtime_checkable
class IVectorStore(Protocol):
    """Abstraction for semantic embeddings storage (e.g., Qdrant, pgvector)."""

    async def upsert(self, collection: str, vector_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        """Insert or update a vector and its metadata payload."""
        ...

    async def search(self, collection: str, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve the top-k most similar vectors, returning their payloads."""
        ...

    async def health_check(self) -> bool:
        """Check if the vector store backend is reachable."""
        ...


@runtime_checkable
class IEventStream(Protocol):
    """Abstraction for asynchronous event publishing/consumption (e.g., Redis Streams)."""

    async def publish(self, topic: str, event_data: dict[str, Any]) -> str:
        """Publish an event to a topic, returning the message ID."""
        ...

    async def consume(self, topic: str, consumer_group: str, max_messages: int = 10) -> list[dict[str, Any]]:
        """Consume pending events from a topic."""
        ...

    async def health_check(self) -> bool:
        """Check if the event stream backend is reachable."""
        ...
