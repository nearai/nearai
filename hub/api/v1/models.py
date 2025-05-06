import json
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from os import getenv
from typing import Dict, Iterator, List, Optional

import ftfy
from dotenv import load_dotenv
from nearai.shared.models import RunMode
from openai.types.beta.thread import Thread as OpenAITThread
from openai.types.beta.threads.message import Attachment
from openai.types.beta.threads.message import Message as OpenAITThreadMessage
from openai.types.beta.threads.message_content import MessageContent
from openai.types.beta.threads.message_delta import MessageDelta as OpenAITMessageDelta
from openai.types.beta.threads.message_delta_event import MessageDeltaEvent as OpenAITMessageDeltaEvent
from openai.types.beta.threads.run import Run as OpenAIRun
from openai.types.beta.threads.text import Text
from openai.types.beta.threads.text_content_block import TextContentBlock
from sqlalchemy import BigInteger
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.types import TypeDecorator
from sqlmodel import Column, Field, Session, SQLModel, create_engine

from hub.api.v1.entry_location import EntryLocation

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


class Framework(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"


def sanitize(value):
    """Recursively sanitize data with SingleStore-specific handling."""
    if isinstance(value, str):
        # Fix common encoding errors like mojibake (e.g., "â€™" → "’")
        fixed_text = ftfy.fix_text(value)

        # Normalize Unicode to NFC form for consistent database storage
        normalized = unicodedata.normalize("NFC", fixed_text)

        # Replace invalid UTF-8 characters instead of removing them
        return normalized.encode("utf-8", "replace").decode("utf-8").strip()

    if isinstance(value, list):
        # Recursively process list elements while preserving order
        return [sanitize(item) for item in value]

    if isinstance(value, dict):
        # Clean both keys and values while maintaining dictionary structure
        return {k: sanitize(v) for k, v in value.items()}

    # Return non-string/non-collection values unchanged
    return value


class UnicodeSafeJSON(TypeDecorator):
    """Custom JSON handler that safely stores/retrieves Unicode-rich JSON data.

    Uses LONGTEXT to avoid SingleStore/MySQL encoding bugs.

    Why LONGTEXT instead of JSON:
    1. Bypasses binary storage issues with MySQL JSON type
    2. Guarantees UTF8MB4 compliance through text column handling
    3. Avoids implicit encoding conversions in database drivers

    Inherits from TypeDecorator to customize these behaviors:
    - Safe Unicode serialization (preserves emojis/special chars)
    - Binary-to-text conversion for reliable deserialization
    """

    impl = LONGTEXT  # Critical: Uses text storage instead of binary JSON
    cache_ok = True  # Essential for query caching and performance

    def process_bind_param(self, value, dialect):
        """Serialize Python objects to UTF8MB4-compliant JSON string."""
        if value is not None:
            # Prevent ASCII escaping (\uXXXX sequences) for Unicode chars
            # enable_ascii=False is crucial for emojis/non-Latin chars
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        """Convert database result to Python objects with encoding safety."""
        if value is not None:
            # Force string conversion to handle:
            # - Legacy database drivers returning bytes
            # - Mixed encoding edge cases
            # - SingleStore's binary storage peculiarities
            return json.loads(str(value))
        return value


class RegistryEntry(SQLModel, table=True):
    """Entry stored in the registry."""

    __tablename__ = "registry_entry"
    __table_args__ = {
        "mysql_collate": "utf8mb4_unicode_ci",  # Use case-insensitive Unicode collation for full text search
    }

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
    details: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))
    """Free-form dictionary with details about the entry."""
    show_entry: bool = Field(default=True)
    """Whether to show the entry in the registry by default."""

    def get_framework(self) -> str:
        """Get the framework of the entry."""
        agent_details = self.details.get("agent", {})
        framework = agent_details.get("framework", "minimal")

        if framework in ["minimal", "base"]:
            return Framework.MINIMAL.value
        elif framework in ["web-agent", "standard"]:
            return Framework.STANDARD.value
        else:
            return framework

    def get_key(self, object: Optional[str] = None) -> str:
        """Get the key to the entry or object in S3."""
        assert S3_PREFIX is not None
        key = f"{S3_PREFIX}/{self.namespace}/{self.name}/{self.version}"
        if object is not None:
            key = f"{key}/{object}"
        return key

    def to_location(self) -> EntryLocation:
        """Convert to EntryLocation."""
        return EntryLocation(namespace=self.namespace, name=self.name, version=self.version)

    def is_private(self) -> bool:
        """Check if the entry is private."""
        return self.details.get("private_source", False)


