import concurrent.futures
import json
from dataclasses import dataclass
from functools import partial
from itertools import islice
from typing import Any, Callable, Dict, Optional, Tuple, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from tqdm import tqdm

from nearai.evaluation import load_benchmark_entry_info, record_evaluation_metrics, record_single_score_evaluation
from nearai.openapi_client.api.benchmark_api import BenchmarkApi
from nearai.solvers import SolverScoringMethod, SolverStrategy


@dataclass
class DatasetInfo:
    name: str
    subset: Optional[str]
    dataset: Union[Dataset, DatasetDict]
    metadata: dict

    def get_dataset(self) -> Dataset:  # noqa: D102
        if isinstance(self.dataset, DatasetDict):
            if self.subset is None:
                print(
                    f"Please specify subset with a --subset flag. Available subsets: {', '.join(self.dataset.keys())}"
                )
                exit(1)
            return self.dataset[self.subset]
        elif isinstance(self.dataset, Dataset):
            return self.dataset
        else:
            raise ValueError(f"Expected a Dataset or DatasetDict, got {type(self.dataset)}")

    def get_dataset_evaluation_name(self) -> str:  # noqa: D102
        details = self.metadata["details"]
        if benchmark_metadata := details.get("benchmark", None):
            evaluation_name = benchmark_metadata.get("evaluation_name", "")
            if not evaluation_name:
                return ""
            if not self.subset:
                return evaluation_name
            evaluation_separator = benchmark_metadata.get("evaluation_separator", "_")
            return f"{evaluation_name}{evaluation_separator}{self.subset}"
        else:
            return ""


class BenchmarkExecutor:
    def __init__(  # noqa: D107
        self,
        dataset_info: DatasetInfo,
        solver_strategy: SolverStrategy,
        benchmark_id: int,
    ):
        self.dataset_info = dataset_info
        self.solver_strategy = solver_strategy
        self.benchmark_id = benchmark_id
        self.client = BenchmarkApi()
        self.solver_strategy.dataset_evaluation_name = self.dataset_info.get_dataset_evaluation_name()

    def run(self, progress: bool = True, max_concurrent: int = 32, record: bool = False) -> None:  # noqa: D102
        data_tasks = (
            self.dataset_info.get_dataset()
            if self.solver_strategy.scoring_method != SolverScoringMethod.Custom
            else self.solver_strategy.get_custom_tasks()
        )

        cache_ = self.client.get_benchmark_result_v1_benchmark_get_result_get(benchmark_id=self.benchmark_id)
        # Need to do json.loads twice to convert back to the same data returned by solvers.
        cache = {result.index: (result.solved, load_benchmark_entry_info(result.info)) for result in cache_}

        n_true_results = 0
        remaining = len(data_tasks)
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            task_ctor = partial(
                solve_task,
                benchmark_id=self.benchmark_id,
                cache=cache,
                solve_fn=self.solver_strategy.solve,
            )
            tasks = iter(executor.submit(task_ctor, index=index, datum=datum) for index, datum in enumerate(data_tasks))

            total = len(data_tasks)
            bar = tqdm(total=total, disable=not progress)
            futures = list(islice(tasks, max_concurrent))
            while futures:
                completed, ongoing_futures = concurrent.futures.wait(
                    futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                futures = list(ongoing_futures)
                for completed_future in completed:
                    bar.update(1)
                    remaining -= 1

                    result = completed_future.result()
                    results.append(result)
                    status, info = result
                    if status:
                        n_true_results += 1
                    if self.solver_strategy.scoring_method == SolverScoringMethod.TrueOrFalseList:
                        bar.set_description(
                            f"Correct/Seen - {n_true_results}/{total - remaining} - {n_true_results / (total - remaining):.2%}"  # noqa: E501
                        )
                    elif info != "":
                        bar.set_description(f"{info}")

                    try:
                        next_task = next(tasks)
                        futures.append(next_task)
                    except StopIteration:
                        continue
            bar.close()  # Ensure the progress bar is closed

        if self.solver_strategy.scoring_method == SolverScoringMethod.TrueOrFalseList:
            print(f"Final score: {n_true_results}/{total} - {n_true_results / total:.2%}")
            if record:
                record_single_score_evaluation(
                    self.solver_strategy, self.benchmark_id, data_tasks, round(n_true_results / total * 100, 2)
                )
        else:
            evaluation_metrics = self.solver_strategy.get_evaluation_metrics(results)
            print(evaluation_metrics)
            if record:
                record_evaluation_metrics(self.solver_strategy, self.benchmark_id, data_tasks, evaluation_metrics)


def solve_task(
    benchmark_id: int,
    cache: Dict[int, Tuple[bool, str]],
    solve_fn: Callable[[Any], Union[bool, Tuple[bool, Any]]],
    index: int,
    datum: Any,
) -> Tuple[bool, Any]:
    if index in cache:
        return cache[index]

    result = solve_fn(datum)
    status = False
    info = ""
    if isinstance(result, tuple):
        status, info = result
    else:
        status = result

    client = BenchmarkApi()
    client.add_benchmark_result_v1_benchmark_add_result_get(
        benchmark_id=benchmark_id,
        index=index,
        solved=status,
        info=json.dumps(info),
    )

    return (status, info)
