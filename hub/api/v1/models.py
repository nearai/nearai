import uuid
from contextlib import contextmanager
from datetime import datetime
from os import getenv
from typing import Dict, Iterator, List, Optional

from dotenv import load_dotenv
from openai.types.beta.thread import Thread as OpenAITThread
from openai.types.beta.threads.message import Attachment
from openai.types.beta.threads.message import Message as OpenAITThreadMessage
from openai.types.beta.threads.message_content import MessageContent
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.text import Text
from openai.types.beta.threads.text_content_block import TextContentBlock
from sqlmodel import JSON, Column, Field, Session, SQLModel, create_engine

load_dotenv()

S3_ENDPOINT = getenv("S3_ENDPOINT")
S3_BUCKET = getenv("S3_BUCKET")
S3_PREFIX = getenv("S3_PREFIX")
DB_HOST = getenv("DATABASE_HOST")
DB_USER = getenv("DATABASE_USER")
DB_PASSWORD = getenv("DATABASE_PASSWORD")
DB_NAME = getenv("DATABASE_NAME")
STORAGE_TYPE = getenv("STORAGE_TYPE", "file")
DB_POOL_SIZE = int(getenv("DATABASE_POOL_SIZE", 10))


class RegistryEntry(SQLModel, table=True):
    """Entry stored in the registry."""

    __tablename__ = "registry_entry"

    id: int = Field(default=None, primary_key=True)
    namespace: str = Field(nullable=False)
    """Namespace under which the entry is stored. Usually the username (NEAR account id) of the owner."""
    name: str = Field(nullable=False)
    """Name of the entry."""
    version: str = Field(nullable=False)
    """Version of the entry."""
    time: datetime = Field(default_factory=datetime.now, nullable=False)
    """Time when the entry was added to the registry."""
    description: str = Field(default="", nullable=False)
    """Long description of the entry."""
    category: str = Field(default="", nullable=False)
    """Type of the entry, e.g. 'dataset', 'model', 'agent', ...."""
    details: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    """Free-form dictionary with details about the entry."""
    show_entry: bool = Field(default=True)
    """Whether to show the entry in the registry by default."""

    def get_key(self, object: Optional[str] = None) -> str:
        """Get the key to the entry or object in S3."""
        assert S3_PREFIX is not None
        key = f"{S3_PREFIX}/{self.namespace}/{self.name}/{self.version}"
        if object is not None:
            key = f"{key}/{object}"
        return key

    def is_private(self) -> bool:
        """Check if the entry is private."""
        return self.details.get("private_source", False)


class HubSecrets(SQLModel, table=True):
    """Encrypted hub secrets stored in the registry."""

    __tablename__ = "hub_secrets"

    id: int = Field(default=None, primary_key=True)

    owner_namespace: str = Field(nullable=False)
    """Owner of the secret"""

    namespace: str = Field(nullable=False)
    """Namespace of the secret recipient"""
    name: str = Field(default="", nullable=False)
    """Name of the secret recipient"""
    version: str = Field(default="", nullable=False)
    """Version of the secret recipient"""

    key: str = Field(nullable=False)
    value: str = Field(nullable=False)

    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    """Time when the entry was added to the registry."""
    description: str = Field(default="", nullable=False)
    """Long description of the entry."""
    category: str = Field(default="", nullable=False)
    """Type of the entry, e.g. 'dataset', 'model', 'agent', ...."""


class Tags(SQLModel, table=True):
    """Many-to-many table between registry entries and tags."""

    __tablename__ = "entry_tags"

    registry_id: int = Field(primary_key=True)
    tag: str = Field(primary_key=True)


class Stars(SQLModel, table=True):
    account_id: str = Field(primary_key=True)
    namespace: str = Field(primary_key=True)
    name: str = Field(primary_key=True)


