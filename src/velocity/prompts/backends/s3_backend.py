"""
S3-based prompt storage backend.
Loads versioned prompt YAML files from an S3 bucket via IObjectStore.
Includes a local cache (in-memory) to avoid redundant network roundtrips.
"""

import yaml
import logging
from typing import Any

from velocity.exceptions import PromptNotFoundError
from velocity.infra import IObjectStore, ICacheBackend
from velocity.prompts.backends.base import IPromptBackend
from velocity.prompts.models import PromptVersion

logger = logging.getLogger(__name__)


class S3PromptBackend(IPromptBackend):
    """
    Implementation of IPromptBackend using an Object Store (e.g., S3).
    Expects prompt files to be stored as YAML blobs:
    prompts/{prompt_id}/{version}.yaml
    """

    def __init__(self, object_store: IObjectStore, cache: ICacheBackend | None = None):
        self.object_store = object_store
        self.cache = cache

    def _get_key(self, prompt_id: str, version: str) -> str:
        """Construct the S3 key for a prompt version."""
        return f"prompts/{prompt_id}/{version}.yaml"

    async def fetch(self, prompt_id: str, version: str = "latest") -> PromptVersion:
        """
        Fetch a prompt version from the object store.
        Uses the local cache if available.
        """
        key = self._get_key(prompt_id, version)
        
        # Check cache first
        if self.cache:
            cached_data = await self.cache.get(key)
            if cached_data:
                logger.debug(f"Prompt cache hit for {key}")
                data = yaml.safe_load(cached_data)
                return self._parse_data(prompt_id, version, data)

        # Fetch from object store
        logger.debug(f"Fetching {key} from S3")
        raw_bytes = await self.object_store.get_object(key)
        
        if not raw_bytes:
            # Fallback for simple prompts without versioning structure
            alt_key = f"prompts/{prompt_id}.yaml"
            if version == "latest":
                raw_bytes = await self.object_store.get_object(alt_key)
                
            if not raw_bytes:
                raise PromptNotFoundError(
                    f"Prompt '{prompt_id}' version '{version}' not found in S3",
                    details={"key": key}
                )

        try:
            content = raw_bytes.decode("utf-8")
            data = yaml.safe_load(content)
            
            # Populate cache
            if self.cache:
                await self.cache.set(key, content, ttl_seconds=3600)  # 1 hour cache
                
            return self._parse_data(prompt_id, version, data)
        except Exception as e:
            logger.error(f"Error parsing prompt from {key}: {e}")
            raise PromptNotFoundError(
                f"Failed to load prompt '{prompt_id}': {str(e)}",
                details={"key": key}
            )

    def _parse_data(self, prompt_id: str, version: str, data: dict[str, Any]) -> PromptVersion:
        """Helper to convert YAML data into a PromptVersion object."""
        return PromptVersion(
            prompt_id=data.get("prompt_id", prompt_id),
            version=data.get("version", version),
            content=data.get("content", ""),
            author=data.get("author"),
            changelog=data.get("changelog"),
            model_hint=data.get("model_hint"),
            eval_score=data.get("eval_score"),
            variables=data.get("variables", []),
            metadata=data.get("metadata", {})
        )

    async def list_versions(self, prompt_id: str) -> list[str]:
        """
        List all versions for a prompt.
        Note: requires IObjectStore to support listing or prefix queries.
        If not supported, returns an empty list.
        """
        # This implementation depends on IObjectStore having listing capabilities.
        # For now, we return an empty list as IPromptBackend is Protocol-based 
        # and base IObjectStore didn't specify list_objects.
        return []

    async def health_check(self) -> bool:
        """Verify the object store is reachable."""
        return await self.object_store.health_check()
