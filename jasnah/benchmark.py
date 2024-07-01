import concurrent.futures
from dataclasses import dataclass
from itertools import islice
from typing import Optional, Union

from datasets import Dataset, DatasetDict
from tqdm import tqdm

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
    def __init__(self, dataset_info: DatasetInfo, solver_strategy: SolverStrategy):
        self.dataset_info = dataset_info
        self.solver_strategy = solver_strategy

    def run(self, progress: bool = True, max_concurrent: int = 32) -> None:
        dataset = self.dataset_info.get_dataset()

        correct = 0
        remaining = len(dataset)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            tasks = iter(executor.submit(self.solver_strategy.solve, datum=datum) for datum in dataset)
            total = len(dataset)
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
