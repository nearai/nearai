import base64
import logging
import mimetypes
import os
import time
from typing import Dict, Optional

import chardet
import requests
from dotenv import load_dotenv
from nearai.shared.models import GitHubSource

from hub.api.v1.files import upload_file_to_storage
from hub.api.v1.sql import SqlClient
from hub.tasks.embedding_generation import generate_embeddings_for_file

"""
This module handles the import of files from GitHub repositories into the vector store.

It provides functionality to fetch repository contents, read file contents,
create file records, and process GitHub sources for vector stores.
"""

logger = logging.getLogger(__name__)

load_dotenv()

BASE_URL = "https://api.github.com/repos"
RATE_LIMIT_WAIT = 60
MAX_CONTENT_LENGTH = 1024 * 1024  # 1 MB

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def handle_rate_limit(func):
    """Decorator to handle GitHub API rate limiting.

    If a rate limit is encountered, the function will wait and retry.

    Args:
    ----
        func: The function to be decorated.

    Returns:
    -------
        A wrapper function that handles rate limiting.

    """

    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code == 403:
            logger.warning(f"Rate limit exceeded. Waiting for {RATE_LIMIT_WAIT} seconds...")
            time.sleep(RATE_LIMIT_WAIT)
            return wrapper(*args, **kwargs)
        return response

    return wrapper


@handle_rate_limit
def github_get(url: str, source_auth: Optional[str] = None) -> requests.Response:
    """Make a GET request to the GitHub API.

    Args:
    ----
        url (str): The GitHub API endpoint URL.
        source_auth (Optional[str]): Optional authentication token.

    Returns:
    -------
        requests.Response: The response from the GitHub API.

    Raises:
    ------
        ValueError: If no GitHub token is provided.

    """
    headers = HEADERS.copy()
    if not source_auth and not GITHUB_TOKEN:
        raise ValueError("GitHub token is required")
    if source_auth:
        headers["Authorization"] = f"token {source_auth}"
    return requests.get(url, headers=headers)


def get_repo_contents(owner: str, repo: str, branch: str = "main", caller_auth: Optional[str] = None) -> Optional[Dict]:
    """Fetch the contents of a GitHub repository.

    Args:
    ----
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        branch (str): The branch to fetch (default is "main").
        caller_auth (Optional[str]): Optional caller authentication token.

    Returns:
    -------
        Optional[Dict]: A dictionary containing the repository contents, or None if the request fails.

    """
    url = f"{BASE_URL}/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = github_get(url, caller_auth)
    if response.status_code == 200:
        return response.json()
    logger.error(f"Error fetching contents: {response.status_code}")
    return None


def read_file_content(blob_url: str) -> Optional[str]:
    """Read the content of a file from a GitHub blob URL.

    Args:
    ----
        blob_url (str): The GitHub blob URL of the file.

    Returns:
    -------
        Optional[str]: The content of the file as a string, or None if the request fails or the file is too large.

    """
    response = github_get(blob_url)
    if response.status_code == 200:
        content = base64.b64decode(response.json()["content"])
        if len(content) > MAX_CONTENT_LENGTH:
            logger.warning("File too large, skipping content.")
            return None

        detected = chardet.detect(content)
        encoding = detected["encoding"] if detected and detected["encoding"] else "utf-8"

        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            logger.error(f"Unable to decode content for {blob_url} with {encoding}")
            return None
    logger.error(f"Error fetching file content: {response.status_code}")
    return None


async def create_file_from_content(account_id: str, filename: str, content: str, purpose: str) -> Optional[str]:
    """Create a file record from content and upload it to storage.

    Args:
    ----
        account_id (str): The account ID of the user.
        filename (str): The name of the file.
        content (str): The content of the file.
        purpose (str): The purpose of the file.

    Returns:
    -------
        Optional[str]: The file ID if successful, None otherwise.

    """
    content_bytes = content.encode("utf-8")
    file_size = len(content_bytes)
    content_type = mimetypes.guess_type(filename)[0] or "text/plain"

    safe_filename = os.path.basename(filename)
    object_key = f"vector-store-files/{account_id}/{safe_filename}"
    try:
        file_uri = await upload_file_to_storage(content_bytes, object_key)
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {str(e)}")
        return None

    sql_client = SqlClient()
    try:
        file_id = sql_client.create_file(
            account_id=account_id,
            file_uri=file_uri,
            purpose=purpose,
            filename=safe_filename,
            content_type=content_type,
            file_size=file_size,
            encoding="utf-8",
        )
        return file_id
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        return None


async def process_github_source(
    source: GitHubSource, vector_store_id: str, account_id: str, source_auth: Optional[str] = None
):
    """Process files from a GitHub source and add them to the vector store.

    Args:
    ----
        source (GitHubSource): The GitHub source details.
        vector_store_id (str): The ID of the vector store to add files to.
        account_id (str): The account ID of the user.
        source_auth (Optional[str]): The caller's authentication token for the source.
            If available, a default token from the environment will be used as a fallback.

    """
    logger.info(f"Processing GitHub source for vector store: {vector_store_id}")
    sql_client = SqlClient()

    repo_contents = get_repo_contents(source.owner, source.repo, source.branch, source_auth)
    if repo_contents is None or "tree" not in repo_contents:
        logger.error(f"Failed to fetch repository contents for {source.owner}/{source.repo}")
        return

    for item in repo_contents["tree"]:
        if item["type"] != "blob":
            continue

        content = read_file_content(item["url"])
        if content is None:
            continue

        file_id = await create_file_from_content(account_id, item["path"], content, "assistants")
        if not file_id:
            continue

        vector_store = sql_client.get_vector_store(vector_store_id)
        if not vector_store:
            logger.error(f"Vector store {vector_store_id} not found")
            continue

        sql_client.update_files_in_vector_store(
            vector_store_id=vector_store_id,
            file_ids=vector_store.file_ids + [file_id],
            account_id=account_id,
        )
        await generate_embeddings_for_file(file_id, vector_store_id, vector_store.chunking_strategy)

    logger.info(f"Completed processing GitHub source for vector store: {vector_store_id}")
