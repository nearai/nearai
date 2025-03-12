import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from dotenv import load_dotenv
from fastapi import APIRouter
from nearai.evaluation import EVALUATED_ENTRY_METADATA
from nearai.registry import get_registry_folder
from pydantic import BaseModel

from hub.api.v1.entry_location import EntryLocation
from hub.api.v1.registry import download_file_inner, download_metadata_inner, get, list_entries_inner, list_files_inner

load_dotenv()

v1_router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
)


def _is_important_metric(metric_name, metrics) -> bool:
    """Simple heuristics to determine if the metric is important."""
    if len(metrics) == 2:
        # One score and metadata. Do not include lean benchmarks.
        return "lean" not in metric_name
    return "coding" in metric_name or "average" in metric_name or "avg" in metric_name


class EvaluationTable(BaseModel):
    rows: List[Dict[str, str]]
    columns: List[str]
    important_columns: List[str]


@v1_router.get("/table")
async def table() -> EvaluationTable:
    rows, columns, important_columns = evaluation_table()
    list_rows = [
        {**dict(key_tuple), **{m: metrics[m] for m in columns if metrics.get(m)}} for key_tuple, metrics in rows.items()
    ]
    return EvaluationTable(rows=list_rows, columns=columns, important_columns=important_columns)


def evaluation_table() -> Tuple[Dict[tuple[tuple[str, Any], ...], Dict[str, str]], List[str], List[str]]:
    """Returns rows, columns, and important columns."""
    entries = list_entries_inner(
        namespace="",
        category="evaluation",
        tags="",
        total=10000,
        offset=0,
        show_hidden=False,
        show_latest_version=True,
    )
    rows: Dict[tuple[tuple[str, Any], ...], Dict[str, str]] = {}
    metric_names: Set[str] = set()
    important_metric_names: Set[str] = set()
    for entry in entries:
        evaluation_path = download_evaluation(
            EntryLocation(
                namespace=entry.namespace,
                name=entry.name,
                version=entry.version,
            )
        )
        metrics_path = evaluation_path / "metrics.json"
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            key = {
                "model": metrics[EVALUATED_ENTRY_METADATA].get("model", ""),
                "agent": metrics[EVALUATED_ENTRY_METADATA].get("agent", ""),
                "namespace": metrics[EVALUATED_ENTRY_METADATA].get("namespace", ""),
                "version": metrics[EVALUATED_ENTRY_METADATA].get("version", ""),
                "provider": metrics[EVALUATED_ENTRY_METADATA].get("provider", ""),
            }

            # Convert the key dictionary to a tuple to use as a key in rows
            key_tuple = tuple(key.items())

            # Initialize the inner dictionary if this key doesn't exist
            if key_tuple not in rows:
                rows[key_tuple] = {}

            # Add all other metrics that are not EVALUATED_ENTRY_METADATA
            for metric_name, metric_value in metrics.items():
                if metric_name == EVALUATED_ENTRY_METADATA:
                    continue
                if _is_important_metric(metric_name, metrics):
                    important_metric_names.add(metric_name)
                rows[key_tuple][metric_name] = str(metric_value)
                metric_names.add(metric_name)

    sorted_metric_names = sorted(metric_names)
    columns = ["model", "agent", "namespace", "version", "provider"] + sorted_metric_names
    important_columns = ["model", "agent"] + sorted(important_metric_names)
    return rows, columns, important_columns


def download_evaluation(entry_location: EntryLocation) -> Path:
    """Downloads evaluation from the registry locally."""
    download_path = get_registry_folder() / entry_location.namespace / entry_location.name / entry_location.version

    entry = get(entry_location)

    metadata_path = download_path / "metadata.json"
    metadata = download_metadata_inner(entry)
    if metadata is None:
        raise ValueError(f"Entry {entry_location} not found.")
    if download_path.exists():
        with open(metadata_path, "r") as f:
            existing_metadata = json.load(f)
            if existing_metadata["version"] == metadata.version:
                return download_path
    download_path.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w") as f:
        f.write(metadata.model_dump_json(indent=2))

    files = [file.filename for file in list_files_inner(entry)]
    for file in files:
        local_path = download_path / file
        result = download_file_inner(entry, file)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in result.iter_chunks():
                f.write(chunk)

    return download_path
