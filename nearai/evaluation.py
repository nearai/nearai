import json
import re
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, List, Union

from datasets import Dataset  # type: ignore[attr-defined]
from tabulate import tabulate

from nearai.openapi_client.api.benchmark_api import BenchmarkApi
from nearai.registry import get_registry_folder, registry
from nearai.solvers import SolverStrategy

EVALUATED_ENTRY_METADATA = "evaluated_entry_metadata"


def load_benchmark_entry_info(info: str) -> Any:
    """Deserializes benchmark info entry from db data."""
    first_decode = json.loads(info)
    try:
        second_decode = json.loads(first_decode)
        return second_decode
    except json.JSONDecodeError as e:
        if "Unterminated string" in str(e):
            last_brace = first_decode.rfind("}")
            if last_brace != -1:
                try:
                    return json.loads(first_decode[: last_brace + 1])
                except json.JSONDecodeError as e:
                    pass
    return first_decode


def record_single_score_evaluation(
    solver_strategy: SolverStrategy, benchmark_id: int, data_tasks: Union[Dataset, List[dict]], score: float
) -> None:
    """Uploads single score evaluation into registry."""
    evaluation_name = solver_strategy.evaluation_name()
    record_evaluation_metrics(solver_strategy, benchmark_id, data_tasks, {evaluation_name: score}, False)


def _prepend_name_to_metrics(evaluation_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {f"{evaluation_name}/{key}": value for key, value in metrics.items()}


def record_evaluation_metrics(
    solver_strategy: SolverStrategy,
    benchmark_id: int,
    data_tasks: Union[Dataset, List[dict]],
    metrics: Dict[str, Any],
    prepend_evaluation_name: bool = True,
) -> None:
    """Uploads evaluation metrics into registry."""
    evaluation_name = solver_strategy.evaluation_name()
    model = ""
    agent = ""
    version = ""
    model = solver_strategy.model_name
    agent = solver_strategy.agent_name()
    version = solver_strategy.agent_version()

    upload_evaluation(
        evaluation_name,
        benchmark_id,
        data_tasks,
        metrics if not prepend_evaluation_name else _prepend_name_to_metrics(evaluation_name, metrics),
        model,
        agent,
        solver_strategy.evaluated_entry_namespace(),
        version,
        solver_strategy.model_provider(),
    )


def upload_evaluation(
    evaluation_name: str,
    benchmark_id: int,
    data_tasks: Union[Dataset, List[dict]],
    metrics: Dict[str, Any],
    model: str = "",
    agent: str = "",
    namespace: str = "",
    version: str = "",
    provider: str = "",
) -> None:
    """Uploads evaluation into registry.

    `evaluation_name`: a unique name for (benchmark, solver) tuple, e.g. "mbpp" or "live_bench" or "mmlu-5-shot".
    `metrics`: metrics from evaluation.
    `model`: model that was used.
    `agent`: agent that was evaluated, in any.
    `namespace`: namespace of evaluated agent or evaluated model.
    `version`: version of evaluated agent or evaluated model.
    `provider`: provider of model used; pass `local` if running locally.
    """
    key = f"evaluation_{evaluation_name}"
    metrics[EVALUATED_ENTRY_METADATA] = {}
    if agent != "":
        metrics[EVALUATED_ENTRY_METADATA]["agent"] = agent
        key += f"_agent_{agent}"
    if model != "":
        metrics[EVALUATED_ENTRY_METADATA]["model"] = model
        key += f"_model_{model}"
    if namespace != "":
        metrics[EVALUATED_ENTRY_METADATA]["namespace"] = namespace
        key += f"_namespace_{namespace}"
    if version != "":
        metrics[EVALUATED_ENTRY_METADATA]["version"] = version
        key += f"_version_{version}"
    if provider != "":
        metrics[EVALUATED_ENTRY_METADATA]["provider"] = provider
        # Url providers like 'https://api.openai.com/v1' can't be included into registry entry name
        # because of special characters.
        clean_provider = re.sub(r"[^a-zA-Z0-9_\-.]", "_", provider)
        key += f"_provider_{clean_provider}"

    entry_path = get_registry_folder() / key
    # Create folder entry_path if not present
    entry_path.mkdir(parents=True, exist_ok=True)
    # Write file metrics.json inside
    metrics_file = entry_path / "metrics.json"
    with metrics_file.open("w") as f:
        json.dump(metrics, f, indent=2)

    # Get solutions from cache in benchmark.py
    cache = BenchmarkApi().get_benchmark_result_v1_benchmark_get_result_get(benchmark_id)
    solutions = []
    for result in cache:
        try:
            solution = {
                "datum": data_tasks[result.index],
                "status": result.solved,
                "info": load_benchmark_entry_info(result.info) if result.info else {},
            }
            solutions.append(solution)
        except (AttributeError, json.JSONDecodeError, TypeError) as e:
            print(f"Exception while creating solutions data: {str(e)}.")
            # Skip entries that can't be properly formatted
            continue

    # Write solutions file
    solutions_file = entry_path / "solutions.json"
    with solutions_file.open("w") as f:
        json.dump(solutions, f, indent=2)

    metadata_path = entry_path / "metadata.json"
    # TODO(#273): Currently that will not update existing evaluation.
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "name": key,
                "version": "0.1.0",
                "description": "",
                "category": "evaluation",
                "tags": [],
                "details": {},
                "show_entry": True,
            },
            f,
            indent=2,
        )

    registry.upload(Path(entry_path), show_progress=True)


