"""
Data structures for managing versioned system prompts.
Enables A/B testing, rollout deployments, and deterministic prompt tracking.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class PromptVersion:
    """
    Represents a specific, immutable version of a semantic instruction block (System Prompt).
    Loaded from storage (e.g., File, S3, Git).
    """
    
    prompt_id: str
    version: str
    content: str
    
    author: str | None = None
    changelog: str | None = None
    model_hint: str | None = None
    eval_score: float | None = None
    
    # Expected substitution variables (e.g., "{customer_name}")
    variables: list[str] = field(default_factory=list)
    
    # Additional semantic descriptors
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def fully_qualified_name(self) -> str:
        """Returns the canonical reference, e.g., 'fraud-agent@2.3.0'"""
        return f"{self.prompt_id}@{self.version}"
