# Benchmarks and Evaluations

`Benchmarks` allow you to compare different agents and solvers on specific tasks, so you can determine which is the best fit for your needs.

`Evaluations` are the results of running benchmarks. They are stored in the registry and can be used to compare different agents and solvers.

## How is a benchmark implemented?

A benchmark is the combination of a dataset and a solver (more on this below). 

Once you have created a dataset and its solver, you can run the benchmark using the `benchmark` command.

For example, to run the `mpbb` benchmark on the `llama v3`, you can use:

```bash
nearai benchmark run mbpp MBPPSolverStrategy \
    --model llama-v3-70b-instruct \
    --subset=train \
    --max_concurrent=1
```

### Adding a benchmark dataset

`nearai` leverages [huggingface datasets](https://huggingface.co/docs/datasets/en/index) as the primitive when operating with datasets + benchmarks (see [`load_dataset`](../api.md#nearai.dataset.load_dataset)). This means that to add a new benchmark, you need to create a new dataset and register it with the `nearai` registry (we will go over this in [Implementing the "3 digit addition" benchmark](#implementing-the-3-digit-addition-benchmark)).

There is also a support for datasets of custom format.

### Adding a solver

To implement a solver, you will need to implement the [SolverStrategy](../api.md#nearai.solvers.SolverStrategy) interface under the [`nearai.solvers`](../api.md#nearai.solvers) module. The most important method the solver should implement is the [`solve`](../api.md#nearai.solvers.SolverStrategy.solve) method. This method should take a datum, run your implementation specific agentic strategy / strategies, and return a result.

## Implementing the "3 digit addition" benchmark

In this section we will be implementing a benchmark we'll call "3 digit addition". The goal of the benchmark is to test an agents ability to add two 1-3 digit numbers together. The dataset will consist of 1000 examples of 3 digit addition problems and their solutions. The solver will adjudicate the agent answers and return a single accuracy score. While this benchmark is simple and can be solved with a simple program, it serves as a good example of how to implement a benchmark in `nearai`.

### Step 1: Creating the dataset

To create this dataset, we will first synthetically generate the data. We will then register the dataset with the `nearai` registry.

```python
import random
from itertools import product

import datasets

SAMPLE_SIZE = 1000
SEED = 42
PATH = "3_digit_addition"

random.seed(SEED)
datasets.Dataset.from_generator(
    lambda: iter(
        {
            "input": f"{a} + {b}",
            "output": str(a + b)
        }
        for a, b in random.sample(list(product(range(1000), range(1000))), SAMPLE_SIZE)
    ),
    features=datasets.Features(
        {
            "input": datasets.Value("string"),
            "output": datasets.Value("string")
        }
    )
).save_to_disk(PATH)
```

Now to upload the dataset to the registry we'll run the command:

```bash
nearai registry upload ./3_digit_addition
```

### Step 2: Creating the solver

To create the solver, we will implement the `SolverStrategy` interface. The solver will take in a datum, parse the input, execute any setup for the agent, run the agent, and return the correctness of the agents result.

???+ note "Remember"
    To ensure this solver is registered with `nearai`:
    
    1. Write this implementation in the [`nearai.solvers`](../api.md#nearai.solvers) module.
    2. Import it in the `__init__.py` file in the [`nearai.solvers`](../api.md#nearai.solvers) module.

```python
# ... other imports ...
from pydantic import BaseModel
from huggingface import Dataset
from nearai.solvers import SolverStrategy

from typing import Dict, List

class ThreeDigitAdditionDatum(BaseModel):
    input: str
    output: str

class ThreeDigitAdditionSolver(SolverStrategy):
    """Solver for the 3 digit addition benchmark."""

    def __init__(self, dataset_ref: Dataset, model: str = "", agent: str = ""):
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref

    def evaluation_name(self) -> str:
        return "3_digit_addition"

    def compatible_datasets(self) -> List[str]:
        return ["3_digit_addition"]

    def solve(self, datum: Dict[str, str]) -> bool:
        datum = ThreeDigitAdditionDatum(**datum)
        label = datum.input.replace(" + ", "+")
        session = self.start_inference_session(label)
        
        goal = f"""Please add the following numbers together: {datum.input}\n\nOutput the result only."""
        result = session.run_task(goal).strip()
        return result == datum.output
```

The code above can run for both models and agents. If both `model` and `agent` are given, the `model` value will be inserted into `agent` metadata.

To check agent functionality to write files:
```python
    def solve(self, datum: Dict[str, str]) -> bool:
        datum = ThreeDigitAdditionDatum(**datum)
        label = datum.input.replace(" + ", "+")
        session = self.start_inference_session(label)
        
        goal = f"""Please add the following numbers together: {datum.input}\n\nOutput the result in a file called 'result.txt'."""
        session.run_task(goal)
        with open(os.path.join(session.path, "result.txt"), "r") as f:
            result = f.read().strip()
        return result == datum.output
```

### Step 3: Running the benchmark

To run the benchmark, we will use the `nearai` CLI. We will specify the dataset and solver we want to use.

```bash
nearai benchmark run near.ai/3_digit_addition/1.00 ThreeDigitAdditionSolver --agent ~/.nearai/registry/<my_agent>
```

# Benchmarks Cache

Benchmark individual tasks and completion are cached in registry or locally. To see registry benchmark completion caches:

```bash
nearai benchmark list
```

To force execution and overwrite cache pass `--force` flag.

```bash
nearai benchmark run near.ai/mbpp/1.0.0 MBPPSolverStrategy --model 'llama-3p2-1b-instruct' --subset test --force
```

# Example runs
```bash
$ nearai benchmark run near.ai/mbpp/1.0.0 MBPPSolverStrategy --model 'llama-3p2-1b-instruct' --subset test
$ nearai benchmark run near.ai/mmlu/1.0.0 MMLUSolverStrategy --model 'llama-v3p1-405b-instruct' --subset test
$ nearai benchmark run near.ai/mbpp/1.0.0 MBPPSolverStrategy --model 'qwen2p5-72b-instruct' --subset test --agent ~/.nearai/registry/flatirons.near/example-travel-agent/1
$ nearai benchmark run near.ai/live_bench/1.0.0 LiveBenchSolverStrategy --model 'qwen2p5-72b-instruct' --agent ~/.nearai/registry/flatirons.near/example-travel-agent/1
```

# Evaluations
## Recording benchmark result as an evaluation

To record benchmark results as an evaluation, pass `--record`. It is strongly recommended to pass this flag after verifying successful run of the benchmark.

```bash
$ nearai benchmark run near.ai/mbpp/1.0.0 MBPPSolverStrategy --model 'llama-3p2-1b-instruct' --subset test
Final score: 131/500 - 26.20%
$ nearai benchmark run near.ai/mbpp/1.0.0 MBPPSolverStrategy --model 'llama-3p2-1b-instruct' --subset test --record
```

That creates new evaluation entry in the registry:
```bash
$ nearai registry list --category=evaluation
┌────────────────────────────────────────────────────────────────────────┬────────────┬───────────────┬────────┐
│ entry                                                                  │ category   │ description   │ tags   │
├────────────────────────────────────────────────────────────────────────┼────────────┼───────────────┼────────┤
│ alomonos.near/evaluation_mbpp_model_llama-v3p2-1b-                     │ evaluation │               │        │
│ instruct_provider_fireworks/0.0.1                                      │            │               │        │
```

## View evaluation table

To view evaluation table in CLI:
```bash
$ nearai evaluation table --num_columns=8
$ nearai evaluation table --all_key_columns --num_columns=8
$ nearai evaluation table --all_metrics
```

https://app.near.ai/evaluations has a functionality to choose any columns.


## Submit an experiment

To submit a new experiment run:

```
nearai submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as nearai are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `nearai.CONFIG.supervisor_id`. See [examples/prepare_data.py](https://github.com/nearai/nearai/blob/main/examples/prepare_data.py) for an example.


## Issues

- [Overwriting existing evaluation entry is currently not supported](https://github.com/nearai/nearai/issues/273)
- [litellm.Timeout errors when running benchmark](https://github.com/nearai/nearai/issues/367)
- [Feature request: tag individual evaluation metrics](https://github.com/nearai/nearai/issues/242)
- [Feature request: add view for a metric](https://github.com/nearai/nearai/issues/331)
- [Feature request: add cost of running benchmark to evaluation results as a separate metric](https://github.com/nearai/nearai/issues/74)
- [Feature request: hide evaluation results for hidden agents and models](https://github.com/nearai/nearai/issues/373)
- [Capabilities Benchmarks Tracking: list of benchmarks we want to add](https://github.com/nearai/nearai/issues/57)