class AgentData(SQLModel, table=True):
    """Agent key value storage."""

    __tablename__ = "agent_data"

    namespace: str = Field(primary_key=True)
    name: str = Field(primary_key=True)
    key: str = Field(primary_key=True)
    value: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)


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


class Fork(SQLModel, table=True):
    __tablename__ = "forks"

    category: str = Field(primary_key=True)
    from_namespace: str = Field(nullable=False)
    from_name: str = Field(nullable=False)
    to_namespace: str = Field(primary_key=True)
    to_name: str = Field(primary_key=True)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: int = Field(default=None, primary_key=True)
    registry_path: str = Field(nullable=False)
    account_id: str = Field(nullable=False)
    status: str = Field(nullable=False)
    worker_id: Optional[str] = Field(default=None)
    worker_kind: str = Field(nullable=False)
    info: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))
    result: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))


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
    info: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))


class Log(SQLModel, table=True):
    __tablename__ = "logs"
    id: int = Field(default=None, primary_key=True)
    account_id: str = Field(nullable=False)
    target: str = Field(nullable=False)
    info: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))


class Delta(SQLModel, table=True):
    __tablename__ = "deltas"
    id: int = Field(default=None, primary_key=True)
    object: str = Field(default="thread.message.delta", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    content: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    step_details: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    filename: Optional[str] = Field(default=None)
    message_id: Optional[str] = Field(default=None, index=True)
    run_id: Optional[str] = Field(default=None, index=True)
    thread_id: Optional[str] = Field(default=None, index=True)

    def to_openai(self) -> OpenAITMessageDeltaEvent:
        """Convert to OpenAI MessageDeltaEvent."""
        return OpenAITMessageDeltaEvent(
            id=str(self.id),
            object="thread.message.delta",
            delta=OpenAITMessageDelta(role="assistant", content=self.content),
        )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=lambda: "msg_" + uuid.uuid4().hex[:24], primary_key=True)
    object: str = Field(default="message", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    thread_id: str = Field(nullable=False, foreign_key="threads.id")
    status: str = Field(default="completed", nullable=False)
    incomplete_details: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    completed_at: Optional[datetime] = Field(default=None)
    incomplete_at: Optional[datetime] = Field(default=None)
    role: str = Field(nullable=False)
    content: List[MessageContent] = Field(sa_column=Column(UnicodeSafeJSON))
    assistant_id: Optional[str] = Field(default=None)
    run_id: Optional[str] = Field(default=None)
    attachments: Optional[List[Attachment]] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    meta_data: Optional[Dict] = Field(default=None, sa_column=Column("metadata", UnicodeSafeJSON))

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

            if isinstance(self.content, Iterator):
                self.content = [
                    TextContentBlock(text=Text(value=content["text"], annotations=[]), type="text")
                    if content["type"] == "text"
                    else content
                    for content in self.content
                ]

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
            "content": "\n".join([c["text"]["value"] for c in self.content]),
            "role": self.role,
        }