def print_evaluation_table(
    rows: List[Dict[str, str]],
    columns: List[str],
    important_columns: List[str],
    all_key_columns: bool,
    all_metrics: bool,
    num_columns: int,
    metric_name_max_length: int,
) -> None:
    """Prints table of evaluations."""
    metric_names = columns[5:] if all_metrics else important_columns[2:]
    _print_metrics_tables(rows, metric_names, num_columns, all_key_columns, metric_name_max_length)


def _shorten_metric_name(name: str, max_length: int) -> str:
    """Shortens metric name if needed."""
    if len(name) <= max_length:
        return name
    keep = max_length - 2  # 2 dots
    beginning = keep // 3
    ending = keep - beginning
    return name[:beginning] + ".." + name[-ending:]


def _print_metrics_tables(
    rows: List[Dict[str, str]],
    metric_names: List[str],
    num_columns: int,
    all_key_columns: bool,
    metric_name_max_length: int,
):
    """Builds table(s) and prints them."""
    # Shorten metric names
    short_metric_names = [_shorten_metric_name(name, metric_name_max_length) for name in metric_names]

    # Prepare the base header and rows
    base_header = ["model", "agent"]
    if all_key_columns:
        base_header.extend(["namespace", "version", "provider"])

    base_rows = []
    for row in rows:
        base_row = [fill(row.pop("model", "")), fill(row.pop("agent", ""))]
        namespace = row.pop("namespace", "")
        version = row.pop("version", "")
        provider = row.pop("provider", "")
        if all_key_columns:
            base_row.extend([fill(namespace), fill(version), fill(provider)])
        base_rows.append((base_row, row))

    n_metrics_per_table = max(1, num_columns - len(base_header))
    # Split metrics into groups
    metric_groups = list(
        zip(
            [
                short_metric_names[i : i + n_metrics_per_table]
                for i in range(0, len(short_metric_names), n_metrics_per_table)
            ],
            [metric_names[i : i + n_metrics_per_table] for i in range(0, len(metric_names), n_metrics_per_table)],
        )
    )

    # Print tables
    for short_group, full_group in metric_groups:
        header = base_header + short_group
        table = []
        for base_row, row_metrics in base_rows:
            table_row = base_row + [fill(str(row_metrics.get(metric, ""))) for metric in full_group]
            table.append(table_row)
        print(tabulate(table, headers=header, tablefmt="simple_grid"))
