from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel


class SimilaritySearch(BaseModel):
    file_id: str
    chunk_text: str
    distance: float


class ChunkingStrategy(BaseModel):
    """Defines the chunking strategy for vector stores."""

    pass


class ExpiresAfter(BaseModel):
    """Defines the expiration policy for vector stores."""

    anchor: Literal["last_active_at"]
    """The anchor point for expiration calculation."""
    days: int
    """The number of days after which the vector store expires."""


class CreateVectorStoreRequest(BaseModel):
    """Request model for creating a new vector store."""

    chunking_strategy: Optional[ChunkingStrategy] = None
    """The chunking strategy to use for the vector store."""
    expires_after: Optional[ExpiresAfter] = None
    """The expiration time for the vector store."""
    file_ids: Optional[List[str]] = None
    """The file IDs to attach to the vector store."""
    metadata: Optional[Dict[str, str]] = None
    """The metadata to attach to the vector store."""
    name: str
    """The name of the vector store."""


class Source(BaseModel):
    type: str


class GitHubSource(Source):
    type: str = "github"
    owner: str
    repo: str
    branch: str = "main"


class GitLabSource(Source):
    type: str = "gitlab"
    owner: str
    repo: str
    branch: str = "main"


class CreateVectorStoreFromSourceRequest(BaseModel):
    name: str
    source: Union[GitHubSource, GitLabSource]
    source_auth: Optional[str] = None
    chunking_strategy: Optional[ChunkingStrategy] = None
    expires_after: Optional[ExpiresAfter] = None
    metadata: Optional[Dict[str, str]] = None
