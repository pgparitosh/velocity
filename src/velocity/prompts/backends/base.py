"""
Abstractions governing where deterministic Prompt content is stored.
E.g., Git-tracked YAML files (FileBackend) or Immutable Object storage (S3Backend).
"""

from typing import Protocol, runtime_checkable

from velocity.prompts.models import PromptVersion


@runtime_checkable
class IPromptBackend(Protocol):
    """
    Protocol describing how external string resources (Prompt text) are 
    resolved and loaded into the immutable caching layer.
    """

    async def fetch(self, prompt_id: str, version: str = "latest") -> PromptVersion:
        """
        Retrieves a specifically addressed Prompt definition.
        
        Args:
            prompt_id: Identifier of the prompt block (e.g., 'kyc_agent_system')
            version: Target version pin (e.g., '1.3.4' or 'latest')
            
        Raises:
            PromptNotFoundError if the addressed block does not exist.
        """
        ...

    async def list_versions(self, prompt_id: str) -> list[str]:
        """
        Returns all known semantic tags/versions associated with a prompt root ID.
        Useful for auditing or 'canary' rollout verification.
        """
        ...
        
    async def health_check(self) -> bool:
        """Verify reachability of the underlying backend."""
        ...
