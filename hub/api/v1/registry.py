import datetime
import json
import logging
import re
from collections import defaultdict
from os import getenv
from typing import Any, Dict, List, Optional

import boto3
import botocore
import botocore.exceptions
from dotenv import load_dotenv
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from nearai.shared.client_config import DEFAULT_NAMESPACE
from pydantic import BaseModel, field_validator, model_validator
from sqlmodel import col, delete, select, text

from hub.api.v1.auth import AuthToken, get_auth, get_optional_auth
from hub.api.v1.entry_location import EntryLocation, valid_identifier
from hub.api.v1.models import Fork, RegistryEntry, Tags, get_session, sanitize

DEFAULT_NAMESPACE_WRITE_ACCESS_LIST = [
    "spensa2.near",
    "marcelo.near",
    "vadim.near",
    "root.near",
    "cmrfrd.near",
    "pierre-dev.near",
    "alomonos.near",
    "flatirons.near",
    "calebjacob.near",
]

load_dotenv()
S3_BUCKET = getenv("S3_BUCKET")

S3_ENDPOINT = getenv("S3_ENDPOINT")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
)

v1_router = APIRouter(
    prefix="/registry",
    tags=["registry"],
)


# Add logger configuration
logger = logging.getLogger(__name__)

tag_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")


def valid_tag(tag: str) -> str:
    result = tag_pattern.match(tag)
    if result is None:
        raise HTTPException(status_code=400, detail=f"Invalid tag: {repr(tag)}. Should match {tag_pattern.pattern}")
    return result[0]


def with_write_access(use_forms=False):
    default = Depends(EntryLocation.as_form) if use_forms else Body()

    def fn_with_write_access(
        entry_location: EntryLocation = default,
        auth: AuthToken = Depends(get_auth),
    ) -> EntryLocation:
        """Check the user has write access to the entry."""
        if auth.account_id == entry_location.namespace:
            return entry_location
        if entry_location.namespace == DEFAULT_NAMESPACE:
            if auth.account_id in DEFAULT_NAMESPACE_WRITE_ACCESS_LIST:
                return entry_location
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized. Namespace: {entry_location.namespace} != Account: {auth.account_id}",
        )

    return fn_with_write_access


def get_or_create(entry_location: EntryLocation = Depends(with_write_access())) -> int:
    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.namespace == entry_location.namespace,
                RegistryEntry.name == entry_location.name,
                RegistryEntry.version == entry_location.version,
            )
        ).first()

        if entry is None:
            entry = RegistryEntry(
                namespace=entry_location.namespace,
                name=entry_location.name,
                version=entry_location.version,
            )
            session.add(entry)
            session.commit()

        return entry.id


def get(entry_location: EntryLocation = Body()) -> RegistryEntry:
    logger.debug(f"Getting entry: {entry_location}")

    if entry_location.version == "latest":
        return latest_version(entry_location)

    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.namespace == entry_location.namespace,
                RegistryEntry.name == entry_location.name,
                RegistryEntry.version == entry_location.version,
            )
        ).first()

        if entry is None:
            logger.debug(f"Entry not found: {entry_location}")
            raise HTTPException(status_code=404, detail=f"Entry '{entry_location}' not found")

        return entry


def get_read_access(
    entry: RegistryEntry = Depends(get),
    auth: Optional[AuthToken] = Depends(get_optional_auth),
) -> RegistryEntry:
    current_account_id = auth.account_id if auth else None
    if entry.is_private() and entry.namespace != current_account_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return entry


def latest_version(entry_location: EntryLocation = Body()) -> RegistryEntry:
    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry)
            .where(
                RegistryEntry.namespace == entry_location.namespace,
                RegistryEntry.name == entry_location.name,
            )
            .order_by(col(RegistryEntry.id).desc())
            .limit(1)
        ).first()

        if entry is None:
            raise HTTPException(status_code=404, detail=f"Entry '{entry_location}' not found")

        return entry


class EntryMetadataInput(BaseModel):
    category: str
    description: str
    tags: List[str]
    details: Dict
    show_entry: bool

    @model_validator(mode="before")
    @classmethod
    def preprocess_all_fields(cls, data: Any) -> Any:
        """Global preprocessing validator that sanitizes all input data before validation."""
        return sanitize(data)

    @field_validator("tags", mode="after")
    @classmethod
    def process_tags(cls, tags: List[str]) -> List[str]:
        """Post-sanitization processing for tags.

        1. Remove empty/whitespace-only tags
        2. Deduplicate while preserving order
        3. Enforce case consistency
        """
        # Use dictionary keys to preserve order and remove duplicates
        return list({tag.strip().lower(): None for tag in tags if tag.strip()}.keys())


