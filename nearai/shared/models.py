from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel
from typing_extensions import Required, TypedDict


class ThreadMode(Enum):
    SAME = 1
    FORK = 2
    CHILD = 3


class RunMode(Enum):
    SIMPLE = 0
    WITH_CALLBACK = 1


class SimilaritySearch(BaseModel):
    file_id: str
    chunk_text: str
    distance: float


class SimilaritySearchFile(BaseModel):
    file_id: str
    file_content: str
    distance: float
    filename: str


class StaticFileChunkingStrategyParam(TypedDict, total=False):
    chunk_overlap_tokens: Required[int]
    """The number of tokens that overlap between chunks. The default value is `400`.

    Note that the overlap must not exceed half of `max_chunk_size_tokens`.
    """

    max_chunk_size_tokens: Required[int]
    """The maximum number of tokens in each chunk.

    The default value is `800`. The minimum value is `100` and the maximum value is
    `4096`.
    """


class StaticFileChunkingStrategyObjectParam(TypedDict, total=False):
    static: Required[StaticFileChunkingStrategyParam]
    type: Required[Literal["static"]]


class ChunkingStrategy(BaseModel):
    """Defines the chunking strategy for vector stores."""

    pass


class AutoFileChunkingStrategyParam(TypedDict, total=False):
    type: Required[Literal["auto"]]
    """Always `auto`."""


class ExpiresAfter(TypedDict, total=False):
    anchor: Required[Literal["last_active_at"]]
    """Anchor timestamp after which the expiration policy applies.

    Supported anchors: `last_active_at`.
    """

    days: Required[int]
    """The number of days after the anchor time that the vector store will expire."""


# class ExpiresAfter(BaseModel):
#     """Defines the expiration policy for vector stores."""
#
#     anchor: Literal["last_active_at"]
#     """The anchor point for expiration calculation."""
#     days: int
#     """The number of days after which the vector store expires."""


class CreateVectorStoreRequest(BaseModel):
    """Request model for creating a new vector store."""

    chunking_strategy: Union[AutoFileChunkingStrategyParam, StaticFileChunkingStrategyParam, None] = None
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


class VectorStoreFileCreate(BaseModel):
    """Request model for creating a vector store file."""

    file_id: str
    """File ID returned from upload file endpoint."""


class Delta(BaseModel):
    id: Optional[str] = None
    object: str = "thread.message.delta"
    content: dict
    filename: Optional[str] = None
