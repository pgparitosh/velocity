"""
Platform configuration and service initialization.
"""

import os
from typing import Any

from velocity.observability.dev import DevObservabilityPlugin


def create_dev_observability_plugin(config: Any = None) -> DevObservabilityPlugin | None:
    """
    Create a dev observability plugin based on platform configuration and environment.

    Priority:
    1. VELOCITY_DEV_LOGGING environment variable
    2. platform_config.yaml observability.dev_logging.enabled
    3. Development environment check

    Args:
        config: Configuration object with optional 'observability' attribute

    Returns:
        DevObservabilityPlugin if enabled, None otherwise
    """
    if config is None:
        config = {}

    # Check environment variable first (highest priority)
    env_logging = os.getenv("VELOCITY_DEV_LOGGING", "").lower()
    if env_logging == "false":
        return None
    if env_logging == "true":
        # Explicitly enabled via environment
        verbose = os.getenv("VELOCITY_DEV_LOGGING_VERBOSE", "").lower() == "true"
        return DevObservabilityPlugin(enabled=True, verbose=verbose)

    # Handle both dict and config object
    if hasattr(config, "get"):
        # It's a dict-like object
        obs_config = config.get("observability", {})
        dev_config = obs_config.get("dev_logging", {})
        environment = config.get("environment", "prod")
    else:
        # It's a config object
        obs_config = getattr(config, "observability", {})
        dev_config = getattr(obs_config, "dev_logging", {})
        environment = getattr(config, "environment", "prod")

    # Only create in dev environment
    if environment != "dev":
        return None

    enabled = (
        dev_config.get("enabled", True)
        if hasattr(dev_config, "get")
        else getattr(dev_config, "enabled", True)
    )
    verbose = (
        dev_config.get("verbose", False)
        if hasattr(dev_config, "get")
        else getattr(dev_config, "verbose", False)
    )

    if enabled:
        return DevObservabilityPlugin(enabled=True, verbose=verbose)

    return None