class EntryMetadata(EntryMetadataInput):
    name: str
    version: str


def check_file_exists(key):
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


@v1_router.post("/upload_file")
async def upload_file(
    entry_location: EntryLocation = Depends(with_write_access(use_forms=True)),
    path: str = Form(...),
    file: UploadFile = File(...),
):
    entry = get(entry_location)
    key = entry.get_key(path)

    if check_file_exists(key):
        raise HTTPException(status_code=400, detail=f"File {key} already exists.")

    assert isinstance(S3_BUCKET, str)
    s3.upload_fileobj(file.file, S3_BUCKET, key)

    return {"status": "File uploaded", "path": key}


@v1_router.post("/download_file")
def download_file(
    entry: RegistryEntry = Depends(get_read_access),
    path: str = Body(),
):
    return StreamingResponse(download_file_inner(entry, path).iter_chunks())


def download_file_inner(
    entry: RegistryEntry,
    path: str = Body(),
):
    source = entry.details.get("_source")

    if source is None:
        # Default source, which is S3
        assert isinstance(S3_BUCKET, str)
        bucket = S3_BUCKET
        key = entry.get_key(path)
    elif source["origin"] == "s3":
        bucket = source["bucket"]
        key = source["key"]
        key = key.strip("/") + "/" + path.strip("/")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

    # https://stackoverflow.com/a/71126498/4950797
    object = s3.get_object(Bucket=bucket, Key=key)
    return object["Body"]


@v1_router.post("/upload_metadata")
async def upload_metadata(registry_entry_id: int = Depends(get_or_create), metadata: EntryMetadataInput = Body()):
    with get_session() as session:
        entry = session.get(RegistryEntry, registry_entry_id)
        assert entry is not None

        full_metadata = EntryMetadata(name=entry.name, version=entry.version, **metadata.model_dump())

        entry.category = full_metadata.category
        entry.description = full_metadata.description
        entry.details = full_metadata.details
        entry.show_entry = full_metadata.show_entry

        session.add(entry)

        # Delete all previous tags
        # Ignore type check since delete is not supported as a valid statement.
        # https://github.com/tiangolo/sqlmodel/issues/909
        session.exec(delete(Tags).where(Tags.registry_id == entry.id))  # type: ignore

        # Add the new tags
        if len(full_metadata.tags) > 0:
            tags = [Tags(registry_id=entry.id, tag=tag) for tag in full_metadata.tags]
            session.add_all(tags)

        session.commit()

        return {"status": "Updated metadata", "namespace": entry.namespace, "metadata": full_metadata.model_dump()}


@v1_router.post("/download_metadata")
def download_metadata(entry: RegistryEntry = Depends(get_read_access)) -> EntryMetadata:
    return download_metadata_inner(entry)


def download_metadata_inner(entry: RegistryEntry) -> EntryMetadata:
    with get_session() as session:
        q_tags = select(Tags).where(Tags.registry_id == entry.id)
        tags = [tag.tag for tag in session.exec(q_tags).all()]

    return EntryMetadata(
        name=entry.name,
        version=entry.version,
        category=entry.category,
        description=entry.description,
        tags=tags,
        details=entry.details,
        show_entry=entry.show_entry,
    )


class Filename(BaseModel):
    filename: str


@v1_router.post("/list_files")
def list_files(entry: RegistryEntry = Depends(get_read_access)) -> List[Filename]:
    """Lists all files that belong to an entry."""
    logger.info(f"Listing files for entry: {entry}")
    return list_files_inner(entry)


def list_files_inner(entry: RegistryEntry) -> List[Filename]:
    """Lists all files that belong to an entry."""
    source = entry.details.get("_source")

    if source is None:
        # Default source, which is S3
        assert isinstance(S3_BUCKET, str)
        bucket = S3_BUCKET
        key = entry.get_key()
    elif source["origin"] == "s3":
        bucket = source["bucket"]
        key = source["key"]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

    key = key.strip("/") + "/"
    logger.info(f"Listing files for bucket: {bucket}, key: {key}")
    objects = s3.list_objects(Bucket=bucket, Prefix=key)
    files = [Filename(filename=obj["Key"][len(key) :]) for obj in objects.get("Contents", [])]
    return files


