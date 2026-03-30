"""
Text Embedding Abstractions and Providers.
Converts arbitrary text strings into fixed-length floating point vectors
for semantic search and classification.
"""

from typing import Protocol, runtime_checkable

from openai import AsyncOpenAI


@runtime_checkable
class ITextEmbedder(Protocol):
    """Protocol for embedding models."""
    
    async def embed_text(self, text: str) -> list[float]:
        """Convert text to a vector."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Convert a list of texts to vectors."""
        ...


class MockEmbedder(ITextEmbedder):
    """Static mock for testing and local dev without API calls."""
    
    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        # Return a deterministic mock vector based on text length or content
        val = float(len(text)) / 100.0
        return [val] * self.dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(t) for t in texts]


class OpenAIEmbedder(ITextEmbedder):
    """OpenAI implementation using text-embedding-3-small by default."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed_text(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=self.model
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Remove newlines for better performance as per OpenAI docs
        cleaned = [t.replace("\n", " ") for t in texts]
        response = await self.client.embeddings.create(
            input=cleaned,
            model=self.model
        )
        return [item.embedding for item in response.data]