class Jobs(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    registry_path: str = Field(nullable=False)
    account_id: str = Field(nullable=False)
    status: str = Field(nullable=False)
    worker_id: Optional[str] = Field(default=None)
    info: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    result: Dict = Field(default_factory=dict, sa_column=Column(JSON))


class Permissions(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    account_id: str = Field(nullable=False)
    permission: str = Field(nullable=False)


class Benchmark(SQLModel, table=True):
    __tablename__ = "benchmarks"

    id: int = Field(default=None, primary_key=True)
    namespace: str = Field(nullable=False)
    benchmark: str = Field(nullable=False)
    solver: str = Field(nullable=False)
    args: str = Field(nullable=False)


class BenchmarkResult(SQLModel, table=True):
    __tablename__ = "benchmark_results"

    id: int = Field(default=None, primary_key=True)
    benchmark_id: int = Field(nullable=False)
    index: int = Field(nullable=False)
    solved: bool = Field(nullable=False)
    info: Dict = Field(default_factory=dict, sa_column=Column(JSON))


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=lambda: "msg_" + uuid.uuid4().hex[:24], primary_key=True)
    object: str = Field(default="message", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    thread_id: str = Field(nullable=False, foreign_key="threads.id")
    status: str = Field(default="completed", nullable=False)
    incomplete_details: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    completed_at: Optional[datetime] = Field(default=None)
    incomplete_at: Optional[datetime] = Field(default=None)
    role: str = Field(nullable=False)
    content: List[MessageContent] = Field(sa_column=Column(JSON))
    assistant_id: Optional[str] = Field(default=None)
    run_id: Optional[str] = Field(default=None)
    attachments: Optional[List[Attachment]] = Field(default=None, sa_column=Column(JSON))
    meta_data: Optional[Dict] = Field(default=None, sa_column=Column("metadata", JSON))

    def __init__(self, **data):  # noqa: D107
        super().__init__(**data)
        if not is_valid_thread_message_role(self.role):
            raise ValueError(f"Invalid role: {self.role}")
        if not is_valid_message_status(self.status):
            raise ValueError(f"Invalid status: {self.status}")
        if self.attachments:
            # Convert each attachment to a dictionary
            self.attachments = [
                attachment.model_dump() if hasattr(attachment, "model_dump") else attachment
                for attachment in self.attachments
            ]
        if self.content:
            if isinstance(self.content, str):
                self.content = [TextContentBlock(text=Text(value=self.content, annotations=[]), type="text")]

            # Handle both Pydantic models and dictionaries
            self.content = [
                content.model_dump() if hasattr(content, "model_dump") else content for content in self.content
            ]

    def to_openai(self) -> OpenAITThreadMessage:
        """Convert to OpenAI Thread."""
        return OpenAITThreadMessage(
            metadata=self.meta_data,
            created_at=int(self.created_at.timestamp()),
            id=self.id,
            object="thread.message",
            role=self.role,  # type: ignore
            content=self.content,
            status=self.status,  # type: ignore
            attachments=self.attachments,
            thread_id=self.thread_id,
            run_id=self.run_id,
            assistant_id=self.assistant_id,
            completed_at=int(self.completed_at.timestamp()) if self.completed_at else None,
            incomplete_at=int(self.incomplete_at.timestamp()) if self.incomplete_at else None,
        )

    def to_completions_model(self):
        """Transform to a model compatible with OpenAI completions API."""
        print("self.content", self.content)
        return {
            "id": self.id,
            "content": "\n".join([c["text"]["value"] for c in self.content]),
            "role": self.role,
        }


class Thread(SQLModel, table=True):
    __tablename__ = "threads"

    id: str = Field(default_factory=lambda: "thread_" + uuid.uuid4().hex[:24], primary_key=True)
    object: str = Field(default="thread", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    tool_resources: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    meta_data: Optional[Dict] = Field(default=None, sa_column=Column("metadata", JSON))
    owner_id: str = Field(nullable=False)

    def to_openai(self) -> OpenAITThread:
        """Convert to OpenAI Thread."""
        return OpenAITThread(
            metadata=self.meta_data,
            tool_resources=None,  # TODO: Implement conversion
            created_at=int(self.created_at.timestamp()),
            id=self.id,
            object="thread",
        )


class Run(SQLModel, table=True):
    __tablename__ = "runs"

    id: str = Field(default_factory=lambda: "run_" + uuid.uuid4().hex[:24], primary_key=True)
    object: str = Field(default="thread.run", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    assistant_id: str = Field(nullable=False)
    thread_id: str = Field(nullable=False, foreign_key="threads.id")
    status: str = Field(default="queued")
    started_at: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    failed_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    last_error: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    model: str = Field(nullable=False)
    instructions: Optional[str] = Field(default=None)
    tools: List[Dict] = Field(default=[], sa_column=Column(JSON))
    file_ids: List[str] = Field(default=[], sa_column=Column(JSON))
    meta_data: Optional[Dict] = Field(default=None, sa_column=Column("metadata", JSON))
    usage: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    temperature: Optional[float] = Field(default=None)
    top_p: Optional[float] = Field(default=None)
    max_prompt_tokens: Optional[int] = Field(default=None)
    max_completion_tokens: Optional[int] = Field(default=None)
    truncation_strategy: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    response_format: Optional[str] = Field(default=None)
    tool_choice: Optional[str] = Field(default=None)
    parallel_tool_calls: bool = Field(default=False)

    def __init__(self, **data):  # noqa: D107
        super().__init__(**data)
        if not is_valid_run_status(self.status):
            raise ValueError(f"Invalid status: {self.status}")

    def to_openai(self) -> OpenAIRun:
        """Convert to OpenAI Run object."""
        return OpenAIRun(
            id=self.id,
            object="thread.run",
            created_at=int(self.created_at.timestamp()),
            assistant_id=self.assistant_id,
            thread_id=self.thread_id,
            status=self.status,  # type: ignore
            started_at=int(self.started_at.timestamp()) if self.started_at else None,
            expires_at=int(self.expires_at.timestamp()) if self.expires_at else None,
            cancelled_at=int(self.cancelled_at.timestamp()) if self.cancelled_at else None,
            failed_at=int(self.failed_at.timestamp()) if self.failed_at else None,
            completed_at=int(self.completed_at.timestamp()) if self.completed_at else None,
            last_error=None,
            model=self.model,
            instructions=self.instructions or "",
            tools=[],
            metadata=self.meta_data,
            usage=None,
            temperature=self.temperature,
            top_p=self.top_p,
            max_prompt_tokens=self.max_prompt_tokens,
            max_completion_tokens=self.max_completion_tokens,
            truncation_strategy=None,
            response_format=None,
            tool_choice=None,
            parallel_tool_calls=self.parallel_tool_calls,
        )


db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(db_url, pool_size=DB_POOL_SIZE)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


# Constants for file URI prefixes
FILE_URI_PREFIX = "file::"
S3_URI_PREFIX = "s3::"


SUPPORTED_MIME_TYPES = {
    "text/x-c": [".c"],
    "text/x-c++": [".cpp"],
    "text/css": [".css"],
    "text/csv": [".csv"],
    "text/html": [".html"],
    "text/x-java": [".java"],
    "text/javascript": [".js"],
    "text/markdown": [".md"],
    "text/x-php": [".php"],
    "text/x-python": [".py"],
    "text/x-script.python": [".py"],
    "text/x-ruby": [".rb"],
    "text/x-tex": [".tex"],
    "text/plain": [".txt"],
    "text/xml": [".xml"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".a"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/json": [".json"],
    "application/pdf": [".pdf"],
    "application/typescript": [".ts"],
    "application/yaml": [".yaml"],
}

SUPPORTED_TEXT_ENCODINGS = ["utf-8", "utf-16", "ascii"]


def is_valid_thread_message_role(role: str) -> bool:
    # Only "user" and "assistant" are allowed: https://platform.openai.com/docs/api-reference/messages/createMessage
    return role in ("user", "assistant")


def is_valid_message_status(status: str) -> bool:
    return status in ("in_progress", "incomplete", "completed")


def is_valid_run_status(status: str) -> bool:
    return status in (
        "queued",
        "in_progress",
        "requires_action",
        "cancelling",
        "cancelled",
        "failed",
        "completed",
        "incomplete",
        "expired",
    )
