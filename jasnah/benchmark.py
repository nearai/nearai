import concurrent.futures
import json
from dataclasses import dataclass
from functools import partial
from itertools import islice
from typing import Any, Callable, Dict, Optional, Tuple, Union

from datasets import Dataset, DatasetDict
from tqdm import tqdm

from jasnah.db import db
from jasnah.solvers import SolverStrategy


@dataclass
class DatasetInfo:
    name: str
    subset: Optional[str]
    dataset: Union[Dataset, DatasetDict]

    def get_dataset(self) -> Dataset:
        if isinstance(self.dataset, DatasetDict):
            assert self.subset is not None, f"Subset must be: {', '.join(self.dataset.keys())}"
            return self.dataset[self.subset]
        elif isinstance(self.dataset, Dataset):
            return self.dataset
        else:
            raise ValueError(f"Expected a Dataset or DatasetDict, got {type(self.dataset)}")


class BenchmarkExecutor:
    def __init__(self, dataset_info: DatasetInfo, solver_strategy: SolverStrategy, benchmark_id: int):
        self.dataset_info = dataset_info
        self.solver_strategy = solver_strategy
        self.benchmark_id = benchmark_id

    def run(self, progress: bool = True, max_concurrent: int = 32) -> None:
        dataset = self.dataset_info.get_dataset()

        cache = db.get_benchmark_status(self.benchmark_id)

        correct = 0
        remaining = len(dataset)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            task_ctor = partial(solve_task, benchmark_id=self.benchmark_id, cache=cache, solve_fn=self.solver_strategy.solve)
            tasks = iter(executor.submit(task_ctor, index=index, datum=datum) for index, datum in enumerate(dataset))

            total = len(dataset)
            bar = tqdm(total=total, disable=not progress)
            futures = list(islice(tasks, max_concurrent))
            while futures:
                completed, ongoing_futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
                futures = list(ongoing_futures)
                for completed_future in completed:
                    bar.update(1)
                    remaining -= 1

                    result = completed_future.result()
                    if result:
                        correct += 1
                    bar.set_description(
                        f"Correct/Seen - {correct}/{total - remaining} - {correct/(total - remaining):.2%}"
                    )

                    try:
                        next_task = next(tasks)
                        futures.append(next_task)
                    except StopIteration:
                        continue

        print(f"Final score: {correct}/{total} - {correct/total:.2%}")


def solve_task(benchmark_id: int, cache: Dict[int, bool], solve_fn: Callable[[Any], Union[bool, Tuple[bool, Any]]], index: int, datum: Any):
    if index in cache:
        return cache[index]

    result = solve_fn(datum)
    info = ""

    if isinstance(result, tuple):
        result, info = result

    db.update_benchmark_result(benchmark_id, index, result, json.dumps(info))

    return result
