from typing import Any, Dict, List, Mapping, Optional

from datasets import load_from_disk  # type: ignore
from torch.utils.data import Dataset
from torchtune.modules.tokenizers import BaseTokenizer


def truncate(
    tokens: List[Any],
    max_seq_len: int,
    eos_id: Optional[Any] = None,
) -> List[Any]:
    """Truncate a list of tokens to a maximum length. If eos_id is provided, the last token will be replaced with eos_id.

    Args:
    ----
        tokens (List[Any]): list of tokens to truncate
        max_seq_len (int): maximum length of the list
        eos_id (Optional[Any]): token to replace the last token with. If None, the
            last token will not be replaced. Default is None.

    Returns:
    -------
        List[Any]: truncated list of tokens

    """  # noqa: E501
    tokens_truncated = tokens[:max_seq_len]
    if eos_id is not None and tokens_truncated[-1] != eos_id:
        tokens_truncated[-1] = eos_id
    return tokens_truncated


class TextCompletionDataset(Dataset):
    """Freeform dataset for any unstructured text corpus. Quickly load any dataset from Hugging Face or local disk and tokenize it for your model.

    Args:
    ----
        tokenizer (BaseTokenizer): Tokenizer used to encode data. Tokenize must implement an ``encode`` and ``decode`` method.
        source (str): path string of dataset, anything supported by Hugging Face's ``load_dataset``
            (https://huggingface.co/docs/datasets/en/package_reference/loading_methods#datasets.load_dataset.path)
        column (str): name of column in the sample that contains the text data. This is typically required
            for Hugging Face datasets or tabular data. For local datasets with a single column, use the default "text",
            which is what is assigned by Hugging Face datasets when loaded into memory. Default is "text".
        max_seq_len (Optional[int]): Maximum number of tokens in the returned input and label token id lists.
            Default is None, disabling truncation. We recommend setting this to the highest you can fit in memory
            and is supported by the model. For example, llama2-7B supports up to 4096 for sequence length.
        **load_dataset_kwargs (Dict[str, Any]): additional keyword arguments to pass to ``load_dataset``.

    """  # noqa: E501

    def __init__(  # noqa: D107
        self,
        tokenizer: BaseTokenizer,
        source: str,
        column: str = "text",
        split: Optional[str] = None,
        max_seq_len: Optional[int] = None,
        **load_dataset_kwargs: Dict[str, Any],
    ) -> None:
        self._tokenizer = tokenizer
        self._data = load_from_disk(source, **load_dataset_kwargs)
        if split is not None:
            self._data = self._data[split]
        self.max_seq_len = max_seq_len
        self._column = column

    def __len__(self) -> int:  # noqa: D105
        return len(self._data)

    def __getitem__(self, index: int) -> Dict[str, List[int]]:  # noqa: D105
        sample = self._data[index]
        return self._prepare_sample(sample)

    def _prepare_sample(self, sample: Mapping[str, Any]) -> Dict[str, List[int]]:
        prompt = sample[self._column]
        tokens = self._tokenizer.encode(text=prompt, add_bos=True, add_eos=True)

        # Truncate if needed, but don't coerce EOS id
        if self.max_seq_len is not None:
            tokens = truncate(tokens, self.max_seq_len - 1)

        # No need to offset labels by 1 - happens in the recipe
        labels = tokens.copy()

        return {"tokens": tokens, "labels": labels}


def dataset(
    tokenizer: BaseTokenizer,
    source: str,
    column: str = "text",
    split: str = "train",
    max_seq_len: Optional[int] = None,
    **load_from_disk_kwargs: Dict[str, Any],
) -> TextCompletionDataset:
    ds = TextCompletionDataset(
        tokenizer=tokenizer,
        source=source,
        column=column,
        split=split,
        max_seq_len=max_seq_len,
        **load_from_disk_kwargs,
    )
    return ds