class Thread(SQLModel, table=True):
    __tablename__ = "threads"

    id: str = Field(default_factory=lambda: "thread_" + uuid.uuid4().hex[:24], primary_key=True)
    object: str = Field(default="thread", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    tool_resources: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    meta_data: Optional[Dict] = Field(default=None, sa_column=Column("metadata", UnicodeSafeJSON))
    owner_id: str = Field(nullable=False)
    parent_id: Optional[str] = Field(default=None)
    child_thread_ids: List[str] = Field(default=[], sa_column=Column(UnicodeSafeJSON))

    def to_openai(self) -> OpenAITThread:
        """Convert to OpenAI Thread."""
        # Assuming agent_ids is a list, join it into a string
        if self.meta_data and "agent_ids" in self.meta_data:
            agent_ids = ",".join(self.meta_data["agent_ids"])  # Join the list into a single string
            self.meta_data["agent_ids"] = agent_ids

        self.meta_data = self.meta_data or {}
        if self.owner_id:
            self.meta_data["owner_id"] = self.owner_id
        if self.parent_id:
            self.meta_data["parent_id"] = self.parent_id
        if self.child_thread_ids:
            self.meta_data["child_thread_ids"] = json.dumps(self.child_thread_ids)

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
    last_error: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    model: str = Field(nullable=False)
    instructions: Optional[str] = Field(default=None)
    tools: List[Dict] = Field(default=[], sa_column=Column(UnicodeSafeJSON))
    file_ids: List[str] = Field(default=[], sa_column=Column(UnicodeSafeJSON))
    meta_data: Optional[Dict] = Field(default=None, sa_column=Column("metadata", UnicodeSafeJSON))
    usage: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    temperature: Optional[float] = Field(default=None)
    top_p: Optional[float] = Field(default=None)
    max_prompt_tokens: Optional[int] = Field(default=None)
    max_completion_tokens: Optional[int] = Field(default=None)
    truncation_strategy: Optional[Dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    response_format: Optional[str] = Field(default=None)
    tool_choice: Optional[str] = Field(default=None)
    parallel_tool_calls: bool = Field(default=False)
    parent_run_id: Optional[str] = Field(default=None)
    child_run_ids: List[str] = Field(default=[], sa_column=Column(UnicodeSafeJSON))
    run_mode: Optional[RunMode] = Field(default=None)

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


class Delegation(SQLModel, table=True):
    __tablename__ = "delegation"

    id: int = Field(default=None, primary_key=True)
    original_account_id: str = Field(nullable=False)
    delegation_account_id: str = Field(nullable=False)
    expires_at: Optional[datetime] = Field(default=None)


class ScheduledRun(SQLModel, table=True):
    __tablename__ = "scheduled_runs"
    id: int = Field(default=None, primary_key=True)
    thread_id: str = Field(nullable=True)
    agent: str = Field(nullable=False)
    input_message: str = Field(nullable=False)
    run_params: Dict = Field(default_factory=dict, sa_column=Column(UnicodeSafeJSON))
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    created_by: str = Field(nullable=False)
    run_at: datetime = Field(nullable=False)
    has_run: bool = Field(default=False, nullable=False)


class Completion(SQLModel, table=True):
    __tablename__ = "completions"

    id: int = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    account_id: str = Field(max_length=64, nullable=False)
    query: List[dict] = Field(sa_column=Column(UnicodeSafeJSON))
    response: Optional[dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    model: str = Field(sa_column=Column(LONGTEXT))
    provider: str = Field(sa_column=Column(LONGTEXT))
    endpoint: str = Field(sa_column=Column(LONGTEXT))
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    completion_tokens: int = Field(nullable=False)
    prompt_tokens: int = Field(nullable=False)
    total_tokens: int = Field(nullable=False)
    completion_tokens_details: Optional[dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))
    prompt_tokens_details: Optional[dict] = Field(default=None, sa_column=Column(UnicodeSafeJSON))


db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4&use_unicode=1&binary_prefix=true"
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
    "text/javascript": [".js", ".jsx"],
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
    "application/typescript": [".ts", ".tsx"],
    "application/yaml": [".yaml"],
    "image/png": [".png"],
    "image/jpeg": [".jpg"],
    "image/gif": [".gif"],
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
