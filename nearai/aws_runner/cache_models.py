import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Union

"""
Cache models for the AWS Runner caching system.

This module defines immutable data structures used for caching expensive resources
like agent data and provider models. The cache system is designed to:

1. Improve performance by reusing expensive resources across invocations
2. Ensure complete state isolation to prevent data leakage between users
3. Support configurable expiration for time-sensitive cached data

The cache can be controlled through environment variables:
- USE_AGENT_CACHE: When set to "false", disables agent caching (default: "true")
"""


@dataclass(frozen=True)
class AgentCacheEntry:
    """Immutable cache entry for agent data.

    This class stores the minimal data required to recreate a clean agent instance.
    It's immutable to prevent accidental modifications that could cause state leakage.

    Cached agents are deep-copied when retrieved to ensure complete isolation
    between invocations, preventing any state leakage between different users.
    """

    identifier: str
    agent_files: Union[List[Dict[str, Any]], Path]  # We store this as-is but deep copy during retrieval
    metadata: Dict[str, Any]  # We store this as-is but deep copy during retrieval

    @classmethod
    def from_agent(cls, agent):
        """Create a cache entry from an agent instance.

        This should be called before the agent runs any code to ensure
        we're capturing a clean state.
        """
        return cls(
            identifier=agent.identifier,
            # Create copies to ensure isolation
            agent_files=copy.deepcopy(agent.agent_files),
            metadata=copy.deepcopy(agent.metadata or {}),
        )


@dataclass(frozen=True)
class ProviderModelsCacheEntry:
    """Immutable cache entry for provider models.

    Stores provider models data with a timestamp to ensure freshness.
    Provider models are automatically expired after a configurable timeout
    (default: 3600 seconds) to ensure we don't use outdated model information.
    """

    models: Any  # The actual models data
    timestamp: float  # When the cache was created/updated
