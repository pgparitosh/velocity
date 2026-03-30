"""
Provider Factory.
Responsible for instantiating LLM providers based on the platform configuration.
"""

from typing import Dict
from velocity.config import ProviderConfig
from velocity.core.llm_gateway import ILlmProvider
from velocity.infra.providers.anthropic import AnthropicProvider

# from velocity.infra.providers.google import GoogleProvider
from velocity.infra.providers.groq import GroqProvider
from velocity.infra.providers.ollama import OllamaProvider
from velocity.infra.providers.openai import OpenAIProvider


def create_provider(name: str, config: ProviderConfig) -> ILlmProvider:
    """
    Factory method to create a specific LLM provider instance.
    """
    api_key = config.api_key_env  # In a real app, this would be fetched from env vars
    # For local running, we'll try to get it from environment variables or use the literal value if it's not an env var name
    import os

    actual_api_key = os.environ.get(api_key, api_key)

    if name == "openai":
        return OpenAIProvider(api_key=actual_api_key, models=config.models)
    elif name == "groq":
        return GroqProvider(api_key=actual_api_key, models=config.models)
    elif name == "anthropic":
        return AnthropicProvider(api_key=actual_api_key, models=config.models)
    elif name == "ollama":
        if not config.base_url:
            raise ValueError("Ollama provider requires a base_url configuration.")
        return OllamaProvider(
            api_key=actual_api_key, models=config.models, base_url=config.base_url
        )
    # elif name == "google":
    #     return GoogleProvider(api_key=actual_api_key, models=config.models)
    else:
        raise ValueError(f"Unknown LLM provider: {name}")


def create_all_providers(provider_configs: Dict[str, ProviderConfig]) -> Dict[str, ILlmProvider]:
    """
    Instantiate all configured providers.
    """
    providers = {}
    for name, config in provider_configs.items():
        try:
            providers[name] = create_provider(name, config)
        except Exception as e:
            # Log failure but allow other providers to initialize
            import logging

            logging.getLogger(__name__).error(f"Failed to initialize provider '{name}': {e}")

    return providers
