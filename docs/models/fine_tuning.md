# `nearai` fine-tuning guide

As a part of the `nearai` project, we provide a collection of tools to fine-tune and evaluate models. [Fine-tuning](https://en.wikipedia.org/wiki/Fine-tuning_(deep_learning)) is a set of techniques to tune model parameters in a parameter-efficient way to improve model performance on specific tasks. More commonly, fine-tuning is used to modify the _behavior_ of a pre-trained model. Some examples of this are to produce structured output (JSON, XLM, etc), to produce stylized output (poetic, neutral, etc), or to respond properly to instruction based prompts.

In this guide, we will walk through the process of fine-tuning `llama-3-8b-instruct` on the [orca-math-word-problems-200k](https://huggingface.co/datasets/HuggingFaceH4/orca-math-word-problems-200k) dataset to improve its performance on the [gsm8k](https://huggingface.co/datasets/gsm8k) benchmark.

# Step 1: Create the dataset

The two datasets we will be using are [orca-math-word-problems-200k](https://huggingface.co/datasets/HuggingFaceH4/orca-math-word-problems-200k) and [gsm8k](https://huggingface.co/datasets/gsm8k). Both datasets are a collection of word based math problems + answers. For convenience, we will download the datasets from huggingface, save it to disk, and then upload it into the `nearai` registry.

```python
import re
from textwrap import dedent
from datasets import load_dataset, concatenate_datasets, DatasetDict
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B-Instruct")

ds_math_word_problems = load_dataset("HuggingFaceH4/orca-math-word-problems-200k")
ds_gsm8k = load_dataset("openai/gsm8k", "main")['train']

## create new column by concatenating the 'question' and 'answer' columns
def to_q_a(x):
    q_n_a = tokenizer.apply_chat_template(
        [
            {
                "role": "system",
                "content": "You are a helpful assistant. Please answer the math question."
            },
            {
                "role": "user",
                "content": x["question"]
            },
            {
                "role": "assistant",
                "content": x["answer"]
            }
        ],
        tokenize=False
    )
    return {
        "question_and_answer": q_n_a
    }
ds_math_word_problems = ds_math_word_problems.map(to_q_a)

def to_q_a_gsm8k(x):
    q_n_a = tokenizer.apply_chat_template(
        [
            {
                "role": "system",
                "content": "You are a helpful assistant. Please answer the math question."
            },
            {
                "role": "user",
                "content": x["question"]
            },
            {
                "role": "assistant",
                "content": re.sub(r"<<.*?>>", "", x["answer"])
            }
        ],
        tokenize=False
    )
    return {
        "question_and_answer": q_n_a
    }
ds_gsm8k = ds_gsm8k.map(to_q_a_gsm8k)

## combine the datasets
ds_combined = concatenate_datasets([ds_math_word_problems['train_sft'], ds_gsm8k])
ds_combined = ds_combined.remove_columns([col for col in ds_combined.column_names if col != "question_and_answer"])

# Add a split on 'train'
ds_combined = ds_combined.train_test_split(test_size=0.0001, seed=42)
ds_dict = DatasetDict({
    'train': ds_combined['train'],
    'validation': ds_combined['test']
})
ds_dict.save_to_disk("orca_math_gsm8k_train")
```

```bash
nearai registry upload ./orca_math_gsm8k_train
```

# Step 2: Fine-tune the model

Under the hood, `nearai` uses [torchtune](https://github.com/pytorch/torchtune) to manage the fine-tuning process. To launch a fine-tuning job you can use `nearai finetune`.

Here is the command we used to fine-tune `llama-3-8b-instruct` on our combined `orca-math-word-problems-200k` and `gsm8k` dataset on an 8-GPU machine:

```bash
uv run python3 -m nearai finetune start \
    --model llama-3-8b-instruct \
    --format llama3-8b \
    --tokenizer llama-3-8b-instruct/tokenizer.model \
    --dataset ./orca_math_gsm8k_train \
    --method nearai.finetune.text_completion.dataset \
    --column question_and_answer \
    --split train \
    --num_procs 8
```

To change the configuration of the fine-tuning job, edit `etc/finetune/llama3-8b.yml`.

Included in the output of the command is the path to the fine-tuned model checkpoint. In this case, the path was `~.nearai/finetune/job-2024-08-29_20-58-08-207756662/checkpoint_output`. The path may/will be different based on the time you run the command.

# Step 3: Serve the fine-tuned model

To serve fine-tuned models, we use [vllm](https://github.com/vllm-project/vllm). Once we serve the fine-tuned model + the baseline model, we will benchmark it against both.

```
uv run python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --enable-lora \
    --lora-modules mynewlora=<path_to_checkpoint> \
    --tensor-parallel 8
```

Now we will run the `gsm8k` benchmark on both the baseline model and the fine-tuned model using `nearai benchmark`. The solvers will call our fine-tuned model and the baseline model through the vllm server.

```sh
python3 -m nearai benchmark run \
    cmrfrd.near/gsm8k/0.0.2 \
    GSM8KSolverStrategy \
    --subset test \
    --model local::meta-llama/Meta-Llama-3-8B-Instruct

python3 -m nearai benchmark run \
    cmrfrd.near/gsm8k/0.0.2 \
    GSM8KSolverStrategy \
    --subset test \
    --model local::mynewlora
```

And we can see the results of the benchmark. And we can see that the fine-tuned model performs better than the baseline model.

```
# meta-llama/Meta-Llama-3-8B-Instruct
Correct/Seen - 1061/1319 - 80.44%

# fine tuned llama3-8b-instruct
Correct/Seen - 966/1319 - 73.24%
```

From these results, we can see that our fine-tuned model needs improvement to perform better than the baseline model.