class ForkOf(BaseModel):
    namespace: str
    name: str


class EntryInformation(BaseModel):
    id: int
    namespace: str
    name: str
    version: str
    updated: datetime.datetime
    category: str
    description: str
    details: Dict[str, Any]
    tags: List[str]
    num_forks: int
    num_stars: int
    starred_by_point_of_view: bool
    fork_of: Optional[ForkOf]


@v1_router.post("/list_entries")
def list_entries(
    namespace: str = "",
    category: str = "",
    tags: str = "",
    total: int = 32,
    offset: int = 0,
    show_hidden: bool = False,
    show_latest_version: bool = True,
    starred_by: str = "",
    star_point_of_view: str = "",
    fork_of_name: str = "",
    fork_of_namespace: str = "",
) -> List[EntryInformation]:
    return list_entries_inner(
        namespace=namespace,
        category=category,
        tags=tags,
        total=total,
        offset=offset,
        show_hidden=show_hidden,
        show_latest_version=show_latest_version,
        starred_by=starred_by,
        star_point_of_view=star_point_of_view,
        fork_of_name=fork_of_name,
        fork_of_namespace=fork_of_namespace,
    )


def list_entries_inner(
    namespace: str = "",
    category: str = "",
    tags: str = "",
    custom_where: str = "",
    total: int = 32,
    offset: int = 0,
    show_hidden: bool = False,
    show_latest_version: bool = True,
    starred_by: str = "",
    star_point_of_view: str = "",
    fork_of_name: str = "",
    fork_of_namespace: str = "",
) -> List[EntryInformation]:
    tags_list = list({tag for tag in tags.split(",") if tag})

    bind_params: Dict[str, Any] = {
        "show_entry": 1 - int(show_hidden),
    }

    if category:
        category = valid_tag(category)
        category_condition = "AND category = :category"
        bind_params["category"] = category
    else:
        category_condition = ""

    if namespace:
        namespace = valid_identifier(namespace)
        namespace_condition = "AND registry.namespace = :namespace"
        bind_params["namespace"] = namespace
    else:
        namespace_condition = ""

    if fork_of_name and fork_of_namespace:
        fork_of_namespace = valid_identifier(fork_of_namespace)
        fork_of_condition = "AND fork_from_namespace = :fork_of_namespace AND fork_from_name = :fork_of_name"
        bind_params["fork_of_name"] = fork_of_name
        bind_params["fork_of_namespace"] = fork_of_namespace
    else:
        fork_of_condition = ""

    latest_version_condition = (
        """JOIN (SELECT MAX(id) as id FROM registry_entry GROUP BY namespace, name) last_entry
             ON last_entry.id = registry.id"""
        if show_latest_version
        else ""
    )

    # TODO add extra protection to avoid SQL INJECTION?
    custom_where_condition = f" AND ({custom_where})" if custom_where else ""

    bind_params["star_point_of_view"] = star_point_of_view
    bind_params["starred_by"] = starred_by

    if starred_by:
        starred_by_condition = "AND CountedStars.starred_by_target = 1"
    else:
        starred_by_condition = ""

    with get_session() as session:
        entries_info: List[EntryInformation] = []

        if len(tags_list) == 0:
            query_text = f"""WITH
            CountedStars AS (
                SELECT namespace, name, COUNT(account_id) as num_stars,
                CASE WHEN MAX(account_id = :star_point_of_view) THEN 1 ELSE 0 END as starred_by_pov,
                CASE WHEN MAX(account_id = :starred_by) THEN 1 ELSE 0 END as starred_by_target
                FROM stars
                GROUP BY namespace, name
            ),
            CountedForks AS (
                SELECT
                    category as counted_forks_category,
                    from_namespace as counted_forks_from_namespace,
                    from_name as counted_forks_from_name,
                    COUNT(to_namespace) as num_forks
                FROM forks
                GROUP BY counted_forks_category, counted_forks_from_namespace, counted_forks_from_name
            ),
            Fork AS (
                SELECT
                    category as fork_category,
                    from_namespace as fork_from_namespace,
                    from_name as fork_from_name,
                    to_namespace as fork_to_namespace,
                    to_name as fork_to_name
                FROM forks
            )
            SELECT
                registry.id, registry.namespace, registry.name, registry.version,
                registry.category, registry.description, registry.details, registry.time,
                CountedStars.num_stars, CountedStars.starred_by_pov, CountedForks.num_forks,
                Fork.fork_from_namespace, Fork.fork_from_name
            FROM registry_entry registry
            LEFT JOIN CountedStars
                ON registry.namespace = CountedStars.namespace AND registry.name = CountedStars.name
            LEFT JOIN CountedForks
                ON registry.category = CountedForks.counted_forks_category
                    AND registry.namespace = CountedForks.counted_forks_from_namespace
                    AND registry.name = CountedForks.counted_forks_from_name
            LEFT JOIN Fork
                ON registry.category = Fork.fork_category
                    AND registry.namespace = Fork.fork_to_namespace
                    AND registry.name = Fork.fork_to_name
            {latest_version_condition}
            WHERE show_entry >= :show_entry
                {category_condition}
                {namespace_condition}
                {starred_by_condition}
                {fork_of_condition}
                {custom_where_condition}
            ORDER BY registry.id DESC
            LIMIT :total
            OFFSET :offset
            """

            bind_params["total"] = total
            bind_params["offset"] = offset

        else:
            tags_list = [valid_tag(tag) for tag in tags_list]

            query_text = f"""WITH
                    CountedStars AS (
                        SELECT namespace, name, COUNT(account_id) as num_stars,
                        CASE WHEN MAX(account_id = :star_point_of_view) THEN 1 ELSE 0 END as starred_by_pov,
                        CASE WHEN MAX(account_id = :starred_by) THEN 1 ELSE 0 END as starred_by_target
                        FROM stars
                        GROUP BY namespace, name
                    ),
                    CountedForks AS (
                        SELECT
                            category as counted_forks_category,
                            from_namespace as counted_forks_from_namespace,
                            from_name as counted_forks_from_name,
                            COUNT(to_namespace) as num_forks
                        FROM forks
                        GROUP BY counted_forks_category, counted_forks_from_namespace, counted_forks_from_name
                    ),
                    Fork AS (
                        SELECT
                            category as fork_category,
                            from_namespace as fork_from_namespace,
                            from_name as fork_from_name,
                            to_namespace as fork_to_namespace,
                            to_name as fork_to_name
                        FROM forks
                    ),
                    FilteredRegistry AS (
                        SELECT
                            registry.id, CountedStars.num_stars, CountedStars.starred_by_pov,
                            CountedForks.num_forks, Fork.fork_from_namespace, Fork.fork_from_name
                        FROM registry_entry registry
                        {latest_version_condition}
                        JOIN entry_tags ON registry.id = entry_tags.registry_id
                        LEFT JOIN CountedStars
                            ON registry.namespace = CountedStars.namespace
                            AND registry.name = CountedStars.name
                        LEFT JOIN CountedForks
                            ON registry.category = CountedForks.counted_forks_category
                                AND registry.namespace = CountedForks.counted_forks_from_namespace
                                AND registry.name = CountedForks.counted_forks_from_name
                        LEFT JOIN Fork
                            ON registry.category = Fork.fork_category
                                AND registry.namespace = Fork.fork_to_namespace
                                AND registry.name = Fork.fork_to_name
                        WHERE show_entry >= :show_entry
                            AND entry_tags.tag IN :tags
                            {category_condition}
                            {namespace_condition}
                            {starred_by_condition}
                            {fork_of_condition}
                            {custom_where_condition}
                        GROUP BY registry.id
                        HAVING COUNT(DISTINCT entry_tags.tag) = :ntags
                    ),
                    RankedRegistry AS (
                        SELECT
                            id, num_stars, starred_by_pov, num_forks, fork_from_namespace, fork_from_name,
                            ROW_NUMBER() OVER (ORDER BY id DESC) AS col_rank
                        FROM FilteredRegistry
                    )

                    SELECT registry.id, registry.namespace, registry.name, registry.version,
                           registry.category, registry.description, registry.details, registry.time,
                           ranked.num_stars, ranked.starred_by_pov, num_forks, fork_from_namespace,
                           fork_from_name
                    FROM RankedRegistry ranked
                    JOIN registry_entry registry ON ranked.id = registry.id
                    WHERE   ranked.col_rank >= :lower_bound AND
                            ranked.col_rank < :upper_bound
                    ORDER BY registry.id DESC
                """

            bind_params["lower_bound"] = offset + 1
            bind_params["upper_bound"] = offset + total + 1
            bind_params["tags"] = tags_list
            bind_params["ntags"] = len(tags_list)

        for (
            id,
            namespace_,
            name,
            version,
            category_,
            description,
            details,
            timestamp,
            num_stars,
            pov,
            num_forks,
            fork_from_namespace,
            fork_from_name,
        ) in session.exec(text(query_text).bindparams(**bind_params)).all():  # type: ignore
            fork_of = None

            if fork_from_namespace and fork_from_name:
                fork_of = ForkOf(namespace=fork_from_namespace, name=fork_from_name)

            entries_info.append(
                EntryInformation(
                    id=id,
                    namespace=namespace_,
                    name=name,
                    version=version,
                    updated=timestamp.replace(tzinfo=datetime.timezone.utc),
                    category=category_,
                    description=description,
                    details=json.loads(details),
                    tags=[],
                    num_forks=num_forks or 0,
                    num_stars=num_stars or 0,
                    starred_by_point_of_view=bool(pov),
                    fork_of=fork_of,
                )
            )

        # Get the tags of all entries
        ids = [entry.id for entry in entries_info]

        q_tags = select(Tags).where(Tags.registry_id.in_(ids))  # type: ignore
        q_tags_r = session.exec(q_tags).all()

        q_tags_dict: Dict[int, List[str]] = defaultdict(list)
        for tag in q_tags_r:
            q_tags_dict[tag.registry_id].append(tag.tag)

        for entry in entries_info:
            entry.tags = q_tags_dict[entry.id]

        entries_info.sort(key=lambda x: x.id, reverse=True)

        return entries_info


