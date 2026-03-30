"""
File-based prompt storage backend.
Loads versioned prompt YAML files from a local directory structure.
"""

import os
import yaml
import logging
from typing import Any

from velocity.exceptions import PromptNotFoundError
from velocity.prompts.backends.base import IPromptBackend
from velocity.prompts.models import PromptVersion

logger = logging.getLogger(__name__)


class FilePromptBackend(IPromptBackend):
    """
    Implementation of IPromptBackend for local file storage.
    Expects prompt files in a directory structure:
    root_dir/
      prompt_id/
        v1.0.0.yaml
        v1.1.0.yaml
        latest.yaml (optional, or symlink)
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def _get_prompt_path(self, prompt_id: str, version: str) -> str:
        """Construct the file path for a prompt version."""
        # We look for prompt_id/version.yaml
        return os.path.join(self.root_dir, prompt_id, f"{version}.yaml")

    async def fetch(self, prompt_id: str, version: str = "latest") -> PromptVersion:
        """
        Fetch a prompt version from the filesystem.
        """
        path = self._get_prompt_path(prompt_id, version)
        
        if not os.path.exists(path):
            # Try root_dir/prompt_id.yaml for simple prompts
            alt_path = os.path.join(self.root_dir, f"{prompt_id}.yaml")
            if os.path.exists(alt_path) and version == "latest":
                path = alt_path
            else:
                logger.error(f"Prompt file not found: {path} (alt: {alt_path})")
                raise PromptNotFoundError(
                    f"Prompt '{prompt_id}' version '{version}' not found in {self.root_dir}",
                    details={"path": path}
                )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
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
        except Exception as e:
            logger.error(f"Error loading prompt file {path}: {e}")
            raise PromptNotFoundError(
                f"Failed to load prompt '{prompt_id}': {str(e)}",
                details={"path": path, "original_error": str(e)}
            )

    async def list_versions(self, prompt_id: str) -> list[str]:
        """List all YAML files in the prompt_id directory."""
        dir_path = os.path.join(self.root_dir, prompt_id)
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            return []
            
        versions = []
        for f in os.listdir(dir_path):
            if f.endswith(".yaml"):
                versions.append(f[:-5]) # Strip .yaml
        return sorted(versions)

    async def health_check(self) -> bool:
        """Verify the root directory exists and is readable."""
        return os.path.isdir(self.root_dir) and os.access(self.root_dir, os.R_OK)
