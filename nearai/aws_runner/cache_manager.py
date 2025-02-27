"""Cache manager for AWS Lambda runners.

This module provides centralized cache management with explicit state reset
capabilities, ensuring proper isolation between invocations.

Cache Behavior:
- Agent cache: stores immutable cache entries for agents, keyed by agent identifier
- Provider models cache: stores provider models with a timestamp, allowing for expiration

The cache is designed to prevent state leakage between AWS Lambda invocations while
preserving intentional caching of expensive resources.
"""

import copy
import logging
import time
from typing import Any, Dict, Optional, Tuple

from nearai.agents.agent import Agent
from nearai.aws_runner.cache_models import AgentCacheEntry, ProviderModelsCacheEntry

# Set up logging
logger = logging.getLogger("CacheManager")


class CacheManager:
    """Manages caching and state isolation for Lambda invocations.

    This class centralizes all caching operations to prevent state leakage
    between AWS Lambda invocations while preserving intentional caching of
    expensive resources.
    """

    _instance = None  # Singleton instance

    def __new__(cls):
        """Implement singleton pattern for centralized cache management."""
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize cache state."""
        # Agent cache: maps agent identifiers to immutable cache entries
        self._agent_cache: Dict[str, AgentCacheEntry] = {}

        # Provider models cache
        self._provider_models_cache: Optional[ProviderModelsCacheEntry] = None

        logger.debug("CacheManager initialized")

    def cache_agent(self, agent: Agent) -> None:
        """Cache a clean agent before it runs any code.

        Args:
        ----
            agent: The agent to cache

        """
        try:
            # Create an immutable cache entry from the agent
            cache_entry = AgentCacheEntry.from_agent(agent)

            # Store in the cache
            self._agent_cache[agent.identifier] = cache_entry
            logger.debug("Cached agent: %s", agent.identifier)
        except Exception as e:
            logger.error("Failed to cache agent %s: %s", getattr(agent, "identifier", "unknown"), str(e))
            # We log the error but don't raise it to avoid disrupting execution

    def get_agent(self, agent_identifier: str) -> Optional[Agent]:
        """Get a fresh agent instance from the cache.

        Args:
        ----
            agent_identifier: The agent identifier to retrieve

        Returns:
        -------
            A fresh Agent instance or None if not found or an error occurs

        """
        try:
            cache_entry = self._agent_cache.get(agent_identifier)
            if not cache_entry:
                logger.debug("Agent cache miss: %s", agent_identifier)
                return None

            # Create a clean agent instance from the cached data
            # Deep copy to ensure complete isolation
            agent = Agent(
                cache_entry.identifier,
                copy.deepcopy(cache_entry.agent_files),
                copy.deepcopy(cache_entry.metadata),
                change_to_temp_dir=True,
            )
            logger.debug("Agent cache hit: %s", agent_identifier)
            return agent
        except Exception as e:
            logger.error("Error retrieving agent %s from cache: %s", agent_identifier, str(e))
            # Return None instead of propagating the exception
            return None

    def cache_provider_models(self, models: Any) -> None:
        """Cache provider models with a timestamp.

        Args:
        ----
            models: The provider models to cache

        """
        try:
            self._provider_models_cache = ProviderModelsCacheEntry(
                models=copy.deepcopy(models),
                timestamp=time.time(),
            )
            logger.debug("Cached provider models")
        except Exception as e:
            logger.error("Failed to cache provider models: %s", str(e))
            # We log the error but don't raise it

    def get_provider_models(self, max_age_seconds: float = 3600) -> Optional[Tuple[Any, float]]:
        """Get provider models if available and not expired.

        Args:
        ----
            max_age_seconds: Maximum age in seconds for cached models

        Returns:
        -------
            A tuple of (models, age_in_seconds) or None if expired or not found or an error occurs

        """
        try:
            if not self._provider_models_cache:
                logger.debug("Provider models cache miss: no cache entry")
                return None

            current_time = time.time()
            age = current_time - self._provider_models_cache.timestamp

            # Return None if too old
            if age > max_age_seconds:
                logger.debug("Provider models cache expired: age=%f seconds", age)
                return None

            # Return a copy of the models to ensure isolation
            models_copy = copy.deepcopy(self._provider_models_cache.models)
            logger.debug("Provider models cache hit: age=%f seconds", age)
            return models_copy, age

        except Exception as e:
            logger.error("Error retrieving provider models from cache: %s", str(e))
            # Return None instead of propagating the exception
            return None


# Initialize the singleton instance
cache_manager = CacheManager()