class ForkEntryModifications(BaseModel):
    name: str
    description: str
    version: str


class ForkResult(BaseModel):
    status: str
    entry: EntryLocation


@v1_router.post("/fork")
def fork_entry(
    modifications: ForkEntryModifications = Body(),
    entry: RegistryEntry = Depends(get_read_access),
    auth: AuthToken = Depends(get_auth),
) -> ForkResult:
    """Fork an existing registry entry to the current user's namespace."""
    with get_session() as session:
        new_entry = RegistryEntry(
            namespace=auth.account_id,
            name=modifications.name,
            version=modifications.version,
            category=entry.category,
            description=modifications.description,
            details=entry.details,
            show_entry=True,
        )

        # Remove X (Twitter) event triggers from the forked entry's details
        if "triggers" in new_entry.details:
            triggers = new_entry.details["triggers"]
            if "events" in triggers:
                events = triggers["events"]
                if "x_mentions" in events:
                    del events["x_mentions"]
                # Optional: Remove the events object if empty after deletion
                if not events:
                    del triggers["events"]
            # Optional: Remove the triggers object if empty after deletions
            if not triggers:
                del new_entry.details["triggers"]

        new_entry_collision_check = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.category == new_entry.category,
                RegistryEntry.namespace == new_entry.namespace,
                RegistryEntry.name == new_entry.name,
            )
        ).first()

        if new_entry_collision_check is not None:
            logger.debug(f"Fork request collides with existing entry: {new_entry_collision_check}")
            raise HTTPException(
                status_code=409, detail="Fork request collides with existing entry. Choose a different name."
            )

        session.add(new_entry)

        session.add(
            Fork(
                category=entry.category,
                from_namespace=entry.namespace,
                from_name=entry.name,
                to_namespace=new_entry.namespace,
                to_name=new_entry.name,
            )
        )

        session.commit()

        files = list_files_inner(entry)
        assert isinstance(S3_BUCKET, str)
        bucket = S3_BUCKET

        for file in files:
            key = entry.get_key(file.filename)
            new_key = new_entry.get_key(file.filename)
            s3.copy_object(Bucket=bucket, Key=new_key, CopySource={"Bucket": bucket, "Key": key})

        result = ForkResult(
            status="Entry forked and uploaded",
            entry=EntryLocation(name=new_entry.name, namespace=new_entry.namespace, version=new_entry.version),
        )

        return result
